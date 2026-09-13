import os
from cryptography.fernet import Fernet

class CryptoManager:
    def __init__(self, key_file):
        self.key_file = key_file
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)

    def _get_or_create_key(self):
        try:
            import keyring
            stored_key = keyring.get_password("TailscaleClientPro", "MasterEncryptionKey")
            if stored_key:
                return stored_key.encode('utf-8')
        except Exception:
            pass
            
        # Fallback to local key file check
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "rb") as f:
                    key = f.read()
                    # Try to migrate local key to secure Keyring
                    try:
                        import keyring
                        keyring.set_password("TailscaleClientPro", "MasterEncryptionKey", key.decode('utf-8'))
                    except Exception:
                        pass
                    return key
            except Exception:
                pass
        
        # Generate new key
        new_key = Fernet.generate_key()
        
        # Try to save to Keyring securely
        try:
            import keyring
            keyring.set_password("TailscaleClientPro", "MasterEncryptionKey", new_key.decode('utf-8'))
        except Exception:
            pass
            
        # Write to local file as robust fallback
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        with open(self.key_file, "wb") as f:
            f.write(new_key)
        return new_key

    def encrypt(self, text):
        if not text:
            return ""
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text:
            return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            return ""

KEYRING_SERVICE = "TailscaleClientPro"

def store_profile_secret(profile_id: str, secret: str) -> None:
    """Stores sensitive profile authentication key in OS Keyring."""
    if not profile_id:
        return
    try:
        import keyring
        username = f"auth_key_{profile_id}"
        if secret:
            keyring.set_password(KEYRING_SERVICE, username, secret)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, username)
            except Exception:
                pass
    except Exception:
        pass

def get_profile_secret(profile_id: str) -> str:
    """Retrieves sensitive profile authentication key from OS Keyring."""
    if not profile_id:
        return ""
    try:
        import keyring
        username = f"auth_key_{profile_id}"
        secret = keyring.get_password(KEYRING_SERVICE, username)
        return secret or ""
    except Exception:
        return ""

def delete_profile_secret(profile_id: str) -> None:
    """Deletes sensitive profile authentication key from OS Keyring."""
    if not profile_id:
        return
    try:
        import keyring
        username = f"auth_key_{profile_id}"
        try:
            keyring.delete_password(KEYRING_SERVICE, username)
        except Exception:
            pass
    except Exception:
        pass

