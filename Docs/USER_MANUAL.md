# Tailscale & Headscale Client: Comprehensive User Manual 📖🌐
**Simple, Step-by-Step Guide for Everyday Users, Field Engineers, Remote Workers & IT Admins**

**Document ID:** THC-DOC-USR-5.0  
**Target Audience:** All Skill Levels (Complete Beginner to Advanced Network Engineer)  
**Tone:** Plain-English, Step-by-Step, Enterprise Certified  
**Software Release:** 5.0.0  

---

## 🌟 What is Tailscale & Headscale?

Think of **Tailscale** like a secure, invisible extension cord that connects your laptop, home computer, office workstation, and cloud servers together—no matter where they are in the world.

* **No Port Forwarding Required:** Works behind strict hotel Wi-Fi, mobile hotspots, and corporate firewalls.
* **Direct & Blazing Fast:** Whenever possible, your devices connect directly to each other using state-of-the-art **WireGuard®** encryption.
* **What is Headscale?** Headscale is an open-source, private server you can host yourself instead of using the official Tailscale cloud service. This desktop client supports **both** seamlessly with instant profile switching!

---

## 👤 Who Uses This App? (User Roles)

| Role | What They Use It For | Everyday Workflow |
| :--- | :--- | :--- |
| **Everyday Remote Worker** | Accessing company files, intranets, and remote desktop | Click **Connect** in morning, forget about it all day, click **Disconnect** when done. |
| **Field Engineer / IT Admin** | Managing servers, SSH access, remote diagnostics | Switch between multiple client Tailnets/Headscale instances, monitor peer latencies. |
| **Privacy & Security Conscious User** | Encrypting public Wi-Fi traffic | Route all internet traffic through a trusted home or cloud **Exit Node**. |
| **DevOps / SysAdmin** | Fleet administration & network observability | Inspect mesh peer statuses, latency, direct vs DERP relaying, and manage subnet routing. |

---

## 🚀 Visual Interface Tour

```mermaid
flowchart TD
    classDef top fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#e0e7ff;
    classDef card fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef action fill:#022c22,stroke:#10b981,stroke-width:2px,color:#ecfdf5;

    subgraph Top_Bar ["1️⃣ Profile & Global Control Bar"]
        P_SEL["Active Profile Tabs<br><i>[Office Headscale | Home Tailnet]</i>"]:::top
        BTN_CONN["Primary State Action<br><b>[🟢 Connect] / [🔴 Disconnect]</b>"]:::action
    end

    subgraph Status_Panel ["2️⃣ Connection & Node Telemetry Card"]
        IP["Mesh IPv4 / IPv6<br><b>100.64.0.5 / fd7a:...</b>"]:::card
        NET["Current Tailnet / Controller<br><b>vpn.company.com</b>"]:::card
        EXIT["Active Exit Node<br><b>None (Direct Internet)</b>"]:::card
    end

    subgraph Peer_Grid ["3️⃣ Interactive Mesh Peer Table"]
        COL["Host Name | IP Address | OS / Client | Relay / Latency | Action"]:::card
    end

    Top_Bar --> Status_Panel
    Status_Panel --> Peer_Grid
```

---

## 🛠️ Step-by-Step User Guides

---

### 1. How to Connect to Your Network (First-Time Connection) 🔌

Connecting takes just one click:

1. Open the **Tailscale & Headscale Client** from your Start Menu, Applications folder, or system tray.
2. In the top-right corner, check the large status button:
   - If it says **`Connect`**, click it! (Keyboard shortcut: <kbd>Ctrl</kbd>+<kbd>Return</kbd>).
3. **If using official Tailscale:**
   - Your browser opens to `login.tailscale.com`.
   - Log in using your Google, Microsoft, GitHub, or Apple account.
   - You will see *"Authentication successful! You can close this tab."*
4. The client button turns into **`Disconnect`** and the status badge turns **`Connected (Green)`**.
5. Your computer is now securely linked to your personal mesh network!

---

### 2. How to Add and Switch Between Multiple Profiles 📂

Need to access your **Personal Home Lab** in the morning and **Company Headscale** in the afternoon? Multi-Profile makes switching instantaneous without re-typing credentials!

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant App as 🖥️ Desktop Client
    participant SQLite as 🗄️ SQLite Vault (traffic_stats.db)
    participant Keyring as 🔐 OS Hardware Vault (Keyring)
    participant Tailscale as ⚙️ tailscaled Service

    User->>App: Clicks "+" New Profile Tab
    User->>App: Enters Name: "Corporate Headscale", URL: "https://hs.corp.net"
    App->>SQLite: Saves profile network topology & feature flags
    App->>Keyring: Stores auth key into OS vault under auth_key_<UUIDv4>
    Keyring-->>App: Credential secured with zero plaintext files
    User->>App: Selects "Corporate Headscale" Tab
    App->>Tailscale: Re-authenticates daemon to corporate coordination server
    Tailscale-->>App: New network peer list loaded
    App-->>User: Active: Corporate Headscale (Connected)
```

#### Steps to Add a New Profile:
1. Click the **`➕`** tab button in the tab bar or select **`Profile`** $\to$ **`Add New Profile`**.
2. Enter a unique name for the environment (e.g. `Office Work`, `Home Server`, `Client Lab`).
3. Set your credentials:
   * **Login Server URL:**
     * Leave default (`https://controlplane.tailscale.com`) for official Tailscale SaaS.
     * Enter your sovereign Headscale server URL (e.g. `https://headscale.mycompany.com`).
   * **Authentication Method:**
     * **Pre-Auth Key:** Paste your authentication token (e.g. `tskey-auth-...`). The client immediately delegates it to the native OS Credential Vault (`Windows Credential Manager`, `macOS Keychain`, `Linux SecretService`) indexed by an immutable UUIDv4. Zero plaintext secrets touch your disk.
     * **Web Browser SSO:** Check "Use SSO" for interactive single sign-on browser authorization.
4. Click **`Save`**.
5. **Switching Profiles**: Simply click the profile's tab in the top tab bar. The client handles the background handover cleanly without leaking credentials!

---

### 3. Routing All Internet Through an Exit Node (Public Wi-Fi Protection) 🛡️

When you are at a coffee shop, airport, or hotel, attackers on the same Wi-Fi could try to snoop on your connection. An **Exit Node** sends 100% of your web browsing through an encrypted tunnel to a trusted machine (like your home router or office server).

```mermaid
flowchart LR
    classDef untrusted fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fee2e2;
    classDef tunnel fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef exit fill:#022c22,stroke:#10b981,stroke-width:2px,color:#ecfdf5;

    Laptop["💻 Your Laptop<br>(Airport Wi-Fi)"]:::untrusted
    Tunnel["🔒 Encrypted WireGuard Tunnel<br>(Total Traffic Protection)"]:::tunnel
    ExitNode["🏠 Home or Office Exit Node<br>(Trusted Gateway)"]:::exit
    Web["🌐 Public Internet<br>(Google, Bank, Netflix)"]:::exit

    Laptop ==>|All Traffic Encrypted| Tunnel
    Tunnel ==> ExitNode
    ExitNode ==> Web
```

#### How to Enable an Exit Node:
1. Look at the **`Exit Node`** selector dropdown on the main dashboard.
2. Click the dropdown to see all machines in your network that offer exit routing.
3. Select your chosen node (e.g., `home-pfsense` or `aws-us-east`).
4. **Local LAN Access Checkbox:**
   * ✅ **Checked:** You can still print to local Wi-Fi printers or reach your local smart TV.
   * ⬜ **Unchecked:** Maximum privacy; absolutely all traffic is routed through the remote node.
5. Click **`Apply Exit Node`**. You are now browsing securely!
6. To turn it off, select **`None (Direct)`** and click Apply.

---

### 4. Managing Node Preferences & Application Settings ⚙️

Click the **`Settings`** menu item under **File** $\to$ **Settings** or press <kbd>Ctrl</kbd>+<kbd>,</kbd> to open preferences:

| Setting | What It Does | Recommended State |
| :--- | :--- | :--- |
| **Run on System Startup** | Automatically starts the client when your PC boots. | Optional |
| **Auto-Connect at Launch** | Automatically initiates VPN tunnel connection when application starts. | Optional |
| **Enable Logs** | Writes debug and operational logs to disk in the application directory. | ✅ **Enabled** |
| **Advanced Features** | Enables granular routing, subnet advertisement, exit node settings, and peer dialog. | ✅ **Enabled** |
| **Allow Insecure SSL** | Permits connecting to Headscale servers using self-signed or internal CA certificates. | Homelab / Testing |
| **Global DNS Fallback** | Enables fallback DNS resolution if the Tailnet MagicDNS cannot be reached. | Optional |
| **Check Screen Reader on Startup** | Validates speech synthesis and assistive technology tools on application launch. | For AT Users |

---

### 5. Reading Diagnostics & System Logs 🔍

If you ever encounter an issue or IT support asks for logs:
1. Click **`Logs`** $\to$ **`Global Logs`** in the menu bar.
2. Select any active profile or engine log to open the dedicated **Log Viewer**.
3. Use the search bar at the top to filter for errors or warnings (e.g. `derp`, `handshake`, `expired`).
4. Click **`Copy All`** or **`Export Log...`** to save a timestamped diagnostic file for your support team.

---

### 6. Viewing Software License & Attributions ⚖️

To inspect open-source license agreements and copyright terms:
1. Open the **Help** menu and select **`View License`**.
2. The dedicated License Viewer displays the full legal text of the **GNU General Public License v3.0 (GPLv3)**.
3. The dialog features keyboard-first accessibility: dismiss anytime by pressing <kbd>Esc</kbd>, <kbd>Enter</kbd>, or clicking **`Close`**.

---

## ♿ Accessibility & Keyboard Shortcuts Cheatsheet

This software has been certified under **EN 301 549 (Software Clause 11)** and **WCAG 2.1 Level AA**. Every function is 100% operable using only the keyboard or a screen reader (NVDA, JAWS, Windows Narrator, Apple VoiceOver, Orca).

### Verified Global Keyboard Shortcuts

| Key Combination | Action Scope | Operation |
| :--- | :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Application Global | **Check Screen Reader & AT Setup** (Launches interactive accessibility diagnostics) |

### Universal Focus Navigation & Dialog Controls

All screens and modal dialogs follow logical Qt `<tabstops>` order with visible focus indicators:

| Key Combination | Context | Operation |
| :--- | :--- | :--- |
| <kbd>Tab</kbd> / <kbd>Shift</kbd> + <kbd>Tab</kbd> | All Windows & Dialogs | Step forward/backward through `<tabstops>` focus chain |
| <kbd>Enter</kbd> / <kbd>Return</kbd> | Focused Button or Dialog | Execute focused control or default primary action |
| <kbd>Esc</kbd> | Modal Dialogs | Instantly close dialog and return focus without keyboard trap |
| <kbd>Space</kbd> | Focused Button/Checkbox | Activate or toggle focused control |
| <kbd>Up</kbd> / <kbd>Down</kbd> Arrows | Tables & Lists | Navigate peer items or profile selections |
| <kbd>Alt</kbd> + Underlined Letter | Menu Bar | Access menus (e.g. <kbd>Alt</kbd>+<kbd>F</kbd> for File, <kbd>Alt</kbd>+<kbd>P</kbd> for Profile, <kbd>Alt</kbd>+<kbd>H</kbd> for Help) |

---

## 🎙️ Assistive Technology & Screen Reader Setup (Linux & Windows N)

While Windows (Standard) and macOS include built-in screen readers preconfigured in their OS kernels, specific Linux workstation distributions and Windows "N" European editions may require installing the speech synthesis engine:

### 1. Linux Setup (Ubuntu / Debian / Fedora / Arch)

The client communicates directly with the **Orca Screen Reader** via AT-SPI2 / D-Bus:

* **Ubuntu / Debian / Linux Mint**:
  ```bash
  sudo apt update && sudo apt install -y orca at-spi2-core speech-dispatcher
  ```
* **Fedora / RHEL / CentOS Stream**:
  ```bash
  sudo dnf install -y orca at-spi2-core speech-dispatcher
  ```
* **Arch Linux / Manjaro**:
  ```bash
  sudo pacman -S --noconfirm orca at-spi2-core speech-dispatcher
  ```
* **openSUSE**:
  ```bash
  sudo zypper install -y orca at-spi2-core speech-dispatcher
  ```

> **How to toggle Orca**: Press <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>S</kbd> (or run `orca --replace &` in terminal).

### 2. Windows N Editions (European Media-Free Editions)

Windows N editions require the Windows Media Feature Pack to enable voice synthesis for **Windows Narrator**:

* **Via Settings**: Open **Settings** $\to$ **Apps** $\to$ **Optional Features** $\to$ **Add a feature** $\to$ select **Media Feature Pack** and install.
* **Via Administrator PowerShell**:
  ```powershell
  DISM /Online /Add-Capability /CapabilityName:Media.MediaFeaturePack~~~~0.0.1.0
  ```

> **How to toggle Windows Narrator**: Press <kbd>Win</kbd> + <kbd>Ctrl</kbd> + <kbd>Enter</kbd>.

### 3. Apple macOS (VoiceOver)
Pre-installed into macOS. Toggle anytime with <kbd>Cmd</kbd> + <kbd>F5</kbd> (or triple-click Touch ID).

### 4. Optional Startup Verification & Diagnostics Tool
* **In Settings (File → Settings)**: Toggle **"Check Screen Reader / AT on Startup"** (default: *Disabled*). When enabled, the client inspects whether Orca or speech components are active upon launch and displays remediation guidance if missing.
* **In Network Diagnostics (Advanced → Diagnostics)**: Click **"Check Screen Reader"** at any time to run an instant non-destructive accessibility health check.

---

## ❓ Frequently Asked Questions (FAQ)

#### Q: Does Tailscale slow down my internet connection?
**A:** No! For normal websites (Google, YouTube), your computer connects directly via your standard ISP. Only traffic destined for your private mesh nodes (or when using an Exit Node) goes through the VPN.

#### Q: Why does my status say "Needs Machine Registration"?
**A:** When connecting to a self-hosted Headscale server for the first time, your server administrator must approve your machine. Share the machine key shown on your screen with your administrator, who will run `headscale nodes register`.

#### Q: Can I run this client alongside other VPNs?
**A:** Yes! Because Tailscale uses an isolated overlay network adapter (`100.64.0.0/10`), it operates harmoniously without interfering with standard company VPNs unless both attempt to route the exact same IP subnets.
