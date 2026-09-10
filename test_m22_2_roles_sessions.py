"""M22.2: roles, accounts, durable sessions - HTTP-level integration
tests over real FastAPI TestClient calls (same setUp discipline as
test_multi_user_isolation.py), covering exactly the acceptance criteria
in URI_M22_ARCHITECTURE.md's M22.2 milestone entry:

    - first-account-becomes-ADMIN bootstrap, every later signup USER
    - a server "restart" (a fresh AuthSessionStore pointed at the same
      persisted file) no longer invalidates a still-valid session
    - experience_tier is user-editable via the caller's OWN account
      only, and is a zero-authority preference
    - device listing/revocation is self-scoped per user
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import ROLE_ADMIN, ROLE_USER, UserAccountStore


class RolesSessionsTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts
        self._original_user_state_root = server._USER_STATE_ROOT

        self.accounts_path = os.path.join(
            self.temp_dir.name, "user_accounts.json"
        )
        self.sessions_path = os.path.join(
            self.temp_dir.name, "auth_sessions.json"
        )

        server._user_account_store = UserAccountStore(
            storage_path=self.accounts_path
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=self.sessions_path
        )
        server._user_contexts = {}
        server._USER_STATE_ROOT = os.path.join(self.temp_dir.name, "users")

        # M22.3: several accounts are signed up per test method here,
        # all from TestClient's single fixed fake client host - without
        # a reset, the module-level rate limiter (shared process state,
        # keyed by client IP - see edge.py) would otherwise carry a
        # count across every test in this file (and every other test
        # module run in the same process), tripping on a later,
        # legitimate call.
        edge.reset_rate_limiters()

        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        server._USER_STATE_ROOT = self._original_user_state_root
        edge.reset_rate_limiters()

    def _signup(self, username, password="correct-horse-1", device_id=None):
        payload = {"username": username, "password": password}
        if device_id is not None:
            payload["device_id"] = device_id
        response = self.client.post("/auth/signup", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------
    # Bootstrap: first account -> ADMIN, everyone else -> USER.
    # ------------------------------------------------------------

    def test_first_account_becomes_admin(self):
        alice = self._signup("bootstrap-alice")

        me = self.client.get("/auth/me", headers=self._auth(alice["token"]))

        self.assertEqual(me.json()["role"], ROLE_ADMIN)

    def test_second_account_becomes_ordinary_user(self):
        self._signup("bootstrap-alice2")
        bob = self._signup("bootstrap-bob2")

        me = self.client.get("/auth/me", headers=self._auth(bob["token"]))

        self.assertEqual(me.json()["role"], ROLE_USER)

    def test_exactly_one_account_ever_holds_admin_across_several_signups(
        self,
    ):
        # This test's own point is 5 real signups in a row, past the
        # M22.3 signup rate limit (3/300s/IP - see edge.py) that every
        # other test in this class stays comfortably under. Resetting
        # before EACH signup (not just once before the loop) is what's
        # actually needed - the limit is 3 per window, so 5 signups in
        # a row would still trip it after a single upfront reset.
        # Resetting per call (rather than raising the limit or
        # exempting this test's IP) keeps the limiter's real threshold
        # intact and unweakened everywhere else, including production.
        tokens = []
        for i in range(5):
            edge.reset_rate_limiters()
            tokens.append(self._signup(f"bootstrap-many-{i}")["token"])

        roles = [
            self.client.get("/auth/me", headers=self._auth(t)).json()[
                "role"
            ]
            for t in tokens
        ]

        self.assertEqual(roles.count(ROLE_ADMIN), 1)
        self.assertEqual(roles.count(ROLE_USER), 4)
        self.assertEqual(roles[0], ROLE_ADMIN)

    # ------------------------------------------------------------
    # Durable sessions: a "restart" does not invalidate a live token.
    # ------------------------------------------------------------

    def test_session_survives_a_fresh_auth_session_store_instance(self):
        alice = self._signup("durable-alice")

        # Simulate a server restart: a brand-new AuthSessionStore
        # instance pointed at the same on-disk file, exactly as a real
        # process restart would construct.
        server._auth_session_store = AuthSessionStore(
            storage_path=self.sessions_path
        )

        me = self.client.get("/auth/me", headers=self._auth(alice["token"]))

        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.json()["authenticated"])
        self.assertEqual(me.json()["user_id"], alice["user_id"])

    def test_role_survives_a_fresh_user_account_store_instance(self):
        alice = self._signup("durable-role-alice")

        server._user_account_store = UserAccountStore(
            storage_path=self.accounts_path
        )

        me = self.client.get("/auth/me", headers=self._auth(alice["token"]))

        self.assertEqual(me.json()["role"], ROLE_ADMIN)

    # ------------------------------------------------------------
    # experience_tier: self-scoped, zero-authority preference.
    # ------------------------------------------------------------

    def test_experience_tier_defaults_to_basic(self):
        alice = self._signup("tier-alice")

        me = self.client.get("/auth/me", headers=self._auth(alice["token"]))

        self.assertEqual(me.json()["experience_tier"], "BASIC")

    def test_user_can_change_their_own_experience_tier(self):
        alice = self._signup("tier-alice2")

        response = self.client.post(
            "/auth/experience-tier",
            headers=self._auth(alice["token"]),
            json={"experience_tier": "ADVANCED"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["experience_tier"], "ADVANCED")

        me = self.client.get("/auth/me", headers=self._auth(alice["token"]))
        self.assertEqual(me.json()["experience_tier"], "ADVANCED")

    def test_invalid_experience_tier_is_rejected(self):
        alice = self._signup("tier-alice3")

        response = self.client.post(
            "/auth/experience-tier",
            headers=self._auth(alice["token"]),
            json={"experience_tier": "SUPER_ADVANCED"},
        )
        self.assertEqual(response.status_code, 400)

    def test_experience_tier_update_requires_login(self):
        response = self.client.post(
            "/auth/experience-tier",
            json={"experience_tier": "ADVANCED"},
        )
        self.assertEqual(response.status_code, 401)

    def test_changing_experience_tier_never_changes_role(self):
        alice = self._signup("tier-role-alice")
        bob = self._signup("tier-role-bob")

        self.client.post(
            "/auth/experience-tier",
            headers=self._auth(bob["token"]),
            json={"experience_tier": "ADVANCED"},
        )

        bob_me = self.client.get(
            "/auth/me", headers=self._auth(bob["token"])
        ).json()
        self.assertEqual(bob_me["role"], ROLE_USER)
        self.assertEqual(bob_me["experience_tier"], "ADVANCED")

        alice_me = self.client.get(
            "/auth/me", headers=self._auth(alice["token"])
        ).json()
        self.assertEqual(alice_me["role"], ROLE_ADMIN)

    def test_user_cannot_set_another_users_experience_tier_via_the_endpoint(
        self,
    ):
        # The endpoint takes no target user_id at all - it can only
        # ever act on the caller's own token-resolved account. This
        # proves there is no field that could be (ab)used to target
        # someone else.
        alice = self._signup("tier-target-alice")
        bob = self._signup("tier-target-bob")

        response = self.client.post(
            "/auth/experience-tier",
            headers=self._auth(bob["token"]),
            json={
                "experience_tier": "ADVANCED",
                "user_id": alice["user_id"],
            },
        )
        self.assertEqual(response.status_code, 200)

        alice_me = self.client.get(
            "/auth/me", headers=self._auth(alice["token"])
        ).json()
        self.assertEqual(alice_me["experience_tier"], "BASIC")

    # ------------------------------------------------------------
    # Devices: self-scoped listing and revocation.
    # ------------------------------------------------------------

    def test_devices_lists_only_the_callers_own_devices(self):
        alice = self._signup("device-alice", device_id="alice-phone")
        bob = self._signup("device-bob", device_id="bob-phone")

        alice_devices = self.client.get(
            "/auth/devices", headers=self._auth(alice["token"])
        ).json()["devices"]

        self.assertEqual(len(alice_devices), 1)
        self.assertEqual(alice_devices[0]["device_id"], "alice-phone")

    def test_devices_requires_login(self):
        response = self.client.get("/auth/devices")
        self.assertEqual(response.status_code, 401)

    def test_revoke_device_logs_out_that_device_only(self):
        alice = self._signup("revoke-alice", device_id="alice-phone")
        alice_second_login = self.client.post(
            "/auth/login",
            json={
                "username": "revoke-alice",
                "password": "correct-horse-1",
                "device_id": "alice-laptop",
            },
        ).json()

        response = self.client.delete(
            "/auth/devices/alice-phone",
            headers=self._auth(alice["token"]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revoked_sessions"], 1)

        # The phone's token no longer authenticates - a presented-but-
        # revoked token is a 401, exactly like any other invalid token
        # (see _resolve_authenticated_user_id's own docstring; matches
        # test_multi_user_isolation.py's
        # test_logged_out_token_can_no_longer_authenticate).
        me_phone = self.client.get(
            "/auth/me", headers=self._auth(alice["token"])
        )
        self.assertEqual(me_phone.status_code, 401)

        # ...but the laptop's session is untouched.
        me_laptop = self.client.get(
            "/auth/me", headers=self._auth(alice_second_login["token"])
        )
        self.assertTrue(me_laptop.json()["authenticated"])

    def test_revoke_device_never_reaches_another_users_device(self):
        alice = self._signup("cross-alice", device_id="shared-phone")
        bob = self._signup("cross-bob", device_id="shared-phone")

        self.client.delete(
            "/auth/devices/shared-phone",
            headers=self._auth(alice["token"]),
        )

        bob_me = self.client.get(
            "/auth/me", headers=self._auth(bob["token"])
        )
        self.assertTrue(bob_me.json()["authenticated"])

    def test_revoke_unknown_device_id_revokes_nothing(self):
        alice = self._signup("revoke-nothing-alice")

        response = self.client.delete(
            "/auth/devices/never-registered",
            headers=self._auth(alice["token"]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revoked_sessions"], 0)


if __name__ == "__main__":
    unittest.main()
