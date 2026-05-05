# src/ui/main_window.py

import sys
import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenu
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtGui import QAction
from .components.log_viewer_dlg import LogViewerDialog
from .dashboard import DashboardView
from PySide6.QtGui import QAction, QActionGroup


class MainWindow(QMainWindow):
    def __init__(self, manager, ts_manager):
        super().__init__()
        self.manager = manager
        self.ts_manager = ts_manager
        
        # 1. Load your UI file
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "windows", "main_window.ui")
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
        self.setMinimumSize(self.ui_window.minimumSize())
        self.setMaximumSize(self.ui_window.maximumSize())
        self.resize(self.ui_window.size())

        self.current_theme = "light" # Default is LIGHT
        self.change_theme("light")

        # 4. Initialize tabs
        self.refresh_tabs()

    def _create_menu_bar(self):
        
        menubar = self.menuBar()
        
        # --- File Menu ---
        file_menu = menubar.addMenu("&File")


        self.actionExit = QAction("&Exit", self)
        self.actionExit.triggered.connect(self.close)
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
        
        # Set initial check
        self.actionLightTheme.setChecked(True)
        
        # --- Logs Menu ---
        logs_menu = menubar.addMenu("&Logs")
        self.menuGlobalLogs = logs_menu.addMenu("&Global Logs")

        self.menuGlobalLogs.aboutToShow.connect(self.populate_logs_menu)
        
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
        
        # Determine log directory (sync with pyside_launcher.py logic)
        if sys.platform == "win32":
            app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client_Pro")
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client_Pro")
        
        print(f"DEBUG: Scanning log directory: {app_dir}")
        
        if not os.path.exists(app_dir):
            print("DEBUG: Log directory does not exist.")
            self.menuGlobalLogs.addAction("No logs found").setEnabled(False)
            return
            
        log_files = [f for f in os.listdir(app_dir) if f.endswith(".log")]
        print(f"DEBUG: Found log files: {log_files}")
        
        if not log_files:
            self.menuGlobalLogs.addAction("No .log files found").setEnabled(False)
            return
            
        for lf in sorted(log_files):
            action = QAction(lf, self)
            full_path = os.path.join(app_dir, lf)
            # Use a default argument in lambda to capture the current path
            action.triggered.connect(lambda checked, p=full_path, n=lf: LogViewerDialog(p, n, self).show())
            self.menuGlobalLogs.addAction(action)

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

        # 2. Determine Local Styles
        if target_theme == "dark":
            style = """
                QTabWidget#tabWidget { background-color: #1a1e2e; }
                #tabWidget QTabWidget::pane { border: 1px solid #3d4b7c; background-color: #1a1e2e; top: -1px; }
                
                /* Force background for the content area widgets */
                #tabWidget QWidget { background-color: #1a1e2e; }
                
                #tabWidget QTabBar::tab { background-color: #1e243a; color: #9ca3af; padding: 10px 20px; border: 1px solid #3d4b7c; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-size: 11px; font-weight: 600; }
                #tabWidget QTabBar::tab:hover { background-color: #2a324b; color: #ffffff; }
                #tabWidget QTabBar::tab:selected { background-color: #1a1e2e; color: #3b82f6; border-bottom: 2px solid #3b82f6; font-weight: bold; }
                
                #tabWidget QLineEdit, #tabWidget QTextEdit, #tabWidget QPlainTextEdit, #tabWidget QSpinBox { background-color: #0f111a; color: #ffffff; border: 1px solid #3d4b7c; padding: 8px; border-radius: 4px; selection-background-color: #3b82f6; }
                #tabWidget QLineEdit:focus { border: 1px solid #3b82f6; background-color: #161b22; }
                
                #tabWidget QPushButton { background-color: #1e243a; color: #ffffff; border: 1px solid #3d4b7c; padding: 8px 20px; border-radius: 6px; font-weight: 600; }
                #tabWidget QPushButton:hover { background-color: #2a324b; border-color: #3b82f6; }
                #tabWidget QPushButton:pressed { background-color: #0f111a; }
                
                #tabWidget QLabel { color: #e5e7eb; background-color: transparent; font-weight: 500; }
                #tabWidget QCheckBox, #tabWidget QRadioButton, #tabWidget QGroupBox { color: #d1d5db; background-color: transparent; font-weight: 500; }
                
                #tabWidget QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #3d4b7c; border-radius: 4px; background-color: #0f111a; }
                #tabWidget QCheckBox::indicator:checked { background-color: #3b82f6; border-color: #3b82f6; }
            """
        else:
            style = """
                #tabWidget QTabWidget::pane { border: 1px solid #d0d0d0; background-color: #f8f9fa; top: -1px; }
                #tabWidget QTabBar::tab { background-color: #e9ecef; color: #495057; padding: 10px 20px; border: 1px solid #dee2e6; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; font-size: 11px; font-weight: 600; }
                #tabWidget QTabBar::tab:hover { background-color: #f8f9fa; }
                #tabWidget QTabBar::tab:selected { background-color: #f8f9fa; color: #0056b3; border-bottom: 2px solid #0056b3; font-weight: bold; }
                
                #tabWidget QLineEdit, #tabWidget QTextEdit, #tabWidget QPlainTextEdit, #tabWidget QSpinBox { background-color: #ffffff; color: #212529; border: 1px solid #ced4da; padding: 8px; border-radius: 4px; }
                #tabWidget QLineEdit:focus { border: 1px solid #80bdff; outline: 0; }
                
                #tabWidget QPushButton { background-color: #f8f9fa; color: #212529; border: 1px solid #ced4da; padding: 8px 20px; border-radius: 6px; font-weight: 600; }
                #tabWidget QPushButton:hover { background-color: #e2e6ea; border-color: #0056b3; }
                
                #tabWidget QLabel, #tabWidget QCheckBox, #tabWidget QRadioButton, #tabWidget QGroupBox { color: #212529; background-color: transparent; }
            """
            
        # 3. Apply style ONLY to the TabWidget
        if self.tabWidget:
            self.tabWidget.setObjectName("tabWidget")
            self.tabWidget.setStyleSheet(style)
        
        self.current_qss = style

    def _apply_theme_to_dialog(self, dialog):
        if hasattr(self, 'current_qss'):
            dialog_style = self.current_qss.replace("#tabWidget ", "")
            bg = "#1a1e2e" if self.resolved_theme == "dark" else "#f0f0f0"
            dialog_style = f"QDialog {{ background-color: {bg}; color: {'#d1d5db' if self.resolved_theme == 'dark' else '#1a1a1a'}; }} " + dialog_style
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
        from .components.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self)
        dialog.setWindowTitle("Add New VPN Profile")
        self._apply_theme_to_dialog(dialog)
        if dialog.exec():
            data = dialog.get_data()
            if not data or not data["name"]: return
            from ..core.models import Profile
            
            # Map 'sso' to 'google' if that's what the thinker app expected
            auth_mode = "google" if data["auth_mode"] == "sso" else data["auth_mode"]
            data["auth_mode"] = auth_mode
            
            new_profile = Profile(name=data["name"], **data)
            self.manager.add_profile(new_profile)
            self.refresh_tabs()


    def remove_profile_clicked(self):
        if not self.tabWidget: return
        index = self.tabWidget.currentIndex()
        if index >= 0:
            name = self.tabWidget.tabText(index)
            self.manager.remove_profile(name)
            self.refresh_tabs()

    def refresh_tabs(self):
        if not self.tabWidget:
            # Try to find it again just in case
            self.tabWidget = self.findChild(QTabWidget, "tabWidget")
            
        if not self.tabWidget: return
        
        while self.tabWidget.count() > 0:
            self.tabWidget.removeTab(0)
            
        for name, profile in self.manager.profiles.items():
            view = DashboardView(self.manager, self.ts_manager, profile)
            self.tabWidget.addTab(view, name)
        
        if not self.manager.profiles:
            view = DashboardView(self.manager, self.ts_manager)
            self.tabWidget.addTab(view, "Default")
