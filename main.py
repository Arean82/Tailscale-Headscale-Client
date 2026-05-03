# main.py
# This module contains the main application logic for the TAILSCALE VPN Client.

import platform
import time
import psutil
import sys # Added for freeze support

from gui.gui_start import start_gui
from logic.logger import app_logger
from logic.vpn_logic import initialize_app_storage

# Move this inside the block so child processes don't log it
if __name__ == '__main__':
    # Required for multiprocessing in compiled EXE
    import multiprocessing
    from concurrent.futures import ThreadPoolExecutor
    multiprocessing.freeze_support()

    app_logger.info("Application starting up...")

    def run_init_tasks():
        with ThreadPoolExecutor() as executor:
            # Task 1: Initialize storage
            executor.submit(initialize_app_storage)
            
            # Task 2: Windows specific service check (if on Windows)
            if platform.system() == "Windows":
                def wait_for_tailscale():
                    SERVICE_NAME = "Tailscale"
                    app_logger.debug(f"Checking for service: {SERVICE_NAME}")
                    
                    def is_service_running(name):
                        try:
                            service = psutil.win_service_get(name)
                            return service.as_dict()['status'] == 'running'
                        except Exception as e:
                            app_logger.error(f"Error checking service: {e}")
                            return False

                    timeout = 60
                    start_time = time.time()
                    while not is_service_running(SERVICE_NAME):
                        if time.time() - start_time > timeout:
                            app_logger.warning("Tailscale did not start within 60 seconds.")
                            break
                        time.sleep(1)
                
                executor.submit(wait_for_tailscale)

    # Run initialization tasks in background so GUI can start immediately
    import threading
    threading.Thread(target=run_init_tasks, daemon=True).start()

    app_logger.info("Launching GUI...")
    start_gui()