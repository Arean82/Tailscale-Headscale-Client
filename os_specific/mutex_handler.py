# mutex_handler.py
# This module provides a cross-platform mutex handler to ensure only one instance of the application runs at

import sys
import os
import errno
from utils import write_log

if sys.platform == "win32":
    import msvcrt
elif sys.platform.startswith("linux") or sys.platform == "darwin":
    import fcntl

# Global lock handle
_lock_file_handle = None
_lock_file_path = None  # Settable by main app

def set_lock_file_path(path):
    global _lock_file_path
    _lock_file_path = path

def acquire_mutex():
    """
    Acquires a file-based lock. Works cross-platform (Windows & Linux/macOS).
    Returns True on success, False if lock is held, None on error.
    """
    global _lock_file_handle

    if not _lock_file_path:
        write_log("Mutex error: Lock file path not set.", level="ERROR")
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
                if e.errno == errno.EACCES or e.errno == errno.EDEADLK:
                    write_log("Windows file lock: Another instance detected.", level="INFO")
                    return False
                else:
                    write_log(f"Windows file lock error: {e}", level="ERROR")
                    return None

        else:  # Linux/macOS
            try:
                fcntl.flock(_lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                write_log("Unix file lock acquired.", level="INFO")
                return True
            except BlockingIOError:
                write_log("Unix file lock: Another instance detected.", level="INFO")
                return False
            except Exception as e:
                write_log(f"Unix file lock error: {e}", level="ERROR")
                return None

    except Exception as e:
        write_log(f"Could not create/open lock file: {e}", level="ERROR")
        return None

def release_mutex(_):
    """
    Releases the file-based lock.
    """
    global _lock_file_handle, _lock_file_path

    if _lock_file_handle:
        try:
            if sys.platform == "win32":
                msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(_lock_file_handle, fcntl.LOCK_UN)

            _lock_file_handle.close()
            if os.path.exists(_lock_file_path):
                os.remove(_lock_file_path)
            write_log("Lock released and file deleted.", level="INFO")

        except Exception as e:
            write_log(f"Error releasing lock: {e}", level="ERROR")

        _lock_file_handle = None
