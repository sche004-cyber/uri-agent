"""M34 C3.3: Heterogeneous Multi-Capability Routing.

Proves that a `multi_action` Decision Contract whose `actions` name MORE
THAN ONE real capability (via each action's own optional `capability`
key) is authorized per-action, per-capability - never collapsed into a
single-capability verdict, never granted permission/approval inherited
from a sibling action's capability, and never silently executed
partially. Every single-capability contract (no action sets its own
"capability") must behave byte-identically to before this milestone -
proven directly against `decision_gates.py`'s own pre-existing fixtures
and `canonical_execution.py`'s own real dispatch/allowlist path.
"""

import unittest
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import patch

from uri_core.core.decision_engine import DecisionOutcome, _validate_contract
from uri_core.core.decision_gates import GateResult, evaluate_gates
from uri_core.core import canonical_execution as ce


def _decision(**contract_fields) -> DecisionOutcome:
    base = {
        "goal": "test", "mode": "multi_action", "capability": None, "actions": [],
        "clarification": None, "unsupported_reason": None, "requires_approval": False,
        "confidence": "high", "reason": "test",
    }
    base.update(contract_fields)
    return DecisionOutcome(status="ok", contract=base)


class _FakeTwoCapabilityDirectory:
    """A minimal double exposing exactly the shape `evaluate_gates()`
    reads, with TWO distinct, independently-connected capabilities -
    isolates the heterogeneous grouping/rollup logic from any live
    network/OAuth state, mirroring `test_decision_gates.py`'s own
    `_FakeConnectedGmailDirectory` pattern."""

    ENTRIES: Dict[str, Dict[str, Any]] = {
        "Gmail": {
            "capability_id": "Gmail", "actions": ["list_labels", "search_messages"],
            "available": True, "availability_known": True, "availability_reason": None,
            "permission_required": True, "approval_required": False,
            "action_schemas": {
                "list_labels": {"parameters": {}, "required": [], "approval_requirement": "none"},
                "search_messages": {
                    "parameters": {"query": {"type": "string"}}, "required": ["query"],
                    "approval_requirement": "none",
                },
            },
        },
        "Drive": {
            "capability_id": "Drive", "actions": ["list_files", "delete_file"],
            "available": True, "availability_known": True, "availability_reason": None,
            "permission_required": True, "approval_required": None,
            "action_schemas": {
                "list_files": {"parameters": {}, "required": [], "approval_requirement": "none"},
                "delete_file": {
                    "parameters": {"file_id": {"type": "string"}}, "required": ["file_id"],
                    "approval_requirement": "user_approval_required",
                },
            },
        },
    }

    def describe(self, capability_id):
        return self.ENTRIES.get(capability_id)

    def overlaps(self):
        return []


class HeterogeneousGateGroupingTests(unittest.TestCase):
    """decision_gates.py: per-action capability grouping and rollup."""

    def test_single_capability_contract_is_byte_identical_to_pre_c3_3_shape(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[{"name": "list_labels", "inputs": {}}, {"name": "search_messages", "inputs": {"query": "x"}}],
        )
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, p: True,
        )
        self.assertEqual(result.outcome, "READY")
        self.assertEqual(result.capability_id, "Gmail")
        self.assertEqual(result.sub_results, [])

    def test_all_actions_authorized_across_two_capabilities_is_ready_with_sub_results(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[
                {"name": "list_labels", "inputs": {}},
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
            ],
        )
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, p: True,
        )
        self.assertEqual(result.outcome, "READY")
        self.assertEqual(len(result.sub_results), 2)
        outcomes = {r.capability_id: r.outcome for r in result.sub_results}
        self.assertEqual(outcomes, {"Gmail": "READY", "Drive": "READY"})

    def test_one_action_denied_blocks_the_whole_chain_never_partial(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[
                {"name": "list_labels", "inputs": {}},
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
            ],
        )

        def checker(capability_id, principal):
            return capability_id == "Gmail"  # Drive is denied

        result = evaluate_gates(decision, capability_directory=directory, permission_checker=checker)
        self.assertEqual(result.outcome, "PERMISSION_DENIED")
        self.assertEqual(result.capability_id, "Drive")
        sub = {r.capability_id: r.outcome for r in result.sub_results}
        self.assertEqual(sub, {"Gmail": "READY", "Drive": "PERMISSION_DENIED"})

    def test_one_action_requires_approval_blocks_the_whole_chain(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[
                {"name": "list_labels", "inputs": {}},
                {"name": "delete_file", "inputs": {"file_id": "f1"}, "capability": "Drive"},
            ],
        )
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, p: True,
        )
        self.assertEqual(result.outcome, "APPROVAL_REQUIRED")
        self.assertEqual(result.capability_id, "Drive")

    def test_mixed_read_write_across_capabilities_read_ready_write_needs_approval(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[
                {"name": "search_messages", "inputs": {"query": "x"}},  # read, Gmail
                {"name": "delete_file", "inputs": {"file_id": "f1"}, "capability": "Drive"},  # write, Drive
            ],
        )
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, p: True,
        )
        self.assertEqual(result.outcome, "APPROVAL_REQUIRED")
        sub = {r.capability_id: r.outcome for r in result.sub_results}
        self.assertEqual(sub["Gmail"], "READY")
        self.assertEqual(sub["Drive"], "APPROVAL_REQUIRED")

    def test_repeated_same_capability_actions_stay_in_one_group(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[
                {"name": "list_labels", "inputs": {}},
                {"name": "search_messages", "inputs": {"query": "a"}},
                {"name": "search_messages", "inputs": {"query": "b"}},
            ],
        )
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, p: True,
        )
        self.assertEqual(result.outcome, "READY")
        self.assertEqual(result.sub_results, [])  # single group, unchanged shape

    def test_unmapped_per_action_capability_is_invalid_proposal_blocks_all(self):
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Gmail",
            actions=[
                {"name": "list_labels", "inputs": {}},
                {"name": "do_something", "inputs": {}, "capability": "NoSuchCapability"},
            ],
        )
        result = evaluate_gates(
            decision, capability_directory=directory, permission_checker=lambda cap, p: True,
        )
        self.assertEqual(result.outcome, "INVALID_PROPOSAL")
        self.assertEqual(result.capability_id, "NoSuchCapability")

    def test_no_permission_inheritance_between_capabilities(self):
        """A permission_checker that only ever recognizes Gmail must
        never let a Drive action through - proves each group's
        permission check reads ONLY its own capability_id."""
        directory = _FakeTwoCapabilityDirectory()
        decision = _decision(
            capability="Drive",
            actions=[{"name": "list_files", "inputs": {}}, {"name": "list_labels", "inputs": {}, "capability": "Gmail"}],
        )

        def checker(capability_id, principal):
            return capability_id == "Gmail"

        result = evaluate_gates(decision, capability_directory=directory, permission_checker=checker)
        self.assertEqual(result.outcome, "PERMISSION_DENIED")
        self.assertEqual(result.capability_id, "Drive")


class RollupDeterminismTests(unittest.TestCase):
    """The top-level rollup outcome must depend only on the SET of
    sub-results, never on the order `actions` listed their capabilities
    in - proven by evaluating the identical heterogeneous failure with
    the actions reversed and asserting an identical verdict, and by
    reusing this module's own established gate-check order
    (`_OUTCOME_PRECEDENCE`) rather than "first blocker wins."""

    def test_permission_denied_then_approval_required_same_regardless_of_order(self):
        directory = _FakeTwoCapabilityDirectory()
        forward_actions = [
            {"name": "list_labels", "inputs": {}},  # Gmail - would be denied
            {"name": "delete_file", "inputs": {"file_id": "f1"}, "capability": "Drive"},  # approval required
        ]
        reversed_actions = list(reversed(forward_actions))

        def checker(capability_id, principal):
            return capability_id != "Gmail"  # only Gmail is denied

        forward = evaluate_gates(
            _decision(capability="Gmail", actions=forward_actions),
            capability_directory=directory, permission_checker=checker,
        )
        backward = evaluate_gates(
            _decision(capability="Gmail", actions=reversed_actions),
            capability_directory=directory, permission_checker=checker,
        )
        # PERMISSION_DENIED (gate 6) outranks APPROVAL_REQUIRED (gate 7)
        # in the module's own established gate order - true regardless
        # of which action the model listed first.
        self.assertEqual(forward.outcome, "PERMISSION_DENIED")
        self.assertEqual(forward.outcome, backward.outcome)
        self.assertEqual(forward.capability_id, backward.capability_id)
        self.assertEqual(forward.capability_id, "Gmail")

    def test_disconnected_outranks_missing_parameter_regardless_of_order(self):
        directory = _FakeTwoCapabilityDirectory()
        # Drive's own entry (unlike the shared class default) is
        # rebuilt here as disconnected for one call, connected for the
        # comparison, to isolate the precedence claim without adding a
        # third fixture class.
        class _DisconnectedDrive(_FakeTwoCapabilityDirectory):
            def describe(self, capability_id):
                entry = super().describe(capability_id)
                if entry is None or capability_id != "Drive":
                    return entry
                return {**entry, "available": False, "availability_reason": "unavailable_runtime"}

        forward_actions = [
            {"name": "search_messages", "inputs": {}},  # Gmail - missing required "query"
            {"name": "list_files", "inputs": {}, "capability": "Drive"},  # Drive - disconnected
        ]
        reversed_actions = list(reversed(forward_actions))

        forward = evaluate_gates(
            _decision(capability="Gmail", actions=forward_actions),
            capability_directory=_DisconnectedDrive(), permission_checker=lambda c, p: True,
        )
        backward = evaluate_gates(
            _decision(capability="Gmail", actions=reversed_actions),
            capability_directory=_DisconnectedDrive(), permission_checker=lambda c, p: True,
        )
        # DISCONNECTED (gate 5) outranks MISSING_PARAMETER (gate 4) in
        # the module's own established gate order.
        self.assertEqual(forward.outcome, "DISCONNECTED")
        self.assertEqual(forward.outcome, backward.outcome)
        self.assertEqual(forward.capability_id, backward.capability_id)
        self.assertEqual(forward.capability_id, "Drive")

    def test_tie_between_same_outcome_two_capabilities_is_order_independent(self):
        """Two sub-results sharing the SAME outcome must still resolve
        to the identical top-level capability_id regardless of action
        order - proves the tie-break (alphabetical capability_id) is
        itself order-independent, not merely the primary precedence
        rank."""
        directory = _FakeTwoCapabilityDirectory()
        forward_actions = [
            {"name": "list_labels", "inputs": {}},
            {"name": "list_files", "inputs": {}, "capability": "Drive"},
        ]
        reversed_actions = list(reversed(forward_actions))

        forward = evaluate_gates(
            _decision(capability="Gmail", actions=forward_actions),
            capability_directory=directory, permission_checker=lambda c, p: False,
        )
        backward = evaluate_gates(
            _decision(capability="Gmail", actions=reversed_actions),
            capability_directory=directory, permission_checker=lambda c, p: False,
        )
        self.assertEqual(forward.outcome, "PERMISSION_DENIED")
        self.assertEqual(forward.outcome, backward.outcome)
        # Both capabilities are denied identically; the alphabetical
        # tie-break must pick the same one either way ("Drive" < "Gmail").
        self.assertEqual(forward.capability_id, backward.capability_id)
        self.assertEqual(forward.capability_id, "Drive")

    def test_rollup_precedence_matches_established_gate_order(self):
        from uri_core.core.decision_gates import _OUTCOME_PRECEDENCE
        expected_order_positions = {
            "DEGRADED": 0, "INVALID_PROPOSAL": 1, "DISCONNECTED": 2,
            "UNSUPPORTED": 3, "UNAVAILABLE": 4, "MISSING_PARAMETER": 5,
            "PERMISSION_DENIED": 6, "APPROVAL_REQUIRED": 7,
        }
        self.assertEqual(
            {outcome: _OUTCOME_PRECEDENCE.index(outcome) for outcome in expected_order_positions},
            expected_order_positions,
        )


class ContractValidationTests(unittest.TestCase):
    """decision_engine.py: `_validate_contract` accepts and checks the
    optional per-action `capability` key, additively."""

    def test_valid_per_action_capability_is_accepted(self):
        directory = _FakeTwoCapabilityDirectory()
        contract = {
            "goal": "g", "mode": "multi_action", "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}},
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
            ],
            "clarification": None, "unsupported_reason": None, "requires_approval": False,
            "confidence": "high", "reason": "r",
        }
        outcome = _validate_contract(contract, {"Gmail", "Drive"}, directory)
        self.assertEqual(outcome.status, "ok")

    def test_unknown_per_action_capability_is_rejected(self):
        directory = _FakeTwoCapabilityDirectory()
        contract = {
            "goal": "g", "mode": "multi_action", "capability": "Gmail",
            "actions": [{"name": "x", "inputs": {}, "capability": "NotReal"}],
            "clarification": None, "unsupported_reason": None, "requires_approval": False,
            "confidence": "high", "reason": "r",
        }
        outcome = _validate_contract(contract, {"Gmail"}, directory)
        self.assertEqual(outcome.status, "invalid")
        self.assertIn("unknown_capability_for_action", outcome.invalid_reason)

    def test_unknown_action_for_a_valid_per_action_capability_is_rejected(self):
        directory = _FakeTwoCapabilityDirectory()
        contract = {
            "goal": "g", "mode": "multi_action", "capability": "Gmail",
            "actions": [{"name": "does_not_exist", "inputs": {}, "capability": "Drive"}],
            "clarification": None, "unsupported_reason": None, "requires_approval": False,
            "confidence": "high", "reason": "r",
        }
        outcome = _validate_contract(contract, {"Gmail", "Drive"}, directory)
        self.assertEqual(outcome.status, "invalid")
        self.assertIn("unknown_action", outcome.invalid_reason)

    def test_single_capability_contract_validation_unchanged(self):
        directory = _FakeTwoCapabilityDirectory()
        contract = {
            "goal": "g", "mode": "single_action", "capability": "Gmail",
            "actions": [{"name": "list_labels", "inputs": {}}],
            "clarification": None, "unsupported_reason": None, "requires_approval": False,
            "confidence": "high", "reason": "r",
        }
        outcome = _validate_contract(contract, {"Gmail", "Drive"}, directory)
        self.assertEqual(outcome.status, "ok")

    def test_per_action_capability_on_non_multi_action_is_rejected(self):
        directory = _FakeTwoCapabilityDirectory()
        contract = {
            "goal": "g", "mode": "single_action", "capability": "Gmail",
            "actions": [{"name": "list_files", "inputs": {}, "capability": "Drive"}],
            "clarification": None, "unsupported_reason": None, "requires_approval": False,
            "confidence": "high", "reason": "r",
        }
        outcome = _validate_contract(contract, {"Gmail", "Drive"}, directory)
        self.assertEqual(outcome.status, "invalid")
        self.assertEqual(outcome.invalid_reason, "per_action_capability_requires_multi_action")

    def test_null_per_action_capability_inherits_top_level_capability(self):
        directory = _FakeTwoCapabilityDirectory()
        contract = {
            "goal": "g", "mode": "multi_action", "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}, "capability": None},
                {"name": "search_messages", "inputs": {"query": "x"}, "capability": None},
            ],
            "clarification": None, "unsupported_reason": None, "requires_approval": False,
            "confidence": "high", "reason": "r",
        }
        outcome = _validate_contract(contract, {"Gmail", "Drive"}, directory)
        self.assertEqual(outcome.status, "ok")


class CanonicalAllowlistTests(unittest.TestCase):
    """canonical_execution.py: the allowlist rollback lever must cover
    EVERY capability a heterogeneous proposal touches, not only the
    contract's own top-level `capability`."""

    def test_decide_fallback_reason_checks_every_capability_id_when_given(self):
        with patch.object(ce, "_current_allowlist", return_value=frozenset({"Gmail"})):
            reason = ce.decide_fallback_reason(
                gate_outcome="READY", capability_id="Gmail", mode="multi_action",
                capability_ids=["Gmail", "Drive"],
            )
        self.assertEqual(reason, "canonical_killswitch_not_allowlisted")

    def test_decide_fallback_reason_allows_when_every_capability_id_is_allowlisted(self):
        with patch.object(ce, "_current_allowlist", return_value=frozenset({"Gmail", "Drive"})):
            reason = ce.decide_fallback_reason(
                gate_outcome="READY", capability_id="Gmail", mode="multi_action",
                capability_ids=["Gmail", "Drive"],
            )
        self.assertIsNone(reason)

    def test_omitted_capability_ids_falls_back_to_single_capability_id_unchanged(self):
        with patch.object(ce, "_current_allowlist", return_value=frozenset({"Gmail"})):
            reason = ce.decide_fallback_reason(
                gate_outcome="READY", capability_id="Gmail", mode="multi_action",
            )
        self.assertIsNone(reason)

    def test_top_level_gmail_all_actions_drive_is_not_allowlist_blind(self):
        contract = {
            "mode": "multi_action", "capability": "Gmail",
            "actions": [
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
            ],
        }
        self.assertEqual(ce.effective_capability_ids(contract), ["Drive"])
        with patch.object(ce, "_current_allowlist", return_value=frozenset({"Gmail"})):
            reason = ce.decide_fallback_reason(
                gate_outcome="READY", capability_id="Gmail", mode="multi_action",
                capability_ids=ce.effective_capability_ids(contract),
            )
        self.assertEqual(reason, "canonical_killswitch_not_allowlisted")

    def test_gmail_drive_chain_checks_both_effective_capabilities(self):
        contract = {
            "mode": "multi_action", "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}},
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
            ],
        }
        with patch.object(ce, "_current_allowlist", return_value=frozenset({"Gmail"})):
            blocked = ce.decide_fallback_reason(
                gate_outcome="READY", capability_id="Gmail", mode="multi_action",
                capability_ids=ce.effective_capability_ids(contract),
            )
        with patch.object(ce, "_current_allowlist", return_value=frozenset({"Gmail", "Drive"})):
            allowed = ce.decide_fallback_reason(
                gate_outcome="READY", capability_id="Gmail", mode="multi_action",
                capability_ids=ce.effective_capability_ids(contract),
            )
        self.assertEqual(blocked, "canonical_killswitch_not_allowlisted")
        self.assertIsNone(allowed)


class HeterogeneousApprovalAtomicityTests(unittest.TestCase):
    def test_ready_read_and_approval_required_write_execute_zero_actions(self):
        """The canonical entry point must not enter chain dispatch when
        one heterogeneous action needs approval, even if an earlier action
        is READY and would otherwise execute first."""
        executed_steps = []

        class _Registry:
            def get_capability(self, capability_id):
                return object() if capability_id in {"Gmail", "Drive"} else None

        class _Dispatch:
            registry = _Registry()

            def dispatch_chain_explicit(self, steps, **kwargs):
                executed_steps.extend(steps)
                return {"status": "success", "execution": {"status": "success"}}

        contract = {
            "mode": "multi_action", "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}, "capability": "Gmail"},
                {"name": "delete_file", "inputs": {"file_id": "f1"}, "capability": "Drive"},
            ],
            "goal": "g", "clarification": None, "unsupported_reason": None,
            "reason": "r", "requires_approval": False, "confidence": "high",
        }
        gate = GateResult(
            outcome="APPROVAL_REQUIRED", capability_id="Drive",
            sub_results=[
                GateResult(outcome="READY", capability_id="Gmail", action_names=["list_labels"]),
                GateResult(outcome="APPROVAL_REQUIRED", capability_id="Drive", action_names=["delete_file"]),
            ],
        )
        orchestrator = SimpleNamespace(
            multi_action_dispatch=_Dispatch(), session_manager=None,
            capability_registry=None, conversation_history=None,
        )
        turn_state = SimpleNamespace(data={"turn": {"user_text": "g"}})
        with patch.object(ce, "build_turn_state_and_directory", return_value=(turn_state, object())), \
             patch.object(ce, "propose_decision", return_value=DecisionOutcome(status="ok", contract=contract)), \
             patch("uri_core.core.decision_gates.evaluate_gates", return_value=gate):
            result = ce.run_canonical_for_ask(
                orchestrator=orchestrator, session_id="s1", user_text="g", principal=None,
            )
        self.assertEqual(executed_steps, [])
        self.assertEqual(result["status"], "approval_required")
        self.assertEqual(result["execution"]["status"], "not_executed")


class MixedRegistryDispatchGuardTests(unittest.TestCase):
    """canonical_execution.py: `_execute_canonical` must never attempt a
    heterogeneous chain across a legacy (non-multi-action-registered)
    capability and a multi-action one - no existing execution boundary
    can run that mix safely, so it must decline (fall back), never
    silently drop or misroute an action."""

    class _FakeRegistry:
        def __init__(self, known):
            self._known = set(known)

        def get_capability(self, capability_id):
            return object() if capability_id in self._known else None

    class _FakeDispatch:
        def __init__(self, known):
            self.registry = MixedRegistryDispatchGuardTests._FakeRegistry(known)

    class _FakeOrchestrator:
        def __init__(self, known):
            self.multi_action_dispatch = MixedRegistryDispatchGuardTests._FakeDispatch(known)

    def test_all_actions_in_the_multi_action_registry_dispatches_normally(self):
        orchestrator = self._FakeOrchestrator({"Gmail", "Drive"})
        contract = {
            "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}},
                {"name": "list_files", "inputs": {}, "capability": "Drive"},
            ],
        }
        with patch.object(ce, "_execute_multi_action", return_value={"status": "success"}) as mocked:
            result = ce._execute_canonical(
                contract, orchestrator=orchestrator, session_id="s1", user_text="t", principal=None,
            )
        mocked.assert_called_once()
        self.assertEqual(result, {"status": "success"})

    def test_an_action_naming_a_non_registered_capability_declines_rather_than_misroutes(self):
        orchestrator = self._FakeOrchestrator({"Gmail"})  # "remember_fact" is NOT in the registry
        contract = {
            "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}},
                {"name": "remember_fact", "inputs": {}, "capability": "remember_fact"},
            ],
        }
        with patch.object(ce, "_execute_multi_action") as mocked:
            result = ce._execute_canonical(
                contract, orchestrator=orchestrator, session_id="s1", user_text="t", principal=None,
            )
        mocked.assert_not_called()
        self.assertIsNone(result)


class RunCanonicalForAskMixedRegistryFallbackTests(unittest.TestCase):
    """End-to-end proof, at the real `run_canonical_for_ask()` entry
    point (not just the `_execute_canonical()` unit level): when the
    mixed-registry guard declines a heterogeneous proposal, the turn
    genuinely falls back - no execution path runs (Gmail's action is
    NOT quietly executed alone, `remember_fact` is NOT quietly executed
    alone, nothing is flattened into a single-capability call with
    weaker identity), and the caller (`server.py`'s `/ask`) receives
    only the same `{"_canonical_fallback": True, "fallback_reason":
    ...}` shape every other declined canonical turn produces - which
    structurally carries no capability-specific execution detail at
    all, so the subsequent legacy path re-decides entirely from the
    raw user_text, never inheriting anything from the rejected
    canonical attempt."""

    def test_rejected_heterogeneous_chain_never_executes_and_falls_back_cleanly(self):
        orchestrator = SimpleNamespace(
            multi_action_dispatch=MixedRegistryDispatchGuardTests._FakeDispatch({"Gmail"}),
            session_manager=None, capability_registry=None, conversation_history=None,
        )
        fake_turn_state = SimpleNamespace(data={"turn": {"user_text": "t"}})
        fake_contract = {
            "mode": "multi_action", "capability": "Gmail",
            "actions": [
                {"name": "list_labels", "inputs": {}},
                {"name": "remember_fact", "inputs": {}, "capability": "remember_fact"},
            ],
        }
        fake_decision = DecisionOutcome(status="ok", contract=fake_contract)
        # Deliberately the BEST case for a would-be authority bypass:
        # the real per-capability gate pipeline already said READY for
        # both groups (this fixture stands in for that real, already-
        # proven-correct result so this test isolates ONLY the
        # dispatch-layer registry-mixing guard, not gate logic already
        # covered above).
        fake_gate_result = GateResult(
            outcome="READY", capability_id="Gmail",
            sub_results=[
                GateResult(outcome="READY", capability_id="Gmail"),
                GateResult(outcome="READY", capability_id="remember_fact"),
            ],
        )

        with patch.object(ce, "build_turn_state_and_directory", return_value=(fake_turn_state, object())), \
             patch.object(ce, "propose_decision", return_value=fake_decision), \
             patch("uri_core.core.decision_gates.evaluate_gates", return_value=fake_gate_result), \
             patch.object(ce, "_execute_multi_action") as mocked_multi_action, \
             patch.object(ce, "_execute_legacy_capability") as mocked_legacy:
            result = ce.run_canonical_for_ask(
                orchestrator=orchestrator, session_id="s1", user_text="t", principal=None,
            )

        # No execution boundary ran at all - not the multi-action chain
        # (remember_fact's own special case was folded into this same
        # boundary by M33 Batch D and no longer exists separately - see
        # canonical_execution.py's deleted _execute_remember_fact), not
        # the legacy single-tool boundary. The heterogeneous proposal
        # was never flattened into executing ONE of its two actions
        # with the other silently dropped, and never routed through
        # legacy AS IF it had been a single-capability proposal.
        mocked_multi_action.assert_not_called()
        mocked_legacy.assert_not_called()

        self.assertTrue(result.get("_canonical_fallback"))
        self.assertEqual(result.get("fallback_reason"), "execution_dispatch_returned_none")
        # The fallback envelope itself carries no capability/action
        # identity from the rejected proposal - the legacy path that
        # runs next (server.py's own existing chain, untouched by this
        # milestone) re-decides purely from `user_text`, never from
        # this rejected canonical attempt's own capability list.
        self.assertEqual(set(result.keys()), {"_canonical_fallback", "fallback_reason", "gate_outcome"})


if __name__ == "__main__":
    unittest.main()
