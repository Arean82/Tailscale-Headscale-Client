import os
import sys
import re
from PySide6.QtWidgets import QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QMenu, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize, QProcess
from PySide6.QtGui import QAction, QGuiApplication, QPainter, QPen, QColor
from .simple_dialogs import BaseUiDialog
from ...core.tailscale import get_tailscale_path

class PeerNameBadgeWidget(QWidget):
    def __init__(self, host_name, username="", tags=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # 1. Hostname Label (Theme-Safe)
        self.lbl_host = QLabel(host_name, self)
        self.lbl_host.setStyleSheet("font-family: 'Segoe UI'; font-weight: 500;")
        layout.addWidget(self.lbl_host)
        
        # 2. Namespace / Owner User Badge (Blue capsule pill)
        if username:
            short_user = username.split('@')[0]
            lbl_user = QLabel(short_user, self)
            lbl_user.setStyleSheet(
                "background-color: #2563eb; color: #ffffff; padding: 1px 6px; "
                "border-radius: 4px; font-size: 10px; font-weight: bold; font-family: 'Segoe UI';"
            )
            layout.addWidget(lbl_user)
            
        # 3. ACL Tag Badges (Purple capsule pill)
        if tags:
            for tag in tags:
                clean_tag = tag.replace("tag:", "")
                lbl_tag = QLabel(clean_tag, self)
                lbl_tag.setStyleSheet(
                    "background-color: #7c3aed; color: #ffffff; padding: 1px 6px; "
                    "border-radius: 4px; font-size: 10px; font-weight: bold; font-family: 'Segoe UI';"
                )
                layout.addWidget(lbl_tag)
                
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    def sizeHint(self):
        # Allow the table auto-resizer to reserve comfortable space
        return QSize(220, 28)


class LatencySparklineWidget(QWidget):
    def __init__(self, parent=None, is_active=True, is_online=True, peer_ip=None):
        super().__init__(parent)
        self.is_active = is_active
        self.is_online = is_online
        self.peer_ip = peer_ip

        # No baseline values — graph stays empty until real ping data arrives.
        # 0 means "no data yet" and is excluded from rendering.
        self.values = []

        if self.is_online and self.peer_ip:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._run_ping)
            self.timer.start(2000)
            # Kick off the first ping immediately instead of waiting 2s
            QTimer.singleShot(0, self._run_ping)

    def _run_ping(self):
        """Spawn a non-blocking tailscale ping against this peer's IP."""
        if not self.peer_ip:
            return
        self.proc = QProcess(self)
        self.proc.finished.connect(self._on_ping_finished)
        # --timeout=2s keeps the subprocess short; until=false means it stops
        # after the first successful reply (matches existing 2s timer cadence).
        self.proc.start(get_tailscale_path(), ["ping", "--timeout=2s", "--until=false", self.peer_ip])

    def _on_ping_finished(self, exit_code, exit_status):
        output = self.proc.readAllStandardOutput().data().decode(errors="ignore")
        # Output line looks like:
        #   pong from mailserver-01 via 1.2.3.4:5 in 23ms
        # Pick the first 'in <n>ms' we can find.
        match = re.search(r'in\s+(\d+)\s*ms', output)
        if match:
            self.values.append(int(match.group(1)))
            if len(self.values) > 12:
                self.values.pop(0)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        if not self.is_online:
            painter.setPen(QPen(QColor("#6b7280"), 1.5, Qt.DashLine))
            painter.drawLine(10, height // 2, width - 60, height // 2)

            painter.setPen(QPen(QColor("#9ca3af"), 1))
            text_rect = self.rect()
            text_rect.setLeft(width - 55)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, "Offline")
            return

        # No data yet — show placeholder instead of a misleading flat line
        if not self.values:
            painter.setPen(QPen(QColor("#6b7280"), 1.5, Qt.DashLine))
            painter.drawLine(10, height // 2, width - 60, height // 2)

            painter.setPen(QPen(QColor("#9ca3af"), 1))
            text_rect = self.rect()
            text_rect.setLeft(width - 55)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, "...")
            return

        # Scaling bounds
        max_val = max(self.values) if max(self.values) > 0 else 1
        avg_val = sum(self.values) / len(self.values)

        if avg_val < 32:
            color = QColor("#10b981")  # Vibrant Green
        elif avg_val < 70:
            color = QColor("#f59e0b")  # Warm Amber
        else:
            color = QColor("#ef4444")  # Alert Red

        pen = QPen(color, 2, Qt.SolidLine)
        painter.setPen(pen)

        points = []
        step = (width - 70) / max(11, len(self.values) - 1)
        for i, val in enumerate(self.values):
            x = 10 + i * step
            y = height - 8 - ((val / 80.0) * (height - 16))
            y = max(4, min(height - 4, y))
            points.append((x, y))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        last_x, last_y = points[-1]
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(last_x - 3, last_y - 3, 6, 6)

        painter.setPen(QPen(QColor("#d1d5db"), 1))
        text_rect = self.rect()
        text_rect.setLeft(width - 55)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, f"{self.values[-1]}ms")

    def sizeHint(self):
        # Give sparkline canvas and latency text ample rendering room
        return QSize(160, 28)


class PeerListDialog(BaseUiDialog):
    def __init__(self, ts_manager, parent=None):
        super().__init__("peer_list.ui", parent)
        self.ts_manager = ts_manager
        self.setFixedSize(680, 480)  # Expanded slightly to give headers and metrics perfect padding
        
        # Resolve UI elements
        self.lineEditSearch = self.ui.findChild(QLineEdit, "lineEditSearch")
        self.btnRefresh = self.ui.findChild(QPushButton, "btnRefresh")
        self.tablePeers = self.ui.findChild(QTableWidget, "tablePeers")
        self.labelPeerCount = self.ui.findChild(QLabel, "labelPeerCount")
        
        # Connect signals
        if self.lineEditSearch:
            self.lineEditSearch.textChanged.connect(self._filter_peers)
        if self.btnRefresh:
            self.btnRefresh.clicked.connect(self._trigger_refresh)
            
        self.ts_manager.connection_status_changed.connect(self._on_status_updated)
        
        # Configure Table Headers with Smart Resize Behaviors
        if self.tablePeers:
            self.tablePeers.setWordWrap(True)
            self.tablePeers.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.tablePeers.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            header = self.tablePeers.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)            # Hostname stretches
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)   # IP matches content
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # OS matches content
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # Status matches content
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Path matches content
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)   # Sparkline matches hint
            
            self.tablePeers.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tablePeers.customContextMenuRequested.connect(self._show_context_menu)
            
        # Initial Population
        self._populate_peers()

    def _trigger_refresh(self):
        if self.btnRefresh:
            self.btnRefresh.setText("Refreshing...")
            self.btnRefresh.setEnabled(False)
        self.ts_manager.check_status()

    def _on_status_updated(self, is_connected, status_text):
        if self.btnRefresh:
            self.btnRefresh.setText("Refresh")
            self.btnRefresh.setEnabled(True)
        self._populate_peers()

    def _populate_peers(self):
        if not self.tablePeers:
            return
            
        self.tablePeers.setRowCount(0)
        
        cached_status = self.ts_manager.cache.get("status")
        raw_data = cached_status.get("raw_data", {}) if cached_status else {}

        # Top-level User map: {user_id_int: {LoginName, DisplayName, ...}}
        # Used to resolve each peer's numeric "User" field to a real username.
        user_map = raw_data.get("User", {}) or {}

        peer_dict = raw_data.get("Peer", {})
        if not peer_dict:
            self.tablePeers.setRowCount(1)
            self.tablePeers.setColumnCount(6)
            item = QTableWidgetItem("No peers found or disconnected. Connect to view peers.")
            item.setFlags(Qt.ItemIsEnabled)
            self.tablePeers.setItem(0, 0, item)
            if self.labelPeerCount:
                self.labelPeerCount.setText("Total Devices: 0")
            return
            
        self.tablePeers.setColumnCount(6)
        self.tablePeers.setRowCount(len(peer_dict))
        
        for idx, (peer_key, peer_info) in enumerate(peer_dict.items()):
            dns_name = peer_info.get("DNSName", "").split('.')[0]
            host_name = dns_name or peer_info.get("HostName", "Unknown Device")
            
            ips = peer_info.get("TailscaleIPs", [])
            ip_str = ips[0] if ips else "-"
            
            os_name = peer_info.get("OS", "Unknown").capitalize()
            
            active = peer_info.get("Active", False)
            online = peer_info.get("Online", False)
            if active:
                status = "🟢 Active"
            elif online:
                status = "🔵 Idle"
            else:
                status = "⚪ Offline"
                
            # Determine path (Direct vs Relayed)
            is_direct = peer_info.get("CurAddr", "") != ""
            relay_region = peer_info.get("Relay", "")
            if not online:
                path_text = "—"
            elif is_direct:
                path_text = "⚡ Direct"
            elif relay_region:
                path_text = f"☁️ Relay ({relay_region})"
            else:
                path_text = "☁️ Relay"

            # Keep text empty to completely block double-text drawing overlap!
            item_host = QTableWidgetItem("")
            # Store raw hostname inside Qt.UserRole so robust search filtering works perfectly!
            item_host.setData(Qt.UserRole, host_name)
            
            item_ip = QTableWidgetItem(ip_str)
            item_os = QTableWidgetItem(os_name)
            item_status = QTableWidgetItem(status)
            item_path = QTableWidgetItem(path_text)
            
            for item in [item_host, item_ip, item_os, item_status, item_path]:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                
            self.tablePeers.setItem(idx, 0, item_host)
            self.tablePeers.setItem(idx, 1, item_ip)
            self.tablePeers.setItem(idx, 2, item_os)
            self.tablePeers.setItem(idx, 3, item_status)
            self.tablePeers.setItem(idx, 4, item_path)
            
            # Create and Bind PeerNameBadgeWidget to column 0
            # peer_info["User"] is a numeric owner ID — resolve it via the
            # top-level User map to get a real LoginName (e.g. "alice@example.com").
            user_id = peer_info.get("User", "")
            user_info = user_map.get(user_id, {}) if user_id != "" else {}
            user_name = user_info.get("LoginName") or user_info.get("DisplayName") or ""
            tags_list = peer_info.get("Tags", []) or []
            badge_widget = PeerNameBadgeWidget(host_name, username=user_name, tags=tags_list, parent=self)
            self.tablePeers.setCellWidget(idx, 0, badge_widget)

            # Create and Bind Real-Time Sparkline Widget to column 5
            # Pass the peer's primary Tailscale IP so the widget can run real
            # tailscale ping commands instead of showing placeholder data.
            sparkline = LatencySparklineWidget(self, is_active=active, is_online=online, peer_ip=ip_str if ip_str != "-" else None)
            self.tablePeers.setCellWidget(idx, 5, sparkline)
            
        if self.labelPeerCount:
            self.labelPeerCount.setText(f"Total Devices: {len(peer_dict)}")
            
        self._filter_peers()

    def _filter_peers(self):
        if not self.tablePeers:
            return
            
        query = self.lineEditSearch.text().lower().strip() if self.lineEditSearch else ""
        visible_count = 0
        
        for row in range(self.tablePeers.rowCount()):
            item_host = self.tablePeers.item(row, 0)
            item_ip = self.tablePeers.item(row, 1)
            item_os = self.tablePeers.item(row, 2)
            
            if not item_host:
                continue
                
            # Retrieve search content from Qt.UserRole safely
            host_text = item_host.data(Qt.UserRole) or ""
            match = (query in host_text.lower() or 
                     (item_ip and query in item_ip.text().lower()) or 
                     (item_os and query in item_os.text().lower()))
                     
            if match or not query:
                self.tablePeers.setRowHidden(row, False)
                visible_count += 1
            else:
                self.tablePeers.setRowHidden(row, True)
                
        if self.labelPeerCount and query:
            self.labelPeerCount.setText(f"Filtered: {visible_count} of {self.tablePeers.rowCount()}")

    def _show_context_menu(self, position):
        if not self.tablePeers:
            return
            
        selected_ranges = self.tablePeers.selectedRanges()
        if not selected_ranges:
            return
            
        row = selected_ranges[0].topRow()
        item_ip = self.tablePeers.item(row, 1)
        if not item_ip or item_ip.text() == "-":
            return
            
        ip_addr = item_ip.text()
        
        menu = QMenu(self)
        copy_action = QAction("📋 Copy IP Address", self)
        copy_action.triggered.connect(lambda: QGuiApplication.clipboard().setText(ip_addr))
        menu.addAction(copy_action)
        
        menu.exec(self.tablePeers.viewport().mapToGlobal(position))

    def closeEvent(self, event):
        try:
            self.ts_manager.connection_status_changed.disconnect(self._on_status_updated)
        except Exception:
            pass
        super().closeEvent(event)
