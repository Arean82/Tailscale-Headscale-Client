# 🌐 TAILSCALE VPN Client
### *Cross-Platform Tailscale + Headscale Mesh Orchestration*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python) ![UI](https://img.shields.io/badge/UI-PySide6--Native-blue) ![Security](https://img.shields.io/badge/Security-WireGuard-green) ![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**TAILSCALE VPN Client** is a professional GUI orchestration tool designed to connect Tailscale nodes to a self-hosted **Headscale** server. It replaces the standard cloud-hosted control plane with a local, private interface, offering enhanced privacy, multi-profile management, and real-time traffic analytics.

---

## 📂 Project Structure

The repository is highly modular, separating UI rendering (PySide6) from core VPN logic and OS-specific functions:

```text
C:.
├── .gitignore
├── assets/                        # 🖼️ Graphical UI assets & Screenshots
│   ├── cancel_icon.png
│   ├── google_icon.png            # SSO login icon
│   ├── icon.ico                   # App Icon (Windows)
│   ├── icon.png                   # App Icon (PNG)
│   ├── key_icon.png               # Auth-key authentication icon
│   ├── save_logo.png
│   └── screenshots/               # 🖼️ Application screenshots and diagrams
│       ├── 01_connected.png
│       ├── 01_main.png
│       ├── 02_select_auth.png
│       ├── 04_traffic_stats.png
│       └── 05_close_disable_if_connected.png
├── LICENSE                        # ⚖️ Application legal terms
├── main.py                        # 🚀 Entry point: Checks service status and boots GUI
├── README.md                      # 📖 Documentation (this file)
├── requirements.txt               # 📦 Project dependencies
├── src/                           # 🖥️ Application Source Code
│   ├── ui/                        # UI Components & Tabs
│   ├── core/                      # Data & Process Management
│   ├── logic/                     # Business Logic (migrated)
│   ├── utils/                     # Shared Utilities (Logger, Crypto)
│   └── os_specific/               # Platform-specific handlers
└── pygui/                         # 🎨 Qt Designer .ui files
```

---

## ✨ Key Features

* **🚀 Multi-Profile Tabs**: Manage unique Headscale environments simultaneously via a clean, modern tabbed interface.
* **📝 Dynamic Global Logging**: Built-in debugging engine that intercepts CLI outputs and Python streams, viewable through an interactive in-app Log Viewer.
* **📊 Live Traffic Monitoring**: Real-time Sent/Received data tracking with persistent daily totals stored locally.
* **🔐 Dual Authentication**: Native support for pre-generated **Auth-Keys** and automated **OIDC (Google SSO)** login flows.
* **🎨 Modern UI/Theming**: Built on PySide6, supporting high-contrast Dark and Light themes with fluid transitions.
* **⚙️ Intelligent Boot**: Automatically monitors and waits for the Tailscale OS service to initialize before exposing connection controls.

---

## 🚀 Getting Started

### 📋 Prerequisites

* **Tailscale**: The Tailscale backend engine must be installed and the system service should be actively running.
* **Headscale Server**: A reachable URL for your private network coordinator.

### 🛠️ Installation & Usage

1. **Clone the Repo**: `git clone https://github.com/user/Tailscale-Headscale-Client.git`
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Launch**: Run `python main.py` (or compile to a standalone `.exe` using PyInstaller).
4. **Connect**:
   * Navigate to `Profile > Add New Profile`.
   * Enter your **TAILSCALE VPN URL** and **Auth Key** (or select SSO).
   * Click **Connect**.

---

## 🛠 Configuration

* **Profile & Data Storage**: Profiles, encrypted credentials, and databases are stored securely in `%AppData%/Tailscale_VPN_Client_Pro` (Windows) or `~/.local/share/Tailscale_VPN_Client_Pro` (Linux).
* **Auto-Connect**: Enable via `File > Settings` to automatically reconnect the last active profile on launch.
* **Diagnostic Logs**: Enable via `File > Settings`. When activated, dedicated logs are generated and viewable directly via `Logs > Global logs`.

---

## 📜 Logging & Diagnostics

TAILSCALE VPN Client includes a powerful, opt-in diagnostic logging engine to help troubleshoot VPN handshakes, routing issues, and UI events.

* **Enable/Disable**: Navigate to `File > Settings` and check **Enable Global App Logs**.
* **In-App Viewer**: View logs without leaving the application by navigating to `Logs > Global logs`. The built-in viewer features auto-scrolling and severity tagging.

---

## ⚠️ Disclaimer

This project is an independent effort and is **not** officially affiliated with Tailscale Inc. or the Headscale project. Use this software at your own risk.
