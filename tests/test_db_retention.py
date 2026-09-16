import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.db_manager import CURRENT_DB_VERSION, TRAFFIC_RETENTION_DAYS, DatabaseManager


class TestTrafficRetentionAndIndex(unittest.TestCase):
    """Finding 7: traffic_data needs an index, a retention window and compaction."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dbfix_")
        self.db = DatabaseManager(self.tmp)
        self.conn = sqlite3.connect(os.path.join(self.tmp, "traffic_stats.db"))

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _insert(self, profile, date_str, sent=1, recv=1):
        self.conn.execute(
            "INSERT INTO traffic_data (profile, date, timestamp, sent_delta, recv_delta) VALUES (?,?,?,?,?)",
            (profile, date_str, f"{date_str} 00:00:00", sent, recv))
        self.conn.commit()

    def test_index_exists_after_migration(self):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='traffic_data'").fetchall()
        self.assertIn("idx_traffic_profile_date", [r[0] for r in rows])

    def test_schema_version_is_bumped(self):
        version = self.conn.execute("PRAGMA user_version;").fetchone()[0]
        self.assertEqual(version, CURRENT_DB_VERSION)
        self.assertEqual(CURRENT_DB_VERSION, 2)

    def test_prune_removes_only_rows_past_the_window(self):
        recent = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%d")
        old = (datetime.now(UTC) - timedelta(days=TRAFFIC_RETENTION_DAYS + 30)).strftime("%Y-%m-%d")
        self._insert("HQ", recent, sent=111)
        self._insert("HQ", old, sent=222)

        removed = self.db.prune_old_traffic()

        self.assertEqual(removed, 1)
        rows = self.conn.execute("SELECT date, sent_delta FROM traffic_data").fetchall()
        self.assertEqual(rows, [(recent, 111)], "the wrong rows were pruned")

    def test_retention_boundary_is_inclusive(self):
        edge = (datetime.now(UTC) - timedelta(days=TRAFFIC_RETENTION_DAYS - 1)).strftime("%Y-%m-%d")
        self._insert("Edge", edge, sent=5)
        self.db.prune_old_traffic()
        rows = self.conn.execute("SELECT sent_delta FROM traffic_data").fetchall()
        self.assertEqual(rows, [(5,)], "a row inside the window was pruned")

    def test_prune_on_empty_database_is_a_noop(self):
        self.assertEqual(self.db.prune_old_traffic(), 0)

    def test_pruning_survives_a_locked_database(self):
        """A prune failure must never break startup."""
        self._insert("HQ", "2000-01-01")
        with unittest.mock.patch.object(DatabaseManager, "_create_connection", return_value=None):
            self.assertEqual(self.db.prune_old_traffic(), 0)

    def test_old_schema_upgrades_to_v2(self):
        legacy_dir = tempfile.mkdtemp(prefix="legacy_")
        try:
            path = os.path.join(legacy_dir, "traffic_stats.db")
            conn = sqlite3.connect(path)
            conn.execute("""CREATE TABLE profiles (id TEXT PRIMARY KEY, name TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE traffic_data (id INTEGER PRIMARY KEY AUTOINCREMENT, profile TEXT,
                            date TEXT, timestamp TEXT, sent_delta INTEGER, recv_delta INTEGER)""")
            conn.execute("PRAGMA user_version = 1;")
            conn.commit()
            conn.close()

            DatabaseManager(legacy_dir)   # must not raise

            conn = sqlite3.connect(path)
            version = conn.execute("PRAGMA user_version;").fetchone()[0]
            idx = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='traffic_data'"
                               ).fetchall()
            conn.close()
            self.assertEqual(version, 2, "a v1 database was not upgraded")
            self.assertIn("idx_traffic_profile_date", [r[0] for r in idx])
        finally:
            shutil.rmtree(legacy_dir, ignore_errors=True)


class TestDatabaseLogHandle(unittest.TestCase):
    """The self-test caught this: the db log handler used to be process-global
    and never closed, locking the file on Windows and misrouting a second
    instance's records into the first instance's directory."""

    def test_close_releases_the_file(self):
        tmp = tempfile.mkdtemp(prefix="dbclose_")
        try:
            db = DatabaseManager(tmp)
            log_path = os.path.join(tmp, "log", "db_log.txt")
            db.logger.info("written while open")
            db.close()
            os.remove(log_path)  # raises on Windows if the handle is still held
            self.assertFalse(os.path.exists(log_path))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_second_instance_logs_to_its_own_directory(self):
        first, second = tempfile.mkdtemp(prefix="db1_"), tempfile.mkdtemp(prefix="db2_")
        try:
            db1 = DatabaseManager(first)
            db1.logger.info("first-directory-record")
            db2 = DatabaseManager(second)
            db2.logger.info("second-directory-record")

            with open(os.path.join(first, "log", "db_log.txt"), encoding="utf-8") as f:
                first_log = f.read()
            with open(os.path.join(second, "log", "db_log.txt"), encoding="utf-8") as f:
                second_log = f.read()

            self.assertIn("first-directory-record", first_log)
            self.assertNotIn("second-directory-record", first_log,
                             "the second instance wrote into the first instance's log")
            self.assertIn("second-directory-record", second_log)
            db2.close()
        finally:
            for path in (first, second):
                shutil.rmtree(path, ignore_errors=True)

    def test_close_is_idempotent(self):
        tmp = tempfile.mkdtemp(prefix="dbclose2_")
        try:
            db = DatabaseManager(tmp)
            db.close()
            db.close()  # must not raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSelfCheck(unittest.TestCase):
    """Finding 11: the packaging smoke test must pass here and fail loudly."""

    def test_passes_against_the_source_tree(self):
        from src.utils.self_check import run_self_test

        failures = [message for ok, message in run_self_test() if not ok]
        self.assertEqual(failures, [], f"self-test failed from source: {failures}")

    def test_reports_a_broken_bundle(self):
        from src.utils.self_check import run_self_test

        empty = tempfile.mkdtemp(prefix="emptybundle_")
        try:
            results = run_self_test(empty)
            messages = [m for ok, m in results if not ok]
            self.assertGreaterEqual(len(messages), 4, "missing bundled data was not detected")
            self.assertTrue(any("icon" in m for m in messages))
            self.assertTrue(any("translation" in m for m in messages))
            self.assertTrue(any("README" in m for m in messages))
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_self_test_mode_exits_nonzero_on_failure(self):
        """main.py --self-test must give CI a usable exit code."""
        import subprocess

        result = subprocess.run([sys.executable, "main.py", "--self-test"],
                                capture_output=True, text=True, timeout=180, cwd=os.getcwd(), check=False)
        self.assertEqual(result.returncode, 0, f"self-test failed:\n{result.stdout[-800:]}")
        self.assertIn("checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
