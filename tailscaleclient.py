# tailscaleclient.py
# This module defines the TailscaleClient class, which manages Tailscale VPN connections,

import cmd
import os
import sys
import subprocess
import threading
import time
from tkinter import messagebox

# Import necessary functions from vpn_logic.py
from vpn_logic import save_key, save_url, write_profile_log, write_log
from net_stats import log_tailscale_stats # Assuming net_stats.py is available

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

    def run_command(self, cmd, require_sudo=False):
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if require_sudo and sys.platform.startswith("linux"):
            self._print_output("Elevated command: using pkexec.")
            cmd = ["pkexec"] + cmd
        elif require_sudo and sys.platform == "win32":
            self._print_output("Windows commands requiring elevation usually prompt or need an elevated terminal.")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            return result.stdout + result.stderr
        except FileNotFoundError:
            return "Error: Tailscale command not found. Ensure Tailscale is installed and in your PATH."
        except Exception as e:
            write_log(f"Error running command '{' '.join(cmd)}': {e}", level="ERROR")
            return f"Error running command: {e}"

    def _periodic_traffic_logger(self, profile):
        write_log(f"Starting periodic traffic logger for profile: {profile}", level="DEBUG")
        while self._periodic_logger_running.is_set():
            if not self.connected:
                write_log(f"Periodic traffic logger stopped for {profile}: disconnected.", level="DEBUG")
                break
            log_tailscale_stats(profile)
            self._periodic_logger_running.wait(30)
        write_log(f"Periodic traffic logger exited for profile: {profile}", level="DEBUG")

    def _stop_periodic_logger(self):
        if self._periodic_logger_thread and self._periodic_logger_thread.is_alive():
            write_log("Attempting to stop periodic traffic logger...", level="DEBUG")
            self._periodic_logger_running.clear()
            self._periodic_logger_thread.join(timeout=5)
            if self._periodic_logger_thread.is_alive():
                write_log("Periodic traffic logger thread did not terminate gracefully.", level="WARNING")
            else:
                write_log("Periodic traffic logger successfully stopped.", level="DEBUG")
        self._periodic_logger_thread = None
        self._periodic_logger_running.clear()

    #def connect(self, key, server, tab_name, ping_ip=None):

    def connect(self, key, server, tab_name):
        def task(auth_key, login_server, profile_name):
            auth_key = auth_key.strip()
            login_server = login_server.strip()
    
            # Save credentials
            save_key(auth_key, profile_name)
            save_url(login_server, profile_name)
    
            self._show_progress("Starting Tailscale service...", 1)
    
            # Start tailscale service
            if sys.platform == "win32":
                self.run_command(["powershell", "-Command", "Start-Service Tailscale"], require_sudo=True)
                time.sleep(2)
            elif sys.platform.startswith("linux"):
                self.run_command(["systemctl", "start", "tailscaled"], require_sudo=True)
                time.sleep(2)
    
            self._show_progress("Starting Tailscale service...", 2)
    
            # Prepare base command
            cmd = ["tailscale", "up", f"--login-server={login_server}", "--accept-routes"]
    
            from vpn_logic import get_file_path
            mode_file = get_file_path("auth_mode", profile_name)
            auth_mode = "auth_key"
            if os.path.exists(mode_file):
                with open(mode_file, "r") as f:
                    auth_mode = f.read().strip()
    
            if auth_mode == "auth_key":
                if not auth_key:
                    self._print_output("Error: Auth key is missing.")
                    write_profile_log(profile_name, "Missing auth key in 'auth_key' mode.")
                    self._update_status("🔴 Disconnected", "red")
                    self._show_progress("Connection failed.", 0)
                    return
                cmd.insert(2, f"--auth-key={auth_key}")
            else:
                self._print_output("Using Google Login (SSO) mode.")
                write_profile_log(profile_name, "Using Google Login (SSO) mode.")
    
            # Safe display
            safe_cmd_display = [p if not p.startswith("--auth-key=") else "--auth-key=****" for p in cmd]
            self._print_output(f"Running: {' '.join(safe_cmd_display)}")
            write_profile_log(profile_name, f"Running: {' '.join(safe_cmd_display)}")
    
            self._show_progress("Waiting for SSO login...", 2)
    
            # Execute the 'tailscale up' command
            output = self.run_command(cmd, require_sudo=True)
    
            # If SSO mode, check for login URL
            if auth_mode != "auth_key":
                for line in output.splitlines():
                    if "https://" in line and "/a/" in line:
                        login_url = line.strip()
                        write_profile_log(profile_name, f"SSO login URL: {login_url}")
                        self._print_output(f"🔐 SSO Login URL: {login_url}")
                        if self.message_popup_callback:
                            self.message_popup_callback("SSO Login Required", f"Please authenticate in your browser:\n\n{login_url}")
                        try:
                            import webbrowser
                            webbrowser.open(login_url)
                        except:
                            pass
                        break
                    
            # Verify connection
            write_profile_log(profile_name, "Attempting to connect...")
            write_profile_log(profile_name, f"Command output:\n{output.strip()}")
            status_output = self.run_command(["tailscale", "status"])
            self._print_output("Verifying connection...\n" + status_output)
    
            if "Logged out" in status_output or "disconnected" in status_output.lower() or "failed" in output.lower():
                self.connected = False
                self.logged_in = False
                self._update_status("🔴 Disconnected", "red")
                messagebox.showerror("Connection Failed", "Login failed. Check logs or try again.")
                self._notify_logged_out()
                write_profile_log(profile_name, "Connection failed.")
                self._stop_periodic_logger()
                self._show_progress("Connection failed.", 0)
            else:
                self.connected = True
                self.logged_in = True
                self._update_status("🟢 Connected", "green")
                self._notify_connected()
                write_profile_log(profile_name, "Connection successful.")
                self._stop_periodic_logger()
                self._periodic_logger_running.set()
                self._periodic_logger_thread = threading.Thread(
                    target=self._periodic_traffic_logger, args=(profile_name,), daemon=True
                )
                self._periodic_logger_thread.start()
                self._show_progress("Connected successfully!", 0)
    
        # Correct: call the thread with proper args
        threading.Thread(target=task, args=(key, server, tab_name), daemon=True).start()


    def disconnect(self, profile_name):
        def task():
            self._print_output("Disconnecting from Tailscale...")
    
            output = self.run_command(["tailscale", "logout"])
            write_profile_log(profile_name, f"Disconnect output:\n{output.strip()}")
    
            self.connected = False
            self.logged_in = False
    
            self._update_status("🔴 Disconnected", "red")
            self._notify_logged_out()
            self._notify_post_disconnect()
            self._notify_post_logout()
            self._stop_periodic_logger()
    
            self._show_progress("Disconnected.", 0)
    
        threading.Thread(target=task, daemon=True).start()


    # (disconnect, logout, check_status remain unchanged)
