import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCriticalBugFixes(unittest.TestCase):
    """Regression tests for the four critical fixes from the 2026-09-14 review."""

    def test_manage_sys_streams_survives_missing_console(self):
        """Bug 1: windowed (console=False) builds have sys.__stdout__/__stderr__ = None;
        restoring them directly made every print() raise inside Qt slots."""
        from src.utils.logger import manage_sys_streams
        real_dunder_out, real_dunder_err = sys.__stdout__, sys.__stderr__
        saved_stdout, saved_stderr = sys.stdout, sys.stderr
        try:
            sys.__stdout__ = None
            sys.__stderr__ = None
            manage_sys_streams(False, None)
            self.assertIsNotNone(sys.stdout)
            self.assertIsNotNone(sys.stderr)
            print("must not raise")
            sys.stdout.write("direct write")
            sys.stdout.flush()
            self.assertFalse(sys.stdout.isatty())
        finally:
            sys.__stdout__, sys.__stderr__ = real_dunder_out, real_dunder_err
            sys.stdout, sys.stderr = saved_stdout, saved_stderr

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


if __name__ == "__main__":
    unittest.main()
