import os
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QTextBrowser, 
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt, QUrl, QThread, Signal, QObject
from PySide6.QtGui import QTextOption
import hashlib
import requests
import re

class BaseUiDialog(QDialog):
    def __init__(self, ui_name, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ui_path = os.path.join(base_dir, "pygui", "dialogs", ui_name)
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

    def showEvent(self, event):
        """Play a smooth fade-in animation when the dialog opens."""
        from PySide6.QtCore import QPropertyAnimation
        self.setWindowOpacity(0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()
        super().showEvent(event)

    def _fade_out_and_close(self, result_code):
        """Play fade-out and then close with the given result code."""
        from PySide6.QtCore import QPropertyAnimation
        self.exit_anim = QPropertyAnimation(self, b"windowOpacity")
        self.exit_anim.setDuration(250)
        self.exit_anim.setStartValue(1)
        self.exit_anim.setEndValue(0)
        self.exit_anim.finished.connect(lambda: self.done(result_code))
        self.exit_anim.start()

    def accept(self):
        self._fade_out_and_close(QDialog.Accepted)

    def reject(self):
        self._fade_out_and_close(QDialog.Rejected)

class AboutDialog(BaseUiDialog):
    def __init__(self, parent=None):
        super().__init__("about.ui", parent)
        self.setFixedSize(300, 180)
        
        # Set dynamic text to avoid hardcoding in UI files
        from ...utils.constants import APP_VERSION, APP_COPYRIGHT, APP_NAME
        
        lbl_name = self.ui.findChild(QLabel, "labelAppName")
        lbl_version = self.ui.findChild(QLabel, "labelVersion")
        lbl_copyright = self.ui.findChild(QLabel, "labelCopyright")
        
        if lbl_name: lbl_name.setText(APP_NAME)
        if lbl_version: lbl_version.setText(f"Version {APP_VERSION}")
        if lbl_copyright: lbl_copyright.setText(APP_COPYRIGHT)

def get_logical_filename(url):
    import urllib.parse
    import re
    unquoted = urllib.parse.unquote(url)
    ext = unquoted.split('.')[-1].split('?')[0]
    if len(ext) > 4 or not ext or '/' in ext:
        ext = 'png'
    clean = re.sub(r'^https?://', '', unquoted)
    clean = re.sub(r'^(img\.shields\.io/badge/|raw\.githubusercontent\.com/)', '', clean)
    clean = re.sub(r'[^a-zA-Z0-9\-_.]', '-', clean)
    clean = re.sub(r'-+', '-', clean)
    clean = clean.strip('-')
    if not clean.endswith(f".{ext}"):
        clean = f"{clean}.{ext}"
    return clean


class ImageDownloadWorker(QObject):
    image_ready = Signal()

    def __init__(self, urls, cache_dir):
        super().__init__()
        self.urls = urls
        self.cache_dir = cache_dir

    def run(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        for url in self.urls:
            filename = get_logical_filename(url)
            local_path = os.path.join(self.cache_dir, filename)
            
            if not os.path.exists(local_path):
                try:
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(r.content)
                        self.image_ready.emit()
                except Exception as e:
                    print(f"DEBUG: Download failed for {url}: {e}")
        
class ReadmeDialog(BaseUiDialog):
    def __init__(self, theme="light", parent=None):
        super().__init__("readme.ui", parent)
        self.theme = theme
        self.setFixedSize(800, 600)
        
        self.viewer = self.findChild(QTextBrowser, "textBrowser")
        self.btnClose = self.findChild(QPushButton, "closeBtn")
        
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)
            
        # For background downloads
        self.download_thread = None
        self.worker = None
        
        self.load_readme()

    def load_readme(self):
        if not self.viewer: return
        
        # Set base path for local images
        import sys
        if sys.platform == "win32":
            app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
        self.viewer.setSearchPaths([app_dir])
        
        md_text = ""
        # Try to resolve README.md from the bundle/development directory
        if hasattr(sys, '_MEIPASS'):
            readme_path = os.path.join(sys._MEIPASS, "README.md")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            readme_path = os.path.join(base_dir, "README.md")
            
        if not os.path.exists(readme_path):
            readme_path = os.path.join(os.getcwd(), "README.md")
            
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                md_text = f.read()
        
        if md_text:
            # 1. First Pass: Replace already cached images and identify missing ones
            md_text, missing_urls = self._prepare_readme_content(md_text)
            
            # 2. Start background downloader if needed
            if missing_urls:
                self._start_background_download(missing_urls)
            
            try:
                import markdown
                html_body = markdown.markdown(md_text, extensions=["fenced_code", "tables", "extra"])
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
                    img {{ max-width: 100%; height: auto; display: inline-block; margin: 5px; }}
                    h1, h2, h3 {{ border-bottom: 1px solid {border_color}; padding-bottom: .3em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
                    pre {{ 
                        background-color: {code_bg}; 
                        padding: 16px; 
                        border-radius: 6px; 
                        border: 1px solid {border_color};
                        overflow-x: auto;
                    }}
                    code {{ background-color: {code_bg}; padding: .2em .4em; border-radius: 3px; font-family: 'Consolas', 'Monaco', monospace; }}
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

    def _prepare_readme_content(self, md_text):
        """Identifies which images are cached and which need downloading."""
        import sys
        if sys.platform == "win32":
            app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
            
        cache_dir = os.path.join(app_dir, "assets", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        img_urls = re.findall(r'!\[.*?\]\((https?://.*?)\)', md_text)
        img_urls += re.findall(r'<img.*?src=["\'](https?://.*?)["\']', md_text)
        
        missing_urls = []
        for url in set(img_urls):
            filename = get_logical_filename(url)
            local_path = os.path.join(cache_dir, filename)
            
            if os.path.exists(local_path):
                local_url = QUrl.fromLocalFile(local_path).toString()
                md_text = md_text.replace(url, local_url)
            else:
                missing_urls.append(url)
            
        return md_text, missing_urls

    def _start_background_download(self, urls):
        """Launches the background thread to fetch images."""
        if self.download_thread and self.download_thread.isRunning():
            return
            
        import sys
        if sys.platform == "win32":
            app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
            
        self.download_thread = QThread()
        self.worker = ImageDownloadWorker(urls, os.path.join(app_dir, "assets", "cache"))
        self.worker.moveToThread(self.download_thread)
        
        self.download_thread.started.connect(self.worker.run)
        self.worker.image_ready.connect(self.load_readme) # Refresh on every image
        
        # Cleanup
        self.worker.image_ready.connect(self.worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        
        self.download_thread.start()

class TrafficDialog(BaseUiDialog):
    def __init__(self, parent=None, session_text="", daily_text="", history=None):
        super().__init__("traffic.ui", parent)
        self.setFixedSize(460, 560)
        
        # Access managers from parent (DashboardView)
        self.manager = parent.manager if parent else None
        self.ts_manager = parent.ts_manager if parent else None
        
        # Resolve UI elements
        self.labelStatus = self.ui.findChild(QLabel, "labelStatus")
        self.labelActiveProfile = self.ui.findChild(QLabel, "labelActiveProfile")
        self.labelActiveIP = self.ui.findChild(QLabel, "labelActiveIP")
        self.labelLoginServer = self.ui.findChild(QLabel, "labelLoginServer")
        
        label_stats = self.ui.findChild(QLabel, "labelStats")
        label_daily = self.ui.findChild(QLabel, "labelDailyStats")
        table_history = self.ui.findChild(QTableWidget, "tableHistory")
        
        if label_stats:
            clean_session = session_text.replace("Traffic: ", "") if session_text else "Sent 0.00 B / Received 0.00 B"
            label_stats.setText(clean_session)
            
        if label_daily:
            label_daily.setText(daily_text)
            
        # Connect status updates if we have the ts_manager
        if self.ts_manager:
            self.ts_manager.connection_status_changed.connect(self._on_status_changed)
            self._on_status_changed(*self.ts_manager.check_status())
            
        # Populate History Section
        if table_history and history:
            def format_b(b):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if b < 1024: return f"{b:.2f} {unit}"
                    b /= 1024
                return f"{b:.2f} TB"

            table_history.setRowCount(len(history))
            table_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            for i, (ts, sent, recv) in enumerate(history):
                table_history.setItem(i, 0, QTableWidgetItem(ts))
                table_history.setItem(i, 1, QTableWidgetItem(format_b(sent)))
                table_history.setItem(i, 2, QTableWidgetItem(format_b(recv)))
                
                # Make items non-editable (redundant due to UI property but good practice)
                for col in range(3):
                    table_history.item(i, col).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        elif table_history:
            table_history.setRowCount(1)
            table_history.setColumnCount(3)
            table_history.setItem(0, 0, QTableWidgetItem("No history available"))

    def _on_status_changed(self, is_connected, status_text):
        if not self.labelStatus:
            return
            
        if is_connected:
            self.labelStatus.setText("Connected")
            self.labelStatus.setStyleSheet("color: #22c55e; font-weight: bold;")
        else:
            if status_text == "Pending Admin Approval":
                self.labelStatus.setText("Pending Admin Approval")
                self.labelStatus.setStyleSheet("color: #f59e0b; font-weight: bold;")
            elif "Connecting" in status_text or status_text == "Checking...":
                self.labelStatus.setText("Connecting...")
                self.labelStatus.setStyleSheet("color: #eab308; font-weight: bold;")
            else:
                self.labelStatus.setText("Disconnected")
                self.labelStatus.setStyleSheet("color: #ef4444; font-weight: bold;")
                
        # Resolve active profile name
        active_name = "Default"
        parent = self.parent()
        if parent and hasattr(parent, 'profile') and parent.profile:
            active_name = parent.profile.name
            
        if self.labelActiveProfile:
            self.labelActiveProfile.setText(active_name)
            
        # Resolve active profile URL
        if self.labelLoginServer and self.manager:
            profile = self.manager.profiles.get(active_name) if active_name != "Default" else None
            login_server = profile.login_server if profile else "https://controlplane.tailscale.com"
            self.labelLoginServer.setText(login_server)
            
        # Fetch Active IP
        if self.labelActiveIP and self.ts_manager:
            cached_status = self.ts_manager.cache.get("status")
            ips = cached_status.get("ips", []) if cached_status else []
            if ips:
                self.labelActiveIP.setText(", ".join(ips))
            else:
                self.labelActiveIP.setText("-")

    def closeEvent(self, event):
        try:
            if self.ts_manager:
                self.ts_manager.connection_status_changed.disconnect(self._on_status_changed)
        except Exception:
            pass
        super().closeEvent(event)

class LicenseDialog(QDialog):
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self.setWindowTitle("License")
        self.setFixedSize(600, 450)
        layout = QVBoxLayout(self)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setReadOnly(True)
        
        bg_color = "#1e1e1e" if theme == "dark" else "#ffffff"
        text_color = "#d4d4d4" if theme == "dark" else "#1a1a1a"
        self.text_browser.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; font-family: monospace;")
        
        content = "LICENSE file not found."
        import sys
        if hasattr(sys, '_MEIPASS'):
            license_path = os.path.join(sys._MEIPASS, "LICENSE")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            license_path = os.path.join(base_dir, "LICENSE")
            
        if not os.path.exists(license_path):
            license_path = os.path.join(os.getcwd(), "LICENSE")
            
        if os.path.exists(license_path):
            with open(license_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.text_browser.setPlainText(content)
        layout.addWidget(self.text_browser)
        
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.accept)
        self.btnClose.setFixedWidth(100)
        layout.addWidget(self.btnClose, alignment=Qt.AlignCenter)
