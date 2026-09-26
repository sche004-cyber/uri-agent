# M33.3 — S2 State: `wrong_binding_impact` Production Field and Execution-Gate Check (frozen plan)

**Current state:** `S2_IMPLEMENTATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT`.
**S2_PLAN_FROZEN:** YES. **S2_IMPLEMENTATION_COMPLETE:** YES. **S2_AUDIT_PENDING:** YES. **S2_CLOSED_FROZEN:** NO. **M33_3_COMPLETE:** NO. **NEXT_SLICE_AUTHORIZED:** NO.
**State history:** S2 `BLOCKED only on implementation authorization` (`docs/plans/M33_3_CROSS_PLAN_STATE.md` §4; PG-2 satisfied) → User S2 plan+implement task package (2026-09-26, starting HEAD `2fa90fbbb1fc00ceca828adbdc90a5442c263892`) → scope recovery and User decisions U-1 to U-3 (§3) → `S2_PLAN_FROZEN` (this file, §1–§12, frozen before any code change) → implementation → `S2_IMPLEMENTATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT`.
**Implementation authorized:** **YES, S2 only**, by the User's S2 task package. S1 stays closed/frozen. S3–S13 stay unauthorized.
**Workstream identity:** `URI-REFERENCE-CLARIFICATION`.
**Date:** 2026-09-26.
**Implementation report:** `docs/plans/M33_3_S2_IMPLEMENTATION_REPORT.md`.

---

## 1. Recovered authority

| Source | What it fixes for S2 | Precedence |
|---|---|---|
| `docs/plans/M33_3_CROSS_PLAN_STATE.md` §4 S2 row | S2 = "`Action.wrong_binding_impact` production field + execution-gate check"; gate PG-2 satisfied | slice definition |
| Cross-plan state §2 D1 [USER] | `gmail_create_draft` = `RECOVERABLE`; independent of `EffectType` / `ApprovalRequirement` / `RiskLevel`; never derived mechanically from `EffectType`; a future send is expected to be `CONSEQUENTIAL` | User decision |
| Plan A R2.6 (`M33_3_ARN_ARCHITECTURE_AND_LT1B_RENDERER_PLAN.md`) | field on `Action` beside `effect_type`, `approval_requirement`, `risk`; values `NONE` / `RECOVERABLE` / `CONSEQUENTIAL`; undeclared = `CONSEQUENTIAL`; consumer = execution gate; `TENTATIVE` + `CONSEQUENTIAL` → block, require `CONFIRM_ONE`; approval stays a separate gate; action-level maximum, per-parameter impact deferred; declared per action, never computed | plan contract |
| Plan B R1.4 (`M33_3_URI_BRAIN_ARCHITECTURE_PROPOSAL.md`) | same contract; home `uri_core/capabilities/base.py` | consistent with R2.6 |
| Cross-plan audit §8 | "new **optional** field" on the production `Action`; "propagates through `LegacyCapabilityAdapter`" | consistent; adds optional + adapter |
| Plan A R3.2 I-3, I-5, rebind check 7 | the impact is re-read from declared metadata, never from a cached value; the redo passes the gate with `CONFIRMED(Y)` | lifecycle consumers |
| Plan A R4.2 / R4.3 | `CERTAINTY` → `CONFIRMED` for every impact; impact checked at proposal time; `CONSEQUENTIAL`/undeclared → `CONFIRM_ONE` | authority rules S1 already implements |
| `docs/plans/M33_3_S1_STATE.md` §4.2 | S1 receives impact as an injected value; S2 owns the `Action` field and the execution gate | S1/S2 boundary |

No conflicting S2 draft exists. R4 wins over earlier Plan A text; none of R3/R4 changes R2.6 (R3.4, R4.9).

## 2. S2 objective

When the bound reference turns out to be wrong, what consequence does executing the proposed action with it have? S2 makes that consequence a **declared, typed property of the production `Action`**, and makes the **execution gate** refuse to execute an action on a `TENTATIVE` reference binding when that consequence is `CONSEQUENTIAL` or undeclared. Later clarification logic (S1 R2.9 check, R3.2 rebind check 7, S13 wiring) reads the same declared value.

S2 does not rate organizational risk, entitlement, approval need, or security class. Those remain `risk`, `approval_requirement`, permissions, and the approval gate.

## 3. Decisions

Already governed (no question asked): D1; three-value taxonomy; undeclared → `CONSEQUENTIAL`; home on `Action`; adapter propagation; consumer = execution gate; approval independent; action-level granularity; no derivation from `EffectType`.

User decisions made during this run (2026-09-26):

- **U-1 — gate wiring: opt-in executor gate.** Add the field, adapter propagation, D1 declarations, and a pure gate function in `uri_core/capabilities`. Add an opt-in `reference_bindings` argument to `MultiActionExecutor.execute`. When the argument is absent (every current caller), behavior is unchanged. S13 supplies real binding states later. The legacy `ApprovalGate.execute_tool` path is not touched.
- **U-2 — D1 scope: both draft actions.** Declare `RECOVERABLE` for the legacy capability `gmail_create_draft` and for the Gmail multi-action action `create_draft` (same operation; it never sends).
- **U-3 — declarations: D1 only.** No other action is declared. Every other action stays undeclared and is treated as `CONSEQUENTIAL`. Further declarations need their own User decision.

## 4. Contract

### 4.1 `WrongBindingImpact` (new, `uri_core/capabilities/wrong_binding.py`)

`str` enum, values exactly `NONE`, `RECOVERABLE`, `CONSEQUENTIAL` (upper case, equal to S1's `uri_v1.turn.rar_clarification_contract.WrongBindingImpact` values).

| Class | Meaning | Admissible evidence | Example | Gate behavior on `TENTATIVE` |
|---|---|---|---|---|
| `NONE` | a wrong reference has no effect beyond the shown result | explicit per-action declaration only | none declared in S2 (U-3) | allow |
| `RECOVERABLE` | a wrong reference produces an effect the User can correct before any external consequence | explicit per-action declaration only | `gmail_create_draft`, Gmail `create_draft` (D1, U-2) | allow |
| `CONSEQUENTIAL` | a wrong reference can cause an effect that cannot be corrected before it matters | explicit declaration, or the fail-closed default | a future send action (D1); every undeclared action | block; require `CONFIRM_ONE` |

`NONE` and `RECOVERABLE` produce the same gate result. They are not merged, because the three-value taxonomy is governed (D1, R2.6, Plan B R1.4) and both S1 and R3.2 check 7 use the same set.

### 4.2 `Action.wrong_binding_impact` (modified, `uri_core/capabilities/base.py`)

| Field | Type | Allowed | Required | Source | Validation / invalid behavior |
|---|---|---|---|---|---|
| `wrong_binding_impact` | `Optional[WrongBindingImpact]` | `None` (undeclared) or one of the three values | optional, default `None` | explicit declaration in the capability definition | `__post_init__` coerces an exact value string; any other value raises `ValueError` (same rule as `effect_type`). A value set after construction is re-validated by `effective_wrong_binding_impact`, which fails closed. |

`None` is kept distinct from `CONSEQUENTIAL` so that "undeclared" stays visible. Not persisted; not fingerprinted (the approval fingerprint covers `(capability_id, arguments)` only and is unchanged).

### 4.3 `effective_wrong_binding_impact(action) -> (WrongBindingImpact, declared: bool)`

Returns the declared value when it is a valid `WrongBindingImpact`. Returns `(CONSEQUENTIAL, False)` when the field is `None`, missing, or invalid. Pure; reads the live `Action` every call (no cache).

### 4.4 `ReferenceBindingStatus` and `ReferenceBinding`

`ReferenceBindingStatus`: `str` enum `CONFIRMED`, `TENTATIVE` — the only binding states that may reach execution (Plan A R2.3/R4.3). Values equal S1 `BindingState` names.

`ReferenceBinding` (frozen dataclass): `ref_key: str` (non-empty), `candidate_id: str` (non-empty), `status: ReferenceBindingStatus`. Supplied by the caller (S13 later maps S1 binding records into it). S2 never creates, confirms, or changes a binding.

### 4.5 `WrongBindingGateDecision` and `evaluate_wrong_binding_gate(action, reference_bindings)`

Frozen dataclass: `allowed: bool`, `outcome: str` (§5), `wrong_binding_impact: WrongBindingImpact`, `impact_declared: bool`, `blocking_ref_keys: tuple[str, ...]`, `required_clarification: Optional[str]` (`"CONFIRM_ONE"` or `None`).

### 4.6 Executor integration (`uri_core/capabilities/executor.py`)

- `execute(..., reference_bindings=None)`. The gate runs after input-schema validation and **before** the approval check. A blocked result is recorded as status `reference_confirmation_required` or `invalid_reference_binding`, with the decision fields in the audit entry. The handler is not called.
- `execute_chain`: a step may carry `reference_bindings`; it is passed to that step's `execute`. A blocked step halts the chain (existing halt rule).
- With `reference_bindings=None`, the executor path is unchanged.

### 4.7 Adapter and declarations (`uri_core/capabilities/registry.py`, `uri_core/capabilities/gmail/capability.py`)

- `KNOWN_CAPABILITY_WRONG_BINDING_IMPACT = {"gmail_create_draft": RECOVERABLE}` — an explicit declaration table, separate from `KNOWN_CAPABILITY_EFFECTS` and never derived from it.
- `LegacyCapabilityAdapter.from_descriptor`: if the descriptor supplies `wrong_binding_impact` (mapping key or attribute, not `None`), a valid value is used and an invalid value becomes undeclared (`None`) without falling back to the table (contradictory metadata fails closed). If the descriptor supplies nothing, the table value is used; otherwise undeclared.
- Gmail multi-action `create_draft`: `wrong_binding_impact=RECOVERABLE` (U-2).

## 5. Decision table (execution gate)

Evaluated in row order; first match wins. "Impact" is `effective_wrong_binding_impact(action)`.

| # | `reference_bindings` | Binding validity | Impact | `allowed` | `outcome` | `required_clarification` |
|---|---|---|---|---|---|---|
| G1 | `None` | — | any | yes | `NOT_APPLICABLE` | — |
| G2 | not a list/tuple (for example a dict, string, or single binding) | invalid | any | no | `INVALID_REFERENCE_BINDING` | — |
| G3 | contains an item that is not a `ReferenceBinding`, has an empty `ref_key`/`candidate_id`, a status outside `CONFIRMED`/`TENTATIVE` (for example `PENDING`, `REJECTED`, `TENTATIVE_APPLIED`, a raw string), or a duplicate `ref_key` | invalid | any | no | `INVALID_REFERENCE_BINDING` | — |
| G4 | empty sequence | valid | any | yes | `NO_REFERENCE_BINDING` | — |
| G5 | every binding `CONFIRMED` | valid | any, including undeclared | yes | `ALLOWED_CONFIRMED` | — |
| G6 | at least one `TENTATIVE` | valid | `NONE` or `RECOVERABLE` (declared) | yes | `ALLOWED_TENTATIVE_RECOVERABLE` | — |
| G7 | at least one `TENTATIVE` | valid | `CONSEQUENTIAL` declared, or undeclared/invalid (→ `CONSEQUENTIAL`) | no | `CONFIRMATION_REQUIRED` | `CONFIRM_ONE` (`blocking_ref_keys` = the `TENTATIVE` keys) |

Executor status mapping: G2/G3 → `invalid_reference_binding`; G7 → `reference_confirmation_required`; G1/G4/G5/G6 → continue to the approval check and the handler.

Reversibility / post-execution states: not distinguished by S2. `TENTATIVE_APPLIED`, `APPLIED`, and later states are not pre-execution binding states; supplying them is G3. Post-execution Change / redo stays in S1 (R3.2), where rebind check 7 reads the impact; the redo passes this gate with `CONFIRMED(Y)` (G5).

## 6. Invariants

- **S2-I1.** Undeclared or invalid impact is never treated as `NONE` or `RECOVERABLE`.
- **S2-I2.** `wrong_binding_impact` is never derived from `effect_type`, `approval_requirement`, `risk`, or `read_only`.
- **S2-I3.** Approval does not satisfy the gate: G7 blocks even with `user_approved=True` / `admin_approved=True`. The gate does not grant or consume approval, and approval checks still run after an allowed gate.
- **S2-I4.** The gate never creates, confirms, rebinds, or upgrades a binding, never executes the handler on a block, and never authorizes redo.
- **S2-I5.** Impact is read from the live `Action` at each evaluation; no cached classification exists.
- **S2-I6.** With `reference_bindings=None`, `MultiActionExecutor` behavior is unchanged.
- **S2-I7.** No model, provider, router, network, or `uri_v1` import in S2 code; `uri_v1` still has no `uri_core` import.
- **S2-I8.** Frozen S1, frozen RAR (A9), `rar_contracts.py`, and the Batch A battery are unchanged.

## 7. Multi-reference and multi-action

- Several references on one action: any `TENTATIVE` binding with a `CONSEQUENTIAL` action blocks (action-level maximum, R2.6).
- Tool chains: each step is gated against its own action with its own supplied bindings.
- One reference feeding several actions, parallel actions, bundle dependency ordering, and action change between clarification and execution: **DEFERRED** to S13 wiring. S2 re-reads the impact at execution time (S2-I5), so a changed declaration is honored; detecting that the caller's proposed action changed is the caller's responsibility.

## 8. Scope matrix

| Class | Items |
|---|---|
| **IN SCOPE** | new `uri_core/capabilities/wrong_binding.py`; `uri_core/capabilities/base.py` (field); `uri_core/capabilities/registry.py` (declaration table, adapter); `uri_core/capabilities/executor.py` (opt-in gate); `uri_core/capabilities/gmail/capability.py` (one declaration); `uri_core/capabilities/__init__.py` (exports); new `tests/test_m33_3_s2_wrong_binding_impact.py`; this file; the implementation report; additive governance updates to `docs/plans/M33_3_CROSS_PLAN_STATE.md` and `docs/governance/URI_STATE.yaml` |
| **BOUNDARY** (consume, do not redesign) | S1 `WrongBindingImpact` and `BindingState` (value parity only); `ApprovalRequirement` / approval flow; `MultiActionDispatch`; `CapabilityDescriptor` (unchanged; adapter reads an optional attribute) |
| **PROTECTED** | `uri_v1/**` (S1 and RAR), `uri_v1/turn/rar_deterministic.py`, `uri_v1/turn/rar_contracts.py`, `fixtures/m33_3_batch_a/**`, S1 tests, `uri_ui/**` |
| **DEFERRED** | legacy `ApprovalGate.execute_tool` path, orchestrator / canonical-execution / dispatch wiring, S1→gate binding mapping (S13); external descriptor schema field (`uri_core/external/contract.py`) and registry `describe_capability` exposure (not required; later slice); declarations beyond D1 (User decision); per-parameter impact (R2.6); S3+ |

## 9. Test battery (defined before coding; `tests/test_m33_3_s2_wrong_binding_impact.py`)

1. Taxonomy: exactly three values; equal to S1's value set; `ReferenceBindingStatus` values are S1 `BindingState` names.
2. `Action` field: default `None`; string coercion; invalid value raises `ValueError`; not derived from `effect_type` (external-write and read-only actions both default undeclared).
3. `effective_wrong_binding_impact`: declared values; `None` → `CONSEQUENTIAL` undeclared; post-construction tampering (invalid string, wrong type) → `CONSEQUENTIAL` undeclared; live re-read after mutation.
4. Decision table G1–G7, table-driven, every impact × status combination.
5. Invalid bindings (G2/G3): dict, string, bare binding, non-binding item, empty keys, `PENDING`/`REJECTED`/`TENTATIVE_APPLIED`/lowercase strings, duplicate `ref_key`.
6. Executor: no bindings → unchanged status sequence; G7 blocks before approval, handler not called, even with `user_approved`/`admin_approved`; G6/G5 proceed to the approval check (still `approval_required` without approval); invalid → `invalid_reference_binding`; audit entry carries decision fields.
7. Chain: a blocked step halts; unblocked steps unaffected; steps without bindings unchanged.
8. Adapter: table declaration for `gmail_create_draft`; valid descriptor override; invalid descriptor value → undeclared, no table fallback; unknown capability → undeclared; mapping and attribute descriptors.
9. Gmail multi-action: `create_draft` = `RECOVERABLE`; every other Gmail action undeclared (U-3).
10. D1 independence: `gmail_create_draft` is `EXTERNAL_WRITE` and `RECOVERABLE`; no action other than the two D1 actions is declared.
11. Boundary: `wrong_binding.py` imports no model/provider/network/`uri_v1` module; `uri_v1` still has no `uri_core` import; protected hashes (§12) unchanged; the frozen S1 files are byte-identical to `2fa90fb` (checked in qualification, not in the test).

Reliability numbers: none are claimed; the battery is deterministic.

## 10. Implementation order

1. `wrong_binding.py`. 2. `Action` field. 3. Declaration table and adapter. 4. Gmail declaration. 5. Executor gate and chain pass-through. 6. Exports. 7. Tests. 8. Qualification (S2, S1 regression, capability/executor regression, RAR deterministic regression, governance validator, protected hashes). 9. Report and governance. 10. Commit and push only S2 files.

## 11. Stop conditions

- Any need to change `uri_v1/**`, frozen RAR, `rar_contracts.py`, Batch A fixtures, or `uri_ui/**`.
- Any need to change the legacy approval path, orchestrator, dispatch, or canonical execution.
- Any change to the executor's behavior when `reference_bindings` is absent.
- Any declaration beyond U-2, or any derivation of impact from `EffectType`.
- Any model, provider, router, or network dependency.
- Any protected-hash mismatch.

## 12. Protected hash anchors (verified 2026-09-26 before and after implementation)

| Artifact | SHA-256 (LF-normalized) |
|---|---|
| `uri_v1/turn/rar_deterministic.py` (A9) | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `fixtures/m33_3_batch_a/battery.json` | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` |

## 13. Authorization state

- `S2_PLAN_FROZEN: YES` (§1–§12 frozen before code).
- `S2_IMPLEMENTATION_COMPLETE: YES` (evidence: implementation report).
- `S2_AUDIT_PENDING: YES`. `S2_CLOSED_FROZEN: NO`.
- `S1_CLOSED_FROZEN: YES` (unchanged). `M33_3_COMPLETE: NO`. `NEXT_SLICE_AUTHORIZED: NO`. No `INT-*` event. `URI-RAR` not adopted.
- Next safe step: independent S2 audit, bounded repair, requalification, and close/freeze if accepted.
