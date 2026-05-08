import os
import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

app = QApplication([])
loader = QUiLoader()
ui_path = os.path.join("pygui", "windows", "tab_widget.ui")
ui_file = QFile(ui_path)
ui_file.open(QFile.ReadOnly)
ui_content = loader.load(ui_file)
ui_file.close()

print(f"UI file: {ui_path}")
for child in ui_content.findChildren(QPushButton):
    print(f"Button: {child.objectName()} - Text: {child.text()}")
for child in ui_content.findChildren(QLabel):
    try:
        print(f"Label: {child.objectName()} - Text: {child.text().encode('ascii', 'ignore').decode()}")
    except:
        print(f"Label: {child.objectName()}")
for child in ui_content.findChildren(QLineEdit):
    print(f"LineEdit: {child.objectName()} - Text: {child.text()}")
