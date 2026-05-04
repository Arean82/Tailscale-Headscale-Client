from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
import sys

app = QApplication(sys.argv)
loader = QUiLoader()
# Create a dummy ui file
with open("test.ui", "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?><ui version="4.0"><class>Form</class><widget class="QWidget" name="Form"><widget class="QPushButton" name="myButton"/></widget></ui>')

ui_file = QFile("test.ui")
ui_file.open(QFile.ReadOnly)
widget = loader.load(ui_file)
ui_file.close()

print(f"Widget: {widget}")
try:
    print(f"myButton: {widget.myButton}")
except AttributeError:
    print("Attribute 'myButton' not found")
