# Tailscale-Headscale Client Pro (PySide6 Edition)

[![Tailscale](https://img.shields.io/badge/Tailscale-v1.6-blue)](https://tailscale.com) [![PySide6](https://img.shields.io/badge/PySide6-v6.6-green)](https://pyside.org) [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/Arean82/Tailscale-Headscale-Client) [![License](https://img.shields.io/badge/License-MIT-orange)](LICENSE) [![Python](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org)

A professional-grade, high-performance cross-platform GUI client for Tailscale and Headscale. This client combines robust VPN logic with a premium, animated modern interface following enterprise-level separation of concerns.

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

### ⚡ Power Features & Smart Routing (Advanced Features)
- **Granular Exit Node & Subnet Selection:** Advanced options (`node.ui`) per-profile tab allowing customizable `--exit-node` and `--advertise-routes` parameters.
- **Intelligent Route Auto-Suggestion:** Selecting an exit node instantly queries its advertised IP routes and automatically populates the Subnet Routes field in real-time, eliminating manual copying.
- **Native Multi-Account Switching:** Support for rapid native profile swapping (`tailscale switch`) under 0.5s with zero authentication barriers.
- **Automatic Tab Grouping:** Advanced native-switch profiles are automatically arranged side-by-side at the front of the tab bar for perfect visual organization.
- **Smart Tab Locking Matrix:** Connecting to an active native switch profile automatically locks standard custom-server tabs (greying them out), leaving only compatible instant-switch tabs unlocked for complete session safety.
- **Connection Switch Confirmation:** Sleek warning prompts if attempting to initiate a new connection while another is already active to prevent accidental disconnects.

### 🛡️ Reliability & Security
- **Delta Traffic Tracking:** Advanced persistence logic to prevent data loss across reboots.
- **Cross-Platform Run on Startup:** Modern, independent, real-time registration supporting Windows Registry keys (`HKCU\...\Run`), macOS Launch Agents, and Linux `.desktop` entries.
- **Single Instance Enforcement:** Prevents process collisions with system-wide locking.
- **Credential Masking:** Secure Auth Key storage with an interactive eye-toggle switch.
- **Silent SSO Flow:** Background URL detection (stdout/stderr) for a seamless browser-based login.

---

## 🛠️ Quick Start & Developer Setup

To run and test the application locally, follow these simple steps:

### 1. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Development Client
```bash
python main.py
```

> [!IMPORTANT]
> Ensure the Tailscale background daemon (`tailscaled` on Linux/macOS or the Tailscale Windows Service) is running on your system for the client to establish successful connections.

---

## 📂 Visual Project Structure

```text
📂 Tailscale-Headscale-Client/
├── 🖼️ assets/                     # Icons, logos, and branding assets
├── 🎨 pygui/                      # UI Definition Files (.ui)
│   ├── 🪟 dialogs/                # Popup windows
│   │   ├── 📄 about.ui
│   │   ├── 📄 credentials.ui
│   │   ├── 📄 settings.ui
│   │   ├── 📄 node.ui                 # Exit Node & Switch Profile Dialog
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

## 🏛️ Architecture & Separation of Concerns

This client enforces strict modular design principles separating application-level preferences from connection-level parameters:

| ⚙️ Global Settings Dialog | 🛡️ Per-Profile Advanced Options |
| :--- | :--- |
| **Scope:** Application-wide behavior | **Scope:** Specific profile/connection parameters |
| **Features:** Auto-start on boot, Auto-connect, Global logs, Profile creation limit | **Features:** Exit Node selectors, Subnet Routes, Instant Switch checklist mapping |
| **Aesthetic:** Clean, compact, minimal configuration | **Aesthetic:** Detailed, power-user network configurations |

---

## 📦 Distribution & Packaging

### 🪟 Windows (Inno Setup)
1. Generate the distribution bundle:
   ```bash
   pyinstaller TailscaleClient_OneDir.spec
   ```
2. Compile `TailscaleClient_Installer.iss` using Inno Setup compiler to generate the professional executable installer.

### 🐧 Linux (Ubuntu/Debian .deb)
1. Compile the binaries:
   ```bash
   pyinstaller TailscaleClient_OneDir.spec
   ```
2. Run the packaging shell script to build the `.deb` file:
   ```bash
   chmod +x build_linux_deb.sh
   ./build_linux_deb.sh
   ```

### 🍎 macOS (.app & .dmg)
1. Build the Mac App Bundle:
   ```bash
   pyinstaller TailscaleClient_Mac.spec
   ```
2. Package the generated `.app` bundle into a clean installable `.dmg` image using `hdiutil`.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
