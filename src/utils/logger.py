import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# This will be set during initialization in main.py
APP_DIR = None

# Single source for the on-disk line layout, shared by the rotating file handler
# and the live log stream so both render identically.
LOG_LINE_FORMAT = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'


class SignalLogHandler(logging.Handler):
    """Forwards formatted records to a sink callback (e.g. a Qt signal emitter).

    Used by the Log Viewer for live tailing; kept Qt-free so it can be unit
    tested. A failing sink must never break logging, so emit() defers to
    handleError() instead of raising.
    """

    def __init__(self, sink, level=logging.DEBUG):
        super().__init__(level)
        self._sink = sink
        self.setFormatter(logging.Formatter(LOG_LINE_FORMAT))

    def emit(self, record):
        try:
            self._sink(self.format(record))
        except Exception:  # noqa: BLE001 - logging must never propagate to the caller
            self.handleError(record)


class ScrubbingFormatter(logging.Formatter):
    def format(self, record):
        orig_msg = record.msg
        if isinstance(record.msg, str):
            record.msg = scrub_credentials(record.msg)
        try:
            val = super().format(record)
        finally:
            record.msg = orig_msg
        return val

def setup_logger(name, log_file, level=logging.DEBUG):
    """Setup a standard logger with rotating file and console output."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    formatter = ScrubbingFormatter(LOG_LINE_FORMAT)
    
    # Standard handler
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(handler)

    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# --- Advanced Features from legacy logic/logger.py ---

import re


def scrub_credentials(text):
    if not text or not isinstance(text, str):
        return text
    # Mask Tailscale key variants (tskey-auth-..., tskey-api-..., tskey-client-...)
    text = re.sub(r'tskey-[A-Za-z]+-\S+', 'tskey-[REDACTED]', text)
    # Mask Headscale machine/node key material that can appear in CLI output
    text = re.sub(r'\b(?:mkey|nodekey):[A-Za-z0-9+/=_-]+', '[REDACTED-KEY]', text)
    # Mask any potential API keys/passwords in connection arguments
    text = re.sub(r'--authkey=\S+', '--authkey=[REDACTED]', text)
    text = re.sub(r'--auth-key=\S+', '--auth-key=[REDACTED]', text)
    return text

class StreamToLogger:
    """Redirects stdout/stderr to the logging module with integrated credential scrubbing."""
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        scrubbed = scrub_credentials(buf)
        for line in scrubbed.rstrip().splitlines():
            if line.strip():
                self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

class NullWriter:
    """No-op sink used when no console exists.

    In windowed (console=False) PyInstaller builds, sys.__stdout__/sys.__stderr__
    are None; restoring them directly makes every print() raise AttributeError
    inside Qt slots, silently aborting the rest of the slot.
    """

    def write(self, buf):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False


def _console_stream(real_stream):
    return real_stream if real_stream is not None else NullWriter()


def manage_sys_streams(enabled, logger=None):
    """Overrides or restores standard print outputs."""
    if enabled and logger:
        sys.stdout = StreamToLogger(logger, logging.DEBUG)
        sys.stderr = StreamToLogger(logger, logging.ERROR)
    else:
        sys.stdout = _console_stream(sys.__stdout__)
        sys.stderr = _console_stream(sys.__stderr__)

# One rotating, scrubbing logger per profile: the connection log must not grow
# without bound, and it must not persist credentials in clear text (the CLI can
# echo key material in its output).
_profile_loggers: dict[str, logging.Logger] = {}
PROFILE_LOG_MAX_BYTES = 10 * 1024 * 1024
PROFILE_LOG_BACKUPS = 3


def get_global_log_dir(base_dir):
    """Directory holding the per-profile connection logs."""
    path = os.path.join(base_dir, "GlobalLogs")
    os.makedirs(path, exist_ok=True)
    return path


def _app_data_dir():
    if sys.platform == "win32":
        return os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")


def get_profile_logger(profile_name, base_dir=None):
    """Returns the rotating, scrubbing logger that owns a profile's connection log."""
    safe_name = "".join(c for c in profile_name if c.isalnum() or c in (' ', '.', '_', '-')).strip().replace(' ', '_')
    if safe_name in _profile_loggers:
        return _profile_loggers[safe_name]

    logger = logging.getLogger(f"TailscaleClient.Profile.{safe_name}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # profile output stays out of app.log

    if not logger.handlers:
        log_dir = get_global_log_dir(base_dir or _app_data_dir())
        handler = RotatingFileHandler(
            os.path.join(log_dir, f"{safe_name}_connection.log"),
            maxBytes=PROFILE_LOG_MAX_BYTES, backupCount=PROFILE_LOG_BACKUPS,
        )
        handler.setFormatter(ScrubbingFormatter(LOG_LINE_FORMAT))
        logger.addHandler(handler)

    _profile_loggers[safe_name] = logger
    return logger


def write_profile_log(profile_name, data, base_dir=None):
    """Writes connection output to the profile's log (rotated and redacted)."""
    if not profile_name or not data:
        return
    try:
        get_profile_logger(profile_name, base_dir).info(data.rstrip())
    except OSError:
        # Logging failure should not disrupt main process execution
        return

# Global instance for easy access
app_logger = None

def refresh_all_loggers(base_dir, enabled):
    """Refreshes the main loggers and system streams."""
    log_file = os.path.join(base_dir, "app.log")
    logger = setup_logger("TailscaleClient", log_file)
    manage_sys_streams(enabled, logger)
    return logger

# Global instance for easy access
app_logger = None
