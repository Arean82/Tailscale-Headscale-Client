import time
import psutil
import platform

from gui_main import start_gui

SERVICE_NAME = "Tailscale"
PROCESS_NAME = "tailscaled"  # Linux/macOS service name

def is_service_running():
    system = platform.system()

    if system == "Windows":
        try:
            service = psutil.win_service_get(SERVICE_NAME)
            return service.as_dict()['status'] == 'running'
        except Exception:
            return False

    else:
        # For Linux/macOS — check process name
        for proc in psutil.process_iter(attrs=['name']):
            if proc.info['name'] == PROCESS_NAME:
                return True
        return False

print("Checking if Tailscale is running...")

timeout = 60  # seconds
start_time = time.time()

while not is_service_running():
    if time.time() - start_time > timeout:
        print("Tailscale did not start within 60 seconds. Launching GUI anyway.")
        break
    print("Tailscale not running yet. Waiting 2 seconds...")
    time.sleep(2)

print("Launching GUI...")
start_gui()
