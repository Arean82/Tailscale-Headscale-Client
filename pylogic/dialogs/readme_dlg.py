# pylogic/dialogs/readme_dlg.py
# Replaces gui/readme_viewer.py (pywebview + multiprocessing) with QWebEngineView.
# Runs entirely in-process — no subprocess needed.
# Loads pygui/dialogs/readme.ui which hosts a QWebEngineView.

import os

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from pylogic.ui_helpers import load_ui, center_window


# Inline CSS for the rendered README — mirrors the original pywebview styling
_README_CSS = """
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    margin: 40px auto;
    max-width: 720px;
    padding-bottom: 80px;
    color: #24292e;
  }
  h1, h2, h3 { border-bottom: 1px solid #e1e4e8; padding-bottom: 6px; }
  pre  { background: #f6f8fa; padding: 14px; border-radius: 6px; overflow-x: auto; }
  code { background: #f6f8fa; padding: 3px 6px; border-radius: 4px; font-size: 90%; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #dfe2e5; padding: 8px 12px; }
</style>
"""


class ReadmeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = load_ui("pygui/dialogs/readme.ui", parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowTitle("README — TAILSCALE VPN Client")
        self.resize(820, 620)

        if parent:
            center_window(parent, self)

        self.ui.btnClose.clicked.connect(self.accept)
        self._load_readme()

    # ------------------------------------------------------------------

    def _load_readme(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        path = os.path.join(base_dir, "README.md")

        if not os.path.exists(path):
            self.ui.webView.setHtml(
                "<h2>README not found</h2>"
                "<p>No README.md file was found in the project root.</p>"
            )
            return

        with open(path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Convert markdown → HTML
        try:
            import markdown
            html_body = markdown.markdown(
                md_content, extensions=["fenced_code", "tables"]
            )
        except ImportError:
            # Fallback: show raw markdown in a <pre> block if markdown pkg missing
            html_body = f"<pre>{md_content}</pre>"

        full_html = f"<!DOCTYPE html><html><head>{_README_CSS}</head><body>{html_body}</body></html>"
        self.ui.webView.setHtml(full_html, QUrl("file:///"))
