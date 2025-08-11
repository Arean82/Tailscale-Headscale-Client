# vpn_logic.py
# This module contains the core logic for managing VPN connections, including
# handling credentials, saving/loading profiles, and executing Tailscale commands.

import os
import sys
import subprocess # Keep for run_command in TailscaleClient
import base64
import hashlib
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
import json
import threading
import time
from tkinter import messagebox


# Import OS-specific mutex functions
from os_specific.mutex_handler import acquire_mutex, release_mutex, set_lock_file_path

# Assuming net_stats.py is available and handles its own platform specifics
from net_stats import log_tailscale_stats
from utils import write_log

from config import APP_BASE_DIR, APP_DATA_DIR, LOG_DIR

# --- Global Configuration and Utilities ---
PASSWORD = "some-hardcoded-passphrase" # Consider getting this more securely
KEY = base64.urlsafe_b64encode(hashlib.sha256(PASSWORD.encode()).digest())
fernet = Fernet(KEY)

# Secure File Path Setup (OS-agnostic base directory)
if sys.platform == "win32":
    APP_BASE_DIR = os.path.join(os.environ.get('APPDATA'), "Tailscale_VPN_Client")
elif sys.platform.startswith("linux"):
    APP_BASE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
else:
    APP_BASE_DIR = os.path.join(os.path.expanduser("~"), "Tailscale_VPN_Client")

APP_DATA_DIR = os.path.join(APP_BASE_DIR, "data")
LOG_DIR = os.path.join(APP_BASE_DIR, "log")
TAB_NAMES_FILE = os.path.join(APP_DATA_DIR, "tab_names.json")
LAST_TAB_FILE = os.path.join(APP_DATA_DIR, "last_tab.json")
LOG_FILE = os.path.join(LOG_DIR, "app_log.txt")
LOCK_FILE = os.path.join(APP_BASE_DIR, "app.lock") # Lock file in base directory
SETTINGS_FILE = os.path.join(APP_BASE_DIR, "settings.json")

# Set the lock file path for the mutex handler (important for Linux)
set_lock_file_path(LOCK_FILE)

# --- General Utilities ---
def check_tailscale_installed():
    """Checks if Tailscale CLI is installed and in PATH."""
    return shutil.which("tailscale") is not None

def initialize_app_storage():
    """Ensures the main application directories exist."""
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception as e:
        messagebox.showerror("Storage Error", f"Could not create application directories:\n{e}")
        sys.exit(1)

# Initialize storage upon import/startup
initialize_app_storage()

def get_tab_dir(tab_name):
    """Returns the specific directory for a given tab name within APP_DATA_DIR."""
    if not tab_name:
        raise ValueError("Tab name cannot be empty for directory creation.")
    sanitized_name = "".join(c for c in tab_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
    sanitized_name = sanitized_name.replace(' ', '_')
    if not sanitized_name:
        raise ValueError("Sanitized tab name is empty. Please use valid characters.")
    return os.path.join(APP_DATA_DIR, sanitized_name)

def get_file_path(base_filename, tab_name):
    """Generates a file path within a tab's specific directory."""
    tab_dir = get_tab_dir(tab_name)
    os.makedirs(tab_dir, exist_ok=True)
    return os.path.join(tab_dir, base_filename)



def write_profile_log(tab_name, entry, level="DEBUG"):
    """Writes a debug-level log entry to the profile's connection.log."""
    try:
        log_path = get_file_path("connection.log", tab_name)
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with open(log_path, "a") as f:
            f.write(f"{timestamp} [{level}] {entry}\n")
    except Exception as e:
        write_log(f"Error writing profile log for '{tab_name}': {e}", level="ERROR")

def encrypt_key(plain_text_key):
    """Encrypts the given plain text key."""
    return fernet.encrypt(plain_text_key.encode()).decode()

def decrypt_key(encrypted_key):
    """Decrypts the given encrypted key."""
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except Exception:
        return ""

def load_saved_url(tab_name):
    """Loads a URL specific to a tab's name."""
    try:
        url_file = get_file_path("Tailscale_VPN_url", tab_name)
        if os.path.exists(url_file):
            with open(url_file, 'r') as f:
                return f.read().strip()
    except Exception as e:
        write_log(f"Error loading saved URL for profile '{tab_name}': {e}", level="ERROR")
    return ""

def save_url(url, tab_name):
    """Saves a URL specific to a tab's name."""
    try:
        url_file = get_file_path("Tailscale_VPN_url", tab_name)
        with open(url_file, 'w') as f:
            f.write(url.strip())
    except Exception as e:
        write_log(f"Error saving URL for tab '{tab_name}': {e}", level="ERROR")

def load_saved_key(tab_name):
    """Loads an encrypted key specific to a tab's name."""
    try:
        key_file = get_file_path("Tailscale_VPN_key", tab_name)
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                encrypted = f.read().strip()
                return decrypt_key(encrypted)
    except Exception as e:
        write_log(f"Error loading saved key for profile '{tab_name}': {e}", level="ERROR")
    return ""

def save_key(key, tab_name):
    """Saves an encrypted key specific to a tab's name."""
    try:
        key_file = get_file_path("Tailscale_VPN_key", tab_name)
        with open(key_file, 'w') as f:
            f.write(encrypt_key(key.strip()))
    except Exception as e:
        write_log(f"Error saving key for profile '{tab_name}': {e}", level="ERROR")

def load_tab_names():
    """Loads the dictionary mapping tab IDs to tab names."""
    try:
        if os.path.exists(TAB_NAMES_FILE):
            with open(TAB_NAMES_FILE, 'r') as f:
                return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        write_log(f"Error loading tab names: {e}", level="ERROR")
    return {}

def save_tab_names(tab_id_to_name_map):
    """Saves the dictionary mapping tab IDs to tab names."""
    try:
        with open(TAB_NAMES_FILE, 'w') as f:
            json.dump(tab_id_to_name_map, f)
    except Exception as e:
        write_log(f"Error saving tab names: {e}", level="ERROR")

def load_last_selected_tab_id():
    """Loads the ID of the last selected tab."""
    try:
        if os.path.exists(LAST_TAB_FILE):
            with open(LAST_TAB_FILE, 'r') as f:
                data = json.load(f)
                return data.get("last_selected_tab_id")
    except Exception as e:
        write_log(f"Error loading last selected tab ID: {e}", level="ERROR")
    return None

def save_last_selected_tab_id(tab_id):
    """Saves the ID of the last selected tab."""
    try:
        with open(LAST_TAB_FILE, 'w') as f:
            json.dump({"last_selected_tab_id": tab_id}, f)
    except Exception as e:
        write_log(f"Error saving last selected tab ID: {e}", level="ERROR")

# vpn_logic.py (add near your other utils)
def save_auth_mode(tab_name, mode):
    """Saves the authentication mode (e.g., 'google' or 'auth_key') for a tab."""
    try:
        mode_file = get_file_path("auth_mode", tab_name)
        with open(mode_file, 'w') as f:
            f.write(mode.strip())
    except Exception as e:
        write_log(f"Error saving auth mode for tab '{tab_name}': {e}", level="ERROR")

def get_auth_mode(tab_name):
    from vpn_logic import get_file_path  # or move this to top if already imported
    mode_file = get_file_path("auth_mode", tab_name)
    if os.path.exists(mode_file):
        with open(mode_file, "r") as f:
            return f.read().strip()
    return "auth_key"  # default fallback

def is_sso_mode(tab_name):
    return get_auth_mode(tab_name).lower() == "google"



# Log Rotation (main log file)
def rotate_log():
    """Rotates the main application log file if it's from a different month/year."""
    if not os.path.exists(LOG_FILE):
        return
    try:
        file_mtime = datetime.fromtimestamp(os.path.getmtime(LOG_FILE))
        now = datetime.now()
        if file_mtime.month != now.month or file_mtime.year != now.year:
            archive_name = os.path.join(LOG_DIR, f"vpn_connect_{file_mtime.strftime('%Y_%m')}.log")
            if not os.path.exists(archive_name):
                os.rename(LOG_FILE, archive_name)
    except Exception as e:
        write_log(f"Log rotation error: {e}", level="ERROR")

# Call log rotation once on startup
rotate_log()

# Load and save settings
def load_settings():
    """Load settings from JSON file or return defaults."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            write_log(f"Failed to load settings: {e}", level="ERROR")
    # Default settings
    return {
        "auto_connect": False
    }

def save_settings(settings):
    """Save settings dictionary to JSON file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        write_log(f"Failed to save settings: {e}", level="ERROR")

# Auto-connect logic
# This function should be called at application startup to check if auto-connect is enabled
# and to attempt to connect to the last used tab if applicable.
# It assumes that the application has a reference to the main app object and the last tab ID
# is stored in LAST_TAB_FILE.
def auto_connect_if_enabled(app, last_tab_id):
    """Auto-connect VPN on startup if enabled in settings."""
    settings = load_settings()
    if not settings.get("auto_connect", False):
        return  # Do nothing if disabled

    # Try to select last tab and auto-connect
    if last_tab_id is not None and last_tab_id in app.tabs:
        for tab_frame_id in app.notebook.tabs():
            tab_widget = app.notebook.nametowidget(tab_frame_id)
            if hasattr(tab_widget, 'tab_id') and tab_widget.tab_id == last_tab_id:
                app.notebook.select(tab_frame_id)
                app.update_tab_states()
                if hasattr(tab_widget, "connect_vpn"):
                    app.after(500, tab_widget.connect_vpn)
                return
    else:
        # No last tab or not found: try first tab
        if app.notebook.tabs():
            first_tab_widget = app.notebook.nametowidget(app.notebook.tabs()[0])
            app.notebook.select(app.notebook.tabs()[0])
            app.update_tab_states()
            if hasattr(first_tab_widget, "connect_vpn"):
                app.after(500, first_tab_widget.connect_vpn)
                