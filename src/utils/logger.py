import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler

# This will be set during initialization in main.py
APP_DIR = None

def setup_logger(name, log_file, level=logging.DEBUG):
    """Setup a standard logger with rotating file and console output."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    # Standard handler
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(handler)

    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# --- Advanced Features from legacy logic/logger.py ---

class StreamToLogger:
    """Redirects stdout/stderr to the logging module."""
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            if line.strip():
                self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

def manage_sys_streams(enabled, logger=None):
    """Overrides or restores standard print outputs."""
    if enabled and logger:
        sys.stdout = StreamToLogger(logger, logging.DEBUG)
        sys.stderr = StreamToLogger(logger, logging.ERROR)
    else:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

def get_profile_logger(profile_name, base_dir):
    """Dynamically creates a logger for a specific profile connection."""
    safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '.', '_', '-')).strip().replace(' ', '_')
    log_dir = os.path.join(base_dir, "GlobalLogs")
    log_file = os.path.join(log_dir, f"{safe_name}_connection.log")
    return setup_logger(f"Profile_{safe_name}", log_file)

def get_global_log_dir(base_dir):
    path = os.path.join(base_dir, "GlobalLogs")
    os.makedirs(path, exist_ok=True)
    return path

def refresh_all_loggers(base_dir, enabled):
    """Refreshes the main loggers and system streams."""
    log_file = os.path.join(base_dir, "app.log")
    logger = setup_logger("TailscaleClient", log_file)
    manage_sys_streams(enabled, logger)
    return logger

# Global instance for easy access
app_logger = None
