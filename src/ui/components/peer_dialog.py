import os
from PySide6.QtWidgets import QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QMenu
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication
from .simple_dialogs import BaseUiDialog

class PeerListDialog(BaseUiDialog):
    def __init__(self, ts_manager, parent=None):
        super().__init__("peer_list.ui", parent)
        self.ts_manager = ts_manager
        self.setFixedSize(620, 480)
        
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
        
        # Configure Table Headers
        if self.tablePeers:
            self.tablePeers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        
        # Parse Peer Dictionary from Tailscale Status JSON
        peer_dict = raw_data.get("Peer", {})
        if not peer_dict:
            self.tablePeers.setRowCount(1)
            self.tablePeers.setColumnCount(4)
            item = QTableWidgetItem("No peers found or disconnected. Connect to view peers.")
            item.setFlags(Qt.ItemIsEnabled)
            self.tablePeers.setItem(0, 0, item)
            if self.labelPeerCount:
                self.labelPeerCount.setText("Total Devices: 0")
            return
            
        self.tablePeers.setColumnCount(4)
        self.tablePeers.setRowCount(len(peer_dict))
        
        for idx, (peer_key, peer_info) in enumerate(peer_dict.items()):
            # Resolve Hostname
            dns_name = peer_info.get("DNSName", "").split('.')[0]
            host_name = dns_name or peer_info.get("HostName", "Unknown Device")
            
            # Resolve IP
            ips = peer_info.get("TailscaleIPs", [])
            ip_str = ips[0] if ips else "-"
            
            # Resolve OS
            os_name = peer_info.get("OS", "Unknown").capitalize()
            
            # Resolve Status
            active = peer_info.get("Active", False)
            online = peer_info.get("Online", False)
            if active:
                status = "🟢 Active"
            elif online:
                status = "🔵 Idle"
            else:
                status = "⚪ Offline"
                
            # Populate Row Items
            item_host = QTableWidgetItem(host_name)
            item_ip = QTableWidgetItem(ip_str)
            item_os = QTableWidgetItem(os_name)
            item_status = QTableWidgetItem(status)
            
            for item in [item_host, item_ip, item_os, item_status]:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                
            self.tablePeers.setItem(idx, 0, item_host)
            self.tablePeers.setItem(idx, 1, item_ip)
            self.tablePeers.setItem(idx, 2, item_os)
            self.tablePeers.setItem(idx, 3, item_status)
            
        if self.labelPeerCount:
            self.labelPeerCount.setText(f"Total Devices: {len(peer_dict)}")
            
        # Run filter in case a search was already typed
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
                
            match = (query in item_host.text().lower() or 
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
