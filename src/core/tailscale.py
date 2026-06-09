# src/core/tailscale.py
# This is the core Tailscale utility for the application.

import sys
import os
import re
import shutil
from PySide6.QtCore import QObject, Signal, QProcess

def get_tailscale_path():
    """Dynamically resolve the absolute path to the Tailscale executable on macOS, Windows, and Linux."""
    # 1. Check if tailscale is in system PATH
    resolved = shutil.which("tailscale")
    if resolved:
        return resolved
        
    if sys.platform == "darwin":
        # Check standard macOS installation paths
        mac_paths = [
            "/Applications/Tailscale.app/Contents/Resources/cli/tailscale",
            "/opt/homebrew/bin/tailscale",
            "/usr/local/bin/tailscale",
            "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path
                
    elif sys.platform == "win32":
        # Check standard Windows installation paths
        win_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Tailscale", "tailscale.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Tailscale", "tailscale.exe"),
            os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Tailscale", "tailscale.exe")
        ]
        for path in win_paths:
            if os.path.exists(path):
                return path
                
    elif sys.platform.startswith("linux"):
        # Check standard Linux installation paths
        linux_paths = [
            "/usr/sbin/tailscale",
            "/usr/bin/tailscale",
            "/usr/local/bin/tailscale",
            "/sbin/tailscale"
        ]
        for path in linux_paths:
            if os.path.exists(path):
                return path
                
    # Fallback default
    return "tailscale"

class TailscaleProcess(QObject):
    output_received = Signal(str)
    error_received = Signal(str)
    status_changed = Signal(str)
    sso_url_found = Signal(str)
    finished = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)
        self.current_command = ""

    def _handle_error(self, error):
        if error == QProcess.FailedToStart:
            msg = "Tailscale is not installed on this system or is not found in your system's PATH. Please install Tailscale."
            self.error_received.emit(msg)
            self.finished.emit(-1, "FailedToStart")

    def __del__(self):
        """Ensure process is cleaned up safely."""
        self.cleanup()

    def cleanup(self):
        """Explicitly and gracefully terminate the active QProcess and any orphans."""
        try:
            if hasattr(self, 'process') and self.process is not None:
                if self.process.state() != QProcess.NotRunning:
                    self.process.terminate()
                    if not self.process.waitForFinished(500):
                        self.process.kill()
            
            # Forceful watchdog for any remaining orphaned child tailscale processes
            try:
                import psutil
                import os
                parent = psutil.Process(os.getpid())
                for child in parent.children(recursive=True):
                    if "tailscale" in child.name().lower():
                        child.kill()
            except Exception:
                pass
        except (RuntimeError, AttributeError):
            pass


    def run_command(self, cmd_args, profile_name=None):
        """Starts a tailscale command, ensuring any previous command is cleaned up."""
        try:
            if self.process.state() != QProcess.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(1000):
                    self.process.kill()
        except (RuntimeError, AttributeError):
            # Process object might be in a weird state during shutdown
            pass

        self.current_command = " ".join(cmd_args)
        self.profile_name = profile_name
        self.process.start(get_tailscale_path(), cmd_args)

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode().strip()
        if data:
            self.output_received.emit(data)
            
            # Log to profile file if provided
            if hasattr(self, 'profile_name') and self.profile_name:
                from ..utils.logger import write_profile_log
                write_profile_log(self.profile_name, data)
            
            # Check for SSO URL
            if "https://" in data:
                match = re.search(r'https://\S+', data)
                if match:
                    self.sso_url_found.emit(match.group(0))

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode().strip()
        if data:
            # Check for SSO login/authentication instructions in stderr
            if "https://" in data or "to authenticate" in data.lower() or "visit:" in data.lower():
                match = re.search(r'https://\S+', data)
                if match:
                    self.sso_url_found.emit(match.group(0))
                return # Do NOT emit as a critical error
                
            self.error_received.emit(data)

    def _handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code, str(exit_status))

class TailscaleManager(QObject):
    connection_status_changed = Signal(bool, str) # (is_connected, status_text)
    state_changed = Signal(object) # AppState transition signal
    
    def __init__(self, cache_dir: str = None, parent=None):
        super().__init__(parent)
        from .models import AppState
        self.current_state = AppState.DISCONNECTED
        self.use_local_api = True
        self.sso_timeout = 120
        self.insecure_ssl = False
        self.active_session = None
        self.worker = TailscaleProcess()
        self.worker.sso_url_found.connect(self._on_sso_url_found)
        self.worker.finished.connect(self._on_worker_finished)
        
        # Reconnection & SSO Timeout timers
        from PySide6.QtCore import QTimer
        self.sso_timeout_timer = QTimer(self)
        self.sso_timeout_timer.setSingleShot(True)
        self.sso_timeout_timer.timeout.connect(self._on_sso_timeout)
        
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.timeout.connect(self._on_reconnect_retry)
        
        self.last_connect_args = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        # Initialize Cache
        cache_file = os.path.join(cache_dir, "ts_cache.json") if cache_dir else "ts_cache.json"
        from .cache_manager import CacheManager
        self.cache = CacheManager(cache_file, expiry_seconds=30)
        
        # Async check process
        self.status_proc = QProcess(self)
        self.status_proc.finished.connect(self._on_status_finished)

    def _update_state(self, status_text):
        from .models import AppState
        new_state = AppState.DISCONNECTED
        if status_text == "Connected":
            new_state = AppState.CONNECTED
            self.sso_timeout_timer.stop()
            self.reconnect_attempts = 0
        elif status_text == "Connecting...":
            new_state = AppState.CONNECTING
        elif status_text == "Logged Out":
            new_state = AppState.LOGGED_OUT
        elif status_text == "Pending Admin Approval":
            new_state = AppState.PENDING_APPROVAL
        elif "error" in status_text.lower():
            new_state = AppState.ERROR
            
        if self.current_state != new_state:
            self.current_state = new_state
            self.state_changed.emit(new_state)

    def _on_sso_timeout(self):
        """Handle SSO login flow timeout."""
        from .models import AppState, LoginState
        if self.active_session:
            self.active_session.update_state(LoginState.TIMEOUT, "SSO Login timed out.")
            self.active_session.cleanup()
        if self.current_state == AppState.CONNECTING:
            self.worker.cleanup()
            self._update_state("Error")
            self.worker.error_received.emit("SSO Login timed out. Please try connecting again.")

    def _trigger_reconnect(self):
        """Triggers automatic reconnect attempts with exponential backoff."""
        from .models import AppState
        if self.last_connect_args and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_attempts * 3000  # 3s, 6s, 9s backoff
            self._update_state("Connecting...")
            self.worker.error_received.emit(f"Connection failed. Retrying automatically (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay/1000:.0f}s...")
            self.reconnect_timer.start(delay)
        else:
            self._update_state("Error")

    def _on_reconnect_retry(self):
        """Executes the actual reconnection retry."""
        if self.last_connect_args:
            login_server = self.last_connect_args.get("login_server")
            auth_key = self.last_connect_args.get("auth_key")
            use_sso = self.last_connect_args.get("use_sso")
            profile_name = self.last_connect_args.get("profile_name")
            exit_node = self.last_connect_args.get("exit_node")
            routes = self.last_connect_args.get("routes")
            allow_lan = self.last_connect_args.get("allow_lan", False)
            disable_snat = self.last_connect_args.get("disable_snat", False)
            hostname = self.last_connect_args.get("hostname", "")
            force_reset = self.last_connect_args.get("force_reset", False)
            advertise_exit_node = self.last_connect_args.get("advertise_exit_node", False)
            shields_up = self.last_connect_args.get("shields_up", False)
            force_reauth = self.last_connect_args.get("force_reauth", False)
            advertise_tags = self.last_connect_args.get("advertise_tags", "")
            
            args = ["up", f"--login-server={login_server}", "--accept-routes"]
            if force_reset:
                args.append("--reset")
            if force_reauth:
                args.append("--force-reauth")
            if advertise_exit_node:
                args.append("--advertise-exit-node")
            if shields_up:
                args.append("--shields-up")
            if advertise_tags:
                args.append(f"--advertise-tags={advertise_tags}")
            if getattr(self, "insecure_ssl", False):
                args.append("--insecure-skip-tls-verify=true")
            if not use_sso and auth_key:
                args.insert(1, f"--auth-key={auth_key}")
                
            if hostname:
                args.append(f"--hostname={hostname}")
                
            if exit_node:
                args.append(f"--exit-node={exit_node}")
                if allow_lan:
                    args.append("--exit-node-allow-lan-access=true")
                
            if routes:
                args.append(f"--advertise-routes={routes}")
                if disable_snat:
                    args.append("--snat-subnet-routes=false")
                
            self.worker.run_command(args, profile_name)

    def _on_sso_url_found(self, url):
        if self.active_session:
            self.active_session.set_sso_url(url)
        import webbrowser
        webbrowser.open(url)

    def _on_worker_finished(self, code, status):
        self.check_status()
        from .models import AppState
        if code != 0 and self.current_state == AppState.CONNECTING:
            self._trigger_reconnect()

    def cleanup(self):
        """Cleanly and gracefully terminate all active background subprocesses on shutdown."""
        if hasattr(self, 'worker') and self.worker is not None:
            self.worker.cleanup()
            
        try:
            if hasattr(self, 'status_proc') and self.status_proc is not None:
                if self.status_proc.state() != QProcess.NotRunning:
                    self.status_proc.terminate()
                    if not self.status_proc.waitForFinished(500):
                        self.status_proc.kill()
        except (RuntimeError, AttributeError):
            pass
        
    def check_status(self, force=False):
        """Asynchronously check tailscale status using JSON or instantly via Local API."""
        cached_status = self.cache.get("status")
        
        if not force and cached_status:
            self.connection_status_changed.emit(cached_status["connected"], cached_status["text"])
            return cached_status["connected"], cached_status["text"]

        if self.use_local_api:
            try:
                from src.utils.local_api import query_local_api
                data = query_local_api()
                is_connected = False
                status_text = "Disconnected"
                ips = data.get("TailscaleIPs", [])
                state = data.get("BackendState", "")
                
                if state == "Running":
                    is_connected = True
                    status_text = "Connected"
                elif state == "NeedsLogin":
                    is_connected = False
                    status_text = "Logged Out"
                elif state == "NeedsMachineAuth":
                    is_connected = False
                    status_text = "Pending Admin Approval"
                else:
                    status_text = state or "Disconnected"
                    
                self.cache.set("status", {"connected": is_connected, "text": status_text, "ips": ips, "raw_data": data})
                self._update_state(status_text)
                self.connection_status_changed.emit(is_connected, status_text)
                return is_connected, status_text
            except Exception:
                # Silently fallback to CLI process on any Local API error
                pass

        if self.status_proc.state() == QProcess.NotRunning:
            self.status_proc.start(get_tailscale_path(), ["status", "--json"])
        
        # Return cached status as a placeholder if we have it, otherwise "Checking"
        if cached_status:
            return cached_status["connected"], cached_status["text"]
        return False, "Checking..."

    def _on_status_finished(self):
        output = self.status_proc.readAllStandardOutput().data().decode()
        
        is_connected = False
        status_text = "Disconnected"
        ips = []
        raw_data = {}
        
        try:
            import json
            data = json.loads(output)
            raw_data = data
            state = data.get("BackendState", "")
            ips = data.get("TailscaleIPs", [])
            
            if state == "Running":
                is_connected = True
                status_text = "Connected"
            elif state == "NeedsLogin":
                is_connected = False
                status_text = "Logged Out"
            elif state == "NeedsMachineAuth":
                is_connected = False
                status_text = "Pending Admin Approval"
            else:
                status_text = state or "Disconnected"
        except Exception:
            if "logged out" in output.lower():
                is_connected = False
                status_text = "Logged Out"
            elif "running" in output.lower() or "connected" in output.lower():
                is_connected = True
                status_text = "Connected"
            
        self.cache.set("status", {"connected": is_connected, "text": status_text, "ips": ips, "raw_data": raw_data})
        self._update_state(status_text)
        self.connection_status_changed.emit(is_connected, status_text)

    def start_service(self):
        """Try to start Tailscale service if not running."""
        # This is a best-effort start. If it requires elevation, 
        # it might fail if the user isn't admin, but matches legacy behavior.
        if sys.platform == "win32":
            # Using QProcess for non-blocking start
            QProcess.startDetached("powershell", ["-Command", "Start-Service Tailscale"])
        elif sys.platform.startswith("linux"):
            QProcess.startDetached("systemctl", ["start", "tailscaled"])
        elif sys.platform == "darwin":
            QProcess.startDetached("launchctl", ["start", "com.tailscale.tailscaled"])

    def connect(self, login_server, auth_key=None, use_sso=False, profile_name=None, exit_node=None, routes=None, ssh=False, accept_dns=False, allow_lan=False, disable_snat=False, hostname="", force_reset=False, advertise_exit_node=False, shields_up=False, force_reauth=False, advertise_tags=""):
        self.last_connect_args = {
            "login_server": login_server,
            "auth_key": auth_key,
            "use_sso": use_sso,
            "profile_name": profile_name,
            "exit_node": exit_node,
            "routes": routes,
            "ssh": ssh,
            "accept_dns": accept_dns,
            "allow_lan": allow_lan,
            "disable_snat": disable_snat,
            "hostname": hostname,
            "force_reset": force_reset,
            "advertise_exit_node": advertise_exit_node,
            "shields_up": shields_up,
            "force_reauth": force_reauth,
            "advertise_tags": advertise_tags
        }
        self.reconnect_attempts = 0
        
        # 1. Best-effort service start
        self.start_service()
        
        # 2. Run 'up' command
        args = ["up", f"--login-server={login_server}", "--accept-routes"]
        if force_reset:
            args.append("--reset")
        if force_reauth:
            args.append("--force-reauth")
        if advertise_exit_node:
            args.append("--advertise-exit-node")
        if shields_up:
            args.append("--shields-up")
        if advertise_tags:
            args.append(f"--advertise-tags={advertise_tags}")
        if getattr(self, "insecure_ssl", False):
            args.append("--insecure-skip-tls-verify=true")
        if ssh:
            args.append("--ssh")
        args.append(f"--accept-dns={'true' if accept_dns else 'false'}")
        
        if not use_sso and auth_key:
            args.insert(1, f"--auth-key={auth_key}")
            
        if hostname:
            args.append(f"--hostname={hostname}")
            
        if exit_node:
            args.append(f"--exit-node={exit_node}")
            if allow_lan:
                args.append("--exit-node-allow-lan-access=true")
            
        if routes:
            args.append(f"--advertise-routes={routes}")
            if disable_snat:
                args.append("--snat-subnet-routes=false")
        
        self.cache.clear() # Clear cache on new connection attempt
        self._update_state("Connecting...")
        
        # Start dynamic SSO timeout if SSO mode is enabled
        if use_sso:
            self.sso_timeout_timer.start(self.sso_timeout * 1000)
            
        self.worker.run_command(args, profile_name)
        from .models import LoginSession
        self.active_session = LoginSession(self.sso_timeout)
        self.active_session.start(self.worker.process)

    def switch_profile(self, native_profile_name, profile_name=None):
        """Instantly switch to a native Tailscale profile."""
        self.cache.clear()
        self.worker.run_command(["switch", native_profile_name], profile_name)

    def logout(self, profile_name=None):
        if hasattr(self, 'active_session') and self.active_session:
            self.active_session.cancel()
            self.active_session = None
        self.cache.clear()
        self.worker.run_command(["logout"], profile_name)

    def logout_sync(self):
        """Synchronous logout for app exit."""
        import subprocess
        self.cache.clear()
        try:
            # Hide console window on Windows
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                import subprocess
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            
            subprocess.run([get_tailscale_path(), "logout"], capture_output=True, startupinfo=startupinfo, creationflags=creationflags)
        except:
            pass

    def get_stats(self):
        """Get psutil stats for the Tailscale interface."""
        import psutil
        try:
            stats = psutil.net_io_counters(pernic=True)
            
            # 1. Try resolving by cached IP address
            cached_status = self.cache.get("status")
            ts_ips = cached_status.get("ips", []) if cached_status else []
            if ts_ips:
                addrs = psutil.net_if_addrs()
                target_iface = None
                for iface, addr_list in addrs.items():
                    for addr in addr_list:
                        if addr.address in ts_ips:
                            target_iface = iface
                            break
                    if target_iface:
                        break
                
                if target_iface and target_iface in stats:
                    return stats[target_iface]

            # 2. Fallback to name matching
            for iface, data in stats.items():
                if "tailscale" in iface.lower():
                    return data
        except Exception:
            pass
        return None

    def check_status_sync(self):
        """Synchronous check for app exit logic."""
        import subprocess
        import json
        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run([get_tailscale_path(), "status", "--json"], capture_output=True, text=True, startupinfo=startupinfo, creationflags=creationflags)
            data = json.loads(result.stdout)
            state = data.get("BackendState")
            
            # Legacy logic: only block if NOT NeedsLogin/Stopped
            is_connected = (state != "NeedsLogin" and state != "Stopped" and state != "NoState")
            return is_connected, state
        except:
            return False, "Error"

    def get_version(self):
        """Helper to synchronously check the Tailscale CLI version."""
        import subprocess
        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run([get_tailscale_path(), "version"], capture_output=True, text=True, startupinfo=startupinfo, creationflags=creationflags)
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    def run_ping(self, target):
        """Helper to synchronously execute a tailscale ping command against a peer."""
        import subprocess
        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run([get_tailscale_path(), "ping", "--timeout", "2s", target], capture_output=True, text=True, startupinfo=startupinfo, creationflags=creationflags)
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    def run_netcheck(self):
        """Helper to synchronously execute a tailscale netcheck command."""
        import subprocess
        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run([get_tailscale_path(), "netcheck"], capture_output=True, text=True, startupinfo=startupinfo, creationflags=creationflags)
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"
