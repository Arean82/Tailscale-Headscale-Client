# logic/logger.py

import os
import logging
from logging.handlers import RotatingFileHandler
from config import APP_BASE_DIR
from logic.vpn_logic import load_settings

# Define the global log directory
GLOBAL_LOG_DIR = os.path.join(APP_BASE_DIR, "GlobalLogs")

def get_global_log_dir():
    """Returns the path to the global log directory, creating it if it doesn't exist."""
    os.makedirs(GLOBAL_LOG_DIR, exist_ok=True)
    return GLOBAL_LOG_DIR

def setup_global_logger():
    """Configures and returns the global app logger based on user settings."""
    logger = logging.getLogger("MAPView_Global_Logger")
    
    # Prevent adding multiple handlers if the logger is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Always set level to DEBUG or INFO so it catches messages
    logger.setLevel(logging.DEBUG) 

    # Check if logs are enabled in settings
    settings = load_settings()
    if settings.get("enable_logs", False):
        log_dir = get_global_log_dir()
        log_file = os.path.join(log_dir, "app_debug.log")
        
        # Use a rotating file handler to keep log files from getting too huge (max 5MB, keep 3 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    else:
        # If disabled, attach a NullHandler so logging calls don't crash, but do nothing
        logger.addHandler(logging.NullHandler())

    return logger

# Create a convenient instance to import across the app
app_logger = setup_global_logger()