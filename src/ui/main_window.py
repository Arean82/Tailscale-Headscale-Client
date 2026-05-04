import os
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMenuBar, QTabWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

from .dashboard import DashboardView

class MainWindow(QMainWindow):
    def __init__(self, manager, ts_manager):
        super().__init__()
        self.manager = manager
        self.ts_manager = ts_manager
        
        # 1. Load your UI file
        loader = QUiLoader()
        ui_path = os.path.join("pygui", "windows", "main_window.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.ui_window = loader.load(ui_file) # This is the QMainWindow from your UI
        ui_file.close()
        
        # 2. Steal the central widget and menu bar from the loaded UI
        # This is the most reliable way to preserve your design
        self.setCentralWidget(self.ui_window.findChild(QWidget, "centralwidget"))
        
        menubar = self.ui_window.findChild(QMenuBar, "menuBar")
        if menubar:
            self.setMenuBar(menubar)
            
        self.tabWidget = self.findChild(QTabWidget, "tabWidget")
        self.setWindowTitle(self.ui_window.windowTitle())
        self.setMinimumSize(self.ui_window.minimumSize())
        self.setMaximumSize(self.ui_window.maximumSize())
        self.resize(self.ui_window.size())

        # 3. Connect Actions (Finding them on the loaded UI window)
        from PySide6.QtGui import QAction
        
        self.actionExit = self.ui_window.findChild(QAction, "actionExit")
        if self.actionExit: self.actionExit.triggered.connect(self.close)
        
        self.actionAddProfile = self.ui_window.findChild(QAction, "actionAddProfile")
        if self.actionAddProfile: self.actionAddProfile.triggered.connect(self.add_profile_clicked)
        
        self.actionRemoveProfile = self.ui_window.findChild(QAction, "actionRemoveProfile")
        if self.actionRemoveProfile: self.actionRemoveProfile.triggered.connect(self.remove_profile_clicked)
        
        self.actionAbout = self.ui_window.findChild(QAction, "actionAbout")
        if self.actionAbout: self.actionAbout.triggered.connect(self.show_about)
        
        self.actionLicense = self.ui_window.findChild(QAction, "actionLicense")
        if self.actionLicense: self.actionLicense.triggered.connect(self.show_license)
        
        self.actionReadme = self.ui_window.findChild(QAction, "actionReadme")
        if self.actionReadme: self.actionReadme.triggered.connect(self.show_readme)
        
        # 4. Initialize tabs
        self.refresh_tabs()


    def show_about(self):
        from .components.simple_dialogs import AboutDialog
        AboutDialog(self).exec()

    def show_license(self):
        from .components.simple_dialogs import LicenseDialog
        LicenseDialog(self).exec()

    def show_readme(self):
        from .components.simple_dialogs import ReadmeDialog
        ReadmeDialog(self).exec()


    def add_profile_clicked(self):
        from .components.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data or not data["name"]: return
            from ..core.models import Profile
            
            # Map 'sso' to 'google' if that's what the thinker app expected
            auth_mode = "google" if data["auth_mode"] == "sso" else data["auth_mode"]
            data["auth_mode"] = auth_mode
            
            new_profile = Profile(name=data["name"], **data)
            self.manager.add_profile(new_profile)
            self.refresh_tabs()


    def remove_profile_clicked(self):
        if not self.tabWidget: return
        index = self.tabWidget.currentIndex()
        if index >= 0:
            name = self.tabWidget.tabText(index)
            self.manager.remove_profile(name)
            self.refresh_tabs()

    def refresh_tabs(self):
        if not self.tabWidget:
            # Try to find it again just in case
            self.tabWidget = self.findChild(QTabWidget, "tabWidget")
            
        if not self.tabWidget: return
        
        while self.tabWidget.count() > 0:
            self.tabWidget.removeTab(0)
            
        for name, profile in self.manager.profiles.items():
            view = DashboardView(self.manager, self.ts_manager, profile)
            self.tabWidget.addTab(view, name)
        
        if not self.manager.profiles:
            view = DashboardView(self.manager, self.ts_manager)
            self.tabWidget.addTab(view, "Default")
