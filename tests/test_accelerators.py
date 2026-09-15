import os
import re
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.main_window import CONNECT_TOGGLE_SHORTCUT, GLOBAL_ACCELERATORS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UI_DIR = os.path.join(ROOT, "pygui", "windows")


def ui_shortcuts(ui_file):
    """Accelerator strings declared in a Qt Designer .ui file."""
    with open(os.path.join(UI_DIR, ui_file), encoding="utf-8") as f:
        return set(re.findall(r'<property name="shortcut">\s*<string>(.*?)</string>', f.read()))


def readme_accelerators():
    """Accelerators listed in the README 'Application Global Accelerators' table."""
    with open(os.path.join(ROOT, "Docs", "README.md"), encoding="utf-8") as f:
        text = f.read()
    section = re.search(
        r"### Application Global Accelerators(.*?)(?:\n### |\n---)", text, re.DOTALL)
    if not section:
        return set()

    shortcuts = set()
    for raw_line in section.group(1).splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or line.startswith("| :") or "Shortcut" in line:
            continue
        cell = line.split("|")[1]
        keys = re.findall(r"<kbd>(.*?)</kbd>", cell)
        if keys:
            shortcuts.add("+".join(k.strip() for k in keys))
    return shortcuts


class TestAcceleratorConsistency(unittest.TestCase):
    """The designer .ui, the Python rebuild and the docs must agree on shortcuts."""

    def test_code_implements_every_designed_accelerator(self):
        designed = ui_shortcuts("main_window.ui")
        self.assertTrue(designed, "no accelerators found in pygui/windows/main_window.ui")
        implemented = set(GLOBAL_ACCELERATORS.values())
        self.assertEqual(designed - implemented, set(),
                         "accelerators declared in main_window.ui but not applied in code")

    def test_connect_toggle_matches_designer(self):
        self.assertIn(CONNECT_TOGGLE_SHORTCUT, ui_shortcuts("tab_widget.ui"))

    def test_documented_accelerators_all_exist(self):
        documented = readme_accelerators()
        self.assertTrue(documented, "could not parse the README accelerator table")
        implemented = set(GLOBAL_ACCELERATORS.values()) | {CONNECT_TOGGLE_SHORTCUT}
        self.assertEqual(documented - implemented, set(),
                         "shortcuts documented in Docs/README.md but not implemented")

    def test_no_duplicate_accelerators(self):
        sequences = list(GLOBAL_ACCELERATORS.values()) + [CONNECT_TOGGLE_SHORTCUT]
        self.assertEqual(len(sequences), len(set(sequences)), "duplicate shortcut binding")


if __name__ == "__main__":
    unittest.main()
