# src/core/tailscale.py
# This is the core Tailscale utility for the application.

import sys
import os
import shutil
from typing import Optional
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
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            except (psutil.Error, OSError):
                return
        except (RuntimeError, AttributeError):
            return

    def run_command(self, cmd_args, profile_name=None):
        """Starts a tailscale command, ensuring any previous command is cleaned up."""
        try:
            if self.process.state() != QProcess.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(1000):
                    self.process.kill()
        except (RuntimeError, AttributeError):
            # Process object might be in a weird state during shutdown
            return

        self.current_command = " ".join(cmd_args)
        self.profile_name = profile_name
        self.process.start(get_tailscale_path(), cmd_args)

    def _extract_auth_url(self, text: str) -> str | None:
        """Deterministically extracts and validates an authentication/registration URL without regex."""
        import urllib.parse
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            for token in line.split():
                # Strip common terminal wrapper/punctuation characters
                clean = token.strip(" \t\r\n'\"()[]<>,;")
                clean = clean.rstrip(".")
                if clean.startswith(("https://", "http://")):
                    try:
                        parsed = urllib.parse.urlparse(clean)
                        if parsed.scheme in ("http", "https") and parsed.netloc:
                            # Verify path points to Tailscale/Headscale auth endpoints or contains auth key
                            path_lower = parsed.path.lower()
                            if any(k in path_lower for k in ("/register", "/a/", "/auth", "mkey:")) or "mkey:" in clean:
                                return clean
                            # General fallback if line explicitly states to authenticate/visit
                            line_lower = line.lower()
                            if "authenticate" in line_lower or "visit:" in line_lower:
                                return clean
                    except ValueError:
                        continue
        return None

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode().strip()
        if data:
            self.output_received.emit(data)
            
            # Log to profile file if provided
            if hasattr(self, 'profile_name') and self.profile_name:
                from ..utils.logger import write_profile_log
                write_profile_log(self.profile_name, data)
            
            # Deterministically check for auth URL
            url = self._extract_auth_url(data)
            if url:
                self.sso_url_found.emit(url)

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode().strip()
        if data:
            # Deterministically check for auth URL in stderr
            url = self._extract_auth_url(data)
            if url:
                self.sso_url_found.emit(url)
                return  # Do NOT emit as a critical error

            # Actionable diagnostics for Headscale pre-auth key expiration
            data_lower = data.lower()
            if "invalid auth key" in data_lower or "key has expired" in data_lower or "authorization failed" in data_lower:
                p_info = f" for profile '{self.profile_name}'" if hasattr(self, 'profile_name') and self.profile_name else ""
                data = f"Authentication Failed{p_info}: Headscale Auth Key is expired or invalid. Please update the key in the profile settings.\n\nDetails: {data}"

            self.error_received.emit(data)

    def _handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code, str(exit_status))

class TailscaleManager(QObject):
    connection_status_changed = Signal(bool, str) # (is_connected, status_text)
    state_changed = Signal(object) # AppState transition signal
    
    def __init__(self, cache_dir: Optional[str] = None, parent=None):
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
        if self.last_connect_args and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_attempts * 3000  # 3s, 6s, 9s backoff
            self._update_state("Connecting...")
            self.worker.error_received.emit(f"Connection failed. Retrying automatically (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay/1000:.0f}s...")
            self.reconnect_timer.start(delay)
        else:
            self._update_state("Error")

    def _build_up_args(self, connect_args):
        """Construct a complete, unambiguous argument list for 'tailscale up' with explicit true/false values."""
        import shlex
        login_server = connect_args.get("login_server")
        auth_key = connect_args.get("auth_key")
        use_sso = connect_args.get("use_sso")
        exit_node = connect_args.get("exit_node")
        routes = connect_args.get("routes")
        ssh = connect_args.get("ssh", False)
        accept_dns = connect_args.get("accept_dns", False)
        accept_routes = connect_args.get("accept_routes", True)
        allow_lan = connect_args.get("allow_lan", False)
        disable_snat = connect_args.get("disable_snat", False)
        hostname = connect_args.get("hostname", "")
        force_reset = connect_args.get("force_reset", False)
        advertise_exit_node = connect_args.get("advertise_exit_node", False)
        shields_up = connect_args.get("shields_up", False)
        force_reauth = connect_args.get("force_reauth", False)
        advertise_tags = connect_args.get("advertise_tags", "")
        unattended = connect_args.get("unattended", False)
        webclient = connect_args.get("webclient", False)
        advertise_connector = connect_args.get("advertise_connector", False)
        accept_risk = connect_args.get("accept_risk", "")
        extra_args = connect_args.get("extra_args", "")

        args = ["up", f"--login-server={login_server}"]

        if not use_sso and auth_key:
            args.append(f"--auth-key={auth_key}")

        # Explicit tri-state / boolean flags to guarantee toggling works predictably
        args.append(f"--accept-routes={'true' if accept_routes else 'false'}")
        args.append(f"--accept-dns={'true' if accept_dns else 'false'}")
        args.append(f"--shields-up={'true' if shields_up else 'false'}")
        args.append(f"--ssh={'true' if ssh else 'false'}")
        args.append(f"--advertise-exit-node={'true' if advertise_exit_node else 'false'}")

        if force_reset:
            args.append("--reset")
        if force_reauth:
            args.append("--force-reauth")
        if advertise_tags:
            args.append(f"--advertise-tags={advertise_tags}")
        if getattr(self, "insecure_ssl", False):
            args.append("--insecure-skip-tls-verify=true")

        if unattended and sys.platform == "win32":
            args.append(f"--unattended={'true' if unattended else 'false'}")
        if webclient:
            args.append(f"--webclient={'true' if webclient else 'false'}")
        if advertise_connector:
            args.append(f"--advertise-connector={'true' if advertise_connector else 'false'}")

        if accept_risk and accept_risk.lower() != "none":
            args.append(f"--accept-risk={accept_risk}")

        if hostname:
            args.append(f"--hostname={hostname}")

        if exit_node:
            args.append(f"--exit-node={exit_node}")
            args.append(f"--exit-node-allow-lan-access={'true' if allow_lan else 'false'}")

        if routes:
            args.append(f"--advertise-routes={routes}")
            if disable_snat:
                args.append("--snat-subnet-routes=false")

        if extra_args:
            try:
                args.extend(shlex.split(extra_args))
            except Exception as e:
                self.logger.error(f"Error parsing extra flags '{extra_args}': {e}")

        return args

    def _on_reconnect_retry(self):
        """Executes the actual reconnection retry."""
        if self.last_connect_args:
            profile_name = self.last_connect_args.get("profile_name")
            args = self._build_up_args(self.last_connect_args)
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
            return
        
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
                    is_connected = False
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
                is_connected = False
                status_text = state or "Disconnected"
        except Exception:
            if "logged out" in output.lower():
                is_connected = False
                status_text = "Logged Out"
            elif "running" in output.lower() or "connected" in output.lower():
                is_connected = True
                status_text = "Connected"
            else:
                is_connected = False
                status_text = "Disconnected"
            
        self.cache.set("status", {"connected": is_connected, "text": status_text, "ips": ips, "raw_data": raw_data})
        self._update_state(status_text)
        self.connection_status_changed.emit(is_connected, status_text)

    def start_service(self):
        """Try to start Tailscale service if not running."""
        # This is a best-effort start. If it requires elevation, 
        # it might fail if the user isn't admin, but matches legacy behavior.
        if sys.platform == "win32":
            # Native Windows net command starts service instantly without PowerShell overhead
            QProcess.startDetached("net", ["start", "Tailscale"])
        elif sys.platform.startswith("linux"):
            QProcess.startDetached("systemctl", ["start", "tailscaled"])
        elif sys.platform == "darwin":
            QProcess.startDetached("launchctl", ["start", "com.tailscale.tailscaled"])

    def connect(self, login_server, auth_key=None, use_sso=False, profile_name=None, exit_node=None, routes=None, ssh=False, accept_dns=False, allow_lan=False, disable_snat=False, hostname="", force_reset=False, advertise_exit_node=False, shields_up=False, force_reauth=False, advertise_tags="", accept_routes=True, unattended=False, webclient=False, advertise_connector=False, accept_risk="", extra_args=""):
        # Detect if switching to a different Headscale server to prevent machine key conflicts
        last_server = self.last_connect_args.get("login_server") if self.last_connect_args else None
        if last_server and login_server and last_server.strip() != login_server.strip():
            # Server changed: Perform synchronous logout so old machine key doesn't conflict
            self.logout_sync()

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
            "advertise_tags": advertise_tags,
            "accept_routes": accept_routes,
            "unattended": unattended,
            "webclient": webclient,
            "advertise_connector": advertise_connector,
            "accept_risk": accept_risk,
            "extra_args": extra_args
        }
        self.reconnect_attempts = 0
        
        # 1. Best-effort service start
        self.start_service()
        
        # 2. Build 'up' command arguments
        args = self._build_up_args(self.last_connect_args)
        
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
        except (subprocess.SubprocessError, OSError):
            # Service may already be logged out or stopped
            return

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
        except (KeyError, OSError, psutil.Error):
            return None
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
        except Exception:
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
