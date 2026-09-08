"""M20 (W3): a FAILED single-capability execution now reaches the
Brain re-evaluation loop regardless of which authority selected it -
a learned skill (SkillMemory) or the deterministic CapabilityPlanner,
not only a fresh Brain proposal (as before this milestone).

Before this change, orchestrator.py's capability_selected branch only
called _continue_brain_evaluation_loop when plan["source"] ==
"model_reasoning" - a learned-skill or CapabilityPlanner selection
that failed simply ended the turn with an honest error and no attempt
to find another route, exactly the "stops with a tool/skill-
unavailable error" symptom the M20 audit's requirement 2 called out.

No network/Ollama involved - every gateway here is driven by a fake,
in-process model_callable, mirroring test_orchestrator_brain_
reevaluation.py's own discipline.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.state import SessionManager


class _FixedSemanticInterpreter:
    def __init__(self, result: dict):
        self._result = result

    def interpret(self, user_text: str) -> dict:
        return self._result


class _FakeDispatcher:
    def __init__(self, results_by_capability=None):
        self.calls = []
        self._results_by_capability = results_by_capability or {}

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if tool_name in self._results_by_capability:
            return self._results_by_capability[tool_name]
        return {"status": "success", "data": {"tool": tool_name}}


def _by_attempt_count(responses_by_count):
    """Inspects the request's attempt_history length (0 = initial
    proposal, 1+ = a re-evaluation call) to decide how to respond -
    lets these tests drive a deterministic "first no proposal, then
    evaluate the real failure" sequence without a real model."""

    def _call(request_json):
        request = json.loads(request_json)
        count = len(request.get("attempt_history", []))
        payload = responses_by_count.get(
            count, responses_by_count.get("default", {})
        )
        return json.dumps(payload)

    return _call


NOTE_SEMANTIC_RESULT = {
    "goal": "Search Gmail for a message",
    "task_type": "information retrieval",
    "domain": "email",
    "requested_output": "email search results",
    "entities": [],
}


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(self, model_reasoning_gateway=None, **kwargs):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=model_reasoning_gateway,
            enable_model_reasoning_shadow=True,
            enable_skill_router_shadow=False,
            enable_response_narrative=False,
            session_manager=SessionManager(
                storage_path=os.path.join(self.temp_dir.name, "sessions")
            ),
            **kwargs,
        )
        orchestrator.skill_memory = SkillMemory(
            storage_path=os.path.join(
                self.temp_dir.name, "skill_memory.json"
            )
        )
        return orchestrator


class LearnedSkillFailureReachesRecoveryTests(_IsolatedOrchestratorCase):
    """A learned-skill selection (plan["source"] == "skill_memory")
    that fails now triggers the Brain re-evaluation loop."""

    def test_learned_skill_failure_reaches_recovery_loop(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    # Initial call: no fresh proposal at all, so the
                    # learned skill below is used as the plan.
                    0: {"action": None},
                    # Recovery call: the Brain evaluates the real
                    # failure and has nothing further to propose - a
                    # valid, complete answer per REASONING_SYSTEM_PROMPT.
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": (
                                "gmail_search failed and no other "
                                "registered capability can search "
                                "email."
                            ),
                        },
                        "action": None,
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: {
                "tool_name": "gmail_search",
                "task_type": "information retrieval",
                "domain": "email",
                "success_count": 3,
            }
        )

        dispatcher = _FakeDispatcher(
            {
                "gmail_search": {
                    "status": "error",
                    "message": "Gmail is not connected.",
                }
            }
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="search my email for the invoice"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["plan"]["source"], "skill_memory")
        self.assertEqual(result["execution"]["status"], "error")

        # The recovery loop actually ran - proven by brain_evaluation
        # being present at all (pre-M20, no second reasoning call
        # would ever have been made for a non-Brain-sourced plan).
        self.assertIn("brain_evaluation", result)
        self.assertFalse(result["brain_evaluation"]["satisfied"])
        self.assertEqual(
            result["brain_evaluation"]["status"], "no_further_proposal"
        )

        # Only the single failed dispatch happened - the recovery call
        # itself never executes anything on its own; it only reasons.
        self.assertEqual(len(dispatcher.calls), 1)
        self.assertEqual(dispatcher.calls[0][0], "gmail_search")


class CapabilityPlannerFailureReachesRecoveryTests(_IsolatedOrchestratorCase):
    """A deterministic CapabilityPlanner selection (plan has no
    "source" key at all) that fails now also triggers recovery."""

    def test_capability_planner_failure_reaches_recovery_loop(self):
        gateway = ModelReasoningGateway(
            model_callable=_by_attempt_count(
                {
                    0: {"action": None},
                    1: {
                        "evaluation": {
                            "satisfied": False,
                            "reason": "The lookup failed; nothing else applies.",
                        },
                        "action": None,
                    },
                }
            )
        )
        orchestrator = self._orchestrator(model_reasoning_gateway=gateway)

        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        orchestrator.capability_planner.plan = lambda sr: {
            "status": "capability_selected",
            "tool_name": "gmail_search",
            "reason": "deterministic keyword match",
        }

        dispatcher = _FakeDispatcher(
            {
                "gmail_search": {
                    "status": "unavailable",
                    "message": "Gmail credentials missing.",
                }
            }
        )
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        result = orchestrator.process_user_input(
            session_id="s1", user_text="search my email for the invoice"
        )

        self.assertEqual(result["status"], "success")
        self.assertNotIn("source", result["plan"])
        self.assertEqual(result["execution"]["status"], "unavailable")

        self.assertIn("brain_evaluation", result)
        self.assertFalse(result["brain_evaluation"]["satisfied"])


class PausedExecutionStillNoOpsTests(_IsolatedOrchestratorCase):
    """A non-Brain-sourced plan that pauses on approval must still
    never be sent for evaluation - the existing _is_paused_execution
    guard inside _continue_brain_evaluation_loop must keep protecting
    every plan source, not only model_reasoning ones."""

    def test_awaiting_approval_from_learned_skill_does_not_evaluate(self):
        calls = []

        def _model_callable(request_json):
            calls.append(json.loads(request_json))
            return json.dumps({"action": None})

        gateway = ModelReasoningGateway(model_callable=_model_callable)

        # Route straight through the ApprovalGate's real pausing logic
        # by giving it a capability_registry entry that requires
        # approval - constructed and injected at orchestrator-
        # construction time (not mutated afterward), so
        # capability_registry/capability_feasibility/approval_gate all
        # stay consistent with each other, exactly like
        # ApprovalRequiredStillPausesTests in
        # test_orchestrator_model_driven_selection.py already does.
        from uri_core.core.approval_gate import ApprovalGate
        from uri_core.core.approval_store import ApprovalStore
        from uri_core.core.audit_trail import AuditTrail
        from uri_core.core.capability_registry import CapabilityRegistry

        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "active_tools": {
                        "risky_capability": {
                            "file_path": "x.py",
                            "class_name": "X",
                            "method": "run",
                            "approval_requirement": "user_approval_required",
                            "risk": "high",
                        }
                    }
                },
                f,
            )

        registry = CapabilityRegistry(registry_path=registry_path)
        approval_gate = ApprovalGate(
            dispatcher=None,
            capability_registry=registry,
            approval_store=ApprovalStore(
                storage_path=os.path.join(
                    self.temp_dir.name, "approvals.json"
                )
            ),
            audit_trail=AuditTrail(),
        )

        orchestrator = self._orchestrator(
            model_reasoning_gateway=gateway,
            approval_gate=approval_gate,
            capability_registry=registry,
        )
        approval_gate.dispatcher = orchestrator.dispatcher

        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: {
                "tool_name": "risky_capability",
                "task_type": "information retrieval",
                "domain": "email",
                "success_count": 1,
            }
        )

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertEqual(result["execution"]["status"], "awaiting_approval")
        # Only the initial reasoning call happened - the recovery loop
        # never ran a second (evaluation) call for a paused result.
        self.assertEqual(len(calls), 1)
        self.assertNotIn("brain_evaluation", result)


if __name__ == "__main__":
    unittest.main()
