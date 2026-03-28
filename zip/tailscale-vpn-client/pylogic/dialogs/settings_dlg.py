# pylogic/dialogs/settings_dlg.py
# PySide6 port of gui/settings.py

import os
import sys
import subprocess

from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Qt

from pylogic.ui_helpers import load_ui, center_window
from logic.vpn_logic import load_settings, save_settings
from logic.logger import get_global_log_dir, refresh_all_loggers, clear_global_logs


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = load_ui("pygui/dialogs/settings.ui", parent=self)

        # Embed loaded widget inside this dialog
        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.setWindowTitle("Settings")
        self.setFixedSize(340, 240)
        self.setWindowModality(Qt.ApplicationModal)

        if parent:
            center_window(parent, self)

        # Widget references
        self.chkAutoConnect   = self.ui.chkAutoConnect
        self.chkEnableLogs    = self.ui.chkEnableLogs
        self.frameLogDetails  = self.ui.frameLogDetails
        self.labelLogPath     = self.ui.labelLogPath
        self.btnOpenLogFolder = self.ui.btnOpenLogFolder
        self.btnClose         = self.ui.btnClose

        # Load current settings
        self.settings = load_settings()
        self.chkAutoConnect.setChecked(self.settings.get("auto_connect", False))
        self.chkEnableLogs.setChecked(self.settings.get("enable_logs", False))
        self.labelLogPath.setText(f"Path: {get_global_log_dir()}")

        self._update_log_ui()

        # Connections
        self.chkAutoConnect.toggled.connect(self._on_auto_connect_toggle)
        self.chkEnableLogs.toggled.connect(self._on_log_toggle)
        self.btnOpenLogFolder.clicked.connect(self._open_log_folder)
        self.btnClose.clicked.connect(self.accept)

    def _on_auto_connect_toggle(self, checked: bool):
        self.settings["auto_connect"] = checked
        save_settings(self.settings)

    def _on_log_toggle(self, checked: bool):
        if not checked:
            reply = QMessageBox.question(
                self, "Disable & Delete Logs",
                "Disabling logs will permanently delete all existing log files.\n\n"
                "Are you sure you want to proceed?",
                QMessageBox.Ok | QMessageBox.Cancel,
            )
            if reply != QMessageBox.Ok:
                self.chkEnableLogs.blockSignals(True)
                self.chkEnableLogs.setChecked(True)
                self.chkEnableLogs.blockSignals(False)
                return
            clear_global_logs()

        self.settings["enable_logs"] = checked
        save_settings(self.settings)
        self._update_log_ui()
        refresh_all_loggers()

    def _update_log_ui(self):
        self.frameLogDetails.setVisible(self.chkEnableLogs.isChecked())

    def _open_log_folder(self):
        log_dir = get_global_log_dir()
        if sys.platform == "win32":
            os.startfile(log_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", log_dir])
        else:
            subprocess.Popen(["xdg-open", log_dir])
