from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Profile:
    name: str
    login_server: str = "https://controlplane.tailscale.com"
    auth_key: str = ""
    auth_mode: str = "auth_key"  # "auth_key" or "sso"
    auto_connect: bool = False

@dataclass
class AppSettings:
    auto_start: bool = False
    auto_connect: bool = False
    enable_logs: bool = False
    max_tabs: int = 5
    last_profile: Optional[str] = None

