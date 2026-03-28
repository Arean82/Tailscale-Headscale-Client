# pylogic/dialogs/license_dlg.py
# PySide6 port of gui/license_viewer.py

import os

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt

from pylogic.ui_helpers import load_ui, center_window


class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = load_ui("pygui/dialogs/license.ui", parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowTitle("License")
        self.resize(520, 420)

        if parent:
            center_window(parent, self)

        self.ui.btnClose.clicked.connect(self.accept)
        self._load_license()

    # ------------------------------------------------------------------

    def _load_license(self):
        # Walk up from this file's directory to find the project root LICENSE
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        path = os.path.join(base_dir, "LICENSE")

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.ui.textArea.setPlainText(f.read())
        else:
            self.ui.textArea.setPlainText("LICENSE file not found in project root.")
