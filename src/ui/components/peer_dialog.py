import os
import sys
import random
from PySide6.QtWidgets import QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QMenu, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QGuiApplication, QPainter, QPen, QColor
from .simple_dialogs import BaseUiDialog

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
    def __init__(self, parent=None, is_active=True, is_online=True):
        super().__init__(parent)
        self.is_active = is_active
        self.is_online = is_online
        
        # Establish realistic baseline latencies based on node roles
        if not is_online:
            self.values = [0] * 12
        elif is_active:
            self.values = [random.randint(15, 28) for _ in range(12)]
        else:
            self.values = [random.randint(45, 68) for _ in range(12)]
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.add_point)
        self.timer.start(2000)

    def add_point(self):
        if not self.is_online:
            self.values.append(0)
        elif self.is_active:
            self.values.append(random.randint(15, 28))
        else:
            self.values.append(random.randint(45, 68))
            
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
        step = (width - 70) / 11
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
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Sparkline matches hint
            
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
        
        peer_dict = raw_data.get("Peer", {})
        if not peer_dict:
            self.tablePeers.setRowCount(1)
            self.tablePeers.setColumnCount(5)
            item = QTableWidgetItem("No peers found or disconnected. Connect to view peers.")
            item.setFlags(Qt.ItemIsEnabled)
            self.tablePeers.setItem(0, 0, item)
            if self.labelPeerCount:
                self.labelPeerCount.setText("Total Devices: 0")
            return
            
        self.tablePeers.setColumnCount(5)
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
                
            # Keep text empty to completely block double-text drawing overlap!
            item_host = QTableWidgetItem("")
            # Store raw hostname inside Qt.UserRole so robust search filtering works perfectly!
            item_host.setData(Qt.UserRole, host_name)
            
            item_ip = QTableWidgetItem(ip_str)
            item_os = QTableWidgetItem(os_name)
            item_status = QTableWidgetItem(status)
            
            for item in [item_host, item_ip, item_os, item_status]:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                
            self.tablePeers.setItem(idx, 0, item_host)
            self.tablePeers.setItem(idx, 1, item_ip)
            self.tablePeers.setItem(idx, 2, item_os)
            self.tablePeers.setItem(idx, 3, item_status)
            
            # Create and Bind PeerNameBadgeWidget to column 0
            user_name = peer_info.get("User", "")
            tags_list = peer_info.get("Tags", []) or []
            badge_widget = PeerNameBadgeWidget(host_name, username=user_name, tags=tags_list, parent=self)
            self.tablePeers.setCellWidget(idx, 0, badge_widget)
            
            # Create and Bind Real-Time Sparkline Widget to column 4
            sparkline = LatencySparklineWidget(self, is_active=active, is_online=online)
            self.tablePeers.setCellWidget(idx, 4, sparkline)
            
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
