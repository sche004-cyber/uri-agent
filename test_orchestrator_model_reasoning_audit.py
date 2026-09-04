import json
import os
import unittest
from unittest.mock import MagicMock

from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator

_SESSION_IDS = [
    "model-reasoning-audit-1",
    "model-reasoning-audit-2",
    "model-reasoning-audit-3",
    "model-reasoning-audit-4",
]


def _session_file(session_id):
    return os.path.join("uri_workspace", "sessions", f"{session_id}.json")


def _model_reasoning_events(orchestrator, session_id):
    # The (unmodified) skill-router shadow audit call records its own
    # event on every turn regardless of enable_skill_router_shadow
    # (with status="shadow_disabled" when off) - these tests disable
    # it purely to reduce noise, not to make it silent, so assertions
    # here filter to the event type this milestone actually added
    # rather than assuming a total count.
    return [
        event
        for event in orchestrator.audit_trail.for_session(session_id)
        if event.event_type == "model_reasoning_shadow_evaluation"
    ]


def _fake_callable_proposing(capability_name):
    """A Callable[[str], str] matching model_callable's contract - no
    network, no Ollama. Used to drive the comparison-audit logic
    deterministically."""

    def _call(request_json):
        return json.dumps({"action": {"capability": capability_name}})

    return _call


class TestOrchestratorModelReasoningAudit(unittest.TestCase):
    """
    _record_model_reasoning_audit mirrors the existing
    _record_skill_router_audit pattern: a single, small AuditTrail
    event comparing the model reasoning shadow's proposed capability
    against the tool actually selected on this turn. These tests
    assert it stays observational (never changes plan/execution),
    stays quiet when there's nothing configured to compare, and never
    breaks the live request if audit recording itself fails.
    """

    def setUp(self):
        for session_id in _SESSION_IDS:
            path = _session_file(session_id)
            if os.path.exists(path):
                os.remove(path)

    def tearDown(self):
        for session_id in _SESSION_IDS:
            path = _session_file(session_id)
            if os.path.exists(path):
                os.remove(path)

    def _base_orchestrator(self, model_reasoning_gateway=None):
        orchestrator = UriOrchestrator(
            model_reasoning_gateway=model_reasoning_gateway
        )
        orchestrator.enable_skill_router_shadow = False

        orchestrator.semantic_interpreter = MagicMock()
        orchestrator.semantic_interpreter.interpret.return_value = {
            "goal": "Draft an office note",
            "task_type": "document drafting",
            "domain": "administrative",
            "requested_output": "office note",
        }

        orchestrator.skill_memory = MagicMock()
        orchestrator.skill_memory.find_matching_skill.return_value = None

        orchestrator.capability_planner.plan = (
            lambda semantic_result: {
                "status": "capability_selected",
                "tool_name": "draft_institutional_note",
            }
        )

        orchestrator.dispatcher.execute_tool = MagicMock(
            return_value={
                "status": "success",
                "data": {"draft": "Office note generated."},
            }
        )

        return orchestrator

    def test_no_event_recorded_when_model_not_configured(self):
        # Default gateway (model_callable=None, the default everywhere
        # except where an adapter is explicitly wired in) - no real
        # proposal exists, so nothing should be recorded.
        orchestrator = self._base_orchestrator()

        result = orchestrator.process_user_input(
            session_id="model-reasoning-audit-1",
            user_text="Draft an office note.",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["model_reasoning"]["result"]["status"],
            "model_not_configured",
        )

        events = _model_reasoning_events(
            orchestrator, "model-reasoning-audit-1"
        )
        self.assertEqual(len(events), 0)

    def test_records_agreement_when_proposal_matches_planner(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_callable_proposing(
                "draft_institutional_note"
            )
        )
        orchestrator = self._base_orchestrator(
            model_reasoning_gateway=gateway
        )

        result = orchestrator.process_user_input(
            session_id="model-reasoning-audit-2",
            user_text="Draft an office note.",
        )

        # Fully observational: execution is still driven by
        # CapabilityPlanner/ToolDispatcher, not by the shadow proposal.
        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )

        events = _model_reasoning_events(
            orchestrator, "model-reasoning-audit-2"
        )
        self.assertEqual(len(events), 1)

        event = events[0]
        self.assertEqual(
            event.event_type, "model_reasoning_shadow_evaluation"
        )
        self.assertEqual(event.capability, "draft_institutional_note")
        self.assertEqual(
            event.metadata["planner_tool_name"], "draft_institutional_note"
        )
        self.assertTrue(event.metadata["agrees_with_planner"])

    def test_records_disagreement_when_proposal_differs_from_planner(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_callable_proposing(
                "extract_student_records"
            )
        )
        orchestrator = self._base_orchestrator(
            model_reasoning_gateway=gateway
        )

        result = orchestrator.process_user_input(
            session_id="model-reasoning-audit-3",
            user_text="Draft an office note.",
        )

        # Still fully observational - the deterministic planner's
        # choice is what actually executed, regardless of disagreement.
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )

        events = _model_reasoning_events(
            orchestrator, "model-reasoning-audit-3"
        )
        self.assertEqual(len(events), 1)

        event = events[0]
        self.assertEqual(event.capability, "extract_student_records")
        self.assertFalse(event.metadata["agrees_with_planner"])

    def test_audit_failure_never_breaks_the_live_request(self):
        gateway = ModelReasoningGateway(
            model_callable=_fake_callable_proposing(
                "draft_institutional_note"
            )
        )
        orchestrator = self._base_orchestrator(
            model_reasoning_gateway=gateway
        )
        orchestrator.audit_trail.record = MagicMock(
            side_effect=RuntimeError("audit backend unavailable")
        )

        result = orchestrator.process_user_input(
            session_id="model-reasoning-audit-4",
            user_text="Draft an office note.",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(
            result["execution"]["tool"], "draft_institutional_note"
        )


if __name__ == "__main__":
    unittest.main()
