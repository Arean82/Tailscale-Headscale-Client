from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QInputDialog, QFrame, QMessageBox
from .components.profile_dialog import ProfileDialog
from ..core.models import Profile

class ProfilesView(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        self.header = QHBoxLayout()
        self.title = QLabel("Connection Profiles")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.header.addWidget(self.title)
        self.header.addStretch()
        
        self.add_btn = QPushButton("+ New Profile")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_profile)
        self.header.addWidget(self.add_btn)
        
        self.layout.addLayout(self.header)
        
        self.profiles_list = QListWidget()
        self.profiles_list.setObjectName("LogView") # Reuse dark style
        self.layout.addWidget(self.profiles_list)
        
        self.actions_layout = QHBoxLayout()
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_profile)
        self.actions_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("color: #F44336;")
        self.delete_btn.clicked.connect(self.delete_profile)
        self.actions_layout.addWidget(self.delete_btn)
        
        self.layout.addLayout(self.actions_layout)
        
        self.refresh_list()

    def refresh_list(self):
        self.profiles_list.clear()
        for name in self.manager.profiles.keys():
            self.profiles_list.addItem(name)

    def add_profile(self):
        dialog = ProfileDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data["name"]: return
            
            if data["name"] in self.manager.profiles:
                QMessageBox.warning(self, "Error", "Profile name already exists.")
                return
                
            new_profile = Profile(
                name=data["name"],
                login_server=data["login_server"],
                auth_key=data["auth_key"]
            )
            self.manager.add_profile(new_profile)
            self.refresh_list()

    def edit_profile(self):
        item = self.profiles_list.currentItem()
        if not item: return
        
        profile = self.manager.profiles[item.text()]
        dialog = ProfileDialog(self, profile)
        if dialog.exec():
            data = dialog.get_data()
            profile.login_server = data["login_server"]
            profile.auth_key = data["auth_key"]
            self.manager.save_profiles()
            self.refresh_list()


    def delete_profile(self):
        item = self.profiles_list.currentItem()
        if not item: return
        self.manager.remove_profile(item.text())
        self.refresh_list()
