import sys
import os
import re
from PySide6.QtCore import QObject, Signal, QProcess

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
        self.current_command = ""

    def __del__(self):
        """Ensure process is cleaned up safely."""
        try:
            # Check if the internal C++ object still exists
            if hasattr(self, 'process') and self.process is not None:
                if self.process.state() != QProcess.NotRunning:
                    self.process.terminate()
                    if not self.process.waitForFinished(500):
                        self.process.kill()
        except (RuntimeError, AttributeError):
            # Object already deleted by Qt's parent-child system
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
        self.process.start("tailscale", cmd_args)

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
            self.error_received.emit(data)
            
            # Tailscale often prints the login URL to stderr
            if "https://" in data:
                match = re.search(r'https://\S+', data)
                if match:
                    self.sso_url_found.emit(match.group(0))

    def _handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code, str(exit_status))

class TailscaleManager(QObject):
    connection_status_changed = Signal(bool, str) # (is_connected, status_text)
    
    def __init__(self, cache_dir: str = None, parent=None):
        super().__init__(parent)
        self.worker = TailscaleProcess()
        self.worker.sso_url_found.connect(self._on_sso_url_found)
        self.worker.finished.connect(self._on_worker_finished)
        
        # Initialize Cache
        cache_file = os.path.join(cache_dir, "ts_cache.json") if cache_dir else "ts_cache.json"
        from .cache_manager import CacheManager
        self.cache = CacheManager(cache_file, expiry_seconds=30)
        
        # Async check process
        self.status_proc = QProcess(self)
        self.status_proc.finished.connect(self._on_status_finished)

    def _on_sso_url_found(self, url):
        import webbrowser
        webbrowser.open(url)

    def _on_worker_finished(self, code, status):
        self.check_status()
        
    def check_status(self, force=False):
        """Asynchronously check tailscale status using JSON."""
        cached_status = self.cache.get("status")
        
        if not force and cached_status:
            self.connection_status_changed.emit(cached_status["connected"], cached_status["text"])
            return cached_status["connected"], cached_status["text"]

        if self.status_proc.state() == QProcess.NotRunning:
            self.status_proc.start("tailscale", ["status", "--json"])
        
        # Return cached status as a placeholder if we have it, otherwise "Checking"
        if cached_status:
            return cached_status["connected"], cached_status["text"]
        return False, "Checking..."

    def _on_status_finished(self):
        output = self.status_proc.readAllStandardOutput().data().decode()
        
        is_connected = False
        status_text = "Disconnected"
        ips = []
        
        try:
            import json
            data = json.loads(output)
            state = data.get("BackendState", "")
            ips = data.get("TailscaleIPs", [])
            
            if state == "Running":
                is_connected = True
                status_text = "Connected"
            elif state == "NeedsLogin":
                is_connected = False
                status_text = "Logged Out"
            else:
                status_text = state or "Disconnected"
        except Exception:
            if "logged out" in output.lower():
                is_connected = False
                status_text = "Logged Out"
            elif "running" in output.lower() or "connected" in output.lower():
                is_connected = True
                status_text = "Connected"
            
        self.cache.set("status", {"connected": is_connected, "text": status_text, "ips": ips})
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

    def connect(self, login_server, auth_key=None, use_sso=False, profile_name=None):
        # 1. Best-effort service start
        self.start_service()
        
        # 2. Run 'up' command
        args = ["up", f"--login-server={login_server}", "--accept-routes"]
        if not use_sso and auth_key:
            args.insert(1, f"--auth-key={auth_key}")
        
        self.cache.clear() # Clear cache on new connection attempt
        self.worker.run_command(args, profile_name)

    def logout(self, profile_name=None):
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
            
            subprocess.run(["tailscale", "logout"], capture_output=True, startupinfo=startupinfo, creationflags=creationflags)
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
            
            result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, startupinfo=startupinfo, creationflags=creationflags)
            data = json.loads(result.stdout)
            state = data.get("BackendState")
            
            # Legacy logic: only block if NOT NeedsLogin/Stopped
            is_connected = (state != "NeedsLogin" and state != "Stopped" and state != "NoState")
            return is_connected, state
        except:
            return False, "Error"
