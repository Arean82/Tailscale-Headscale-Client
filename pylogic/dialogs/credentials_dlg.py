# pylogic/dialogs/credentials_dlg.py
# PySide6 port of gui/change_credentials_popup.py
# Uses QStackedWidget instead of Tkinter place-animation for SSO/auth-key switching.

from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt

from pylogic.ui_helpers import load_ui, center_window
from logic.vpn_logic import get_auth_mode, save_auth_mode


class CredentialsDialog(QDialog):
    def __init__(self, parent=None, tab_name="", current_url="",
                 current_key="", save_callback=None):
        super().__init__(parent)

        self.tab_name      = tab_name
        self.save_callback = save_callback

        self.ui = load_ui("pygui/dialogs/credentials.ui", parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowTitle(f"Set VPN Credentials — '{tab_name}'")
        self.setFixedSize(300, 280)
        self.setWindowModality(Qt.ApplicationModal)

        if parent:
            center_window(parent, self)

        # Widget refs
        self.chkUseSSO       = self.ui.chkUseSSO
        self.stackedWidget   = self.ui.stackedWidget
        self.lineEditUrlAuth  = self.ui.lineEditUrlAuth
        self.lineEditKey      = self.ui.lineEditKey
        self.lineEditUrlSSO   = self.ui.lineEditUrlSSO
        self.btnSave          = self.ui.btnSave
        self.btnCancel        = self.ui.btnCancel

        # Pre-fill
        self.lineEditUrlAuth.setText(current_url)
        self.lineEditUrlSSO.setText(current_url)
        self.lineEditKey.setText(current_key)

        # Restore saved auth mode
        saved_mode = get_auth_mode(tab_name)
        is_sso     = (saved_mode == "google")
        self.chkUseSSO.setChecked(is_sso)
        self._switch_page(is_sso)

        # Connections
        self.chkUseSSO.toggled.connect(self._switch_page)
        self.btnSave.clicked.connect(self._on_save)
        self.btnCancel.clicked.connect(self.reject)

    # ------------------------------------------------------------------

    def _switch_page(self, use_sso: bool):
        # QStackedWidget: page 0 = auth_key, page 1 = SSO
        self.stackedWidget.setCurrentIndex(1 if use_sso else 0)

    def _on_save(self):
        use_sso = self.chkUseSSO.isChecked()

        if use_sso:
            url = self.lineEditUrlSSO.text().strip()
            key = ""
        else:
            url = self.lineEditUrlAuth.text().strip()
            key = self.lineEditKey.text().strip()

        if not url:
            QMessageBox.warning(self, "Missing Data", "VPN URL is required.")
            return

        mode = "google" if use_sso else "auth_key"

        if self.save_callback:
            self.save_callback(url, key, mode)

        save_auth_mode(self.tab_name, mode)
        self.accept()

        QMessageBox.information(
            self.parent(), "Saved",
            f"Credentials saved for '{self.tab_name}'."
        )
