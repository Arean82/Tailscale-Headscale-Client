# sso.py
# This module handles the Tailscale SSO login process, including running the command,
# opening the browser for authentication, and waiting for the connection to be established.

import subprocess
import threading
import webbrowser
import re
from logic.statuscheck import wait_until_connected

def run_sso_login(cmd, expected_url_part, output_callback=None, error_callback=None, success_callback=None, cancel_event=None):
    """
    Runs the interactive Tailscale SSO command, streams output line-by-line,
    opens the browser for login, waits for connection, and optionally calls success_callback.
    Supports a cancel_event to abort the process.
    """
    def runner():
        process = None
        try:
            browser_opened = False
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Stream output
            while True:
                if cancel_event and cancel_event.is_set():
                    process.terminate()
                    return

                line = process.stdout.readline()
                if not line:
                    break
                
                if output_callback:
                    output_callback(line)
                
                # Robust URL detection using Regex
                if not browser_opened and "https://" in line:
                    match = re.search(r'https://\S+', line)
                    if match:
                        url = match.group(0)
                        if expected_url_part in url:
                            try:
                                webbrowser.open(url)
                                browser_opened = True
                            except Exception as e:
                                if error_callback:
                                    error_callback(f"Failed to open browser: {e}")
            
            process.wait()

            if cancel_event and cancel_event.is_set():
                return

            if output_callback:
                output_callback("[DEBUG] Waiting for Tailscale to connect...")
            
            # Polling with cancel check
            from logic.statuscheck import is_logged_out
            import time
            
            timeout = 180
            interval = 5
            for _ in range(timeout // interval):
                if cancel_event and cancel_event.is_set():
                    return
                if not is_logged_out():
                    if output_callback:
                        output_callback("[INFO] Tailscale connected successfully.")
                    if success_callback:
                        success_callback()
                    return
                time.sleep(interval)
                
            if error_callback:
                error_callback("[ERROR] Timed out waiting for Tailscale to connect.")
                
        except Exception as e:
            msg = f"SSO login error: {e}"
            if error_callback:
                error_callback(msg)
            elif output_callback:
                output_callback(msg)
        finally:
            if process and process.poll() is None:
                process.terminate()

    threading.Thread(target=runner, daemon=True).start()
