# utils.py
# This module provides utility functions for the application, such as centering windows,
# formatting bytes, writing logs, and adding tooltips.

import tkinter as tk
import os
from datetime import datetime

# Define the path for the main application log file
# This needs to be consistent with config.py's LOG_DIR
from config import LOG_DIR

# Ensure the log directory exists for write_log
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_log.txt")

def center_window(parent, child, width, height):
    """Centers a Toplevel window relative to its parent window."""
    parent.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    x = parent_x + (parent_width // 2) - (width // 2)
    y = parent_y + (parent_height // 2) - (height // 2)

    screen_width = parent.winfo_screenwidth()
    screen_height = parent.winfo_screenheight()

    if x < 0: x = 0
    if y < 0: y = 0
    if x + width > screen_width: x = screen_width - width
    if y + height > screen_height: x = screen_height - height

    child.geometry(f"{width}x{height}+{int(x)}+{int(y)}")


def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def write_log(entry, level="INFO"):
    """Writes an entry to the main application log file."""
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            f.write(f"{timestamp} [{level}] {entry}\n")
    except Exception as e:
        print(f"Failed to write log (fallback print): {e} - Original entry: {entry}")

def add_tooltip(widget, text, parent=None):
    tooltip = tk.Toplevel(parent or widget)
    tooltip.withdraw()
    tooltip.overrideredirect(True)
    tooltip.attributes("-topmost", True)

    label = tk.Label(
        tooltip, text=text,
        background="lightyellow", borderwidth=1,
        relief="solid", font=("Segoe UI", 8)
    )
    label.pack()

    def show_tooltip(event):
        tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        tooltip.deiconify()

    def hide_tooltip(event):
        tooltip.withdraw()

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)

    widget.tooltip_label = label  # Attach tooltip label for future updates
    widget.tooltip_window = tooltip