import logging
import os
import sys
import json
from logging.handlers import RotatingFileHandler

# This will be set during initialization in main.py
APP_DIR = None

class ScrubbingFormatter(logging.Formatter):
    def format(self, record):
        orig_msg = record.msg
        if isinstance(record.msg, str):
            record.msg = scrub_credentials(record.msg)
        try:
            val = super().format(record)
        finally:
            record.msg = orig_msg
        return val

def setup_logger(name, log_file, level=logging.DEBUG):
    """Setup a standard logger with rotating file and console output."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    formatter = ScrubbingFormatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
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

import re

def scrub_credentials(text):
    if not text or not isinstance(text, str):
        return text
    # Mask Tailscale auth keys (e.g. tskey-auth-...)
    text = re.sub(r'tskey-auth-\S+', 'tskey-auth-[REDACTED]', text)
    # Mask any potential API keys/passwords in connection arguments
    text = re.sub(r'--authkey=\S+', '--authkey=[REDACTED]', text)
    text = re.sub(r'--auth-key=\S+', '--auth-key=[REDACTED]', text)
    return text

class StreamToLogger:
    """Redirects stdout/stderr to the logging module with integrated credential scrubbing."""
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        scrubbed = scrub_credentials(buf)
        for line in scrubbed.rstrip().splitlines():
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

def write_profile_log(profile_name, data):
    """Safely append connection standard output to a profile-specific log file."""
    try:
        safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '.', '_', '-')).strip().replace(' ', '_')
        if sys.platform == "win32":
            app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
        
        log_dir = os.path.join(app_dir, "GlobalLogs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{safe_name}_connection.log")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(data + "\n")
    except Exception:
        pass

# Global instance for easy access
app_logger = None
