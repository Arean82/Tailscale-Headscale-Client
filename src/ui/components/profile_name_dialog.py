import os
from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QMessageBox, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt

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
            
            # Accessibility (EN 301 549 11.2.1.1 / WCAG 1.1.1 Non-text Content)
            if self.line_edit:
                self.line_edit.setAccessibleName("New Profile Name Input")
                self.line_edit.setAccessibleDescription("Enter an alphanumeric name for the new network profile.")
            if self.btn_create:
                self.btn_create.setAccessibleName("Create Profile Button")
                self.btn_create.setAccessibleDescription("Validates the entered name and creates the new profile tab.")
                self.btn_create.clicked.connect(self.accept)
            
    def accept(self):
        name = self.get_name()
        sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Profile name cannot be empty.")
            return
        if not sanitized:
            QMessageBox.warning(self, "Invalid Name", "Profile name must contain at least one valid alphanumeric character.")
            return
        if ".." in sanitized:
            QMessageBox.warning(self, "Invalid Name", "Profile name cannot contain path traversal sequences like '..'.")
            return
        super().accept()

    def get_name(self):
        return self.line_edit.text().strip() if self.line_edit else ""

    def keyPressEvent(self, event):
        """Ensure Escape cancels ProfileNameDialog (EN 301 549 11.2.1.2 - No Keyboard Trap)."""
        if event.key() == Qt.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)
