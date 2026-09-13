import os
from PySide6.QtWidgets import QDialog, QStackedWidget, QCheckBox, QLineEdit, QMessageBox, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

from .simple_dialogs import BaseUiDialog

class ProfileDialog(BaseUiDialog):
    def __init__(self, parent=None, profile=None, manager=None):
        super().__init__("credentials.ui", parent)
        self.manager = manager
        self.setFixedSize(350, 350)
        
        # Access widgets through self.ui
        self.chkUseSSO = self.ui.findChild(QCheckBox, "chkUseSSO")
        self.stackedWidget = self.ui.findChild(QStackedWidget, "stackedWidget")
        self.btnSave = self.ui.findChild(QPushButton, "btnSave")
        self.btnCancel = self.ui.findChild(QPushButton, "btnCancel")
        self.url_auth = self.ui.findChild(QLineEdit, "lineEditUrlAuth")
        self.url_sso = self.ui.findChild(QLineEdit, "lineEditUrlSSO")
        self.key_entry = self.ui.findChild(QLineEdit, "lineEditKey")
        self.chkEnableFallback = self.ui.findChild(QCheckBox, "chkEnableFallback")
        self.lineEditFallbackIP = self.ui.findChild(QLineEdit, "lineEditFallbackIP")
        
        # 3. Connection Logic (Toggled is better than stateChanged)
        if self.chkUseSSO:
            self.chkUseSSO.toggled.connect(self._handle_sso_toggle)
            
        # 4. Sync URLs (so you don't type twice)
        if self.url_auth and self.url_sso:
            self.url_auth.textChanged.connect(self.url_sso.setText)
            self.url_sso.textChanged.connect(self.url_auth.setText)
            
        # 5. Buttons
        if self.btnSave:
            self.btnSave.clicked.connect(self.accept)
            self.btnSave.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        if self.btnCancel:
            self.btnCancel.clicked.connect(self.reject)
            self.btnCancel.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: bold;")
            
        # 6. Eye Toggle for Auth Key
        self.btnToggleKey = self.ui.findChild(QPushButton, "btnToggleKey")
        if self.btnToggleKey:
            self.btnToggleKey.clicked.connect(self._toggle_key_visibility)

        # Accessibility (EN 301 549 11.2.1.1 / WCAG 1.1.1 Non-text Content)
        profile_a11y = [
            (self.chkUseSSO, "Use Web Browser SSO Toggle", "Switch between pre-shared auth key and browser-based SSO authentication."),
            (self.url_auth, "Control Server URL Input", "Address of the Tailscale or Headscale control plane."),
            (self.url_sso, "SSO Control Server URL Input", "Address of the control plane for browser SSO authentication."),
            (self.key_entry, "Pre-Auth Key Input", "Enter node authentication key or token."),
            (self.btnToggleKey, "Toggle Key Masking Button", "Toggles visibility between masked password bullets and plain text."),
            (self.chkEnableFallback, "Emergency Fallback IP Toggle", "Enables direct IP routing if DNS resolution fails."),
            (self.lineEditFallbackIP, "Emergency Server IP Input", "Fallback IPv4 address for control server."),
            (self.btnSave, "Save Credentials Button", "Saves the authentication settings for this profile."),
            (self.btnCancel, "Cancel Credentials Button", "Discards changes and closes the credentials dialog."),
        ]
        for w, name, desc in profile_a11y:
            if w:
                w.setAccessibleName(name)
                w.setAccessibleDescription(desc)
            
        # 6b. Fallback Toggle logic
        if self.chkEnableFallback and self.lineEditFallbackIP:
            self.chkEnableFallback.toggled.connect(self.lineEditFallbackIP.setVisible)
            self.lineEditFallbackIP.setVisible(self.chkEnableFallback.isChecked())
            
        # 7. Set Initial State
        if profile:
            if self.url_auth: self.url_auth.setText(profile.login_server)
            if self.url_sso: self.url_sso.setText(profile.login_server)
            if self.key_entry: self.key_entry.setText(profile.auth_key)
            if profile.auth_mode == "google":
                if self.chkUseSSO: self.chkUseSSO.setChecked(True)
                if self.stackedWidget: self.stackedWidget.setCurrentIndex(1)
            
            if self.chkEnableFallback:
                global_fallback = getattr(self.manager.settings, 'global_dns_fallback', False) if self.manager else False
                self.chkEnableFallback.setChecked(getattr(profile, 'enable_dns_fallback', False) or global_fallback)
            if self.lineEditFallbackIP:
                self.lineEditFallbackIP.setText(getattr(profile, 'last_known_ip', ""))
                self.lineEditFallbackIP.setVisible(self.chkEnableFallback.isChecked() if self.chkEnableFallback else False)
        else:
            if self.stackedWidget: self.stackedWidget.setCurrentIndex(0)

    def _handle_sso_toggle(self, is_checked):
        if self.stackedWidget:
            # Page 0 = pageAuthKey (URL + Key)
            # Page 1 = pageSSO (URL Only)
            index = 1 if is_checked else 0
            self.stackedWidget.setCurrentIndex(index)

    def get_data(self):
        use_sso = self.chkUseSSO.isChecked() if self.chkUseSSO else False
        enable_fallback = self.chkEnableFallback.isChecked() if self.chkEnableFallback else False
        fallback_ip = self.lineEditFallbackIP.text().strip() if self.lineEditFallbackIP else ""
        
        if use_sso:
            url = self.url_sso.text().strip() if self.url_sso else ""
            if not url:
                QMessageBox.warning(self, "Missing Data", "VPN URL is required.")
                return None
            return {
                "name": url,
                "login_server": url,
                "auth_key": "",
                "auth_mode": "google",
                "enable_dns_fallback": enable_fallback,
                "last_known_ip": fallback_ip
            }
        else:
            url = self.url_auth.text().strip() if self.url_auth else ""
            key = self.key_entry.text().strip() if self.key_entry else ""
            if not url:
                QMessageBox.warning(self, "Missing Data", "VPN URL is required.")
                return None
            return {
                "name": url,
                "login_server": url,
                "auth_key": key,
                "auth_mode": "auth_key",
                "enable_dns_fallback": enable_fallback,
                "last_known_ip": fallback_ip
            }

    def _toggle_key_visibility(self):
        """Switches the Auth Key between masked and visible."""
        if not self.key_entry or not self.btnToggleKey:
            return
            
        if self.key_entry.echoMode() == QLineEdit.Password:
            self.key_entry.setEchoMode(QLineEdit.Normal)
            self.btnToggleKey.setText("🙈") # Monkey Covering Eyes (Hide)
        else:
            self.key_entry.setEchoMode(QLineEdit.Password)
            self.btnToggleKey.setText("👁️") # Eye (Show)
