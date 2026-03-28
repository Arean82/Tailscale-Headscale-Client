# pylogic/ui_helpers.py
# Consolidates: gui/utils.py, gui/common.py, gui/themes.py, gui/styles.py, gui/darkstyle.py
# Provides shared utilities, constants, and helpers for the PySide6 GUI layer.

import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader

from config import LOG_DIR
from logic.logger import app_logger

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def resource_path(relative_path: str) -> str:
    """
    Returns absolute path to a resource.
    Works for both dev mode and PyInstaller frozen EXE (_MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_ui(ui_relative_path: str, parent: QWidget = None) -> QWidget:
    """
    Loads a .ui file via QUiLoader and returns the top-level widget.

    Usage:
        ui = load_ui("pygui/dialogs/settings.ui", parent=self)

    The ui_relative_path is resolved through resource_path() so it works
    in both development and frozen EXE environments.
    """
    loader = QUiLoader()
    path = resource_path(ui_relative_path)
    ui_file = QFile(path)
    if not ui_file.open(QIODevice.ReadOnly):
        raise FileNotFoundError(
            f"Cannot open UI file: {path}\n"
            f"QFile error: {ui_file.errorString()}"
        )
    widget = loader.load(ui_file, parent)
    ui_file.close()
    if widget is None:
        raise RuntimeError(
            f"QUiLoader failed to load: {path}\n"
            f"Loader error: {loader.errorString()}"
        )
    return widget


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------

def center_window(parent: QWidget, child: QWidget) -> None:
    """Centers a child window relative to its parent."""
    if parent is None:
        return
    parent_geo = parent.geometry()
    child_geo  = child.geometry()
    x = parent_geo.x() + (parent_geo.width()  - child_geo.width())  // 2
    y = parent_geo.y() + (parent_geo.height() - child_geo.height()) // 2

    screen = parent.screen().availableGeometry()
    x = max(screen.x(), min(x, screen.x() + screen.width()  - child_geo.width()))
    y = max(screen.y(), min(y, screen.y() + screen.height() - child_geo.height()))

    child.move(x, y)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_bytes(size: float) -> str:
    """Converts a byte count to a human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_log.txt")


def write_log(entry: str, level: str = "INFO") -> None:
    """
    Writes an entry to the flat app log file and the global rotating logger.
    Drop-in replacement for the old gui/utils.py write_log.
    """
    # Original flat-file behaviour (preserved)
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            f.write(f"{timestamp} [{level}] {entry}\n")
    except Exception as e:
        print(f"Failed to write log (fallback print): {e} — entry: {entry}")

    # Global rotating logger
    try:
        level_upper = level.upper()
        if level_upper == "ERROR":
            app_logger.error(entry)
        elif level_upper in ("WARNING", "WARN"):
            app_logger.warning(entry)
        elif level_upper == "INFO":
            app_logger.info(entry)
        else:
            app_logger.debug(entry)
    except Exception as e:
        print(f"Failed to write to global app_logger: {e}")


# ---------------------------------------------------------------------------
# Tooltip helper
# ---------------------------------------------------------------------------

def add_tooltip(widget: QWidget, text: str) -> None:
    """Sets a tooltip on a PySide6 widget."""
    widget.setToolTip(text)


# ---------------------------------------------------------------------------
# Theme / colour constants  (from gui/common.py + gui/themes.py)
# ---------------------------------------------------------------------------

COLORS = {
    "bg_dark":  "#1e1e1e",
    "fg_light":  "#d4d4d4",
    "blue":      "#569cd6",
    "green":     "#4ec9b0",
    "gold":      "#dcdcaa",
    "orange":    "#ce9178",
    "danger":    "#f44336",
    "accent":    "#007acc",
}

FONTS = {
    "body": ("Segoe UI", 11),
    "mono": ("Consolas", 11),
}

THEMES = {
    "light": {
        "bgcolor": "#d9d9d9",
        "fgcolor": "black",
    },
    "dark": {
        "bgcolor": "#2e2e2e",
        "fgcolor": "white",
    },
}

# ---------------------------------------------------------------------------
# Qt stylesheet builders  (replaces gui/styles.py + gui/darkstyle.py)
# ---------------------------------------------------------------------------

# Colour tokens for each theme
_STYLE_TOKENS = {
    "light": {
        "bg":           "#d9d9d9",
        "fg":           "#000000",
        "btn_bg":       "#d9d9d9",
        "btn_hover":    "#c9c9c9",
        "btn_disabled": "#cccccc",
        "entry_bg":     "#ffffff",
        "entry_fg":     "#000000",
        "tab_sel":      "#c9c9c9",
        "tab_hover":    "#e0e0e0",
        "connect_bg":   "#4CAF50",
        "connect_hov":  "#45a049",
        "disconn_bg":   "#f44336",
        "disconn_hov":  "#da190b",
        "logout_bg":    "#FF9800",
        "logout_hov":   "#fb8c00",
    },
    "dark": {
        "bg":           "#2e2e2e",
        "fg":           "#ffffff",
        "btn_bg":       "#2e2e2e",
        "btn_hover":    "#444444",
        "btn_disabled": "#555555",
        "entry_bg":     "#444444",
        "entry_fg":     "#ffffff",
        "tab_sel":      "#505050",
        "tab_hover":    "#606060",
        "connect_bg":   "#4CAF50",
        "connect_hov":  "#45a049",
        "disconn_bg":   "#f44336",
        "disconn_hov":  "#da190b",
        "logout_bg":    "#FF9800",
        "logout_hov":   "#fb8c00",
    },
}


def build_stylesheet(theme_name: str = "light") -> str:
    """
    Returns a Qt stylesheet string for the given theme.
    Replaces setup_styles() / setup_dark_styles() from the old codebase.
    """
    t = _STYLE_TOKENS.get(theme_name, _STYLE_TOKENS["light"])
    return f"""
    QMainWindow, QDialog, QWidget {{
        background-color: {t['bg']};
        color: {t['fg']};
        font-family: 'Segoe UI';
        font-size: 9pt;
    }}
    QPushButton {{
        background-color: {t['btn_bg']};
        color: {t['fg']};
        border: 1px solid #888888;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: bold;
    }}
    QPushButton:hover  {{ background-color: {t['btn_hover']}; }}
    QPushButton:disabled {{ background-color: {t['btn_disabled']}; color: #888888; }}

    QPushButton#btn_connect {{
        background-color: {t['connect_bg']}; color: white; border: none;
    }}
    QPushButton#btn_connect:hover {{ background-color: {t['connect_hov']}; }}

    QPushButton#btn_disconnect {{
        background-color: {t['disconn_bg']}; color: white; border: none;
    }}
    QPushButton#btn_disconnect:hover {{ background-color: {t['disconn_hov']}; }}

    QPushButton#btn_logout {{
        background-color: {t['logout_bg']}; color: white; border: none;
    }}
    QPushButton#btn_logout:hover {{ background-color: {t['logout_hov']}; }}

    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {t['entry_bg']};
        color: {t['entry_fg']};
        border: 1px solid #888888;
        border-radius: 3px;
        padding: 3px;
    }}
    QLineEdit:disabled {{ background-color: {t['btn_disabled']}; }}

    QLabel {{
        background-color: transparent;
        color: {t['fg']};
    }}

    QTabWidget::pane {{
        border: none;
        background-color: {t['bg']};
    }}
    QTabBar::tab {{
        background-color: {t['btn_bg']};
        color: {t['fg']};
        padding: 5px 12px;
        font-weight: bold;
        border: none;
    }}
    QTabBar::tab:selected {{ background-color: {t['tab_sel']}; }}
    QTabBar::tab:hover    {{ background-color: {t['tab_hover']}; }}

    QMenuBar {{
        background-color: {t['bg']};
        color: {t['fg']};
    }}
    QMenuBar::item:selected {{ background-color: {t['tab_hover']}; }}
    QMenu {{
        background-color: {t['bg']};
        color: {t['fg']};
    }}
    QMenu::item:selected {{ background-color: {t['tab_sel']}; }}

    QCheckBox {{ color: {t['fg']}; }}
    QScrollBar:vertical {{
        background: {t['bg']}; width: 10px;
    }}
    """
