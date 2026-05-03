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
from logic.logger import app_logger, get_profile_logger


# Import OS-specific mutex functions
from os_specific.mutex_handler import acquire_mutex, release_mutex, set_lock_file_path

# Assuming net_stats.py is available and handles its own platform specifics
from logic.net_stats import log_tailscale_stats
from gui.utils import write_log

from config import APP_BASE_DIR, APP_DATA_DIR, LOG_DIR
from concurrent.futures import ThreadPoolExecutor

# --- Global Configuration and Utilities ---
# --- Encryption Setup ---
MASTER_KEY_FILE = os.path.join(APP_BASE_DIR, "master.key")

def get_encryption_key():
    """Retrieves the encryption key from a file or generates a new one."""
    if os.path.exists(MASTER_KEY_FILE):
        try:
            with open(MASTER_KEY_FILE, "rb") as f:
                return f.read()
        except Exception as e:
            app_logger.error(f"Failed to read master key: {e}")
    
    # Fallback/Initialization: Generate a new key
    # For backward compatibility, you might want to use the old key if it exists
    # but for a 'fix', we should move to a secure random key.
    new_key = Fernet.generate_key()
    try:
        os.makedirs(APP_BASE_DIR, exist_ok=True)
        with open(MASTER_KEY_FILE, "wb") as f:
            f.write(new_key)
        return new_key
    except Exception as e:
        app_logger.error(f"Failed to save master key: {e}")
        # Last resort: use a derived key (less secure but works)
        return base64.urlsafe_b64encode(hashlib.sha256(b"fallback-salt").digest())

# Initialize Fernet with the master key
ENCRYPTION_KEY = get_encryption_key()
fernet = Fernet(ENCRYPTION_KEY)
OLD_PASSWORD = "some-hardcoded-passphrase"
OLD_KEY = base64.urlsafe_b64encode(hashlib.sha256(OLD_PASSWORD.encode()).digest())
old_fernet = Fernet(OLD_KEY)

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

# --- High-Performance Caching Layer ---
class DataCache:
    _settings = None
    _tab_names = None
    _profile_data = {} # {profile_name: {url: ..., key: ..., mode: ...}}

    @classmethod
    def get_settings(cls):
        if cls._settings is None:
            cls._settings = load_settings(use_cache=False)
        return cls._settings

    @classmethod
    def set_settings(cls, settings):
        cls._settings = settings

    @classmethod
    def get_tab_names(cls):
        if cls._tab_names is None:
            cls._tab_names = load_tab_names(use_cache=False)
        return cls._tab_names

    @classmethod
    def set_tab_names(cls, tab_names):
        cls._tab_names = tab_names

    @classmethod
    def get_profile_info(cls, tab_name):
        if tab_name not in cls._profile_data:
            cls._profile_data[tab_name] = {
                "url": load_saved_url(tab_name, use_cache=False),
                "key": load_saved_key(tab_name, use_cache=False),
                "mode": get_auth_mode(tab_name, use_cache=False)
            }
        return cls._profile_data[tab_name]

    @classmethod
    def invalidate_profile(cls, tab_name):
        if tab_name in cls._profile_data:
            del cls._profile_data[tab_name]

    @classmethod
    def preload_all_profiles(cls):
        """Loads all profile data in parallel for super-fast startup."""
        tab_names = cls.get_tab_names()
        with ThreadPoolExecutor() as executor:
            executor.map(cls.get_profile_info, tab_names.values())

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
    """Sends a log entry to the profile-specific logger."""
    try:
        prof_logger = get_profile_logger(tab_name)
        level_upper = level.upper()
        if level_upper == "INFO":
            prof_logger.info(entry)
        elif level_upper == "ERROR":
            prof_logger.error(entry)
        elif level_upper in ["WARNING", "WARN"]:
            prof_logger.warning(entry)
        else:
            prof_logger.debug(entry)
    except Exception as e:
        app_logger.error(f"Failed to write to profile logger for {tab_name}: {e}")

def encrypt_key(plain_text_key):
    """Encrypts the given plain text key."""
    return fernet.encrypt(plain_text_key.encode()).decode()

def decrypt_key(encrypted_key):
    """Decrypts the given encrypted key with fallback support."""
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except Exception:
        # Try fallback with old hardcoded key
        try:
            decrypted = old_fernet.decrypt(encrypted_key.encode()).decode()
            # If successful, re-encrypt with the new key for future use
            return decrypted
        except Exception:
            return ""

def load_saved_url(tab_name, use_cache=True):
    """Loads a URL specific to a tab's name, utilizing cache for speed."""
    if use_cache and tab_name in DataCache._profile_data:
        return DataCache._profile_data[tab_name].get("url", "")
    
    try:
        url_file = get_file_path("Tailscale_VPN_url", tab_name)
        if os.path.exists(url_file):
            with open(url_file, 'r') as f:
                url = f.read().strip()
                if use_cache:
                    if tab_name not in DataCache._profile_data: DataCache._profile_data[tab_name] = {}
                    DataCache._profile_data[tab_name]["url"] = url
                return url
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

def load_saved_key(tab_name, use_cache=True):
    """Loads an encrypted key specific to a tab's name, utilizing cache."""
    if use_cache and tab_name in DataCache._profile_data:
        return DataCache._profile_data[tab_name].get("key", "")

    try:
        key_file = get_file_path("Tailscale_VPN_key", tab_name)
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                encrypted = f.read().strip()
                key = decrypt_key(encrypted)
                if use_cache:
                    if tab_name not in DataCache._profile_data: DataCache._profile_data[tab_name] = {}
                    DataCache._profile_data[tab_name]["key"] = key
                return key
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

def load_tab_names(use_cache=True):
    """Loads the dictionary mapping tab IDs to tab names, utilizing cache."""
    if use_cache and DataCache._tab_names is not None:
        return DataCache._tab_names

    try:
        if os.path.exists(TAB_NAMES_FILE):
            with open(TAB_NAMES_FILE, 'r') as f:
                names = {int(k): v for k, v in json.load(f).items()}
                if use_cache:
                    DataCache._tab_names = names
                return names
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

def get_auth_mode(tab_name, use_cache=True):     # FIXED: Removed the internal import that caused the crash
    if use_cache and tab_name in DataCache._profile_data:
        return DataCache._profile_data[tab_name].get("mode", "auth_key")

    mode_file = get_file_path("auth_mode", tab_name)
    if os.path.exists(mode_file):
        try:
            with open(mode_file, "r") as f:
                mode = f.read().strip()
                if use_cache:
                    if tab_name not in DataCache._profile_data: DataCache._profile_data[tab_name] = {}
                    DataCache._profile_data[tab_name]["mode"] = mode
                return mode
        except:
            return "auth_key"
    return "auth_key"

def is_sso_mode(tab_name):
    return get_auth_mode(tab_name).lower() == "google"



# Log rotation is now handled automatically by RotatingFileHandler in logger.py

# Load and save settings
def load_settings(use_cache=True):
    """Load settings from JSON file or return defaults, utilizing cache."""
    if use_cache and DataCache._settings is not None:
        return DataCache._settings

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                if use_cache:
                    DataCache._settings = settings
                return settings
        except Exception as e:
            write_log(f"Failed to load settings: {e}", level="ERROR")
    # Default settings
    return {
        "auto_connect": False,
        "max_tabs": 5
    }

def save_settings(settings):
    """Save settings dictionary to JSON file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        write_log(f"Failed to save settings: {e}", level="ERROR")

# Auto-connect logic has been moved to gui/gui_main.py to improve decoupling.
                