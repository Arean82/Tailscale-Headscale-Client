# main.py
# This script checks if the Tailscale service is running on Windows and launches a GUI application.

import platform
import time
import psutil

from gui_start import start_gui

if platform.system() == "Windows":
    SERVICE_NAME = "Tailscale"

    def is_service_running(name):
        try:
            service = psutil.win_service_get(name)
            return service.as_dict()['status'] == 'running'
        except Exception:
            return False

    timeout = 60
    start_time = time.time()

    while not is_service_running(SERVICE_NAME):
        if time.time() - start_time > timeout:
            print("Tailscale did not start within 60 seconds. Launching GUI anyway.")
            break
        print("Tailscale not running yet. Waiting 2 seconds...")
        time.sleep(2)

print("Launching GUI...")
start_gui()