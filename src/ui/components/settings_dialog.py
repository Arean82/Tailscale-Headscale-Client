# src/ui/components/settings_dialog.py

import os
from PySide6.QtWidgets import QDialog, QCheckBox, QPushButton, QLabel, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

class SettingsDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        
        # Load UI
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "dialogs", "settings.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()
        
        self.setWindowTitle("Settings")
        
        # Access widgets
        self.chkAutoConnect = self.findChild(QCheckBox, "chkAutoConnect")
        self.chkEnableLogs = self.findChild(QCheckBox, "chkEnableLogs")
        self.labelLogPath = self.findChild(QLabel, "labelLogPath")
        self.btnOpenLogFolder = self.findChild(QPushButton, "btnOpenLogFolder")
        self.btnClose = self.findChild(QPushButton, "btnClose")
        
        # Set initial values
        if self.chkAutoConnect:
            self.chkAutoConnect.setChecked(self.manager.settings.auto_connect)
            
        if self.chkEnableLogs:
            self.chkEnableLogs.setChecked(self.manager.settings.enable_logs)
            
        if self.labelLogPath:
            from src.utils.logger import get_global_log_dir
            self.labelLogPath.setText(f"Path: {get_global_log_dir(self.manager.base_dir)}")
            
        # Connections
        if self.chkAutoConnect:
            self.chkAutoConnect.toggled.connect(self._save_settings)
        if self.chkEnableLogs:
            self.chkEnableLogs.toggled.connect(self._save_settings)
        if self.btnOpenLogFolder:
            self.btnOpenLogFolder.clicked.connect(self._open_log_folder)
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)

    def _save_settings(self):
        self.manager.settings.auto_connect = self.chkAutoConnect.isChecked() if self.chkAutoConnect else False
        self.manager.settings.enable_logs = self.chkEnableLogs.isChecked() if self.chkEnableLogs else False
        self.manager.save_settings()
        
        # Refresh loggers if log setting changed
        from src.utils.logger import refresh_all_loggers
        refresh_all_loggers(self.manager.base_dir, self.manager.settings.enable_logs)

    def _open_log_folder(self):
        from src.utils.logger import get_global_log_dir
        path = get_global_log_dir(self.manager.base_dir)
        if os.path.exists(path):
            import subprocess
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.Popen(['xdg-open', path])
        else:
            QMessageBox.warning(self, "Error", "Log folder does not exist yet.")
