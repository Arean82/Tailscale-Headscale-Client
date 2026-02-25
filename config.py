# config.py
# This module defines the base directory and common paths for the Tailscale VPN Client.
# It ensures that the application can run on both Windows and Linux platforms without hardcoding paths.

import os
import sys

# Secure File Path Setup (OS-agnostic base directory)
if sys.platform == "win32":
    APP_BASE_DIR = os.path.join(os.environ.get('APPDATA'), "Tailscale_VPN_Client")
elif sys.platform.startswith("linux"):
    APP_BASE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
else:
    APP_BASE_DIR = os.path.join(os.path.expanduser("~"), "Tailscale_VPN_Client")

# Define common subdirectories relative to APP_BASE_DIR
APP_DATA_DIR = os.path.join(APP_BASE_DIR, "data")
LOG_DIR = os.path.join(APP_BASE_DIR, "log")

# Ensure base directories exist as soon as config is imported
# This is crucial for logging to work correctly from the start
os.makedirs(APP_DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
