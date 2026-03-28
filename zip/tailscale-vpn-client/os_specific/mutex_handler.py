# os_specific/mutex_handler.py
# Cross-platform file-based mutex to ensure only one app instance runs at a time.
# Fixed: write_log now imported from pylogic.ui_helpers (no longer from gui.utils).

import sys
import os
import errno

# write_log lives in pylogic.ui_helpers in the new structure.
# Fall back to a print if that import hasn't been set up yet (e.g. very early startup).
try:
    from pylogic.ui_helpers import write_log
except ImportError:
    def write_log(msg, level="INFO"):
        print(f"[{level}] {msg}")

if sys.platform == "win32":
    import msvcrt
elif sys.platform.startswith("linux") or sys.platform == "darwin":
    import fcntl

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_lock_file_handle = None
_lock_file_path   = None


def set_lock_file_path(path: str) -> None:
    global _lock_file_path
    _lock_file_path = path


def acquire_mutex():
    """
    Acquires a file-based lock.
    Returns True  — lock acquired (this is the only instance)
            False — lock held by another instance
            None  — error acquiring lock
    """
    global _lock_file_handle

    if not _lock_file_path:
        write_log("Mutex error: lock file path not set.", level="ERROR")
        return None

    try:
        os.makedirs(os.path.dirname(_lock_file_path), exist_ok=True)
        _lock_file_handle = open(_lock_file_path, "w")

        if sys.platform == "win32":
            try:
                msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                write_log("Windows file lock acquired.", level="INFO")
                return True
            except OSError as e:
                if e.errno in (errno.EACCES, errno.EDEADLK):
                    write_log("Windows file lock: another instance detected.", level="INFO")
                    return False
                write_log(f"Windows file lock error: {e}", level="ERROR")
                return None
        else:
            try:
                fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                write_log("Unix file lock acquired.", level="INFO")
                return True
            except BlockingIOError:
                write_log("Unix file lock: another instance detected.", level="INFO")
                return False
            except Exception as e:
                write_log(f"Unix file lock error: {e}", level="ERROR")
                return None

    except Exception as e:
        write_log(f"Could not create/open lock file: {e}", level="ERROR")
        return None


def release_mutex(_=None) -> None:
    """Releases the file-based lock and removes the lock file."""
    global _lock_file_handle, _lock_file_path

    if _lock_file_handle:
        try:
            if sys.platform == "win32":
                msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(_lock_file_handle, fcntl.LOCK_UN)

            _lock_file_handle.close()
            if _lock_file_path and os.path.exists(_lock_file_path):
                os.remove(_lock_file_path)
            write_log("Lock released and file deleted.", level="INFO")

        except Exception as e:
            write_log(f"Error releasing lock: {e}", level="ERROR")

        _lock_file_handle = None
