"""Prototype 1 — multi-user identity + login foundation.

Proves the required behaviour end-to-end over real HTTP (FastAPI
TestClient, no Ollama/network):

    - login (POST /auth/signup, POST /auth/login) identifies a user
      and hands back a bearer token bound to a fresh, isolated user_id
    - an authenticated request (Authorization: Bearer <token>) selects
      that user_id's own profile/memory/growth/session/approval state
    - User A cannot read or mutate User B's profile, memory, tasks, or
      approvals, even when guessing/reusing the same conversation
      session_id or a real action_id from the other user
    - client identity (device_id) stays separate from user identity
      (login-issued user_id) - see test_login_user_id_is_independent_
      of_legacy_device_identity
    - a request with no Authorization header at all keeps behaving
      exactly like the pre-login, single-ambient-install prototype
      (backward compatibility for every pre-existing test/caller)
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.user_accounts import UserAccountStore


class _FakeDispatcher:
    """Same pattern as test_server_approval_endpoints.py's own
    _FakeDispatcher - pc_system_optimization has no real executable
    backing (it is Milestone 6's deliberately not_implemented example
    capability), so a real ToolDispatcher cannot actually execute it."""

    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDraftingProvider:
    def __init__(self, content="I've handled that for you."):
        self.content = content

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        return ModelResponse(
            content=self.content, model="fake", provider="fake"
        )


NOTE_SEMANTIC_RESULT = {
    "task_type": "document drafting",
    "domain": "administrative",
    "goal": "prepare a note",
    "requested_output": "office note",
    "entities": ["office note"],
}


class MultiUserIsolationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts
        self._original_user_state_root = server._USER_STATE_ROOT

        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_accounts.json"
            )
        )
        server._auth_session_store = AuthSessionStore()
        server._user_contexts = {}
        # Every per-user profile/memory/growth/session/approval store
        # this test's _get_user_context()/_build_user_context() calls
        # create must land under this temp directory, never under the
        # real uri_workspace/users/ tree - matching every other store
        # in this codebase's test-isolation discipline.
        server._USER_STATE_ROOT = os.path.join(
            self.temp_dir.name, "users"
        )

        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        server._USER_STATE_ROOT = self._original_user_state_root
        self.temp_dir.cleanup()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _signup(self, username: str, password: str = "correct-horse-1"):
        response = self.client.post(
            "/auth/signup",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _make_ask_ready(self, user_id: str):
        """Builds (if not already built) user_id's real _UserContext and
        neuters everything network-dependent in its orchestrator, same
        discipline as test_server_ask_narrative.py's setUp - so POST
        /ask can be exercised over real HTTP without Ollama."""
        context = server._get_user_context(user_id)

        context.orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, f"{user_id}-skill_memory.json"
            )
        )
        context.orchestrator.semantic_interpreter = (
            _FixedSemanticInterpreter(NOTE_SEMANTIC_RESULT)
        )
        context.orchestrator.enable_model_reasoning_shadow = False
        context.orchestrator.enable_skill_router_shadow = False
        context.orchestrator.enable_response_narrative = True
        context.orchestrator.response_drafting_provider = (
            _FakeDraftingProvider()
        )
        return context

    # ------------------------------------------------------------
    # Signup / login identify a user
    # ------------------------------------------------------------

    def test_signup_returns_a_fresh_user_id_and_a_usable_token(self):
        body = self._signup("alice")

        self.assertIn("user_id", body)
        self.assertIn("token", body)
        self.assertEqual(body["username"], "alice")

        me = self.client.get("/auth/me", headers=self._auth(body["token"]))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["authenticated"], True)
        self.assertEqual(me.json()["user_id"], body["user_id"])

    def test_duplicate_username_signup_is_rejected(self):
        self._signup("bob")

        second = self.client.post(
            "/auth/signup",
            json={"username": "bob", "password": "another-pass-1"},
        )
        self.assertEqual(second.status_code, 400)

    def test_login_with_correct_credentials_identifies_the_same_user(self):
        signup_body = self._signup("carol", password="carols-secret-1")

        login_response = self.client.post(
            "/auth/login",
            json={"username": "carol", "password": "carols-secret-1"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(
            login_response.json()["user_id"], signup_body["user_id"]
        )
        # A fresh token, not a reuse of the signup token.
        self.assertNotEqual(
            login_response.json()["token"], signup_body["token"]
        )

    def test_login_with_wrong_password_is_rejected(self):
        self._signup("dave", password="daves-secret-1")

        response = self.client.post(
            "/auth/login",
            json={"username": "dave", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    def test_login_with_unknown_username_is_rejected_the_same_way(self):
        # Same status/shape as a wrong password - see
        # test_login_with_wrong_password_is_rejected - so this endpoint
        # can never be used to enumerate valid usernames.
        response = self.client.post(
            "/auth/login",
            json={"username": "nobody-registered", "password": "whatever1"},
        )
        self.assertEqual(response.status_code, 401)

    def test_request_with_malformed_authorization_header_is_rejected(self):
        response = self.client.get(
            "/profile", headers={"Authorization": "not-a-bearer-token"}
        )
        self.assertEqual(response.status_code, 401)

    def test_request_with_unknown_token_is_rejected(self):
        response = self.client.get(
            "/profile",
            headers={"Authorization": "Bearer this-token-was-never-issued"},
        )
        self.assertEqual(response.status_code, 401)

    def test_logged_out_token_can_no_longer_authenticate(self):
        body = self._signup("erin")
        headers = self._auth(body["token"])

        logout = self.client.post("/auth/logout", headers=headers)
        self.assertEqual(logout.status_code, 200)

        after_logout = self.client.get("/profile", headers=headers)
        self.assertEqual(after_logout.status_code, 401)

    # ------------------------------------------------------------
    # Backward compatibility: no Authorization header at all keeps
    # working exactly like the pre-login, single-ambient install.
    # ------------------------------------------------------------

    def test_no_authorization_header_falls_back_to_legacy_ambient_profile(
        self,
    ):
        response = self.client.get("/profile")
        self.assertEqual(response.status_code, 200)
        # Same shape/behaviour as before login existed - no 401, no
        # user-scoped redirection.
        self.assertIn("communication_style", response.json())

    # ------------------------------------------------------------
    # Profile isolation
    # ------------------------------------------------------------

    def test_profile_is_isolated_between_two_users(self):
        alice = self._signup("profile-alice")
        bob = self._signup("profile-bob")

        self.client.post(
            "/profile",
            headers=self._auth(alice["token"]),
            json={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": ["alice-only"],
            },
        )
        self.client.post(
            "/profile",
            headers=self._auth(bob["token"]),
            json={
                "communication_style": "conversational",
                "autonomy_level": "routineAutoApprove",
                "focus_areas": ["bob-only"],
            },
        )

        alice_profile = self.client.get(
            "/profile", headers=self._auth(alice["token"])
        ).json()
        bob_profile = self.client.get(
            "/profile", headers=self._auth(bob["token"])
        ).json()

        self.assertEqual(alice_profile["communication_style"], "formal")
        self.assertEqual(alice_profile["focus_areas"], ["alice-only"])

        self.assertEqual(
            bob_profile["communication_style"], "conversational"
        )
        self.assertEqual(bob_profile["focus_areas"], ["bob-only"])

    # ------------------------------------------------------------
    # Memory isolation
    # ------------------------------------------------------------

    def test_memory_is_isolated_between_two_users(self):
        alice = self._signup("memory-alice")
        bob = self._signup("memory-bob")

        self.client.post(
            "/memory",
            headers=self._auth(alice["token"]),
            json={"category": "preference", "content": "Alice likes tea."},
        )

        alice_memories = self.client.get(
            "/memory", headers=self._auth(alice["token"])
        ).json()["memories"]
        bob_memories = self.client.get(
            "/memory", headers=self._auth(bob["token"])
        ).json()["memories"]

        self.assertEqual(len(alice_memories), 1)
        self.assertEqual(bob_memories, [])

    def test_user_cannot_update_or_delete_another_users_memory(self):
        alice = self._signup("memory2-alice")
        bob = self._signup("memory2-bob")

        created = self.client.post(
            "/memory",
            headers=self._auth(alice["token"]),
            json={"category": "preference", "content": "Alice likes tea."},
        ).json()

        update_attempt = self.client.put(
            f"/memory/{created['memory_id']}",
            headers=self._auth(bob["token"]),
            json={"category": "preference", "content": "Hijacked."},
        )
        self.assertEqual(update_attempt.status_code, 404)

        delete_attempt = self.client.delete(
            f"/memory/{created['memory_id']}",
            headers=self._auth(bob["token"]),
        )
        self.assertEqual(delete_attempt.status_code, 404)

        # Alice's memory is untouched.
        alice_memories = self.client.get(
            "/memory", headers=self._auth(alice["token"])
        ).json()["memories"]
        self.assertEqual(len(alice_memories), 1)
        self.assertEqual(alice_memories[0]["content"], "Alice likes tea.")

    # ------------------------------------------------------------
    # Tasks/approvals isolation
    # ------------------------------------------------------------

    def test_tasks_are_isolated_between_two_users(self):
        alice = self._signup("tasks-alice")
        bob = self._signup("tasks-bob")

        alice_context = server._get_user_context(alice["user_id"])
        alice_context.orchestrator.approval_gate.approval_store.propose(
            capability_id="pc_system_optimization",
            arguments={"request_text": "optimize alice's machine"},
            session_id="s1",
        )

        alice_tasks = self.client.get(
            "/tasks", headers=self._auth(alice["token"])
        ).json()["tasks"]
        bob_tasks = self.client.get(
            "/tasks", headers=self._auth(bob["token"])
        ).json()["tasks"]

        self.assertEqual(len(alice_tasks), 1)
        self.assertEqual(bob_tasks, [])

    def test_user_cannot_approve_another_users_action_id(self):
        alice = self._signup("approve-alice")
        bob = self._signup("approve-bob")

        alice_context = server._get_user_context(alice["user_id"])
        # pc_system_optimization is a real registry entry with zero
        # executable backing (see capability_registry.py's Milestone 6
        # docstring) - swapping in a fake dispatcher, exactly like
        # test_server_approval_endpoints.py already does, is what lets
        # Alice's own later approval actually reach "success" instead
        # of failing on "no real tool implementation", which is not
        # what this test is proving.
        fake_dispatcher = _FakeDispatcher()
        alice_context.orchestrator.approval_gate.dispatcher = (
            fake_dispatcher
        )

        proposed = (
            alice_context.orchestrator.approval_gate.approval_store.propose(
                capability_id="pc_system_optimization",
                arguments={},
                session_id="s1",
            )
        )

        bob_attempt = self.client.post(
            "/approve",
            headers=self._auth(bob["token"]),
            json={"action_id": proposed.action_id, "session_id": "s1"},
        )

        self.assertEqual(bob_attempt.status_code, 200)
        self.assertEqual(bob_attempt.json()["status"], "error")

        # Alice can still approve her own action afterwards - Bob's
        # failed attempt did not consume or corrupt it.
        alice_attempt = self.client.post(
            "/approve",
            headers=self._auth(alice["token"]),
            json={"action_id": proposed.action_id, "session_id": "s1"},
        )
        self.assertEqual(alice_attempt.json()["status"], "success")

    # ------------------------------------------------------------
    # Conversation/session isolation, including the same session_id
    # string reused across two different logins.
    # ------------------------------------------------------------

    def test_same_session_id_stays_isolated_across_two_logins(self):
        alice = self._signup("session-alice")
        bob = self._signup("session-bob")

        self._make_ask_ready(alice["user_id"])
        self._make_ask_ready(bob["user_id"])

        self.client.post(
            "/ask",
            headers=self._auth(alice["token"]),
            json={"session_id": "shared-session-id", "text": "draft a note"},
        )
        self.client.post(
            "/ask",
            headers=self._auth(bob["token"]),
            json={"session_id": "shared-session-id", "text": "draft a note"},
        )

        alice_session_manager = server._get_user_context(
            alice["user_id"]
        ).orchestrator.session_manager
        bob_session_manager = server._get_user_context(
            bob["user_id"]
        ).orchestrator.session_manager

        # Both sessions exist independently under the identical
        # session_id string - proving isolation is keyed by user_id,
        # not by session_id colliding into shared state.
        self.assertIsNot(alice_session_manager, bob_session_manager)
        self.assertNotEqual(
            alice_session_manager.storage_path,
            bob_session_manager.storage_path,
        )

        alice_session = alice_session_manager.get_session(
            "shared-session-id"
        )
        bob_session = bob_session_manager.get_session("shared-session-id")

        # Each session was independently populated by its own /ask call
        # above rather than one leaking into or overwriting the other.
        self.assertEqual(
            alice_session.task, bob_session.task
        )  # both drafted the same request text, from separate state
        self.assertIsNot(
            alice_session.current_facts, bob_session.current_facts
        )

    def test_login_user_id_is_independent_of_legacy_device_identity(self):
        """client identity (device_id) must remain separate from user
        identity (the user_id a login token resolves to) - signing up
        two different accounts must never change this install's single
        device_id, and neither account's user_id may equal it."""
        device_before = self.client.get("/identity").json()["device_id"]

        alice = self._signup("device-alice")
        bob = self._signup("device-bob")

        device_after = self.client.get("/identity").json()["device_id"]

        self.assertEqual(device_before, device_after)
        self.assertNotEqual(alice["user_id"], device_after)
        self.assertNotEqual(bob["user_id"], device_after)
        self.assertNotEqual(alice["user_id"], bob["user_id"])


if __name__ == "__main__":
    unittest.main()
