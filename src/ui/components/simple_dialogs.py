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
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
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
        
        self.viewer = self.findChild(QTextBrowser, "textBrowser")
        self.btnClose = self.findChild(QPushButton, "closeBtn")
        
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)
            
        self.load_readme()

    def load_readme(self):
        if not self.viewer: return
        
        md_text = ""
        if os.path.exists("README.md"):
            with open("README.md", "r", encoding="utf-8") as f:
                md_text = f.read()
        
        if md_text:
            try:
                import markdown
                html_body = markdown.markdown(md_text, extensions=["fenced_code", "tables"])
            except ImportError:
                html_body = f"<pre style='white-space: pre-wrap;'>{md_text}</pre>"
            
            bg_color = "#ffffff" if self.theme == "light" else "#1a1e2e"
            text_color = "#1a1a1a" if self.theme == "light" else "#e5e7eb"
            link_color = "#0056b3" if self.theme == "light" else "#60a5fa"
            code_bg = "#f6f8fa" if self.theme == "light" else "#0f111a"
            border_color = "#eaecef" if self.theme == "light" else "#3d4b7c"
            
            content = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                        background-color: {bg_color};
                        color: {text_color};
                        line-height: 1.6;
                        padding: 20px;
                    }}
                    h1, h2, h3 {{ border-bottom: 1px solid {border_color}; padding-bottom: .3em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
                    pre {{ 
                        background-color: {code_bg}; 
                        padding: 16px; 
                        border-radius: 6px; 
                        border: 1px solid {border_color};
                    }}
                    code {{ background-color: {code_bg}; padding: .2em .4em; border-radius: 3px; font-family: monospace; }}
                    a {{ color: {link_color}; text-decoration: none; }}
                    table {{ border-spacing: 0; border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
                    table th, table td {{ border: 1px solid {border_color}; padding: 6px 13px; }}
                </style>
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
            self.viewer.setHtml(content)
        else:
            self.viewer.setPlainText("README.md not found.")

class TrafficDialog(BaseUiDialog):
    def __init__(self, parent=None, session_text="", daily_text="", history=None):
        super().__init__("traffic.ui", parent)
        
        label_stats = self.ui.findChild(QLabel, "labelStats")
        label_daily = self.ui.findChild(QLabel, "labelDailyStats")
        label_history = self.ui.findChild(QLabel, "labelHistory")
        
        if label_stats:
            label_stats.setText(session_text)
        if label_daily:
            label_daily.setText(daily_text)
            
        # Populate History Section
        if label_history and history:
            history_html = """
                <table width='100%' border='0' cellspacing='0' cellpadding='5' style='font-family: Courier New;'>
                    <tr style='background-color: #f0f0f0;'>
                        <th align='left'><b>Timestamp</b></th>
                        <th align='right'><b>Sent</b></th>
                        <th align='right'><b>Received</b></th>
                    </tr>
            """
            
            def format_b(b):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if b < 1024: return f"{b:.2f} {unit}"
                    b /= 1024
                return f"{b:.2f} TB"

            for i, (ts, sent, recv) in enumerate(history):
                bg = "white" if i % 2 == 0 else "#fafafa"
                history_html += f"""
                    <tr bgcolor='{bg}'>
                        <td style='border-bottom: 1px solid #eee;'>{ts}</td>
                        <td align='right' style='border-bottom: 1px solid #eee;'>{format_b(sent)}</td>
                        <td align='right' style='border-bottom: 1px solid #eee;'>{format_b(recv)}</td>
                    </tr>
                """
            history_html += "</table>"
            label_history.setText(history_html)
        elif label_history:
            label_history.setText("<i>No history available for this profile.</i>")

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
