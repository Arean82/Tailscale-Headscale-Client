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

        # 7. Setup Pulse Animation (for "Connecting..." state)
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, Qt, QEasingCurve
        self.opacity_effect = QGraphicsOpacityEffect(self.btnVpnAction)
        self.btnVpnAction.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(1000)
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setEndValue(0.4)
        self.pulse_anim.setLoopCount(-1) # Infinite
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutQuad)

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
        
        # Stop pulse if we are no longer connecting
        if status_text != "Checking..." and "Connecting" not in self.btnVpnAction.text():
            if hasattr(self, 'pulse_anim'):
                self.pulse_anim.stop()
                self.opacity_effect.setOpacity(1.0)
        
        # If we are checking, don't revert to "Disconnected" if we were already connected
        if status_text == "Checking..." and self.labelStatus.text() == "🟢 Connected":
            return

        if is_connected:
            self.labelStatus.setText("🟢 Connected")
            self.labelStatus.setStyleSheet("color: #22c55e; font-weight: bold;")
            
            self.prev_stats = None
            
        # Capture baseline if not already set (for session tracking)
        if is_connected:
            if self.prev_stats is None:
                self.prev_stats = self.ts_manager.get_stats()
            
            if self.btnVpnAction:
                self.btnVpnAction.setText("Logout")
                self.btnVpnAction.setStyleSheet("""
                    QPushButton { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #b91c1c);
                        color: white; 
                        font-weight: bold; 
                        border-radius: 6px;
                        border: 1px solid #991b1b;
                    }
                    QPushButton:hover { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #dc2626);
                    }
                """)
            if self.btnChangeCredentials:
                self.btnChangeCredentials.setEnabled(False)
                self.btnChangeCredentials.setStyleSheet("""
                    QPushButton { 
                        background-color: #374151; color: #9ca3af; font-weight: bold; border-radius: 6px; 
                    }
                """)
            if self.btnShowStats:
                self.btnShowStats.setStyleSheet("""
                    QPushButton { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d97706, stop:1 #92400e);
                        color: white; font-weight: bold; border-radius: 6px; border: 1px solid #b45309;
                    }
                    QPushButton:hover { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #d97706);
                    }
                """)
        else:
            self.labelStatus.setText("🔴 Disconnected")
            self.labelStatus.setStyleSheet("color: #ef4444; font-weight: bold;")
            
            # Reset baseline when disconnected
            self.prev_stats = None
            
            if self.btnVpnAction:
                self.btnVpnAction.setText("Connect")
                self.btnVpnAction.setStyleSheet("""
                    QPushButton { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #15803d);
                        color: white; 
                        font-weight: bold; 
                        border-radius: 6px;
                        border: 1px solid #166534;
                    }
                    QPushButton:hover { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #16a34a);
                    }
                """)
            if self.btnChangeCredentials:
                self.btnChangeCredentials.setEnabled(True)
                self.btnChangeCredentials.setStyleSheet("""
                    QPushButton { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4338ca);
                        color: white; font-weight: bold; border-radius: 6px; border: 1px solid #4f46e5;
                    }
                    QPushButton:hover { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #818cf8, stop:1 #4f46e5);
                    }
                """)
            if self.btnShowStats:
                self.btnShowStats.setStyleSheet("""
                    QPushButton { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d97706, stop:1 #92400e);
                        color: white; font-weight: bold; border-radius: 6px; border: 1px solid #b45309;
                    }
                    QPushButton:hover { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #d97706);
                    }
                """)

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
                    QPushButton { 
                        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #d97706);
                        color: white; 
                        font-weight: bold; 
                        border-radius: 6px;
                        border: 1px solid #b45309;
                    }
                """)
                # Start the pulse animation
                if hasattr(self, 'pulse_anim'):
                    self.pulse_anim.start()
            
            if is_sso:
                import webbrowser
                
                # Connect to SSO URL detection
                def on_url_found(sso_url):
                    webbrowser.open(sso_url)
                    # We don't need a dialog, the button already says "Connecting..."
                
                def on_finished(code, status):
                    # Refresh status once the process finishes/browser login is done
                    self.ts_manager.check_status()
                
                # Disconnect old connections to avoid duplicates (silently)
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
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
