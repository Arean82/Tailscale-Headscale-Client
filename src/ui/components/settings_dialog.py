# src/ui/components/settings_dialog.py

import os
from PySide6.QtWidgets import QDialog, QCheckBox, QPushButton, QLabel, QMessageBox, QSlider, QVBoxLayout, QHBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt

from .simple_dialogs import BaseUiDialog

class SettingsDialog(BaseUiDialog):
    def __init__(self, manager, parent=None):
        super().__init__("settings.ui", parent)
        self.manager = manager
        
        # Access widgets through self.ui
        self.chkAutoConnect = self.ui.findChild(QCheckBox, "chkAutoConnect")
        self.chkEnableLogs = self.ui.findChild(QCheckBox, "chkEnableLogs")
        self.labelLogPath = self.ui.findChild(QLabel, "labelLogPath")
        self.btnOpenLogFolder = self.ui.findChild(QPushButton, "btnOpenLogFolder")
        self.btnClose = self.ui.findChild(QPushButton, "btnClose")
        
        # Set initial values
        if self.chkAutoConnect:
            self.chkAutoConnect.setChecked(self.manager.settings.auto_connect)
            
        if self.chkEnableLogs:
            self.chkEnableLogs.setChecked(self.manager.settings.enable_logs)
            
        if self.labelLogPath:
            from src.utils.logger import get_global_log_dir
            self.labelLogPath.setText(f"Path: {self.manager.base_dir}")
            
        # Access slider widgets from UI
        self.sliderMaxTabs = self.ui.findChild(QSlider, "sliderMaxTabs")
        self.labelMaxTabsValue = self.ui.findChild(QLabel, "labelMaxTabsValue")
        
        if self.sliderMaxTabs:
            self.sliderMaxTabs.setValue(self.manager.settings.max_tabs)
            self.sliderMaxTabs.valueChanged.connect(self._on_slider_changed)
            
        if self.labelMaxTabsValue:
            self.labelMaxTabsValue.setText(f"Value: {self.manager.settings.max_tabs}")
            
        # Connections
        if self.chkAutoConnect:
            self.chkAutoConnect.toggled.connect(self._save_settings)
        if self.chkEnableLogs:
            self.chkEnableLogs.toggled.connect(self._save_settings)
        if self.btnOpenLogFolder:
            self.btnOpenLogFolder.clicked.connect(self._open_log_folder)
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)

    def _on_slider_changed(self, value):
        if self.labelMaxTabsValue:
            self.labelMaxTabsValue.setText(f"Value: {value}")
        self.manager.settings.max_tabs = value
        self.manager.save_settings()

    def _save_settings(self):
        self.manager.settings.auto_connect = self.chkAutoConnect.isChecked() if self.chkAutoConnect else False
        self.manager.settings.enable_logs = self.chkEnableLogs.isChecked() if self.chkEnableLogs else False
        self.manager.save_settings()
        
        # Refresh loggers if log setting changed
        from src.utils.logger import refresh_all_loggers
        refresh_all_loggers(self.manager.base_dir, self.manager.settings.enable_logs)

    def _open_log_folder(self):
        path = self.manager.base_dir
        if os.path.exists(path):
            import subprocess
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
        else:
            QMessageBox.warning(self, "Error", "Log folder does not exist yet.")
