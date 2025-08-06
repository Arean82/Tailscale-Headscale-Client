# sso.py
# This module handles the Tailscale SSO login process, including running the command,
# opening the browser for authentication, and waiting for the connection to be established.

import subprocess
import threading
import webbrowser
from statuscheck import wait_until_connected  # import the polling function

def run_sso_login(cmd, expected_url_part, output_callback=None, error_callback=None):
    """
    Runs the interactive Tailscale SSO command, streams output line-by-line,
    opens the browser when the login URL is emitted, and waits until connection is established.
    """
    def runner():
        try:
            browser_opened = False
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                if output_callback:
                    output_callback(line)
                stripped = line.strip()
                # Open browser once when the SSO URL appears (contains expected_url_part)
                if not browser_opened and stripped.startswith("https://") and expected_url_part in stripped:
                    try:
                        webbrowser.open(stripped)
                        browser_opened = True
                    except Exception as e:
                        if error_callback:
                            error_callback(f"Failed to open browser: {e}")
            process.wait()

            # ✅ Poll for connection after browser login
            if output_callback:
                output_callback("[DEBUG] Waiting for Tailscale to connect...")
            connected = wait_until_connected()
            if connected:
                if output_callback:
                    output_callback("[INFO] Tailscale connected successfully.")
            else:
                if error_callback:
                    error_callback("[ERROR] Timed out waiting for Tailscale to connect.")
        except Exception as e:
            if error_callback:
                error_callback(f"SSO login error: {e}")
            elif output_callback:
                output_callback(f"SSO login error: {e}")

    threading.Thread(target=runner, daemon=True).start()
