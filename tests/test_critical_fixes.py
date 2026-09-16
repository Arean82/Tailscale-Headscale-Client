import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main


class TestCriticalBugFixes(unittest.TestCase):
    """Regression tests for the four critical fixes from the 2026-09-14 review."""

    def test_manage_sys_streams_survives_missing_console(self):
        """Bug 1: windowed (console=False) builds have sys.__stdout__/__stderr__ = None;
        restoring them directly made every print() raise inside Qt slots."""
        from src.utils.logger import manage_sys_streams
        # patch.object: mypy rejects direct assignment to the final dunders
        # (ruff rejects setattr), and patch restores every stream on exit.
        with patch.object(sys, "__stdout__", None), \
                patch.object(sys, "__stderr__", None), \
                patch.object(sys, "stdout", sys.stdout), \
                patch.object(sys, "stderr", sys.stderr):
            manage_sys_streams(False, None)
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
            print("must not raise")
            sys.stdout.write("direct write")
            sys.stdout.flush()
            self.assertFalse(sys.stdout.isatty())

    def test_apply_fallback_pins_domain_when_dns_fails(self):
        """Bug 2: the inverted early-return skipped the hosts-file edit exactly
        when DNS resolution failed — the emergency the feature exists for."""
        from src.utils import dns_fallback as df
        tmp = os.path.join(tempfile.gettempdir(), "hosts_df_regression")
        with open(tmp, "w") as f:
            f.write("127.0.0.1 localhost\n")
        original_hosts = df.HOSTS_FILE
        df.HOSTS_FILE = tmp
        try:
            domain = "definitely-nonexistent-48151623.invalid"
            self.assertTrue(df.apply_fallback(domain, "192.0.2.55"))
            with open(tmp) as f:
                content = f.read()
            self.assertIn(f"192.0.2.55 {domain}", content)

            # Re-apply must not duplicate the pinned entry.
            self.assertTrue(df.apply_fallback(domain, "192.0.2.55"))
            with open(tmp) as f:
                self.assertEqual(f.read().count(f"192.0.2.55 {domain}"), 1)

            # Domain already resolving to the target IP short-circuits without editing.
            self.assertTrue(df.apply_fallback("localhost", "127.0.0.1"))
        finally:
            df.HOSTS_FILE = original_hosts
            os.remove(tmp)

    def test_apply_fallback_non_windows_returns_false_without_elevation(self):
        """Bug 2 (crash half): non-Windows platforms must return False instead of
        reaching ctypes.windll and raising AttributeError inside connect()."""
        from src.utils import dns_fallback as df
        tmpdir = tempfile.mkdtemp()
        bogus_hosts = os.path.join(tmpdir, "no_such_dir", "hosts")
        original_hosts = df.HOSTS_FILE
        df.HOSTS_FILE = bogus_hosts
        try:
            with patch.object(df.sys, "platform", "linux"):
                self.assertFalse(df.apply_fallback("some.domain.invalid", "192.0.2.1"))
        finally:
            df.HOSTS_FILE = original_hosts
            os.rmdir(tmpdir)

    def test_build_up_args_survives_malformed_extra_args(self):
        """Bug 3: the shlex error handler referenced a non-existent self.logger,
        turning a recoverable parse error into an AttributeError in connect()."""
        from src.core.tailscale import TailscaleManager

        class FakeSelf:
            insecure_ssl = False

        args = TailscaleManager._build_up_args(
            FakeSelf(),
            {"login_server": "https://hs.example.com", "extra_args": '"unbalanced'},
        )
        self.assertIn("--login-server=https://hs.example.com", args)
        self.assertFalse(any("unbalanced" in a for a in args))

        ok_args = TailscaleManager._build_up_args(
            FakeSelf(),
            {"login_server": "https://hs.example.com", "extra_args": "--foo bar"},
        )
        self.assertIn("--foo", ok_args)
        self.assertIn("bar", ok_args)

    def test_qt_material_declared_for_installs_and_freezing(self):
        """Bug 4: main_window imports qt_material at runtime; it must be listed in
        requirements.txt and in every PyInstaller spec's hiddenimports."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(os.path.join(root, "requirements.txt"), encoding="utf-8") as f:
            self.assertIn("qt-material", f.read().replace("_", "-").lower())
        for spec in (
            "TailscaleClient_OneFile.spec",
            "TailscaleClient_OneDir.spec",
            "TailscaleClient_Mac.spec",
        ):
            with open(os.path.join(root, spec), encoding="utf-8") as f:
                self.assertIn("'qt_material'", f.read(), msg=spec)

    def test_dns_fallback_cli_routing(self):
        """Frozen elevated relaunch: --dns-fallback args must dispatch to the
        hosts editor and return an exit code; anything else returns None."""
        from src.utils import dns_fallback as df
        calls = []

        def fake_edit(domain, ip):
            calls.append((domain, ip))
            return True

        with patch.object(df, "_edit_hosts", fake_edit):
            self.assertIsNone(df.run_cli_if_requested(["prog.exe", "--gui"]))
            self.assertIsNone(df.run_cli_if_requested(["prog.exe"]))
            self.assertEqual(
                df.run_cli_if_requested(["prog.exe", "--dns-fallback", "apply", "hs.example.com", "1.2.3.4"]), 0
            )
            self.assertEqual(
                df.run_cli_if_requested(["prog.exe", "--dns-fallback", "remove", "hs.example.com"]), 0
            )
            self.assertEqual(df.run_cli_if_requested(["prog.exe", "--dns-fallback", "bogus"]), 2)
        self.assertEqual(calls, [("hs.example.com", "1.2.3.4"), ("hs.example.com", None)])

    def test_flush_buffer_restores_on_write_failure(self):
        """Candidate 5 gap: a DB write error mid-flush must not silently discard
        buffered traffic deltas — the snapshot is merged back into the buffer."""
        import sqlite3

        from src.core.db_manager import DatabaseManager
        tmp_dir = os.path.join(tempfile.gettempdir(), "db_flush_regression")
        os.makedirs(tmp_dir, exist_ok=True)
        try:
            db = DatabaseManager(tmp_dir)
            db.traffic_buffer["p"] = {"sent": 100, "recv": 50}

            class BadCursor:
                def execute(self, *args, **kwargs):
                    raise sqlite3.Error("disk I/O error (simulated)")

            class BadConn:
                def cursor(self):
                    return BadCursor()

                def close(self):
                    pass

            db._create_connection = BadConn
            db.flush_buffer()
            self.assertEqual(db.traffic_buffer.get("p"), {"sent": 100, "recv": 50})

            # Also verify the no-connection path restores
            db.traffic_buffer["p2"] = {"sent": 10, "recv": 5}
            db._create_connection = lambda: None
            db.flush_buffer()
            self.assertEqual(db.traffic_buffer.get("p2"), {"sent": 10, "recv": 5})
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestInstallerMutex(unittest.TestCase):
    """Inno Setup watches AppMutex to refuse replacing files of a running app."""

    def test_non_windows_creates_no_handle(self):
        with patch.object(main.sys, "platform", "linux"):
            self.assertIsNone(main.acquire_installer_mutex())

    def test_handle_is_created_once_and_then_reused(self):
        calls = []

        def create_mutex(*args):
            calls.append(args)
            return 4321

        fake_ctypes = SimpleNamespace(
            windll=SimpleNamespace(kernel32=SimpleNamespace(CreateMutexW=create_mutex)))
        with patch.object(main, "ctypes", fake_ctypes), \
                patch.object(main.sys, "platform", "win32"), \
                patch.object(main, "_mutex_handle", None):
            first = main.acquire_installer_mutex()
            second = main.acquire_installer_mutex()

        self.assertEqual(first, 4321, "the handle must reach the caller")
        self.assertIs(first, second, "a second call must not create a second mutex")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], main.SINGLE_INSTANCE_MUTEX,
                         "the mutex name must match AppMutex in the installer script")

    def test_a_failing_create_leaves_the_app_running(self):
        """Best-effort by design: no mutex arm on Windows must not be fatal."""
        class Boom:
            def __getattr__(self, name):
                raise AttributeError(name)

        # create=True: the module-level logger only exists once the entry point has
        # run setup_logger, which it always has by the time this is called.
        with patch.object(main, "ctypes", SimpleNamespace(windll=Boom())), \
                patch.object(main.sys, "platform", "win32"), \
                patch.object(main, "_mutex_handle", None), \
                patch.object(main, "logger", SimpleNamespace(debug=lambda *_: None), create=True):
            self.assertIsNone(main.acquire_installer_mutex())


if __name__ == "__main__":
    unittest.main()
