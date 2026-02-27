# 🌐 TAILSCALE VPN Client
### *Cross-Platform Tailscale + Headscale Mesh Orchestration*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python) ![UI](https://img.shields.io/badge/UI-CustomTkinter-orange) ![Security](https://img.shields.io/badge/Security-WireGuard-green) ![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**TAILSCALE VPN Client** is a professional GUI orchestration tool designed to connect Tailscale nodes to a self-hosted **Headscale** server. It replaces the standard cloud-hosted control plane with a local, private interface, offering enhanced privacy, multi-profile management, and real-time traffic analytics.

---

## 📂 Project Structure

The repository is highly modular, separating UI rendering (CustomTkinter) from core VPN logic and OS-specific functions:

```text
C:.
├── .gitignore
├── 1.txt
├── config.py                      # ⚙️ Global configuration and OS-agnostic path definitions
├── icon.ico
├── icon.png                       
├── LICENSE                        # ⚖️ Application legal terms
├── main.py                        # 🚀 Entry point: Checks service status and boots GUI
├── README.md                      # 📖 Documentation (this file)
├── requirements.txt               # 📦 Project dependencies
├── requirements_full.txt
├── version_info.txt
├── Application Images/            # 🖼️ Application screenshots and diagrams
│   ├── 01_connected.png
│   ├── 01_main.png
│   ├── 02_select_auth.png
│   ├── 04_traffic_stats.png
│   └── 05_close_disable_if_connected.png
├── assets/                        # 🖼️ Graphical UI assets
│   ├── cancel_icon.png
│   ├── google_icon.png            # SSO login icon
│   ├── icon.png
│   ├── key_icon.png               # Auth-key authentication icon
│   └── save_logo.png
├── gui/                           # 🖥️ GUI Package (CustomTkinter Components)
│   ├── __init__.py
│   ├── about.py                   # About popup window
│   ├── about_viewer.py            # Detailed about viewer
│   ├── change_credentials_popup.py# Prompt for changing VPN keys/SSO
│   ├── common.py                  # Shared UI constants (COLORS, FONTS)
│   ├── darkstyle.py               # Dark theme configurations
│   ├── gui_main.py                # Main Window UI (TabbedClientApp class)
│   ├── gui_start.py               # Tkinter root initialization
│   ├── gui_tabs.py                # Individual profile tab logic (ClientTab class)
│   ├── license_viewer.py          # Always-on-top LICENSE viewer
│   ├── log_viewer.py              # 📜 In-app dynamic log reader
│   ├── progress_popup.py          # Bottom-right status notifications
│   ├── readme_viewer.py           # Always-on-top markdown viewer
│   ├── settings.py                # ⚙️ App settings (Auto-connect, logs)
│   ├── sso.py                     # 🔑 OIDC/Google SSO browser handshake logic
│   ├── styles.py                  # Light theme configurations
│   ├── tailscaleclient.py         # 🛠️ Tailscale CLI wrapper for backend commands
│   ├── themes.py                  # Shared color palette definitions
│   ├── traffic_popup.py           # 📈 Live bandwidth statistics UI
│   └── utils.py                   # 🔧 Formatting, window centering, and UI helpers
├── logic/                         # 🧠 Core Application Logic
│   ├── __init__.py
│   ├── db_manager.py              # 🗄️ SQLite handler for persistent traffic logs
│   ├── logger.py                  # 📝 Global logging engine & print redirection
│   ├── net_stats.py               # 📊 Low-level network interface monitoring
│   ├── statuscheck.py             # 🔍 Tailscale connection polling and status checks
│   └── vpn_logic.py               # 🔌 Profile orchestration and credential encryption
└── os_specific/                   # 💻 OS-level Integrations
    ├── __init__.py
    ├── command_executor.py        # OS command routing
    └── mutex_handler.py           # 🔒 Single-instance application enforcement

```

---

## ✨ Key Features

* **🚀 Multi-Profile Tabs**: Manage up to 5 unique Headscale environments simultaneously via a clean, modern tabbed interface.
* **📝 Dynamic Global Logging**: Built-in debugging engine that intercepts CLI outputs and Python streams, viewable through an interactive in-app Log Viewer with syntax highlighting and search.
* **📊 Live Traffic Monitoring**: Real-time Sent/Received data tracking with persistent daily totals stored locally via SQLite.
* **🔐 Dual Authentication**: Native support for pre-generated **Auth-Keys** and automated **OIDC (Google SSO)** login flows.
* **📌 Seamless Window Management**: Viewers, popups, and settings are correctly transient to the main window, preventing taskbar clutter.
* **🎨 Modern UI/Theming**: Built on CustomTkinter, supporting high-contrast Dark and Light themes with fluid transitions.
* **⚙️ Intelligent Boot**: Automatically monitors and waits for the Tailscale OS service to initialize before exposing connection controls.
* **🔔 Progress Tracking**: Real-time step-by-step progress notifications for connection handshakes.

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

* **Profile & Data Storage**: Profiles, encrypted credentials, and databases are stored securely in `%AppData%/Tailscale_VPN_Client` (Windows) or `~/.local/share/Tailscale_VPN_Client` (Linux).
* **Auto-Connect**: Enable via `File > Settings` to automatically reconnect the last active profile on launch.
* **Diagnostic Logs**: Enable via `File > Settings`. When activated, dedicated `app.log`, `network.log`, `database.log`, and `[Profile]_connection.log` files are generated. View them directly via `Logs > Global logs`.
* **Credentials**: Use the **Change Credentials** button within any disconnected tab to update server URLs or switch between Auth Key and SSO modes on the fly.

---

## 📜 Logging & Diagnostics

TAILSCALE VPN Client includes a powerful, opt-in diagnostic logging engine to help troubleshoot VPN handshakes, routing issues, and UI events.

* **Enable/Disable**: Navigate to `File > Settings` and check **Enable Global App Logs**. Disabling this feature will safely prompt you to delete all existing diagnostic files to save space.
* **Log Types**: When enabled, the app automatically generates the following files inside a dedicated `GlobalLogs` directory:
* `app.log`: Core application events, window transitions, and GUI errors.
* `database.log`: SQLite transactions and schema validations.
* `network.log`: Low-level interface traffic metrics.
* `[ProfileName]_connection.log`: Real-time terminal output directly from the Tailscale CLI for specific profiles.


* **In-App Viewer**: You can view these files without leaving the application by navigating to `Logs > Global logs`. The built-in viewer features auto-scrolling, color-coded severity tagging (INFO, WARNING, ERROR), and text search.

---

## 🤝 Contributing

Contributions are welcome! Whether it's adding support for new Tailscale CLI flags, extending cross-platform compatibility, or enhancing the CustomTkinter UI, please feel free to submit a Pull Request.

---

## ⚠️ Disclaimer

This project is an independent effort and is **not** officially affiliated with Tailscale Inc. or the Headscale project. Use this software at your own risk. Always ensure you understand the security implications of self-hosting network infrastructure.
