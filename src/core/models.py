import uuid
from dataclasses import dataclass, field
from enum import Enum


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
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
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
    force_reset: bool = False
    advertise_exit_node: bool = False
    shields_up: bool = False
    force_reauth: bool = False
    advertise_tags: str = ""
    accept_routes: bool = True
    unattended: bool = False
    webclient: bool = False
    advertise_connector: bool = False
    accept_risk: str = ""
    extra_args: str = ""

@dataclass
class AppSettings:
    auto_start: bool = False
    auto_connect: bool = False
    enable_logs: bool = False
    advanced_features: bool = False
    global_dns_fallback: bool = False
    max_tabs: int = 5
    last_profile: str | None = None
    use_local_api: bool = True
    sso_timeout: int = 120
    language: str = "en_US"
    enable_tray_switcher: bool = False
    insecure_ssl: bool = False
    startup_delay: int = 10
    check_screen_reader: bool = False


