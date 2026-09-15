import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.main_window import MainWindow


class FakeWindow:
    """Stands in for MainWindow's dependencies only.

    MainWindow itself is a top-level widget (tray icon, timers, .ui loading) and
    terminating the interpreter when built headless, so the real
    check_daemon_async is exercised as an unbound method against this stub.
    """

    def __init__(self, use_local_api):
        self.manager = SimpleNamespace(settings=SimpleNamespace(use_local_api=use_local_api))
        self.cli_probes = []
        self.probe_results = []
        self._probe_daemon_cli = self.cli_probes.append
        self._handle_daemon_probe = lambda running, retry: self.probe_results.append((running, retry))


class TestLocalApiToggleIsAuthoritative(unittest.TestCase):
    """'Enable Experimental Local API' off must mean zero LocalAPI contact."""

    def _patch_probe(self):
        from src.utils import local_api

        calls = []
        original = local_api.is_local_api_available
        local_api.is_local_api_available = lambda *a, **k: (calls.append(1), True)[1]
        self.addCleanup(setattr, local_api, "is_local_api_available", original)
        return calls

    def test_toggle_off_never_contacts_localapi(self):
        calls = self._patch_probe()
        win = FakeWindow(use_local_api=False)

        MainWindow.check_daemon_async(win)

        self.assertEqual(calls, [], "LocalAPI was contacted while the toggle is off")
        self.assertEqual(len(win.cli_probes), 1, "the CLI probe should have been used instead")

    def test_toggle_on_uses_localapi_probe(self):
        calls = self._patch_probe()
        win = FakeWindow(use_local_api=True)

        MainWindow.check_daemon_async(win)

        self.assertEqual(len(calls), 1, "the LocalAPI probe should run while ticked")
        self.assertEqual(win.cli_probes, [], "no CLI probe when the LocalAPI answered")

    def test_running_daemon_stops_retrying(self):
        self._patch_probe()
        win = FakeWindow(use_local_api=True)
        MainWindow.check_daemon_async(win)
        # is_local_api_available() returns True in the stub -> no retry scheduled
        self.assertEqual(win.probe_results, [(True, 0)])


if __name__ == "__main__":
    unittest.main()
