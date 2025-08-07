# net_stats.py

import psutil
import os
import logging
from datetime import datetime

# Import shared configuration and logging
from config import APP_BASE_DIR, LOG_DIR
from utils import write_log

# Use APP_BASE_DIR for consistency
DB_FILE = os.path.join(APP_BASE_DIR, "traffic_stats.db") # This should probably be in db_manager, but keeping consistent with original structure for now.

# Set up logging for net_stats
os.makedirs(LOG_DIR, exist_ok=True) # Ensure LOG_DIR from config is created
LOG_FILE = os.path.join(LOG_DIR, "net_stats_log.txt") # Separate log file
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import insert_traffic_data from db_manager here, after db_manager has its imports sorted
from db_manager import insert_traffic_data

def get_tailscale_stats():
    """
    Get psutil stats for the Tailscale interface.
    Returns snetio (or None if not found).
    """
    stats = psutil.net_io_counters(pernic=True)
    for iface, data in stats.items():
        if "tailscale" in iface.lower():
            return data
    write_log("Tailscale interface not found.", level="DEBUG")
    return None

def log_tailscale_stats(profile):
    """
    Fetch and log current Tailscale stats to the DB.
    Call this periodically or after connect.
    """
    stats = get_tailscale_stats()
    if stats:
        insert_traffic_data(profile, stats.bytes_sent, stats.bytes_recv)
    else:
        write_log(f"No Tailscale stats to log for profile '{profile}'.", level="DEBUG")

