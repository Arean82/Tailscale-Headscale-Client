import importlib.util
import os
import sys
import time
import unittest
from typing import ClassVar

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_SC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "auto_translate.py"))
_spec = importlib.util.spec_from_file_location("_auto_translate", _SC)
_at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_at)

from src.ui.main_window import MainWindow


class FakePipe:
    def __init__(self, payload):
        self._payload = payload

    def data(self):
        return self._payload


class FakeProc:
    """Minimal stand-in for the QProcess the daemon probe inspects."""

    def __init__(self, stderr=b"", stdout=b"", exit_code=0):
        self._stderr, self._stdout, self._code = stderr, stdout, exit_code

    def readAllStandardError(self):
        return FakePipe(self._stderr)

    def readAllStandardOutput(self):
        return FakePipe(self._stdout)

    def exitCode(self):
        return self._code


class TestShortcutDetection(unittest.TestCase):
    """CodeQL alert #103: the regex must not backtrack exponentially."""

    REAL_SHORTCUTS: ClassVar[list[str]] = [
        "Ctrl+Return", "Ctrl+,", "Ctrl+Q", "Ctrl+N", "Ctrl+Shift+D", "Ctrl+Shift+P",
        "Ctrl+Shift+N", "Ctrl+Shift+S", "Ctrl+Alt+A", "F1", "Shift+F1",
        "Ctrl + Return",  # whitespace variant must still be recognised
    ]

    def test_all_real_shortcuts_are_detected(self):
        for shortcut in self.REAL_SHORTCUTS:
            self.assertFalse(_at.is_translatable(shortcut), f"missed shortcut {shortcut!r}")

    def test_normal_ui_strings_are_translatable(self):
        for text in ("Close", "Add New Profile", "VPN Status: Disconnected",
                     "Accept DNS (--accept-dns)", "e.g. 10.0.0.0/24", "F1 help text", "Ctrl"):
            self.assertTrue(_at.is_translatable(text), f"wrongly skipped {text!r}")

    def test_stylesheet_strings_still_skipped(self):
        self.assertFalse(_at.is_translatable("color: #569cd6;"))
        self.assertFalse(_at.is_translatable("border: none; background: transparent;"))

    def test_adversarial_input_is_linear(self):
        # The old pattern was exponential on inputs like 'Alt+' + many '+!' pairs
        adversarial = "Alt+" + ("+!" * 40) + "+x"
        started = time.monotonic()
        _at.is_translatable(adversarial)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.5, f"regex took {elapsed:.2f}s — looks like catastrophic backtracking")


class TestDaemonProbeResult(unittest.TestCase):
    """CodeQL alert #104: the classification used to sit inline in a closure."""

    def test_reachable_daemon(self):
        self.assertTrue(MainWindow._daemon_probe_result(FakeProc(stdout=b'{"BackendState":"Running"}')))

    def test_nonzero_exit_means_unreachable(self):
        self.assertFalse(MainWindow._daemon_probe_result(FakeProc(exit_code=1)))

    def test_cli_error_messages_are_detected_case_insensitively(self):
        self.assertFalse(MainWindow._daemon_probe_result(FakeProc(stderr=b"failed to connect to local tailscaled")))
        self.assertFalse(MainWindow._daemon_probe_result(FakeProc(stderr=b"Tailscaled may not be running")))

    def test_logged_out_daemon_still_counts_as_running(self):
        # NeedsLogin is a healthy daemon: the wait dialog must not appear
        self.assertTrue(MainWindow._daemon_probe_result(FakeProc(stdout=b'{"BackendState":"NeedsLogin"}')))


if __name__ == "__main__":
    unittest.main()
