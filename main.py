# main.py
# This is the main entry point for the application.

import multiprocessing
import os
import sys

from PySide6.QtWidgets import QApplication

from src.core.manager import Manager
from src.core.tailscale import TailscaleManager
from src.ui.main_window import MainWindow
from src.utils.crash_handler import install as install_crash_handlers
from src.utils.dns_fallback import run_cli_if_requested
from src.utils.logger import manage_sys_streams, setup_logger

#: Named mutex the installer detects through AppMutex (see TailscaleClient_Installer.iss)
SINGLE_INSTANCE_MUTEX = "Arean82.TailscaleClientPro"

_mutex_handle = None


def acquire_installer_mutex():
    """Creates the named mutex Inno Setup's AppMutex looks for.

    Windows-only and best-effort: single-instance enforcement itself is handled
    by the QLockFile below; this exists so the installer can refuse to replace
    files while the application is running.
    """
    global _mutex_handle  # noqa: PLW0603 - the handle must outlive the call or Windows releases it
    if sys.platform != "win32":
        return
    try:
        import ctypes
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    except (AttributeError, OSError) as e:
        logger.debug(f"Could not create the installer-detection mutex: {e}")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Elevated hosts-file helper: dns_fallback relaunches this executable with
    # --dns-fallback args when UAC is needed; handle it and exit before the GUI
    # or the single-instance lock are touched.
    fallback_exit_code = run_cli_if_requested()
    if fallback_exit_code is not None:
        sys.exit(fallback_exit_code)

    # Packaging smoke test: validates bundled data and a real DB round-trip
    # without opening the GUI (used by CI against the frozen executable).
    if "--self-test" in sys.argv:
        from src.utils.self_check import main as run_self_test

        sys.exit(run_self_test())

    # 1. Setup App Data & Logger
    if sys.platform == "win32":
        app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
    else:
        app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
    
    os.makedirs(app_dir, exist_ok=True)
    log_file = os.path.join(app_dir, "app.log")
    logger = setup_logger("TailscaleClient", log_file)

    # Failures must reach app.log: windowed builds have no console, so an
    # unhandled exception would otherwise be written nowhere.
    install_crash_handlers()
    acquire_installer_mutex()

    logger.info("Application starting up (PySide6 Edition)...")

    # Copy icon to persistent APPDATA directory for 100% reliable loading (especially on Windows Startup)
    import shutil
    try:
        def get_asset_path_early(relative_path):
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, relative_path)
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
        
        bundled_icon = get_asset_path_early("assets/icon.png")
        persistent_icon = os.path.join(app_dir, "icon.png")
        if os.path.exists(bundled_icon) and (
            not os.path.exists(persistent_icon) or os.path.getsize(bundled_icon) != os.path.getsize(persistent_icon)
        ):
            shutil.copy2(bundled_icon, persistent_icon)
    except OSError as e:
        logger.error(f"Failed to copy icon to persistent APPDATA: {e}")

    # 2. Initialize App & Check Lock
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        app.setStyle("WindowsVista") 
        try:
            import ctypes
            myappid = 'arean82.tailscale.headscale.client.pro'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except (AttributeError, OSError):
            # Shell32 or AppUserModelID not available on non-Windows/wine
            pass
            
    # Dynamically set app name to match the running .exe name (specified in your .spec file)
    exe_name = os.path.splitext(os.path.basename(sys.executable))[0]
    if exe_name.lower() in ["python", "pythonw", "main"]:  # Running from source code
        app.setApplicationName("Tailscale Client Pro")
    else:  # Running from the compiled .exe
        app.setApplicationName(exe_name)
    
    
    from PySide6.QtGui import QIcon
    def get_asset_path(relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
        
    app.setWindowIcon(QIcon(get_asset_path("assets/icon.png")))

    from PySide6.QtCore import QLockFile
    from PySide6.QtWidgets import QMessageBox
    
    # 3. Initialize Manager to load settings and translation (so early popups are translated)
    manager = Manager(app_dir)
    
    # Load language translation if not English
    if manager.settings.language != "en_US":
        from PySide6.QtCore import QTranslator
        translator = QTranslator(app)
        qm_path = get_asset_path(f"locales/{manager.settings.language}.qm")
        if os.path.exists(qm_path):
            if translator.load(qm_path):
                app.installTranslator(translator)
                logger.info(f"Loaded translation file: {qm_path}")
            else:
                logger.warning(f"Failed to load translation file: {qm_path}")
        else:
            logger.warning(f"Translation file not found: {qm_path}")

    from PySide6.QtCore import QCoreApplication
    lock_path = os.path.join(app_dir, "app.lock")
    lock_file = QLockFile(lock_path)
    
    if not lock_file.tryLock(2000):
        QMessageBox.warning(None, 
                          QCoreApplication.translate("main", "Already Running"), 
                          QCoreApplication.translate("main", "An instance of Tailscale Client Pro is already running.\n"
                                                             "Please check your task manager or system tray."))
        sys.exit(0)

    # 4. Initialize TailscaleManager

    ts_manager_raw = TailscaleManager(app_dir)
    ts_manager_raw.use_local_api = manager.settings.use_local_api
    ts_manager_raw.sso_timeout = manager.settings.sso_timeout
    ts_manager_raw.insecure_ssl = manager.settings.insecure_ssl
    
    from src.core.state_coordinator import StateCoordinator
    ts_manager = StateCoordinator(manager, ts_manager_raw)
    
    # Initialize system stream redirection if enabled
    manage_sys_streams(manager.settings.enable_logs, logger)
    
    window = MainWindow(manager, ts_manager)
    window.show()
    
    exit_code = app.exec()
    lock_file.unlock()
    sys.exit(exit_code)