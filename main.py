# main.py
import platform
import time
import psutil

from gui.gui_start import start_gui
from logic.logger import app_logger  # <--- Import the logger

app_logger.info("Application starting up...") # <--- Log an event

if platform.system() == "Windows":
    SERVICE_NAME = "Tailscale"
    app_logger.debug(f"Checking for service: {SERVICE_NAME}") # <--- Log an event

    def is_service_running(name):
        try:
            service = psutil.win_service_get(name)
            return service.as_dict()['status'] == 'running'
        except Exception as e:
            app_logger.error(f"Error checking service: {e}") # <--- Log an error
            return False

    timeout = 60
    start_time = time.time()

    while not is_service_running(SERVICE_NAME):
        if time.time() - start_time > timeout:
            app_logger.warning("Tailscale did not start within 60 seconds. Launching GUI anyway.")
            print("Tailscale did not start within 60 seconds. Launching GUI anyway.")
            break
        print("Tailscale not running yet. Waiting 2 seconds...")
        time.sleep(2)

app_logger.info("Launching GUI...")
print("Launching GUI...")
start_gui()