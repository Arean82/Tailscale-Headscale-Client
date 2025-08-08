# main.py
# This script serves as the entry point for the GUI application.

import time
import psutil  # pip install psutil

from gui_main import start_gui

SERVICE_NAME = "Tailscale"

def is_service_running(name):
    try:
        service = psutil.win_service_get(name)
        return service.as_dict()['status'] == 'running'
    except Exception:
        return False

print("Checking if Tailscale service is running...")

# Wait for Tailscale to be running, with a timeout
timeout = 60  # seconds
start_time = time.time()

while not is_service_running(SERVICE_NAME):
    if time.time() - start_time > timeout:
        print("Tailscale service did not start within 60 seconds. Launching GUI anyway.")
        break
    print("Tailscale not running yet. Waiting 2 seconds...")
    time.sleep(2)

print("Launching GUI...")
start_gui()
