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


    def run_command(self, cmd_args, profile_name=None):
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

    def _handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code, str(exit_status))

class TailscaleManager(QObject):
    connection_status_changed = Signal(bool, str) # (is_connected, status_text)
    
    def __init__(self, cache_dir: str = None, parent=None):
        super().__init__(parent)
        self.worker = TailscaleProcess()
        
        # Initialize Cache
        cache_file = os.path.join(cache_dir, "ts_cache.json") if cache_dir else "ts_cache.json"
        from .cache_manager import CacheManager
        self.cache = CacheManager(cache_file, expiry_seconds=30)
        
        # Async check process
        self.status_proc = QProcess(self)
        self.status_proc.finished.connect(self._on_status_finished)
        
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
        
        try:
            import json
            data = json.loads(output)
            state = data.get("BackendState", "")
            
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
            
        self.cache.set("status", {"connected": is_connected, "text": status_text})
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
            if sys.platform == "win32":
                import subprocess
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(["tailscale", "logout"], capture_output=True, startupinfo=startupinfo)
        except:
            pass

    def get_stats(self):
        """Get psutil stats for the Tailscale interface."""
        import psutil
        try:
            stats = psutil.net_io_counters(pernic=True)
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
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, startupinfo=startupinfo)
            data = json.loads(result.stdout)
            state = data.get("BackendState")
            
            # Legacy logic: only block if NOT NeedsLogin/Stopped
            is_connected = (state != "NeedsLogin" and state != "Stopped" and state != "NoState")
            return is_connected, state
        except:
            return False, "Error"
