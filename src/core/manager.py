import json
import os
from typing import Dict, List, Optional
from .models import Profile, AppSettings
from ..utils.crypto import CryptoManager

class Manager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.tab_names_file = os.path.join(self.data_dir, "tab_names.json")
        self.settings_file = os.path.join(self.base_dir, "settings.json") # Legacy has it in base_dir
        self.crypto = CryptoManager(os.path.join(base_dir, "master.key"))
        
        from .db_manager import DatabaseManager
        self.db = DatabaseManager(base_dir)
        
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.profiles: Dict[str, Profile] = {}
        self.settings = AppSettings()
        
        self.load_settings()
        self.load_profiles()

    def _get_tab_dir(self, tab_name):
        sanitized_name = "".join(c for c in tab_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        sanitized_name = sanitized_name.replace(' ', '_')
        return os.path.join(self.data_dir, sanitized_name)

    def _read_file(self, path):
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return ""

    def load_profiles(self):
        if os.path.exists(self.tab_names_file):
            try:
                with open(self.tab_names_file, "r") as f:
                    tab_names = json.load(f)
                    for tab_id, name in tab_names.items():
                        profile_dir = self._get_tab_dir(name)
                        url = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_url"))
                        enc_key = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_key"))
                        mode = self._read_file(os.path.join(profile_dir, "auth_mode")) or "auth_key"
                        exit_node = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_exit_node"))
                        routes = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_routes"))
                        native_profile = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_native_profile"))
                        is_native_switch = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_is_native_switch")) == "True"
                        
                        key = self.crypto.decrypt(enc_key)
                        self.profiles[name] = Profile(
                            name=name,
                            login_server=url or "https://controlplane.tailscale.com",
                            auth_key=key,
                            auth_mode=mode,
                            exit_node=exit_node,
                            routes=routes,
                            native_profile=native_profile,
                            is_native_switch=is_native_switch
                        )
            except Exception:
                pass

    def save_profiles(self):
        # Save tab_names.json
        tab_names = {str(i+1): name for i, name in enumerate(self.profiles.keys())}
        with open(self.tab_names_file, "w") as f:
            json.dump(tab_names, f, indent=4)
            
        # Save individual profile files
        for name, profile in self.profiles.items():
            profile_dir = self._get_tab_dir(name)
            os.makedirs(profile_dir, exist_ok=True)
            
            with open(os.path.join(profile_dir, "Tailscale_VPN_url"), "w") as f:
                f.write(profile.login_server)
            
            with open(os.path.join(profile_dir, "Tailscale_VPN_key"), "w") as f:
                f.write(self.crypto.encrypt(profile.auth_key))
                
            with open(os.path.join(profile_dir, "auth_mode"), "w") as f:
                f.write(profile.auth_mode)

            with open(os.path.join(profile_dir, "Tailscale_VPN_exit_node"), "w") as f:
                f.write(profile.exit_node)

            with open(os.path.join(profile_dir, "Tailscale_VPN_routes"), "w") as f:
                f.write(profile.routes)

            with open(os.path.join(profile_dir, "Tailscale_VPN_native_profile"), "w") as f:
                f.write(profile.native_profile)

            with open(os.path.join(profile_dir, "Tailscale_VPN_is_native_switch"), "w") as f:
                f.write(str(profile.is_native_switch))

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.settings = AppSettings(**data)
            except Exception:
                pass

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            json.dump(self.settings.__dict__, f, indent=4)

    def add_profile(self, profile: Profile):
        self.profiles[profile.name] = profile
        self.save_profiles()

    def remove_profile(self, name: str):
        if name in self.profiles:
            # Optionally remove the directory (legacy does this if empty)
            profile_dir = self._get_tab_dir(name)
            try:
                if os.path.exists(profile_dir):
                    # Remove files first
                    for f in ["Tailscale_VPN_url", "Tailscale_VPN_key", "auth_mode"]:
                        p = os.path.join(profile_dir, f)
                        if os.path.exists(p): os.remove(p)
                    if not os.listdir(profile_dir):
                        os.rmdir(profile_dir)
            except Exception:
                pass
                
            del self.profiles[name]
            self.save_profiles()
