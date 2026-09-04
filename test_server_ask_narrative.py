"""Tests for Milestone 8A's wiring at the HTTP boundary: POST /ask
builds bounded personalization from the real (test-isolated) profile/
memory stores and passes it through; the response carries an additive
"narrative" field. No Ollama/network involved."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.user_memory import MemoryStore
from uri_core.core.user_profile import UserProfile, UserProfileStore


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDraftingProvider:
    def __init__(self, content="I've drafted that for you."):
        self.content = content
        self.calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.calls.append({"system": system, "user": user})
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


class AskNarrativeEndpointTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_memory_store = server._memory_store
        self._original_user_profile_store = server._user_profile_store
        self._original_semantic_interpreter = (
            server._orchestrator.semantic_interpreter
        )
        self._original_enable_model_reasoning_shadow = (
            server._orchestrator.enable_model_reasoning_shadow
        )
        self._original_enable_skill_router_shadow = (
            server._orchestrator.enable_skill_router_shadow
        )
        self._original_enable_response_narrative = (
            server._orchestrator.enable_response_narrative
        )
        self._original_response_drafting_provider = (
            server._orchestrator.response_drafting_provider
        )
        self._original_skill_memory = server._orchestrator.skill_memory

        # Isolate from the real, ambient uri_workspace/skill_memory.json
        # - otherwise a skill learned from prior real usage/tests could
        # short-circuit process_user_input via the "workflow_recalled"
        # branch, which narrative drafting is not wired into (see
        # test_orchestrator_approval_gate.py's identical rationale).
        server._orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory.json"
            )
        )

        server._memory_store = MemoryStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_memory.json"
            )
        )
        server._user_profile_store = UserProfileStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_profile.json"
            )
        )
        server._orchestrator.semantic_interpreter = (
            _FixedSemanticInterpreter(NOTE_SEMANTIC_RESULT)
        )
        server._orchestrator.enable_model_reasoning_shadow = False
        server._orchestrator.enable_skill_router_shadow = False

        self.provider = _FakeDraftingProvider()
        server._orchestrator.enable_response_narrative = True
        server._orchestrator.response_drafting_provider = self.provider

        self.client = TestClient(server.app)

    def tearDown(self):
        server._memory_store = self._original_memory_store
        server._user_profile_store = self._original_user_profile_store
        server._orchestrator.semantic_interpreter = (
            self._original_semantic_interpreter
        )
        server._orchestrator.enable_model_reasoning_shadow = (
            self._original_enable_model_reasoning_shadow
        )
        server._orchestrator.enable_skill_router_shadow = (
            self._original_enable_skill_router_shadow
        )
        server._orchestrator.enable_response_narrative = (
            self._original_enable_response_narrative
        )
        server._orchestrator.response_drafting_provider = (
            self._original_response_drafting_provider
        )
        server._orchestrator.skill_memory = self._original_skill_memory
        self.temp_dir.cleanup()

    def test_ask_response_includes_narrative_field(self):
        response = self.client.post(
            "/ask", json={"session_id": "s1", "text": "draft a note"}
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("narrative", body)
        self.assertEqual(body["narrative"], "I've drafted that for you.")

    def test_saved_profile_reaches_the_drafting_call(self):
        self.client.post(
            "/profile",
            json={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": ["insurance renewals"],
            },
        )

        self.client.post(
            "/ask", json={"session_id": "s1", "text": "draft a note"}
        )

        payload = self.provider.calls[-1]["user"]
        self.assertIn("formal", payload)
        self.assertIn("insurance renewals", payload)

    def test_confirmed_memory_reaches_the_drafting_call(self):
        self.client.post(
            "/memory",
            json={"category": "interest", "content": "badminton"},
        )

        self.client.post(
            "/ask", json={"session_id": "s1", "text": "draft a note"}
        )

        payload = self.provider.calls[-1]["user"]
        self.assertIn("badminton", payload)

    def test_no_profile_or_memory_still_answers_successfully(self):
        response = self.client.post(
            "/ask", json={"session_id": "s1", "text": "draft a note"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_narrative_absent_when_disabled(self):
        server._orchestrator.enable_response_narrative = False

        response = self.client.post(
            "/ask", json={"session_id": "s1", "text": "draft a note"}
        )

        self.assertIsNone(response.json()["narrative"])
        # The structured, pre-existing fields are unaffected either way.
        self.assertEqual(
            response.json()["execution"]["status"], "success"
        )


if __name__ == "__main__":
    unittest.main()
