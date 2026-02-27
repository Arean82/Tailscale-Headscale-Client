# logic/statuscheck.py

import subprocess
import time
import json
from logic.logger import app_logger

def is_logged_out():
    try:
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
        app_logger.debug(f"tailscale status output: {result.stdout.strip()}")
        return 'Logged out.' in result.stdout
    except subprocess.TimeoutExpired:
        app_logger.debug("tailscale status timed out")
        return True  
    except Exception as e:
        app_logger.error(f"Error checking Tailscale status: {e}")
        return True

def wait_until_connected(timeout=180, interval=10):
    for attempt in range(timeout // interval):
        app_logger.debug(f"Polling attempt {attempt + 1}...")
        if not is_logged_out():
            app_logger.info("Connected successfully!")
            return True
        time.sleep(interval)
    app_logger.warning("Timed out waiting for connection")
    return False

def check_connected():
    try:
        output = subprocess.check_output(["tailscale", "status", "--json"], text=True)
        data = json.loads(output)
        return any(peer.get("Online", False) for peer in data.get("Peer", {}).values())
    except Exception as e:
        app_logger.error(f"[StatusCheck] Error checking connection: {e}")
        return False