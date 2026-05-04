import sys
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

    def __init__(self):
        super().__init__()
        self.worker = TailscaleProcess()
        
    def check_status(self):
        # We can use another QProcess or a simple check
        check_proc = QProcess()
        check_proc.start("tailscale", ["status"])
        check_proc.waitForFinished(5000)
        output = check_proc.readAllStandardOutput().data().decode().lower()
        
        is_connected = False
        status_text = "Disconnected"
        
        if "logged out" in output:
            is_connected = False
            status_text = "Logged Out"
        elif "logged in" in output or "connected" in output:
            is_connected = True
            status_text = "Connected"
            
        self.connection_status_changed.emit(is_connected, status_text)
        return is_connected, status_text

    def connect(self, login_server, auth_key=None, use_sso=False):
        args = ["up", f"--login-server={login_server}", "--accept-routes"]
        if not use_sso and auth_key:
            args.insert(1, f"--auth-key={auth_key}")
        
        self.worker.run_command(args)

    def logout(self):
        self.worker.run_command(["logout"])
