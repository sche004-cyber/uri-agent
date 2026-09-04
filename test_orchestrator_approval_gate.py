"""End-to-end tests proving Milestone 7's wiring into UriOrchestrator
itself: the real process_user_input -> capability_selected branch now
routes through ApprovalGate, and the 4 real tools regress identically
since their registry entries all have approval_requirement == "none".
No Ollama/network involved - semantic_interpreter is injected."""

import json
import os
import tempfile
import unittest

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.model_providers.base import ModelResponse
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDraftingProvider:
    def __init__(self, content="URI has completed this action."):
        self.content = content
        self.calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.calls.append({"system": system, "user": user})
        return ModelResponse(
            content=self.content, model="fake", provider="fake"
        )


def _orchestrator_with_temp_registry(
    semantic_result: dict, entries: dict, **orchestrator_kwargs
):
    temp_dir = tempfile.TemporaryDirectory()
    registry_path = os.path.join(
        temp_dir.name, "capabilities_registry.json"
    )
    with open(registry_path, "w", encoding="utf-8") as file:
        json.dump({"active_tools": entries}, file)

    approval_store = ApprovalStore(
        storage_path=os.path.join(temp_dir.name, "approvals.json")
    )
    capability_registry = CapabilityRegistry(registry_path=registry_path)

    orchestrator = UriOrchestrator(
        semantic_interpreter=_FixedSemanticInterpreter(semantic_result),
        enable_model_reasoning_shadow=False,
        enable_skill_router_shadow=False,
        **orchestrator_kwargs,
    )

    # Rewire the orchestrator's capability_planner/approval_gate to the
    # temp registry - equivalent to what happens for the real registry
    # at real startup, but isolated for this test.
    orchestrator.capability_planner.registry_path = registry_path
    orchestrator.capability_planner.capability_registry = (
        capability_registry
    )
    orchestrator.dispatcher.registry_path = registry_path
    orchestrator.capability_registry = capability_registry
    # Isolate from the real, ambient uri_workspace/skill_memory.json -
    # otherwise a skill learned from prior real usage/tests could
    # short-circuit process_user_input via the "workflow_recalled"
    # branch before capability_planner/approval_gate are ever reached.
    orchestrator.skill_memory = SkillMemory(
        storage_path=os.path.join(temp_dir.name, "skill_memory.json")
    )
    orchestrator.approval_gate = ApprovalGate(
        dispatcher=orchestrator.dispatcher,
        capability_registry=capability_registry,
        approval_store=approval_store,
        audit_trail=orchestrator.audit_trail,
    )

    return orchestrator, temp_dir


class RealFourToolsRegressionTests(unittest.TestCase):
    """The 4 real registered tools all have approval_requirement ==
    "none" in the actual shipped registry - process_user_input must
    execute them exactly as before this milestone, with no approval
    detour."""

    def test_note_drafting_executes_directly_without_approval(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                {
                    "task_type": "document drafting",
                    "domain": "administrative",
                    "goal": "prepare a note",
                    "requested_output": "office note",
                    "entities": ["office note"],
                }
            ),
            enable_model_reasoning_shadow=False,
            enable_skill_router_shadow=False,
        )
        # Isolate from real, ambient prior-learned skills - see
        # _orchestrator_with_temp_registry's identical comment.
        orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                temp_dir.name, "skill_memory.json"
            )
        )

        result = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["execution"]["status"], "success")
        self.assertNotEqual(
            result["execution"]["status"], "awaiting_approval"
        )


class ApprovalRequiredCapabilityEndToEndTests(unittest.TestCase):
    """A synthetic approval-required capability, proving the full
    process_user_input -> awaiting_approval -> decide_action ->
    executed pipeline end-to-end through the real orchestrator, not
    just the gate in isolation."""

    def setUp(self):
        self.semantic_result = {
            "task_type": "document drafting",
            "domain": "administrative",
            "goal": "prepare a note",
            "requested_output": "office note",
            "entities": ["office note"],
        }
        self.orchestrator, self.temp_dir = _orchestrator_with_temp_registry(
            self.semantic_result,
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "user_approval_required",
                    "risk": "high",
                }
            },
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_call_returns_awaiting_approval_not_execution(self):
        result = self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["execution"]["status"], "awaiting_approval"
        )
        self.assertIn("action_id", result["response"])

    def test_approving_the_action_id_executes_it(self):
        first = self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = first["response"]["action_id"]

        decision = self.orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertEqual(decision["status"], "success")

    def test_rejecting_the_action_id_never_executes(self):
        first = self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = first["response"]["action_id"]

        decision = self.orchestrator.decide_action(
            action_id=action_id, approved=False, session_id="s1"
        )

        self.assertEqual(decision["status"], "cancelled")

    def test_a_second_ask_call_alone_does_not_approve_anything(self):
        # Simulates a model/user simply re-describing the same request
        # again - a second /ask must produce a brand new proposal, not
        # silently treat repetition as approval.
        first = self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        second = self.orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )

        self.assertNotEqual(
            first["response"]["action_id"],
            second["response"]["action_id"],
        )
        self.assertEqual(
            second["execution"]["status"], "awaiting_approval"
        )


class DecideActionNarrativeTests(unittest.TestCase):
    """Issue 3: decide_action (POST /approve, POST /cancel) gets the
    same additive narrative treatment process_user_input already has
    - the actual completion, not just the initial proposal, can be
    explained in URI's voice instead of only ever showing raw tool
    output."""

    def _setup(self, provider=None, **kwargs):
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "task_type": "document drafting",
                "domain": "administrative",
                "goal": "prepare a note",
                "requested_output": "office note",
                "entities": ["office note"],
            },
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "user_approval_required",
                    "risk": "controlled",
                }
            },
            enable_response_narrative=True,
            response_drafting_provider=provider or _FakeDraftingProvider(),
            **kwargs,
        )
        self.addCleanup(temp_dir.cleanup)
        return orchestrator

    def test_narrative_absent_when_disabled(self):
        orchestrator, temp_dir = _orchestrator_with_temp_registry(
            {
                "task_type": "document drafting",
                "domain": "administrative",
                "goal": "prepare a note",
                "requested_output": "office note",
                "entities": ["office note"],
            },
            {
                "draft_institutional_note": {
                    "file_path": (
                        "uri_core/tools/draft_institutional_note.py"
                    ),
                    "class_name": "InstitutionalNoteDraftCmp",
                    "method": "generate",
                    "approval_requirement": "user_approval_required",
                }
            },
        )
        self.addCleanup(temp_dir.cleanup)

        proposal = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = proposal["response"]["action_id"]

        decision = orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertIn("narrative", decision)
        self.assertIsNone(decision["narrative"])

    def test_approved_decision_gets_a_narrative(self):
        orchestrator = self._setup(
            provider=_FakeDraftingProvider(
                content="I've drafted the note as requested."
            )
        )

        proposal = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = proposal["response"]["action_id"]

        decision = orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertEqual(decision["status"], "success")
        self.assertEqual(
            decision["narrative"], "I've drafted the note as requested."
        )

    def test_cancelled_decision_gets_a_narrative_too(self):
        orchestrator = self._setup(
            provider=_FakeDraftingProvider(
                content="No problem - I won't proceed with that."
            )
        )

        proposal = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = proposal["response"]["action_id"]

        decision = orchestrator.decide_action(
            action_id=action_id, approved=False, session_id="s1"
        )

        self.assertEqual(decision["status"], "cancelled")
        self.assertEqual(
            decision["narrative"], "No problem - I won't proceed with that."
        )

    def test_original_request_text_reaches_the_drafting_call(self):
        provider = _FakeDraftingProvider()
        orchestrator = self._setup(provider=provider)

        proposal = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note about the budget"
        )
        action_id = proposal["response"]["action_id"]

        orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        payload = provider.calls[-1]["user"]
        self.assertIn("draft a note about the budget", payload)

    def test_invalid_action_id_still_returns_a_narrative_key(self):
        orchestrator = self._setup()

        decision = orchestrator.decide_action(
            action_id="fabricated-id", approved=True, session_id="s1"
        )

        self.assertEqual(decision["status"], "error")
        self.assertIn("narrative", decision)

    def test_drafting_failure_on_decide_falls_back_cleanly(self):

        class _RaisingProvider:
            def complete(self, **kwargs):
                raise ConnectionError("no ollama")

        orchestrator = self._setup(provider=_RaisingProvider())

        proposal = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = proposal["response"]["action_id"]

        decision = orchestrator.decide_action(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertEqual(decision["status"], "success")
        self.assertIsNone(decision["narrative"])

    def test_approval_gate_itself_remains_untouched_by_this_addition(self):
        # ApprovalGate.decide() itself must still return exactly what
        # it always did - the narrative is layered on by
        # UriOrchestrator.decide_action(), not by ApprovalGate.
        orchestrator = self._setup()

        proposal = orchestrator.process_user_input(
            session_id="s1", user_text="draft a note"
        )
        action_id = proposal["response"]["action_id"]

        raw_gate_result = orchestrator.approval_gate.decide(
            action_id=action_id, approved=True, session_id="s1"
        )

        self.assertNotIn("narrative", raw_gate_result)


if __name__ == "__main__":
    unittest.main()
