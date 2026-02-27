# logic/logger.py
# This module manages all logging functionality for the TAILSCALE VPN Client, including global loggers and dynamic profile loggers.  It uses Python's built-in logging library to create loggers that write to files in a dedicated GlobalLogs directory. The loggers are configured to only write to files if the user has enabled logging in the settings, ensuring that logs are generated according to user preferences.  The module also provides a function to refresh all loggers when the user toggles the logging setting, allowing for dynamic enabling/disabling of logs without needing to restart the application.  

import os
import sys
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

# --- Print Redirection Logic ---
class StreamToLogger:
    """Redirects print() (stdout/stderr) to the logging module."""
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            if line.strip():  # Avoid logging empty blank lines
                self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

def manage_sys_streams(enabled):
    """Overrides or restores standard print outputs."""
    if enabled:
        sys.stdout = StreamToLogger(app_logger, logging.DEBUG)
        sys.stderr = StreamToLogger(app_logger, logging.ERROR)
    else:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

# --- Logger Setup ---
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

# Pre-configure our specific loggers
app_logger = setup_logger("AppLogger", "app.log")
db_logger  = setup_logger("DBLogger", "database.log")
net_logger = setup_logger("NetLogger", "network.log")

# Setup stream capture initially based on current settings
manage_sys_streams(_is_logging_enabled())

def get_profile_logger(profile_name):
    """Dynamically creates or retrieves a logger for a specific profile."""
    safe_profile_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
    safe_profile_name = safe_profile_name.replace(' ', '_')
    logger_name = f"ProfileLogger_{safe_profile_name}"
    log_filename = f"{safe_profile_name}_connection.log"
    return setup_logger(logger_name, log_filename)

def clear_global_logs():
    """Safely closes logger file handles and deletes the log files."""
    # 1. Find all active loggers and close their file handlers (releases Windows file locks)
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    loggers.extend([app_logger, db_logger, net_logger]) # Ensure our mains are included
    
    for logger in loggers:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
            
    # 2. Delete files in the directory
    if os.path.exists(GLOBAL_LOG_DIR):
        for filename in os.listdir(GLOBAL_LOG_DIR):
            file_path = os.path.join(GLOBAL_LOG_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                # If it fails to delete, print to standard console (since file logs are closing)
                print(f"Failed to delete {file_path}: {e}")

def refresh_all_loggers():
    """Called by settings.py when the user toggles the checkbox."""
    global app_logger, db_logger, net_logger
    enabled = _is_logging_enabled()
    
    app_logger = setup_logger("AppLogger", "app.log")
    db_logger  = setup_logger("DBLogger", "database.log")
    net_logger = setup_logger("NetLogger", "network.log")
    
    manage_sys_streams(enabled)