"""Automated accessibility smoke test.

The compliance documents claim EN 301 549 / WCAG 2.1 AA conformance; the only
automated backing for that claim used to be `a11y_checker` probing for screen
reader components. These tests verify the other half: that interactive widgets
in the shipped dialogs actually carry accessible names.

A QApplication is created at import time (offscreen) because pytest imports this
module first (alphabetically), before test modules that build a QCoreApplication.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSlider,
    QApplication,
    QComboBox,
    QLineEdit,
    QListWidget,
    QTableWidget,
    QTabWidget,
    QTextBrowser,
    QWidget,
)

_app = QApplication.instance() or QApplication([])

# Widgets a user operates; QScrollBar/QTabBar are internal Qt children whose
# accessibility is provided by their container, so they are out of scope here.
INTERACTIVE = (QAbstractButton, QLineEdit, QComboBox, QListWidget, QTableWidget,
               QTextBrowser, QTabWidget, QAbstractSlider)
INTERNAL = ("QScrollBar", "QTabBar", "QAbstractSpinBox")


def build_dialogs():
    """Constructs the dialogs that can be built without user data or a daemon."""
    from src.ui.components.diagnostics_dialog import DiagnosticsDialog
    from src.ui.components.log_viewer_dlg import LogViewerDialog
    from src.ui.components.profile_name_dialog import ProfileNameDialog
    from src.ui.components.simple_dialogs import AboutDialog, LicenseDialog, ReadmeDialog

    log_path = os.path.join(tempfile.mkdtemp(prefix="a11y_"), "app.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2026-09-16 10:00:00,000 - INFO - [x.py:1] - sample\n")

    return {
        "AboutDialog": AboutDialog,
        "LicenseDialog": LicenseDialog,
        "ReadmeDialog": ReadmeDialog,
        "DiagnosticsDialog": DiagnosticsDialog,
        "ProfileNameDialog": ProfileNameDialog,
        "LogViewerDialog": lambda: LogViewerDialog(log_path, "app.log"),
    }


class TestDialogAccessibility(unittest.TestCase):
    def test_import_time_application_is_still_alive(self):
        """The dialogs below can only be built while the shared QApplication lives."""
        self.assertIs(QApplication.instance(), _app)

    def _audit(self, factory):
        dialog = factory()
        try:
            missing = []
            for widget in dialog.findChildren(QWidget):
                if not isinstance(widget, INTERACTIVE) or type(widget).__name__ in INTERNAL:
                    continue
                if not widget.accessibleName().strip():
                    missing.append(f"{type(widget).__name__}({widget.objectName() or 'unnamed'})")
            return missing
        finally:
            dialog.deleteLater()

    def test_every_dialog_is_constructible(self):
        """Also guards against a .ui rename breaking a dialog at runtime."""
        for name, factory in build_dialogs().items():
            with self.subTest(dialog=name):
                dialog = factory()
                self.assertIsNotNone(dialog)
                dialog.deleteLater()

    def test_interactive_widgets_have_accessible_names(self):
        for name, factory in build_dialogs().items():
            with self.subTest(dialog=name):
                missing = self._audit(factory)
                self.assertEqual(missing, [], f"{name}: widgets without an accessible name: {missing}")

    def test_key_controls_have_accessible_descriptions(self):
        """Buttons that trigger an action need more than a bare name."""
        for name, factory in build_dialogs().items():
            dialog = factory()
            try:
                for button in dialog.findChildren(QAbstractButton):
                    if type(button).__name__ in INTERNAL:
                        continue
                    with self.subTest(dialog=name, button=button.objectName() or type(button).__name__):
                        self.assertTrue(button.accessibleName().strip(),
                                        f"{name}: button {button.objectName()!r} has no accessible name")
                        self.assertTrue(button.accessibleDescription().strip(),
                                        f"{name}: button {button.objectName()!r} has no accessible description")
            finally:
                dialog.deleteLater()


class TestA11yCheckerContract(unittest.TestCase):
    """The screen-reader probe must always answer with a usable result."""

    def test_checker_returns_structured_result(self):
        from src.utils.a11y_checker import check_screen_reader_environment

        result = check_screen_reader_environment()
        self.assertIsInstance(result.is_healthy, bool)
        self.assertTrue(result.title.strip())
        self.assertTrue(result.summary.strip())
        self.assertTrue(result.details.strip())


if __name__ == "__main__":
    unittest.main()
