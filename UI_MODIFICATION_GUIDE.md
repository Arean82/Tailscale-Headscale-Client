# UI Modification Guide: Window Sizes & Resizing

This document outlines exactly where and how to modify the window dimensions for the Tailscale Client Pro application. **By default, all windows are non-resizable (Fixed Size) to maintain a consistent professional layout.**

---

## 1. Main Window Dimensions
*   **File**: `src/ui/main_window.py`
*   **Line 37**: 
    ```python
    self.setFixedSize(420, 280)
    ```
*   **Action**: Change the numbers (Width, Height) to your preference.

---

## 2. Dialog Window Sizes (Popups)
Dialog sizes are managed in `src/ui/components/`.

### Simple Dialogs (About, Readme, Traffic, License)
*   **File**: `src/ui/components/simple_dialogs.py`
*   **Action**: Look for `self.setFixedSize(W, H)` in the `__init__` method of each class:
    *   **AboutDialog**: `self.setFixedSize(360, 280)`
    *   **ReadmeDialog**: `self.setFixedSize(1000, 800)`
    *   **TrafficDialog**: `self.setFixedSize(450, 500)`
    *   **LicenseDialog**: `self.setFixedSize(600, 450)`

### Profile/Credentials Dialog
*   **File**: `src/ui/components/profile_dialog.py`
*   **Action**: `self.setFixedSize(300, 200)`

### Profile Name Dialog (Add Profile)
*   **File**: `src/ui/components/profile_name_dialog.py`
*   **Action**: `self.setFixedSize(360, 150)`

### Settings Dialog
*   **File**: `src/ui/components/settings_dialog.py`
*   **Action**: `self.setFixedSize(340, 200)`

### Log Viewer Dialog
*   **File**: `src/ui/components/log_viewer_dlg.py`
*   **Action**: `self.setFixedSize(900, 650)`

---

## 3. Modifying Data Lists (Tables)
When displaying logs or structured history (like in the Traffic Dialog), we use `QTableWidget`.

### Changing Table Appearance
*   **Edit alternating colors**: In the `.ui` file or code, set `alternatingRowColors` to `True`.
*   **Column behavior**: To change how columns resize, modify the `setSectionResizeMode` in `simple_dialogs.py`.
    *   `Stretch`: Fill all available space.
    *   `ResizeToContents`: Adjust based on data width.

---

## Technical Tip: Enabling Resizing
If you want to allow the user to resize a window again:
1. Replace `self.setFixedSize(W, H)` with `self.resize(W, H)`.
2. Ensure you haven't set `setMaximumSize` or `setMinimumSize` to the same values.

