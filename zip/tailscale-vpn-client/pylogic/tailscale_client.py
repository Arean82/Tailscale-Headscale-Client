# pylogic/tailscale_client.py
# PySide6 port of gui/tailscaleclient.py
# All tkinter.messagebox calls replaced with message_popup_callback.
# Threading unchanged — all callbacks must be thread-safe (use Qt signals).

import os
import sys
import subprocess
import threading
import time

from logic.statuscheck import wait_until_connected
from logic.vpn_logic import save_key, save_url, write_profile_log, write_log
from logic.net_stats import log_tailscale_stats
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
        message_popup_callback=None,
    ):
        self.output_callback        = output_callback
        self.status_callback        = status_callback
        self.connected_callback     = connected_callback
        self.logged_out_callback    = logged_out_callback
        self.post_disconnect_callback = post_disconnect_callback
        self.post_logout_callback   = post_logout_callback
        self.progress_callback      = progress_callback
        self.message_popup_callback = message_popup_callback

        self.connected  = False
        self.logged_in  = False
        self._periodic_logger_thread  = None
        self._periodic_logger_running = threading.Event()

    # ------------------------------------------------------------------
    # Internal dispatch helpers
    # ------------------------------------------------------------------

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

    def _show_popup(self, title, message):
        """Replaces tkinter.messagebox.showerror/showinfo."""
        if self.message_popup_callback:
            self.message_popup_callback(title, message)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def run_command(self, cmd, require_sudo=False):
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if require_sudo and sys.platform.startswith("linux"):
            self._print_output("Elevated command: using pkexec.")
            cmd = ["pkexec"] + cmd

        app_logger.debug(f"Running terminal command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, startupinfo=startupinfo
            )
            output = result.stdout + result.stderr
            app_logger.debug(f"Terminal Response:\n{output.strip()}")
            return output
        except FileNotFoundError:
            app_logger.error("Tailscale command not found.")
            return "Error: Tailscale command not found. Ensure Tailscale is installed and in your PATH."
        except Exception as e:
            app_logger.error(f"Error running command '{' '.join(cmd)}': {e}")
            write_log(f"Error running command '{' '.join(cmd)}': {e}", level="ERROR")
            return f"Error running command: {e}"

    # ------------------------------------------------------------------
    # Periodic traffic logger
    # ------------------------------------------------------------------

    def _periodic_traffic_logger(self, profile):
        app_logger.debug(f"Starting periodic traffic logger for: {profile}")
        while self._periodic_logger_running.is_set():
            if not self.connected:
                break
            log_tailscale_stats(profile)
            self._periodic_logger_running.wait(30)

    def _stop_periodic_logger(self):
        if self._periodic_logger_thread and self._periodic_logger_thread.is_alive():
            self._periodic_logger_running.clear()
            self._periodic_logger_thread.join(timeout=5)
        self._periodic_logger_thread = None
        self._periodic_logger_running.clear()

    def _start_periodic_logger(self, profile):
        self._stop_periodic_logger()
        self._periodic_logger_running.set()
        self._periodic_logger_thread = threading.Thread(
            target=self._periodic_traffic_logger, args=(profile,), daemon=True
        )
        self._periodic_logger_thread.start()

    # ------------------------------------------------------------------
    # Status check
    # ------------------------------------------------------------------

    def is_connected(self):
        try:
            output = self.run_command(["tailscale", "status"])
            if "logged out" in output.lower() or "disconnected" in output.lower():
                return False
            return "logged in" in output.lower() or "connected" in output.lower()
        except Exception as e:
            app_logger.error(f"Error checking connection status: {e}")
            return False

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------

    def connect(self, key, server, tab_name):
        def task(auth_key, login_server, profile_name):
            auth_key     = auth_key.strip()
            login_server = login_server.strip()
            save_key(auth_key, profile_name)
            save_url(login_server, profile_name)
            self._show_progress("Starting Tailscale service...", 1)

            if sys.platform == "win32":
                self.run_command(
                    ["powershell", "-Command", "Start-Service Tailscale"],
                    require_sudo=True,
                )
                time.sleep(2)
            elif sys.platform.startswith("linux"):
                self.run_command(["systemctl", "start", "tailscaled"], require_sudo=True)
                time.sleep(2)

            self._show_progress("Starting Tailscale service...", 2)
            cmd = ["tailscale", "up", f"--login-server={login_server}", "--accept-routes"]

            from logic.vpn_logic import get_file_path
            mode_file  = get_file_path("auth_mode", profile_name)
            auth_mode  = "auth_key"
            if os.path.exists(mode_file):
                with open(mode_file, "r") as f:
                    auth_mode = f.read().strip()

            if auth_mode == "auth_key":
                if not auth_key:
                    self._print_output("Error: Auth key is missing.")
                    self._update_status("🔴 Disconnected", "red")
                    self._show_progress("Connection failed.", 0)
                    return
                cmd.insert(2, f"--auth-key={auth_key}")
            else:
                self._print_output("Using Google Login (SSO) mode.")

            safe_cmd = [
                p if not p.startswith("--auth-key=") else "--auth-key=****"
                for p in cmd
            ]
            self._print_output(f"Running: {' '.join(safe_cmd)}")
            self._show_progress("Waiting for SSO login...", 2)

            output_lines = []
            full_cmd = (["pkexec"] + cmd) if sys.platform.startswith("linux") else cmd
            process  = subprocess.Popen(
                full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )

            for line in process.stdout:
                line = line.strip()
                output_lines.append(line)
                self._print_output(line)
                write_profile_log(profile_name, line)

                if "https://" in line and "/a/" in line:
                    self._print_output(f"🔐 SSO Login URL: {line}")
                    self._show_popup("SSO Login Required",
                                     f"Please authenticate in your browser:\n\n{line}")
                    try:
                        import webbrowser
                        webbrowser.open(line)
                    except Exception as e:
                        app_logger.error(f"Failed to open browser: {e}")

                if line.strip().lower() == "success.":
                    self._mark_connected(profile_name)

            process.wait()
            output = "\n".join(output_lines)

            if not self.connected:
                status_output = self.run_command(["tailscale", "status"])
                self._print_output("Verifying connection...\n" + status_output)

                if "logged out" in status_output.lower() or "disconnected" in status_output.lower():
                    self._mark_disconnected()
                    self._show_popup("Connection Failed",
                                     "Login failed. Check logs or try again.")
                else:
                    self._mark_connected(profile_name)

            if auth_mode != "auth_key" and not self.connected:
                self._print_output("[DEBUG] Waiting for Tailscale to connect via SSO polling...")
                if wait_until_connected():
                    self._mark_connected(profile_name)
                else:
                    self._mark_disconnected()
                    self._show_popup("Connection Failed",
                                     "Login via SSO timed out. Please try again.")

            # Final verification
            status_output = self.run_command(["tailscale", "status"])
            self._print_output("Verifying connection...\n" + status_output)

            if (
                "Logged out" in status_output
                or "disconnected" in status_output.lower()
                or "failed" in output.lower()
            ):
                self._mark_disconnected()
            else:
                self._mark_connected(profile_name)

        threading.Thread(target=task, args=(key, server, tab_name), daemon=True).start()

    def _mark_connected(self, profile_name):
        self.connected = True
        self.logged_in = True
        self._update_status("🟢 Connected", "green")
        self._notify_connected()
        self._start_periodic_logger(profile_name)
        self._show_progress("Connected successfully!", 0)

    def _mark_disconnected(self):
        self.connected = False
        self.logged_in = False
        self._update_status("🔴 Disconnected", "red")
        self._notify_logged_out()
        self._stop_periodic_logger()
        self._show_progress("Connection failed.", 0)

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    def disconnect(self, profile_name):
        def task():
            self._print_output("Disconnecting from Tailscale...")
            self.run_command(["tailscale", "logout"])
            self.connected = False
            self.logged_in = False
            self._update_status("🔴 Disconnected", "red")
            self._notify_logged_out()
            self._notify_post_disconnect()
            self._notify_post_logout()
            self._stop_periodic_logger()
            self._show_progress("Disconnected.", 0)

        threading.Thread(target=task, daemon=True).start()
