# src/ui/main_window.py

from PySide6.QtWidgets import QSystemTrayIcon
import sys
import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenu, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer, Qt, QEvent
from PySide6.QtGui import QAction, QActionGroup
from .components.log_viewer_dlg import LogViewerDialog
from .dashboard import DashboardView
from ..core.tailscale import get_tailscale_path


class MainWindow(QMainWindow):
    def __init__(self, manager, ts_manager):
        super().__init__()
        self.manager = manager
        self.ts_manager = ts_manager
        self.ts_manager.setParent(self)
        
        # 1. Load your UI file
        loader = QUiLoader()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ui_path = os.path.join(base_dir, "pygui", "windows", "main_window.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.ui_window = loader.load(ui_file) # This is the QMainWindow from your UI
        ui_file.close()
        
        # 2. Steal the central widget from the loaded UI
        self.setCentralWidget(self.ui_window.findChild(QWidget, "centralwidget"))
        
        # 3. Create Menu Bar in Code (Full Control)
        self._create_menu_bar()
            
        self.tabWidget = self.findChild(QTabWidget, "tabWidget")
        self.setWindowTitle("Tailscale Client Pro")
        self.setFixedSize(420, 280)

        self.current_theme = "light" # Default is LIGHT
        self.change_theme("light")

        # 4. Initialize tabs
        self.refresh_tabs()

        # 5. Connect to status changes for disabling actions
        self.ts_manager.connection_status_changed.connect(self._update_profile_actions_state)
        self.ts_manager.worker.error_received.connect(self._show_worker_error)
        # Initial check
        self._update_profile_actions_state(*self.ts_manager.check_status())
        
        # 6. Setup System Tray
        self._setup_tray()

        # 7. Auto-connect if no dialog is showing
        if self.manager.profiles:
            QTimer.singleShot(1000, self.auto_connect_if_enabled)
        else:
            QTimer.singleShot(500, self.ensure_initial_profile)
            
        # 8. Setup Periodic DB Flush (Every 5 minutes)
        self.flush_timer = QTimer(self)
        self.flush_timer.timeout.connect(self.manager.db.flush_buffer)
        self.flush_timer.start(300000) # 300,000 ms = 5 mins

        # 9. Startup Animation (Fade In)
        from PySide6.QtCore import QPropertyAnimation
        self.setWindowOpacity(0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(500) # 500ms
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()
        
        # 10. Asynchronous Service Check
        QTimer.singleShot(100, self.check_daemon_async)

        # 11. Centralized Traffic Polling (Every 3 seconds, only active tab)
        self.central_polling_timer = QTimer(self)
        self.central_polling_timer.timeout.connect(self._poll_active_tab)
        self.central_polling_timer.start(3000)

    def _setup_tray(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        from PySide6.QtGui import QIcon
        
        self.tray_icon = QSystemTrayIcon(self)
        # Try to find icon.png in the project root or assets
        icon_path = os.path.join(os.getcwd(), "icon.png")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
        
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback to a standard icon
            from PySide6.QtWidgets import QStyle
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.showNormal)
        show_action.triggered.connect(self.activateWindow)
        
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Exit")
        quit_action.triggered.connect(self._force_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_icon_activated)
        self.tray_icon.show()

    def check_daemon_async(self):
        from PySide6.QtCore import QProcess
        self.daemon_check_proc = QProcess(self)
        
        def on_check_finished():
            output = self.daemon_check_proc.readAllStandardError().data().decode().lower() + \
                     self.daemon_check_proc.readAllStandardOutput().data().decode().lower()
            is_running = not ("failed to connect" in output or "tailscaled may not be running" in output or self.daemon_check_proc.exitCode() != 0)
            if not is_running:
                self.show_service_wait_dialog()
                
        self.daemon_check_proc.finished.connect(on_check_finished)
        self.daemon_check_proc.start(get_tailscale_path(), ["status", "--json"])

    def show_service_wait_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
        from PySide6.QtCore import Qt, QTimer
        
        self.ts_manager.start_service()
        
        wait_dialog = QDialog(self)
        wait_dialog.setWindowTitle("Starting Service")
        wait_dialog.setStyleSheet("QDialog { background-color: #1a1e2e; color: white; } QLabel { color: white; font-weight: bold; }")
        wait_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        wait_dialog.setFixedSize(320, 120)
        
        layout = QVBoxLayout(wait_dialog)
        label = QLabel("Waiting for Tailscale Service...")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(False)
        layout.addWidget(progress)
        
        self.wait_dialog = wait_dialog
        import time
        self.wait_start_time = time.time()
        
        self.wait_timer = QTimer(self)
        self.wait_timer.timeout.connect(self._poll_daemon_status)
        self.wait_timer.start(1000)
        
        wait_dialog.exec()

    def _poll_daemon_status(self):
        from PySide6.QtCore import QProcess
        import time
        self.poll_proc = QProcess(self)
        
        def on_poll_finished():
            output = self.poll_proc.readAllStandardError().data().decode().lower() + \
                     self.poll_proc.readAllStandardOutput().data().decode().lower()
            is_running = not ("failed to connect" in output or "tailscaled may not be running" in output or self.poll_proc.exitCode() != 0)
            if is_running or (time.time() - self.wait_start_time > 60):
                self.wait_timer.stop()
                self.wait_dialog.close()
                self.refresh_tabs()
                
        self.poll_proc.finished.connect(on_poll_finished)
        self.poll_proc.start(get_tailscale_path(), ["status", "--json"])

    def _tray_icon_activated(self, reason):
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def _force_quit(self):
        # Synchronous check for 100% accuracy before exit
        is_connected, _ = self.ts_manager.check_status_sync()
        if is_connected:
            reply = QMessageBox.warning(
                self, 'Active Connection',
                "VPN is still connected. Do you want to logout and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            
            # Use synchronous logout to ensure it finishes before the app exits
            self.ts_manager.logout_sync()
        
        # Clean up lock file is handled in main.py, so we just exit
        self.ts_manager.cleanup()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        # Match strict legacy logic (gui/gui_main.py:447-450)
        # Use sync check to avoid async lag during window closure
        is_connected, _ = self.ts_manager.check_status_sync()
        if is_connected:
            QMessageBox.warning(
                self, 
                "WARNING !", 
                "Please logout from all connections first."
            )
            event.ignore()
            return

        # Cleanup empty profile directories
        for name in self.manager.profiles.keys():
            profile_dir = self.manager._get_tab_dir(name)
            if os.path.exists(profile_dir) and not os.listdir(profile_dir):
                try: os.rmdir(profile_dir)
                except: pass
                
        # Final flush of traffic data before exit to prevent data loss
        if hasattr(self.manager, 'db'):
            self.manager.db.flush_buffer()
            
        self.ts_manager.cleanup()
        event.accept()

    def changeEvent(self, event):
        # Match legacy logic: Hide to tray on minimize (gui/gui_main.py:171-172)
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide()
                self.tray_icon.showMessage(
                    "Tailscale Client Pro",
                    "Application minimized to tray.",
                    QSystemTrayIcon.Information,
                    2000
                )
        super().changeEvent(event)

    def _on_tab_changed(self, index):
        if index >= 0:
            name = self.tabWidget.tabText(index)
            if name != "Default":
                self.manager.settings.last_profile = name
                self.manager.save_settings()

    def auto_connect_if_enabled(self):
        if self.manager.settings.auto_connect:
            last_name = self.manager.settings.last_profile
            target_idx = 0
            
            if last_name:
                for i in range(self.tabWidget.count()):
                    if self.tabWidget.tabText(i) == last_name:
                        target_idx = i
                        break
            
            if self.tabWidget.count() > target_idx:
                self.tabWidget.setCurrentIndex(target_idx)
                view = self.tabWidget.widget(target_idx)
                if hasattr(view, "toggle_connection"):
                    if not self.ts_manager.check_status()[0]:
                        view.toggle_connection()

    def ensure_initial_profile(self):
        if not self.manager.profiles:
            success = self.add_profile_clicked()
            if not success and not self.manager.profiles:
                # Ask for confirmation before closing
                reply = QMessageBox.warning(
                    self, 'Profile Required',
                    "A profile is mandatory to use this application.\n\nWithout creating a profile, you cannot continue. Are you sure you want to close?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    sys.exit(0)
                else:
                    # Try again
                    self.ensure_initial_profile()

    def _create_menu_bar(self):
        
        menubar = self.menuBar()
        
        # --- File Menu ---
        file_menu = menubar.addMenu("&File")


        self.actionExit = QAction("&Exit", self)
        self.actionExit.triggered.connect(self._force_quit)
        file_menu.addAction(self.actionExit)
        
        self.actionSettings = QAction("&Settings", self)
        self.actionSettings.triggered.connect(self.show_settings)
        file_menu.addAction(self.actionSettings)
        
        # --- Profile Menu ---
        profile_menu = menubar.addMenu("&Profile")


        self.actionAddProfile = QAction("&Add New Profile", self)
        self.actionAddProfile.triggered.connect(self.add_profile_clicked)
        profile_menu.addAction(self.actionAddProfile)
        
        self.actionRemoveProfile = QAction("&Remove Current Profile", self)
        self.actionRemoveProfile.triggered.connect(self.remove_profile_clicked)
        profile_menu.addAction(self.actionRemoveProfile)
        
        # --- Theme Menu ---
        theme_menu = menubar.addMenu("&Theme")


        self.theme_group = QActionGroup(self)
        
        self.actionSystemTheme = QAction("&System Default", self)
        self.actionSystemTheme.setCheckable(True)
        self.actionSystemTheme.triggered.connect(lambda: self.change_theme("system"))
        self.theme_group.addAction(self.actionSystemTheme)
        theme_menu.addAction(self.actionSystemTheme)
        
        self.actionLightTheme = QAction("&Light Theme", self)
        self.actionLightTheme.setCheckable(True)
        self.actionLightTheme.triggered.connect(lambda: self.change_theme("light"))
        self.theme_group.addAction(self.actionLightTheme)
        theme_menu.addAction(self.actionLightTheme)
        
        self.actionDarkTheme = QAction("&Dark Theme", self)
        self.actionDarkTheme.setCheckable(True)
        self.actionDarkTheme.triggered.connect(lambda: self.change_theme("dark"))
        self.theme_group.addAction(self.actionDarkTheme)
        theme_menu.addAction(self.actionDarkTheme)
        
        self.actionVibrantTheme = QAction("&Vibrant Pro Theme", self)
        self.actionVibrantTheme.setCheckable(True)
        self.actionVibrantTheme.triggered.connect(lambda: self.change_theme("vibrant"))
        self.theme_group.addAction(self.actionVibrantTheme)
        theme_menu.addAction(self.actionVibrantTheme)
        
        # Set initial check
        self.actionLightTheme.setChecked(True)
        
        # --- Logs Menu ---
        logs_menu = menubar.addMenu("&Logs")
        self.menuGlobalLogs = logs_menu.addMenu("&Global Logs")

        self.menuGlobalLogs.aboutToShow.connect(self.populate_logs_menu)
        
        # --- Advanced Menu ---
        self.advanced_menu = menubar.addMenu("&Advanced")
        self.actionAdvanced = QAction("&Advanced Options...", self)
        self.actionAdvanced.triggered.connect(self.show_advanced_dialog)
        self.advanced_menu.addAction(self.actionAdvanced)
        
        self.actionPeerList = QAction("&Peer List...", self)
        self.actionPeerList.triggered.connect(self.show_peer_list)
        self.advanced_menu.addAction(self.actionPeerList)
        
        self.update_advanced_menu_state()
        
        # --- Help Menu ---
        help_menu = menubar.addMenu("&Help")
        
        self.actionAbout = QAction("&About Us", self)
        self.actionAbout.triggered.connect(self.show_about)
        help_menu.addAction(self.actionAbout)
        
        self.actionLicense = QAction("View &License", self)
        self.actionLicense.triggered.connect(self.show_license)
        help_menu.addAction(self.actionLicense)
        
        self.actionReadme = QAction("&Readme", self)
        self.actionReadme.triggered.connect(self.show_readme)
        help_menu.addAction(self.actionReadme)

    def populate_logs_menu(self):

        
        if not self.menuGlobalLogs:
            # Try finding it again recursively if it was missed
            self.menuGlobalLogs = self.ui_window.findChild(QMenu, "menuGlobalLogs")
            
        if not self.menuGlobalLogs:
            return

        self.menuGlobalLogs.clear()
        
        # Determine log directory (sync with main.py logic)
        app_dir = self.manager.base_dir
        
        if not os.path.exists(app_dir):
            self.menuGlobalLogs.addAction("No logs found").setEnabled(False)
            return
            
        # 1. Main logs directly in app_dir
        log_files = [(f, os.path.join(app_dir, f)) for f in os.listdir(app_dir) if f.endswith(".log")]
        
        # 2. Connection logs in GlobalLogs/
        global_logs_dir = os.path.join(app_dir, "GlobalLogs")
        if os.path.exists(global_logs_dir):
            conn_logs = [(f"Profile: {f.replace('_connection.log', '')}", os.path.join(global_logs_dir, f)) 
                         for f in os.listdir(global_logs_dir) if f.endswith(".log")]
            log_files.extend(conn_logs)
            
        if not log_files:
            self.menuGlobalLogs.addAction("No .log files found").setEnabled(False)
            return
            
        for display_name, full_path in sorted(log_files, key=lambda x: x[0]):
            action = QAction(display_name, self)
            action.triggered.connect(lambda checked, p=full_path, n=display_name: LogViewerDialog(p, n, self).show())
            self.menuGlobalLogs.addAction(action)

    def _poll_active_tab(self):
        if hasattr(self, 'tabWidget') and self.tabWidget:
            active_widget = self.tabWidget.currentWidget()
            if active_widget and hasattr(active_widget, "_update_traffic_label"):
                active_widget._update_traffic_label()

    def _show_worker_error(self, message):
        """Displays an interactive premium Dependency Wizard if Tailscale is missing."""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Tailscale Dependency Required")
        msg_box.setText(f"{message}\n\nTailscale is required to run this VPN client.")
        msg_box.setInformativeText("Would you like to open the official Tailscale download page now?")
        
        download_btn = msg_box.addButton("Download Tailscale", QMessageBox.AcceptRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == download_btn:
            QDesktopServices.openUrl(QUrl("https://tailscale.com/download"))

    def _update_profile_actions_state(self, is_connected, status_text):
        """Enable/disable profile actions based on connection status."""
        can_edit = not is_connected
        if hasattr(self, 'actionAddProfile'):
            self.actionAddProfile.setEnabled(can_edit)
        if hasattr(self, 'actionRemoveProfile'):
            self.actionRemoveProfile.setEnabled(can_edit)
        if hasattr(self, 'profiles_view'):
            self.profiles_view.set_edit_enabled(can_edit)

        # Smart Tab Locking Matrix based on active Native Switch state
        if self.tabWidget:
            current_idx = self.tabWidget.currentIndex()
            if current_idx >= 0:
                current_name = self.tabWidget.tabText(current_idx)
                current_profile = self.manager.profiles.get(current_name)
                
                if is_connected and current_profile and current_profile.is_native_switch and self.manager.settings.advanced_features:
                    for idx in range(self.tabWidget.count()):
                        p_name = self.tabWidget.tabText(idx)
                        profile = self.manager.profiles.get(p_name)
                        if profile:
                            self.tabWidget.setTabEnabled(idx, profile.is_native_switch)
                else:
                    # Disconnected or not a native switch - enable all tabs
                    for idx in range(self.tabWidget.count()):
                        self.tabWidget.setTabEnabled(idx, True)

    def change_theme(self, theme_name):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QGuiApplication, Qt, QColor
        
        self.current_theme = theme_name
        
        target_theme = theme_name
        if theme_name == "system":
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "colorScheme"):
                scheme = hints.colorScheme()
                target_theme = "dark" if scheme == Qt.ColorScheme.Dark else "light"
            else:
                target_theme = "light"
        
        self.resolved_theme = target_theme
        
        # 1. DO NOT touch QApplication stylesheet or MainWindow Palette
        # This keeps the Menu Bar 100% Native.

        # 2. Determine Local Styles dynamically from QSS files
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        qss_path = os.path.join(base_dir, "assets", "themes", f"{target_theme}.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                style = f.read()
        except Exception:
            style = ""
            
        # 3. Apply style ONLY to the TabWidget
        if self.tabWidget:
            self.tabWidget.setObjectName("tabWidget")
            self.tabWidget.setStyleSheet(style)
        
        self.current_qss = style
        
        # 4. Instantly refresh tab buttons to reflect the new theme
        if self.tabWidget:
            for i in range(self.tabWidget.count()):
                widget = self.tabWidget.widget(i)
                if widget and hasattr(widget, "update_status"):
                    widget.update_status(*self.ts_manager.check_status())

    def _apply_theme_to_dialog(self, dialog):
        if hasattr(self, 'current_qss'):
            dialog_style = self.current_qss.replace("#tabWidget ", "")
            if self.resolved_theme == "dark":
                bg = "#1a1e2e"
                text_color = "#d1d5db"
            elif self.resolved_theme == "vibrant":
                bg = "#04060d"
                text_color = "#f8fafc"
            else:
                bg = "#f0f0f0"
                text_color = "#1a1a1a"
            dialog_style = f"QDialog {{ background-color: {bg}; color: {text_color}; }} " + dialog_style
            dialog.setStyleSheet(dialog_style)





    def show_about(self):
        from .components.simple_dialogs import AboutDialog
        dlg = AboutDialog(self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def show_settings(self):
        from .components.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.manager, self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def show_peer_list(self):
        from .components.peer_dialog import PeerListDialog
        dlg = PeerListDialog(self.ts_manager, self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def show_license(self):
        from .components.simple_dialogs import LicenseDialog
        dlg = LicenseDialog(self.resolved_theme, self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def show_readme(self):
        from .components.simple_dialogs import ReadmeDialog
        dlg = ReadmeDialog(self.resolved_theme, self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()


    def add_profile_clicked(self):
        # Enforce max tabs limit
        if len(self.manager.profiles) >= self.manager.settings.max_tabs:
            QMessageBox.warning(self, "Limit Reached", 
                              f"You have reached the maximum limit of {self.manager.settings.max_tabs} profiles.\n"
                              "You can increase this limit in File -> Settings.")
            return False

        # 1. First Step: Get Profile Name using profile.ui
        from .components.profile_name_dialog import ProfileNameDialog
        
        name_dialog = ProfileNameDialog(self)
        self._apply_theme_to_dialog(name_dialog)
        
        if name_dialog.exec():
            profile_name = name_dialog.get_name()
            if not profile_name:
                QMessageBox.warning(self, "Error", "Profile name cannot be empty.")
                return False
            
            if profile_name in self.manager.profiles:
                QMessageBox.warning(self, "Error", "Profile name already exists.")
                return False

            # Create profile with default values - user can change credentials later
            from ..core.models import Profile
            new_profile = Profile(name=profile_name)
            
            self.manager.add_profile(new_profile)
            self.refresh_tabs()
            return True
        return False


    def remove_profile_clicked(self):
        if not self.tabWidget: return
        index = self.tabWidget.currentIndex()
        if index >= 0:
            name = self.tabWidget.tabText(index)
            
            # Verification
            reply = QMessageBox.question(
                self, 'Confirm Deletion',
                f"Are you sure you want to delete the profile '{name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.manager.remove_profile(name)
                self.refresh_tabs()

    def refresh_tabs(self):
        if not self.tabWidget:
            # Try to find it again just in case
            self.tabWidget = self.findChild(QTabWidget, "tabWidget")
            
        if not self.tabWidget: return
        
        # 1. Clear all tabs
        while self.tabWidget.count() > 0:
            self.tabWidget.removeTab(0)
            
        # 2. Add Profile tabs (Sort by is_native_switch so they group together at the front)
        sorted_profiles = sorted(
            self.manager.profiles.items(),
            key=lambda x: x[1].is_native_switch,
            reverse=True
        )
        
        for name, profile in sorted_profiles:
            view = DashboardView(self.manager, self.ts_manager, profile)
            self.tabWidget.addTab(view, name)
        
        if not self.manager.profiles:
            view = DashboardView(self.manager, self.ts_manager)
            self.tabWidget.addTab(view, "Default")
        
        # 3. Restore connection status disabling
        self._update_profile_actions_state(*self.ts_manager.check_status())
        
        # 4. Connect tab change signal to track last profile
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            try:
                self.tabWidget.currentChanged.disconnect(self._on_tab_changed)
            except:
                pass
        self.tabWidget.currentChanged.connect(self._on_tab_changed)

    def update_advanced_menu_state(self):
        """Enable or disable the Advanced Options menu based on app settings."""
        if hasattr(self, 'advanced_menu') and self.advanced_menu is not None:
            self.advanced_menu.setEnabled(self.manager.settings.advanced_features)

    def show_advanced_dialog(self):
        """Open the advanced options dialog for the active tab's profile."""
        current_idx = self.tabWidget.currentIndex()
        if current_idx < 0:
            QMessageBox.warning(self, "No Active Profile", "Please create or select a profile first.")
            return
            
        profile_name = self.tabWidget.tabText(current_idx)
        profile = self.manager.profiles.get(profile_name)
        
        if not profile:
            QMessageBox.warning(self, "No Active Profile", "Please create or select a profile first.")
            return
            
        from .components.node_dialog import NodeDialog
        dlg = NodeDialog(profile, self.manager, self)
        dlg.exec()
