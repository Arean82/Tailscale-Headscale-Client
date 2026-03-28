# pylogic/sso.py
# Handles the Tailscale SSO login process: runs the command, opens the browser,
# and waits for the connection to be established.
# No UI dependency — pure threading + subprocess helper.
# Identical logic to the original gui/sso.py.

import subprocess
import threading
import webbrowser

from logic.statuscheck import wait_until_connected


def run_sso_login(
    cmd,
    expected_url_part,
    output_callback=None,
    error_callback=None,
    success_callback=None,
):
    """
    Runs the interactive Tailscale SSO command, streams output line-by-line,
    opens the browser for login, waits for connection, and calls success_callback
    when connected.

    All callbacks are invoked from the worker thread — callers that update
    Qt widgets must route these through Qt signals.
    """

    def runner():
        try:
            browser_opened = False
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                if output_callback:
                    output_callback(line)
                stripped = line.strip()
                if (
                    not browser_opened
                    and stripped.startswith("https://")
                    and expected_url_part in stripped
                ):
                    try:
                        webbrowser.open(stripped)
                        browser_opened = True
                    except Exception as e:
                        if error_callback:
                            error_callback(f"Failed to open browser: {e}")

            process.wait()

            if output_callback:
                output_callback("[DEBUG] Waiting for Tailscale to connect...")

            connected = wait_until_connected()
            if connected:
                if output_callback:
                    output_callback("[INFO] Tailscale connected successfully.")
                if success_callback:
                    success_callback()
            else:
                if error_callback:
                    error_callback("[ERROR] Timed out waiting for Tailscale to connect.")

        except Exception as e:
            msg = f"SSO login error: {e}"
            if error_callback:
                error_callback(msg)
            elif output_callback:
                output_callback(msg)

    threading.Thread(target=runner, daemon=True).start()
