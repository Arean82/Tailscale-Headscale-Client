"""Global crash and Qt message handling.

In a windowed (``console=False``) build ``sys.stderr`` is ``None``, so an
unhandled exception - in the main thread, in a Qt slot, or on the executor's
worker thread - is written nowhere and the app simply misbehaves. Everything
here forwards such failures into the rotating application log.

Import side-effect free: Qt is imported lazily so this module (and its tests)
work without a GUI stack.
"""

import logging
import sys
import threading

logger = logging.getLogger("TailscaleClient.CrashHandler")


def _report(origin: str, exc_type, exc_value, exc_tb) -> None:
    logger.critical(
        f"Unhandled exception ({origin}): {exc_type.__name__}: {exc_value}",
        exc_info=(exc_type, exc_value, exc_tb),
    )


def log_unhandled(exc_type, exc_value, exc_tb) -> None:
    """Excepthook for the main thread (also used by tests)."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Ctrl+C must keep its normal behaviour
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    _report("main thread", exc_type, exc_value, exc_tb)


def log_unhandled_thread(args) -> None:
    """Excepthook for worker threads (the executor's blocking worker included)."""
    if args.exc_type is SystemExit:
        return
    _report(f"thread {getattr(args.thread, 'name', '?')}", args.exc_type, args.exc_value, args.exc_traceback)


def log_qt_message(msg_type, context, message) -> None:
    """Routes Qt's own diagnostics (qWarning, QProcess warnings, ...) into logging."""
    from PySide6.QtCore import QtMsgType

    level = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }.get(msg_type, logging.INFO)

    location = ""
    if context is not None and getattr(context, "file", None):
        location = f" ({context.file}:{context.line})"
    logger.log(level, f"[Qt]{location} {message}")


def install() -> None:
    """Installs the crash hooks and the Qt message handler.

    Safe to call before the QApplication exists (the Qt handler is installed
    only when Qt is importable) and idempotent per process.
    """
    sys.excepthook = log_unhandled
    threading.excepthook = log_unhandled_thread

    try:
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(log_qt_message)
        logger.debug("Qt message handler installed")
    except ImportError as e:  # pragma: no cover - Qt is a hard dependency in the app
        logger.debug(f"Qt message handler not installed: {e}")

    logger.debug("Crash handlers installed")
