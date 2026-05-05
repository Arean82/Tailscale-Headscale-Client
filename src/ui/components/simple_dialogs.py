import os
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QTextBrowser, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtGui import QTextOption

class BaseUiDialog(QDialog):
    def __init__(self, ui_name, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "dialogs", ui_name)
        ui_file = QFile(ui_path)
        if ui_file.exists():
            ui_file.open(QFile.ReadOnly)
            self.ui = loader.load(ui_file)
            ui_file.close()
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.ui)
            
            self.setWindowTitle(self.ui.windowTitle())
            
            # Common close button finding
            self.btnClose = self.ui.findChild(QPushButton, "btnClose")
            if self.btnClose:
                self.btnClose.clicked.connect(self.accept)
                self.btnClose.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: bold;")

class AboutDialog(BaseUiDialog):
    def __init__(self, parent=None):
        super().__init__("about.ui", parent)
        
        # Set dynamic text to avoid hardcoding in UI files
        from ...logic.constants import APP_VERSION, APP_COPYRIGHT, APP_NAME
        
        lbl_name = self.ui.findChild(QLabel, "labelAppName")
        lbl_version = self.ui.findChild(QLabel, "labelVersion")
        lbl_copyright = self.ui.findChild(QLabel, "labelCopyright")
        
        if lbl_name: lbl_name.setText(APP_NAME)
        if lbl_version: lbl_version.setText(f"Version {APP_VERSION}")
        if lbl_copyright: lbl_copyright.setText(APP_COPYRIGHT)

class ReadmeDialog(BaseUiDialog):
    def __init__(self, theme="light", parent=None):
        super().__init__("readme.ui", parent)
        self.theme = theme
        self.resize(1000, 800)
        
        # Replace QTextBrowser with QWebEngineView for badge support
        self.old_viewer = self.findChild(QTextBrowser, "textBrowser")
        self.btnClose = self.findChild(QPushButton, "closeBtn")
        
        from PySide6.QtWebEngineWidgets import QWebEngineView
        self.viewer = QWebEngineView()
        
        # Replace the old viewer in the layout
        if self.old_viewer and self.old_viewer.parentWidget():
            layout = self.old_viewer.parentWidget().layout()
            if layout:
                layout.replaceWidget(self.old_viewer, self.viewer)
                self.old_viewer.deleteLater()
        
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)
            
        self.load_readme()

    def load_readme(self):
        content = "README.md not found."
        md_text = ""
        if os.path.exists("README.md"):
            with open("README.md", "r", encoding="utf-8") as f:
                md_text = f.read()
        
        if md_text:
            try:
                import markdown
                html_body = markdown.markdown(md_text, extensions=["fenced_code", "tables"])
            except ImportError:
                html_body = f"<pre>{md_text}</pre>"
            
            bg_color = "#ffffff" if self.theme == "light" else "#1a1a1a"
            text_color = "#1a1a1a" if self.theme == "light" else "#ffffff"
            link_color = "#0056b3" if self.theme == "light" else "#40a9ff"
            
            content = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                        margin: 40px auto;
                        max-width: 900px;
                        background-color: {bg_color};
                        color: {text_color};
                        line-height: 1.6;
                        padding: 0 20px;
                    }}
                    h1, h2, h3 {{ border-bottom: 1px solid #eaecef; padding-bottom: .3em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
                    pre {{ 
                        background-color: #f6f8fa; 
                        padding: 16px; 
                        border-radius: 6px; 
                        border: 1px solid #ddd;
                        overflow: auto;
                    }}
                    code {{ background-color: rgba(27,31,35,.05); padding: .2em .4em; border-radius: 3px; font-family: SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace; }}
                    a {{ color: {link_color}; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    img {{ max-width: 100%; }}
                    table {{ border-spacing: 0; border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
                    table th, table td {{ border: 1px solid #dfe2e5; padding: 6px 13px; }}
                    table tr {{ background-color: {bg_color}; border-top: 1px solid #c6cbd1; }}
                    table tr:nth-child(2n) {{ background-color: #f6f8fa; }}
                </style>
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
        self.viewer.setHtml(content)

class TrafficDialog(BaseUiDialog):
    def __init__(self, parent=None, stats_text=""):
        super().__init__("traffic.ui", parent)
        label_stats = self.findChild(QLabel, "labelStats")
        if label_stats:
            label_stats.setText(stats_text)

class LicenseDialog(QDialog):
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self.setWindowTitle("License")
        self.resize(600, 450)
        layout = QVBoxLayout(self)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setReadOnly(True)
        
        bg_color = "#1e1e1e" if theme == "dark" else "#ffffff"
        text_color = "#d4d4d4" if theme == "dark" else "#1a1a1a"
        self.text_browser.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; font-family: monospace;")
        
        content = "LICENSE file not found."
        if os.path.exists("LICENSE"):
            with open("LICENSE", "r", encoding="utf-8") as f:
                content = f.read()
        self.text_browser.setPlainText(content)
        layout.addWidget(self.text_browser)
        
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.accept)
        self.btnClose.setFixedWidth(100)
        layout.addWidget(self.btnClose, alignment=Qt.AlignCenter)
