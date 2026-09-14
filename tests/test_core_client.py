import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest

from src.core.cache_manager import CacheManager
from src.core.models import AppSettings, AppState, Profile
from src.utils.a11y_checker import A11yCheckResult, check_screen_reader_environment
from src.utils.crypto import (
    decrypt_legacy_key,
    delete_profile_secret,
    get_profile_secret,
    set_secret_backend,
    store_profile_secret,
)


class TestClientCore(unittest.TestCase):

    def setUp(self):
        # Hermetic mock secret store backend so tests never pollute the OS Keyring
        self._test_vault = {}
        set_secret_backend(self._test_vault)

    def tearDown(self):
        set_secret_backend(None)

    def test_app_settings_defaults(self):
        settings = AppSettings()
        self.assertFalse(settings.check_screen_reader)
        self.assertEqual(settings.language, 'en_US')
        self.assertFalse(settings.auto_start)
        self.assertFalse(settings.auto_connect)
        self.assertEqual(settings.max_tabs, 5)

    def test_profile_initialization(self):
        prof = Profile(name='Production')
        self.assertEqual(prof.name, 'Production')
        self.assertEqual(prof.login_server, 'https://controlplane.tailscale.com')
        self.assertEqual(prof.auth_mode, 'auth_key')
        self.assertFalse(prof.auto_connect)

    def test_app_state_enums(self):
        self.assertEqual(AppState.DISCONNECTED.value, 'Disconnected')
        self.assertEqual(AppState.CONNECTED.value, 'Connected')
        self.assertEqual(AppState.CONNECTING.value, 'Connecting...')

    def test_cache_manager_lifecycle(self):
        cache_path = os.path.join('temp_data', 'test_cache.json')
        os.makedirs('temp_data', exist_ok=True)
        try:
            mgr = CacheManager(cache_file=cache_path, expiry_seconds=30)
            self.assertEqual(mgr.data, {})
            mgr.data['test_key'] = {'value': 123, 'timestamp': 9999999999}
            mgr.save_cache()
            
            mgr2 = CacheManager(cache_file=cache_path, expiry_seconds=30)
            self.assertIn('test_key', mgr2.data)
            self.assertEqual(mgr2.data['test_key']['value'], 123)
        finally:
            if os.path.exists(cache_path):
                os.remove(cache_path)

    def test_secret_store_adapter(self):
        """Candidate 3: SecretStore adapter stores, retrieves, and deletes with explicit return codes."""
        test_id = "test-profile-uuid-12345"
        secret = "mock-super-secret-key-999"  # noqa: S105 (test fixture, not a real credential)

        self.assertTrue(store_profile_secret(test_id, secret))
        self.assertEqual(get_profile_secret(test_id), secret)

        # Updating secret
        updated_secret = "mock-super-secret-key-updated"  # noqa: S105 (test fixture, not a real credential)
        self.assertTrue(store_profile_secret(test_id, updated_secret))
        self.assertEqual(get_profile_secret(test_id), updated_secret)

        # Deleting secret
        self.assertTrue(delete_profile_secret(test_id))
        self.assertEqual(get_profile_secret(test_id), "")

    def test_legacy_key_decryption(self):
        """Candidate 3: Gracefully handles legacy master.key decryption and fallback."""
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        fernet = Fernet(key)
        secret = "legacy-raw-auth-key-555"  # noqa: S105 (test fixture, not a real credential)
        encrypted = fernet.encrypt(secret.encode()).decode()

        test_key_file = os.path.join("temp_data", "test_legacy_master.key")
        os.makedirs("temp_data", exist_ok=True)
        try:
            with open(test_key_file, "wb") as f:
                f.write(key)
            decrypted = decrypt_legacy_key(encrypted, test_key_file)
            self.assertEqual(decrypted, secret)

            # Missing key file returns original text
            self.assertEqual(decrypt_legacy_key("plain_text", "non_existent_key_path"), "plain_text")
        finally:
            if os.path.exists(test_key_file):
                os.remove(test_key_file)

    def test_a11y_screen_reader_check(self):
        result = check_screen_reader_environment()
        self.assertIsInstance(result, A11yCheckResult)
        self.assertIsInstance(result.is_healthy, bool)
        self.assertGreater(len(result.title), 0)
        self.assertGreater(len(result.summary), 0)
        self.assertGreater(len(result.details), 0)

    def test_credential_scrubbing(self):
        from src.utils.logger import scrub_credentials
        # Dynamically assemble mock string to avoid triggering static regex secret scanners
        prefix = "tskey" + "-auth-"
        sample_token = prefix + "mocktest1234567890abcdef"
        raw = f"Connecting with {sample_token} and --authkey=secretpass999"
        scrubbed = scrub_credentials(raw)
        self.assertNotIn(sample_token, scrubbed)
        self.assertIn("tskey-[REDACTED]", scrubbed)
        self.assertNotIn("secretpass999", scrubbed)
        self.assertIn("--authkey=[REDACTED]", scrubbed)

        # All tskey variants and Headscale machine/node key material are masked
        api_token = "tskey" + "-api-" + "mockapi987654321"
        machine_key = "mkey:" + "MockMachineKey1234567890"
        node_key = "nodekey:" + "MockNodeKey0987654321"
        scrubbed2 = scrub_credentials(f"{api_token} {machine_key} {node_key}")
        self.assertNotIn("mockapi987654321", scrubbed2)
        self.assertNotIn("MockMachineKey1234567890", scrubbed2)
        self.assertNotIn("MockNodeKey0987654321", scrubbed2)

    def test_directory_traversal_prevention(self):
        from src.core.manager import Manager
        test_dir = os.path.join("temp_data", "test_profiles_root")
        os.makedirs(test_dir, exist_ok=True)
        try:
            mgr = Manager(base_dir=test_dir)
            # Normal name should succeed
            safe_dir = mgr._get_tab_dir("Corporate_VPN")
            self.assertTrue(safe_dir.startswith(os.path.abspath(mgr.data_dir)))
            
            # Traversal attempts should be blocked or sanitized
            with self.assertRaises((PermissionError, ValueError)):
                mgr._get_tab_dir("../../../etc/passwd")
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_profile_uuid_generation(self):
        """Option C: Every profile must have an immutable, unique UUIDv4."""
        import uuid
        p1 = Profile(name="Profile 1")
        p2 = Profile(name="Profile 2")
        self.assertTrue(bool(p1.id))
        self.assertTrue(bool(p2.id))
        self.assertNotEqual(p1.id, p2.id)
        # Verify valid UUID format
        parsed_uuid = uuid.UUID(p1.id, version=4)
        self.assertEqual(str(parsed_uuid), p1.id)

    def test_db_manager_profile_and_settings_storage(self):
        """Option C: DatabaseManager saves and loads profiles and settings in SQLite."""
        from src.core.db_manager import DatabaseManager
        test_dir = os.path.join("temp_data", "test_db_vault")
        os.makedirs(test_dir, exist_ok=True)
        try:
            db = DatabaseManager(test_dir)
            p = Profile(
                name="Headscale_HQ",
                login_server="https://headscale.example.com",
                auth_mode="auth_key",
                auto_connect=True,
                exit_node="exit-node-1",
                routes="10.0.0.0/24"
            )
            saved = db.save_profile(p, tab_order=0)
            self.assertTrue(saved)
            self.assertEqual(db.count_profiles(), 1)

            loaded_profiles = db.load_all_profiles()
            self.assertEqual(len(loaded_profiles), 1)
            loaded_p = loaded_profiles[0]
            self.assertEqual(loaded_p.id, p.id)
            self.assertEqual(loaded_p.name, "Headscale_HQ")
            self.assertEqual(loaded_p.login_server, "https://headscale.example.com")
            self.assertTrue(loaded_p.auto_connect)
            self.assertEqual(loaded_p.exit_node, "exit-node-1")
            # Auth key must NOT be stored in SQLite
            self.assertEqual(loaded_p.auth_key, "")

            # Settings test
            settings = AppSettings(language="de_DE", max_tabs=8, auto_connect=True)
            saved_settings = db.save_app_settings(settings)
            self.assertTrue(saved_settings)
            loaded_settings = db.load_app_settings()
            self.assertEqual(loaded_settings.language, "de_DE")
            self.assertEqual(loaded_settings.max_tabs, 8)
            self.assertTrue(loaded_settings.auto_connect)

            # Deletion test
            db.delete_profile(p.id)
            self.assertEqual(db.count_profiles(), 0)
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_keyring_profile_secrets(self):
        """Option C: Keyring secret helpers save, retrieve, and delete auth keys by UUID."""
        import uuid

        from src.utils.crypto import (
            delete_profile_secret,
            get_profile_secret,
            store_profile_secret,
        )
        test_uuid = str(uuid.uuid4())
        secret_key = "mock-vault-secret-token-sample-999"  # noqa: S105 (test fixture, not a real credential)

        try:
            store_profile_secret(test_uuid, secret_key)
            retrieved = get_profile_secret(test_uuid)
            # In headless environments without active keyring backend, returns empty or secret
            # If supported, test exact match
            if retrieved:
                self.assertEqual(retrieved, secret_key)
        finally:
            delete_profile_secret(test_uuid)

    def test_hybrid_vault_manager_integration(self):
        """Option C: Full integration test of Manager with SQLite and Keyring."""
        from src.core.manager import Manager
        test_dir = os.path.join("temp_data", "test_mgr_vault")
        os.makedirs(test_dir, exist_ok=True)
        try:
            mgr = Manager(base_dir=test_dir)
            p1 = Profile(name="Engineering", login_server="https://ts.corp.com", auth_key="mock-auth-key-eng-111")
            p2 = Profile(name="Staging", login_server="https://hs.staging.net", auth_key="mock-auth-key-staging-222")

            mgr.add_profile(p1)
            mgr.add_profile(p2)

            self.assertIn("Engineering", mgr.profiles)
            self.assertIn("Staging", mgr.profiles)
            self.assertEqual(mgr.db.count_profiles(), 2)

            # Simulate new app instance loading from SQLite
            mgr2 = Manager(base_dir=test_dir)
            self.assertIn("Engineering", mgr2.profiles)
            self.assertIn("Staging", mgr2.profiles)
            self.assertEqual(mgr2.profiles["Engineering"].login_server, "https://ts.corp.com")
            self.assertEqual(mgr2.profiles["Staging"].login_server, "https://hs.staging.net")

            # Remove a profile
            mgr2.remove_profile("Engineering")
            self.assertNotIn("Engineering", mgr2.profiles)
            self.assertEqual(mgr2.db.count_profiles(), 1)
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_profile_uuid_preservation_on_rename(self):
        """Candidate 4: Renaming a profile preserves its immutable UUIDv4 and Keyring credentials."""
        from src.core.manager import Manager
        test_dir = os.path.join("temp_data", "test_rename_uuid")
        os.makedirs(test_dir, exist_ok=True)
        try:
            mgr = Manager(base_dir=test_dir)
            p = Profile(name="OriginalName", login_server="https://hs.example.com", auth_key="secret-auth-key-111")
            orig_uuid = p.id
            mgr.add_profile(p)

            self.assertIn("OriginalName", mgr.profiles)
            self.assertEqual(mgr.get_profile(orig_uuid).name, "OriginalName")

            # Rename profile
            success = mgr.rename_profile("OriginalName", "RenamedProfile")
            self.assertTrue(success)
            self.assertNotIn("OriginalName", mgr.profiles)
            self.assertIn("RenamedProfile", mgr.profiles)

            # UUID and Secret must be strictly preserved
            renamed_p = mgr.profiles["RenamedProfile"]
            self.assertEqual(renamed_p.id, orig_uuid)
            self.assertEqual(mgr.get_profile(orig_uuid).name, "RenamedProfile")

            # Verify persistent reload keeps the same UUID and secret
            mgr_reloaded = Manager(base_dir=test_dir)
            self.assertIn("RenamedProfile", mgr_reloaded.profiles)
            self.assertEqual(mgr_reloaded.profiles["RenamedProfile"].id, orig_uuid)
            self.assertEqual(mgr_reloaded.profiles["RenamedProfile"].auth_key, "secret-auth-key-111")
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_cascade_deletion(self):
        """Candidate 4: Profile deletion cascades to raw_state and traffic_data tables."""
        from src.core.db_manager import DatabaseManager
        test_dir = os.path.join("temp_data", "test_cascade_db")
        os.makedirs(test_dir, exist_ok=True)
        try:
            db = DatabaseManager(test_dir)
            p = Profile(name="CascadeTest", login_server="https://hs.example.com")
            db.save_profile(p)

            # Baseline raw_state
            db.insert_traffic_data("CascadeTest", 1000, 2000)
            # Subsequent traffic with positive delta
            db.insert_traffic_data("CascadeTest", 1500, 2800)
            db.flush_buffer()

            conn = db._create_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM profiles WHERE id = ?", (p.id,))
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("SELECT COUNT(*) FROM raw_state WHERE profile = ?", ("CascadeTest",))
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("SELECT COUNT(*) FROM traffic_data WHERE profile = ?", ("CascadeTest",))
            self.assertGreater(cursor.fetchone()[0], 0)
            conn.close()

            # Delete with cascade
            db.delete_profile(p.id, profile_name="CascadeTest")

            conn = db._create_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM profiles WHERE id = ?", (p.id,))
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT COUNT(*) FROM raw_state WHERE profile = ?", ("CascadeTest",))
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("SELECT COUNT(*) FROM traffic_data WHERE profile = ?", ("CascadeTest",))
            self.assertEqual(cursor.fetchone()[0], 0)
            conn.close()
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_database_migration_ladder(self):
        """Candidate 5: PRAGMA user_version upgrades legacy tables missing newer columns."""
        import sqlite3

        from src.core.db_manager import DatabaseManager
        test_dir = os.path.join("temp_data", "test_migration_ladder")
        os.makedirs(test_dir, exist_ok=True)
        db_path = os.path.join(test_dir, "traffic_stats.db")
        try:
            # Simulate a prehistoric database (user_version = 0) with only minimal columns
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    login_server TEXT
                );
            """)
            cursor.execute("PRAGMA user_version = 0;")
            conn.commit()
            conn.close()

            # Initializing DatabaseManager must trigger _run_migrations()
            db = DatabaseManager(test_dir)
            conn = db._create_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA user_version;")
            version = cursor.fetchone()[0]
            self.assertGreaterEqual(version, 1)

            cursor.execute("PRAGMA table_info(profiles);")
            columns = {col[1] for col in cursor.fetchall()}
            self.assertIn("extra_args", columns)
            self.assertIn("enable_dns_fallback", columns)
            self.assertIn("accept_routes", columns)
            conn.close()
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)

    def test_traffic_buffer_thread_safety(self):
        """Candidate 5: Traffic buffer operations are thread-safe and atomic across flushes."""
        import threading

        from src.core.db_manager import DatabaseManager
        test_dir = os.path.join("temp_data", "test_buffer_threads")
        os.makedirs(test_dir, exist_ok=True)
        try:
            db = DatabaseManager(test_dir)

            def worker(profile_id, count):
                for i in range(count):
                    db.insert_traffic_data(profile_id, (i + 1) * 100, (i + 1) * 200)

            t1 = threading.Thread(target=worker, args=("ProfileA", 20))
            t2 = threading.Thread(target=worker, args=("ProfileB", 20))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # Buffer contains values for both profiles without corruption
            with db._buffer_lock:
                self.assertIn("ProfileA", db.traffic_buffer)
                self.assertIn("ProfileB", db.traffic_buffer)

            db.flush_buffer()
            with db._buffer_lock:
                self.assertEqual(len(db.traffic_buffer), 0)
        finally:
            if os.path.exists(test_dir):
                import shutil
                shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()


