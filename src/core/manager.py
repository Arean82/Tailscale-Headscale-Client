import json
import os
import shutil
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
        if not sanitized_name:
            raise ValueError(f"Invalid profile name: '{tab_name}' resolves to empty.")
            
        resolved_path = os.path.abspath(os.path.join(self.data_dir, sanitized_name))
        if not resolved_path.startswith(os.path.abspath(self.data_dir)):
            raise PermissionError(f"Directory traversal attempt detected: '{tab_name}'")
            
        return resolved_path

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
                        last_known_ip = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_last_known_ip"))
                        enable_dns_fallback = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_enable_dns_fallback")) == "True"
                        force_reset = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_force_reset")) == "True"
                        advertise_exit_node = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_advertise_exit_node")) == "True"
                        shields_up = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_shields_up")) == "True"
                        force_reauth = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_force_reauth")) == "True"
                        advertise_tags = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_advertise_tags"))
                        enable_ssh = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_enable_ssh")) == "True"
                        accept_dns = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_accept_dns")) == "True"
                        allow_lan = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_allow_lan")) == "True"
                        disable_snat = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_disable_snat")) == "True"
                        hostname = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_hostname"))

                        key = self.crypto.decrypt(enc_key)
                        self.profiles[name] = Profile(
                            name=name,
                            login_server=url or "https://controlplane.tailscale.com",
                            auth_key=key,
                            auth_mode=mode,
                            exit_node=exit_node,
                            routes=routes,
                            native_profile=native_profile,
                            is_native_switch=is_native_switch,
                            last_known_ip=last_known_ip,
                            enable_dns_fallback=enable_dns_fallback,
                            force_reset=force_reset,
                            advertise_exit_node=advertise_exit_node,
                            shields_up=shields_up,
                            force_reauth=force_reauth,
                            advertise_tags=advertise_tags,
                            enable_ssh=enable_ssh,
                            accept_dns=accept_dns,
                            allow_lan=allow_lan,
                            disable_snat=disable_snat,
                            hostname=hostname
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

            with open(os.path.join(profile_dir, "Tailscale_VPN_last_known_ip"), "w") as f:
                f.write(profile.last_known_ip)

            with open(os.path.join(profile_dir, "Tailscale_VPN_enable_dns_fallback"), "w") as f:
                f.write(str(profile.enable_dns_fallback))

            with open(os.path.join(profile_dir, "Tailscale_VPN_force_reset"), "w") as f:
                f.write(str(profile.force_reset))
                
            with open(os.path.join(profile_dir, "Tailscale_VPN_advertise_exit_node"), "w") as f:
                f.write(str(profile.advertise_exit_node))

            with open(os.path.join(profile_dir, "Tailscale_VPN_shields_up"), "w") as f:
                f.write(str(profile.shields_up))

            with open(os.path.join(profile_dir, "Tailscale_VPN_force_reauth"), "w") as f:
                f.write(str(profile.force_reauth))

            with open(os.path.join(profile_dir, "Tailscale_VPN_advertise_tags"), "w") as f:
                f.write(profile.advertise_tags)

            with open(os.path.join(profile_dir, "Tailscale_VPN_enable_ssh"), "w") as f:
                f.write(str(profile.enable_ssh))

            with open(os.path.join(profile_dir, "Tailscale_VPN_accept_dns"), "w") as f:
                f.write(str(profile.accept_dns))

            with open(os.path.join(profile_dir, "Tailscale_VPN_allow_lan"), "w") as f:
                f.write(str(profile.allow_lan))

            with open(os.path.join(profile_dir, "Tailscale_VPN_disable_snat"), "w") as f:
                f.write(str(profile.disable_snat))

            with open(os.path.join(profile_dir, "Tailscale_VPN_hostname"), "w") as f:
                f.write(profile.hostname)

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    from dataclasses import fields
                    valid_fields = {field.name for field in fields(AppSettings)}
                    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                    self.settings = AppSettings(**filtered_data)
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
            profile_dir = self._get_tab_dir(name)
            try:
                if os.path.exists(profile_dir):
                    shutil.rmtree(profile_dir, ignore_errors=True)
            except Exception:
                pass

            del self.profiles[name]
            self.save_profiles()
