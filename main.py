# main.py
import platform
import time
import psutil
import sys
import os
import multiprocessing

from PySide6.QtWidgets import QApplication
from src.core.manager import Manager
from src.core.tailscale import TailscaleManager
from src.ui.main_window import MainWindow
from src.utils.logger import setup_logger, manage_sys_streams

def is_service_running(name, logger):
    try:
        service = psutil.win_service_get(name)
        return service.as_dict()["status"] == "running"
    except Exception as e:
        logger.error(f"Error checking service: {e}")
        return False

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # 1. Setup App Data & Logger
    if sys.platform == "win32":
        app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client_Pro")
    else:
        app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client_Pro")
    
    os.makedirs(app_dir, exist_ok=True)
    log_file = os.path.join(app_dir, "app.log")
    logger = setup_logger("TailscaleClient", log_file)
    
    logger.info("Application starting up (PySide6 Edition)...")

    # 2. Windows Service Check
    if platform.system() == "Windows":
        SERVICE_NAME = "Tailscale"
        timeout = 60
        start_time = time.time()

        while not is_service_running(SERVICE_NAME, logger):
            if time.time() - start_time > timeout:
                logger.warning("Tailscale did not start within 60s. Launching GUI anyway.")
                break
            time.sleep(2)

    # 3. Initialize Core & GUI
    app = QApplication(sys.argv)
    if sys.platform == "win32":
        app.setStyle("WindowsVista") # Ensure native menu bar
    app.setApplicationName("Tailscale Client Pro")

    manager = Manager(app_dir)
    ts_manager = TailscaleManager(app_dir)
    
    # Initialize system stream redirection if enabled
    manage_sys_streams(manager.settings.enable_logs, logger)
    
    window = MainWindow(manager, ts_manager)
    window.show()
    
    sys.exit(app.exec())