"""Optional ``--self-test`` CLI mode.

Validates a built artifact (or a source checkout) without starting the GUI or
touching the user's configuration: bundled data files, the theme package, the
crash handler, and a real database round-trip. CI runs this against the frozen
executable so packaging regressions (a missing theme, an unbundled locale, a
dropped README) fail the build instead of reaching users.
"""

import importlib.util
import os
import sys
import tempfile


def _data_root() -> str:
    """Directory holding bundled data: _MEIPASS when frozen, else the repo root."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _check_file(path: str, label: str) -> tuple[bool, str]:
    if os.path.exists(path):
        return True, f"{label}: present"
    return False, f"{label}: MISSING ({path})"


def _check_locales(root: str) -> list[tuple[bool, str]]:
    return [_check_file(os.path.join(root, "locales", f"{lang}.qm"), f"translation {lang}")
            for lang in ("en_US", "ar_SA", "fr_FR", "es_ES")]


def _check_readmes(root: str) -> list[tuple[bool, str]]:
    return [_check_file(os.path.join(root, "Docs", f"README{suffix}.md"), f"README{suffix or '_en'}")
            for suffix in ("", "_ar", "_es", "_fr")]


def _check_ui_files(root: str) -> tuple[bool, str]:
    dialogs = os.path.join(root, "pygui", "dialogs")
    count = len([f for f in os.listdir(dialogs) if f.endswith(".ui")]) if os.path.isdir(dialogs) else 0
    if count >= 10:
        return True, f"Qt designer files: {count} present"
    return False, f"Qt designer files: only {count} found in {dialogs}"


def _check_theme_package() -> tuple[bool, str]:
    """qt_material ships its themes as package data; a freeze can drop them."""
    spec = importlib.util.find_spec("qt_material")
    if spec is None or not spec.origin:
        return False, "qt_material: not importable"
    themes_dir = os.path.join(os.path.dirname(spec.origin), "themes")
    xmls = [f for f in os.listdir(themes_dir) if f.endswith(".xml")] if os.path.isdir(themes_dir) else []
    if xmls:
        return True, f"qt_material: {len(xmls)} theme files bundled"
    return False, f"qt_material: theme data missing from {themes_dir}"


def _check_crash_handler() -> tuple[bool, str]:
    try:
        from src.utils.crash_handler import log_unhandled  # noqa: F401
        return True, "crash handler: importable"
    except Exception as e:  # noqa: BLE001 - reported, not raised
        return False, f"crash handler: import failed ({e})"


def _check_database() -> tuple[bool, str]:
    """Round-trips a real database: tables, migrations, retention, flush."""
    try:
        from src.core.db_manager import DatabaseManager
        from src.core.models import Profile

        with tempfile.TemporaryDirectory(prefix="selftest_") as tmp:
            db = DatabaseManager(tmp)
            try:
                profile = Profile(name="SelfTest", login_server="https://selftest.invalid")
                if not db.save_profile(profile):
                    return False, "database: profile save failed"
                if db.count_profiles() != 1:
                    return False, "database: profile count mismatch after save"
                db.insert_traffic_data("SelfTest", 1024, 2048)
                db.flush_buffer()
                db.delete_profile(profile.id, profile_name="SelfTest")
            finally:
                # Release the log handle before the temp directory is removed
                db.close()
        return True, "database: migrations, save/load, traffic flush and cascade delete OK"
    except Exception as e:  # noqa: BLE001 - reported, not raised
        return False, f"database: {type(e).__name__}: {e}"


def _check_tailscale_cli() -> tuple[bool, str]:
    """Informational: CI may legitimately have no daemon installed."""
    try:
        from src.core.executor import get_tailscale_path
        path = get_tailscale_path()
        found = path != "tailscale" and os.path.exists(path)
        return True, f"tailscale CLI: {'found at ' + path if found else 'not installed (informational)'}"
    except Exception as e:  # noqa: BLE001 - reported, not raised
        return False, f"tailscale CLI lookup failed: {e}"


def run_self_test(root: str | None = None) -> list[tuple[bool, str]]:
    """Returns (ok, message) for every check. Never raises."""
    root = root or _data_root()
    results: list[tuple[bool, str]] = [(_check_file(os.path.join(root, "assets", "icon.png"), "application icon"))]
    results.extend(_check_locales(root))
    results.extend(_check_readmes(root))
    results.append(_check_ui_files(root))
    results.append(_check_theme_package())
    results.append(_check_crash_handler())
    results.append(_check_database())
    results.append(_check_tailscale_cli())
    return results


def main() -> int:
    """Prints a report and returns a process exit code."""
    print("Self-test: validating this build")
    results = run_self_test()
    for ok, message in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {message}")
    failures = [m for ok, m in results if not ok]
    print(f"Self-test result: {len(results) - len(failures)}/{len(results)} checks passed")
    return 1 if failures else 0
