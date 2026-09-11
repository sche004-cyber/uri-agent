"""M22.5: Encrypted-at-rest per-user provider key store.

Security contract (non-negotiable):
  - Keys are encrypted with Fernet (AES-128-CBC + HMAC) before being
    written to disk.  The raw key string is NEVER written as plaintext.
  - The Fernet encryption key is derived from URI_PROVIDER_KEY_SECRET
    (env var) via PBKDF2-HMAC-SHA256.  The env var is read once at
    construction time; its value is not retained after key derivation.
  - get_key_for_use() is the ONLY function that ever decrypts and returns
    the raw key.  It exists solely to be called by build_provider() in
    config/model_roles.py at the moment of provider construction.  The
    decrypted value MUST NOT be cached, stored, logged, or returned
    across any API or process boundary.
  - No read-back API endpoint wires to this module.  describe_key()
    returns only {configured: bool, last_four: str}.
  - This module MUST NOT be imported by prompt-assembly modules:
    provider_semantic_interpreter.py, model_reasoning_adapter.py,
    response_drafting.py, document_composer.py.
    (Enforced by test_provider_keys_boundary.py / invariant #4.)
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from uri_core.core.portable_paths import user_scoped_path

# Fixed salt - deterministic derivation so the same secret always
# produces the same Fernet key for a given installation.  Never stored
# alongside the ciphertext.
_PBKDF2_SALT = b"uri_provider_key_store_v1"
_PBKDF2_ITERATIONS = 100_000
_KEY_FILENAME = "provider_keys.enc"


def _derive_fernet(secret: str) -> Fernet:
    """Derive a Fernet key from a passphrase via PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_PBKDF2_SALT,
        iterations=_PBKDF2_ITERATIONS,
    )
    key_bytes = kdf.derive(secret.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(key_bytes))


class ProviderKeyStore:
    """Per-user encrypted provider key store.

    Instantiate with the authenticated user''s user_id.  One instance
    should be constructed per request; it should not be cached at the
    application level.

    Raises ValueError at construction time if URI_PROVIDER_KEY_SECRET
    is not set, so callers fail loudly rather than silently storing keys
    with no encryption.
    """

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._path = Path(user_scoped_path(user_id, _KEY_FILENAME))
        secret = os.environ.get("URI_PROVIDER_KEY_SECRET", "")
        if not secret:
            raise ValueError(
                "URI_PROVIDER_KEY_SECRET environment variable must be set "
                "before ProviderKeyStore can be used."
            )
        self._fernet = _derive_fernet(secret)
        # Erase the reference immediately - do not retain the secret.
        del secret

    # ------------------------------------------------------------------
    # Write path (the only path that accepts a raw key)
    # ------------------------------------------------------------------

    def set_key(self, provider_id: str, raw_key: str) -> None:
        """Encrypt and persist raw_key for provider_id.

        raw_key is erased from local scope as soon as it is encrypted.
        This is the ONLY write path; there is no append, no update-in-
        place, and no plaintext write step.
        """
        encrypted = self._fernet.encrypt(raw_key.encode("utf-8")).decode("ascii")
        last_four = raw_key[-4:] if len(raw_key) >= 4 else "****"
        # Erase the raw key from this scope now that it is encrypted.
        raw_key = ""  # noqa: S105 - intentional zeroing

        store = self._load_store()
        store[provider_id] = {
            "enc": encrypted,
            "last_four": last_four,
        }
        self._save_store(store)

    # ------------------------------------------------------------------
    # Read paths (never return the raw key except get_key_for_use)
    # ------------------------------------------------------------------

    def has_key(self, provider_id: str) -> bool:
        """True if an encrypted key exists for this provider."""
        return provider_id in self._load_store()

    def describe_key(self, provider_id: str) -> Optional[Dict]:
        """Returns {configured: bool, last_four: str} or None.

        Never returns the encrypted ciphertext or any derivable subset
        of the key.
        """
        store = self._load_store()
        if provider_id not in store:
            return None
        return {
            "configured": True,
            "last_four": store[provider_id].get("last_four", "****"),
        }

    def get_key_for_use(self, provider_id: str) -> Optional[str]:
        """Decrypt and return the raw key for immediate use by build_provider.

        CALLER CONTRACT: the returned string must be consumed immediately
        to construct a ModelProvider, and must not be:
          - stored in any variable that outlives the request scope
          - cached on any application-level object
          - logged, audited, or included in any response
          - returned across any HTTP or IPC boundary

        Returns None if no key has been stored for this provider.
        """
        store = self._load_store()
        if provider_id not in store:
            return None
        try:
            raw = self._fernet.decrypt(
                store[provider_id]["enc"].encode("ascii")
            ).decode("utf-8")
            return raw
        except (InvalidToken, KeyError, ValueError):
            # Decryption failure - key was written with a different secret,
            # or the file was corrupted.  Return None so the caller can
            # surface an explicit "key not usable" error rather than leaking
            # exception details.
            return None

    # ------------------------------------------------------------------
    # Internal persistence helpers
    # ------------------------------------------------------------------

    def _load_store(self) -> Dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_store(self, store: Dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(self._path) + ".tmp"
        Path(tmp).write_text(json.dumps(store), encoding="utf-8")
        Path(tmp).replace(self._path)
