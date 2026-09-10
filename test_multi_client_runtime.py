"""Prototype 2 — multi-client + runtime awareness.

Proves, over real HTTP (FastAPI TestClient, no Ollama/network), that
one authenticated user can connect from multiple clients while
runtime/device capabilities stay separate from user state:

    - the same account can log in from two different clients
      (device_id) at once, each getting its own token
    - both clients land on the exact same _UserContext (profile,
      memory, growth, sessions, approvals - identical to
      test_multi_user_isolation.py's single-client proof, now with two
      concurrent logins)
    - GET /auth/me tells the two clients' device_id apart, while both
      report the identical runtime_device_id (the PC/install actually
      running the backend)
    - device_id is optional/backward compatible and never leaks into
      user-authoritative state (profile/memory)
    - two different users' devices stay isolated from each other, same
      as Prototype 1, even when both are logged in at once
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.identity import DeviceIdentityStore
from uri_core.core.user_accounts import UserAccountStore


class MultiClientRuntimeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts
        self._original_user_state_root = server._USER_STATE_ROOT
        self._original_device_identity_store = server._device_identity_store

        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_accounts.json"
            )
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(
                self.temp_dir.name, "auth_sessions.json"
            )
        )
        server._user_contexts = {}
        server._USER_STATE_ROOT = os.path.join(self.temp_dir.name, "users")
        # A dedicated, temp-backed runtime device identity so this test
        # never touches (or depends on) the real machine's
        # uri_workspace/device_identity.json.
        server._device_identity_store = DeviceIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "device_identity.json"
            )
        )

        # M22.3: this test signs up/logs in several accounts per test
        # method, all from TestClient's single fixed fake client host -
        # without a reset, the module-level rate limiter (shared process
        # state, keyed by client IP - see edge.py) would otherwise carry
        # a count across every test in this file (and every other test
        # module run in the same process), tripping on a later,
        # legitimate call. Reset here, not disabled, so the limiter's
        # real behaviour is still exercised by test_m22_3_rate_limiting.py
        # without this file's own isolation tests being collateral
        # damage.
        edge.reset_rate_limiters()

        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        server._USER_STATE_ROOT = self._original_user_state_root
        server._device_identity_store = self._original_device_identity_store
        edge.reset_rate_limiters()
        self.temp_dir.cleanup()

    def _auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _signup(self, username, password="correct-horse-1", device_id=None):
        payload = {"username": username, "password": password}
        if device_id is not None:
            payload["device_id"] = device_id
        response = self.client.post("/auth/signup", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _login(self, username, password="correct-horse-1", device_id=None):
        payload = {"username": username, "password": password}
        if device_id is not None:
            payload["device_id"] = device_id
        response = self.client.post("/auth/login", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # ------------------------------------------------------------
    # Same user, multiple clients
    # ------------------------------------------------------------

    def test_same_user_can_log_in_from_two_devices_at_once(self):
        account = self._signup("multi-alice", device_id="phone-abc")

        pc_login = self._login(
            "multi-alice", device_id="pc-xyz"
        )

        # Two independent tokens for the same account.
        self.assertNotEqual(account["token"], pc_login["token"])
        self.assertEqual(account["user_id"], pc_login["user_id"])

        # Both tokens remain independently valid at the same time - the
        # PC login did not invalidate the phone's signup-issued token.
        phone_me = self.client.get(
            "/auth/me", headers=self._auth(account["token"])
        ).json()
        pc_me = self.client.get(
            "/auth/me", headers=self._auth(pc_login["token"])
        ).json()

        self.assertTrue(phone_me["authenticated"])
        self.assertTrue(pc_me["authenticated"])
        self.assertEqual(phone_me["user_id"], pc_me["user_id"])

    def test_auth_me_distinguishes_device_id_per_login(self):
        phone = self._signup("multi-bob", device_id="phone-111")
        pc = self._login("multi-bob", device_id="pc-222")

        phone_me = self.client.get(
            "/auth/me", headers=self._auth(phone["token"])
        ).json()
        pc_me = self.client.get(
            "/auth/me", headers=self._auth(pc["token"])
        ).json()

        self.assertEqual(phone_me["device_id"], "phone-111")
        self.assertEqual(pc_me["device_id"], "pc-222")
        self.assertNotEqual(phone_me["device_id"], pc_me["device_id"])

    def test_both_clients_of_the_same_user_share_the_same_state(self):
        phone = self._signup("multi-carol", device_id="phone-1")
        pc = self._login("multi-carol", device_id="pc-1")

        # Write from the "phone" client.
        self.client.post(
            "/profile",
            headers=self._auth(phone["token"]),
            json={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": ["set-from-phone"],
            },
        )
        self.client.post(
            "/memory",
            headers=self._auth(phone["token"]),
            json={"category": "preference", "content": "Set from phone."},
        )

        # Read from the "pc" client - same account, different login/
        # device_id, must see exactly what the phone client wrote.
        pc_profile = self.client.get(
            "/profile", headers=self._auth(pc["token"])
        ).json()
        pc_memories = self.client.get(
            "/memory", headers=self._auth(pc["token"])
        ).json()["memories"]

        self.assertEqual(pc_profile["communication_style"], "formal")
        self.assertEqual(pc_profile["focus_areas"], ["set-from-phone"])
        self.assertEqual(len(pc_memories), 1)
        self.assertEqual(pc_memories[0]["content"], "Set from phone.")

    def test_both_clients_of_the_same_user_share_tasks_and_approvals(self):
        phone = self._signup("multi-dave", device_id="phone-2")
        pc = self._login("multi-dave", device_id="pc-2")

        # A pending action proposed under this user's single shared
        # _UserContext (see server._get_user_context) - regardless of
        # which login/device_id happened to trigger it, both of this
        # user's clients must see it.
        context = server._get_user_context(phone["user_id"])
        context.orchestrator.approval_gate.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={"request_text": "optimize"},
            session_id="s1",
        )

        phone_tasks = self.client.get(
            "/tasks", headers=self._auth(phone["token"])
        ).json()["tasks"]
        pc_tasks = self.client.get(
            "/tasks", headers=self._auth(pc["token"])
        ).json()["tasks"]

        self.assertEqual(len(phone_tasks), 1)
        self.assertEqual(len(pc_tasks), 1)
        self.assertEqual(phone_tasks[0]["action_id"], pc_tasks[0]["action_id"])

    # ------------------------------------------------------------
    # Runtime/device awareness
    # ------------------------------------------------------------

    def test_runtime_device_id_is_identical_across_different_logins(self):
        alice = self._signup("runtime-alice", device_id="alice-phone")
        bob = self._signup("runtime-bob", device_id="bob-phone")

        alice_me = self.client.get(
            "/auth/me", headers=self._auth(alice["token"])
        ).json()
        bob_me = self.client.get(
            "/auth/me", headers=self._auth(bob["token"])
        ).json()

        # Same backend process serving both users -> identical runtime
        # identity, even though their user_id and device_id all differ.
        self.assertEqual(
            alice_me["runtime_device_id"], bob_me["runtime_device_id"]
        )
        self.assertNotEqual(alice_me["user_id"], bob_me["user_id"])
        self.assertNotEqual(alice_me["device_id"], bob_me["device_id"])

    def test_runtime_device_id_matches_get_identity(self):
        identity_response = self.client.get("/identity").json()

        someone = self._signup("runtime-carol", device_id="carols-pc")
        me = self.client.get(
            "/auth/me", headers=self._auth(someone["token"])
        ).json()

        self.assertEqual(
            me["runtime_device_id"], identity_response["device_id"]
        )

    def test_device_id_is_optional_and_backward_compatible(self):
        account = self._signup("runtime-erin")  # no device_id supplied

        me = self.client.get(
            "/auth/me", headers=self._auth(account["token"])
        ).json()

        self.assertTrue(me["authenticated"])
        self.assertIsNone(me["device_id"])
        self.assertIsNotNone(me["runtime_device_id"])

    def test_unauthenticated_auth_me_reports_both_device_fields_as_none(
        self,
    ):
        me = self.client.get("/auth/me").json()

        self.assertFalse(me["authenticated"])
        self.assertIsNone(me["device_id"])
        self.assertIsNone(me["runtime_device_id"])

    def test_device_id_never_appears_in_profile_or_memory_storage(self):
        """runtime/device capabilities and identifiers must never be
        stored as user memory/profile data (Prototype 2 requirement) -
        a distinctive device_id string must not leak into the on-disk
        profile/memory files this login's writes produce."""
        distinctive_device_id = "distinctive-marker-should-never-leak"
        account = self._signup(
            "runtime-frank", device_id=distinctive_device_id
        )

        self.client.post(
            "/profile",
            headers=self._auth(account["token"]),
            json={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": ["frank-focus"],
            },
        )
        self.client.post(
            "/memory",
            headers=self._auth(account["token"]),
            json={"category": "preference", "content": "Frank likes coffee."},
        )

        context = server._get_user_context(account["user_id"])

        with open(
            context.profile_store.storage_path, "r", encoding="utf-8"
        ) as file:
            profile_contents = file.read()
        with open(
            context.memory_store.storage_path, "r", encoding="utf-8"
        ) as file:
            memory_contents = file.read()

        self.assertNotIn(distinctive_device_id, profile_contents)
        self.assertNotIn(distinctive_device_id, memory_contents)

    # ------------------------------------------------------------
    # Different users' devices remain isolated even when several
    # clients/logins are active at once.
    # ------------------------------------------------------------

    def test_different_users_devices_remain_isolated_with_multiple_logins(
        self,
    ):
        alice_phone = self._signup("iso-alice", device_id="alice-phone")
        alice_pc = self._login("iso-alice", device_id="alice-pc")
        bob_phone = self._signup("iso-bob", device_id="bob-phone")
        bob_pc = self._login("iso-bob", device_id="bob-pc")

        self.client.post(
            "/memory",
            headers=self._auth(alice_phone["token"]),
            json={"category": "preference", "content": "Alice's secret."},
        )
        self.client.post(
            "/memory",
            headers=self._auth(bob_pc["token"]),
            json={"category": "preference", "content": "Bob's secret."},
        )

        for token in (alice_phone["token"], alice_pc["token"]):
            memories = self.client.get(
                "/memory", headers=self._auth(token)
            ).json()["memories"]
            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0]["content"], "Alice's secret.")

        for token in (bob_phone["token"], bob_pc["token"]):
            memories = self.client.get(
                "/memory", headers=self._auth(token)
            ).json()["memories"]
            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0]["content"], "Bob's secret.")


if __name__ == "__main__":
    unittest.main()
