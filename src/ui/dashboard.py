import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

class DashboardView(QWidget):
    def __init__(self, manager, ts_manager, profile=None):
        super().__init__()
        self.manager = manager
        self.ts_manager = ts_manager
        self.profile = profile
        
        # 1. Load your UI file
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "windows", "tab_widget.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.ui_content = loader.load(ui_file) # The top-level QWidget from your UI
        ui_file.close()
        
        # 2. Embed the content using a layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui_content)
        
        # 3. Find widgets within the loaded content
        self.lineEditUrl = self.ui_content.findChild(QLineEdit, "lineEditUrl")
        self.btnVpnAction = self.ui_content.findChild(QPushButton, "btnVpnAction")
        self.labelStatus = self.ui_content.findChild(QLabel, "labelStatus")
        self.btnChangeCredentials = self.ui_content.findChild(QPushButton, "btnChangeCredentials")
        self.btnShowStats = self.ui_content.findChild(QPushButton, "btnShowStats")
        self.labelTraffic = self.ui_content.findChild(QLabel, "labelTraffic")
        
        # 4. Populate with data
        if profile and self.lineEditUrl:
            self.lineEditUrl.setText(profile.login_server)
        
        # 5. Connect signals
        if self.btnVpnAction:
            self.btnVpnAction.clicked.connect(self.toggle_connection)
            # Initial state set by update_status
        if self.btnChangeCredentials:
            self.btnChangeCredentials.clicked.connect(self.change_credentials)
            # Remove hardcoded gray - will be styled by MainWindow QSS
        if self.btnShowStats:
            self.btnShowStats.clicked.connect(self.show_traffic_stats)
            # Remove hardcoded gray - will be styled by MainWindow QSS
            
        self.ts_manager.connection_status_changed.connect(self.update_status)
        # Initial status update
        self.update_status(*self.ts_manager.check_status())

    def show_traffic_stats(self):
        from .components.simple_dialogs import TrafficDialog
        # In the original app, it updates labelTraffic on the tab
        # We can pass the current text to the dialog
        stats = self.labelTraffic.text() if self.labelTraffic else "No stats available."
        TrafficDialog(self, stats).exec()

    def change_credentials(self):
        from .components.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self, self.profile)
        if dialog.exec():
            data = dialog.get_data()
            if not data: return
            if self.profile:
                self.profile.login_server = data["login_server"]
                self.profile.auth_key = data["auth_key"]
                # Match original 'google' mode naming
                self.profile.auth_mode = "google" if data["auth_mode"] == "sso" else data["auth_mode"]
                self.manager.save_profiles()
                if self.lineEditUrl:
                    self.lineEditUrl.setText(self.profile.login_server)


    def update_status(self, is_connected, status_text):
        if not self.labelStatus: return
        
        if is_connected:
            self.labelStatus.setText("🟢 Connected")
            self.labelStatus.setStyleSheet("color: #22c55e; font-weight: bold;") # Emerald
            if self.btnVpnAction:
                self.btnVpnAction.setText("Logout")
                self.btnVpnAction.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; border-radius: 6px;") # Rose
            if self.btnChangeCredentials:
                self.btnChangeCredentials.setEnabled(False)
        else:
            self.labelStatus.setText("🔴 Disconnected")
            self.labelStatus.setStyleSheet("color: #ef4444; font-weight: bold;") # Rose
            if self.btnVpnAction:
                self.btnVpnAction.setText("Connect")
                self.btnVpnAction.setStyleSheet("background-color: #22c55e; color: white; font-weight: bold; border-radius: 6px;") # Emerald
            if self.btnChangeCredentials:
                self.btnChangeCredentials.setEnabled(True)

    def toggle_connection(self):
        is_connected, _ = self.ts_manager.check_status()
        if is_connected:
            self.ts_manager.logout()
        else:
            url = self.lineEditUrl.text() if self.lineEditUrl else "https://controlplane.tailscale.com"
            key = self.profile.auth_key if self.profile else ""
            # Original app uses 'google' for SSO
            is_sso = self.profile.auth_mode == "google" if self.profile else False
            
            if is_sso:
                from .components.progress_dialog import ProgressDialog
                import webbrowser
                
                self.sso_dialog = ProgressDialog(self)
                self.sso_dialog.set_message("Initializing SSO Login...")
                self.sso_dialog.show()
                
                # Connect to SSO URL detection
                def on_url_found(sso_url):
                    webbrowser.open(sso_url)
                    self.sso_dialog.set_message("Please complete login in your browser...")
                
                def on_finished(code, status):
                    self.sso_dialog.close()
                    self.ts_manager.check_status()
                
                # Disconnect old connections to avoid duplicates
                try: self.ts_manager.worker.sso_url_found.disconnect()
                except: pass
                try: self.ts_manager.worker.finished.disconnect()
                except: pass
                
                self.ts_manager.worker.sso_url_found.connect(on_url_found)
                self.ts_manager.worker.finished.connect(on_finished)
                
                self.ts_manager.connect(url, None, True)
            else:
                self.ts_manager.connect(url, key, False)
                # Brief delay to allow command to start before checking status
                from PySide6.QtCore import QTimer
                QTimer.singleShot(2000, self.ts_manager.check_status)

