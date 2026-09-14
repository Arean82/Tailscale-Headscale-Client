# src/ui/main_window.py

import os
import sys

from PySide6.QtCore import QEvent, QFile, QTimer
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QTabWidget,
    QWidget,
)

from ..core.tailscale import get_tailscale_path
from .components.log_viewer_dlg import LogViewerDialog
from .dashboard import DashboardView


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
        if self.tabWidget:
            self.tabWidget.setAccessibleName("VPN Profiles Navigation Tabs")
            self.tabWidget.setAccessibleDescription("Switch between configured Headscale and Tailscale network profiles.")
        self.setWindowTitle("Tailscale Client Pro")
        self.setAccessibleName("Tailscale Client Pro Main Window")
        self.setAccessibleDescription("Main application window for managing Tailscale and Headscale VPN connections.")
        self.setFixedSize(420, 280)

        self.current_theme = "light" # Default is LIGHT
        self.change_theme("light")
        self.last_status_text = None

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
        
        # 10b. Optional Screen Reader / AT Check on Startup (if enabled by operator)
        if getattr(self.manager.settings, 'check_screen_reader', False):
            QTimer.singleShot(1500, self._check_screen_reader_on_startup)

        # 11. Centralized Traffic Polling (Every 3 seconds, only active tab)
        self.central_polling_timer = QTimer(self)
        self.central_polling_timer.timeout.connect(self._poll_active_tab)
        self.central_polling_timer.start(3000)

    def _setup_tray(self):
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QSystemTrayIcon
        
        self.tray_icon = QSystemTrayIcon(self)
        
        # 1. Try to load from persistent APPDATA first (extremely robust for Windows Startup/Auto-start)
        icon_path = os.path.join(self.manager.base_dir, "icon.png")
        
        # 2. If not found, fallback to PyInstaller runtime temp or development folder
        if not os.path.exists(icon_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "assets", "icon.png")
            else:
                icon_path = os.path.join(base_dir, "assets", "icon.png")

            if not os.path.exists(icon_path):
                icon_path = os.path.join(base_dir, "icon.png")
                
        # 3. Final safety fallbacks (Current Working Directory)
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.getcwd(), "icon.png")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(os.getcwd(), "assets", "icon.png")
        
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback to standard style icon
            from PySide6.QtWidgets import QStyle
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        self.tray_menu = QMenu(self)
        self.tray_menu.aboutToShow.connect(self.update_tray_menu)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._tray_icon_activated)
        self.tray_icon.show()
        
        # 4. Safe retry mechanism for Windows Startup (Explorer race condition)
        # Sometimes, Windows launches startup apps before the Explorer Taskbar/System Tray is ready.
        if sys.platform == "win32":
            def safe_retry_show():
                if hasattr(self, 'tray_icon') and self.tray_icon and not self.tray_icon.isVisible():
                    self.tray_icon.show()
            QTimer.singleShot(5000, safe_retry_show)

    def check_daemon_async(self, retry_count=0):
        from PySide6.QtCore import QTimer

        from src.utils.local_api import is_local_api_available
        
        is_running = is_local_api_available()
        if is_running:
            # Successfully running! No dialog needed.
            return
            
        # If not running, let's retry in the background dynamically (every 2 seconds)
        # based on the custom "Startup Daemon Wait" setting (minimum of 5 retries / 10s)
        max_retries = max(5, self.manager.settings.startup_delay // 2)
        if retry_count < max_retries:
            QTimer.singleShot(2000, lambda: self.check_daemon_async(retry_count + 1))
        else:
            # Still not running after retries, show the wait/start dialog
            self.show_service_wait_dialog()

    def show_service_wait_dialog(self):
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout
        
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
        if hasattr(self, 'poll_proc') and self.poll_proc is not None:
            return

        import time

        from PySide6.QtCore import QProcess
        self.poll_proc = QProcess(self)
        
        def on_poll_finished():
            is_running = False
            if self.poll_proc:
                try:
                    output = self.poll_proc.readAllStandardError().data().decode(errors="ignore").lower() + \
                             self.poll_proc.readAllStandardOutput().data().decode(errors="ignore").lower()
                    is_running = not ("failed to connect" in output or "tailscaled may not be running" in output or self.poll_proc.exitCode() != 0)
                except RuntimeError:
                    is_running = False
                finally:
                    self.poll_proc.deleteLater()
                    self.poll_proc = None
            
            if is_running or (time.time() - self.wait_start_time > 60):
                self.wait_timer.stop()
                if self.wait_dialog:
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

    def restart_app(self):
        """Soft-restart the GUI to apply translations without killing the VPN daemon."""
        self.is_restarting = True
        import sys

        from PySide6.QtCore import QProcess
        from PySide6.QtWidgets import QApplication

        # Manually release the single-instance lock right now so the new instance spawns instantly (0ms delay)
        import __main__
        if hasattr(__main__, 'lock_file'):
            __main__.lock_file.unlock()
            
        # Properly handle command line arguments for both PyInstaller and raw Python
        args = sys.argv[1:] if getattr(sys, 'frozen', False) else sys.argv
        QProcess.startDetached(sys.executable, args)
        
        # Close window and quit safely
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        # If we are soft-restarting the GUI, bypass the logout safety warnings completely
        # because the Tailscale daemon will continue running safely in the background.
        if getattr(self, 'is_restarting', False):
            if hasattr(self.manager, 'db'):
                self.manager.db.flush_buffer()
            self.ts_manager.cleanup()
            event.accept()
            return

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
        for name in self.manager.profiles:
            try:
                profile_dir = self.manager._get_tab_dir(name)
            except (PermissionError, ValueError):
                # Unsafe legacy profile name; skip cleanup for it
                continue
            if os.path.exists(profile_dir) and not os.listdir(profile_dir):
                try:
                    os.rmdir(profile_dir)
                except OSError:
                    # Ignore directory-not-empty or in-use errors on exit
                    continue
                
        # Final flush of traffic data before exit to prevent data loss
        if hasattr(self.manager, 'db'):
            self.manager.db.flush_buffer()
            
        self.ts_manager.cleanup()
        event.accept()

    def changeEvent(self, event):
        # Match legacy logic: Hide to tray on minimize (gui/gui_main.py:171-172)
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
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
            
            # Immediately refresh the active tab with cached status to avoid stale UI
            widget = self.tabWidget.widget(index)
            if widget and hasattr(widget, "update_status"):
                widget.update_status(*self.ts_manager.check_status())

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
                if hasattr(view, "toggle_connection") and not self.ts_manager.check_status()[0]:
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
        file_menu = menubar.addMenu(self.tr("&File"))

        self.actionSettings = QAction(self.tr("&Settings"), self)
        self.actionSettings.triggered.connect(self.show_settings)
        file_menu.addAction(self.actionSettings)
        
        self.actionExit = QAction(self.tr("&Exit"), self)
        self.actionExit.triggered.connect(self._force_quit)
        file_menu.addAction(self.actionExit)
        
        # --- Profile Menu ---
        profile_menu = menubar.addMenu(self.tr("&Profile"))


        self.actionAddProfile = QAction(self.tr("&Add New Profile"), self)
        self.actionAddProfile.triggered.connect(self.add_profile_clicked)
        profile_menu.addAction(self.actionAddProfile)

        self.actionRenameProfile = QAction(self.tr("Re&name Current Profile..."), self)
        self.actionRenameProfile.triggered.connect(self.rename_profile_clicked)
        profile_menu.addAction(self.actionRenameProfile)
        
        self.actionRemoveProfile = QAction(self.tr("&Remove Current Profile"), self)
        self.actionRemoveProfile.triggered.connect(self.remove_profile_clicked)
        profile_menu.addAction(self.actionRemoveProfile)
        
        # --- Theme Menu ---
        theme_menu = menubar.addMenu(self.tr("&Theme"))

        self.theme_mode_group = QActionGroup(self)
        
        self.actionLightTheme = QAction(self.tr("&Light Theme (Default)"), self)
        self.actionLightTheme.setCheckable(True)
        self.actionLightTheme.triggered.connect(lambda: self.set_theme_mode("light"))
        self.theme_mode_group.addAction(self.actionLightTheme)
        theme_menu.addAction(self.actionLightTheme)
        
        self.actionDarkTheme = QAction(self.tr("&Dark Theme"), self)
        self.actionDarkTheme.setCheckable(True)
        self.actionDarkTheme.triggered.connect(lambda: self.set_theme_mode("dark"))
        self.theme_mode_group.addAction(self.actionDarkTheme)
        theme_menu.addAction(self.actionDarkTheme)
        
        theme_menu.addSeparator()

        # Add Material Accent sub-menu (accents only; automatically applies light/dark based on mode)
        material_menu = theme_menu.addMenu(self.tr("&Material"))
        self.accent_group = QActionGroup(self)

        # Standard accent (resets to native client QSS)
        self.actionDefaultAccent = QAction(self.tr("Default Accent (Standard)"), self)
        self.actionDefaultAccent.setCheckable(True)
        self.actionDefaultAccent.setChecked(True)
        self.actionDefaultAccent.triggered.connect(lambda: self.set_material_accent(None))
        self.accent_group.addAction(self.actionDefaultAccent)
        material_menu.addAction(self.actionDefaultAccent)
        material_menu.addSeparator()

        # Distinct clean accents
        material_accents = [
            ("Amber", "amber"),
            ("Blue", "blue"),
            ("Cyan", "cyan"),
            ("Light Green", "lightgreen"),
            ("Orange", "orange"),
            ("Pink", "pink"),
            ("Purple", "purple"),
            ("Red", "red"),
            ("Teal", "teal"),
            ("Yellow", "yellow")
        ]

        self.accent_actions = {}
        import importlib.util
        if importlib.util.find_spec("qt_material") is not None:
            for label, key in material_accents:
                act = QAction(self.tr(label), self)
                act.setCheckable(True)
                act.triggered.connect(lambda checked=False, accent=key: self.set_material_accent(accent))
                self.accent_group.addAction(act)
                material_menu.addAction(act)
                self.accent_actions[key] = act
        else:
            act_unavail = QAction(self.tr("qt-material not installed"), self)
            act_unavail.setEnabled(False)
            material_menu.addAction(act_unavail)

        # Set initial check
        self.actionLightTheme.setChecked(True)
        self.current_theme_mode = "light"
        self.current_material_accent = None
        
        # --- Logs Menu ---
        logs_menu = menubar.addMenu(self.tr("&Logs"))
        self.menuGlobalLogs = logs_menu.addMenu(self.tr("&Global Logs"))

        self.menuGlobalLogs.aboutToShow.connect(self.populate_logs_menu)
        
        # --- Advanced Menu ---
        self.advanced_menu = menubar.addMenu(self.tr("&Advanced"))
        self.actionAdvanced = QAction(self.tr("&Advanced Options..."), self)
        self.actionAdvanced.triggered.connect(self.show_advanced_dialog)
        self.advanced_menu.addAction(self.actionAdvanced)
        
        self.actionPeerList = QAction(self.tr("&Peer List..."), self)
        self.actionPeerList.triggered.connect(self.show_peer_list)
        self.advanced_menu.addAction(self.actionPeerList)
        
        self.actionDiagnostics = QAction(self.tr("&Network Diagnostics..."), self)
        self.actionDiagnostics.triggered.connect(self.show_diagnostics)
        self.advanced_menu.addAction(self.actionDiagnostics)
        
        self.actionTraySwitcher = QAction(self.tr("Enable Quick &Exit-Node Switcher"), self)
        self.actionTraySwitcher.setCheckable(True)
        self.actionTraySwitcher.setChecked(self.manager.settings.enable_tray_switcher)
        self.actionTraySwitcher.triggered.connect(self.toggle_tray_switcher)
        self.advanced_menu.addAction(self.actionTraySwitcher)
        
        self.update_advanced_menu_state()
        
        # --- Help Menu ---
        help_menu = menubar.addMenu(self.tr("&Help"))
        
        self.actionAbout = QAction(self.tr("&About Us"), self)
        self.actionAbout.triggered.connect(self.show_about)
        help_menu.addAction(self.actionAbout)
        
        self.actionLicense = QAction(self.tr("View &License"), self)
        self.actionLicense.triggered.connect(self.show_license)
        help_menu.addAction(self.actionLicense)
        
        self.actionReadme = QAction(self.tr("&Readme"), self)
        self.actionReadme.triggered.connect(self.show_readme)
        help_menu.addAction(self.actionReadme)

        help_menu.addSeparator()

        self.actionCheckA11y = QAction(self.tr("Check &Screen Reader Setup..."), self)
        self.actionCheckA11y.setShortcut("Ctrl+Shift+S")
        self.actionCheckA11y.triggered.connect(self.check_screen_reader_interactive)
        help_menu.addAction(self.actionCheckA11y)

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
            self.menuGlobalLogs.addAction(self.tr("No logs found")).setEnabled(False)
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
            self.menuGlobalLogs.addAction(self.tr("No .log files found")).setEnabled(False)
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
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        
        # Only show the dependency download prompt if Tailscale is actually missing from the system!
        if "not installed" in message.lower() or "not found" in message.lower():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Tailscale Dependency Required")
            msg_box.setText(f"{message}\n\nTailscale is required to run this VPN client.")
            msg_box.setInformativeText("Would you like to open the official Tailscale download page now?")
            
            download_btn = msg_box.addButton("Download Tailscale", QMessageBox.AcceptRole)
            msg_box.addButton("Cancel", QMessageBox.RejectRole)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == download_btn:
                QDesktopServices.openUrl(QUrl("https://tailscale.com/download"))
        else:
            # For temporary connection failures, retry logs, or timeouts, show a standard connection warning dialog
            QMessageBox.warning(self, "Connection Warning", message)

    def _update_profile_actions_state(self, is_connected, status_text):
        """Enable/disable profile actions based on connection status."""
        # Trigger native desktop notification on state change
        if hasattr(self, 'last_status_text'):
            if self.last_status_text != status_text and self.last_status_text is not None and hasattr(self, 'tray_icon') and self.tray_icon:
                title = "Tailscale Connected" if is_connected else "Tailscale Status"
                icon = QSystemTrayIcon.Information if is_connected else QSystemTrayIcon.Warning if "Approval" in status_text else QSystemTrayIcon.Information
                self.tray_icon.showMessage(title, f"VPN tunnel status is now {status_text}.", icon, 3000)
            self.last_status_text = status_text

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

    def set_theme_mode(self, mode: str):
        """Sets base theme mode ('light' or 'dark'). Automatically updates Material accent if one is active."""
        self.current_theme_mode = mode
        if mode == "light":
            self.actionLightTheme.setChecked(True)
        else:
            self.actionDarkTheme.setChecked(True)

        if self.current_material_accent:
            self._apply_material_theme(self.current_theme_mode, self.current_material_accent)
        else:
            self.change_theme(mode)

    def set_material_accent(self, accent: str | None):
        """Applies a material accent using the current mode ('light' or 'dark'), or restores native QSS if accent is None."""
        self.current_material_accent = accent
        if not accent:
            self.actionDefaultAccent.setChecked(True)
            self.change_theme(self.current_theme_mode)
            return

        if accent in self.accent_actions:
            self.accent_actions[accent].setChecked(True)
        self._apply_material_theme(self.current_theme_mode, accent)

    def _apply_material_theme(self, mode: str, accent: str):
        """Applies dynamic material theme based on base mode ('light' or 'dark') and selected accent."""
        from PySide6.QtWidgets import QApplication
        from qt_material import apply_stylesheet

        xml_theme = f"{mode}_{accent}.xml"
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            apply_stylesheet(app, theme=xml_theme)
            self.current_qss = app.styleSheet()
        self.resolved_theme = mode

        if self.tabWidget:
            self.tabWidget.setStyleSheet("")
            for i in range(self.tabWidget.count()):
                widget = self.tabWidget.widget(i)
                if widget and hasattr(widget, "update_status"):
                    widget.update_status(*self.ts_manager.check_status())

    def change_theme(self, theme_name):
        from PySide6.QtWidgets import QApplication
        
        self.current_theme = theme_name
        target_theme = "dark" if theme_name == "dark" else "light"
        self.resolved_theme = target_theme
        
        # Reset application-level stylesheet in case we are switching away from qt_material
        app = QApplication.instance()
        app.setStyleSheet("")
        
        # Restore native palette and style
        import sys
        if sys.platform == "win32":
            app.setStyle("WindowsVista")
        app.setPalette(app.style().standardPalette())

        # Determine Local Styles dynamically from QSS files
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        qss_path = os.path.join(base_dir, "assets", "themes", f"{target_theme}.qss")
        try:
            with open(qss_path, encoding="utf-8") as f:
                style = f.read()
        except OSError:
            style = ""
            
        # Apply style ONLY to the TabWidget
        if self.tabWidget:
            self.tabWidget.setObjectName("tabWidget")
            self.tabWidget.setStyleSheet(style)
        
        self.current_qss = style
        
        # Instantly refresh tab buttons to reflect the new theme
        if self.tabWidget:
            for i in range(self.tabWidget.count()):
                widget = self.tabWidget.widget(i)
                if widget and hasattr(widget, "update_status"):
                    widget.update_status(*self.ts_manager.check_status())

    def _apply_theme_to_dialog(self, dialog):
        if not dialog:
            return
        # If a material accent is active, qt_material styles dialogs globally, but ensure explicit palette/colors
        if self.current_material_accent:
            bg = "#121212" if self.resolved_theme == "dark" else "#fafafa"
            text_color = "#ffffff" if self.resolved_theme == "dark" else "#212121"
            dialog.setStyleSheet(f"QDialog {{ background-color: {bg}; color: {text_color}; }}")
            return

        if hasattr(self, 'current_qss') and self.current_qss:
            dialog_style = self.current_qss.replace("#tabWidget ", "")
            if self.resolved_theme == "dark":
                bg = "#1a1e2e"
                text_color = "#d1d5db"
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

    def show_diagnostics(self):
        from .components.diagnostics_dialog import DiagnosticsDialog
        dlg = DiagnosticsDialog(self)
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

    def rename_profile_clicked(self):
        if not self.tabWidget:
            return
        index = self.tabWidget.currentIndex()
        if index < 0:
            return
        old_name = self.tabWidget.tabText(index)
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            self.tr("Rename Profile"),
            self.tr("Enter new profile name:"),
            text=old_name
        )
        if ok and new_name:
            new_name = new_name.strip()
            if not new_name:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Profile name cannot be empty."))
                return
            if new_name == old_name:
                return
            if new_name in self.manager.profiles:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Profile name already exists."))
                return
            if self.manager.rename_profile(old_name, new_name):
                self.refresh_tabs()
                # Select the renamed tab
                for i in range(self.tabWidget.count()):
                    if self.tabWidget.tabText(i) == new_name:
                        self.tabWidget.setCurrentIndex(i)
                        break
            else:
                QMessageBox.warning(self, self.tr("Error"), self.tr("Failed to rename profile."))

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
            except (RuntimeError, TypeError) as sig_err:
                warnings.warn(f"Tab currentChanged disconnect: {sig_err}", category=RuntimeWarning, stacklevel=2)
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
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def toggle_tray_switcher(self, checked):
        self.manager.settings.enable_tray_switcher = checked
        self.manager.save_settings()

    def update_tray_menu(self):
        if not hasattr(self, 'tray_menu') or self.tray_menu is None:
            return
            
        self.tray_menu.clear()
        
        show_action = self.tray_menu.addAction("Show")
        show_action.triggered.connect(self.showNormal)
        show_action.triggered.connect(self.activateWindow)
        
        self.tray_menu.addSeparator()
        
        if self.manager.settings.enable_tray_switcher and self.manager.settings.advanced_features:
            exit_menu = self.tray_menu.addMenu("Exit Node Routing")
            
            # Find discovered exit nodes
            status_cache = self.ts_manager.cache.get("status")
            raw_data = status_cache.get("raw_data") if status_cache else None
            exit_nodes = []
            active_exit_node_ip = None
            
            if raw_data:
                peers = raw_data.get("Peer", {}) or {}
                for peer in peers.values():
                    if peer.get("ExitNodeOption"):
                        name = peer.get("HostName") or peer.get("DNSName", "").split(".")[0]
                        ips = peer.get("TailscaleIPs", [""])
                        ip = ips[0] if ips else ""
                        is_active = peer.get("ExitNode", False)
                        if is_active:
                            active_exit_node_ip = ip
                        if ip:
                            exit_nodes.append((name, ip, is_active))
            
            # 1. None Option
            none_action = exit_menu.addAction("None (Direct Internet)")
            none_action.setCheckable(True)
            none_action.setChecked(active_exit_node_ip is None)
            none_action.triggered.connect(lambda: self.set_tray_exit_node(""))
            
            exit_menu.addSeparator()
            
            if exit_nodes:
                for name, ip, is_active in sorted(exit_nodes, key=lambda x: x[0]):
                    action = exit_menu.addAction(f"{name} ({ip})")
                    action.setCheckable(True)
                    action.setChecked(is_active)
                    action.triggered.connect(lambda checked, target_ip=ip: self.set_tray_exit_node(target_ip))
            else:
                exit_menu.addAction("No Exit Nodes Discovered").setEnabled(False)
                
            self.tray_menu.addSeparator()
            
        quit_action = self.tray_menu.addAction("Exit")
        quit_action.triggered.connect(self._force_quit)

    def set_tray_exit_node(self, ip):
        try:
            self.ts_manager.worker.run_command(["up", f"--exit-node={ip}"])
            self.ts_manager.check_status(force=True)
        except RuntimeError as e:
            print(f"[DEBUG Tray Switcher] Failed to set exit node: {e}")

    def _check_screen_reader_on_startup(self):
        from src.utils.a11y_checker import check_screen_reader_environment
        res = check_screen_reader_environment()
        if not res.is_healthy:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Screen Reader Setup Recommendation")
            msg.setText(f"<b>{res.title}</b><br><br>{res.summary}<br><br>{res.details}")
            if res.remediation_cmd:
                msg.setInformativeText(f"Run this command to install the required accessibility components:<br><br><code>{res.remediation_cmd}</code>")
                btn_copy = msg.addButton("Copy Command", QMessageBox.ActionRole)
                msg.addButton(QMessageBox.Close)
                msg.exec()
                if msg.clickedButton() == btn_copy:
                    from PySide6.QtGui import QGuiApplication
                    clipboard = QGuiApplication.clipboard()
                    clipboard.setText(res.remediation_cmd)
                    QMessageBox.information(self, "Copied", "Command copied to clipboard!")
            else:
                msg.setStandardButtons(QMessageBox.Close)
                msg.exec()

    def check_screen_reader_interactive(self):
        from src.utils.a11y_checker import check_screen_reader_environment
        res = check_screen_reader_environment()
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information if res.is_healthy else QMessageBox.Warning)
        msg.setWindowTitle("Screen Reader Environment Check")
        msg.setText(f"<b>{res.title}</b><br><br>{res.summary}<br><br>{res.details}")
        if res.remediation_cmd:
            msg.setInformativeText(f"Run this command to install or activate the required accessibility components:<br><br><code>{res.remediation_cmd}</code>")
            btn_copy = msg.addButton("Copy Command", QMessageBox.ActionRole)
            msg.addButton(QMessageBox.Close)
            msg.exec()
            if msg.clickedButton() == btn_copy:
                from PySide6.QtGui import QGuiApplication
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(res.remediation_cmd)
                QMessageBox.information(self, "Copied", "Command copied to clipboard!")
        else:
            msg.setStandardButtons(QMessageBox.Close)
            msg.exec()

