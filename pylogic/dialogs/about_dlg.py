# pylogic/dialogs/about_dlg.py
# PySide6 port of gui/about.py + gui/about_viewer.py (merged into one dialog)

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt

from pylogic.ui_helpers import load_ui, center_window


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = load_ui("pygui/dialogs/about.ui", parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowTitle("About Us")
        self.setFixedSize(360, 280)
        self.setWindowModality(Qt.ApplicationModal)

        if parent:
            center_window(parent, self)

        self.ui.btnClose.clicked.connect(self.accept)
