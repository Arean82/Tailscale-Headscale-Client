import os
import base64
import hashlib
from cryptography.fernet import Fernet

class CryptoManager:
    def __init__(self, key_file):
        self.key_file = key_file
        self.key = self._get_or_create_key()
        self.fernet = Fernet(self.key)
        
        # Legacy support
        self.old_password = "some-hardcoded-passphrase"
        self.old_key = base64.urlsafe_b64encode(hashlib.sha256(self.old_password.encode()).digest())
        self.old_fernet = Fernet(self.old_key)

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
            try:
                # Fallback to old key
                return self.old_fernet.decrypt(encrypted_text.encode()).decode()
            except Exception:
                return ""
