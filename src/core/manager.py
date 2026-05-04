import json
import os
from typing import Dict, List, Optional
from .models import Profile, AppSettings
from ..utils.crypto import CryptoManager

class Manager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.profiles_file = os.path.join(self.data_dir, "profiles.json")
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.crypto = CryptoManager(os.path.join(base_dir, "master.key"))
        
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.profiles: Dict[str, Profile] = {}
        self.settings = AppSettings()
        
        self.load_settings()
        self.load_profiles()

    def load_profiles(self):
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, "r") as f:
                    data = json.load(f)
                    for name, p_data in data.items():
                        # Decrypt key if exists
                        if p_data.get("auth_key"):
                            p_data["auth_key"] = self.crypto.decrypt(p_data["auth_key"])
                        self.profiles[name] = Profile(name=name, **p_data)
            except Exception:
                pass

    def save_profiles(self):
        data = {}
        for name, profile in self.profiles.items():
            p_dict = {
                "login_server": profile.login_server,
                "auth_key": self.crypto.encrypt(profile.auth_key),
                "auth_mode": profile.auth_mode,
                "auto_connect": profile.auto_connect
            }
            data[name] = p_dict
            
        with open(self.profiles_file, "w") as f:
            json.dump(data, f, indent=4)

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
            del self.profiles[name]
            self.save_profiles()
