"""M33.3 S2: Action.wrong_binding_impact and the execution-gate check.

Deterministic; no model, provider, or network. Plan:
docs/plans/M33_3_S2_STATE.md (sections 4-9).
"""

import ast
import hashlib
from enum import Enum
from pathlib import Path

import pytest

from uri_core.capabilities import (
    Action,
    ApprovalRequirement,
    Capability,
    LegacyCapabilityAdapter,
    MultiActionCapabilityRegistry,
    MultiActionExecutor,
    ReferenceBinding,
    ReferenceBindingStatus,
    WrongBindingImpact,
    evaluate_wrong_binding_gate,
)
from uri_core.capabilities.base import EffectType
from uri_core.capabilities.gmail.capability import GmailCapability
from uri_core.capabilities.registry import (
    KNOWN_CAPABILITY_EFFECTS,
    KNOWN_CAPABILITY_WRONG_BINDING_IMPACT,
)
from uri_core.capabilities.wrong_binding import (
    CONFIRM_ONE,
    GateOutcome,
    effective_wrong_binding_impact,
)
from uri_v1.turn.rar_clarification_contract import BindingState
from uri_v1.turn.rar_clarification_contract import WrongBindingImpact as S1WrongBindingImpact

ROOT = Path(__file__).resolve().parents[1]
C, T = ReferenceBindingStatus.CONFIRMED, ReferenceBindingStatus.TENTATIVE
NONE, REC, CONS = WrongBindingImpact.NONE, WrongBindingImpact.RECOVERABLE, WrongBindingImpact.CONSEQUENTIAL


def _action(impact=None, **kwargs):
    kwargs.setdefault("handler", lambda **_: {"status": "success"})
    return Action(name="act", description="d", wrong_binding_impact=impact, **kwargs)


def _b(key, status, cid="c1"):
    return ReferenceBinding(key, cid, status)


# 1. Taxonomy and S1 value parity -------------------------------------------------

def test_taxonomy_is_exactly_three_values_and_matches_s1():
    assert [v.value for v in WrongBindingImpact] == ["NONE", "RECOVERABLE", "CONSEQUENTIAL"]
    assert {v.value for v in WrongBindingImpact} == {v.value for v in S1WrongBindingImpact}


def test_binding_status_values_are_s1_binding_state_names():
    assert {s.value for s in ReferenceBindingStatus} == {"CONFIRMED", "TENTATIVE"}
    s1_values = {s.value for s in BindingState}
    assert {s.value for s in ReferenceBindingStatus} <= s1_values


# 2. Action field -------------------------------------------------------------------

def test_action_field_defaults_to_undeclared_independent_of_effect_type():
    for effect in EffectType:
        action = Action(name="a", description="d", effect_type=effect)
        assert action.wrong_binding_impact is None
        assert effective_wrong_binding_impact(action) == (CONS, False)


def test_action_field_coerces_exact_strings_and_rejects_invalid():
    assert _action("RECOVERABLE").wrong_binding_impact is REC
    assert _action(NONE).wrong_binding_impact is NONE
    for bad in ("recoverable", "LOW", "", "SAFE"):
        with pytest.raises(ValueError):
            _action(bad)


def test_foreign_string_enum_cannot_declare_low_impact():
    class ForeignImpact(str, Enum):
        RECOVERABLE = "RECOVERABLE"

    with pytest.raises(ValueError):
        _action(ForeignImpact.RECOVERABLE)
    assert _adapted({"id": "gmail_create_draft", "wrong_binding_impact": ForeignImpact.RECOVERABLE}) is None


# 3. effective impact -----------------------------------------------------------------

@pytest.mark.parametrize("impact", list(WrongBindingImpact))
def test_effective_impact_returns_declared_value(impact):
    assert effective_wrong_binding_impact(_action(impact)) == (impact, True)


@pytest.mark.parametrize("tampered", ["RECOVERABLE", "NONE", "bogus", 0, object(), EffectType.READ_ONLY])
def test_post_construction_tampering_fails_closed(tampered):
    action = _action(NONE)
    action.wrong_binding_impact = tampered
    assert effective_wrong_binding_impact(action) == (CONS, False)


def test_effective_impact_is_read_live_not_cached():
    action = _action(REC)
    bindings = [_b("r1", T)]
    assert evaluate_wrong_binding_gate(action, bindings).allowed
    action.wrong_binding_impact = CONS
    assert not evaluate_wrong_binding_gate(action, bindings).allowed
    action.wrong_binding_impact = None
    assert not evaluate_wrong_binding_gate(action, bindings).allowed


def test_object_without_field_is_undeclared():
    assert effective_wrong_binding_impact(object()) == (CONS, False)


# 4. Decision table G1-G7 ------------------------------------------------------------

IMPACTS = [None, NONE, REC, CONS]
TABLE = []
for impact in IMPACTS:
    TABLE.append((impact, None, True, GateOutcome.NOT_APPLICABLE, (), None))                     # G1
    TABLE.append((impact, [], True, GateOutcome.NO_REFERENCE_BINDING, (), None))                 # G4
    TABLE.append((impact, [_b("r1", C)], True, GateOutcome.ALLOWED_CONFIRMED, (), None))         # G5
    TABLE.append((impact, (_b("r1", C), _b("r2", C, "c2")), True, GateOutcome.ALLOWED_CONFIRMED, (), None))
    for bindings in ([_b("r1", T)], [_b("r1", C), _b("r2", T, "c2")]):
        if impact in (NONE, REC):
            TABLE.append((impact, bindings, True, GateOutcome.ALLOWED_TENTATIVE_RECOVERABLE, (), None))  # G6
        else:
            keys = tuple(b.ref_key for b in bindings if b.status is T)
            TABLE.append((impact, bindings, False, GateOutcome.CONFIRMATION_REQUIRED, keys, CONFIRM_ONE))  # G7


@pytest.mark.parametrize("impact,bindings,allowed,outcome,blocking,clarification", TABLE)
def test_decision_table(impact, bindings, allowed, outcome, blocking, clarification):
    decision = evaluate_wrong_binding_gate(_action(impact), bindings)
    assert decision.allowed is allowed
    assert decision.outcome is outcome
    assert decision.blocking_ref_keys == blocking
    assert decision.required_clarification == clarification
    assert decision.wrong_binding_impact is (impact or CONS)
    assert decision.impact_declared is (impact is not None)


def test_multiple_tentative_bindings_all_reported_when_blocked():
    decision = evaluate_wrong_binding_gate(
        _action(CONS), [_b("r1", T), _b("r2", C, "c2"), _b("r3", T, "c3")])
    assert decision.blocking_ref_keys == ("r1", "r3")


# 5. Invalid bindings (G2/G3) ----------------------------------------------------------

INVALID = [
    {"r1": _b("r1", C)},                          # G2: mapping
    "CONFIRMED",                                  # G2: string
    _b("r1", C),                                  # G2: bare binding
    {_b("r1", C)},                                # G2: set
    [("r1", "c1", C)],                            # G3: tuple, not a ReferenceBinding
    [{"ref_key": "r1", "candidate_id": "c1", "status": "CONFIRMED"}],
    [_b("", C)], [_b("  ", C)], [_b("r1", C, "")],
    [ReferenceBinding("r1", "c1", "CONFIRMED")],  # raw string status
    [ReferenceBinding("r1", "c1", "PENDING")],
    [ReferenceBinding("r1", "c1", "REJECTED")],
    [ReferenceBinding("r1", "c1", "TENTATIVE_APPLIED")],
    [ReferenceBinding("r1", "c1", "tentative")],
    [ReferenceBinding("r1", "c1", None)],
    [ReferenceBinding(1, "c1", C)],
    [_b("r1", C), _b("r1", T, "c2")],             # duplicate ref_key
    [_b("r1", C), None],
]


@pytest.mark.parametrize("impact", IMPACTS)
@pytest.mark.parametrize("bindings", INVALID)
def test_invalid_bindings_fail_closed_for_every_impact(impact, bindings):
    decision = evaluate_wrong_binding_gate(_action(impact), bindings)
    assert not decision.allowed
    assert decision.outcome is GateOutcome.INVALID_REFERENCE_BINDING


def test_binding_subclass_is_rejected():
    class Spoof(ReferenceBinding):
        pass
    decision = evaluate_wrong_binding_gate(_action(REC), [Spoof("r1", "c1", C)])
    assert decision.outcome is GateOutcome.INVALID_REFERENCE_BINDING


@pytest.mark.parametrize("missing", ["ref_key", "candidate_id", "status"])
def test_binding_with_missing_field_fails_closed(missing):
    binding = _b("r1", C)
    object.__delattr__(binding, missing)
    for bindings in ([binding], [_b("valid", C), binding]):
        decision = evaluate_wrong_binding_gate(_action(REC), bindings)
        assert decision.allowed is False
        assert decision.outcome is GateOutcome.INVALID_REFERENCE_BINDING


def test_malformed_object_is_rejected_before_reading_its_fields():
    class Malformed:
        @property
        def ref_key(self):
            raise RuntimeError("untrusted property")

    decision = evaluate_wrong_binding_gate(_action(REC), [_b("valid", C), Malformed()])
    assert decision.allowed is False
    assert decision.outcome is GateOutcome.INVALID_REFERENCE_BINDING


# 6. Executor integration -------------------------------------------------------------

def _executor(impact=None, approval=ApprovalRequirement.NONE, calls=None):
    calls = calls if calls is not None else []

    def handler(**inputs):
        calls.append(inputs)
        return {"status": "success"}

    action = Action(name="act", description="d", parameters={"x": {"type": "string"}},
                    approval_requirement=approval, handler=handler, wrong_binding_impact=impact)
    registry = MultiActionCapabilityRegistry([Capability(name="cap", description="d", category="t",
                                                         actions={"act": action})])
    return MultiActionExecutor(registry), calls


@pytest.mark.parametrize("impact", IMPACTS)
def test_executor_without_bindings_is_unchanged(impact):
    executor, calls = _executor(impact)
    assert executor.execute("cap", "act", {"x": "1"})["status"] == "success"
    assert calls == [{"x": "1"}]
    entry = executor.audit_log[-1]
    assert not any(key.startswith("wrong_binding") for key in entry)
    executor, _ = _executor(impact, ApprovalRequirement.USER_APPROVAL_REQUIRED)
    assert executor.execute("cap", "act", {"x": "1"})["status"] == "approval_required"


@pytest.mark.parametrize("impact", [None, CONS])
def test_executor_blocks_tentative_consequential_even_with_approval(impact):
    for approval in ApprovalRequirement:
        executor, calls = _executor(impact, approval)
        result = executor.execute("cap", "act", {"x": "1"}, user_approved=True, admin_approved=True,
                                  reference_bindings=[_b("r1", T)])
        assert result["status"] == "reference_confirmation_required"
        assert result["required_clarification"] == CONFIRM_ONE
        assert result["blocking_ref_keys"] == ["r1"]
        assert result["wrong_binding_impact"] == "CONSEQUENTIAL"
        assert result["impact_declared"] is (impact is not None)
        assert calls == []


def test_executor_gate_runs_before_approval_prompt():
    executor, calls = _executor(CONS, ApprovalRequirement.USER_APPROVAL_REQUIRED)
    result = executor.execute("cap", "act", {"x": "1"}, reference_bindings=[_b("r1", T)])
    assert result["status"] == "reference_confirmation_required"
    assert calls == []


@pytest.mark.parametrize("impact,bindings", [(NONE, [_b("r1", T)]), (REC, [_b("r1", T)]),
                                             (None, [_b("r1", C)]), (CONS, [_b("r1", C)])])
def test_executor_allowed_gate_still_requires_approval(impact, bindings):
    executor, calls = _executor(impact, ApprovalRequirement.USER_APPROVAL_REQUIRED)
    assert executor.execute("cap", "act", {"x": "1"}, reference_bindings=bindings)["status"] == "approval_required"
    assert calls == []
    assert executor.execute("cap", "act", {"x": "1"}, user_approved=True,
                            reference_bindings=bindings)["status"] == "success"
    assert len(calls) == 1


def test_executor_invalid_bindings_status():
    executor, calls = _executor(REC)
    result = executor.execute("cap", "act", {"x": "1"},
                              reference_bindings=[ReferenceBinding("r1", "c1", "PENDING")])
    assert result["status"] == "invalid_reference_binding"
    assert calls == []


def test_executor_missing_binding_field_never_calls_handler():
    executor, calls = _executor(REC)
    binding = _b("r1", C)
    object.__delattr__(binding, "candidate_id")
    result = executor.execute("cap", "act", {"x": "1"}, reference_bindings=[binding])
    assert result["status"] == "invalid_reference_binding"
    assert calls == []


def test_executor_schema_errors_still_precede_gate():
    executor, _ = _executor(CONS)
    result = executor.execute("cap", "act", {"bad": 1}, reference_bindings=[_b("r1", T)])
    assert result["status"] == "invalid_input"


# 7. Chains -----------------------------------------------------------------------------

def test_chain_step_bindings_are_gated_per_step():
    calls = []

    def handler(**inputs):
        calls.append(inputs)
        return {"status": "success", "v": "ok"}

    actions = {
        "draft": Action(name="draft", description="d", handler=handler, wrong_binding_impact=REC),
        "send": Action(name="send", description="d", handler=handler, wrong_binding_impact=CONS),
    }
    registry = MultiActionCapabilityRegistry([Capability(name="cap", description="d", category="t", actions=actions)])
    executor = MultiActionExecutor(registry)
    result = executor.execute_chain([
        {"id": "a", "capability": "cap", "action": "draft", "reference_bindings": [_b("r1", T)]},
        {"id": "b", "capability": "cap", "action": "send", "reference_bindings": [_b("r1", T)]},
        {"id": "c", "capability": "cap", "action": "draft"},
    ])
    assert result["status"] == "halted" and result["halted_at"] == "b"
    assert result["steps"]["b"]["status"] == "reference_confirmation_required"
    assert len(calls) == 1
    assert executor.execute_chain([
        {"id": "a", "capability": "cap", "action": "send"},
        {"id": "b", "capability": "cap", "action": "send", "reference_bindings": [_b("r1", C)]},
    ])["status"] == "success"


# 8. Adapter propagation -------------------------------------------------------------------

class _Descriptor:
    def __init__(self, cid, **extra):
        self.id = cid
        self.description = "d"
        self.permissions = []
        self.interface = {}
        for key, value in extra.items():
            setattr(self, key, value)


def _adapted(descriptor):
    capability = LegacyCapabilityAdapter.from_descriptor(descriptor)
    return next(iter(capability.actions.values())).wrong_binding_impact


def test_adapter_uses_declaration_table():
    assert _adapted({"id": "gmail_create_draft"}) is REC
    assert _adapted(_Descriptor("gmail_create_draft")) is REC
    assert _adapted({"id": "gmail_create_draft", "wrong_binding_impact": None}) is REC


def test_adapter_descriptor_value_overrides_table():
    assert _adapted({"id": "gmail_create_draft", "wrong_binding_impact": "CONSEQUENTIAL"}) is CONS
    assert _adapted(_Descriptor("fetch_url", wrong_binding_impact="NONE")) is NONE


@pytest.mark.parametrize("bad", ["recoverable", "LOW", "", 3, ["NONE"]])
def test_adapter_invalid_descriptor_value_is_undeclared_without_table_fallback(bad):
    assert _adapted({"id": "gmail_create_draft", "wrong_binding_impact": bad}) is None
    assert _adapted(_Descriptor("gmail_create_draft", wrong_binding_impact=bad)) is None


def test_adapter_unknown_or_undeclared_capability_is_undeclared():
    for cid in ("drive_upload", "gmail_search", "remember_fact", "unknown_capability"):
        assert _adapted({"id": cid}) is None


# 9-10. Declarations (D1, U-2, U-3) ------------------------------------------------------------

def test_declaration_table_is_exactly_d1():
    assert KNOWN_CAPABILITY_WRONG_BINDING_IMPACT == {"gmail_create_draft": REC}
    assert KNOWN_CAPABILITY_EFFECTS["gmail_create_draft"] is EffectType.EXTERNAL_WRITE


def test_gmail_multi_action_declarations():
    capability = GmailCapability(gmail_service=object())
    declared = {name: action.wrong_binding_impact for name, action in capability.actions.items()}
    assert declared.pop("create_draft") is REC
    assert declared and all(value is None for value in declared.values())


# 11. Boundary and protected integrity ----------------------------------------------------------

def test_s2_module_has_no_model_provider_network_or_uri_v1_import():
    path = ROOT / "uri_core/capabilities/wrong_binding.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    assert modules <= {"__future__", "dataclasses", "enum", "typing"}


def test_uri_v1_still_has_no_uri_core_import():
    for path in (ROOT / "uri_v1").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(alias.name.startswith("uri_core") for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("uri_core"), path


def test_protected_hashes_unchanged():
    expected = {
        "uri_v1/turn/rar_deterministic.py": "e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649",
        "uri_v1/turn/rar_contracts.py": "4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819",
        "fixtures/m33_3_batch_a/battery.json": "06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa",
    }
    for path, digest in expected.items():
        source = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(source).hexdigest() == digest, path
