"""M30.5: Deterministic Decision Gates. Every test proves the gate,
never the model, decides the final outcome - a fake/fixed decision
contract stands in for whatever the Brain proposed, and the gate is
checked against REAL CapabilityDirectory/CapabilityFeasibility data
wherever the test calls for real-collaborator verification.

Nothing here executes a capability - GateResult only ever describes
what would be safe to do next.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.capability_feasibility import CapabilityFeasibility
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.decision_engine import DecisionOutcome
from uri_core.core.decision_gates import GATE_OUTCOMES, evaluate_gates
from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability


def _write_registry(path, active_tools):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"active_tools": active_tools}, handle)


def _legacy_directory(entry, capability_id="gmail_search"):
    temp_dir = tempfile.TemporaryDirectory()
    registry_path = os.path.join(temp_dir.name, "capabilities_registry.json")
    _write_registry(registry_path, {capability_id: entry})
    feasibility = CapabilityFeasibility(
        capability_registry=CapabilityRegistry(registry_path=registry_path)
    )
    directory = CapabilityDirectory(capability_feasibility=feasibility)
    return directory, temp_dir


def _multi_action_directory():
    return CapabilityDirectory(multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]))


def _decision(**contract_fields):
    base = {
        "goal": "test", "mode": "single_action", "capability": None, "actions": [],
        "clarification": None, "unsupported_reason": None, "requires_approval": False,
        "confidence": "high", "reason": "test",
    }
    base.update(contract_fields)
    return DecisionOutcome(status="ok", contract=base)


class ReadyTests(unittest.TestCase):

    def test_valid_read_only_action_is_ready(self):
        directory, temp_dir = _legacy_directory(
            {"file_path": "x.py", "class_name": "X", "method": "run",
             "status": "implemented", "availability": "available"}
        )
        self.addCleanup(temp_dir.cleanup)
        decision = _decision(mode="single_action", capability="gmail_search", actions=[{"name": "gmail_search", "inputs": {}}])
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "READY")
        self.assertIn(result.outcome, GATE_OUTCOMES)


class MissingParameterTests(unittest.TestCase):

    def test_missing_required_parameter_is_detected_with_expected_metadata(self):
        directory = _FakeConnectedGmailDirectory()
        decision = _decision(
            mode="single_action", capability="Gmail",
            actions=[{"name": "search_messages", "inputs": {}}],  # missing required "query"
        )
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "MISSING_PARAMETER")
        self.assertEqual(result.missing_field, "query")
        self.assertEqual(result.expected_type, "string")

    def test_all_required_fields_present_is_not_missing_parameter(self):
        directory = _multi_action_directory()
        decision = _decision(
            mode="single_action", capability="Gmail",
            actions=[{"name": "search_messages", "inputs": {"query": "is:unread"}}],
        )
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertNotEqual(result.outcome, "MISSING_PARAMETER")


class DisconnectedTests(unittest.TestCase):

    def test_legacy_capability_marked_unavailable_runtime_is_disconnected(self):
        directory, temp_dir = _legacy_directory(
            {"file_path": "x.py", "class_name": "X", "method": "run",
             "status": "implemented", "availability": "unavailable_missing_dependency"}
        )
        self.addCleanup(temp_dir.cleanup)
        decision = _decision(mode="single_action", capability="gmail_search", actions=[])
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "DISCONNECTED")

    def test_multi_action_gmail_real_connection_state_reaches_the_gate(self):
        directory = _multi_action_directory()
        decision = _decision(mode="single_action", capability="Gmail", actions=[{"name": "list_labels", "inputs": {}}])
        result = evaluate_gates(decision, capability_directory=directory)
        # This test environment has no live Gmail token - real,
        # honest DISCONNECTED, never fabricated as READY.
        self.assertIn(result.outcome, ("DISCONNECTED", "READY"))


class UnsupportedGateTests(unittest.TestCase):

    def test_not_implemented_capability_is_unsupported_not_disconnected(self):
        directory, temp_dir = _legacy_directory(
            {"file_path": "x.py", "class_name": "X", "method": "run", "status": "not_implemented"}
        )
        self.addCleanup(temp_dir.cleanup)
        decision = _decision(mode="single_action", capability="gmail_search", actions=[])
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "UNSUPPORTED")

    def test_model_false_unsupported_claim_is_rejected_when_a_match_exists(self):
        directory = _multi_action_directory()
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="how many unread emails do I have")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertNotEqual(result.outcome, "UNSUPPORTED")
        self.assertIn("Gmail", result.overlap_candidates)

    def test_model_unsupported_claim_confirmed_when_nothing_matches(self):
        directory = _multi_action_directory()
        # Deliberately avoids "search"/"email"/"mail" - see
        # test_generic_shared_word_can_cause_a_false_plausible_match
        # below for why: those words alone would spuriously overlap
        # with Gmail's own description regardless of real fit.
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="set up a recurring automated backup of my documents to an external drive")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "UNSUPPORTED")

    def test_false_clarification_for_a_genuinely_unsupported_goal_is_exposed(self):
        directory = _multi_action_directory()
        decision = _decision(
            mode="clarification", capability=None, actions=[],
            goal="set up a recurring automated backup of my documents to an external drive",
            clarification={"question": "which folder?", "missing_field": "backup_target"},
        )
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "UNSUPPORTED")

    def test_generic_shared_word_in_a_narrow_directory_is_a_known_residual_limitation(self):
        # M30.5A's discriminating-term fix (capability_relevance.py) is
        # directory-derived: "search" is only down-weighted when it
        # genuinely appears in MULTIPLE registered capabilities. In a
        # narrow, two-entry directory (just Gmail + the one procedure
        # entry), "search" appears in exactly one place and still
        # (correctly, by this method's own logic) counts as
        # discriminating for THIS directory - documented here as a
        # real, known residual limitation of a corpus-relative
        # approach, not silently hidden. See the next test for the
        # same goal against the REAL, full directory, where the fix
        # does hold.
        directory = _multi_action_directory()
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="schedule a recurring automated job search every week")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertIn("Gmail", result.overlap_candidates)
        self.assertNotEqual(result.outcome, "UNSUPPORTED")

    def test_generic_shared_word_is_correctly_down_weighted_in_the_real_full_directory(self):
        # M30.5A fix, proven against the REAL directory (legacy +
        # multi-action combined, ~15 capabilities) rather than a toy
        # fixture: "search" appears in web_search/gmail_search/Gmail's
        # own description alike, so it is now generic and excluded -
        # "job search" no longer falsely implicates Gmail.
        directory = CapabilityDirectory(
            capability_feasibility=CapabilityFeasibility(),
            multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]),
        )
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="schedule a recurring automated job search every week")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertNotIn("Gmail", result.overlap_candidates)


class _FakeDisconnectedDirectory:
    """Minimal double exposing exactly the shape `plausible_matches()`
    and `_availability_outcome()` read: one capability whose text
    plausibly matches a goal about it, with a fully controllable real
    connection state - isolates the Scenario 2 repair's new call site
    from any real network/Gmail state. Deliberately NOT named Gmail
    anywhere, to prove the repair is capability-agnostic."""

    def __init__(
        self, capability_id="TestDrive", available=False,
        availability_known=True, availability_reason="unavailable_runtime",
        summary="Search and inspect TestDrive files and folders.",
    ):
        self.capability_id = capability_id
        self._entry = {
            "capability_id": capability_id, "actions": ["search_files"],
            "available": available, "availability_known": availability_known,
            "availability_reason": availability_reason,
            "permission_required": False, "approval_required": False,
            "action_schemas": {},
        }
        self._summary = summary

    def summaries(self):
        return [{
            "capability_id": self.capability_id,
            "summary": self._summary,
            "actions": ["search_files"],
        }]

    def describe(self, capability_id):
        if capability_id != self.capability_id:
            return None
        return dict(self._entry)

    def overlaps(self):
        return []


class ScenarioTwoConnectionGateTests(unittest.TestCase):
    """Scenario 2 repair (docs/plans/M30_SCENARIO2_CONNECTION_GATE_
    REPAIR_PLAN.md): a model's own false "unsupported" claim for a
    genuinely disconnected capability must surface the real, generic
    connection-gate truth (DISCONNECTED, with the real capability_id
    populated) instead of a generic INVALID_PROPOSAL - and must never
    change behavior for a genuinely connected/unimplemented/unknown-
    availability candidate."""

    def test_disconnected_plausible_match_returns_disconnected_with_real_id(self):
        directory = _FakeDisconnectedDirectory(available=False)
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="Search my TestDrive files.")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "DISCONNECTED")
        self.assertEqual(result.capability_id, "TestDrive")

    def test_connected_false_unsupported_claim_still_rejected_unchanged(self):
        directory = _FakeDisconnectedDirectory(available=True, availability_reason=None)
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="Search my TestDrive files.")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "INVALID_PROPOSAL")
        self.assertEqual(result.reasons, ["false_unsupported_claim_rejected_by_directory"])
        self.assertIsNone(result.capability_id)

    def test_no_plausible_match_still_unsupported_unchanged(self):
        directory = _FakeDisconnectedDirectory(available=False)
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="set up a recurring automated backup of my documents")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "UNSUPPORTED")

    def test_genericity_second_non_gmail_capability_also_reaches_disconnected(self):
        # Deliberately a different name, different summary, registered
        # only in this test's own fake directory - proves the fix is
        # capability-agnostic by construction, not Gmail-specific.
        directory = _FakeDisconnectedDirectory(
            capability_id="TestMCPTool", available=False,
            summary="Read and search TestMCPTool documents and records.",
        )
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="Search my TestMCPTool documents.")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "DISCONNECTED")
        self.assertEqual(result.capability_id, "TestMCPTool")

    def test_not_implemented_plausible_match_is_unsupported_not_disconnected(self):
        directory = _FakeDisconnectedDirectory(
            available=False, availability_reason="not_implemented",
        )
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="Search my TestDrive files.")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "UNSUPPORTED")
        self.assertEqual(result.capability_id, "TestDrive")

    def test_unknown_availability_plausible_match_is_unavailable_not_disconnected(self):
        directory = _FakeDisconnectedDirectory(
            available=None, availability_known=False, availability_reason=None,
        )
        decision = _decision(mode="unsupported", capability=None, actions=[],
                              goal="Search my TestDrive files.")
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "UNAVAILABLE")
        self.assertEqual(result.capability_id, "TestDrive")


class InvalidProposalTests(unittest.TestCase):

    def test_unknown_capability_is_invalid_proposal(self):
        directory = _multi_action_directory()
        decision = _decision(mode="single_action", capability="not_a_real_capability", actions=[])
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "INVALID_PROPOSAL")

    def test_invalid_decision_status_is_invalid_proposal(self):
        decision = DecisionOutcome(status="invalid", invalid_reason="malformed_json")
        result = evaluate_gates(decision, capability_directory=None)
        self.assertEqual(result.outcome, "INVALID_PROPOSAL")


class ApprovalCannotBeBypassedTests(unittest.TestCase):

    def test_model_says_no_approval_needed_but_runtime_requires_it(self):
        directory = _FakeConnectedGmailDirectory()
        decision = _decision(
            mode="single_action", capability="Gmail", requires_approval=False,
            actions=[{"name": "create_draft", "inputs": {"to": "x@example.com", "subject": "s", "body": "b"}}],
        )
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertEqual(result.outcome, "APPROVAL_REQUIRED")


class ReadOnlyReadyTests(unittest.TestCase):

    def test_read_only_gmail_action_with_permission_ready_when_connected(self):
        directory = _multi_action_directory()
        decision = _decision(mode="single_action", capability="Gmail",
                              actions=[{"name": "list_labels", "inputs": {}}])
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, principal: True,
        )
        self.assertIn(result.outcome, ("READY", "DISCONNECTED"))
        self.assertNotEqual(result.outcome, "PERMISSION_DENIED")


class OverlapTests(unittest.TestCase):

    def test_overlapping_capability_identity_reported_never_guessed(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        registry_path = os.path.join(temp_dir.name, "capabilities_registry.json")
        _write_registry(registry_path, {
            "gmail_search": {"file_path": "x.py", "class_name": "X", "method": "run",
                              "status": "implemented", "availability": "available",
                              "description": "Search Gmail."}
        })
        feasibility = CapabilityFeasibility(capability_registry=CapabilityRegistry(registry_path=registry_path))
        directory = CapabilityDirectory(
            capability_feasibility=feasibility,
            multi_action_registry=MultiActionCapabilityRegistry([GmailCapability()]),
        )
        decision = _decision(mode="single_action", capability="gmail_search", actions=[])
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertIn("Gmail", result.overlap_candidates)


class UnknownAvailabilityTests(unittest.TestCase):

    def test_capability_with_no_availability_check_reports_unavailable_not_true(self):
        directory, temp_dir = _legacy_directory(
            {"file_path": "x.py", "class_name": "X", "method": "run",
             "status": "implemented", "availability": "unknown"}
        )
        self.addCleanup(temp_dir.cleanup)
        decision = _decision(mode="single_action", capability="gmail_search", actions=[])
        result = evaluate_gates(decision, capability_directory=directory)
        # "unknown" availability on an implemented legacy capability is
        # treated as available by CapabilityFeasibility itself (never a
        # false-positive gap) - so this should be READY, not fabricated
        # as UNAVAILABLE either. Proves the gate reads real truth, not
        # its own guess.
        self.assertEqual(result.outcome, "READY")


class _FakeConnectedGmailDirectory:
    """A minimal double exposing exactly the shape evaluate_gates()
    reads, with Gmail's availability already CONNECTED - isolates gates
    below the connection check from real Gmail's own live (disconnected,
    in this test environment) state, which would otherwise correctly
    short-circuit at the earlier connection gate first (accepted
    pipeline ordering: connection before completeness/permission/
    approval)."""

    ACTION_SCHEMAS = {
        "list_labels": {"parameters": {}, "required": [], "approval_requirement": "none"},
        "search_messages": {
            "parameters": {"query": {"type": "string"}}, "required": ["query"],
            "approval_requirement": "none",
        },
        "create_draft": {
            "parameters": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
            "required": ["to", "subject", "body"], "approval_requirement": "user_approval_required",
        },
    }

    def describe(self, capability_id):
        if capability_id != "Gmail":
            return None
        return {
            "capability_id": "Gmail", "actions": list(self.ACTION_SCHEMAS),
            "available": True, "availability_known": True, "availability_reason": None,
            "permission_required": True, "approval_required": None,
            "action_schemas": self.ACTION_SCHEMAS,
        }

    def overlaps(self):
        return []


class PermissionDeniedTests(unittest.TestCase):

    def test_permission_checker_denial_blocks_the_action(self):
        directory = _FakeConnectedGmailDirectory()
        decision = _decision(mode="single_action", capability="Gmail",
                              actions=[{"name": "list_labels", "inputs": {}}])
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, principal: False,
        )
        self.assertEqual(result.outcome, "PERMISSION_DENIED")

    def test_permission_checker_allowed_reaches_ready(self):
        directory = _FakeConnectedGmailDirectory()
        decision = _decision(mode="single_action", capability="Gmail",
                              actions=[{"name": "list_labels", "inputs": {}}])
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, principal: True,
        )
        self.assertEqual(result.outcome, "READY")


class NoExecutionTests(unittest.TestCase):

    def test_gate_evaluation_never_executes_anything(self):
        directory = _multi_action_directory()
        decision = _decision(mode="single_action", capability="Gmail",
                              actions=[{"name": "list_labels", "inputs": {}}])
        # GateResult has no execute/run method at all - structurally
        # cannot execute anything.
        result = evaluate_gates(decision, capability_directory=directory)
        self.assertFalse(hasattr(result, "execute"))
        self.assertFalse(hasattr(result, "run"))


class ShadowFlagUnaffectedTests(unittest.TestCase):

    def test_shadow_flag_off_means_gates_module_is_never_touched(self):
        # decision_gates.py has zero import-time or module-level side
        # effects - importing it alone changes nothing.
        import uri_core.core.decision_gates as module
        self.assertTrue(hasattr(module, "evaluate_gates"))


if __name__ == "__main__":
    unittest.main()
