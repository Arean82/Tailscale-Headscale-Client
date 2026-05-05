# logic/constants.py
# Centralized constants to avoid circular imports

import os
import sys
from pathlib import Path

# Application paths
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
SETTINGS_FILE = os.path.join(APP_BASE_DIR, "settings.json")
LOCK_FILE = os.path.join(APP_BASE_DIR, "app.lock")

# Application limits
MAX_TABS = 5

# Default settings
DEFAULT_SETTINGS = {
    "auto_connect": False,
    "enable_logs": False,
    "theme": "light"
}

# Security constants - will be generated on first run
KEYRING_SERVICE_NAME = "tailscale_vpn_client"
KEYRING_KEY_NAME = "encryption_key"