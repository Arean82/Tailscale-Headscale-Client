# src/ui/components/settings_dialog.py

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from .simple_dialogs import BaseUiDialog


class SettingsDialog(BaseUiDialog):
    def __init__(self, manager, parent=None):
        super().__init__("settings.ui", parent)
        self.manager = manager
        
        # Remove double margins and apply compact spacing
        self.layout().setContentsMargins(16, 12, 16, 12)
        self.layout().setSpacing(0)
        if self.ui.layout():
            self.ui.layout().setContentsMargins(0, 0, 0, 0)
            self.ui.layout().setSpacing(6)
        
        # Access widgets through self.ui
        self.chkAutoConnect = self.ui.findChild(QCheckBox, "chkAutoConnect")
        self.chkEnableLogs = self.ui.findChild(QCheckBox, "chkEnableLogs")
        self.chkRunAtStartup = self.ui.findChild(QCheckBox, "chkRunAtStartup")
        self.chkAdvanced = self.ui.findChild(QCheckBox, "chkAdvanced")
        self.chkUseLocalAPI = self.ui.findChild(QCheckBox, "chkUseLocalAPI")
        self.chkInsecureSSL = self.ui.findChild(QCheckBox, "chkInsecureSSL")
        self.chkGlobalDnsFallback = self.ui.findChild(QCheckBox, "chkGlobalDnsFallback")
        self.chkCheckScreenReader = self.ui.findChild(QCheckBox, "chkCheckScreenReader")
        self.lineEditLogPath = self.ui.findChild(QLineEdit, "lineEdit")
        self.btnOpenLogFolder = self.ui.findChild(QPushButton, "btnOpenLogFolder")
        self.btnClose = self.ui.findChild(QPushButton, "btnClose")
        self.comboLanguage = self.ui.findChild(QComboBox, "comboLanguage")
        
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
            
        if self.chkInsecureSSL:
            self.chkInsecureSSL.setChecked(self.manager.settings.insecure_ssl)
            
        if self.chkGlobalDnsFallback:
            self.chkGlobalDnsFallback.setChecked(self.manager.settings.global_dns_fallback)
            
        if self.chkCheckScreenReader:
            self.chkCheckScreenReader.setChecked(getattr(self.manager.settings, 'check_screen_reader', False))
            
        if self.lineEditLogPath:
            self.lineEditLogPath.setReadOnly(True)
            self.lineEditLogPath.setText(self.manager.base_dir)

        if self.comboLanguage:
            # PySide6 QUiLoader ignores 'data' fields in .ui combobox items, so we populate manually
            self.comboLanguage.clear()
            self.comboLanguage.addItem("English", "en_US")
            self.comboLanguage.addItem("Arabic", "ar_SA")
            self.comboLanguage.addItem("French", "fr_FR")
            self.comboLanguage.addItem("Spanish", "es_ES")
            
            index = self.comboLanguage.findData(self.manager.settings.language)
            if index >= 0:
                self.comboLanguage.setCurrentIndex(index)
            self.comboLanguage.currentIndexChanged.connect(self._save_settings)
            
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
            
        self.spinStartupDelay = self.ui.findChild(QSpinBox, "spinStartupDelay")
        if self.spinStartupDelay:
            self.spinStartupDelay.setValue(self.manager.settings.startup_delay)
            self.spinStartupDelay.valueChanged.connect(self._save_settings)

        # Accessibility (EN 301 549 11.2.1.1 / WCAG 1.1.1 Non-text Content)
        settings_a11y = [
            (self.chkAutoConnect, "Auto-Connect at Launch Toggle", "Enables automatic VPN tunnel connection upon application start."),
            (self.chkInsecureSSL, "Self-Signed SSL Toggle", "Permits connections to Headscale control servers with untrusted or self-signed certificates."),
            (self.chkAdvanced, "Advanced Features Mode Toggle", "Enables granular routing, subnet advertisement, and exit node settings."),
            (self.chkRunAtStartup, "Launch on OS Startup Toggle", "Configures the client application to run automatically on system boot."),
            (self.chkUseLocalAPI, "Experimental Local API Toggle", "Enables direct communication with tailscaled daemon via local Unix sockets or named pipes."),
            (self.chkEnableLogs, "Global Logging Toggle", "Enables writing debug and operational logs to disk."),
            (self.chkGlobalDnsFallback, "Global DNS Fallback Toggle", "Emergency DNS fallback option."),
            (self.lineEditLogPath, "Application Directory Path", "Displays the local base path where logs and configurations are stored."),
            (self.btnOpenLogFolder, "Open Log Folder Button", "Opens the local log file directory in the system file explorer."),
            (self.comboLanguage, "Application Language Selector", "Select interface language: English, Arabic, French, or Spanish."),
            (self.spinMaxTabs, "Maximum Profile Limit SpinBox", "Sets the maximum number of network profiles allowed in the tab bar."),
            (self.spinStartupDelay, "Startup Daemon Wait Timeout SpinBox", "Sets delay in seconds to wait for daemon readiness upon boot."),
            (self.spinSsoTimeout, "SSO Login Timeout SpinBox", "Sets timeout duration in seconds for web browser single sign-on authentication."),
            (self.btnClose, "Save and Close Settings Button", "Saves all configuration changes and dismisses the dialog."),
        ]
        for w, name, desc in settings_a11y:
            if w:
                w.setAccessibleName(name)
                w.setAccessibleDescription(desc)
            
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
        if self.chkInsecureSSL:
            self.chkInsecureSSL.toggled.connect(self._save_settings)
        if self.chkGlobalDnsFallback:
            self.chkGlobalDnsFallback.toggled.connect(self._save_settings)
        if self.chkCheckScreenReader:
            self.chkCheckScreenReader.toggled.connect(self._save_settings)
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
        old_language = getattr(self.manager.settings, 'language', 'en_US')

        self.manager.settings.auto_connect = self.chkAutoConnect.isChecked() if self.chkAutoConnect else False
        self.manager.settings.enable_logs = self.chkEnableLogs.isChecked() if self.chkEnableLogs else False
        self.manager.settings.auto_start = self.chkRunAtStartup.isChecked() if self.chkRunAtStartup else False
        self.manager.settings.advanced_features = self.chkAdvanced.isChecked() if self.chkAdvanced else False
        self.manager.settings.use_local_api = self.chkUseLocalAPI.isChecked() if self.chkUseLocalAPI else False
        self.manager.settings.insecure_ssl = self.chkInsecureSSL.isChecked() if self.chkInsecureSSL else False
        self.manager.settings.global_dns_fallback = self.chkGlobalDnsFallback.isChecked() if self.chkGlobalDnsFallback else False
        self.manager.settings.check_screen_reader = self.chkCheckScreenReader.isChecked() if self.chkCheckScreenReader else False
        self.manager.settings.startup_delay = self.spinStartupDelay.value() if self.spinStartupDelay else 10
        if self.comboLanguage:
            self.manager.settings.language = self.comboLanguage.currentData()
        self.manager.save_settings()

        new_language = self.manager.settings.language
        lang_changed = (old_language != new_language)
        
        # Propagate live states to the active tailscale manager in real-time
        if self.parent() and hasattr(self.parent(), "ts_manager"):
            self.parent().ts_manager.use_local_api = self.manager.settings.use_local_api
            self.parent().ts_manager.sso_timeout = self.manager.settings.sso_timeout
            self.parent().ts_manager.insecure_ssl = self.manager.settings.insecure_ssl
        
        # Trigger autostart configuration for the current OS
        from src.utils.autostart import set_autostart
        set_autostart(self.manager.settings.auto_start)
        
        # Refresh loggers if log setting changed
        from src.utils.logger import refresh_all_loggers
        refresh_all_loggers(self.manager.base_dir, self.manager.settings.enable_logs)
        
        # Dynamically update advanced menu in main window
        if self.parent() and hasattr(self.parent(), "update_advanced_menu_state"):
            self.parent().update_advanced_menu_state()
            
        # Trigger GUI soft-restart if language changed
        if lang_changed:
            from PySide6.QtCore import QCoreApplication
            title = QCoreApplication.translate("MainWindow", "Language Changed")
            body = QCoreApplication.translate("MainWindow", "The application needs to restart to apply the new language translation.\n\nYour Tailscale VPN connection will remain safely active in the background.\n\nRestart GUI now?")
            
            reply = QMessageBox.question(
                self, title, body,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.accept()
                if self.parent() and hasattr(self.parent(), "restart_app"):
                    self.parent().restart_app()

    def _open_log_folder(self):
        import shutil
        import sys
        path = self.manager.base_dir
        if os.path.exists(path):
            import subprocess
            try:
                if sys.platform == 'win32':
                    os.startfile(path)  # noqa: S606 (folder open in Explorer, not a shell process)
                elif sys.platform == 'darwin':
                    subprocess.Popen([shutil.which("open") or "open", path], shell=False)
                else:
                    subprocess.Popen([shutil.which("xdg-open") or "xdg-open", path], shell=False)
            except OSError as e:
                QMessageBox.warning(
                    self, 
                    "Open Folder Failed", 
                    f"Could not open the log folder automatically.\n\n"
                    f"Please locate it manually at:\n{path}\n\n"
                    f"Details: {e}"
                )
        else:
            QMessageBox.warning(self, "Error", "Log folder does not exist yet.")
