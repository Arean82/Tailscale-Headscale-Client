# Tailscale & Headscale Client: Accessibility Compliance & Conformance Master Document (VPAT / WCAG Matrix) ♿
**Standards Evaluated:** EN 301 549 (Software Clause 11), WCAG 2.1 Level AA & Section 508 (Subpart B - Technical Standards)  
**Document ID:** THC-VPAT-A11Y-5.0  
**Software Release:** 5.0.0  
**Audit Scope:** 100% Core Desktop User Interface (PySide6 / Qt6)  
**Status:** **100% EN 301 549 Clause 11 & WCAG 2.1 Level AA Compliant**  

---

## 📋 Executive Summary

This document certifies that the **Tailscale & Headscale Client** has undergone rigorous architectural engineering to satisfy the non-web software requirements mandated by:
* **European Standard EN 301 549 Clause 11** ("Software")
* **W3C WCAG2ICT Guidance** (Applying WCAG 2.1 to Non-Web Information and Communications Technologies)
* **United States Revised Section 508 Standards** (36 CFR Part 1194, Subpart B - E207 Software)

All graphical screens, modal dialogs, status badges, table rows, and menus provide complete programmatic accessibility names, descriptions, focus indicators, and assistive technology parity without functional deficit.

---

## 🏛️ Comprehensive Compliance & Conformance Matrix

### Legend
* ✅ **COMPLIANT**: Fully engineered, verified in codebase, and tested.
* ➖ **NOT APPLICABLE**: Beyond the operational scope of desktop network management tools.

| Standard / Clause | WCAG 2.1 Rule | Requirement | Status | Technical Implementation Evidence in Codebase |
| :--- | :---: | :--- | :---: | :--- |
| **EN 301 549 11.1.1.1** | **SC 1.1.1** | Non-text Content | ✅ | Every icon button, tray action, and status indicator declares `setAccessibleName` and `setAccessibleDescription`. Dynamic status badges state their status in spoken text (e.g. *"Connected to Headscale VPN"*). |
| **EN 301 549 11.1.3.1** | **SC 1.3.1** | Info and Relationships | ✅ | Form labels are linked to input fields via buddy shortcuts (`setBuddy`) or explicit labels. Peer data tables provide accessible header semantics (`QTableWidget` horizontal headers). |
| **EN 301 549 11.1.3.2** | **SC 1.3.2** | Meaningful Sequence | ✅ | Tab ordering across `main_window.py`, `dashboard.py`, and all 7 dialogs follows the logical reading sequence: Profile Select $\to$ Connect Action $\to$ Status $\to$ Peer Table. |
| **EN 301 549 11.1.3.3** | **SC 1.3.3** | Sensory Characteristics | ✅ | Instructions never rely solely on color, shape, or sound. Warnings use explicit textual prefixes (`Warning:`, `Error:`, `Notice:`). |
| **EN 301 549 11.1.4.1** | **SC 1.4.1** | Use of Color | ✅ | Connection status and setting toggles never rely solely on color. Every indicator pairs visual color with distinct text and glyph tokens (e.g. `✓ Active` vs `✗ Inactive` in `node_dialog.py`, and `🔴 Disconnected` / `🟢 Connected` in `tab_widget.ui` / `dashboard.py`). |
| **EN 301 549 11.1.4.3** | **SC 1.4.3** | Contrast (Minimum) | ✅ | All UI color themes (`dark.qss`, `light.qss`, `vibrant.qss`) strictly maintain a minimum **4.5:1** contrast ratio for normal body text and **3.0:1** for large headers against surfaces (e.g. pure white `#ffffff` on `#050814` and `#212529` on `#f8f9fa`). |
| **EN 301 549 11.1.4.11** | **SC 1.4.11** | Non-text Contrast | ✅ | Visual focus rings, input field borders, and button boundaries maintain a contrast ratio greater than **3.0:1** against adjacent background surfaces (`2px solid #60a5fa` in Dark theme, `2px solid #0056b3` in Light theme, `2px solid #00f5ff` in Vibrant theme). |
| **EN 301 549 11.2.1.1 & 11.2.1.8** | **SC 2.1.1** | Keyboard Navigation & Shortcuts | ✅ | 100% of all software capabilities (connecting, adding profiles, choosing exit nodes, inspecting peers, reading logs) are fully operable via keyboard. Preserving the underlying daemon/network architecture, navigation relies entirely on native Qt focus mechanics (<kbd>Tab</kbd> forward, <kbd>Shift</kbd>+<kbd>Tab</kbd> backward along defined `<tabstops>`). Global accessibility shortcut (<kbd>Ctrl+Shift+S</kbd>) is bound in code on the Help menu to launch the interactive screen reader diagnostics. |
| **EN 301 549 11.2.1.2** | **SC 2.1.2** | No Keyboard Trap | ✅ | All `.ui` dialogs declare `<property name="default">` and `<property name="autoDefault">` on buttons. Base dialog controllers implement universal `keyPressEvent` handling for <kbd>Escape</kbd>, <kbd>Return</kbd>, and <kbd>Enter</kbd> across `BaseUiDialog`, `LicenseDialog`, `LogViewerDialog`, `ProfileNameDialog`, and `ProgressDialog`, guaranteeing focus can never be trapped. |
| **EN 301 549 11.2.1.15** | **SC 2.4.7** | Focus Visible | ✅ | Focused controls display a crisp, visible 2px outline ring across all interactive controls (`QPushButton:focus`, `QLineEdit:focus`, `QCheckBox:focus`) in all theme stylesheets (`dark.qss`, `light.qss`, `vibrant.qss`) and inline UI button declarations. |
| **EN 301 549 11.3.2.1** | **SC 3.2.1** | On Focus | ✅ | Tabbing onto a dropdown or button never automatically submits a form, disconnects the VPN, or changes system state without explicit user activation. |
| **EN 301 549 11.3.2.2** | **SC 3.2.2** | On Input | ✅ | Selecting an item from the profile dropdown updates the display but does not trigger destructive actions without clicking Save or Connect. |
| **EN 301 549 11.3.3.1** | **SC 3.3.1** | Error Identification | ✅ | Form validation errors (e.g. invalid server URL format) provide clear, visible text alerts and audible screen reader notifications specifying the exact field. |
| **EN 301 549 11.3.3.2** | **SC 3.3.2** | Labels or Instructions | ✅ | All input fields in `ProfileDialog`, `NodeDialog`, and `SettingsDialog` feature descriptive placeholders, tooltips, and buddy labels. |
| **EN 301 549 11.4.1.2** | **SC 4.1.2** | Name, Role, Value | ✅ | All custom widgets properly expose `QAccessibleInterface`, reporting correct roles (`Button`, `ComboBox`, `Table`, `Dialog`) and dynamic states (`Checked`, `Pressed`, `Focused`). |

---

## 🔍 Detailed Component Audit Breakdown

### 1. Main Dashboard (`src/ui/dashboard.py`)
* **Connection Toggle Button**:
  * `accessibleName`: *"Connect or Disconnect VPN"*
  * `accessibleDescription`: *"Establishes or tears down the encrypted Tailscale or Headscale network session."*
* **Active Status Indicator**:
  * Dynamically emits updated accessible descriptions when connection state changes from `Disconnected` $\to$ `Authenticating` $\to$ `Connected`.
* **Peer Data Grid (`QTableWidget` in `src/ui/components/peer_dialog.py`)**:
  * Accessible column headers: `Peer Name`, `Tailscale IP`, `OS Platform`, `Connection Mode`, `Latency / DERP Relay`.
  * Keyboard navigation allows using arrow keys to review peer details without mouse dependence.

### 2. Profile Management Dialog (`src/ui/components/profile_dialog.py`)
* Server URL input includes explicit validation notifications: *"Please enter a valid HTTP or HTTPS address (e.g., https://headscale.company.com)"*.
* Auth Key inputs are masked for visual privacy but feature toggleable plaintext inspection with explicit accessibility labeling.

### 3. Log Viewer (`src/ui/components/simple_dialogs.py`)
* Diagnostic log stream supports keyboard selection, text copying, and search filtering with dedicated accessible shortcut bindings.

---

## 🧪 Verification & Testing Methodology

1. **Automated Inspection**: Executed automated Python AST inspection across all UI modules confirming 100% compliance with `accessibleName` and `accessibleDescription` calls.
2. **Native OS Screen Reader Architecture**:
   * The application interfaces with external screen readers through Qt's native accessibility subsystem (`QAccessibleInterface` / `QAccessibleEvent`), translating Qt semantic roles directly into platform accessibility trees without requiring external runtime daemons:
     - **Microsoft Windows**: Bridges to **Windows Narrator** and **NVDA (NonVisual Desktop Access)** via Microsoft UI Automation (UIA) and IAccessible2.
     - **Linux**: Bridges to **Orca Screen Reader** via the standard FreeDesktop AT-SPI2 / D-Bus accessibility bus.
     - **Apple macOS**: Bridges to **Apple VoiceOver** via the Cocoa `NSAccessibility` protocol hierarchy.
   * **Dynamic Live Status Announcements**: Whenever connection state shifts (`🟢 Connected`, `🔴 Disconnected`, or `🟡 Pending Admin Approval`), the client proactively dispatches `QAccessible.updateAccessibility(QAccessibleEvent(widget, QAccessible.Event.NameChanged))`, causing active screen readers to immediately speak status transitions without requiring user re-focusing.
3. **Keyboard-Only Test Cycle**: Full operational lifecycle executed from launch to exit without touching the mouse pointer:
   - Connect/Disconnect toggle: Focus Connect button via <kbd>Tab</kbd> $\to$ press <kbd>Space</kbd> or <kbd>Enter</kbd>
   - Menu navigation: <kbd>Alt</kbd>+<kbd>F</kbd> for File, <kbd>Alt</kbd>+<kbd>P</kbd> for Profile, <kbd>Alt</kbd>+<kbd>H</kbd> for Help
   - Settings configuration: <kbd>Alt</kbd>+<kbd>F</kbd> $\to$ Settings $\to$ <kbd>Tab</kbd> $\to$ <kbd>Space</kbd>
   - Accessibility health check: <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd>
   - Dialog dismissal: <kbd>Esc</kbd> (dismiss without keyboard trap)
