# src/ui/components/node_dialog.py

import os
import json
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QComboBox, QListWidget, QListWidgetItem
from PySide6.QtCore import QProcess, Qt
from .simple_dialogs import BaseUiDialog

class NodeDialog(BaseUiDialog):
    def __init__(self, profile, manager, parent=None):
        super().__init__("node.ui", parent)
        self.setFixedSize(700, 420)
        self.profile = profile
        self.manager = manager
        self.setWindowTitle(f"Advanced Options: {profile.name}")

        # Map peer exit nodes to their advertised subnet routes for real-time suggestions
        self.exit_node_routes_map = {}

        # Access native widgets through self.ui
        self.comboBoxExitNode = self.ui.findChild(QComboBox, "comboBoxExitNode")
        self.lineEditRoutes = self.ui.findChild(QLineEdit, "lineEditRoutes")
        self.lineEditHostname = self.ui.findChild(QLineEdit, "lineEditHostname")
        self.listNativeSwitch = self.ui.findChild(QListWidget, "listNativeSwitch")
        from PySide6.QtWidgets import QCheckBox
        self.chkSSH = self.ui.findChild(QCheckBox, "chkSSH")
        self.chkAcceptDNS = self.ui.findChild(QCheckBox, "chkAcceptDNS")
        self.chkAllowLAN = self.ui.findChild(QCheckBox, "chkAllowLAN")
        self.chkDisableSNAT = self.ui.findChild(QCheckBox, "chkDisableSNAT")
        self.chkDnsFallback = self.ui.findChild(QCheckBox, "chkDnsFallback")
        self.chkForceReset = self.ui.findChild(QCheckBox, "chkForceReset")
        self.chkAdvertiseExitNode = self.ui.findChild(QCheckBox, "chkAdvertiseExitNode")
        self.chkShieldsUp = self.ui.findChild(QCheckBox, "chkShieldsUp")
        self.chkForceReauth = self.ui.findChild(QCheckBox, "chkForceReauth")
        self.lineEditTags = self.ui.findChild(QLineEdit, "lineEditTags")
        self.lineEditEmergencyIp = self.ui.findChild(QLineEdit, "lineEditEmergencyIp")
        self.btnSave = self.ui.findChild(QPushButton, "btnSave")
        self.btnCancel = self.ui.findChild(QPushButton, "btnCancel")
        self.chkAutoPopulate = self.ui.findChild(QCheckBox, "chkAutoPopulate")
        
        if self.chkAutoPopulate:
            self.chkAutoPopulate.stateChanged.connect(self._on_auto_populate_changed)

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

        if self.lineEditHostname:
            self.lineEditHostname.setText(self.profile.hostname)
            self.lineEditHostname.setToolTip("Custom hostname to advertise for this device on the Tailnet.")

        if self.chkSSH:
            self.chkSSH.setChecked(self.profile.enable_ssh)
            self.chkSSH.setToolTip("Enable Tailscale SSH to allow remote access to this device without managing SSH keys.")

        if self.chkAcceptDNS:
            self.chkAcceptDNS.setChecked(self.profile.accept_dns)
            self.chkAcceptDNS.setToolTip("Accept DNS configuration provided by the Tailnet (CorpDNS).")

        if self.chkAllowLAN:
            self.chkAllowLAN.setChecked(self.profile.allow_lan)
            self.chkAllowLAN.setToolTip("Allow access to the local network when routing traffic through an exit node.")

        if self.chkDisableSNAT:
            self.chkDisableSNAT.setChecked(self.profile.disable_snat)
            self.chkDisableSNAT.setToolTip("Disable Source NAT (SNAT) for subnet routes. Traffic will appear with its original source IP.")

        if self.chkDnsFallback:
            global_fallback = getattr(self.manager.settings, 'global_dns_fallback', False)
            self.chkDnsFallback.setChecked(self.profile.enable_dns_fallback or global_fallback)
            self.chkDnsFallback.setToolTip("Fallback to public DNS (e.g., 8.8.8.8) if the Tailnet DNS fails to resolve.")

        if self.chkForceReset:
            self.chkForceReset.setChecked(getattr(self.profile, 'force_reset', False))
            self.chkForceReset.setToolTip("Force reset Tailscale settings (--reset) when connecting to clear stuck configurations.")

        if self.chkAdvertiseExitNode:
            self.chkAdvertiseExitNode.setChecked(getattr(self.profile, 'advertise_exit_node', False))
            self.chkAdvertiseExitNode.setToolTip("Advertise this device as an exit node, allowing other devices on the Tailnet to route their internet traffic through it.")

        if self.chkShieldsUp:
            self.chkShieldsUp.setChecked(getattr(self.profile, 'shields_up', False))
            self.chkShieldsUp.setToolTip("Block incoming connections to this device, even from other devices on the Tailnet.")

        if self.chkForceReauth:
            self.chkForceReauth.setChecked(getattr(self.profile, 'force_reauth', False))
            self.chkForceReauth.setToolTip("Force re-authentication with the login server when connecting.")

        if self.lineEditTags:
            self.lineEditTags.setText(getattr(self.profile, 'advertise_tags', ""))
            self.lineEditTags.setToolTip("A comma-separated list of ACL tags to advertise for this device (e.g., tag:server, tag:prod).")
            
        if self.lineEditEmergencyIp:
            self.lineEditEmergencyIp.setText(self.profile.last_known_ip)
            self.lineEditEmergencyIp.setReadOnly(True)
            self.lineEditEmergencyIp.setToolTip("The last known Tailscale IP address for this profile. Useful for emergencies if DNS is broken.")

        # Asynchronously fetch status and populate exit nodes
        self._fetch_active_status()
        self._fetch_active_prefs()

    def _on_auto_populate_changed(self, state):
        if state == Qt.Checked.value or state == Qt.Checked:
            self._fetch_active_status()
            self._fetch_active_prefs()

    def _fetch_active_prefs(self):
        """Fetches the live preferences from Tailscale to auto-populate the advanced options."""
        from src.core.tailscale import get_tailscale_path
        self.prefs_proc = QProcess(self)
        
        def on_prefs_finished(*args):
            output = self.prefs_proc.readAllStandardOutput().data().decode().strip()
            if not output: return
            
            # Don't auto-populate if the user disabled it
            if self.chkAutoPopulate and not self.chkAutoPopulate.isChecked():
                return
                
            try:
                import json
                prefs = json.loads(output)
                
                # Auto-populate UI from live daemon config (preferring live config over profile config if active)
                if self.chkSSH and prefs.get("RunSSH"):
                    self.chkSSH.setChecked(True)
                if self.chkAcceptDNS and prefs.get("CorpDNS"):
                    self.chkAcceptDNS.setChecked(True)
                if self.chkAllowLAN and prefs.get("ExitNodeAllowLANAccess"):
                    self.chkAllowLAN.setChecked(True)
                if self.chkDisableSNAT and prefs.get("NoSNAT"):
                    self.chkDisableSNAT.setChecked(True)
                if self.chkShieldsUp and prefs.get("ShieldsUp"):
                    self.chkShieldsUp.setChecked(True)
                    
                # Exit nodes are advertised by routing 0.0.0.0/0
                routes = prefs.get("AdvertiseRoutes") or []
                if self.chkAdvertiseExitNode and ("0.0.0.0/0" in routes or "::/0" in routes):
                    self.chkAdvertiseExitNode.setChecked(True)
                    
                # Tags
                tags = prefs.get("AdvertiseTags") or []
                if self.lineEditTags and tags:
                    self.lineEditTags.setText(",".join(tags))
                    
                # Hostname override
                hostname = prefs.get("Hostname")
                if self.lineEditHostname and hostname:
                    self.lineEditHostname.setText(hostname)
                    
                # Auto-resolve Emergency IP from ControlURL if blank
                control_url = prefs.get("ControlURL")
                if control_url and not self.profile.last_known_ip and self.lineEditEmergencyIp:
                    import socket
                    from urllib.parse import urlparse
                    try:
                        domain = urlparse(control_url).hostname
                        if domain:
                            ip = socket.gethostbyname(domain)
                            if ip:
                                self.lineEditEmergencyIp.setText(ip)
                                self.lineEditEmergencyIp.setPlaceholderText("Resolved from live Control URL!")
                    except Exception as res_err:
                        print("DEBUG [node_dialog]: Could not resolve ControlURL IP:", res_err)
                    
            except Exception as e:
                print("DEBUG [node_dialog]: Exception parsing prefs:", e)
                
        self.prefs_proc.finished.connect(on_prefs_finished)
        self.prefs_proc.start(get_tailscale_path(), ["debug", "prefs"])

    def _fetch_active_status(self):
        self.status_proc = QProcess(self)
        
        def on_finished(*args):
            output = self.status_proc.readAllStandardOutput().data().decode().strip()
            print("DEBUG [node_dialog]: tailscale status output length:", len(output))
            if self.comboBoxExitNode:
                self.comboBoxExitNode.setPlaceholderText("Select exit node or type custom...")
            
            try:
                data = json.loads(output)
                exit_nodes = []
                active_system_exit_node = ""
                
                # Parse exit nodes and map their subnet routes
                peers = data.get("Peer") or {}
                for peer_id, peer_info in peers.items():
                    # Parse primary subnet routes advertised by peer
                    allowed_ips = peer_info.get("AllowedIPs") or []
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
                if not self.profile.routes and self.lineEditRoutes and self.chkAutoPopulate and self.chkAutoPopulate.isChecked():
                    self_data = data.get("Self") or {}
                    local_routes = self_data.get("PrimaryRoutes") or []
                    local_subnets = []
                    for route_info in local_routes:
                        route = route_info.get("Proto", "") if isinstance(route_info, dict) else str(route_info)
                        if "/" in route and not route.endswith("/32"):
                            local_subnets.append(route)
                    if local_subnets:
                        self.lineEditRoutes.setText(",".join(local_subnets))
                        self.lineEditRoutes.setPlaceholderText("Detected from active connection!")

                # Auto-populate Hostname if blank
                if not self.profile.hostname and self.lineEditHostname and self.chkAutoPopulate and self.chkAutoPopulate.isChecked():
                    self_data = data.get("Self") or {}
                    ts_hostname = self_data.get("HostName")
                    if ts_hostname:
                        self.lineEditHostname.setText(ts_hostname)
                        self.lineEditHostname.setPlaceholderText("Detected from active connection!")

            except Exception as e:
                print("DEBUG [node_dialog]: Exception parsing status:", e)
                
        self.status_proc.finished.connect(on_finished)
        self.status_proc.errorOccurred.connect(lambda e: print("DEBUG [node_dialog] QProcess errorOccurred:", e))
        self.status_proc.readyReadStandardError.connect(lambda: print("DEBUG [node_dialog] stderr:", self.status_proc.readAllStandardError().data().decode()))
        
        from src.core.tailscale import get_tailscale_path
        ts_path = get_tailscale_path()
        print("DEBUG [node_dialog]: Starting QProcess with path:", ts_path)
        self.status_proc.start(ts_path, ["status", "--json"])

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
        hostname = self.lineEditHostname.text().strip() if self.lineEditHostname else ""

        self.profile.exit_node = exit_node
        self.profile.routes = routes
        self.profile.hostname = hostname
        self.profile.enable_ssh = self.chkSSH.isChecked() if self.chkSSH else False
        self.profile.accept_dns = self.chkAcceptDNS.isChecked() if self.chkAcceptDNS else False
        self.profile.allow_lan = self.chkAllowLAN.isChecked() if self.chkAllowLAN else False
        self.profile.disable_snat = self.chkDisableSNAT.isChecked() if self.chkDisableSNAT else False
        self.profile.enable_dns_fallback = self.chkDnsFallback.isChecked() if self.chkDnsFallback else False
        self.profile.force_reset = self.chkForceReset.isChecked() if self.chkForceReset else False
        self.profile.advertise_exit_node = self.chkAdvertiseExitNode.isChecked() if self.chkAdvertiseExitNode else False
        self.profile.shields_up = self.chkShieldsUp.isChecked() if self.chkShieldsUp else False
        self.profile.force_reauth = self.chkForceReauth.isChecked() if self.chkForceReauth else False
        self.profile.advertise_tags = self.lineEditTags.text().strip() if self.lineEditTags else ""

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
