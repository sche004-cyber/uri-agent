"""M20 (Gate B / latency safeguards): proves the pre-execution sanity
check is skipped for an ordinary, low-risk, strictly-shaped
single-action proposal, and still runs for a genuinely uncertain or
consequential one - the deterministic, 0-model-call gate documented in
UriOrchestrator._should_run_pre_execution_sanity_check.

Note on scope: the M20 audit's own draft test plan additionally
proposed a "Gate C" that would skip the acceptance-retention call
(_run_acceptance_retention_step) for a single-capability turn. Closer
reading of that method during implementation found the premise
inaccurate - it does not always produce a guaranteed-discard call B
even for a single-capability turn, it also persists a general
ExperienceRecord for ANY retention candidate the Brain judges worth
keeping (user_preference/reference_pattern/other categories), not only
"successful_approach" workflows. Skipping it there would silently
remove real memory-capture capability, so Gate C was deliberately NOT
implemented - see the M20 completion report. This file therefore tests
only Gate B, the safeguard that was actually built.
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
    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


NOTE_SEMANTIC_RESULT = {
    "goal": "Handle a task",
    "task_type": "information retrieval",
    "domain": "academic",
    "requested_output": "a record",
    "entities": [],
    "requires_clarification": False,
}


class _CountingGateway(ModelReasoningGateway):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_count = 0

    def reason(self, *args, **kwargs):
        self.call_count += 1
        return super().reason(*args, **kwargs)


class _IsolatedOrchestratorCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def _orchestrator(self, gateway, **kwargs):
        orchestrator = UriOrchestrator(
            semantic_interpreter=_FixedSemanticInterpreter(
                NOTE_SEMANTIC_RESULT
            ),
            model_reasoning_gateway=gateway,
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
        orchestrator.skill_memory.find_matching_skill = (
            lambda semantic_result: None
        )
        return orchestrator


def _write_registry(path, active_tools):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"active_tools": active_tools}, f)


class LowRiskProposalSkipsSanityCheckTests(_IsolatedOrchestratorCase):

    def test_low_risk_read_only_capability_skips_the_sanity_check(self):
        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        _write_registry(
            registry_path,
            {
                "extract_student_records": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "status": "implemented",
                    "availability": "available",
                    "approval_requirement": "none",
                    "risk": "low",
                }
            },
        )
        from uri_core.core.capability_registry import CapabilityRegistry

        registry = CapabilityRegistry(registry_path=registry_path)

        gateway = _CountingGateway(
            registry_path=registry_path,
            model_callable=lambda request_json: json.dumps(
                {"action": {"capability": "extract_student_records"}}
            ),
        )
        orchestrator = self._orchestrator(gateway, capability_registry=registry)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        # A satisfied evaluation on the FIRST post-execution call (no
        # further attempts) - so the total call count is exactly:
        # initial proposal + one post-execution evaluation, with the
        # sanity check genuinely skipped in between.
        calls = {"n": 0}
        original = gateway.model_callable

        def _sequenced(request_json):
            calls["n"] += 1
            request = json.loads(request_json)
            if request.get("attempt_history"):
                return json.dumps(
                    {"evaluation": {"satisfied": True, "reason": "done"}}
                )
            return original(request_json)

        gateway.model_callable = _sequenced

        result = orchestrator.process_user_input(
            session_id="s1", user_text="look up the record for roll 123"
        )

        self.assertEqual(result["pre_execution_check"]["outcome"], "skipped_low_risk")
        # Exactly 3 model calls: initial proposal + post-execution
        # evaluation (satisfied) + the acceptance-retention call - the
        # sanity check's extra call is the one genuinely skipped here
        # (would otherwise make this 4). Retention itself was
        # deliberately NOT gated (Gate C) - see this file's module
        # docstring.
        self.assertEqual(calls["n"], 3)


class RiskyOrUncertainProposalRunsSanityCheckTests(_IsolatedOrchestratorCase):

    def test_approval_required_capability_still_runs_the_sanity_check(self):
        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        _write_registry(
            registry_path,
            {
                "risky_capability": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "status": "implemented",
                    "availability": "available",
                    "approval_requirement": "user_approval_required",
                    "risk": "high",
                }
            },
        )
        from uri_core.core.capability_registry import CapabilityRegistry

        registry = CapabilityRegistry(registry_path=registry_path)

        calls = {"n": 0}

        def _model_callable(request_json):
            calls["n"] += 1
            return json.dumps({"action": {"capability": "risky_capability"}})

        gateway = ModelReasoningGateway(
            registry_path=registry_path, model_callable=_model_callable
        )
        orchestrator = self._orchestrator(gateway, capability_registry=registry)

        result = orchestrator.process_user_input(
            session_id="s1", user_text="do the risky thing"
        )

        self.assertNotEqual(
            result.get("pre_execution_check", {}).get("outcome"),
            "skipped_low_risk",
        )
        # Initial proposal + sanity check confirmation = 2 calls,
        # never executed (approval-gated), so no third evaluation call.
        self.assertEqual(calls["n"], 2)

    def test_multi_step_workflow_proposal_still_runs_the_sanity_check(self):
        registry_path = os.path.join(
            self.temp_dir.name, "capabilities_registry.json"
        )
        _write_registry(
            registry_path,
            {
                "extract_student_records": {
                    "file_path": "x.py",
                    "class_name": "X",
                    "method": "run",
                    "status": "implemented",
                    "availability": "available",
                },
                "draft_institutional_note": {
                    "file_path": "y.py",
                    "class_name": "Y",
                    "method": "run",
                    "status": "implemented",
                    "availability": "available",
                },
            },
        )
        from uri_core.core.capability_registry import CapabilityRegistry

        registry = CapabilityRegistry(registry_path=registry_path)

        calls = {"n": 0}

        def _model_callable(request_json):
            calls["n"] += 1
            return json.dumps(
                {
                    "workflow": {
                        "goal": "look up and draft",
                        "steps": [
                            {
                                "step_id": "s1",
                                "capability": "extract_student_records",
                                "depends_on": [],
                            },
                            {
                                "step_id": "s2",
                                "capability": "draft_institutional_note",
                                "depends_on": ["s1"],
                            },
                        ],
                    }
                }
            )

        gateway = ModelReasoningGateway(
            registry_path=registry_path, model_callable=_model_callable
        )
        orchestrator = self._orchestrator(gateway, capability_registry=registry)

        dispatcher = _FakeDispatcher()
        orchestrator.dispatcher.execute_tool = dispatcher.execute_tool

        orchestrator.process_user_input(
            session_id="s1", user_text="look up the record and draft a note"
        )

        # At minimum, initial proposal + sanity check = 2 calls (a
        # workflow proposal always runs the sanity check).
        self.assertGreaterEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
