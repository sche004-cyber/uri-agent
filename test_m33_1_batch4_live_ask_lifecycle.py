"""M33.1 Batch 4 - live `/ask` lifecycle-intent seam acceptance evidence.

Proves the narrow seam end-to-end over real HTTP (FastAPI TestClient, no
Ollama/network for the ordinary-chat case; real npm for the one
strip-json-comments "remove skill" case, exactly like Batch 3's own
acceptance evidence already does): the model/deterministic interpretation
step, the narrow per-user executor closure, and `execute_lifecycle_intent`'s
own existing authority all compose correctly through `/ask`, without
touching canonical_execution.py, multi_action_dispatch.py, orchestrator.py,
approval_gate.py, or registry_bridge.py.
"""

from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("URI_EXTERNAL_CREDENTIAL_SECRET", "test-external-credential-secret")

from fastapi.testclient import TestClient

from uri_core.app import edge, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.lifecycle_intent_interpreter import LIFECYCLE_INTENT_SEAM_ENV_VAR
from uri_core.core.lifecycle_intent_interpreter import interpret
from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.user_accounts import UserAccountStore
from uri_core.external.descriptors.yt_dlp import DESCRIPTOR_ID as YT_DLP_DESCRIPTOR_ID


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDraftingProvider:
    def __init__(self, content="I've handled that for you."):
        self.content = content

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        return ModelResponse(content=self.content, model="fake", provider="fake")


class LiveAskLifecycleIntentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts
        self._original_user_state_root = server._USER_STATE_ROOT
        self._original_seam_env = os.environ.get(LIFECYCLE_INTENT_SEAM_ENV_VAR)

        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(self.temp_dir.name, "user_accounts.json")
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(self.temp_dir.name, "auth_sessions.json")
        )
        server._user_contexts = {}
        server._USER_STATE_ROOT = os.path.join(self.temp_dir.name, "users")
        edge.reset_rate_limiters()
        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        server._USER_STATE_ROOT = self._original_user_state_root
        if self._original_seam_env is None:
            os.environ.pop(LIFECYCLE_INTENT_SEAM_ENV_VAR, None)
        else:
            os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = self._original_seam_env
        edge.reset_rate_limiters()
        self.temp_dir.cleanup()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _signup(self, username: str, password: str = "correct-horse-1"):
        response = self.client.post("/auth/signup", json={"username": username, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _make_ask_ready(self, user_id: str, semantic_result: dict):
        context = server._get_user_context(user_id)
        context.orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(self.temp_dir.name, f"{user_id}-skill_memory.json")
        )
        context.orchestrator.semantic_interpreter = _FixedSemanticInterpreter(semantic_result)
        context.orchestrator.enable_model_reasoning_shadow = False
        context.orchestrator.enable_skill_router_shadow = False
        context.orchestrator.enable_response_narrative = True
        context.orchestrator.response_drafting_provider = _FakeDraftingProvider()
        return context

    def _ask(self, token: str, text: str, session_id: str = "s-lifecycle") -> dict:
        response = self.client.post(
            "/ask", headers=self._auth(token), json={"session_id": session_id, "text": text},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # ------------------------------------------------------------
    # Seam off by default
    # ------------------------------------------------------------

    def test_seam_is_off_by_default(self):
        os.environ.pop(LIFECYCLE_INTENT_SEAM_ENV_VAR, None)
        alice = self._signup("seam-off-alice")
        self._make_ask_ready(alice["user_id"], {
            "task_type": "conversation", "domain": "general", "goal": "chat",
            "requested_output": "reply", "entities": [],
        })
        body = self._ask(alice["token"], "enable skill yt_dlp")
        # Never a lifecycle envelope - falls through to the unchanged chain.
        self.assertNotIn(body.get("execution") or {}, [
            {"status": "success", "operation": "enable", "target_id": "yt_dlp"},
        ])
        self.assertNotEqual((body.get("execution") or {}).get("operation"), "enable")

    # ------------------------------------------------------------
    # Ordinary conversation is unaffected
    # ------------------------------------------------------------

    def test_ordinary_conversation_is_unaffected(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("ordinary-alice")
        self._make_ask_ready(alice["user_id"], {
            "task_type": "conversation", "domain": "general", "goal": "chat",
            "requested_output": "reply", "entities": [],
        })
        body = self._ask(alice["token"], "How is the weather today?")
        self.assertNotEqual((body.get("execution") or {}).get("operation"), "enable")
        self.assertNotIn("lifecycle", str(body.get("execution")))

    # ------------------------------------------------------------
    # Install / enable / disable a known skill (yt_dlp - no network)
    # ------------------------------------------------------------

    def test_install_enable_disable_known_skill_end_to_end(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("lifecycle-alice")
        context = server._get_user_context(alice["user_id"])

        installed = self._ask(alice["token"], "install skill yt_dlp")
        self.assertEqual(installed["status"], "success")
        self.assertEqual(installed["execution"]["status"], "success")

        enabled = self._ask(alice["token"], "enable skill yt_dlp")
        self.assertEqual(enabled["status"], "success")
        self.assertIsNotNone(
            context.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID)
        )

        disabled = self._ask(alice["token"], "disable skill yt_dlp")
        self.assertEqual(disabled["status"], "success")
        self.assertIsNone(
            context.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID)
        )

    # ------------------------------------------------------------
    # Remove a known skill (strip_json_comments - real npm install)
    # ------------------------------------------------------------

    def test_remove_known_skill_end_to_end(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("remove-alice")
        context = server._get_user_context(alice["user_id"])

        installed = self._ask(alice["token"], "install skill strip_json_comments")
        self.assertEqual(installed["status"], "success")

        removed = self._ask(alice["token"], "remove skill strip_json_comments")
        self.assertEqual(removed["status"], "success")
        self.assertIsNone(context.external_capability_store.get(alice["user_id"], "skill.strip_json_comments"))

    # ------------------------------------------------------------
    # Fail-closed cases
    # ------------------------------------------------------------

    def test_unknown_target_fails_closed(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("unknown-alice")
        body = self._ask(alice["token"], "enable skill totally_unknown_thing")
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["execution"]["status"], "unknown_target")

    def test_ambiguous_natural_language_never_becomes_a_lifecycle_mutation(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("ambiguous-alice")
        self._make_ask_ready(alice["user_id"], {
            "task_type": "conversation", "domain": "general", "goal": "chat",
            "requested_output": "reply", "entities": [],
        })
        ambiguous = [
            "How do I disable skill yt_dlp?",
            "Can URI disable skill yt_dlp?",
            "Do not disable skill yt_dlp.",
            'Explain "disable skill yt_dlp".',
            '"disable skill yt_dlp"',
            "disable skill yt_dlp because it is broken",
            "disable skill yt_dlp --force",
            "launch skill yt_dlp",
        ]
        for text in ambiguous:
            self.assertIsNone(interpret(text), text)
            body = self._ask(alice["token"], text, session_id=f"s-{len(text)}")
            self.assertNotEqual((body.get("execution") or {}).get("operation"), "disable", text)

        context = server._get_user_context(alice["user_id"])
        self.assertIsNone(
            context.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID)
        )

    def test_explicit_command_variants_and_structured_audit_evidence(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("command-alice")
        context = server._get_user_context(alice["user_id"])
        installed = self._ask(alice["token"], "INSTALL SKILL yt-dlp!")
        self.assertEqual(installed["execution"]["status"], "success")
        events = context.orchestrator.audit_trail.all_events()
        event = next(event for event in events if event.event_type == "lifecycle_intent")
        self.assertEqual(event.status, "success")
        self.assertEqual(event.metadata["user_id"], alice["user_id"])
        self.assertEqual(event.metadata["operation"], "install")
        self.assertEqual(event.metadata["target_id"], "yt_dlp")
        self.assertNotIn("INSTALL", str(event.metadata))

    # ------------------------------------------------------------
    # Connect requiring credentials never accepts model-visible secrets
    # ------------------------------------------------------------

    def test_connect_service_requires_credentials_flow(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("connect-alice")
        body = self._ask(alice["token"], "connect service github")
        self.assertEqual(body["execution"]["status"], "credentials_required")
        self.assertNotIn("ghp_", str(body["response"]))
        self.assertNotIn("token", str(body["response"]))

    # ------------------------------------------------------------
    # Cross-user isolation
    # ------------------------------------------------------------

    def test_cross_user_isolation(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        alice = self._signup("iso-alice")
        bob = self._signup("iso-bob")
        bob_context = server._get_user_context(bob["user_id"])

        installed = self._ask(alice["token"], "install skill yt_dlp")
        self.assertEqual(installed["status"], "success")
        enabled = self._ask(alice["token"], "enable skill yt_dlp")
        self.assertEqual(enabled["status"], "success")

        # Bob never installed anything - his own dispatch registry and
        # store are untouched by Alice's actions.
        self.assertIsNone(bob_context.orchestrator.multi_action_dispatch.registry.get_capability(YT_DLP_DESCRIPTOR_ID))
        bob_disable = self._ask(bob["token"], "disable skill yt_dlp")
        self.assertEqual(bob_disable["execution"]["status"], "not_installed")

    # ------------------------------------------------------------
    # Unauthenticated requests never reach the seam
    # ------------------------------------------------------------

    def test_unauthenticated_request_never_reaches_the_seam(self):
        os.environ[LIFECYCLE_INTENT_SEAM_ENV_VAR] = "1"
        response = self.client.post(
            "/ask", json={"session_id": "s-legacy", "text": "enable skill yt_dlp"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotEqual((body.get("execution") or {}).get("operation"), "enable")


if __name__ == "__main__":
    unittest.main()
