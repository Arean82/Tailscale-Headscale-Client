import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer

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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.addWidget(self.ui_content)
        
        # 3. Find widgets within the loaded content
        self.lineEditUrl = self.ui_content.findChild(QLineEdit, "lineEditUrl")
        self.btnVpnAction = self.ui_content.findChild(QPushButton, "btn_connect")
        self.labelStatus = self.ui_content.findChild(QLabel, "labelStatus")
        self.btnChangeCredentials = self.ui_content.findChild(QPushButton, "btnChangeCredentials")
        self.btnShowStats = self.ui_content.findChild(QPushButton, "btnShowStats")
        self.labelTraffic = self.ui_content.findChild(QLabel, "labelTraffic")
        
        # 4. Populate with data
        if profile and self.lineEditUrl:
            self.lineEditUrl.setText(profile.login_server)
        
        # 5. Connect signals
        if self.btnVpnAction:
            self.btnVpnAction.setProperty("colored", "true")
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

        # 6. Setup Traffic Monitoring
        self.prev_stats = None
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_traffic_label)
        self.stats_timer.start(3000) # Every 3 seconds

    def show_traffic_stats(self):
        from .components.simple_dialogs import TrafficDialog
        
        # 1. Get current session stats (from label)
        session_stats = self.labelTraffic.text() if self.labelTraffic else "No session data."
        
        # 2. Get daily totals from DB
        profile_name = self.profile.name if self.profile else "Default"
        
        # Flush buffer so the user sees the latest data
        self.manager.db.flush_buffer()
        
        sent_daily, recv_daily = self.manager.db.get_daily_total(profile_name)
        daily_text = f"Today: Sent {self._format_bytes(sent_daily)} / Received {self._format_bytes(recv_daily)}"
        
        # 3. Get history (Daily totals for last 10 days)
        history = self.manager.db.get_daily_history(profile_name, days=10)
        
        dialog = TrafficDialog(self, session_stats, daily_text, history)
        dialog.exec()

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
        
        # If we are checking, don't revert to "Disconnected" if we were already connected
        if status_text == "Checking..." and self.labelStatus.text() == "🟢 Connected":
            return

        if is_connected:
            self.labelStatus.setText("🟢 Connected")
            self.labelStatus.setStyleSheet("color: #22c55e; font-weight: bold;")
            
            # Capture baseline if not already set (for session tracking)
            if self.prev_stats is None:
                self.prev_stats = self.ts_manager.get_stats()
            
            if self.btnVpnAction:
                self.btnVpnAction.setText("Logout")
                self.btnVpnAction.setStyleSheet("""
                    QPushButton { background-color: #f44336; color: white; font-weight: bold; border-radius: 6px; }
                    QPushButton:hover { background-color: #da190b; }
                """)
            if self.btnChangeCredentials:
                self.btnChangeCredentials.setEnabled(False)
        else:
            self.labelStatus.setText("🔴 Disconnected")
            self.labelStatus.setStyleSheet("color: #ef4444; font-weight: bold;")
            
            # Reset baseline when disconnected
            self.prev_stats = None
            
            if self.btnVpnAction:
                self.btnVpnAction.setText("Connect")
                self.btnVpnAction.setStyleSheet("""
                    QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 6px; }
                    QPushButton:hover { background-color: #45a049; }
                """)
            if self.btnChangeCredentials:
                self.btnChangeCredentials.setEnabled(True)

    def toggle_connection(self):
        is_connected, _ = self.ts_manager.check_status()
        if is_connected:
            self.ts_manager.logout(self.profile.name if self.profile else None)
        else:
            url = self.lineEditUrl.text() if self.lineEditUrl else "https://controlplane.tailscale.com"
            key = self.profile.auth_key if self.profile else ""
            # Original app uses 'google' for SSO
            is_sso = self.profile.auth_mode == "google" if self.profile else False
            
            if self.btnVpnAction:
                self.btnVpnAction.setText("Connecting...")
                self.btnVpnAction.setStyleSheet("""
                    QPushButton { background-color: #FFA500; color: white; font-weight: bold; border-radius: 6px; }
                    QPushButton:hover { background-color: #FF8C00; }
                """)
            
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
                
                self.ts_manager.connect(url, None, True, self.profile.name if self.profile else None)
            else:
                self.ts_manager.connect(url, key, False, self.profile.name if self.profile else None)
                # Brief delay to allow command to start before checking status
                from PySide6.QtCore import QTimer
                QTimer.singleShot(2000, self.ts_manager.check_status)

    def _update_traffic_label(self):
        if not self.labelTraffic: return
        
        stats = self.ts_manager.get_stats()
        if stats and self.prev_stats:
            # Match original app: Show traffic SINCE the session started
            sent = stats.bytes_sent - self.prev_stats.bytes_sent
            recv = stats.bytes_recv - self.prev_stats.bytes_recv
            
            text = f"Traffic: Sent {self._format_bytes(sent)} / Received {self._format_bytes(recv)}"
            self.labelTraffic.setText(text)
            
            # Log to DB (if profile exists)
            if self.profile:
                self.manager.db.insert_traffic_data(self.profile.name, stats.bytes_sent, stats.bytes_recv)
        elif stats and not self.prev_stats:
            # Baseline not yet captured
            self.prev_stats = stats

    def _format_bytes(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
