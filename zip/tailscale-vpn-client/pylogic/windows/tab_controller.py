# pylogic/windows/tab_controller.py
# PySide6 port of gui/gui_tabs.py
# Loads pygui/windows/tab_widget.ui and wires all VPN connect/disconnect logic.
# All cross-thread UI updates go through Qt signals.

import os
import threading
import time
import webbrowser

from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Qt, Signal, QObject, QTimer

from pylogic.ui_helpers import load_ui, add_tooltip, format_bytes
from pylogic.tailscale_client import TailscaleClient
from pylogic.sso import run_sso_login

from logic.vpn_logic import (
    get_auth_mode, is_sso_mode,
    save_url, save_key,
    load_saved_url, load_saved_key,
    write_profile_log, get_file_path,
)
from logic.net_stats import get_tailscale_stats
from logic.statuscheck import wait_until_connected
from logic import db_manager
from logic.logger import app_logger


# ---------------------------------------------------------------------------
# Qt signal bridge — lets worker threads safely call back into the GUI thread
# ---------------------------------------------------------------------------

class _Signals(QObject):
    status_changed    = Signal(str, str)   # text, colour
    progress_update   = Signal(str, int)   # message, step
    traffic_update    = Signal(str)        # traffic label text
    show_popup        = Signal(str, str)   # title, message
    post_connect      = Signal()
    post_disconnect   = Signal()
    post_logout       = Signal()
    notify_logged_out = Signal()


# ---------------------------------------------------------------------------
# TabController
# ---------------------------------------------------------------------------

class TabController(QWidget):
    def __init__(self, parent_page: QWidget, app_controller, tab_id: int, tab_name: str):
        super().__init__(parent_page)

        self.app_instance = app_controller
        self.tab_id       = tab_id
        self.tab_name     = tab_name

        # Load UI into the parent page's layout
        from PySide6.QtWidgets import QVBoxLayout
        self.ui = load_ui("pygui/windows/tab_widget.ui", parent=self)
        layout  = QVBoxLayout(parent_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        parent_page.setLayout(layout)

        # Convenience references to widgets
        self.lineEditUrl          = self.ui.lineEditUrl
        self.labelStatus          = self.ui.labelStatus
        self.btnChangeCredentials = self.ui.btnChangeCredentials
        self.btnVpnAction         = self.ui.btnVpnAction
        self.btnShowStats         = self.ui.btnShowStats
        self.labelTraffic         = self.ui.labelTraffic

        # Pre-fill saved values
        self.lineEditUrl.setText(load_saved_url(tab_name))

        # Signals bridge
        self._sig = _Signals()
        self._sig.status_changed.connect(self._on_status_changed)
        self._sig.progress_update.connect(self._on_progress_update)
        self._sig.traffic_update.connect(self.labelTraffic.setText)
        self._sig.show_popup.connect(self._on_show_popup)
        self._sig.post_connect.connect(self._post_connect_ui)
        self._sig.post_disconnect.connect(self._post_disconnect_ui)
        self._sig.post_logout.connect(self._post_logout_ui)
        self._sig.notify_logged_out.connect(self._notify_app_logged_out)

        # Tooltips
        add_tooltip(self.lineEditUrl,          "Enter your VPN URL (e.g. https://vpn.example.com)")
        add_tooltip(self.btnChangeCredentials, "Change VPN Settings")
        add_tooltip(self.btnShowStats,         "View Network stats")
        add_tooltip(self.labelStatus,          "VPN connection status")
        add_tooltip(self.labelTraffic,         "Live traffic data (updated every 3 seconds)")
        add_tooltip(self.btnVpnAction,         "Connect to VPN")

        # Traffic monitoring
        self.prev_stats  = None
        self._monitoring = False

        # Progress popup
        self._progress_popup = None

        # TailscaleClient
        self.client = TailscaleClient(
            output_callback=self._print_output,
            status_callback=lambda t, c: self._sig.status_changed.emit(t, c),
            connected_callback=lambda: self._sig.post_connect.emit(),
            logged_out_callback=lambda: self._sig.notify_logged_out.emit(),
            post_disconnect_callback=lambda: self._sig.post_disconnect.emit(),
            post_logout_callback=lambda: self._sig.post_logout.emit(),
            progress_callback=lambda m, s: self._sig.progress_update.emit(m, s),
            message_popup_callback=lambda t, m: self._sig.show_popup.emit(t, m),
        )

        # Button connections
        self.btnVpnAction.clicked.connect(self.vpn_status_change)
        self.btnShowStats.clicked.connect(self.open_traffic_popup)
        self.btnChangeCredentials.clicked.connect(self.on_change_credentials_click)

        # Initial button state
        self._update_connect_button_state()
        self._update_change_credentials_button_state()

    # ------------------------------------------------------------------
    # Credential change popup
    # ------------------------------------------------------------------

    def on_change_credentials_click(self):
        from pylogic.dialogs.credentials_dlg import CredentialsDialog
        dlg = CredentialsDialog(
            parent=self,
            tab_name=self.tab_name,
            current_url=load_saved_url(self.tab_name),
            current_key=load_saved_key(self.tab_name),
            save_callback=self._save_credentials,
        )
        dlg.exec()

    def _save_credentials(self, url: str, key: str, mode: str):
        save_url(url, self.tab_name)
        save_key(key, self.tab_name)
        self.lineEditUrl.setText(url)
        try:
            mode_file = get_file_path("auth_mode", self.tab_name)
            with open(mode_file, "w") as f:
                f.write(mode)
        except Exception as e:
            app_logger.error(f"Error saving auth mode for '{self.tab_name}': {e}")
        self._update_connect_button_state()

    # ------------------------------------------------------------------
    # VPN connect / disconnect
    # ------------------------------------------------------------------

    def vpn_status_change(self):
        if self.client.connected:
            self._on_disconnect_and_cleanup()
        else:
            self._on_connect()

    def connect_vpn(self):
        """Public alias used by auto-connect logic."""
        if not self.client.connected:
            self._on_connect()

    def _on_connect(self):
        server = self.lineEditUrl.text().strip()
        key    = load_saved_key(self.tab_name)

        self.lineEditUrl.setEnabled(False)
        self.btnVpnAction.setEnabled(False)
        self._update_change_credentials_button_state()

        if is_sso_mode(self.tab_name):
            cmd = ["tailscale", "up", f"--login-server={server}", "--accept-routes"]

            def on_sso_connected():
                self.client.logged_in = True
                self.client.connected = True
                self._sig.post_connect.emit()
                self._sig.status_changed.emit("🟢 Connected", "green")

            run_sso_login(
                cmd,
                expected_url_part=server,
                output_callback=self._print_output,
                error_callback=lambda e: self._print_output(f"[SSO ERROR] {e}"),
                success_callback=on_sso_connected,
            )

            def poll_and_update():
                if wait_until_connected():
                    self.client.connected = True
                    self._sig.post_connect.emit()
                    self._sig.status_changed.emit("🟢 Connected", "green")
                else:
                    self._sig.status_changed.emit("❌ SSO login failed or timed out", "red")
                    self._sig.post_disconnect.emit()

            threading.Thread(target=poll_and_update, daemon=True).start()

        else:
            self.client.connect(key, server, self.tab_name)

        self.prev_stats  = get_tailscale_stats()
        self._monitoring = True
        threading.Thread(target=self._monitor_traffic_loop, daemon=True).start()

    def _on_disconnect_and_cleanup(self):
        self.btnVpnAction.setEnabled(False)
        self.client.disconnect(self.tab_name)

    # ------------------------------------------------------------------
    # UI state callbacks (always on the GUI thread via signals)
    # ------------------------------------------------------------------

    def _on_status_changed(self, text: str, color: str):
        self.labelStatus.setText(text)
        self.labelStatus.setStyleSheet(f"color: {color};")
        if any(x in text.lower() for x in ["connected", "disconnected", "error", "failed"]):
            self.btnVpnAction.setEnabled(True)

    def _on_progress_update(self, message: str, step: int):
        from pylogic.dialogs.progress_dlg import ProgressWidget
        if self._progress_popup is None:
            self._progress_popup = ProgressWidget(parent=self.window())
        self._progress_popup.show_progress(message, step)

    def _on_show_popup(self, title: str, message: str):
        QMessageBox.information(self, title, message)

    def _post_connect_ui(self):
        self.btnVpnAction.setText("Logout")
        self.btnVpnAction.setObjectName("btn_disconnect")
        self.btnVpnAction.setStyleSheet(
            "background-color: #f44336; color: white; border: none; border-radius: 4px;"
        )
        self.btnVpnAction.setToolTip("Disconnect and Logout from VPN")
        self.lineEditUrl.setEnabled(False)
        self.app_instance.set_connected_tab(self.tab_id)
        self._update_change_credentials_button_state()

    def _post_disconnect_ui(self):
        self.btnVpnAction.setEnabled(True)
        self.lineEditUrl.setEnabled(True)
        if self.app_instance.connected_tab_id == self.tab_id:
            self.app_instance.clear_connected_tab()
        self._update_change_credentials_button_state()
        self.prev_stats  = None
        self._monitoring = False

    def _post_logout_ui(self):
        self.btnVpnAction.setText("Connect")
        self.btnVpnAction.setObjectName("btn_connect")
        self.btnVpnAction.setStyleSheet(
            "background-color: #4CAF50; color: white; border: none; border-radius: 4px;"
        )
        self.btnVpnAction.setToolTip("Connect to VPN")
        self.labelStatus.setText("🔴 Disconnected")
        self.labelStatus.setStyleSheet("color: red;")
        self.lineEditUrl.setEnabled(True)
        if self.app_instance.connected_tab_id == self.tab_id:
            self.app_instance.clear_connected_tab()
        self._update_change_credentials_button_state()

    def _notify_app_logged_out(self):
        self.app_instance.clear_connected_tab()
        self._post_logout_ui()

    # ------------------------------------------------------------------
    # Credential / button state helpers
    # ------------------------------------------------------------------

    def _update_connect_button_state(self):
        url = load_saved_url(self.tab_name)
        key = load_saved_key(self.tab_name)
        sso = is_sso_mode(self.tab_name)
        self.btnVpnAction.setEnabled(bool(url and (key or sso)))

    def _update_change_credentials_button_state(self):
        can_change = not self.client.connected and not self.client.logged_in
        self.btnChangeCredentials.setVisible(can_change)

    # ------------------------------------------------------------------
    # Output / logging
    # ------------------------------------------------------------------

    def _print_output(self, text: str):
        text = text.strip()
        if not text:
            return
        app_logger.debug(f"[{self.tab_name}] {text}")
        saved_url = load_saved_url(self.tab_name).strip()
        if saved_url and saved_url in text:
            try:
                webbrowser.open(text)
            except Exception as e:
                app_logger.error(f"Failed to open browser: {e}")

    # ------------------------------------------------------------------
    # Traffic stats popup
    # ------------------------------------------------------------------

    def open_traffic_popup(self):
        if not self.client.connected:
            QMessageBox.information(self, "VPN Status", "VPN is not connected.")
            return
        from pylogic.dialogs.traffic_dlg import TrafficDialog
        dlg = TrafficDialog(
            parent=self,
            prev_stats=self.prev_stats,
            profile_name=self.tab_name,
        )
        dlg.exec()
        self.prev_stats = get_tailscale_stats()

    # ------------------------------------------------------------------
    # Background traffic monitor
    # ------------------------------------------------------------------

    def _monitor_traffic_loop(self):
        while self._monitoring:
            stats = get_tailscale_stats()
            if stats and self.prev_stats:
                sent = stats.bytes_sent  - self.prev_stats.bytes_sent
                recv = stats.bytes_recv - self.prev_stats.bytes_recv
                self._sig.traffic_update.emit(
                    f"Traffic: Sent {format_bytes(sent)} / Received {format_bytes(recv)}"
                )
            time.sleep(3)
