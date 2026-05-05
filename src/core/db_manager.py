# src/core/db_manager.py
import sqlite3
import os
import logging
from datetime import datetime

class DatabaseManager:
    def __init__(self, base_dir):
        self.db_path = os.path.join(base_dir, "traffic_stats.db")
        self.log_dir = os.path.join(base_dir, "log")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self._setup_logging()
        self._create_table()

    def _setup_logging(self):
        log_file = os.path.join(self.log_dir, "db_log.txt")
        self.logger = logging.getLogger("DatabaseManager")
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _create_connection(self):
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            return None

    def _create_table(self):
        conn = self._create_connection()
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
                self.logger.info("Table 'traffic_data' ensured.")
            except sqlite3.Error as e:
                self.logger.error(f"Error creating table: {e}")
            finally:
                conn.close()

    def insert_traffic_data(self, profile, bytes_sent, bytes_recv):
        conn = self._create_connection()
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
                self.logger.info(f"Logged data for '{profile}': Sent={bytes_sent}, Received={bytes_recv}")
            except sqlite3.Error as e:
                self.logger.error(f"Error inserting traffic data: {e}")
            finally:
                conn.close()

    def get_daily_total(self, profile, date=None):
        conn = self._create_connection()
        if not conn: return 0, 0
        try:
            date_str = (date or datetime.now()).strftime("%Y-%m-%d")
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
                return max(0, last_sent - first_sent), max(0, last_recv - first_recv)
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving daily total: {e}")
        finally:
            conn.close()
        return 0, 0
    def get_traffic_history(self, profile, limit=10):
        conn = self._create_connection()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, bytes_sent, bytes_recv FROM traffic_data
                WHERE profile = ? ORDER BY id DESC LIMIT ?
            """, (profile, limit))
            return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving history: {e}")
        finally:
            conn.close()
        return []
