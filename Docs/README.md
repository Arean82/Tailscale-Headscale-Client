# Tailscale / Headscale Client Pro (Enterprise Platinum Edition)

[![Release](https://img.shields.io/badge/Release-v5.0.0--Enterprise-emerald?style=for-the-badge&logo=shield)](https://github.com/Arean82/Tailscale-Headscale-Client)
[![Tailscale Engine](https://img.shields.io/badge/Tailscale%20Engine-v1.6%2B-blue?style=for-the-badge&logo=tailscale)](https://tailscale.com)
[![PySide6 Qt6](https://img.shields.io/badge/Framework-PySide6%20Qt6-41CD52?style=for-the-badge&logo=qt)](https://pyside.org)
[![Platform Matrix](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)](https://github.com/Arean82/Tailscale-Headscale-Client)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue?style=for-the-badge)](../LICENSE)
[![Security Standard](https://img.shields.io/badge/Security-Hardware%20Keyring%20Vault-orange?style=for-the-badge)](SECURITY.md)

**Tailscale / Headscale Client Pro** is a mission-critical, enterprise-grade desktop coordination client engineered for seamless interoperability between official **Tailscale** control networks and private, self-hosted **Headscale** orchestration nodes. 

Built strictly on **PySide6 (Qt for Python)** without webview bloat, the application enforces deterministic process lifecycles, zero-plaintext credential persistence, high-fidelity real-time telemetry, and complete two-column operational controls designed for zero-drift site reliability operations.

---

## 🏛️ System Architecture Specification

The client implements an isolated, multi-tier architecture separating user interface presentation from state coordination, local daemon execution, and persistent hardware vaults:

```mermaid
graph TB
    %% Explicit Node Styling - Colors ONLY on Nodes
    classDef uiNode fill:#1e1b4b,stroke:#818cf8,stroke-width:1.5px,color:#ffffff;
    classDef coordNode fill:#064e3b,stroke:#34d399,stroke-width:1.5px,color:#ffffff;
    classDef daemonNode fill:#451a03,stroke:#fbbf24,stroke-width:1.5px,color:#ffffff;
    classDef storageNode fill:#164e63,stroke:#22d3ee,stroke-width:1.5px,color:#ffffff;

    %% 100% Transparent Subgraph Containers (Zero Flood Color)
    style UI fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;
    style Core fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;
    style Daemon fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;
    style Storage fill:none,stroke:#475569,stroke-width:1.5px,stroke-dasharray: 5 5,color:#cbd5e1;

    subgraph UI ["🖥️ Presentation Layer (PySide6 GUI)"]
        MW["MainWindow & System Tray"]:::uiNode
        DB["Dashboard & Profile Tabs"]:::uiNode
        ND["NodeDialog (Advanced Options)"]:::uiNode
        PL["PeerList & Sparklines"]:::uiNode
        RD["Markdown Viewer Studio"]:::uiNode
    end

    subgraph Core ["🧠 Core Control & State Coordination"]
        SC["StateCoordinator (Deterministic Gatekeeper)"]:::coordNode
        SM["AppState FSM Machine"]:::coordNode
        TSM["TailscaleProcess (Execution Engine)"]:::coordNode
        WM["ProcessWatchdog (psutil Reaper)"]:::coordNode
    end

    subgraph Daemon ["⚙️ Host OS Daemon Interface"]
        TD["Local tailscaled / Windows Service"]:::daemonNode
        CLI["tailscale CLI (JSON IPC Engine)"]:::daemonNode
        API["Local API Pipe / Domain Socket"]:::daemonNode
    end

    subgraph Storage ["💾 Persistence & Security Layer"]
        KR["OS Credential Vault (Keyring)"]:::storageNode
        SQL["SQLite Database (Traffic History)"]:::storageNode
        FS["Profile Store (JSON)"]:::storageNode
    end

    %% Flow Connections
    MW -->|User Actions| SC
    DB -->|Switch Profile| SC
    ND -->|Flags & Routes| SC
    SC -->|State Guard| SM
    SC -->|Array Execution| TSM
    TSM -->|IPC Commands| CLI
    TSM -->|Local Named Pipe| TD
    TSM -->|Socket Stream| API
    WM -->|Process Health| TD
    SC -->|Persist Config| FS
    TSM -->|Retrieve Keys| KR
    SC -->|Commit Stats| SQL
```

---

## 🔄 Finite State Machine (FSM) & Connection Lifecycle

Network connection state flows strictly through a formal, deterministic Finite State Machine to eliminate race conditions, duplicate execution loops, and orphaned zombie processes:

```mermaid
stateDiagram-v2
    [*] --> DISCONNECTED

    DISCONNECTED --> CONNECTING : Connect Trigger (AuthKey / SSO Handshake)
    CONNECTING --> CONNECTED : Daemon Handshake 200 OK (Interface Active)
    CONNECTING --> ERROR : Timeout / Invalid Key / SSL Refusal / Service Stale
    CONNECTING --> PENDING_APPROVAL : Node Requires Admin Console Authorization

    PENDING_APPROVAL --> CONNECTED : Approved by Administrator
    PENDING_APPROVAL --> DISCONNECTED : User Abort / Handshake Expired

    CONNECTED --> CONNECTING : Switch Environment Profile / Dynamic Reconnect
    CONNECTED --> DISCONNECTED : Clean Operator Disconnect
    CONNECTED --> LOGGED_OUT : Invalidate Profile Session
    CONNECTED --> ERROR : Daemon Crash / Network Interface Dropped

    ERROR --> CONNECTING : Exponential Backoff Retry (3s, 6s, 12s)
    ERROR --> DISCONNECTED : Max Retries (3) Exhausted / Fatal Failure

    LOGGED_OUT --> DISCONNECTED : Select Alternate Environment Profile
```

---

## ⚙️ Enterprise Advanced Options (Two-Column Status Matrix)

The `NodeDialog` advanced configuration panel enforces an exact two-column contract: **Column 0** exposes operator-controlled toggles, while **Column 1** displays live, read-only daemon status badges dynamically colored in `#22c55e` (**`True`**) or `#ef4444` (**`False`**):

| Feature Name | Active CLI Flag Parameter | Column 1 Badge Key | Operational Specification |
| :--- | :--- | :--- | :--- |
| **Allow LAN Access** | `--exit-node-allow-lan-access` | `chkAllowLANValue` | Retains direct local Ethernet/Wi-Fi access while tunneling through an Exit Node. |
| **Enable SSH** | `--ssh` | `chkSSHValue` | Provisions secure Tailscale SSH server daemon managed by network ACL policies. |
| **Accept Routes** | `--accept-routes` | `chkAcceptRoutesValue` | Enables client acceptance of advertised CIDR subnet routes across the Tailnet. |
| **Accept DNS** | `--accept-dns` | `chkAcceptDNSValue` | Injects MagicDNS search domains and designated upstream resolver servers. |
| **Shields Up** | `--shields-up` | `chkShieldsUpValue` | Enforces zero-trust endpoint firewalling by blocking all inbound peer connections. |
| **Run as Exit Node** | `--advertise-exit-node` | `chkAdvertiseExitNodeValue` | Converts the local endpoint into a default gateway for whole-network internet egress. |
| **Disable SNAT** | `--snat-subnet-routes=false` | `chkDisableSNATValue` | Preserves source client IP addresses for bidirectional site-to-site routing. |
| **Unattended Mode** | `--unattended` | `chkUnattendedValue` | Runs daemon persistently in background without an active interactive Windows user session. |
| **Web Client** | `--webclient` | `chkWebclientValue` | Binds internal authenticated browser-based management interface. |
| **App Connector** | `--advertise-connector` | `chkAdvertiseConnectorValue` | Designates the machine as a secure traffic proxy for external corporate SaaS targets. |
| **Subnet Routes** | `--advertise-routes=<CIDR>` | *Input Field* | Publishes RFC 1918 internal subnets (e.g. `10.0.0.0/24, 192.168.1.0/24`). |
| **Custom Hostname** | `--hostname=<NAME>` | *Input Field* | Overrides the local machine name registered within Headscale/Tailscale DNS tables. |
| **Force Reset** | `--reset` | *Execution Flag* | Flushes lingering runtime route state prior to bringing profile up. |
| **Force Reauth** | `--force-reauth` | *Execution Flag* | Enforces complete key exchange with control server, purging cached session tokens. |

---

## 🔒 Security Architecture & Trust Engineering

1. **Zero-Plaintext Credential Vault:** All machine auth keys, pre-shared tokens, and sensitive URLs are encrypted and stored via platform-native credential managers using the `keyring` standard (Windows Credential Locker, macOS Keychain, Linux Secret Service).
2. **Subprocess Injection Defense:** All CLI executions pass commands as tokenized argument arrays (`subprocess.Popen([cmd, arg1, arg2], shell=False)`). Shell interpolation is strictly prohibited, neutralizing command injection vectors.
3. **Automated Process Watchdog:** Process supervision powered by `psutil` actively reaps orphaned daemon tasks upon application exit or profile switching, preventing socket binding collisions.
4. **Resilient Exponential Backoff:** Reconnection logic implements bounded exponential backoff (`3s` -> `6s` -> `12s`), preventing connection flooding and server DDoS during outages.
5. **Self-Signed SSL Accommodation:** Isolated homelab deployments with self-hosted Headscale servers support TLS verification bypass via the `--insecure-skip-tls-verify=true` setting.

---

## 📋 System Compatibility Matrix

| Operating System | Supported Architecture | Minimum Version | Service Manager | Privilege Model |
| :--- | :--- | :--- | :--- | :--- |
| **Windows** | x86_64, ARM64 | Windows 10 (Build 19041+) / Windows 11 | Windows Service (`Tailscale`) | Standard User (Service elevated) |
| **Linux** | x86_64, aarch64 | Ubuntu 20.04+, Debian 11+, Fedora 36+ | `systemd` (`tailscaled.service`) | Group `tailscale` / Socket ACL |
| **macOS** | x86_64, Apple Silicon | macOS 11.0 (Big Sur) or higher | `launchd` / `launchctl` | Keychain Sandbox |

---

## 🛠️ Developer Setup & Verification

```bash
# 1. Clone repository
git clone https://github.com/Arean82/Tailscale-Headscale-Client.git
cd Tailscale-Headscale-Client

# 2. Configure dedicated virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 3. Install release-grade production dependencies
pip install -r requirements.txt

# 4. Launch development client
python main.py
```

---

## 📦 Production Packaging & Distribution

```mermaid
graph LR
    SRC["Python Source Core"] --> PYI["PyInstaller Build Engine (.spec)"]
    PYI --> DIR["Standalone Binary Directory (OneDir)"]
    DIR --> WIN["Inno Setup Compiler -> Windows (.exe)"]
    DIR --> DEB["dpkg-deb Engine -> Linux (.deb)"]
    DIR --> MAC["create-dmg Utility -> macOS (.dmg)"]
```

### Windows Enterprise Installer (Inno Setup)
1. Build binary tree:
   ```powershell
   pyinstaller .\TailscaleClient_OneDir.spec
   ```
2. Compile with Inno Setup Compiler (`TailscaleClient_Installer.iss`):
   Outputs: `dist\installer\TailscaleClientPro_Setup.exe`

### Linux Debian Distribution (.deb)
```bash
chmod +x build_linux_deb.sh
./build_linux_deb.sh
# Outputs: dist/tailscale-client-pro_5.0.0_amd64.deb
```

### macOS Signed Image (.dmg)
```bash
chmod +x build_mac_dmg.sh
./build_mac_dmg.sh
# Outputs: dist/TailscaleClientPro_Setup.dmg
```

---

## 📄 Licensing & Governance

This software is released and distributed under the **GNU General Public License v3.0**. Review the [LICENSE](../LICENSE) file for complete warranty disclaimers and redistribution rights.
