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

@dataclass
class AppSettings:
    auto_start: bool = False
    auto_connect: bool = False
    enable_logs: bool = False
    advanced_features: bool = False
    max_tabs: int = 5
    last_profile: Optional[str] = None
    use_local_api: bool = False
    sso_timeout: int = 120

