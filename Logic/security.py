# logic/security.py
# Secure encryption key management

import base64
import hashlib
import os
from cryptography.fernet import Fernet
from logic.logger import app_logger

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    app_logger.warning("keyring module not available. Using fallback encryption.")


class KeyManager:
    """Manages secure encryption keys with keyring support."""
    
    def __init__(self, service_name="tailscale_vpn_client", key_name="encryption_key"):
        self.service_name = service_name
        self.key_name = key_name
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize the Fernet cipher with a secure key."""
        key = self._get_or_create_key()
        self._fernet = Fernet(key)
    
    def _get_or_create_key(self):
        """Get existing key or create a new one securely."""
        key = None
        
        # Try to get from keyring first
        if KEYRING_AVAILABLE:
            try:
                key_str = keyring.get_password(self.service_name, self.key_name)
                if key_str:
                    key = key_str.encode()
                    app_logger.debug("Encryption key loaded from system keyring")
            except Exception as e:
                app_logger.error(f"Failed to load key from keyring: {e}")
        
        # Fallback to file-based storage
        if not key:
            key_file = os.path.join(os.path.expanduser("~"), ".tailscale_vpn_key")
            if os.path.exists(key_file):
                try:
                    with open(key_file, 'rb') as f:
                        key = f.read()
                    app_logger.debug("Encryption key loaded from file")
                except Exception as e:
                    app_logger.error(f"Failed to load key from file: {e}")
        
        # Create new key if none exists
        if not key:
            key = Fernet.generate_key()
            self._save_key(key)
            app_logger.info("New encryption key generated")
        
        return key
    
    def _save_key(self, key):
        """Save encryption key securely."""
        # Try keyring first
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.service_name, self.key_name, key.decode())
                app_logger.debug("Encryption key saved to system keyring")
                return
            except Exception as e:
                app_logger.error(f"Failed to save key to keyring: {e}")
        
        # Fallback to file
        key_file = os.path.join(os.path.expanduser("~"), ".tailscale_vpn_key")
        try:
            # Set restrictive permissions on Unix-like systems
            if os.name == 'posix':
                old_umask = os.umask(0o077)
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            if os.name == 'posix':
                os.umask(old_umask)
                os.chmod(key_file, 0o600)
            
            app_logger.debug("Encryption key saved to file with restricted permissions")
        except Exception as e:
            app_logger.error(f"Failed to save encryption key: {e}")
            raise
    
    def encrypt(self, plain_text):
        """Encrypt plain text."""
        if not plain_text:
            return ""
        try:
            return self._fernet.encrypt(plain_text.encode()).decode()
        except Exception as e:
            app_logger.error(f"Encryption failed: {e}")
            return ""
    
    def decrypt(self, encrypted_text):
        """Decrypt encrypted text."""
        if not encrypted_text:
            return ""
        try:
            return self._fernet.decrypt(encrypted_text.encode()).decode()
        except Exception as e:
            app_logger.error(f"Decryption failed: {e}")
            return ""


# Global key manager instance
_key_manager = None

def get_key_manager():
    """Get or create the global key manager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager