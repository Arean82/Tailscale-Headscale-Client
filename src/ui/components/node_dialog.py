# src/ui/components/node_dialog.py

import os
import json
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QComboBox, QListWidget, QListWidgetItem
from PySide6.QtCore import QProcess, Qt
from .simple_dialogs import BaseUiDialog

class NodeDialog(BaseUiDialog):
    def __init__(self, profile, manager, parent=None):
        super().__init__("node.ui", parent)
        self.setFixedSize(400, 380)
        self.profile = profile
        self.manager = manager
        self.setWindowTitle(f"Advanced Options: {profile.name}")

        # Map peer exit nodes to their advertised subnet routes for real-time suggestions
        self.exit_node_routes_map = {}

        # Access native widgets through self.ui
        self.comboBoxExitNode = self.ui.findChild(QComboBox, "comboBoxExitNode")
        self.lineEditRoutes = self.ui.findChild(QLineEdit, "lineEditRoutes")
        self.listNativeSwitch = self.ui.findChild(QListWidget, "listNativeSwitch")
        from PySide6.QtWidgets import QCheckBox
        self.chkSSH = self.ui.findChild(QCheckBox, "chkSSH")
        self.chkAcceptDNS = self.ui.findChild(QCheckBox, "chkAcceptDNS")
        self.btnSave = self.ui.findChild(QPushButton, "btnSave")
        self.btnCancel = self.ui.findChild(QPushButton, "btnCancel")

        # Style native Save & Cancel buttons
        if self.btnSave:
            self.btnSave.setStyleSheet("""
                QPushButton { 
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #15803d);
                    color: white; font-weight: bold; border-radius: 6px; padding: 6px 20px; border: 1px solid #166534;
                }
                QPushButton:hover { 
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #16a34a);
                }
            """)
            self.btnSave.clicked.connect(self._save_settings)

        if self.btnCancel:
            self.btnCancel.setStyleSheet("""
                QPushButton { 
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4b5563, stop:1 #1f2937);
                    color: white; font-weight: bold; border-radius: 6px; padding: 6px 20px; border: 1px solid #111827;
                }
                QPushButton:hover { 
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6b7280, stop:1 #374151);
                }
            """)
            self.btnCancel.clicked.connect(self.reject)

        # Style and populate listNativeSwitch
        if self.listNativeSwitch:
            self.listNativeSwitch.setStyleSheet("""
                QListWidget {
                    background-color: #1a1e2e;
                    border: 1px solid #3d4b7c;
                    border-radius: 6px;
                    color: white;
                    padding: 4px;
                }
                QListWidget::item {
                    padding: 4px;
                    color: white;
                }
                QListWidget::item:hover {
                    background-color: #374151;
                    border-radius: 4px;
                }
            """)
            for name, p in self.manager.profiles.items():
                item = QListWidgetItem(name, self.listNativeSwitch)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if p.is_native_switch else Qt.Unchecked)

        # Populate initial values
        if self.comboBoxExitNode:
            self.comboBoxExitNode.setPlaceholderText("Searching for exit nodes...")
            if self.profile.exit_node:
                self.comboBoxExitNode.setEditText(self.profile.exit_node)
            self.comboBoxExitNode.currentTextChanged.connect(self._on_exit_node_changed)

        if self.lineEditRoutes:
            self.lineEditRoutes.setText(self.profile.routes)

        if self.chkSSH:
            self.chkSSH.setChecked(self.profile.enable_ssh)

        if self.chkAcceptDNS:
            self.chkAcceptDNS.setChecked(self.profile.accept_dns)

        # Asynchronously fetch status and populate exit nodes
        self._fetch_active_status()

    def _fetch_active_status(self):
        self.status_proc = QProcess(self)
        
        def on_finished():
            output = self.status_proc.readAllStandardOutput().data().decode().strip()
            if self.comboBoxExitNode:
                self.comboBoxExitNode.setPlaceholderText("Select exit node or type custom...")
            
            try:
                data = json.loads(output)
                exit_nodes = []
                active_system_exit_node = ""
                
                # Parse exit nodes and map their subnet routes
                peers = data.get("Peer", {})
                for peer_id, peer_info in peers.items():
                    # Parse primary subnet routes advertised by peer
                    allowed_ips = peer_info.get("AllowedIPs", [])
                    subnets = [ip for ip in allowed_ips if "/" in ip and not ip.endswith("/32") and not ip.endswith("/128")]
                    
                    name = peer_info.get("HostName", "")
                    dns_name = peer_info.get("DNSName", "").split(".")[0]
                    
                    target_name = name or dns_name
                    if target_name:
                        if peer_info.get("ExitNodeOption", False):
                            exit_nodes.append(target_name)
                        if subnets:
                            self.exit_node_routes_map[target_name] = ",".join(subnets)
                    
                    if peer_info.get("ExitNode", False):
                        active_system_exit_node = target_name

                # Deduplicate and sort exit nodes
                exit_nodes = sorted(list(set(exit_nodes)))
                
                if self.comboBoxExitNode:
                    self.comboBoxExitNode.blockSignals(True)
                    self.comboBoxExitNode.clear()
                    self.comboBoxExitNode.addItem("") # Empty option
                    for node in exit_nodes:
                        self.comboBoxExitNode.addItem(node)
                    
                    default_val = self.profile.exit_node or active_system_exit_node
                    if default_val:
                        index = self.comboBoxExitNode.findText(default_val)
                        if index >= 0:
                            self.comboBoxExitNode.setCurrentIndex(index)
                        else:
                            self.comboBoxExitNode.setEditText(default_val)
                    self.comboBoxExitNode.blockSignals(False)
                    
                # Suggested local subnet routes if blank
                if not self.profile.routes and self.lineEditRoutes:
                    local_routes = data.get("Self", {}).get("PrimaryRoutes", [])
                    local_subnets = []
                    for route_info in local_routes:
                        route = route_info.get("Proto", "")
                        if "/" in route and not route.endswith("/32"):
                            local_subnets.append(route)
                    if local_subnets:
                        self.lineEditRoutes.setText(",".join(local_subnets))
                        self.lineEditRoutes.setPlaceholderText("Detected from active connection!")

            except Exception:
                pass
                
        self.status_proc.finished.connect(on_finished)
        self.status_proc.start("tailscale", ["status", "--json"])

    def _on_exit_node_changed(self, exit_node):
        """Intelligently auto-populate subnet routes when an exit node is selected."""
        exit_node = exit_node.strip()
        if exit_node in self.exit_node_routes_map:
            suggested_routes = self.exit_node_routes_map[exit_node]
            if self.lineEditRoutes and suggested_routes:
                self.lineEditRoutes.setText(suggested_routes)
                self.lineEditRoutes.setPlaceholderText("Auto-populated from selected exit node!")

    def _save_settings(self):
        exit_node = self.comboBoxExitNode.currentText().strip() if self.comboBoxExitNode else ""
        routes = self.lineEditRoutes.text().strip() if self.lineEditRoutes else ""

        self.profile.exit_node = exit_node
        self.profile.routes = routes
        self.profile.enable_ssh = self.chkSSH.isChecked() if self.chkSSH else False
        self.profile.accept_dns = self.chkAcceptDNS.isChecked() if self.chkAcceptDNS else False

        # Save checked profiles
        if self.listNativeSwitch:
            for i in range(self.listNativeSwitch.count()):
                item = self.listNativeSwitch.item(i)
                p_name = item.text()
                is_checked = item.checkState() == Qt.Checked
                if p_name in self.manager.profiles:
                    p = self.manager.profiles[p_name]
                    p.is_native_switch = is_checked
                    if is_checked:
                        p.native_profile = p_name

        self.manager.save_profiles()
        
        # Trigger tab refresh in main window
        if self.parent() and hasattr(self.parent(), "refresh_tabs"):
            self.parent().refresh_tabs()
            
        self.accept()
