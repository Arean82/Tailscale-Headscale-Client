# pylogic/windows/app_controller.py
# PySide6 port of gui/gui_main.py + gui/gui_start.py
# Loads pygui/windows/main_window.ui via QUiLoader.
# All Tkinter/CTk references removed.

import os
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QApplication, QMessageBox,
    QInputDialog,
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QTimer

from pylogic.ui_helpers import (
    load_ui, center_window, write_log, build_stylesheet, resource_path
)
from logic.vpn_logic import (
    acquire_mutex, release_mutex,
    check_tailscale_installed, initialize_app_storage,
    get_tab_dir, load_tab_names, save_tab_names,
    load_last_selected_tab_id, save_last_selected_tab_id,
    load_settings, save_settings,
    get_file_path, TAB_NAMES_FILE,
    write_log as vpn_write_log,
)
from logic.logger import app_logger, get_global_log_dir


MAX_TABS = 5


class AppController(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load .ui
        self.ui = load_ui("pygui/windows/main_window.ui", parent=None)
        self.setCentralWidget(self.ui.centralwidget)
        self.setMenuBar(self.ui.menuBar)
        self.setWindowTitle("TAILSCALE VPN Client")

        # Apply theme
        settings = load_settings()
        self.current_theme_name = settings.get("theme", "light")
        QApplication.instance().setStyleSheet(build_stylesheet(self.current_theme_name))

        # OS-specific geometry
        if sys.platform == "win32":
            self.resize(400, 230)
        else:
            self.resize(420, 260)
        self.setFixedSize(self.size())

        # Icon
        icon_path = resource_path(os.path.join("assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Tab widget (from .ui)
        self.tabWidget = self.ui.tabWidget

        # Internal state
        self.tabs: dict         = {}   # tab_id -> TabController
        self.tab_id_to_name: dict = {}
        self.connected_tab_id   = None
        self.next_tab_id        = 1

        # Mutex
        acquired = acquire_mutex()
        if acquired is False:
            QMessageBox.warning(self, "Already Running",
                                "Another instance of TAILSCALE VPN Client is already running.")
            sys.exit(0)
        elif acquired is None:
            QMessageBox.critical(self, "Error", "Could not acquire system mutex.")
            sys.exit(1)

        # Tailscale check
        if not check_tailscale_installed():
            QMessageBox.critical(self, "Error",
                                 "Tailscale CLI not found. Please install Tailscale.")
            sys.exit(1)

        # Wire menu actions
        self._connect_menu_actions()

        # Load tabs
        self.tab_id_to_name = load_tab_names()
        if self.tab_id_to_name:
            self.next_tab_id = max(self.tab_id_to_name.keys()) + 1

        if not self.tab_id_to_name:
            QTimer.singleShot(100, self._prompt_for_first_tab_name)
        else:
            for tab_id in sorted(self.tab_id_to_name.keys()):
                self.add_new_tab(tab_name=self.tab_id_to_name[tab_id],
                                 existing_tab_id=tab_id)

        self.update_tab_states()

        # Restore last tab
        last_tab_id = load_last_selected_tab_id()
        if last_tab_id and last_tab_id in self.tabs:
            self.select_tab(last_tab_id)
        elif self.tabs:
            self.select_tab(sorted(self.tabs.keys())[0])

    # ------------------------------------------------------------------
    # Menu wiring
    # ------------------------------------------------------------------

    def _connect_menu_actions(self):
        ui = self.ui
        ui.actionExit.triggered.connect(self.on_close_app)
        ui.actionSettings.triggered.connect(self._show_settings)
        ui.actionAddProfile.triggered.connect(self.on_add_new_tab_click)
        ui.actionRemoveProfile.triggered.connect(self.remove_current_tab)
        ui.actionLightTheme.triggered.connect(lambda: self.change_theme("light"))
        ui.actionDarkTheme.triggered.connect(lambda: self.change_theme("dark"))
        ui.actionAbout.triggered.connect(self._show_about)
        ui.actionLicense.triggered.connect(self._show_license)
        ui.actionReadme.triggered.connect(self._show_readme)

        # Dynamic global logs menu — populated just before it's shown
        ui.menuGlobalLogs.aboutToShow.connect(self._populate_global_logs_menu)

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def change_theme(self, theme_name: str):
        self.current_theme_name = theme_name
        QApplication.instance().setStyleSheet(build_stylesheet(theme_name))
        settings = load_settings()
        settings["theme"] = theme_name
        save_settings(settings)

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def add_new_tab(self, tab_name: str, existing_tab_id: int = None):
        from pylogic.windows.tab_controller import TabController

        if existing_tab_id is None:
            new_tab_id = self.next_tab_id
            self.next_tab_id += 1
        else:
            new_tab_id = existing_tab_id

        try:
            os.makedirs(get_tab_dir(tab_name), exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Directory Error",
                                 f"Could not create directory:\n{e}")
            return

        tab_page = QWidget()
        self.tabWidget.addTab(tab_page, tab_name)

        controller = TabController(tab_page, self, new_tab_id, tab_name)
        self.tabs[new_tab_id]          = controller
        self.tab_id_to_name[new_tab_id] = tab_name

        save_tab_names(self.tab_id_to_name)
        self.tabWidget.setCurrentWidget(tab_page)
        self.update_tab_states()

    def select_tab(self, tab_id: int):
        if tab_id not in self.tab_id_to_name:
            return
        tab_name = self.tab_id_to_name[tab_id]
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == tab_name:
                self.tabWidget.setCurrentIndex(i)
                break

    def _prompt_for_first_tab_name(self):
        name, ok = QInputDialog.getText(
            self, "Enter Profile Name",
            "Please enter a PROFILE name for this connection:"
        )
        if not ok or not name.strip():
            QMessageBox.warning(self, "Input Error", "PROFILE Name cannot be empty.")
            QTimer.singleShot(100, self._prompt_for_first_tab_name)
            return
        name = name.strip()
        if name in self.tab_id_to_name.values():
            QMessageBox.warning(self, "Duplicate Name", "That PROFILE Name already exists.")
            QTimer.singleShot(100, self._prompt_for_first_tab_name)
            return
        try:
            os.makedirs(get_tab_dir(name), exist_ok=True)
            self.add_new_tab(tab_name=name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create directory:\n{e}")

    def on_add_new_tab_click(self):
        if len(self.tabs) >= MAX_TABS:
            QMessageBox.warning(self, "Tab Limit",
                                f"Maximum {MAX_TABS} profiles allowed.")
            return
        name, ok = QInputDialog.getText(
            self, "Add New Profile", "Enter a Profile Name:"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.tab_id_to_name.values():
            QMessageBox.warning(self, "Duplicate Name", "That name already exists.")
            return
        try:
            os.makedirs(get_tab_dir(name), exist_ok=True)
            self.add_new_tab(tab_name=name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create directory:\n{e}")

    def remove_current_tab(self):
        if not self.tabs:
            QMessageBox.information(self, "Info", "No profiles to remove.")
            return

        idx = self.tabWidget.currentIndex()
        current_tab_name = self.tabWidget.tabText(idx)
        current_tab_id   = next(
            (k for k, v in self.tab_id_to_name.items() if v == current_tab_name), None
        )

        if self.connected_tab_id == current_tab_id:
            QMessageBox.warning(self, "WARNING !",
                                f"Please logout from profile '{current_tab_name}' first.")
            return

        reply = QMessageBox.question(
            self, "Remove PROFILE",
            f"Remove profile '{current_tab_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            for fname in ("Tailscale_VPN_url", "Tailscale_VPN_key"):
                fpath = get_file_path(fname, current_tab_name)
                if os.path.exists(fpath):
                    os.remove(fpath)
            tab_dir = get_tab_dir(current_tab_name)
            if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                os.rmdir(tab_dir)
        except Exception as e:
            write_log(f"Error removing files: {e}", level="ERROR")

        self.tabWidget.removeTab(idx)
        if current_tab_id in self.tabs:
            del self.tabs[current_tab_id]
        if current_tab_id in self.tab_id_to_name:
            del self.tab_id_to_name[current_tab_id]
        save_tab_names(self.tab_id_to_name)
        write_log(f"Removed tab: '{current_tab_name}'", level="INFO")

        if not self.tabs:
            QTimer.singleShot(100, self._prompt_for_first_tab_name)

        self.update_tab_states()

    # ------------------------------------------------------------------
    # Connected-tab state tracking
    # ------------------------------------------------------------------

    def set_connected_tab(self, tab_id: int):
        self.connected_tab_id = tab_id
        self.update_tab_states()

    def clear_connected_tab(self):
        self.connected_tab_id = None
        self.update_tab_states()

    def update_tab_states(self):
        is_connected = self.connected_tab_id is not None
        self.ui.actionAddProfile.setEnabled(not is_connected)

    # ------------------------------------------------------------------
    # Dialog launchers
    # ------------------------------------------------------------------

    def _show_settings(self):
        from pylogic.dialogs.settings_dlg import SettingsDialog
        dlg = SettingsDialog(parent=self)
        dlg.exec()

    def _show_about(self):
        from pylogic.dialogs.about_dlg import AboutDialog
        dlg = AboutDialog(parent=self)
        dlg.exec()

    def _show_license(self):
        from pylogic.dialogs.license_dlg import LicenseDialog
        if not hasattr(self, "_lic_dlg") or not self._lic_dlg.isVisible():
            self._lic_dlg = LicenseDialog(parent=self)
            self._lic_dlg.show()
        else:
            self._lic_dlg.activateWindow()

    def _show_readme(self):
        from pylogic.dialogs.readme_dlg import ReadmeDialog
        if not hasattr(self, "_readme_dlg") or not self._readme_dlg.isVisible():
            self._readme_dlg = ReadmeDialog(parent=self)
            self._readme_dlg.show()
        else:
            self._readme_dlg.activateWindow()

    def _populate_global_logs_menu(self):
        from pylogic.dialogs.log_viewer_dlg import LogViewerDialog
        menu = self.ui.menuGlobalLogs
        menu.clear()
        log_dir   = get_global_log_dir()
        if not os.path.exists(log_dir):
            menu.addAction("No logs found").setEnabled(False)
            return
        log_files = sorted(f for f in os.listdir(log_dir) if f.endswith(".log"))
        if not log_files:
            menu.addAction("No logs enabled/found").setEnabled(False)
            return
        for lf in log_files:
            action = QAction(lf, self)
            action.triggered.connect(
                lambda checked, f=lf: LogViewerDialog(self, f, f).show()
            )
            menu.addAction(action)

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def on_close_app(self):
        for tab in self.tabs.values():
            if tab.client.logged_in:
                QMessageBox.warning(self, "WARNING !",
                                    "Please logout from all connections first.")
                return

        # Save last selected tab
        idx = self.tabWidget.currentIndex()
        if idx >= 0:
            tab_name = self.tabWidget.tabText(idx)
            tab_id   = next(
                (k for k, v in self.tab_id_to_name.items() if v == tab_name), None
            )
            if tab_id is not None:
                save_last_selected_tab_id(tab_id)

        try:
            for tab_name in self.tab_id_to_name.values():
                tab_dir = get_tab_dir(tab_name)
                if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                    os.rmdir(tab_dir)
            if not self.tabs and os.path.exists(TAB_NAMES_FILE):
                os.remove(TAB_NAMES_FILE)
            release_mutex()
        except Exception as e:
            write_log(f"Error during app shutdown: {e}", level="ERROR")

        self.close()

    def closeEvent(self, event):
        # Intercept window-X click
        for tab in self.tabs.values():
            if tab.client.logged_in:
                QMessageBox.warning(self, "WARNING !",
                                    "Please logout from all connections first.")
                event.ignore()
                return
        release_mutex()
        event.accept()


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def start_gui():
    app_logger.info("Application starting up...")
    initialize_app_storage()

    app = QApplication.instance() or QApplication(sys.argv)

    # High-DPI support (Qt6 has it by default, but be explicit)
    app.setApplicationName("TAILSCALE VPN Client")

    window = AppController()
    window.show()

    app_logger.info("Launching GUI...")
    sys.exit(app.exec())
