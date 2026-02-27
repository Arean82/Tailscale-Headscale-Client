# logic/logger.py
# This module manages all logging functionality for the MAPView VPN Client, including global loggers and dynamic profile loggers.  It uses Python's built-in logging library to create loggers that write to files in a dedicated GlobalLogs directory. The loggers are configured to only write to files if the user has enabled logging in the settings, ensuring that logs are generated according to user preferences.  The module also provides a function to refresh all loggers when the user toggles the logging setting, allowing for dynamic enabling/disabling of logs without needing to restart the application.  

import os
import json
import logging
from logging.handlers import RotatingFileHandler
from config import APP_BASE_DIR

GLOBAL_LOG_DIR = os.path.join(APP_BASE_DIR, "GlobalLogs")
SETTINGS_FILE = os.path.join(APP_BASE_DIR, "settings.json")

def get_global_log_dir():
    os.makedirs(GLOBAL_LOG_DIR, exist_ok=True)
    return GLOBAL_LOG_DIR

def _is_logging_enabled():
    """Reads settings.json directly to check if global logs are enabled."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                return settings.get("enable_logs", False)
        except Exception:
            pass
    return False

def setup_logger(logger_name, log_filename):
    """Creates a specific logger that writes to a file only if enabled."""
    logger = logging.getLogger(logger_name)
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(logging.DEBUG)

    if _is_logging_enabled():
        log_dir = get_global_log_dir()
        log_file = os.path.join(log_dir, log_filename)
        
        handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        logger.addHandler(logging.NullHandler())

    return logger

# --- Pre-configure Static Loggers ---
app_logger = setup_logger("AppLogger", "app.log")
db_logger  = setup_logger("DBLogger", "database.log")
net_logger = setup_logger("NetLogger", "network.log")

# --- Dynamic Profile Loggers ---
def get_profile_logger(profile_name):
    """
    Dynamically creates or retrieves a logger for a specific profile.
    Generates a file like 'Profile1_connection.log' in the GlobalLogs directory.
    """
    safe_profile_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
    safe_profile_name = safe_profile_name.replace(' ', '_')
    
    logger_name = f"ProfileLogger_{safe_profile_name}"
    log_filename = f"{safe_profile_name}_connection.log"
    
    return setup_logger(logger_name, log_filename)

def refresh_all_loggers():
    """Called by settings.py when the user toggles the checkbox."""
    global app_logger, db_logger, net_logger
    
    # Refresh static loggers
    app_logger = setup_logger("AppLogger", "app.log")
    db_logger  = setup_logger("DBLogger", "database.log")
    net_logger = setup_logger("NetLogger", "network.log")
    
    # Note: Profile loggers will naturally refresh the next time get_profile_logger is called