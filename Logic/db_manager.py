# db_manager.py
# This module manages the database for storing traffic statistics.

import sqlite3
from datetime import datetime
import os
import logging
import sys # Import sys for platform detection

# Import APP_BASE_DIR from vpn_logic for consistent pathing
from config import APP_BASE_DIR
from utils import write_log

# Use the dynamically determined APP_BASE_DIR
APP_DIR = APP_BASE_DIR
DB_FILE = os.path.join(APP_DIR, "traffic_stats.db")

# Set up logging for db_manager
# Ensure the log directory exists before setting up logging
LOG_DIR = os.path.join(APP_DIR, "log") # Use APP_DIR for consistency
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "db_log.txt") # Changed to db_log.txt to separate from app_log.txt
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_connection():
    """Create and return a database connection."""
    try:
        return sqlite3.connect(DB_FILE)
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None

def create_table():
    """Create the traffic_data table if it doesn't exist."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traffic_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile TEXT NOT NULL,
                    date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    bytes_sent INTEGER,
                    bytes_recv INTEGER
                );
            """)
            conn.commit()
            logging.info("Table 'traffic_data' ensured.")
        except sqlite3.Error as e:
            logging.error(f"Error creating table: {e}")
        finally:
            conn.close()

def insert_traffic_data(profile, bytes_sent, bytes_recv):
    """Insert current cumulative traffic stats for a profile."""
    conn = create_connection()
    if conn:
        try:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO traffic_data (profile, date, timestamp, bytes_sent, bytes_recv)
                VALUES (?, ?, ?, ?, ?);
            """, (profile, date_str, timestamp_str, bytes_sent, bytes_recv))
            conn.commit()
            logging.info(f"Logged data for '{profile}': Sent={bytes_sent}, Received={bytes_recv} at {timestamp_str}")
        except sqlite3.Error as e:
            logging.error(f"Error inserting traffic data: {e}")
        finally:
            conn.close()

def get_daily_total_traffic(profile, date=None):
    """
    Return total bytes sent and received today for a given profile.
    Assumes bytes_sent/recv are cumulative from the interface.
    """
    conn = create_connection()
    if not conn:
        return 0, 0

    try:
        if date is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        else:
            date_str = date.strftime("%Y-%m-%d")

        cursor = conn.cursor()
        cursor.execute("""
            SELECT bytes_sent, bytes_recv FROM traffic_data
            WHERE date = ? AND profile = ?
            ORDER BY timestamp ASC;
        """, (date_str, profile))
        records = cursor.fetchall()

        if records:
            first_sent, first_recv = records[0]
            last_sent, last_recv = records[-1]

            total_sent = max(0, last_sent - first_sent)
            total_recv = max(0, last_recv - first_recv)

            return total_sent, total_recv
        else:
            logging.info(f"No traffic data found for {profile} on {date_str}")
            return 0, 0
    except sqlite3.Error as e:
        logging.error(f"Error retrieving daily total: {e}")
        return 0, 0
    finally:
        conn.close()

# Ensure DB and table exist on import
create_table()
