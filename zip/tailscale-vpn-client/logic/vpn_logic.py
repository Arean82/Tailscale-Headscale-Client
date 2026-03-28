# logic/vpn_logic.py
# Core logic for managing VPN connections, credentials, profiles, and settings.
# All GUI interactions removed — uses callbacks for any UI feedback.

import os
import sys
import subprocess
import base64
import hashlib
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
import json
import threading
import time

from logic.logger import app_logger

# Import OS-specific mutex functions
from os_specific.mutex_handler import acquire_mutex, release_mutex, set_lock_file_path

# Assuming net_stats.py handles its own platform specifics
from logic.net_stats import log_tailscale_stats

from config import APP_BASE_DIR, APP_DATA_DIR, LOG_DIR

# ---------------------------------------------------------------------------
# Encryption setup
# ---------------------------------------------------------------------------
PASSWORD = "some-hardcoded-passphrase"
KEY      = base64.urlsafe_b64encode(hashlib.sha256(PASSWORD.encode()).digest())
fernet   = Fernet(KEY)

# ---------------------------------------------------------------------------
# Paths  (re-derived here for backward-compat with existing callers)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    APP_BASE_DIR = os.path.join(os.environ.get("APPDATA"), "Tailscale_VPN_Client")
elif sys.platform.startswith("linux"):
    APP_BASE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
else:
    APP_BASE_DIR = os.path.join(os.path.expanduser("~"), "Tailscale_VPN_Client")

APP_DATA_DIR  = os.path.join(APP_BASE_DIR, "data")
LOG_DIR       = os.path.join(APP_BASE_DIR, "log")
TAB_NAMES_FILE = os.path.join(APP_DATA_DIR, "tab_names.json")
LAST_TAB_FILE  = os.path.join(APP_DATA_DIR, "last_tab.json")
LOG_FILE       = os.path.join(LOG_DIR, "app_log.txt")
LOCK_FILE      = os.path.join(APP_BASE_DIR, "app.lock")
SETTINGS_FILE  = os.path.join(APP_BASE_DIR, "settings.json")

# Set lock file path for mutex handler
set_lock_file_path(LOCK_FILE)

# ---------------------------------------------------------------------------
# Storage initialisation
# ---------------------------------------------------------------------------

def check_tailscale_installed() -> bool:
    """Checks if Tailscale CLI is installed and in PATH."""
    return shutil.which("tailscale") is not None


def initialize_app_storage(error_callback=None) -> None:
    """
    Ensures the main application directories exist.
    Calls error_callback(message) instead of showing a messagebox.
    """
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception as e:
        msg = f"Could not create application directories:\n{e}"
        if error_callback:
            error_callback(msg)
        else:
            app_logger.error(msg)
            sys.exit(1)


initialize_app_storage()

# ---------------------------------------------------------------------------
# Tab / profile directory helpers
# ---------------------------------------------------------------------------

def get_tab_dir(tab_name: str) -> str:
    if not tab_name:
        raise ValueError("Tab name cannot be empty.")
    sanitized = "".join(c for c in tab_name if c.isalnum() or c in (" ", ".", "_", "-")).strip()
    sanitized = sanitized.replace(" ", "_")
    if not sanitized:
        raise ValueError("Sanitized tab name is empty. Please use valid characters.")
    return os.path.join(APP_DATA_DIR, sanitized)


def get_file_path(base_filename: str, tab_name: str) -> str:
    tab_dir = get_tab_dir(tab_name)
    os.makedirs(tab_dir, exist_ok=True)
    return os.path.join(tab_dir, base_filename)

# ---------------------------------------------------------------------------
# Profile logging
# ---------------------------------------------------------------------------

def write_log(entry: str, level: str = "INFO") -> None:
    """Writes an entry to the flat app log. Imported by other modules."""
    try:
        with open(LOG_FILE, "a") as f:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            f.write(f"{timestamp} [{level}] {entry}\n")
    except Exception as e:
        print(f"Failed to write log: {e} — entry: {entry}")


def write_profile_log(tab_name: str, entry: str, level: str = "DEBUG") -> None:
    """Writes a log entry to the profile's connection.log and global logger."""
    try:
        log_path = get_file_path("connection.log", tab_name)
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with open(log_path, "a") as f:
            f.write(f"{timestamp} [{level}] {entry}\n")
    except Exception as e:
        write_log(f"Error writing profile log for '{tab_name}': {e}", level="ERROR")

    try:
        from logic.logger import get_profile_logger
        prof_logger = get_profile_logger(tab_name)
        level_upper = level.upper()
        if level_upper == "INFO":
            prof_logger.info(entry)
        elif level_upper == "ERROR":
            prof_logger.error(entry)
        elif level_upper in ("WARNING", "WARN"):
            prof_logger.warning(entry)
        else:
            prof_logger.debug(entry)
    except Exception as e:
        app_logger.error(f"Failed to write to global profile logger for {tab_name}: {e}")

# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def encrypt_key(plain_text_key: str) -> str:
    return fernet.encrypt(plain_text_key.encode()).decode()


def decrypt_key(encrypted_key: str) -> str:
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# Credential persistence
# ---------------------------------------------------------------------------

def load_saved_url(tab_name: str) -> str:
    try:
        url_file = get_file_path("Tailscale_VPN_url", tab_name)
        if os.path.exists(url_file):
            with open(url_file, "r") as f:
                return f.read().strip()
    except Exception as e:
        write_log(f"Error loading saved URL for '{tab_name}': {e}", level="ERROR")
    return ""


def save_url(url: str, tab_name: str) -> None:
    try:
        with open(get_file_path("Tailscale_VPN_url", tab_name), "w") as f:
            f.write(url.strip())
    except Exception as e:
        write_log(f"Error saving URL for '{tab_name}': {e}", level="ERROR")


def load_saved_key(tab_name: str) -> str:
    try:
        key_file = get_file_path("Tailscale_VPN_key", tab_name)
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                return decrypt_key(f.read().strip())
    except Exception as e:
        write_log(f"Error loading saved key for '{tab_name}': {e}", level="ERROR")
    return ""


def save_key(key: str, tab_name: str) -> None:
    try:
        with open(get_file_path("Tailscale_VPN_key", tab_name), "w") as f:
            f.write(encrypt_key(key.strip()))
    except Exception as e:
        write_log(f"Error saving key for '{tab_name}': {e}", level="ERROR")

# ---------------------------------------------------------------------------
# Auth mode
# ---------------------------------------------------------------------------

def save_auth_mode(tab_name: str, mode: str) -> None:
    try:
        with open(get_file_path("auth_mode", tab_name), "w") as f:
            f.write(mode.strip())
    except Exception as e:
        write_log(f"Error saving auth mode for '{tab_name}': {e}", level="ERROR")


def get_auth_mode(tab_name: str) -> str:
    mode_file = get_file_path("auth_mode", tab_name)
    if os.path.exists(mode_file):
        try:
            with open(mode_file, "r") as f:
                return f.read().strip()
        except Exception:
            return "auth_key"
    return "auth_key"


def is_sso_mode(tab_name: str) -> bool:
    return get_auth_mode(tab_name).lower() == "google"

# ---------------------------------------------------------------------------
# Tab name persistence
# ---------------------------------------------------------------------------

def load_tab_names() -> dict:
    try:
        if os.path.exists(TAB_NAMES_FILE):
            with open(TAB_NAMES_FILE, "r") as f:
                return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        write_log(f"Error loading tab names: {e}", level="ERROR")
    return {}


def save_tab_names(tab_id_to_name_map: dict) -> None:
    try:
        with open(TAB_NAMES_FILE, "w") as f:
            json.dump(tab_id_to_name_map, f)
    except Exception as e:
        write_log(f"Error saving tab names: {e}", level="ERROR")


def load_last_selected_tab_id():
    try:
        if os.path.exists(LAST_TAB_FILE):
            with open(LAST_TAB_FILE, "r") as f:
                return json.load(f).get("last_selected_tab_id")
    except Exception as e:
        write_log(f"Error loading last selected tab ID: {e}", level="ERROR")
    return None


def save_last_selected_tab_id(tab_id) -> None:
    try:
        with open(LAST_TAB_FILE, "w") as f:
            json.dump({"last_selected_tab_id": tab_id}, f)
    except Exception as e:
        write_log(f"Error saving last selected tab ID: {e}", level="ERROR")

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            write_log(f"Failed to load settings: {e}", level="ERROR")
    return {"auto_connect": False, "theme": "light", "enable_logs": False}


def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        write_log(f"Failed to save settings: {e}", level="ERROR")

# ---------------------------------------------------------------------------
# Log rotation
# ---------------------------------------------------------------------------

def rotate_log() -> None:
    if not os.path.exists(LOG_FILE):
        return
    try:
        file_mtime = datetime.fromtimestamp(os.path.getmtime(LOG_FILE))
        now = datetime.now()
        if file_mtime.month != now.month or file_mtime.year != now.year:
            archive = os.path.join(LOG_DIR, f"vpn_connect_{file_mtime.strftime('%Y_%m')}.log")
            if not os.path.exists(archive):
                os.rename(LOG_FILE, archive)
    except Exception as e:
        write_log(f"Log rotation error: {e}", level="ERROR")


rotate_log()

# ---------------------------------------------------------------------------
# Auto-connect  (Qt-compatible — uses QTimer.singleShot via callback)
# ---------------------------------------------------------------------------

def auto_connect_if_enabled(app, last_tab_id) -> None:
    """
    Auto-connect VPN on startup if enabled in settings.
    'app' is expected to be the Qt AppController instance which exposes:
      - app.tabs  : dict[tab_id -> tab_controller]
      - app.select_tab(tab_id)
      - app.update_tab_states()
    Uses QTimer.singleShot so it remains GUI-thread-safe.
    """
    from PySide6.QtCore import QTimer

    settings = load_settings()
    if not settings.get("auto_connect", False):
        return

    def _do_connect(tab_controller):
        app.update_tab_states()
        if hasattr(tab_controller, "connect_vpn"):
            QTimer.singleShot(500, tab_controller.connect_vpn)

    if last_tab_id is not None and last_tab_id in app.tabs:
        app.select_tab(last_tab_id)
        _do_connect(app.tabs[last_tab_id])
    elif app.tabs:
        first_id = sorted(app.tabs.keys())[0]
        app.select_tab(first_id)
        _do_connect(app.tabs[first_id])
