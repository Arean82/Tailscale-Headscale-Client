# src/core/db_manager.py
# This is the database manager for the application.

import sqlite3
import os
import logging
from datetime import datetime

class DatabaseManager:
    def __init__(self, base_dir):
        self.db_path = os.path.join(base_dir, "traffic_stats.db")
        self.log_dir = os.path.join(base_dir, "log")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.traffic_buffer = {} # profile -> {'sent': 0, 'recv': 0}
        
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
                # Table for aggregated deltas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS traffic_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile TEXT NOT NULL,
                        date TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        sent_delta INTEGER,
                        recv_delta INTEGER
                    );
                """)
                # Table to keep track of raw counters across restarts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS raw_state (
                        profile TEXT PRIMARY KEY,
                        last_sent INTEGER,
                        last_recv INTEGER
                    );
                """)
                conn.commit()
                self.logger.info("Tables ensured.")
            except sqlite3.Error as e:
                self.logger.error(f"Error creating table: {e}")
            finally:
                conn.close()

    def insert_traffic_data(self, profile, raw_sent, raw_recv):
        """Calculates delta and adds it to the in-memory buffer."""
        conn = self._create_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            
            # 1. Get last raw state
            cursor.execute("SELECT last_sent, last_recv FROM raw_state WHERE profile = ?", (profile,))
            row = cursor.fetchone()
            
            sent_delta = 0
            recv_delta = 0
            
            if row:
                last_s, last_r = row
                sent_delta = raw_sent - last_s if raw_sent >= last_s else raw_sent
                recv_delta = raw_recv - last_r if raw_recv >= last_r else raw_recv
            
            # 2. Add to buffer instead of DB
            if profile not in self.traffic_buffer:
                self.traffic_buffer[profile] = {'sent': 0, 'recv': 0}
            
            self.traffic_buffer[profile]['sent'] += sent_delta
            self.traffic_buffer[profile]['recv'] += recv_delta
            
            # 3. Update raw state (we still do this to keep baseline accurate)
            cursor.execute("""
                INSERT OR REPLACE INTO raw_state (profile, last_sent, last_recv)
                VALUES (?, ?, ?);
            """, (profile, raw_sent, raw_recv))
            
            conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error updating raw state: {e}")
        finally:
            conn.close()

    def flush_buffer(self):
        """Writes all buffered traffic deltas to the database in one batch."""
        if not self.traffic_buffer:
            return
            
        conn = self._create_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            for profile, data in self.traffic_buffer.items():
                if data['sent'] == 0 and data['recv'] == 0:
                    continue
                    
                cursor.execute("""
                    INSERT INTO traffic_data (profile, date, timestamp, sent_delta, recv_delta)
                    VALUES (?, ?, ?, ?, ?);
                """, (profile, date_str, timestamp_str, data['sent'], data['recv']))
            
            conn.commit()
            self.logger.info(f"Flushed traffic buffer for {len(self.traffic_buffer)} profiles.")
            self.traffic_buffer.clear() # Reset buffer after successful flush
        except sqlite3.Error as e:
            self.logger.error(f"Error flushing traffic buffer: {e}")
        finally:
            conn.close()

    def get_daily_total(self, profile, date=None):
        conn = self._create_connection()
        if not conn: return 0, 0
        try:
            date_str = (date or datetime.now()).strftime("%Y-%m-%d")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(sent_delta), SUM(recv_delta) FROM traffic_data
                WHERE date = ? AND profile = ?;
            """, (date_str, profile))
            row = cursor.fetchone()
            if row:
                sent, recv = row
                return (sent or 0), (recv or 0)
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving daily total: {e}")
        finally:
            conn.close()
        return 0, 0

    def get_traffic_history(self, profile, limit=10):
        """Returns the raw last X entries (legacy)."""
        conn = self._create_connection()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, sent_delta, recv_delta FROM traffic_data
                WHERE profile = ? ORDER BY id DESC LIMIT ?
            """, (profile, limit))
            return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving history: {e}")
        finally:
            conn.close()
        return []

    def get_daily_history(self, profile, days=10):
        """Aggregates traffic data into daily totals for the past X days."""
        conn = self._create_connection()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, SUM(sent_delta), SUM(recv_delta)
                FROM traffic_data
                WHERE profile = ?
                GROUP BY date
                ORDER BY date DESC
                LIMIT ?
            """, (profile, days))
            
            return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving daily history: {e}")
        finally:
            conn.close()
        return []
