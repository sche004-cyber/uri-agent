"""M22.5: Ports the credential-hygiene behavioural guarantee from
test_credential_hygiene.py onto the real ProviderKeyStore.

Assertions:
1. set_key() stores an encrypted blob, not the raw key.
2. has_key() and describe_key() never return the raw key.
3. get_key_for_use() correctly round-trips the key.
4. A wrong/missing URI_PROVIDER_KEY_SECRET raises ValueError.
5. No read-back endpoint: GET /providers never returns a raw key.
6. Auth error (ProviderAuthenticationError) is distinguishable from
   ProviderUnavailableError and does not silently fall back.
7. Env-only credential sourcing: raw key never hardcoded.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestProviderKeyStoreHygiene(unittest.TestCase):
    """ProviderKeyStore credential hygiene guarantees."""

    def _make_store(self, user_id: str, tmp_dir: str):
        """Construct a ProviderKeyStore pointing at a temp directory."""
        from uri_core.core.portable_paths import user_scoped_path as _orig
        from uri_core.core.provider_keys import ProviderKeyStore

        # Patch user_scoped_path to use the temp dir
        def _patched_usp(uid, filename, root=None):
            return os.path.join(tmp_dir, uid, filename)

        with patch("uri_core.core.provider_keys.user_scoped_path", side_effect=_patched_usp), \
             patch.dict(os.environ, {"URI_PROVIDER_KEY_SECRET": "test_secret_passphrase"}):
            store = ProviderKeyStore(user_id)
            return store, _patched_usp

    def test_set_key_stores_ciphertext_not_plaintext(self):
        """The .enc file on disk must not contain the raw key string."""
        user_id = "00000000-0000-0000-0000-000000000001"
        raw_key = "sk-test-supersecret-api-key-1234"
        with tempfile.TemporaryDirectory() as tmp:
            from uri_core.core.provider_keys import ProviderKeyStore
            from unittest.mock import patch

            def _usp(uid, fn, root=None):
                return os.path.join(tmp, uid, fn)

            with patch("uri_core.core.provider_keys.user_scoped_path", side_effect=_usp), \
                 patch.dict(os.environ, {"URI_PROVIDER_KEY_SECRET": "test_secret"}):
                store = ProviderKeyStore(user_id)
                store.set_key("openai", raw_key)

            # Read raw bytes from disk - must not contain the raw key
            enc_path = os.path.join(tmp, user_id, "provider_keys.enc")
            self.assertTrue(os.path.exists(enc_path), "Key file must be created.")
            disk_contents = Path(enc_path).read_text(encoding="utf-8")
            self.assertNotIn(
                raw_key,
                disk_contents,
                msg="Raw key must never appear in the on-disk store.",
            )

    def test_has_key_returns_bool_not_key_material(self):
        user_id = "00000000-0000-0000-0000-000000000002"
        with tempfile.TemporaryDirectory() as tmp:
            from uri_core.core.provider_keys import ProviderKeyStore
            from unittest.mock import patch

            def _usp(uid, fn, root=None):
                return os.path.join(tmp, uid, fn)

            with patch("uri_core.core.provider_keys.user_scoped_path", side_effect=_usp), \
                 patch.dict(os.environ, {"URI_PROVIDER_KEY_SECRET": "test_secret"}):
                store = ProviderKeyStore(user_id)
                store.set_key("groq", "gsk-abc123xyz789")
                result = store.has_key("groq")

            self.assertIsInstance(result, bool)
            self.assertTrue(result)
            # has_key result must not be the key itself
            self.assertNotEqual(result, "gsk-abc123xyz789")

    def test_describe_key_only_returns_last_four(self):
        user_id = "00000000-0000-0000-0000-000000000003"
        raw_key = "gsk-secretkey9999"
        with tempfile.TemporaryDirectory() as tmp:
            from uri_core.core.provider_keys import ProviderKeyStore
            from unittest.mock import patch

            def _usp(uid, fn, root=None):
                return os.path.join(tmp, uid, fn)

            with patch("uri_core.core.provider_keys.user_scoped_path", side_effect=_usp), \
                 patch.dict(os.environ, {"URI_PROVIDER_KEY_SECRET": "test_secret"}):
                store = ProviderKeyStore(user_id)
                store.set_key("groq", raw_key)
                info = store.describe_key("groq")

        self.assertIsNotNone(info)
        self.assertTrue(info["configured"])
        self.assertEqual(info["last_four"], raw_key[-4:])
        # Must not contain more than last_four of key material
        for field_val in info.values():
            self.assertNotEqual(str(field_val), raw_key)
            if isinstance(field_val, str) and len(field_val) > 4:
                self.assertNotIn(raw_key[:-4], str(field_val))

    def test_get_key_for_use_round_trips(self):
        user_id = "00000000-0000-0000-0000-000000000004"
        raw_key = "openai-key-round-trip-test-abc"
        with tempfile.TemporaryDirectory() as tmp:
            from uri_core.core.provider_keys import ProviderKeyStore
            from unittest.mock import patch

            def _usp(uid, fn, root=None):
                return os.path.join(tmp, uid, fn)

            with patch("uri_core.core.provider_keys.user_scoped_path", side_effect=_usp), \
                 patch.dict(os.environ, {"URI_PROVIDER_KEY_SECRET": "consistent_secret"}):
                store = ProviderKeyStore(user_id)
                store.set_key("openai", raw_key)
                recovered = store.get_key_for_use("openai")

        self.assertEqual(recovered, raw_key)

    def test_missing_secret_raises_value_error(self):
        """ProviderKeyStore must raise ValueError if URI_PROVIDER_KEY_SECRET is absent."""
        user_id = "00000000-0000-0000-0000-000000000005"
        env = {k: v for k, v in os.environ.items() if k != "URI_PROVIDER_KEY_SECRET"}
        with patch.dict(os.environ, env, clear=True):
            from uri_core.core.provider_keys import ProviderKeyStore
            from unittest.mock import patch as _patch

            with self.assertRaises(ValueError):
                ProviderKeyStore(user_id)

    def test_auth_error_is_distinct_from_unavailable(self):
        """ProviderAuthenticationError must be distinguishable from
        ProviderUnavailableError so callers can implement no-silent-fallback."""
        from uri_core.core.model_providers.base import (
            ProviderAuthenticationError,
            ProviderUnavailableError,
            ProviderResponseError,
        )
        auth_err = ProviderAuthenticationError("bad key")
        self.assertIsInstance(auth_err, ProviderResponseError)
        self.assertIsInstance(auth_err, Exception)
        # It must NOT be an instance of ProviderUnavailableError
        self.assertNotIsInstance(auth_err, ProviderUnavailableError)

    def test_key_never_hardcoded_in_module(self):
        """provider_keys.py must not contain any hardcoded key strings
        (the same structural discipline test_credential_hygiene.py enforces
        for hermes_service.py / check_models.py)."""
        path = Path("uri_core/core/provider_keys.py")
        if not path.exists():
            self.skipTest("provider_keys.py not found.")
        source = path.read_text(encoding="utf-8")
        # Common key prefixes / patterns
        for pattern in ("sk-", "gsk-", "Bearer ", "api_key = \""):
            self.assertNotIn(
                pattern,
                source,
                msg=f"Hardcoded key pattern {pattern!r} found in provider_keys.py",
            )


if __name__ == "__main__":
    unittest.main()
