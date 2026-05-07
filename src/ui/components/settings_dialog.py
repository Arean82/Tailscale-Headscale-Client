# src/ui/components/settings_dialog.py

import os
from PySide6.QtWidgets import QDialog, QCheckBox, QPushButton, QLabel, QMessageBox, QSlider, QVBoxLayout, QHBoxLayout, QSpinBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt

from .simple_dialogs import BaseUiDialog

class SettingsDialog(BaseUiDialog):
    def __init__(self, manager, parent=None):
        super().__init__("settings.ui", parent)
        self.setFixedSize(340, 310)
        self.manager = manager
        
        # Access widgets through self.ui
        self.chkAutoConnect = self.ui.findChild(QCheckBox, "chkAutoConnect")
        self.chkEnableLogs = self.ui.findChild(QCheckBox, "chkEnableLogs")
        self.chkRunAtStartup = self.ui.findChild(QCheckBox, "chkRunAtStartup")
        self.chkAdvanced = self.ui.findChild(QCheckBox, "chkAdvanced")
        self.chkUseLocalAPI = self.ui.findChild(QCheckBox, "chkUseLocalAPI")
        self.labelLogPath = self.ui.findChild(QLabel, "labelLogPath")
        self.btnOpenLogFolder = self.ui.findChild(QPushButton, "btnOpenLogFolder")
        self.btnClose = self.ui.findChild(QPushButton, "btnClose")
        
        # Set initial values
        if self.chkAutoConnect:
            self.chkAutoConnect.setChecked(self.manager.settings.auto_connect)
            
        if self.chkEnableLogs:
            self.chkEnableLogs.setChecked(self.manager.settings.enable_logs)
            
        if self.chkRunAtStartup:
            self.chkRunAtStartup.setChecked(self.manager.settings.auto_start)

        if self.chkAdvanced:
            self.chkAdvanced.setChecked(self.manager.settings.advanced_features)
            
        if self.chkUseLocalAPI:
            self.chkUseLocalAPI.setChecked(self.manager.settings.use_local_api)
            
        if self.labelLogPath:
            from src.utils.logger import get_global_log_dir
            log_dir = get_global_log_dir(self.manager.base_dir)
            self.labelLogPath.setText(f"Path: {log_dir}")
            
        # Access SpinBox for max profile limit from UI
        self.spinMaxTabs = self.ui.findChild(QSpinBox, "spinMaxTabs")
        
        if self.spinMaxTabs:
            self.spinMaxTabs.setValue(self.manager.settings.max_tabs)
            self.spinMaxTabs.valueChanged.connect(self._on_max_tabs_changed)
            
        # Access SpinBox from UI
        self.spinSsoTimeout = self.ui.findChild(QSpinBox, "spinSsoTimeout")
        if self.spinSsoTimeout:
            self.spinSsoTimeout.setValue(self.manager.settings.sso_timeout)
            self.spinSsoTimeout.valueChanged.connect(self._on_sso_timeout_changed)
            
        # Connections
        if self.chkAutoConnect:
            self.chkAutoConnect.toggled.connect(self._on_auto_connect_toggled)
        if self.chkEnableLogs:
            self.chkEnableLogs.toggled.connect(self._save_settings)
        if self.chkRunAtStartup:
            self.chkRunAtStartup.toggled.connect(self._save_settings)
        if self.chkAdvanced:
            self.chkAdvanced.toggled.connect(self._save_settings)
        if self.chkUseLocalAPI:
            self.chkUseLocalAPI.toggled.connect(self._save_settings)
        if self.btnOpenLogFolder:
            self.btnOpenLogFolder.clicked.connect(self._open_log_folder)
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)
            self.btnClose.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #2ec866, stop:1 #1ca34d);
                    color: white;
                    border: 1px solid #198e43;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #34d96f, stop:1 #22b355);
                    border: 1px solid #1ca34d;
                }
                QPushButton:pressed {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #1a9645, stop:1 #147c38);
                    border: 1px solid #126b30;
                }
            """)

    def _on_sso_timeout_changed(self, value):
        self.manager.settings.sso_timeout = value
        self.manager.save_settings()
        if self.parent() and hasattr(self.parent(), "ts_manager"):
            self.parent().ts_manager.sso_timeout = value

    def _on_max_tabs_changed(self, value):
        self.manager.settings.max_tabs = value
        self.manager.save_settings()

    def _on_auto_connect_toggled(self, checked):
        if checked and self.chkRunAtStartup and not self.chkRunAtStartup.isChecked():
            # Temporarily disconnect the chkRunAtStartup signal to prevent redundant saves
            self.chkRunAtStartup.toggled.disconnect(self._save_settings)
            self.chkRunAtStartup.setChecked(True)
            self.chkRunAtStartup.toggled.connect(self._save_settings)
            
            QMessageBox.information(
                self, "Auto-Start Enabled",
                "Enabled 'Run at startup' automatically to allow auto-connection when your system starts!"
            )
        self._save_settings()

    def _save_settings(self):
        self.manager.settings.auto_connect = self.chkAutoConnect.isChecked() if self.chkAutoConnect else False
        self.manager.settings.enable_logs = self.chkEnableLogs.isChecked() if self.chkEnableLogs else False
        self.manager.settings.auto_start = self.chkRunAtStartup.isChecked() if self.chkRunAtStartup else False
        self.manager.settings.advanced_features = self.chkAdvanced.isChecked() if self.chkAdvanced else False
        self.manager.settings.use_local_api = self.chkUseLocalAPI.isChecked() if self.chkUseLocalAPI else False
        self.manager.save_settings()
        
        # Propagate live states to the active tailscale manager in real-time
        if self.parent() and hasattr(self.parent(), "ts_manager"):
            self.parent().ts_manager.use_local_api = self.manager.settings.use_local_api
            self.parent().ts_manager.sso_timeout = self.manager.settings.sso_timeout
        
        # Trigger autostart configuration for the current OS
        from src.utils.autostart import set_autostart
        set_autostart(self.manager.settings.auto_start)
        
        # Refresh loggers if log setting changed
        from src.utils.logger import refresh_all_loggers
        refresh_all_loggers(self.manager.base_dir, self.manager.settings.enable_logs)
        
        # Dynamically update advanced menu in main window
        if self.parent() and hasattr(self.parent(), "update_advanced_menu_state"):
            self.parent().update_advanced_menu_state()

    def _open_log_folder(self):
        from src.utils.logger import get_global_log_dir
        import sys
        path = get_global_log_dir(self.manager.base_dir)
        if os.path.exists(path):
            import subprocess
            try:
                if sys.platform == 'win32':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
            except (FileNotFoundError, Exception) as e:
                QMessageBox.warning(
                    self, 
                    "Open Folder Failed", 
                    f"Could not open the log folder automatically.\n\n"
                    f"Please locate it manually at:\n{path}\n\n"
                    f"Details: {e}"
                )
        else:
            QMessageBox.warning(self, "Error", "Log folder does not exist yet.")
