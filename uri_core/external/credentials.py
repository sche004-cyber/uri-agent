"""M33.1: Isolated per-user external credential store for Connected Services and Skills.

Stores API keys and tokens strictly scoped per user under `portable_paths.user_scoped_path`.
Credentials are never logged, never returned in public descriptor summaries,
and never mixed with model provider keys.
Writes are atomic (temp-file in the same directory + os.replace).

Security contract (matches uri_core.core.provider_keys's existing, established
policy for this exact class of secret - API keys and tokens - applied here
independently, with its own env secret and salt, so a leaked provider-key
secret and a leaked external-credential secret are not the same failure):
  - Each service_or_capability_id's secret_data is JSON-serialized then
    encrypted with Fernet (AES-128-CBC + HMAC) before being written to disk.
    The raw secret is NEVER written as plaintext.
  - The Fernet key is derived from URI_EXTERNAL_CREDENTIAL_SECRET (env var)
    via PBKDF2-HMAC-SHA256. Raises ValueError at construction if unset, so
    callers fail loudly rather than silently storing credentials with no
    encryption.
  - Corrupt ciphertext or a secret mismatch decrypts to nothing (treated as
    "no credential"), never raises past this module and never leaks
    ciphertext or exception detail to a caller.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from typing import Any, Dict, Mapping, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from uri_core.core.portable_paths import DEFAULT_USER_STATE_ROOT, user_scoped_path

CREDENTIALS_FILENAME = "external_credentials.json"

# Fixed salt - deterministic derivation so the same secret always produces
# the same Fernet key for a given installation. Distinct from provider_keys.
# py's own salt so the two secret domains never share derived key material.
_PBKDF2_SALT = b"uri_external_credential_store_v1"
_PBKDF2_ITERATIONS = 100_000
_SECRET_ENV_VAR = "URI_EXTERNAL_CREDENTIAL_SECRET"


def _derive_fernet(secret: str) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_PBKDF2_SALT,
        iterations=_PBKDF2_ITERATIONS,
    )
    key_bytes = kdf.derive(secret.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def _atomic_write_json(path: str, data: Mapping[str, Any]) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-cred-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


class ExternalCredentialStore:
    """Per-user secure external credential store.
    user_id must be a validated UUID or user identifier conforming to user_scoped_path.

    Raises ValueError at construction time if URI_EXTERNAL_CREDENTIAL_SECRET
    is not set, so callers fail loudly rather than silently storing secrets
    with no encryption (mirrors ProviderKeyStore's identical contract).
    """

    def __init__(self, *, root: str = DEFAULT_USER_STATE_ROOT):
        self.root = root
        secret = os.environ.get(_SECRET_ENV_VAR, "")
        if not secret:
            raise ValueError(
                f"{_SECRET_ENV_VAR} environment variable must be set "
                "before ExternalCredentialStore can be used."
            )
        self._fernet = _derive_fernet(secret)
        del secret

    def _path(self, user_id: str) -> str:
        return user_scoped_path(user_id, CREDENTIALS_FILENAME, root=self.root)

    def _load(self, user_id: str) -> Dict[str, Any]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _decrypt_entry(self, ciphertext: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(ciphertext, str):
            return None
        try:
            raw = self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
            decoded = json.loads(raw)
            return decoded if isinstance(decoded, dict) else None
        except (InvalidToken, ValueError, json.JSONDecodeError):
            # Wrong secret, or corrupted ciphertext - treated as absent
            # rather than leaking ciphertext or exception detail.
            return None

    def _save(self, user_id: str, data: Mapping[str, Any]) -> None:
        _atomic_write_json(self._path(user_id), data)

    def set_credential(
        self,
        user_id: str,
        service_or_capability_id: str,
        secret_data: Mapping[str, Any],
    ) -> None:
        encrypted = self._fernet.encrypt(
            json.dumps(dict(secret_data)).encode("utf-8")
        ).decode("ascii")
        data = self._load(user_id)
        data[service_or_capability_id] = encrypted
        self._save(user_id, data)

    def get_credential(
        self,
        user_id: str,
        service_or_capability_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self._decrypt_entry(self._load(user_id).get(service_or_capability_id))

    def has_credential(self, user_id: str, service_or_capability_id: str) -> bool:
        return service_or_capability_id in self._load(user_id)

    def delete_credential(
        self,
        user_id: str,
        service_or_capability_id: str,
    ) -> bool:
        data = self._load(user_id)
        if service_or_capability_id in data:
            del data[service_or_capability_id]
            self._save(user_id, data)
            return True
        return False
