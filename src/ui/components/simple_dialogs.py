import os
from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

class BaseUiDialog(QDialog):
    def __init__(self, ui_name, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "dialogs", ui_name)
        ui_file = QFile(ui_path)
        if ui_file.exists():
            ui_file.open(QFile.ReadOnly)
            self.ui = loader.load(ui_file)
            ui_file.close()
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.ui)
            
            self.setWindowTitle(self.ui.windowTitle())
            
            # Common close button finding
            self.btnClose = self.ui.findChild(QPushButton, "btnClose")
            if self.btnClose:
                self.btnClose.clicked.connect(self.accept)
                self.btnClose.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: bold;")

class AboutDialog(BaseUiDialog):
    def __init__(self, parent=None):
        super().__init__("about.ui", parent)

class ReadmeDialog(BaseUiDialog):
    def __init__(self, parent=None):
        super().__init__("readme.ui", parent)
        # Load README.md into the text viewer if it exists
        text_edit = self.findChild(QTextEdit, "textEdit")
        if text_edit and os.path.exists("README.md"):
            with open("README.md", "r", encoding="utf-8") as f:
                text_edit.setPlainText(f.read())

class TrafficDialog(BaseUiDialog):
    def __init__(self, parent=None, stats_text=""):
        super().__init__("traffic.ui", parent)
        label_stats = self.findChild(QLabel, "labelStats")
        if label_stats:
            label_stats.setText(stats_text)

class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("View License")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        if os.path.exists("LICENSE"):
            with open("LICENSE", "r", encoding="utf-8") as f:
                self.text_edit.setPlainText(f.read())
        layout.addWidget(self.text_edit)
        
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.accept)
        self.btnClose.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: bold;")
        layout.addWidget(self.btnClose)
