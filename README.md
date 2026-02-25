# 🌐 MAPView VPN Client
### *Cross-Platform Tailscale + Headscale Mesh Orchestration*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python) ![UI](https://img.shields.io/badge/UI-CustomTkinter-orange) ![Security](https://img.shields.io/badge/Security-WireGuard-green) ![OS](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)


**MAPView VPN Client** is a professional GUI orchestration tool designed to connect Tailscale nodes to a self-hosted **Headscale** server. It replaces the standard cloud-hosted control plane with a local, private interface, offering enhanced privacy and multi-profile management.

---

## 📂 Project Structure

The repository is organized into modular packages to separate UI rendering from core VPN logic:

```text
C:.
├── main.py                # 🚀 Entry point: Checks service status and boots GUI
├── LICENSE                # ⚖️ Application legal terms
├── README.md              # 📖 Documentation (this file)
├── vpn_logic.py           # 🧠 Core connection and profile orchestration logic
├── tailscaleclient.py     # 🛠️ Tailscale CLI wrapper for backend commands
├── db_manager.py          # 🗄️ SQLite handler for persistent traffic logs
├── net_stats.py           # 📊 Low-level network interface monitoring
├── sso.py                 # 🔑 OIDC/Google SSO browser handshake logic
├── styles.py              # 🎨 Light theme TTK widget configurations
├── darkstyle.py           # 🌙 Dark theme TTK widget configurations
├── themes.py              # 🎨 Shared color palette definitions
├── utils.py               # 🔧 Formatting, window centering, and UI helpers
├── assets/                # 🖼️ Graphical assets
│   ├── icon.png           # Main application icon
│   ├── key_icon.png       # Auth-key authentication icon
│   └── google_icon.png    # SSO login icon
└── gui/                   # 🖥️ GUI Package (Modular Components)
    ├── common.py          # Shared UI constants (COLORS, FONTS)
    ├── gui_main.py        # Main Window (TabbedClientApp class)
    ├── gui_start.py       # Tkinter root initialization
    ├── gui_tabs.py        # Individual profile tab logic (ClientTab class)
    ├── license_viewer.py  # 📜 Always-on-top LICENSE viewer
    ├── readme_viewer.py   # 📄 Always-on-top markdown viewer
    └── progress_popup.py  # 🔔 Bottom-right status notifications

```

---

## ✨ Key Features

* **🚀 Multi-Profile Tabs**: Manage up to 5 unique Headscale environments simultaneously via a clean tabbed interface.
* **📊 Live Traffic Monitoring**: Real-time Sent/Received data tracking with persistent daily totals stored in a local database.
* **🔐 Dual Authentication**: Native support for pre-generated **Auth-Keys** and automated **OIDC (Google SSO)** login flows.
* **📌 Always-on-Top Viewers**: Documentation and License popups remain focused over the main app for easy configuration.
* **🎨 Dynamic Theming**: Toggle between high-contrast Dark and Light themes with consistent widget styling.
* **⚙️ Intelligent Boot**: Automatically monitors and waits for the Tailscale Windows service to initialize before opening.
* **🔔 Progress Tracking**: Real-time step-by-step progress notifications for connection handshakes.

---

## 🚀 Getting Started

### 📋 Prerequisites

* **Tailscale**: The Tailscale backend engine must be installed and the service should be enabled.
* **Headscale Server**: A reachable URL for your private network coordinator.

### 🛠️ Installation & Usage

1. **Clone the Repo**: `git clone https://github.com/user/Tailscale-Headscale-Client.git`
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Launch**: Run `python main.py` or the compiled `.exe` in the `dist/` folder.
4. **Connect**:
* Navigate to `Profile > Add New Profile`.
* Enter your **MAPView VPN URL** and **Auth Key**.
* Click **Connect**.

---

## 🛠 Configuration

* **Auto-Connect**: Enable via `File > Settings` to automatically reconnect the last active profile on launch.
* **Profile Storage**: Profiles and logs are stored locally in `%AppData%/MAPView_VPN_Client` to ensure data persistence.
* **Credentials**: Use the **Change Credentials** button within any tab to update server URLs or security keys on the fly.

---

## 🤝 Contributing

Contributions are welcome! Whether it's adding support for new Tailscale CLI flags or enhancing the CustomTkinter UI, please feel free to submit a Pull Request.

---

## ⚠️ Disclaimer

This project is an independent effort and is **not** officially affiliated with Tailscale Inc. or the Headscale project. Use this software at your own risk. Always ensure you understand the security implications of self-hosting network infrastructure.

