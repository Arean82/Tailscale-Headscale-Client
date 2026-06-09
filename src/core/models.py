from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List

class AppState(Enum):
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting..."
    CONNECTED = "Connected"
    LOGGED_OUT = "Logged Out"
    PENDING_APPROVAL = "Pending Admin Approval"
    ERROR = "Error"

@dataclass
class Profile:
    name: str
    login_server: str = "https://controlplane.tailscale.com"
    auth_key: str = ""
    auth_mode: str = "auth_key"  # "auth_key" or "sso"
    auto_connect: bool = False
    exit_node: str = ""
    routes: str = ""
    native_profile: str = ""
    is_native_switch: bool = False
    enable_ssh: bool = False
    accept_dns: bool = False
    allow_lan: bool = False
    disable_snat: bool = False
    hostname: str = ""
    last_known_ip: str = ""
    enable_dns_fallback: bool = False

@dataclass
class AppSettings:
    auto_start: bool = False
    auto_connect: bool = False
    enable_logs: bool = False
    advanced_features: bool = False
    max_tabs: int = 5
    last_profile: Optional[str] = None
    use_local_api: bool = True
    sso_timeout: int = 120
    enable_tray_switcher: bool = False
    insecure_ssl: bool = False
    startup_delay: int = 10


class LoginState(Enum):
    IDLE = "IDLE"
    STARTED = "STARTED"
    SSO_URL_FOUND = "SSO_URL_FOUND"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class LoginSession:
    def __init__(self, timeout_seconds: int = 120):
        import time
        self.started_at: float = time.time()
        self.state: LoginState = LoginState.IDLE
        self.timeout: int = timeout_seconds
        self.process = None
        self.sso_url: str = ""
        self.error_message: str = ""

    def start(self, process):
        import time
        self.started_at = time.time()
        self.state = LoginState.STARTED
        self.process = process
        self.sso_url = ""
        self.error_message = ""

    def set_sso_url(self, url: str):
        self.sso_url = url
        self.state = LoginState.SSO_URL_FOUND

    def update_state(self, new_state: LoginState, error_msg: str = ""):
        self.state = new_state
        if error_msg:
            self.error_message = error_msg

    def check_timeout(self) -> bool:
        import time
        if self.state in [LoginState.STARTED, LoginState.SSO_URL_FOUND]:
            elapsed = time.time() - self.started_at
            if elapsed > self.timeout:
                self.state = LoginState.TIMEOUT
                self.cleanup()
                return True
        return False

    def cancel(self):
        self.state = LoginState.CANCELLED
        self.cleanup()

    def cleanup(self):
        if self.process:
            try:
                from PySide6.QtCore import QProcess
                if self.process.state() != QProcess.NotRunning:
                    self.process.terminate()
                    if not self.process.waitForFinished(500):
                        self.process.kill()
            except Exception:
                pass
            self.process = None


