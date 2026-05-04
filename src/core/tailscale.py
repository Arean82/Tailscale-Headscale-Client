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
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.current_command = ""

    def run_command(self, cmd_args):
        self.current_command = " ".join(cmd_args)
        # On Windows, we might need to handle pkexec/sudo differently or ignore it
        # Tailscale usually handles its own elevation or requires it beforehand
        self.process.start("tailscale", cmd_args)

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode().strip()
        if data:
            self.output_received.emit(data)
            
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
    
    def __init__(self, cache_dir: str = None):
        super().__init__()
        self.worker = TailscaleProcess()
        
        # Initialize Cache
        cache_file = os.path.join(cache_dir, "ts_cache.json") if cache_dir else "ts_cache.json"
        from .cache_manager import CacheManager
        self.cache = CacheManager(cache_file, expiry_seconds=30)
        
        # Async check process
        self.status_proc = QProcess()
        self.status_proc.finished.connect(self._on_status_finished)
        
    def check_status(self, force=False):
        """Asynchronously check tailscale status."""
        if not force:
            cached_status = self.cache.get("status")
            if cached_status:
                self.connection_status_changed.emit(cached_status["connected"], cached_status["text"])
                return cached_status["connected"], cached_status["text"]

        if self.status_proc.state() == QProcess.NotRunning:
            self.status_proc.start("tailscale", ["status"])
        return False, "Checking..."

    def _on_status_finished(self):
        output = self.status_proc.readAllStandardOutput().data().decode().lower()
        
        is_connected = False
        status_text = "Disconnected"
        
        if "logged out" in output:
            is_connected = False
            status_text = "Logged Out"
        elif "logged in" in output or "connected" in output:
            is_connected = True
            status_text = "Connected"
            
        # Update Cache
        self.cache.set("status", {"connected": is_connected, "text": status_text})
        
        self.connection_status_changed.emit(is_connected, status_text)

    def connect(self, login_server, auth_key=None, use_sso=False):
        args = ["up", f"--login-server={login_server}", "--accept-routes"]
        if not use_sso and auth_key:
            args.insert(1, f"--auth-key={auth_key}")
        
        self.cache.clear() # Clear cache on new connection attempt
        self.worker.run_command(args)

    def logout(self):
        self.cache.clear()
        self.worker.run_command(["logout"])
