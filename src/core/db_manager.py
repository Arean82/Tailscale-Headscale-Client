# src/core/db_manager.py
# This is the database manager for the application.

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any

from .models import AppSettings, Profile

CURRENT_DB_VERSION = 2

#: Traffic rows older than this are discarded at startup (dashboard shows 10 days).
TRAFFIC_RETENTION_DAYS = 90


class DatabaseManager:
    def __init__(self, base_dir):
        self.db_path = os.path.join(base_dir, "traffic_stats.db")
        self.log_dir = os.path.join(base_dir, "log")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.traffic_buffer = {}  # profile -> {'sent': 0, 'recv': 0}
        self._buffer_lock = threading.Lock()
        
        self._setup_logging()
        self._create_table()
        self._run_migrations()
        # Retention runs once per launch: bounded work, and the dashboard only
        # ever reads the most recent days.
        self.prune_old_traffic()

    def _setup_logging(self):
        log_file = os.path.join(self.log_dir, "db_log.txt")
        self.logger = logging.getLogger("DatabaseManager")
        self.logger.setLevel(logging.INFO)

        # Rebind the handler to *this* instance's directory. Keeping a stale
        # handler would leave its file locked (Windows) and send a second
        # instance's records into the previous directory's log.
        for existing in list(self.logger.handlers):
            self.logger.removeHandler(existing)
            try:
                existing.close()
            except Exception as e:  # noqa: BLE001 - a handler that cannot close must not break startup
                self.logger.debug(f"Could not close previous database log handler: {e}")

        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self._log_handler = handler

    def close(self):
        """Releases the database log file handle.

        Windows refuses to delete a file with an open handle, so this matters
        when the data directory is removed (uninstall, portable use, tests).
        """
        handler = getattr(self, "_log_handler", None)
        if handler is not None:
            self.logger.removeHandler(handler)
            handler.close()
            self._log_handler = None

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
                # Table for profiles (Option C: Hybrid Vault topology store)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS profiles (
                        id TEXT PRIMARY KEY,
                        tab_order INTEGER DEFAULT 0,
                        name TEXT NOT NULL,
                        login_server TEXT,
                        auth_mode TEXT,
                        auto_connect BOOLEAN,
                        exit_node TEXT,
                        routes TEXT,
                        native_profile TEXT,
                        is_native_switch BOOLEAN,
                        enable_ssh BOOLEAN,
                        accept_dns BOOLEAN,
                        allow_lan BOOLEAN,
                        disable_snat BOOLEAN,
                        hostname TEXT,
                        last_known_ip TEXT,
                        enable_dns_fallback BOOLEAN,
                        force_reset BOOLEAN,
                        advertise_exit_node BOOLEAN,
                        shields_up BOOLEAN,
                        force_reauth BOOLEAN,
                        advertise_tags TEXT,
                        accept_routes BOOLEAN,
                        unattended BOOLEAN,
                        webclient BOOLEAN,
                        advertise_connector BOOLEAN,
                        accept_risk TEXT,
                        extra_args TEXT
                    );
                """)
                # Table for application settings
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                """)
                conn.commit()
                self.logger.info("Tables ensured.")
            except sqlite3.Error as e:
                self.logger.error(f"Error creating table: {e}")
            finally:
                conn.close()

    def _run_migrations(self):
        """Runs incremental PRAGMA user_version schema migrations to protect existing databases."""
        conn = self._create_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version;")
            row = cursor.fetchone()
            current_version = row[0] if row else 0

            if current_version < 1:
                # Migration 1: Ensure all 13 profile columns exist on existing pre-1.2 schemas
                cursor.execute("PRAGMA table_info(profiles);")
                existing_cols = {col[1] for col in cursor.fetchall()}

                expected_columns = {
                    "tab_order": "INTEGER DEFAULT 0",
                    "login_server": "TEXT",
                    "auth_mode": "TEXT",
                    "auto_connect": "BOOLEAN DEFAULT 0",
                    "exit_node": "TEXT",
                    "routes": "TEXT",
                    "native_profile": "TEXT",
                    "is_native_switch": "BOOLEAN DEFAULT 0",
                    "enable_ssh": "BOOLEAN DEFAULT 0",
                    "accept_dns": "BOOLEAN DEFAULT 0",
                    "allow_lan": "BOOLEAN DEFAULT 0",
                    "disable_snat": "BOOLEAN DEFAULT 0",
                    "hostname": "TEXT",
                    "last_known_ip": "TEXT",
                    "enable_dns_fallback": "BOOLEAN DEFAULT 0",
                    "force_reset": "BOOLEAN DEFAULT 0",
                    "advertise_exit_node": "BOOLEAN DEFAULT 0",
                    "shields_up": "BOOLEAN DEFAULT 0",
                    "force_reauth": "BOOLEAN DEFAULT 0",
                    "advertise_tags": "TEXT",
                    "accept_routes": "BOOLEAN DEFAULT 1",
                    "unattended": "BOOLEAN DEFAULT 0",
                    "webclient": "BOOLEAN DEFAULT 0",
                    "advertise_connector": "BOOLEAN DEFAULT 0",
                    "accept_risk": "TEXT",
                    "extra_args": "TEXT"
                }

                for col_name, col_type in expected_columns.items():
                    if col_name not in existing_cols:
                        try:
                            cursor.execute(f"ALTER TABLE profiles ADD COLUMN {col_name} {col_type};")
                        except sqlite3.OperationalError as alter_err:
                            self.logger.debug(f"Migration column {col_name} alter: {alter_err}")

                cursor.execute("PRAGMA user_version = 1;")
                conn.commit()
                self.logger.info("Database schema migration to user_version 1 completed.")

            if current_version < 2:
                # Migration 2: index the columns the dashboard filters on. Without
                # it every daily aggregation scans the whole traffic table.
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_traffic_profile_date ON traffic_data(profile, date);"
                )
                cursor.execute("PRAGMA user_version = 2;")
                conn.commit()
                self.logger.info("Database schema migration to user_version 2 completed.")
        except sqlite3.Error as e:
            self.logger.error(f"Migration failed: {e}")
        finally:
            conn.close()

    def prune_old_traffic(self, retention_days: int = TRAFFIC_RETENTION_DAYS) -> int:
        """Deletes traffic rows older than the retention window.

        traffic_data grows by one row per profile per flush forever, so without
        pruning the database would expand indefinitely. Returns the row count
        removed; compacts the file when anything was deleted.
        """
        conn = self._create_connection()
        if not conn:
            return 0
        removed = 0
        try:
            cutoff = (datetime.now().astimezone() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM traffic_data WHERE date < ?;", (cutoff,))
            removed = cursor.rowcount or 0
            conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error pruning old traffic rows: {e}")
            return 0
        finally:
            conn.close()

        if removed:
            self.logger.info(f"Pruned {removed} traffic row(s) older than {retention_days} days.")
            self._compact()
        return removed

    def _compact(self):
        """VACUUM after deletions so the file size actually shrinks."""
        conn = self._create_connection()
        if not conn:
            return
        try:
            conn.execute("VACUUM;")
        except sqlite3.Error as e:
            # VACUUM needs free disk space; a failure must not break startup
            self.logger.debug(f"VACUUM skipped: {e}")
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
            
            # 2. Add to buffer instead of DB (thread-safe)
            with self._buffer_lock:
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

    def _restore_buffer(self, items):
        """Merges previously-snapshot deltas back into the buffer after a failed flush."""
        with self._buffer_lock:
            for prof, vals in items.items():
                if prof not in self.traffic_buffer:
                    self.traffic_buffer[prof] = dict(vals)
                else:
                    self.traffic_buffer[prof]['sent'] += vals['sent']
                    self.traffic_buffer[prof]['recv'] += vals['recv']

    def flush_buffer(self):
        """Writes all buffered traffic deltas to the database in one batch (thread-safe).

        On any failure (no connection or DB write error) the snapshot is merged
        back into the buffer so measured traffic is never silently discarded.
        """
        with self._buffer_lock:
            if not self.traffic_buffer:
                return
            items_to_flush = dict(self.traffic_buffer)
            self.traffic_buffer.clear()
            
        conn = self._create_connection()
        if not conn:
            self._restore_buffer(items_to_flush)
            return
        
        try:
            cursor = conn.cursor()
            now = datetime.now().astimezone()  # timezone-aware; wall-clock date kept for daily grouping
            date_str = now.strftime("%Y-%m-%d")
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
            
            flushed_count = 0
            for profile, data in items_to_flush.items():
                if data['sent'] == 0 and data['recv'] == 0:
                    continue
                    
                cursor.execute("""
                    INSERT INTO traffic_data (profile, date, timestamp, sent_delta, recv_delta)
                    VALUES (?, ?, ?, ?, ?);
                """, (profile, date_str, timestamp_str, data['sent'], data['recv']))
                flushed_count += 1
            
            conn.commit()
            self.logger.info(f"Flushed traffic buffer for {flushed_count} profiles.")
        except sqlite3.Error as e:
            self.logger.error(f"Error flushing traffic buffer: {e}")
            self._restore_buffer(items_to_flush)
        finally:
            conn.close()

    def get_daily_total(self, profile, date=None):
        conn = self._create_connection()
        if not conn: return 0, 0
        try:
            date_str = (date or datetime.now().astimezone()).strftime("%Y-%m-%d")
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

    # ==========================================
    # Option C: Hybrid Vault Storage Engine
    # ==========================================

    def save_profile(self, profile: Profile, tab_order: int = 0) -> bool:
        """Persists profile topology and configuration to SQLite (excluding auth_key)."""
        conn = self._create_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO profiles (
                    id, tab_order, name, login_server, auth_mode,
                    auto_connect, exit_node, routes, native_profile,
                    is_native_switch, enable_ssh, accept_dns, allow_lan,
                    disable_snat, hostname, last_known_ip, enable_dns_fallback,
                    force_reset, advertise_exit_node, shields_up, force_reauth,
                    advertise_tags, accept_routes, unattended, webclient,
                    advertise_connector, accept_risk, extra_args
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?
                );
            """, (
                profile.id,
                tab_order,
                profile.name,
                profile.login_server,
                profile.auth_mode,
                1 if profile.auto_connect else 0,
                profile.exit_node,
                profile.routes,
                profile.native_profile,
                1 if profile.is_native_switch else 0,
                1 if profile.enable_ssh else 0,
                1 if profile.accept_dns else 0,
                1 if profile.allow_lan else 0,
                1 if profile.disable_snat else 0,
                profile.hostname,
                profile.last_known_ip,
                1 if profile.enable_dns_fallback else 0,
                1 if profile.force_reset else 0,
                1 if profile.advertise_exit_node else 0,
                1 if profile.shields_up else 0,
                1 if profile.force_reauth else 0,
                profile.advertise_tags,
                1 if getattr(profile, 'accept_routes', True) else 0,
                1 if getattr(profile, 'unattended', False) else 0,
                1 if getattr(profile, 'webclient', False) else 0,
                1 if getattr(profile, 'advertise_connector', False) else 0,
                getattr(profile, 'accept_risk', ""),
                getattr(profile, 'extra_args', "")
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving profile '{profile.name}' ({profile.id}): {e}")
            return False
        finally:
            conn.close()

    def load_all_profiles(self) -> list[Profile]:
        """Loads all profiles ordered by tab_order without auth_key (auth_key retrieved via Keyring)."""
        conn = self._create_connection()
        if not conn:
            return []
        profiles = []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id, name, login_server, auth_mode, auto_connect,
                    exit_node, routes, native_profile, is_native_switch,
                    enable_ssh, accept_dns, allow_lan, disable_snat,
                    hostname, last_known_ip, enable_dns_fallback, force_reset,
                    advertise_exit_node, shields_up, force_reauth, advertise_tags,
                    accept_routes, unattended, webclient, advertise_connector,
                    accept_risk, extra_args
                FROM profiles
                ORDER BY tab_order ASC, rowid ASC;
            """)
            rows = cursor.fetchall()
            for row in rows:
                prof = Profile(
                    id=row[0],
                    name=row[1],
                    login_server=row[2] or "https://controlplane.tailscale.com",
                    auth_key="",  # Kept empty in DB; populated from native Keyring
                    auth_mode=row[3] or "auth_key",
                    auto_connect=bool(row[4]),
                    exit_node=row[5] or "",
                    routes=row[6] or "",
                    native_profile=row[7] or "",
                    is_native_switch=bool(row[8]),
                    enable_ssh=bool(row[9]),
                    accept_dns=bool(row[10]),
                    allow_lan=bool(row[11]),
                    disable_snat=bool(row[12]),
                    hostname=row[13] or "",
                    last_known_ip=row[14] or "",
                    enable_dns_fallback=bool(row[15]),
                    force_reset=bool(row[16]),
                    advertise_exit_node=bool(row[17]),
                    shields_up=bool(row[18]),
                    force_reauth=bool(row[19]),
                    advertise_tags=row[20] or "",
                    accept_routes=bool(row[21]),
                    unattended=bool(row[22]),
                    webclient=bool(row[23]),
                    advertise_connector=bool(row[24]),
                    accept_risk=row[25] or "",
                    extra_args=row[26] or ""
                )
                profiles.append(prof)
        except sqlite3.Error as e:
            self.logger.error(f"Error loading profiles: {e}")
        finally:
            conn.close()
        return profiles

    def delete_profile(self, profile_id: str, profile_name: str | None = None) -> bool:
        """Deletes a profile from profiles, and cascades cleanup to raw_state and traffic_data."""
        conn = self._create_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM profiles WHERE id = ?;", (profile_id,))
            if profile_name:
                cursor.execute("DELETE FROM raw_state WHERE profile = ?;", (profile_name,))
                cursor.execute("DELETE FROM traffic_data WHERE profile = ?;", (profile_name,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting profile {profile_id}: {e}")
            return False
        finally:
            conn.close()

    def count_profiles(self) -> int:
        """Returns total count of stored profiles."""
        conn = self._create_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM profiles;")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def save_app_settings(self, settings: AppSettings) -> bool:
        """Persists application settings key-value pairs into app_settings table."""
        conn = self._create_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            settings_dict = settings.__dict__
            for k, v in settings_dict.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO app_settings (key, value)
                    VALUES (?, ?);
                """, (k, json.dumps(v)))
            conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving app settings: {e}")
            return False
        finally:
            conn.close()

    def load_app_settings(self) -> AppSettings:
        """Loads application settings from app_settings table."""
        conn = self._create_connection()
        if not conn:
            return AppSettings()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM app_settings;")
            rows = cursor.fetchall()
            if not rows:
                return AppSettings()
            
            from dataclasses import fields
            valid_fields = {f.name for f in fields(AppSettings)}
            data: dict[str, Any] = {}
            for key, val_str in rows:
                if key in valid_fields:
                    try:
                        data[key] = json.loads(val_str)
                    except (ValueError, TypeError):
                        data[key] = val_str
            return AppSettings(**data)
        except sqlite3.Error as e:
            self.logger.error(f"Error loading app settings: {e}")
            return AppSettings()
        finally:
            conn.close()

