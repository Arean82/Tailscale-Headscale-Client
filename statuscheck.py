# statuscheck.py
# This module checks the Tailscale connection status and waits until connected.

import subprocess
import time
import json

def is_logged_out():
    try:
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
        print(f"[DEBUG] tailscale status output: {result.stdout.strip()}")
        return 'Logged out.' in result.stdout
    except subprocess.TimeoutExpired:
        print("[DEBUG] tailscale status timed out")
        return True  # Assume logged out on timeout
    except Exception as e:
        print(f"[DEBUG] Error checking Tailscale status: {e}")
        return True

def wait_until_connected(timeout=180, interval=10):
    for attempt in range(timeout // interval):
        print(f"[DEBUG] Polling attempt {attempt + 1}...")
        if not is_logged_out():
            print("[DEBUG] Connected successfully!")
            return True
        time.sleep(interval)
    print("[DEBUG] Timed out waiting for connection")
    return False

def check_connected():
    try:
        output = subprocess.check_output(["tailscale", "status", "--json"], text=True)
        data = json.loads(output)
        return any(peer.get("Online", False) for peer in data.get("Peer", {}).values())
    except Exception as e:
        print(f"[StatusCheck] Error checking connection: {e}")
        return False

