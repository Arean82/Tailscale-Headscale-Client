# src/ui/components/node_dialog.py

import json
import logging

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from .simple_dialogs import BaseUiDialog

logger = logging.getLogger("TailscaleClient.UI.NodeDialog")


class NodeDialog(BaseUiDialog):
    def __init__(self, profile, manager, parent=None):
        super().__init__("node.ui", parent)
        self.setFixedSize(720, 420)
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
        self.chkForceReset = self.ui.findChild(QCheckBox, "chkForceReset")
        self.chkAdvertiseExitNode = self.ui.findChild(QCheckBox, "chkAdvertiseExitNode")
        self.chkShieldsUp = self.ui.findChild(QCheckBox, "chkShieldsUp")
        self.chkForceReauth = self.ui.findChild(QCheckBox, "chkForceReauth")
        self.lineEditTags = self.ui.findChild(QLineEdit, "lineEditTags")
        self.lineEditEmergencyIp = self.ui.findChild(QLineEdit, "lineEditEmergencyIp")
        self.btnSave = self.ui.findChild(QPushButton, "btnSave")
        self.btnCancel = self.ui.findChild(QPushButton, "btnCancel")
        self.chkAutoPopulate = self.ui.findChild(QCheckBox, "chkAutoPopulate")
        self.chkAcceptRoutes = self.ui.findChild(QCheckBox, "chkAcceptRoutes")
        self.chkUnattended = self.ui.findChild(QCheckBox, "chkUnattended")
        self.chkWebclient = self.ui.findChild(QCheckBox, "chkWebclient")
        self.chkAdvertiseConnector = self.ui.findChild(QCheckBox, "chkAdvertiseConnector")
        
        # Column 1 status value checkboxes
        self.chkAllowLANValue = self.ui.findChild(QCheckBox, "chkAllowLANValue")
        self.chkSSHValue = self.ui.findChild(QCheckBox, "chkSSHValue")
        self.chkAcceptRoutesValue = self.ui.findChild(QCheckBox, "chkAcceptRoutesValue")
        self.chkAcceptDNSValue = self.ui.findChild(QCheckBox, "chkAcceptDNSValue")
        self.chkShieldsUpValue = self.ui.findChild(QCheckBox, "chkShieldsUpValue")
        self.chkAdvertiseExitNodeValue = self.ui.findChild(QCheckBox, "chkAdvertiseExitNodeValue")
        self.chkDisableSNATValue = self.ui.findChild(QCheckBox, "chkDisableSNATValue")
        self.chkUnattendedValue = self.ui.findChild(QCheckBox, "chkUnattendedValue")
        self.chkWebclientValue = self.ui.findChild(QCheckBox, "chkWebclientValue")
        self.chkAdvertiseConnectorValue = self.ui.findChild(QCheckBox, "chkAdvertiseConnectorValue")
        self.lineEditExtraArgs = self.ui.findChild(QLineEdit, "lineEditExtraArgs")
        self.lineEditAcceptRisk = self.ui.findChild(QLineEdit, "lineEditAcceptRisk")

        # Accessibility (EN 301 549 11.2.1.1 / WCAG 1.1.1 Non-text Content)
        accessible_configs = [
            (self.comboBoxExitNode, "Exit Node Selector", "Select a remote peer device to route internet egress traffic through."),
            (self.lineEditRoutes, "Subnet Routes Input", "Comma-separated RFC 1918 subnets to advertise to the Tailnet."),
            (self.lineEditHostname, "Custom Hostname Override", "Overrides the machine name advertised to the coordination server."),
            (self.lineEditExtraArgs, "Extra Daemon Arguments", "Custom flags or arguments passed directly to tailscale up."),
            (self.lineEditAcceptRisk, "Risk Acknowledgment Flag", "Risk acknowledgment flags passed to tailscale up (e.g. lose-ssh, all)."),
            (self.lineEditTags, "ACL Tags Input", "Comma-separated ACL tags to assign to this node (e.g. tag:server)."),
            (self.lineEditEmergencyIp, "Emergency Cached IP", "Displays the last known IPv4 address of the node for emergency fallback."),
            (self.listNativeSwitch, "Instant Switch Profile List", "Select multiple compatible profiles for sub-second switching."),
            (self.chkAutoPopulate, "Auto-Sync Daemon Toggle", "Enables pulling live configuration preferences from the Tailscale daemon."),
            (self.btnSave, "Save Advanced Options", "Applies and saves the network and routing configuration."),
            (self.btnCancel, "Cancel Changes", "Discards unsaved modifications and closes the dialog."),
            (self.chkAllowLAN, "Allow LAN Access", "Retains local network access when routing through an exit node."),
            (self.chkSSH, "Enable Tailscale SSH", "Enables secure inbound SSH handled by Tailnet ACL policies."),
            (self.chkAcceptRoutes, "Accept Advertised Routes", "Accepts subnet routes exposed by other devices on the Tailnet."),
            (self.chkAcceptDNS, "Accept Tailnet DNS", "Configures local resolver with Tailnet MagicDNS and upstream servers."),
            (self.chkShieldsUp, "Shields Up Firewall", "Blocks all incoming peer connections for zero-trust endpoint isolation."),
            (self.chkAdvertiseExitNode, "Advertise as Exit Node", "Enables this device to act as an exit gateway for the Tailnet."),
            (self.chkDisableSNAT, "Disable Subnet SNAT", "Preserves original source client IP addresses for advertised subnets."),
            (self.chkUnattended, "Unattended Background Mode", "Runs Tailscale persistently without requiring an active Windows user session."),
            (self.chkWebclient, "Web Client Management", "Binds local browser interface for web-based daemon control."),
            (self.chkAdvertiseConnector, "Advertise App Connector", "Designates machine as proxy node for corporate SaaS destinations."),
            (self.chkForceReset, "Force Reset State", "Clears stuck routing tables and daemon state upon startup."),
            (self.chkForceReauth, "Force Key Reauthentication", "Purges stored authentication tokens and forces fresh server key exchange."),
            # Column 1 Status Badges
            (self.chkAllowLANValue, "Allow LAN Status Badge", "Live status indicator showing whether LAN access is active."),
            (self.chkSSHValue, "SSH Status Badge", "Live status indicator showing whether Tailscale SSH is active."),
            (self.chkAcceptRoutesValue, "Accept Routes Status Badge", "Live status indicator showing whether subnet route acceptance is active."),
            (self.chkAcceptDNSValue, "Accept DNS Status Badge", "Live status indicator showing whether MagicDNS acceptance is active."),
            (self.chkShieldsUpValue, "Shields Up Status Badge", "Live status indicator showing whether Shields Up firewalling is active."),
            (self.chkAdvertiseExitNodeValue, "Exit Node Advertised Status Badge", "Live status indicator showing whether exit node egress is active."),
            (self.chkDisableSNATValue, "Disable SNAT Status Badge", "Live status indicator showing whether SNAT bypass is active."),
            (self.chkUnattendedValue, "Unattended Mode Status Badge", "Live status indicator showing whether unattended mode is active."),
            (self.chkWebclientValue, "Web Client Status Badge", "Live status indicator showing whether web client is active."),
            (self.chkAdvertiseConnectorValue, "App Connector Status Badge", "Live status indicator showing whether app connector is active."),
        ]
        for widget, name, desc in accessible_configs:
            if widget:
                widget.setAccessibleName(name)
                widget.setAccessibleDescription(desc)

        # Dynamic live updates: clicking either checkbox updates badge to bold green True / bold red False
        pairs = [
            (self.chkAllowLAN, self.chkAllowLANValue),
            (self.chkSSH, self.chkSSHValue),
            (self.chkAcceptRoutes, self.chkAcceptRoutesValue),
            (self.chkAcceptDNS, self.chkAcceptDNSValue),
            (self.chkShieldsUp, self.chkShieldsUpValue),
            (self.chkAdvertiseExitNode, self.chkAdvertiseExitNodeValue),
            (self.chkDisableSNAT, self.chkDisableSNATValue),
            (self.chkUnattended, self.chkUnattendedValue),
            (self.chkWebclient, self.chkWebclientValue),
            (self.chkAdvertiseConnector, self.chkAdvertiseConnectorValue),
        ]
        for left_chk, right_chk in pairs:
            if left_chk and right_chk:
                def make_left_sync(r):
                    return lambda checked: (r.setChecked(checked), self._update_bool_badge(r, checked))
                def make_right_sync(l, r):
                    return lambda checked: (l.setChecked(checked), self._update_bool_badge(r, checked))
                left_chk.toggled.connect(make_left_sync(right_chk))
                right_chk.toggled.connect(make_right_sync(left_chk, right_chk))
        
        if self.chkAutoPopulate:
            self.chkAutoPopulate.stateChanged.connect(self._on_auto_populate_changed)

        if self.btnSave:
            self.btnSave.clicked.connect(self._save_settings)

        if self.btnCancel:
            self.btnCancel.clicked.connect(self.reject)

        # Populate listNativeSwitch
        if self.listNativeSwitch:
            for name in self.manager.profiles:
                item = QListWidgetItem(name, self.listNativeSwitch)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                
                # Check if this profile is already in the current profile's switch list
                checked = False
                if self.profile.native_profile:
                    checked = (name in [n.strip() for n in self.profile.native_profile.split(",")])
                    
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

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

        if hasattr(self, 'chkAcceptRoutes') and self.chkAcceptRoutes:
            self.chkAcceptRoutes.setChecked(getattr(self.profile, 'accept_routes', True))

        if hasattr(self, 'chkUnattended') and self.chkUnattended:
            self.chkUnattended.setChecked(getattr(self.profile, 'unattended', False))

        if hasattr(self, 'chkWebclient') and self.chkWebclient:
            self.chkWebclient.setChecked(getattr(self.profile, 'webclient', False))

        if hasattr(self, 'chkAdvertiseConnector') and self.chkAdvertiseConnector:
            self.chkAdvertiseConnector.setChecked(getattr(self.profile, 'advertise_connector', False))

        # Column 1 Value Checkboxes (True / False status badges)
        if self.chkAllowLANValue:
            val = getattr(self.profile, 'allow_lan', False)
            self.chkAllowLANValue.setChecked(val)
            self._update_bool_badge(self.chkAllowLANValue, val)
        if self.chkSSHValue:
            val = getattr(self.profile, 'enable_ssh', False)
            self.chkSSHValue.setChecked(val)
            self._update_bool_badge(self.chkSSHValue, val)
        if self.chkAcceptRoutesValue:
            val = getattr(self.profile, 'accept_routes', True)
            self.chkAcceptRoutesValue.setChecked(val)
            self._update_bool_badge(self.chkAcceptRoutesValue, val)
        if self.chkAcceptDNSValue:
            val = getattr(self.profile, 'accept_dns', False)
            self.chkAcceptDNSValue.setChecked(val)
            self._update_bool_badge(self.chkAcceptDNSValue, val)
        if self.chkShieldsUpValue:
            val = getattr(self.profile, 'shields_up', False)
            self.chkShieldsUpValue.setChecked(val)
            self._update_bool_badge(self.chkShieldsUpValue, val)
        if self.chkAdvertiseExitNodeValue:
            val = getattr(self.profile, 'advertise_exit_node', False)
            self.chkAdvertiseExitNodeValue.setChecked(val)
            self._update_bool_badge(self.chkAdvertiseExitNodeValue, val)
        if self.chkDisableSNATValue:
            val = getattr(self.profile, 'disable_snat', False)
            self.chkDisableSNATValue.setChecked(val)
            self._update_bool_badge(self.chkDisableSNATValue, val)
        if self.chkUnattendedValue:
            val = getattr(self.profile, 'unattended', False)
            self.chkUnattendedValue.setChecked(val)
            self._update_bool_badge(self.chkUnattendedValue, val)
        if self.chkWebclientValue:
            val = getattr(self.profile, 'webclient', False)
            self.chkWebclientValue.setChecked(val)
            self._update_bool_badge(self.chkWebclientValue, val)
        if self.chkAdvertiseConnectorValue:
            val = getattr(self.profile, 'advertise_connector', False)
            self.chkAdvertiseConnectorValue.setChecked(val)
            self._update_bool_badge(self.chkAdvertiseConnectorValue, val)

        if hasattr(self, 'lineEditExtraArgs') and self.lineEditExtraArgs:
            self.lineEditExtraArgs.setText(getattr(self.profile, 'extra_args', ''))

        if hasattr(self, 'lineEditAcceptRisk') and self.lineEditAcceptRisk:
            self.lineEditAcceptRisk.setText(getattr(self.profile, 'accept_risk', ''))

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

    def _update_bool_badge(self, chk, checked):
        if chk:
            if checked:
                chk.setText("✓ Active")
                chk.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 10pt;")
            else:
                chk.setText("✗ Inactive")
                chk.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 10pt;")

    def _on_auto_populate_changed(self, state):
        if state == Qt.Checked.value or state == Qt.Checked:
            self._fetch_active_status()
            self._fetch_active_prefs()

    def _fetch_active_prefs(self):
        """Fetches the live preferences from Tailscale to auto-populate the advanced options."""
        from src.core.tailscale import get_tailscale_path
        self.prefs_proc = QProcess(self)
        
        def on_prefs_finished(*args):
            try:
                if not hasattr(self, 'prefs_proc') or self.prefs_proc is None:
                    return
                output = self.prefs_proc.readAllStandardOutput().data().decode().strip()
            except RuntimeError:
                return
            if not output: return
            
            # Don't auto-populate if the user disabled it
            if self.chkAutoPopulate and not self.chkAutoPopulate.isChecked():
                return
                
            try:
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
                if hasattr(self, 'chkAcceptRoutes') and self.chkAcceptRoutes and "RouteAll" in prefs:
                    self.chkAcceptRoutes.setChecked(bool(prefs.get("RouteAll")))
                if hasattr(self, 'chkUnattended') and self.chkUnattended and "Unattended" in prefs:
                    self.chkUnattended.setChecked(bool(prefs.get("Unattended")))
                    
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
                    except (OSError, ValueError) as res_err:
                        logger.debug(f"Could not resolve ControlURL hostname: {res_err}")
                    
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"Could not parse tailscale prefs: {e}")
                
        self.prefs_proc.finished.connect(on_prefs_finished)
        self.prefs_proc.start(get_tailscale_path(), ["debug", "prefs"])

    def _fetch_active_status(self):
        self.status_proc = QProcess(self)
        
        def on_finished(*args):
            try:
                if not hasattr(self, 'status_proc') or self.status_proc is None:
                    return
                output = self.status_proc.readAllStandardOutput().data().decode().strip()
            except RuntimeError:
                return
            logger.debug(f"tailscale status payload received ({len(output)} bytes)")
            if self.comboBoxExitNode:
                self.comboBoxExitNode.setPlaceholderText("Select exit node or type custom...")
            
            try:
                data = json.loads(output)
                exit_nodes = []
                active_system_exit_node = ""
                
                # Parse exit nodes and map their subnet routes
                peers = data.get("Peer") or {}
                for peer_info in peers.values():
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
                exit_nodes = sorted(set(exit_nodes))
                
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

            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"Could not parse tailscale status payload: {e}")
                
        self.status_proc.finished.connect(on_finished)
        self.status_proc.errorOccurred.connect(self._log_status_proc_error)
        self.status_proc.readyReadStandardError.connect(self._log_status_proc_stderr)
        
        from src.core.tailscale import get_tailscale_path
        ts_path = get_tailscale_path()
        logger.debug(f"Starting exit-node status query with {ts_path!r}")
        self.status_proc.start(ts_path, ["status", "--json"])

    def _log_status_proc_error(self, error):
        logger.debug(f"Exit-node status process error: {error}")

    def _log_status_proc_stderr(self):
        text = self.status_proc.readAllStandardError().data().decode(errors="ignore").strip()
        if text:
            logger.debug(f"Exit-node status process stderr: {text}")

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
        advertise_exit_node = (self.chkAdvertiseExitNodeValue.isChecked() if hasattr(self, 'chkAdvertiseExitNodeValue') and self.chkAdvertiseExitNodeValue else (self.chkAdvertiseExitNode.isChecked() if self.chkAdvertiseExitNode else False))
        
        # Conflict guard: A node cannot route all internet traffic through an external exit node while also advertising itself as an exit node
        if exit_node and (advertise_exit_node or "0.0.0.0/0" in routes or "::/0" in routes):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Exit Node Conflict",
                "A node cannot both route all internet traffic through an external exit node and advertise itself as an exit node (or advertise 0.0.0.0/0).\n\n"
                "Please either clear the Exit Node selection or uncheck 'Run as Exit Node'."
            )
            return

        self.profile.exit_node = exit_node
        self.profile.routes = routes
        self.profile.hostname = hostname
        self.profile.enable_ssh = self.chkSSH.isChecked() if self.chkSSH else False
        self.profile.accept_dns = self.chkAcceptDNS.isChecked() if self.chkAcceptDNS else False
        self.profile.allow_lan = self.chkAllowLAN.isChecked() if self.chkAllowLAN else False
        self.profile.disable_snat = self.chkDisableSNAT.isChecked() if self.chkDisableSNAT else False
        self.profile.force_reset = self.chkForceReset.isChecked() if self.chkForceReset else False
        self.profile.advertise_exit_node = advertise_exit_node
        self.profile.shields_up = self.chkShieldsUp.isChecked() if self.chkShieldsUp else False
        self.profile.force_reauth = self.chkForceReauth.isChecked() if self.chkForceReauth else False
        self.profile.advertise_tags = self.lineEditTags.text().strip() if self.lineEditTags else ""
        self.profile.accept_routes = self.chkAcceptRoutes.isChecked() if hasattr(self, 'chkAcceptRoutes') and self.chkAcceptRoutes else True
        self.profile.unattended = self.chkUnattended.isChecked() if hasattr(self, 'chkUnattended') and self.chkUnattended else False
        self.profile.webclient = self.chkWebclient.isChecked() if hasattr(self, 'chkWebclient') and self.chkWebclient else False
        self.profile.advertise_connector = self.chkAdvertiseConnector.isChecked() if hasattr(self, 'chkAdvertiseConnector') and self.chkAdvertiseConnector else False
        if hasattr(self, 'lineEditExtraArgs') and self.lineEditExtraArgs:
            self.profile.extra_args = self.lineEditExtraArgs.text().strip()
        if hasattr(self, 'lineEditAcceptRisk') and self.lineEditAcceptRisk:
            self.profile.accept_risk = self.lineEditAcceptRisk.text().strip()

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

    def _cleanup_processes(self):
        """Gracefully terminate active probing processes when the dialog closes."""
        for proc in (getattr(self, 'prefs_proc', None), getattr(self, 'status_proc', None)):
            if proc is not None and proc.state() != QProcess.NotRunning:
                proc.terminate()
                if not proc.waitForFinished(300):
                    proc.kill()

    def reject(self):
        self._cleanup_processes()
        super().reject()

    def closeEvent(self, event):
        self._cleanup_processes()
        super().closeEvent(event)
