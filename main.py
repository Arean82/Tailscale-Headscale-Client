# main.py
# This is the main entry point for the application.

import platform
import time
import psutil
import sys
import os
import multiprocessing

from PySide6.QtWidgets import QApplication
from src.core.manager import Manager
from src.core.tailscale import TailscaleManager, get_tailscale_path
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger, manage_sys_streams

def is_daemon_running(logger):
    try:
        import subprocess
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            [get_tailscale_path(), "status", "--json"], 
            capture_output=True, 
            text=True, 
            startupinfo=startupinfo,
            creationflags=creationflags
        )
        if result.returncode == 0:
            return True
        if "failed to connect" in result.stderr.lower() or "tailscaled may not be running" in result.stderr.lower():
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking tailscaled daemon: {e}")
        return False

def start_daemon_service(logger):
    import subprocess
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["powershell", "-Command", "Start-Service Tailscale"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["systemctl", "start", "tailscaled"])
        elif sys.platform == "darwin":
            subprocess.Popen(["launchctl", "start", "com.tailscale.tailscaled"])
    except Exception as e:
        logger.error(f"Failed to start daemon service: {e}")

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # 1. Setup App Data & Logger
    if sys.platform == "win32":
        app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
    else:
        app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client")
    
    os.makedirs(app_dir, exist_ok=True)
    log_file = os.path.join(app_dir, "app.log")
    logger = setup_logger("TailscaleClient", log_file)
    
    logger.info("Application starting up (PySide6 Edition)...")

    # 2. Initialize App & Check Lock
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        app.setStyle("WindowsVista") 
    app.setApplicationName("Tailscale Client Pro")

    from PySide6.QtCore import QLockFile, Qt, QTimer, QEventLoop
    from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressBar
    
    lock_path = os.path.join(app_dir, "app.lock")
    lock_file = QLockFile(lock_path)
    
    if not lock_file.tryLock(100):
        QMessageBox.warning(None, "Already Running", 
                          "An instance of Tailscale Client Pro is already running.\n"
                          "Please check your task manager or system tray.")
        sys.exit(0)

    # 3. Initialize Manager and MainWindow directly (instant launch)

    manager = Manager(app_dir)
    ts_manager_raw = TailscaleManager(app_dir)
    ts_manager_raw.use_local_api = manager.settings.use_local_api
    ts_manager_raw.sso_timeout = manager.settings.sso_timeout
    
    from src.core.state_coordinator import StateCoordinator
    ts_manager = StateCoordinator(manager, ts_manager_raw)
    
    # Initialize system stream redirection if enabled
    manage_sys_streams(manager.settings.enable_logs, logger)
    
    window = MainWindow(manager, ts_manager)
    window.show()
    
    exit_code = app.exec()
    lock_file.unlock()
    sys.exit(exit_code)