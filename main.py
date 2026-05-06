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

    # 3. Windows Service Check with UI
    if platform.system() == "Windows":
        SERVICE_NAME = "Tailscale"
        
        if not is_service_running(SERVICE_NAME, logger):
            # Attempt to start the service first
            import subprocess
            try:
                subprocess.Popen(
                    ["powershell", "-Command", "Start-Service Tailscale"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                logger.error(f"Failed to attempt starting service: {e}")
                
            wait_dialog = QDialog()
            wait_dialog.setWindowTitle("Starting Service")
            wait_dialog.setStyleSheet("QDialog { background-color: #1a1e2e; color: white; } QLabel { color: white; font-weight: bold; }")
            wait_dialog.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
            wait_dialog.setFixedSize(320, 120)
            
            layout = QVBoxLayout(wait_dialog)
            label = QLabel("Waiting for Tailscale Service...")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            
            progress = QProgressBar()
            progress.setRange(0, 0)
            progress.setTextVisible(False)
            layout.addWidget(progress)
            
            wait_dialog.show()
            
            timeout = 60
            start_time = time.time()
            
            loop = QEventLoop()
            timer = QTimer()
            
            def check_service():
                if is_service_running(SERVICE_NAME, logger) or time.time() - start_time > timeout:
                    if time.time() - start_time > timeout:
                        logger.warning("Tailscale did not start within 60s. Launching GUI anyway.")
                    timer.stop()
                    loop.quit()
                    
            timer.timeout.connect(check_service)
            timer.start(500)
            loop.exec()
            
            wait_dialog.close()

    manager = Manager(app_dir)
    ts_manager = TailscaleManager(app_dir)
    
    # Initialize system stream redirection if enabled
    manage_sys_streams(manager.settings.enable_logs, logger)
    
    window = MainWindow(manager, ts_manager)
    window.show()
    
    exit_code = app.exec()
    lock_file.unlock()
    sys.exit(exit_code)