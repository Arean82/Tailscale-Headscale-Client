# src/ui/components/node_dialog.py

import os
import json
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QComboBox
from PySide6.QtCore import QProcess
from .simple_dialogs import BaseUiDialog

class NodeDialog(BaseUiDialog):
    def __init__(self, profile, manager, parent=None):
        super().__init__("node.ui", parent)
        self.setFixedSize(380, 190)
        self.profile = profile
        self.manager = manager
        self.setWindowTitle(f"Advanced Options: {profile.name}")

        # Find the placeholder lineEditExitNode
        self.lineEditExitNode = self.ui.findChild(QLineEdit, "lineEditExitNode")
        self.lineEditRoutes = self.ui.findChild(QLineEdit, "lineEditRoutes")
        self.lineEditNativeProfile = self.ui.findChild(QLineEdit, "lineEditNativeProfile")

        # Dynamically create an editable QComboBox for Exit Nodes
        self.comboBoxExitNode = QComboBox(self)
        self.comboBoxExitNode.setEditable(True)
        self.comboBoxExitNode.setPlaceholderText("Searching for exit nodes...")

        # Swap lineEditExitNode with comboBoxExitNode in the grid layout programmatically
        if self.lineEditExitNode:
            grid = self.lineEditExitNode.parent().layout()
            if grid:
                grid.replaceWidget(self.lineEditExitNode, self.comboBoxExitNode)
                self.lineEditExitNode.hide()
                self.lineEditExitNode.deleteLater()

        # Set initial values
        if self.profile.exit_node:
            self.comboBoxExitNode.setEditText(self.profile.exit_node)
            
        if self.lineEditRoutes:
            self.lineEditRoutes.setText(self.profile.routes)

        if self.lineEditNativeProfile:
            self.lineEditNativeProfile.setText(self.profile.native_profile)

        # Inject Save & Cancel buttons dynamically at the bottom
        btn_layout = QHBoxLayout()
        self.btnSave = QPushButton("Save", self)
        self.btnSave.setStyleSheet("""
            QPushButton { 
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #15803d);
                color: white; font-weight: bold; border-radius: 6px; padding: 6px; border: 1px solid #166534;
            }
            QPushButton:hover { 
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #16a34a);
            }
        """)
        self.btnCancel = QPushButton("Cancel", self)
        self.btnCancel.setStyleSheet("""
            QPushButton { 
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4b5563, stop:1 #1f2937);
                color: white; font-weight: bold; border-radius: 6px; padding: 6px; border: 1px solid #111827;
            }
            QPushButton:hover { 
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6b7280, stop:1 #374151);
            }
        """)

        btn_layout.addWidget(self.btnSave)
        btn_layout.addWidget(self.btnCancel)

        # Get main gridLayout of TabWidget inside node.ui and add our button layout at row 1
        layout = self.ui.layout()
        if layout:
            layout.addLayout(btn_layout, 1, 0, 1, 2)

        self.btnSave.clicked.connect(self._save_settings)
        self.btnCancel.clicked.connect(self.reject)

        # Asynchronously fetch available exit nodes and advertised routes on load
        self._fetch_active_status()

    def _fetch_active_status(self):
        self.status_proc = QProcess(self)
        
        def on_finished():
            output = self.status_proc.readAllStandardOutput().data().decode().strip()
            self.comboBoxExitNode.setPlaceholderText("Select exit node or type custom...")
            
            try:
                data = json.loads(output)
                
                # 1. Parse exit nodes from peers
                exit_nodes = []
                active_system_exit_node = ""
                peers = data.get("Peer", {})
                for peer_id, peer_info in peers.items():
                    if peer_info.get("ExitNodeOption", False):
                        name = peer_info.get("HostName", "")
                        if name:
                            exit_nodes.append(name)
                    # Detect if this peer is the currently active exit node for this machine
                    if peer_info.get("ExitNode", False):
                        active_system_exit_node = peer_info.get("HostName", "")
                
                # Deduplicate and sort
                exit_nodes = sorted(list(set(exit_nodes)))
                
                # Populate combobox
                self.comboBoxExitNode.clear()
                self.comboBoxExitNode.addItem("") # Default empty option
                for node in exit_nodes:
                    self.comboBoxExitNode.addItem(node)
                
                # Restore original configured value or pre-select active system exit node
                default_val = self.profile.exit_node or active_system_exit_node
                if default_val:
                    index = self.comboBoxExitNode.findText(default_val)
                    if index >= 0:
                        self.comboBoxExitNode.setCurrentIndex(index)
                    else:
                        self.comboBoxExitNode.setEditText(default_val)
                        
                # 2. Detect and prepopulate subnet routes if currently blank
                if not self.profile.routes and self.lineEditRoutes:
                    # Check if local node is currently advertising any routes
                    local_routes = data.get("Self", {}).get("PrimaryRoutes", [])
                    # Filter for subnet routes (e.g., contains '/' and not a single host /32)
                    subnets = []
                    for route_info in local_routes:
                        route = route_info.get("Proto", "")
                        if "/" in route and not route.endswith("/32"):
                            subnets.append(route)
                    
                    if subnets:
                        self.lineEditRoutes.setText(",".join(subnets))
                        self.lineEditRoutes.setPlaceholderText("Detected from active connection!")
                        
            except Exception as e:
                # Silently fail if tailscale is offline, keeping the editable field available
                pass
                
        self.status_proc.finished.connect(on_finished)
        self.status_proc.start("tailscale", ["status", "--json"])

    def _save_settings(self):
        exit_node = self.comboBoxExitNode.currentText().strip()
        routes = self.lineEditRoutes.text().strip() if self.lineEditRoutes else ""
        native_profile = self.lineEditNativeProfile.text().strip() if self.lineEditNativeProfile else ""

        self.profile.exit_node = exit_node
        self.profile.routes = routes
        self.profile.native_profile = native_profile
        self.manager.save_profiles()

        QMessageBox.information(
            self, "Settings Saved",
            f"Advanced options for profile '{self.profile.name}' have been saved successfully!"
        )
        self.accept()
