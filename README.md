# Tailscale-Headscale Client Pro (PySide6 Edition)

[![Tailscale](https://img.shields.io/badge/Tailscale-v1.6-blue)](https://tailscale.com) [![PySide6](https://img.shields.io/badge/PySide6-v6.6-green)](https://pyside.org) [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Arean82/Tailscale-Headscale-Client) [![License](https://img.shields.io/badge/License-MIT-orange)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org)

A professional-grade, high-performance GUI client for Tailscale and Headscale. This client combines robust VPN logic with a premium, animated modern interface.

---

## ✨ Full Feature Suite

### 🎨 Visual & UX Excellence
- **Modern Premium UI:** Clean aesthetic featuring vibrant emerald, ruby, indigo, and amber gradients for intuitive interaction.
- **Premium Animations:** 
    - Smooth 500ms startup fade-in.
    - Dynamic "heartbeat" pulse for connection states.
    - Universal fade transitions for all dialog windows.
- **Async Image Caching:** High-performance background loading for README badges and images.
- **Smart Setting Interlocking:** Automatically links **Auto-connect on startup** with **Run at startup** dynamically with user confirmation, providing a high-end automated UX.

### 🛡️ Reliability & Security
- **Delta Traffic Tracking:** Advanced persistence logic to prevent data loss across reboots.
- **Cross-Platform Run on Startup:** Modern, independent, real-time registration supporting Windows Registry keys (`HKCU\...\Run`), macOS Launch Agents, and Linux `.desktop` entries.
- **Single Instance Enforcement:** Prevents process collisions with system-wide locking.
- **Credential Masking:** Secure Auth Key storage with an interactive eye-toggle switch.
- **Silent SSO Flow:** Background URL detection (stdout/stderr) for a seamless browser-based login.

---

## 📁 Visual Project Structure

```text
📂 Tailscale-Headscale-Client/
├── 🖼️ assets/                     # Icons, logos, and branding assets
├── 🎨 pygui/                      # UI Definition Files (.ui)
│   ├── 🪟 dialogs/                # Popup windows
│   │   ├── 📄 about.ui
│   │   ├── 📄 credentials.ui
│   │   ├── 📄 settings.ui
│   │   └── 📄 traffic.ui
│   └── 🖼️ windows/                 # Layouts
│       ├── 📄 main_window.ui
│       └── 📄 tab_widget.ui
├── 💻 src/                        # Core Python Source
│   ├── 🧠 core/                   # Backend Logic
│   │   ├── ⚙️ db_manager.py        # Traffic Persistence
│   │   ├── ⚙️ tailscale.py         # Process & SSO management
│   │   └── ⚙️ cache_manager.py     # Image & State caching
│   ├── 🖥️ ui/                     # PySide6 Implementations
│   │   ├── 🧩 components/          # Shared Dialog Logic
│   │   ├── 🧩 dashboard.py         # Tab View logic
│   │   └── 🧩 main_window.py       # Main Application logic
│   └── 🛠️ utils/                  # Helpers
│       ├── ⚙️ crypto.py            # Key encryption/decryption
│       ├── ⚙️ logger.py            # Event/Activity Logging
│       └── ⚙️ autostart.py         # Native Boot Configuration Manager
├── 📦 TailscaleClient_Installer.iss # Windows Installer Script
├── 📦 build_linux_deb.sh          # Linux Packaging Script
├── 📦 TailscaleClient_Mac.spec      # macOS App Bundle Spec
├── 🚀 main.py                     # Application Entry Point
└── 📖 README.md                   # Documentation
```

---

## 📦 Distribution & Packaging

### 🪟 Windows (Inno Setup)
1. Run `pyinstaller TailscaleClient_OneDir.spec`.
2. Compile `TailscaleClient_Installer.iss` to generate the installer.

### 🐧 Linux (Ubuntu/Debian .deb)
1. Run `pyinstaller TailscaleClient_OneDir.spec`.
2. Run `./build_linux_deb.sh` to generate the `.deb` package.

### 🍎 macOS (.app & .dmg)
1. Run `pyinstaller TailscaleClient_Mac.spec`.
2. Use `hdiutil` to package the `.app` into a `.dmg`.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
