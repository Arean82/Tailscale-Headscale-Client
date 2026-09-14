# src/utils/crypto.py
"""Secret Store & Credential Vault Adapter.

Provides an explicit adapter for hardware-backed OS Keyring credential storage
(Option C Hybrid Vault). Eliminates vestigial master.key generation and silent
credential dropping (Candidate 3).
"""

import logging

logger = logging.getLogger("TailscaleClient.Crypto")

KEYRING_SERVICE = "TailscaleClientPro"

# Pluggable backend override (used for hermetic unit testing without touching OS Credential Store)
_custom_backend = None


def set_secret_backend(backend):
    """Overrides the active secret store backend (e.g. dict-based mock for testing)."""
    global _custom_backend  # noqa: PLW0603 (backend swap is the documented hermetic-test seam)
    _custom_backend = backend


def get_secret_backend():
    """Returns the current backend or None (native OS keyring)."""
    return _custom_backend


def store_profile_secret(profile_id: str, secret: str) -> bool:
    """Stores sensitive profile authentication key in the secret store.

    Returns:
        True if successfully saved or removed.
        False if backend was unavailable or operation failed.
    """
    if not profile_id:
        return False

    if _custom_backend is not None:
        try:
            username = f"auth_key_{profile_id}"
            if secret:
                _custom_backend[username] = secret
            else:
                _custom_backend.pop(username, None)
            return True
        except (KeyError, TypeError) as e:
            logger.error(f"Custom secret backend store failed for {profile_id}: {e}")
            return False

    try:
        import keyring
    except ImportError as e:
        logger.warning(
            f"OS Keyring package unavailable; failed to store credentials for profile {profile_id}: {e}"
        )
        return False

    try:
        username = f"auth_key_{profile_id}"
        if secret:
            keyring.set_password(KEYRING_SERVICE, username, secret)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, username)
            except keyring.errors.KeyringError as e:
                logger.debug(f"Keyring entry removal skipped for {profile_id}: {e}")
        return True
    except keyring.errors.KeyringError as e:
        logger.warning(
            f"OS Keyring unavailable; failed to store credentials for profile {profile_id}: {e}"
        )
        return False


def get_profile_secret(profile_id: str) -> str | None:
    """Retrieves sensitive profile authentication key from the secret store.

    Returns:
        str: Secret key if found, or "" if no secret is set.
        None: If the secret store backend is unavailable or encounters an error.
    """
    if not profile_id:
        return ""

    if _custom_backend is not None:
        try:
            username = f"auth_key_{profile_id}"
            return _custom_backend.get(username, "")
        except (KeyError, TypeError) as e:
            logger.error(f"Custom secret backend get failed for {profile_id}: {e}")
            return None

    try:
        import keyring
    except ImportError as e:
        logger.warning(
            f"OS Keyring package unavailable; failed to retrieve credentials for profile {profile_id}: {e}"
        )
        return None

    try:
        username = f"auth_key_{profile_id}"
        secret = keyring.get_password(KEYRING_SERVICE, username)
        return secret or ""
    except keyring.errors.KeyringError as e:
        logger.warning(
            f"OS Keyring unavailable; failed to retrieve credentials for profile {profile_id}: {e}"
        )
        return None


def delete_profile_secret(profile_id: str) -> bool:
    """Deletes sensitive profile authentication key from the secret store.

    Returns True if successfully deleted or already absent, False on error.
    """
    if not profile_id:
        return False

    if _custom_backend is not None:
        try:
            username = f"auth_key_{profile_id}"
            _custom_backend.pop(username, None)
            return True
        except (KeyError, TypeError) as e:
            logger.error(f"Custom secret backend delete failed for {profile_id}: {e}")
            return False

    try:
        import keyring
    except ImportError as e:
        logger.warning(
            f"OS Keyring package unavailable; failed to delete credentials for profile {profile_id}: {e}"
        )
        return False

    try:
        username = f"auth_key_{profile_id}"
        try:
            keyring.delete_password(KEYRING_SERVICE, username)
        except keyring.errors.KeyringError as e:
            logger.debug(f"Keyring entry removal skipped for {profile_id}: {e}")
        return True
    except keyring.errors.KeyringError as e:
        logger.warning(
            f"OS Keyring unavailable; failed to delete credentials for profile {profile_id}: {e}"
        )
        return False


def _legacy_plaintext_or_drop(text: str) -> str:
    """Resolves a legacy key value when no usable master.key can decrypt it.

    Fernet tokens always start with 'gAAAA', so that prefix identifies
    ciphertext: without its master.key it is unrecoverable and must be dropped
    loudly instead of being installed as a raw auth key. Anything else is
    treated as a plaintext legacy key.
    """
    if text.startswith("gAAAA"):
        logger.warning(
            "Legacy encrypted key detected (Fernet format) but master.key is unavailable; "
            "dropping un-decryptable ciphertext to avoid storing raw ciphertext as key."
        )
        return ""
    return text


def decrypt_legacy_key(encrypted_text: str, key_file_path: str | None = None) -> str:
    """One-time helper for legacy migration: decrypts a key using an existing master.key file."""
    if not encrypted_text:
        return ""
    if not key_file_path:
        return _legacy_plaintext_or_drop(encrypted_text)

    import os

    from cryptography.fernet import Fernet, InvalidToken
    if not os.path.exists(key_file_path):
        return _legacy_plaintext_or_drop(encrypted_text)

    try:
        with open(key_file_path, "rb") as f:
            key = f.read()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_text.encode()).decode()
    except InvalidToken as e:
        # Value is not decryptable with this key — most likely a plaintext
        # legacy key coexisting with a regenerated master.key.
        logger.warning(f"Legacy key not decryptable with master.key ({e}); treating as plaintext.")
        return _legacy_plaintext_or_drop(encrypted_text)
    except (OSError, ValueError) as e:
        logger.warning(f"Legacy key decryption fallback failed: {e}")
        return ""


