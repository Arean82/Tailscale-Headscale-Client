from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QSpinBox, QHBoxLayout, QFrame
from PySide6.QtCore import Qt

class SettingsView(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        self.title = QLabel("Settings")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.layout.addWidget(self.title)
        
        self.card = QFrame()
        self.card.setObjectName("DashboardCard")
        self.card_layout = QVBoxLayout(self.card)
        
        # Auto Start
        self.auto_start_cb = QCheckBox("Launch on system startup")
        self.auto_start_cb.setChecked(self.manager.settings.auto_start)
        self.auto_start_cb.stateChanged.connect(self.save_settings)
        self.card_layout.addWidget(self.auto_start_cb)
        
        self.card_layout.addSpacing(10)
        
        # Max Tabs
        max_tabs_layout = QHBoxLayout()
        max_tabs_layout.addWidget(QLabel("Maximum connection profiles:"))
        self.max_tabs_sb = QSpinBox()
        self.max_tabs_sb.setRange(1, 20)
        self.max_tabs_sb.setValue(self.manager.settings.max_tabs)
        self.max_tabs_sb.valueChanged.connect(self.save_settings)
        max_tabs_layout.addWidget(self.max_tabs_sb)
        max_tabs_layout.addStretch()
        self.card_layout.addLayout(max_tabs_layout)
        
        self.layout.addWidget(self.card)
        self.layout.addStretch()

    def save_settings(self):
        self.manager.settings.auto_start = self.auto_start_cb.isChecked()
        self.manager.settings.max_tabs = self.max_tabs_sb.value()
        self.manager.save_settings()
