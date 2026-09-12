"""M22.5 endpoint tests.

1. Anonymous GET /providers returns 200 (public catalogue data, no key).
2. Anonymous POST /providers/keys returns 401.
3. Anonymous PUT /providers/config returns 401.
4. POST /providers/keys with a logged-in user stores the key and returns
   {provider_id, configured, last_four} - never the raw key.
5. GET /providers never returns a raw key value in any field.
6. User isolation: setting a key as User A does not affect User B''s state.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


def _make_client():
    """Import the FastAPI app and return a TestClient.

    Patched to use a temporary workspace directory so tests do not touch
    production data.
    """
    with tempfile.TemporaryDirectory() as tmp:
        env_patch = {
            "URI_PROVIDER_KEY_SECRET": "test_endpoint_secret_passphrase",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }
        # We need a persistent tmp dir for the duration of the test, so
        # we use a module-level temp dir created in setUpClass.
        pass
    return None


class TestProviderEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._secret = "test_secret_for_endpoints"

        # Patch user_scoped_path before importing server
        def _patched_usp(uid, fn, root=None):
            return os.path.join(cls._tmp, uid, fn)

        cls._usp_patch = patch(
            "uri_core.core.provider_keys.user_scoped_path",
            side_effect=_patched_usp,
        )
        cls._usp_patch2 = patch(
            "uri_core.core.provider_registry.user_scoped_path",
            side_effect=_patched_usp,
        )
        cls._env_patch = patch.dict(
            os.environ, {"URI_PROVIDER_KEY_SECRET": cls._secret}
        )
        cls._usp_patch.start()
        cls._usp_patch2.start()
        cls._env_patch.start()

        import uri_core.app.server as server_mod
        from uri_core.core.user_accounts import UserAccountStore
        from uri_core.core.auth_session import AuthSessionStore

        cls._server_mod = server_mod
        cls._orig_user_account_store = server_mod._user_account_store
        cls._orig_auth_session_store = server_mod._auth_session_store
        cls._orig_user_contexts = server_mod._user_contexts

        server_mod._user_account_store = UserAccountStore(
            storage_path=os.path.join(cls._tmp, "user_accounts.json")
        )
        server_mod._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(cls._tmp, "auth_sessions.json")
        )
        server_mod._user_contexts = {}

        cls._client = TestClient(server_mod.app, raise_server_exceptions=True)

    @classmethod
    def tearDownClass(cls):
        cls._usp_patch.stop()
        cls._usp_patch2.stop()
        cls._env_patch.stop()
        cls._server_mod._user_account_store = cls._orig_user_account_store
        cls._server_mod._auth_session_store = cls._orig_auth_session_store
        cls._server_mod._user_contexts = cls._orig_user_contexts
        import shutil
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def setUp(self):
        from uri_core.app import edge
        edge.reset_rate_limiters()

    def tearDown(self):
        from uri_core.app import edge
        edge.reset_rate_limiters()

    def _login(self, username: str, password: str = "Password123!") -> str:
        """Register + login a test user and return their token."""
        from uri_core.app import edge
        edge.reset_rate_limiters()
        s_resp = self._client.post(
            "/auth/signup",
            json={"username": username, "password": password},
        )
        if s_resp.status_code == 200:
            token = s_resp.json().get("token")
            if token:
                return token
        resp = self._client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        data = resp.json()
        token = data.get("token")
        if not token:
            raise RuntimeError(
                f"Failed to log in test user {username}: signup={s_resp.status_code} {s_resp.text}, login={resp.status_code} {data}"
            )
        return token

    def test_get_providers_anonymous_returns_200(self):
        """GET /providers is accessible without auth - returns catalogue."""
        resp = self._client.get("/providers")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("providers", body)
        self.assertIsInstance(body["providers"], list)

    def test_post_provider_keys_anonymous_returns_401(self):
        """Anonymous POST /providers/keys must be rejected with 401."""
        resp = self._client.post(
            "/providers/keys",
            json={"provider_id": "openai", "api_key": "sk-test-anon"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_put_provider_config_anonymous_returns_401(self):
        """Anonymous PUT /providers/config must be rejected with 401."""
        resp = self._client.put(
            "/providers/config",
            json={"provider_id": "openai", "base_url": "https://api.openai.com/v1"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_post_provider_keys_authenticated_returns_last_four_only(self):
        """A logged-in user can submit a key; response must include only
        last_four - never the raw key."""
        token = self._login("prov_user_a")
        raw_key = "sk-my-secret-key-00001234"

        resp = self._client.post(
            "/providers/keys",
            json={"provider_id": "openai", "api_key": raw_key},
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 500 and "URI_PROVIDER_KEY_SECRET" in resp.text:
            self.skipTest("URI_PROVIDER_KEY_SECRET not available in test env.")

        self.assertEqual(resp.status_code, 200, msg=resp.text)
        body = resp.json()
        self.assertEqual(body["provider_id"], "openai")
        self.assertTrue(body["configured"])
        self.assertEqual(body["last_four"], raw_key[-4:])
        # The raw key must not appear in the response
        self.assertNotIn(raw_key, json.dumps(body))

    def test_get_providers_never_returns_raw_key(self):
        """GET /providers must not include a raw key in any field for any
        provider, even after a key has been submitted."""
        token = self._login("prov_user_b")
        raw_key = "sk-super-secret-key-5678"

        # Submit a key first
        self._client.post(
            "/providers/keys",
            json={"provider_id": "openai", "api_key": raw_key},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = self._client.get(
            "/providers",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        body_str = json.dumps(resp.json())
        self.assertNotIn(
            raw_key,
            body_str,
            msg="GET /providers must never return a raw key value.",
        )

    def test_user_isolation_on_keys(self):
        """User A submitting a key must not affect User B''s configured state."""
        token_a = self._login("prov_iso_a")
        token_b = self._login("prov_iso_b")
        raw_key_a = "sk-user-a-key-xxyy"

        # User A submits a key
        self._client.post(
            "/providers/keys",
            json={"provider_id": "groq", "api_key": raw_key_a},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        # User B should see groq as NOT configured
        resp_b = self._client.get(
            "/providers",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        self.assertEqual(resp_b.status_code, 200)
        providers_b = {p["provider_id"]: p for p in resp_b.json()["providers"]}
        groq_b = providers_b.get("groq", {})
        self.assertFalse(
            groq_b.get("configured", False),
            msg="User B should not see User A''s key as configured.",
        )

    def test_active_brain_for_provider_with_no_catalogue_models_uses_config_override(
        self,
    ):
        """2026-09-12: a provider with an empty catalogue models list
        (e.g. lm_studio - "dynamic, depends on what the user has
        loaded") must use this user's own configured model override,
        never silently fall back to a hardcoded Ollama model name."""
        token = self._login("lm_studio_model_user")
        headers = {"Authorization": f"Bearer {token}"}

        self._client.put(
            "/providers/config",
            json={"provider_id": "lm_studio", "model": "my-local-model-7b"},
            headers=headers,
        )

        resp = self._client.put(
            "/providers/active-brain",
            json={"provider_id": "lm_studio"},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(
            resp.json()["active_brain"]["model"], "my-local-model-7b"
        )

    def test_active_brain_for_provider_with_no_model_anywhere_falls_back_honestly(
        self,
    ):
        """No client-supplied model, no stored config override - the
        hardcoded literal fallback is the last resort only, never the
        first one."""
        token = self._login("lm_studio_no_model_user")
        headers = {"Authorization": f"Bearer {token}"}

        resp = self._client.put(
            "/providers/active-brain",
            json={"provider_id": "lm_studio"},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["active_brain"]["model"], "qwen3:14b")


if __name__ == "__main__":
    unittest.main()
