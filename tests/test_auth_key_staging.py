import importlib.util
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_spec = importlib.util.spec_from_file_location(
    "_test_executor_mod", os.path.join(os.path.dirname(__file__), "test_executor.py"))
_te = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_te)

from src.core.tailscale import AUTH_KEY_FILE_PREFIX, TailscaleManager

#: Value handed to the staging code and then searched for in the argv list.
#: Deliberately *not* credential-shaped: a `tskey-auth-…` literal in the tree trips
#: GitHub secret scanning, and CodeQL reads a hardcoded secret written to disk as
#: clear-text storage. The staging code never validates the key's format, so a
#: realistic shape would add no coverage.
STAGED_VALUE = "fixture-value-that-must-never-reach-the-argv"


def make_manager():
    ex = _te.FakeExecutor()
    mgr = TailscaleManager(cache_dir=tempfile.mkdtemp(), executor=ex)
    return mgr, ex


class TestAuthKeyStaging(unittest.TestCase):
    """Finding 4: the pre-auth key must not be exposed on the command line."""

    def tearDown(self):
        for path in list(getattr(self, "_staged", [])):
            if os.path.exists(path):
                os.remove(path)

    def _staged_path(self, args):
        key_arg = next(a for a in args if a.startswith("--auth-key"))
        return key_arg.split("file:", 1)[1] if "file:" in key_arg else None

    def test_key_is_passed_by_file_reference(self):
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE})

        args, _ = ex.commands[-1]
        path = self._staged_path(args)
        self.assertIsNotNone(path, f"expected --auth-key=file:<path>, got {args}" )
        self._staged = [path]
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), STAGED_VALUE)

    def test_secret_never_appears_in_the_argument_list(self):
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE})

        args, _ = ex.commands[-1]
        self._staged = [self._staged_path(args)]
        self.assertNotIn(STAGED_VALUE, " ".join(args))

    def test_staged_file_is_removed_when_the_command_finishes(self):
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE})
        path = self._staged_path(ex.commands[-1][0])

        ex.finished.emit(0, "0")
        self.assertFalse(os.path.exists(path), "staged key survived a finished command")

    def test_staged_file_is_removed_on_shutdown(self):
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE})
        path = self._staged_path(ex.commands[-1][0])

        mgr.cleanup()
        self.assertFalse(os.path.exists(path), "staged key survived cleanup/exit")

    def test_restaging_clears_the_previous_file(self):
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE})
            first = self._staged_path(ex.commands[-1][0])
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE + "x"})
            second = self._staged_path(ex.commands[-1][0])
        self._staged = [second]
        self.assertNotEqual(first, second)
        self.assertFalse(os.path.exists(first), "previous staged key was left behind")

    def test_sso_flow_stages_nothing(self):
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE, "use_sso": True})
        args, _ = ex.commands[-1]
        self.assertFalse(any(a.startswith("--auth-key") for a in args), "SSO mode must not pass a key")

    def test_survives_an_unwritable_temp_dir(self):
        """Falls back to the inline form rather than failing the connection."""
        mgr, ex = make_manager()
        with patch.object(type(mgr), "start_service", lambda self: None), \
                patch("tempfile.mkstemp", side_effect=OSError("read-only temp")):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": STAGED_VALUE})
        args, _ = ex.commands[-1]
        self.assertIn(f"--auth-key={STAGED_VALUE}", args)


class TestStaleKeySweep(unittest.TestCase):
    """A crash mid-connect must not leave the key file on disk forever."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sweep_")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def _make_file(self, age_seconds):
        path = os.path.join(self.tmp, f"{AUTH_KEY_FILE_PREFIX}stale.key")
        # The sweeper only inspects the file's name and mtime, so this fixture
        # writes an inert marker instead of the value the staging tests use.
        with open(path, "w", encoding="utf-8") as f:
            f.write("stale-fixture")
        stamp = time.time() - age_seconds
        os.utime(path, (stamp, stamp))
        return path

    def test_old_leftover_is_removed(self):
        from src.core.tailscale import STALE_KEY_MAX_AGE_SECONDS

        old = self._make_file(STALE_KEY_MAX_AGE_SECONDS + 600)
        with patch("tempfile.gettempdir", return_value=self.tmp):
            TailscaleManager._sweep_stale_key_files()
        self.assertFalse(os.path.exists(old), "stale key file was not swept")

    def test_fresh_file_is_kept(self):
        """Never delete a key that a concurrent session may still be using."""
        fresh = self._make_file(5)
        with patch("tempfile.gettempdir", return_value=self.tmp):
            TailscaleManager._sweep_stale_key_files()
        self.assertTrue(os.path.exists(fresh), "a fresh key file was deleted")


if __name__ == "__main__":
    unittest.main()
