# UI Modification Guide: Window Sizes & Resizing

This document outlines exactly where and how to modify the window dimensions and resizing behavior for the Tailscale Client Pro application.

---

## 1. Main Window Dimensions
To modify the main window's size or prevent the user from resizing it, edit `src/ui/main_window.py`.

### Change Initial/Minimum Size
*   **File**: `src/ui/main_window.py`
*   **Lines 37-39**: 
    ```python
    37:         self.setMinimumSize(self.ui_window.minimumSize())
    38:         self.setMaximumSize(self.ui_window.maximumSize())
    39:         self.resize(self.ui_window.size())
    ```
*   **Action**: Replace these with specific values, e.g.:
    ```python
    self.resize(500, 600)
    ```

### Disable Main Window Resizing
*   **Action**: Add the following line after `self.resize(...)`:
    ```python
    self.setFixedSize(self.size()) 
    # OR specify exact dimensions:
    self.setFixedSize(500, 600)
    ```

---

## 2. Dialog Window Sizes (Popups)
Dialog sizes are managed in `src/ui/components/simple_dialogs.py`.

### Traffic Statistics Dialog
*   **File**: `src/ui/components/simple_dialogs.py`
*   **Line 120** (inside `__init__`):
    ```python
    119:         super().__init__("traffic.ui", parent)
    ```
*   **Action**: Add your size constraints immediately after `super().__init__`:
    ```python
    self.resize(450, 500)
    self.setFixedSize(450, 500) # Prevents resizing
    ```

### Readme / Documentation Dialog
*   **File**: `src/ui/components/simple_dialogs.py`
*   **Line 53**:
    ```python
    53:         self.resize(1000, 800)
    ```
*   **Action**: Change the numbers to your preferred width and height.

### License Dialog
*   **File**: `src/ui/components/simple_dialogs.py`
*   **Line 128**:
    ```python
    128:         self.resize(600, 450)
    ```

---

## 3. Settings & Credentials Dialogs
These dialogs currently take their size from the `.ui` files. To enforce a specific size or stop resizing in code:

### Profile/Credentials Dialog
*   **File**: `src/ui/components/profile_dialog.py`
*   **Line 9** (inside `__init__`):
    *   Add `self.setFixedSize(400, 300)` to stop resizing.

### Settings Dialog
*   **File**: `src/ui/components/settings_dialog.py`
*   **Line 11** (inside `__init__`):
    *   Add `self.setFixedSize(350, 400)` to stop resizing.

---

## Technical Tip: Stopping All Resizing
In Qt, to completely lock a window's size, the most effective method is:
```python
self.setFixedSize(WIDTH, HEIGHT)
```
If you want to lock it to whatever size it currently is (after loading from UI):
```python
self.setFixedSize(self.size())
```
