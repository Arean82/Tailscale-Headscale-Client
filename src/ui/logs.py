from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt

class LogsView(QWidget):
    def __init__(self, ts_manager):
        super().__init__()
        self.ts_manager = ts_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        self.header = QHBoxLayout()
        self.title = QLabel("System Logs")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.header.addWidget(self.title)
        self.header.addStretch()
        
        self.clear_btn = QPushButton("Clear Logs")
        self.clear_btn.clicked.connect(self.clear_logs)
        self.header.addWidget(self.clear_btn)
        
        self.layout.addLayout(self.header)
        
        self.log_display = QTextEdit()
        self.log_display.setObjectName("LogView")
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)
        
        # Connect signals
        self.ts_manager.worker.output_received.connect(self.append_log)
        self.ts_manager.worker.error_received.connect(self.append_error)

    def append_log(self, text):
        self.log_display.append(f"<span style='color: #4CAF50;'>[INFO]</span> {text}")

    def append_error(self, text):
        self.log_display.append(f"<span style='color: #F44336;'>[ERROR]</span> {text}")

    def clear_logs(self):
        self.log_display.clear()
