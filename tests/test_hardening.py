import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from typing import ClassVar
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.executor import _BlockingWorker
from src.utils import autostart
from src.utils import logger as log_module


def _reset_profile_loggers():
    """Drops cached profile loggers *and* their handlers, so each test gets a
    handler pointing at its own temp directory."""
    log_module._profile_loggers.clear()
    for name in list(logging.Logger.manager.loggerDict):
        if str(name).startswith("TailscaleClient.Profile."):
            logging.getLogger(name).handlers.clear()


class TestProfileLogHardening(unittest.TestCase):
    """Findings 5 + 6: profile connection logs must be redacted and rotated."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="profilelog_")
        _reset_profile_loggers()

    def tearDown(self):
        _reset_profile_loggers()

    def _log_path(self, profile):
        return os.path.join(self.tmp, "GlobalLogs", f"{profile}_connection.log")

    def test_credentials_are_redacted(self):
        log_module.write_profile_log("HQ", "connecting with tskey-auth-mockSEKRET123456", base_dir=self.tmp)
        with open(self._log_path("HQ"), encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("mockSEKRET123456", content)
        self.assertIn("tskey-[REDACTED]", content)

    def test_log_rotates_instead_of_growing_without_bound(self):
        original = log_module.PROFILE_LOG_MAX_BYTES
        log_module.PROFILE_LOG_MAX_BYTES = 512
        try:
            for i in range(60):
                log_module.write_profile_log("Rotate", f"chunk {i} " + "x" * 80, base_dir=self.tmp)
        finally:
            log_module.PROFILE_LOG_MAX_BYTES = original

        files = sorted(os.listdir(os.path.join(self.tmp, "GlobalLogs")))
        self.assertIn("Rotate_connection.log", files)
        self.assertTrue(any(f.endswith(".1") for f in files), f"no rotation happened: {files}")
        self.assertLess(os.path.getsize(self._log_path("Rotate")), 4 * 512,
                        "active log grew past the cap — rotation is not bounding it")

    def test_blank_input_writes_nothing(self):
        log_module.write_profile_log("Empty", "")
        self.assertFalse(os.path.exists(self._log_path("Empty")))

    def test_app_log_still_used_for_application_records(self):
        """Profile loggers must not leak into app.log (propagate=False)."""
        logger = log_module.get_profile_logger("Leak", base_dir=self.tmp)
        self.assertFalse(logger.propagate)


class TestCrashHandler(unittest.TestCase):
    """Finding 3: unhandled exceptions must reach the log, not a missing stderr."""

    def _capture(self):
        records = []

        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = Capture()
        crash_logger = logging.getLogger("TailscaleClient.CrashHandler")
        original_level = crash_logger.level
        crash_logger.setLevel(logging.DEBUG)
        crash_logger.addHandler(handler)
        self.addCleanup(lambda: (crash_logger.removeHandler(handler), crash_logger.setLevel(original_level)))
        return records

    def test_main_thread_exception_is_logged_with_traceback(self):
        from src.utils.crash_handler import log_unhandled

        records = self._capture()
        try:
            raise ValueError("boom")
        except ValueError:
            log_unhandled(*sys.exc_info())

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].levelno, logging.CRITICAL)
        self.assertIn("boom", records[0].getMessage())
        self.assertIsNotNone(records[0].exc_info)

    def test_keyboard_interrupt_is_left_alone(self):
        from src.utils.crash_handler import log_unhandled

        with patch.object(sys, "__excepthook__") as fallback:
            log_unhandled(KeyboardInterrupt, KeyboardInterrupt(), None)
        fallback.assert_called_once()

    def test_worker_thread_exception_is_logged(self):
        from src.utils.crash_handler import log_unhandled_thread

        class Args:
            exc_type = RuntimeError
            exc_value = RuntimeError("worker died")
            exc_traceback = None
            thread = threading.current_thread()

        records = self._capture()
        log_unhandled_thread(Args())
        self.assertEqual(len(records), 1)
        self.assertIn("worker died", records[0].getMessage())

    def test_qt_messages_are_routed(self):
        from PySide6.QtCore import QtMsgType

        from src.utils.crash_handler import log_qt_message

        records = self._capture()
        log_qt_message(QtMsgType.QtWarningMsg, None, "QProcess: destroyed while running")
        self.assertEqual(records[0].levelno, logging.WARNING)
        self.assertIn("QProcess", records[0].getMessage())


class TestMacAutostart(unittest.TestCase):
    """Finding 8: the plist must be loaded/unloaded, not just written."""

    def _run_with_platform(self, enabled):
        calls = []
        with patch.object(sys, "platform", "darwin"), \
                patch.object(autostart, "_launchctl", side_effect=lambda *a: calls.append(a)), \
                patch("os.path.expanduser", return_value=tempfile.mkdtemp()):
            autostart.set_autostart(enabled)
        return [c[0] for c in calls]

    def test_enabling_loads_the_agent(self):
        self.assertIn("load", self._run_with_platform(True))

    def test_disabling_unloads_the_agent(self):
        self.assertIn("unload", self._run_with_platform(False))

    def test_launchctl_failure_is_not_fatal(self):
        with patch("subprocess.run", side_effect=OSError("launchctl missing")):
            self.assertFalse(autostart._launchctl("load", "/nonexistent.plist"))


class TestWorkerCancellation(unittest.TestCase):
    """Finding 9: an in-flight CLI child must be killable at shutdown."""

    SLEEP_CMD: ClassVar[list[str]] = [sys.executable, "-c", "import time; time.sleep(30)"]

    def test_cancel_current_kills_the_child(self):
        worker = _BlockingWorker()
        result = {}

        def run():
            try:
                result["outcome"] = worker._run(list(self.SLEEP_CMD), timeout=25)
            except Exception as e:  # noqa: BLE001 - captured for the assertion
                result["error"] = e

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        deadline = time.monotonic() + 15
        while worker._current_proc is None and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertIsNotNone(worker._current_proc, "child never started")

        worker.cancel_current()
        thread.join(timeout=15)
        self.assertFalse(thread.is_alive(), "worker did not return after cancel")
        self.assertIn("outcome", result, f"worker raised instead of returning: {result.get('error')}")
        code, _, _ = result["outcome"]
        self.assertNotEqual(code, 0, "a killed child must not report success")
        self.assertIsNone(worker._current_proc, "child reference was not cleared")

    def test_timeout_kills_the_child_and_raises(self):
        worker = _BlockingWorker()
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            worker._run(list(self.SLEEP_CMD), timeout=0.5)
        self.assertLess(time.monotonic() - started, 6.0)
        self.assertIsNone(worker._current_proc)

    def test_successful_run_returns_streams(self):
        worker = _BlockingWorker()
        code, out, err = worker._run([sys.executable, "-c", "print('hi')"], timeout=15)
        self.assertEqual(code, 0)
        self.assertIn("hi", out)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
