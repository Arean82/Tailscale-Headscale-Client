# gui/tailscaleclient.py
# This module defines the TailscaleClient class, which manages interactions with the Tailscale command-line tool. It provides methods to connect and disconnect from a VPN server, check connection status, and log traffic stats. The class uses callbacks to communicate with the GUI for status updates and output display. It also integrates with a global logger to log important events and errors throughout the connection process. The code handles both SSO and key-based authentication modes and includes error handling for command execution. 

import os
import sys
import subprocess
import threading
import time
import re
import webbrowser
from logic.statuscheck import wait_until_connected

from logic.vpn_logic import save_key, save_url, write_profile_log, write_log
from logic.net_stats import log_tailscale_stats 

# IMPORT OUR GLOBAL LOGGER
from logic.logger import app_logger

class TailscaleClient:
    def __init__(
        self,
        output_callback=None,
        status_callback=None,
        connected_callback=None,
        logged_out_callback=None,
        post_disconnect_callback=None,
        post_logout_callback=None,
        progress_callback=None,
        message_popup_callback=None
    ):
        self.output_callback = output_callback
        self.status_callback = status_callback
        self.connected_callback = connected_callback
        self.logged_out_callback = logged_out_callback
        self.post_disconnect_callback = post_disconnect_callback
        self.post_logout_callback = post_logout_callback
        self.progress_callback = progress_callback
        self.message_popup_callback = message_popup_callback

        self.connected = False
        self.logged_in = False
        self._periodic_logger_thread = None
        self._periodic_logger_running = threading.Event()

    def _print_output(self, text):
        if self.output_callback:
            self.output_callback(text)

    def _update_status(self, text, color):
        if self.status_callback:
            self.status_callback(text, color)

    def _notify_connected(self):
        if self.connected_callback:
            self.connected_callback()

    def _notify_logged_out(self):
        if self.logged_out_callback:
            self.logged_out_callback()

    def _notify_post_disconnect(self):
        if self.post_disconnect_callback:
            self.post_disconnect_callback()

    def _notify_post_logout(self):
        if self.post_logout_callback:
            self.post_logout_callback()

    def _show_progress(self, message, step):
        if self.progress_callback:
            self.progress_callback(message, step)

    # ---> CRITICAL FIX HERE <---
    def run_command(self, cmd, require_sudo=False):
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if require_sudo and sys.platform.startswith("linux"):
            self._print_output("Elevated command: using pkexec.")
            cmd = ["pkexec"] + cmd

        # Log the command execution
        app_logger.debug(f"Running terminal command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            output = result.stdout + result.stderr
            
            # Log the raw response from the OS
            app_logger.debug(f"Terminal Response:\n{output.strip()}")
            return output
            
        except FileNotFoundError:
            app_logger.error("Tailscale command not found.")
            return "Error: Tailscale command not found. Ensure Tailscale is installed and in your PATH."
        except Exception as e:
            app_logger.error(f"Error running command '{' '.join(cmd)}': {e}")
            write_log(f"Error running command '{' '.join(cmd)}': {e}", level="ERROR")
            return f"Error running command: {e}"

    def _periodic_traffic_logger(self, profile):
        app_logger.debug(f"Starting periodic traffic logger for profile: {profile}")
        while self._periodic_logger_running.is_set():
            if not self.connected:
                app_logger.debug(f"Periodic traffic logger stopped for {profile}: disconnected.")
                break
            log_tailscale_stats(profile)
            self._periodic_logger_running.wait(30)

    def _stop_periodic_logger(self):
        if self._periodic_logger_thread and self._periodic_logger_thread.is_alive():
            self._periodic_logger_running.clear()
            self._periodic_logger_thread.join(timeout=5)
        self._periodic_logger_thread = None
        self._periodic_logger_running.clear()

    def is_connected(self):
        try:
            output = self.run_command(["tailscale", "status"])
            if "logged out" in output.lower() or "disconnected" in output.lower():
                return False
            return "logged in" in output.lower() or "connected" in output.lower()
        except Exception as e:
            app_logger.error(f"Error checking connection status: {e}")
            return False

    def connect(self, key, server, tab_name):
        def task(auth_key, login_server, profile_name):
            auth_key = auth_key.strip()
            login_server = login_server.strip()
            save_key(auth_key, profile_name)
            save_url(login_server, profile_name)
            
            self._show_progress("Preparing Tailscale...", 1)
            self.connected = False
            self.logged_in = False
            
            # 1. Ensure Tailscale Service is running
            if sys.platform == "win32":
                self.run_command(["powershell", "-Command", "Start-Service Tailscale"], require_sudo=True)
            elif sys.platform.startswith("linux"):
                self.run_command(["systemctl", "start", "tailscaled"], require_sudo=True)
            time.sleep(1)

            # 2. Determine auth mode
            from logic.vpn_logic import get_file_path
            mode_file = get_file_path("auth_mode", profile_name)
            auth_mode = "auth_key"
            if os.path.exists(mode_file):
                with open(mode_file, "r") as f:
                    auth_mode = f.read().strip()

            cmd = ["tailscale", "up", f"--login-server={login_server}", "--accept-routes"]
            if auth_mode == "auth_key":
                if not auth_key:
                    self._update_status("🔴 Missing Auth Key", "red")
                    return
                cmd.append(f"--auth-key={auth_key}")
            
            self._show_progress("Connecting...", 2)
            safe_cmd = [p if not p.startswith("--auth-key=") else "--auth-key=****" for p in cmd]
            app_logger.info(f"[{profile_name}] Executing: {' '.join(safe_cmd)}")

            # 3. Start Background Polling Thread (Track #1)
            # This is our safety net if we miss the "Success." message in the stream
            stop_polling = threading.Event()
            def polling_watchdog():
                app_logger.debug(f"[{profile_name}] Watchdog started.")
                timeout = 180
                start_time = time.time()
                while not stop_polling.is_set() and (time.time() - start_time < timeout):
                    if self.is_connected():
                        app_logger.info(f"[{profile_name}] Watchdog detected connection!")
                        self._trigger_connected_ui(profile_name)
                        break
                    time.sleep(3)
                app_logger.debug(f"[{profile_name}] Watchdog stopped.")

            threading.Thread(target=polling_watchdog, daemon=True).start()

            # 4. Start Tailscale Process and Stream Output (Track #2)
            try:
                process = subprocess.Popen(
                    ["pkexec"] + cmd if sys.platform.startswith("linux") else cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1 # Line buffered
                )

                url_opened = False
                for line in process.stdout:
                    line = line.strip()
                    if not line: continue
                    
                    self._print_output(line)
                    write_profile_log(profile_name, line)

                    # Capture "Success." immediately
                    if "success." in line.lower() or "connected" in line.lower():
                        app_logger.info(f"[{profile_name}] Stream captured success message.")
                        self._trigger_connected_ui(profile_name)

                    # Capture and open SSO URL
                    if not url_opened and "https://" in line:
                        match = re.search(r'https://\S+', line)
                        if match:
                            login_url = match.group(0)
                            self._print_output(f"🔐 Please authenticate: {login_url}")
                            url_opened = True
                            if self.message_popup_callback:
                                self.message_popup_callback("SSO Login", f"Authenticate in browser:\n\n{login_url}")
                            webbrowser.open(login_url)

                process.wait()
                
            except Exception as e:
                app_logger.error(f"[{profile_name}] Process error: {e}")
            finally:
                stop_polling.set()

            # 5. Final Verification
            time.sleep(1)
            if not self.connected:
                if self.is_connected():
                    self._trigger_connected_ui(profile_name)
                else:
                    self._update_status("🔴 Connection Failed", "red")
                    self._notify_logged_out()
                    self._show_progress("Failed.", 0)

        threading.Thread(target=task, args=(key, server, tab_name), daemon=True).start()

    def _trigger_connected_ui(self, profile_name):
        """Helper to unify UI updates upon successful connection."""
        if self.connected: return
        self.connected = True
        self.logged_in = True
        self._update_status("🟢 Connected", "green")
        self._notify_connected()
        self._show_progress("Connected!", 0)
        
        # Start periodic traffic logging
        self._stop_periodic_logger()
        self._periodic_logger_running.set()
        self._periodic_logger_thread = threading.Thread(
            target=self._periodic_traffic_logger, args=(profile_name,), daemon=True
        )
        self._periodic_logger_thread.start()

    def disconnect(self, profile_name):
        def task():
            self._print_output("Disconnecting from Tailscale...")  
            output = self.run_command(["tailscale", "logout"])
            self.connected = False
            self.logged_in = False
            self._update_status("🔴 Disconnected", "red")
            self._notify_logged_out()
            self._notify_post_disconnect()
            self._notify_post_logout()
            self._stop_periodic_logger()
            self._show_progress("Disconnected.", 0)
    
        threading.Thread(target=task, daemon=True).start()