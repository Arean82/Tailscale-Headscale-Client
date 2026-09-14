import json
import os
import shutil
import logging
from typing import Dict
from .models import Profile, AppSettings
from ..utils.crypto import (
    CryptoManager,
    store_profile_secret,
    get_profile_secret,
    delete_profile_secret
)

# Child of the app logger configured in main.py so records reach app.log
logger = logging.getLogger("TailscaleClient.Manager")

class Manager:
    """Option C Hybrid Vault Manager:
    - Profile topology & network settings persisted in SQLite (`traffic_stats.db`).
    - Sensitive credentials (auth_key) stored exclusively in OS Keyring indexed by immutable UUIDv4.
    - Application settings persisted in SQLite `app_settings` table.
    - Automatic zero-loss migration from legacy `data/` text file structures.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.tab_names_file = os.path.join(self.data_dir, "tab_names.json")
        self.settings_file = os.path.join(self.base_dir, "settings.json")
        self.crypto = CryptoManager(os.path.join(base_dir, "master.key"))
        
        from .db_manager import DatabaseManager
        self.db = DatabaseManager(base_dir)
        
        self.profiles: Dict[str, Profile] = {}
        self.settings = AppSettings()
        
        # 1. Load Settings (SQLite with legacy fallback)
        self.load_settings()
        
        # 2. Check for legacy migration before loading profiles
        self._check_and_migrate_legacy_data()
        
        # 3. Load Profiles (SQLite + OS Keyring)
        self.load_profiles()

    def _get_tab_dir(self, tab_name: str) -> str:
        """Sanitizes directory paths for legacy folder references and traversal prevention."""
        if ".." in tab_name or "/" in tab_name or "\\" in tab_name:
            raise PermissionError(f"Directory traversal attempt detected: '{tab_name}'")
        sanitized_name = "".join(c for c in tab_name if c.isalnum() or c in (' ', '.', '_', '-')).strip()
        sanitized_name = sanitized_name.replace(' ', '_')
        if not sanitized_name:
            raise ValueError(f"Invalid profile name: '{tab_name}' resolves to empty.")
            
        resolved_path = os.path.abspath(os.path.join(self.data_dir, sanitized_name))
        if not resolved_path.startswith(os.path.abspath(self.data_dir)):
            raise PermissionError(f"Directory traversal attempt detected: '{tab_name}'")
            
        return resolved_path

    def _read_file(self, path: str) -> str:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def _check_and_migrate_legacy_data(self):
        """Seamlessly migrates legacy file-based profiles and settings to SQLite + Keyring."""
        # 1. Settings migration if DB empty but settings.json exists
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    from dataclasses import fields
                    valid_fields = {field.name for field in fields(AppSettings)}
                    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
                    migrated_settings = AppSettings(**filtered_data)
                    self.db.save_app_settings(migrated_settings)
                    self.settings = migrated_settings
            except Exception as e:
                logger.error(f"Error migrating legacy settings: {e}")

        # 2. Profiles migration if SQLite profiles table is empty but tab_names_file exists
        db_count = self.db.count_profiles()
        if db_count == 0 and os.path.exists(self.tab_names_file):
            try:
                logger.info("Migrating legacy profile text files to SQLite and Keyring...")
                with open(self.tab_names_file, "r", encoding="utf-8") as f:
                    tab_names = json.load(f)
                    
                order = 0
                for tab_id, name in tab_names.items():
                    try:
                        profile_dir = self._get_tab_dir(name)
                    except Exception:
                        continue

                    if not os.path.exists(profile_dir):
                        continue

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

                    accept_routes_val = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_accept_routes"))
                    accept_routes = (accept_routes_val != "False")
                    unattended = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_unattended")) == "True"
                    webclient = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_webclient")) == "True"
                    advertise_connector = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_advertise_connector")) == "True"
                    accept_risk = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_accept_risk"))
                    extra_args = self._read_file(os.path.join(profile_dir, "Tailscale_VPN_extra_args"))

                    key = self.crypto.decrypt(enc_key)

                    migrated_prof = Profile(
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
                        hostname=hostname,
                        accept_routes=accept_routes,
                        unattended=unattended,
                        webclient=webclient,
                        advertise_connector=advertise_connector,
                        accept_risk=accept_risk,
                        extra_args=extra_args
                    )
                    
                    # Store topology in SQLite and secret in Keyring
                    self.db.save_profile(migrated_prof, tab_order=order)
                    if key:
                        store_profile_secret(migrated_prof.id, key)
                    order += 1

                # Archive legacy data directory safely to avoid re-migration
                legacy_backup = os.path.join(self.base_dir, "data_migrated_legacy")
                if not os.path.exists(legacy_backup):
                    try:
                        shutil.move(self.data_dir, legacy_backup)
                    except OSError as err:
                        logger.debug(f"Legacy backup folder move: {err}")
                logger.info(f"Successfully migrated {order} legacy profiles to Option C Hybrid Vault.")
            except Exception as e:
                logger.error(f"Error executing legacy profiles migration: {e}")

    def load_profiles(self):
        """Loads profiles from SQLite and populates secrets from OS Keyring."""
        self.profiles.clear()
        db_profiles = self.db.load_all_profiles()
        for prof in db_profiles:
            # Securely retrieve authentication key from native OS Keyring
            prof.auth_key = get_profile_secret(prof.id)
            self.profiles[prof.name] = prof

    def save_profiles(self):
        """Saves all active profiles to SQLite and stores auth keys in OS Keyring."""
        for order, (name, profile) in enumerate(self.profiles.items()):
            self.db.save_profile(profile, tab_order=order)
            if profile.auth_key:
                store_profile_secret(profile.id, profile.auth_key)
            else:
                delete_profile_secret(profile.id)

    def load_settings(self):
        """Loads settings from SQLite database with fallback to settings.json."""
        self.settings = self.db.load_app_settings()

    def save_settings(self):
        """Persists settings to SQLite database and mirrors to legacy settings.json for backward compatibility."""
        self.db.save_app_settings(self.settings)
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings.__dict__, f, indent=4)
        except OSError as err:
            logger.debug(f"Mirroring settings to legacy JSON: {err}")

    def add_profile(self, profile: Profile):
        """Adds or updates a profile in the hybrid vault."""
        self.profiles[profile.name] = profile
        self.save_profiles()

    def remove_profile(self, name: str):
        """Removes a profile from memory, SQLite database, and OS Keyring."""
        if name in self.profiles:
            prof = self.profiles[name]
            delete_profile_secret(prof.id)
            self.db.delete_profile(prof.id)
            del self.profiles[name]
            self.save_profiles()

