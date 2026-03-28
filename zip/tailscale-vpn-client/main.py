# main.py
import platform
import time
import psutil
import sys
import multiprocessing

from pylogic.windows.app_controller import start_gui
from logic.logger import app_logger

if __name__ == "__main__":
    # Required for multiprocessing in compiled EXE
    multiprocessing.freeze_support()

    app_logger.info("Application starting up...")

    if platform.system() == "Windows":
        SERVICE_NAME = "Tailscale"
        app_logger.debug(f"Checking for service: {SERVICE_NAME}")

        def is_service_running(name):
            try:
                service = psutil.win_service_get(name)
                return service.as_dict()["status"] == "running"
            except Exception as e:
                app_logger.error(f"Error checking service: {e}")
                return False

        timeout    = 60
        start_time = time.time()

        while not is_service_running(SERVICE_NAME):
            if time.time() - start_time > timeout:
                app_logger.warning(
                    "Tailscale did not start within 60 seconds. Launching GUI anyway."
                )
                break
            time.sleep(2)

    app_logger.info("Launching GUI...")
    start_gui()
