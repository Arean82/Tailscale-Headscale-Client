import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.components.log_viewer_dlg import classify_line
from src.utils.logger import SignalLogHandler


class TestClassifyLine(unittest.TestCase):
    """The viewer colours and filters on this classification."""

    def test_levels(self):
        self.assertEqual(classify_line("2026-09-16 - ERROR - boom"), "error")
        self.assertEqual(classify_line("2026-09-16 - CRITICAL - boom"), "error")
        self.assertEqual(classify_line("Traceback: Exception in slot"), "error")
        self.assertEqual(classify_line("2026-09-16 - WARNING - careful"), "warning")
        self.assertEqual(classify_line("2026-09-16 - DEBUG - detail"), "debug")
        self.assertEqual(classify_line("2026-09-16 - INFO - started"), "info")
        self.assertEqual(classify_line("plain unlabelled line"), "info")

    def test_error_wins_over_other_markers(self):
        # A line mentioning both WARN and ERROR must be treated as an error
        self.assertEqual(classify_line("WARNING then ERROR occurred"), "error")


class TestSignalLogHandler(unittest.TestCase):
    """Live tailing plumbing: records must reach the sink, formatted like the file."""

    def setUp(self):
        self.received = []
        self.logger = logging.getLogger("TailscaleClient.TestStream")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

    def tearDown(self):
        self.logger.handlers.clear()

    def test_formats_like_the_file_handler(self):
        handler = SignalLogHandler(self.received.append)
        self.logger.addHandler(handler)
        self.logger.warning("tunnel dropped")

        self.assertEqual(len(self.received), 1)
        line = self.received[0]
        self.assertIn("WARNING", line)
        self.assertIn("tunnel dropped", line)
        self.assertEqual(classify_line(line), "warning")

    def test_respects_level_filter(self):
        handler = SignalLogHandler(self.received.append, level=logging.WARNING)
        self.logger.addHandler(handler)
        self.logger.debug("noise")
        self.logger.error("signal")
        self.assertEqual(len(self.received), 1)
        self.assertIn("signal", self.received[0])

    def test_failing_sink_never_breaks_logging(self):
        def bad_sink(_line):
            raise RuntimeError("viewer exploded")

        handler = SignalLogHandler(bad_sink)
        self.logger.addHandler(handler)
        self.logger.error("must not raise")  # would propagate if emit() didn't guard

    def test_detaching_stops_delivery(self):
        handler = SignalLogHandler(self.received.append)
        self.logger.addHandler(handler)
        self.logger.info("before detach")
        self.logger.removeHandler(handler)
        self.logger.info("after detach")
        self.assertEqual(len(self.received), 1)
        self.assertIn("before detach", self.received[0])

    def test_child_loggers_reach_the_app_logger_sink(self):
        """Attaching to TailscaleClient must capture nested UI/core loggers."""
        app_logger = logging.getLogger("TailscaleClient")
        original_level = app_logger.level
        app_logger.setLevel(logging.DEBUG)
        handler = SignalLogHandler(self.received.append)
        app_logger.addHandler(handler)
        try:
            logging.getLogger("TailscaleClient.UI.Dashboard").debug("expiry probe")
        finally:
            app_logger.removeHandler(handler)
            app_logger.setLevel(original_level)

        self.assertEqual(len(self.received), 1)
        self.assertIn("expiry probe", self.received[0])


if __name__ == "__main__":
    unittest.main()
