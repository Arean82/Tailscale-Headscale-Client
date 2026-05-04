import os
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "dialogs", "progress.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file)
        ui_file.close()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        
        self.labelProgress = self.ui.findChild(QLabel, "labelProgress")
        
    def set_message(self, text):
        if self.labelProgress:
            self.labelProgress.setText(text)
            self.labelProgress.update()
