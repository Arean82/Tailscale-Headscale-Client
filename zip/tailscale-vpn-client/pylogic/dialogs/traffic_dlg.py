# pylogic/dialogs/traffic_dlg.py
# PySide6 port of gui/traffic_popup.py

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt

from pylogic.ui_helpers import load_ui, center_window, format_bytes
from logic.net_stats import get_tailscale_stats
from logic import db_manager


class TrafficDialog(QDialog):
    def __init__(self, parent=None, prev_stats=None, profile_name=""):
        super().__init__(parent)

        self.prev_stats    = prev_stats
        self.profile_name  = profile_name

        self.ui = load_ui("pygui/dialogs/traffic.ui", parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowTitle("Traffic Stats")
        self.setFixedSize(260, 240)
        self.setWindowModality(Qt.ApplicationModal)

        if parent:
            center_window(parent, self)

        self.ui.btnClose.clicked.connect(self.accept)

        self._show_stats()

    # ------------------------------------------------------------------

    def _show_stats(self):
        current = get_tailscale_stats()

        if not current:
            self.ui.labelStats.setText("No traffic data available.")
            self.ui.labelDailyStats.setText("")
            return

        # Log current snapshot to DB
        db_manager.insert_traffic_data(
            self.profile_name, current.bytes_sent, current.bytes_recv
        )

        if not self.prev_stats:
            self.ui.labelStats.setText("No previous data to compare.")
            self.ui.labelDailyStats.setText("")
            return

        sent  = current.bytes_sent  - self.prev_stats.bytes_sent
        recv  = current.bytes_recv  - self.prev_stats.bytes_recv

        stats_text = (
            f"Sent (Current): {format_bytes(sent)}\n"
            f"Recv (Current): {format_bytes(recv)}\n"
            f"Total Sent    : {format_bytes(current.bytes_sent)}\n"
            f"Total Recv    : {format_bytes(current.bytes_recv)}"
        )
        self.ui.labelStats.setText(stats_text)

        daily_sent, daily_recv = db_manager.get_daily_total_traffic(self.profile_name)
        daily_text = (
            f"Daily Sent    : {format_bytes(daily_sent)}\n"
            f"Daily Recv    : {format_bytes(daily_recv)}"
        )
        self.ui.labelDailyStats.setText(daily_text)
