import os
from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QMessageBox, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

class ProfileNameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        loader = QUiLoader()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ui_path = os.path.join(base_dir, "pygui", "dialogs", "profile.ui")
        ui_file = QFile(ui_path)
        
        if not ui_file.exists():
            print(f"Error: Could not find {ui_path}")
            return
            
        ui_file.open(QFile.ReadOnly)
        self.ui_content = loader.load(ui_file) # Load as a child widget
        ui_file.close()
        
        if self.ui_content:
            # Create a layout to hold the loaded UI content
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.ui_content)
            
            # Sync properties
            self.setWindowTitle(self.ui_content.windowTitle())
            self.setFixedSize(360, 150)
            
            # Access widgets
            self.line_edit = self.ui_content.findChild(QLineEdit, "lineEdit")
            self.btn_create = self.ui_content.findChild(QPushButton, "btnClose")
            
            if self.btn_create:
                self.btn_create.clicked.connect(self.accept)
        
    def get_name(self):
        return self.line_edit.text().strip() if self.line_edit else ""
