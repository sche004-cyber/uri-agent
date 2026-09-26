# M33.3 — S2 Implementation Report: `wrong_binding_impact` Production Field and Execution-Gate Check

**Verdict:** `S2_IMPLEMENTATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT`.
**S2_PLAN_FROZEN:** YES. **S2_IMPLEMENTATION_COMPLETE:** YES. **S2_AUDIT_PENDING:** YES. **S2_CLOSED_FROZEN:** NO. **M33_3_COMPLETE:** NO. **NEXT_SLICE_AUTHORIZED:** NO.
**Author:** Claude (planner and implementer). This report is not an independent audit.
**Date:** 2026-09-26.
**Frozen plan:** `docs/plans/M33_3_S2_STATE.md` (§1–§12 frozen before any code change).

## 1. Repository baseline

- Branch `m35-uri-v1-parallel-architecture`. Local HEAD and `origin/m35-uri-v1-parallel-architecture` were both `2fa90fbbb1fc00ceca828adbdc90a5442c263892` at start (verified with `git rev-parse` after `git fetch`).
- Pre-existing unrelated working-tree changes (modified `SKILL.md`; 150+ untracked research/docs/scripts files, including untracked `uri_v1/` research directories) were preserved and not staged.
- Governance at start: `S1_CLOSED_FROZEN`, `M33_3_COMPLETE: NO`, `LATER_SLICE_IMPLEMENTATION_AUTHORIZED: NO` (`docs/plans/M33_3_S1_STATE.md`, `docs/plans/M33_3_CROSS_PLAN_STATE.md`, `docs/governance/URI_STATE.yaml`).

## 2. Authority recovered

S2 is defined by `docs/plans/M33_3_CROSS_PLAN_STATE.md` §4 as "`Action.wrong_binding_impact` production field + execution-gate check". The contract comes from Plan A R2.6, Plan B R1.4, and cross-plan audit §8. User decision D1 fixes the only accepted classification. Plan A R3.2 (I-3, I-5, rebind check 7) and R4.2/R4.3 are the downstream consumers. Full precedence table: S2 state §1.

## 3. User decisions (this run)

The repository fixed the home (production `Action`) but not three points. The User answered them (2026-09-26):

| ID | Question | Answer |
|---|---|---|
| U-1 | How far the execution-gate check goes, given that no `uri_core` binding-state producer exists before S13 | Opt-in executor gate: field, adapter, declarations, pure gate, and an opt-in `reference_bindings` argument on `MultiActionExecutor.execute`. No change when the argument is absent. The legacy `ApprovalGate` path is not touched. |
| U-2 | Whether D1 covers the Gmail multi-action `create_draft` too | Yes, both draft actions are `RECOVERABLE`. |
| U-3 | Other declarations | D1 only. Every other action stays undeclared (`CONSEQUENTIAL`). |

## 4. Final S2 design (summary; normative text in the S2 state §4–§7)

- `WrongBindingImpact` = `NONE` / `RECOVERABLE` / `CONSEQUENTIAL` (values equal S1's enum).
- `Action.wrong_binding_impact: Optional[WrongBindingImpact] = None`. `None` = undeclared. Invalid values raise at construction. Post-construction tampering fails closed at evaluation.
- `effective_wrong_binding_impact(action)` → declared value, or `(CONSEQUENTIAL, declared=False)`.
- `ReferenceBinding(ref_key, candidate_id, status)` with `status ∈ {CONFIRMED, TENTATIVE}`.
- `evaluate_wrong_binding_gate` implements decision table G1–G7: no bindings → not applicable; malformed → invalid; all `CONFIRMED` → allow; any `TENTATIVE` → allow only when the declared impact is `NONE`/`RECOVERABLE`, else block with `CONFIRM_ONE`.
- `MultiActionExecutor.execute(..., reference_bindings=None)`: the gate runs after schema validation and before approval. Blocks are recorded as `reference_confirmation_required` or `invalid_reference_binding`. `execute_chain` passes a step's `reference_bindings`.
- `KNOWN_CAPABILITY_WRONG_BINDING_IMPACT = {"gmail_create_draft": RECOVERABLE}`. `LegacyCapabilityAdapter` propagates it. A descriptor value overrides the table. An invalid descriptor value becomes undeclared, with no table fallback.
- Gmail multi-action `create_draft` declares `RECOVERABLE`.

## 5. Implementation files

| File | Change |
|---|---|
| `uri_core/capabilities/wrong_binding.py` | new: enums, `ReferenceBinding`, `WrongBindingGateDecision`, `coerce_declared_impact`, `effective_wrong_binding_impact`, `evaluate_wrong_binding_gate` |
| `uri_core/capabilities/base.py` | `Action.wrong_binding_impact` field and coercion (+8 lines) |
| `uri_core/capabilities/registry.py` | declaration table, `_declared_wrong_binding_impact`, adapter propagation (+26) |
| `uri_core/capabilities/executor.py` | opt-in gate before approval; chain pass-through (+14) |
| `uri_core/capabilities/gmail/capability.py` | `create_draft` declaration (+3) |
| `uri_core/capabilities/__init__.py` | exports (+12) |
| `tests/test_m33_3_s2_wrong_binding_impact.py` | new S2 battery (140 test cases) |
| `docs/plans/M33_3_S2_STATE.md`, this report | new |
| `docs/plans/M33_3_CROSS_PLAN_STATE.md`, `docs/governance/URI_STATE.yaml` | additive S2 state |

Deterministic only. No model-backed path. No new dependency.

## 6. Deviations from the frozen plan

None in behavior. One test assertion drafted during implementation was removed before the first run. That assertion said the Gmail `create_draft` action has a non-`READ_ONLY` `effect_type`, and it was not part of plan §9. The reason is a pre-existing defect that S2 does not own (§9, L-4).

## 7. Tests and qualification

All commands ran from the repository root on Windows, Python 3.13, with `-p no:cacheprovider`.

| # | Command / scope | Result |
|---|---|---|
| A | `python -m pytest -q tests/test_m33_3_s2_wrong_binding_impact.py` | **140 passed** |
| A+B | `python -m pytest -q tests/test_m33_3_s2_wrong_binding_impact.py tests/test_m33_3_s1_*.py` (S2 + frozen S1) | **201 passed** |
| C | `python -m pytest -q test_m35_uriv1_a2_5_deterministic_rar.py test_m35_uriv1_a2_5_rar_adversarial_safety.py test_m35_uriv1_a2_5_rar_contracts.py test_m35_uriv1_a2_5_rar_stage4_refinements.py test_m35_uriv1_a2_5_candidate_invention_fix.py test_m33_3_batch_a_structural.py test_arn_1_deterministic_narrowing.py tests/governance` (deterministic RAR/ARN + governance tests) | **153 passed, 48 subtests passed** |
| D | `python scripts/governance/uri_state_validator.py` | `VALID: docs/governance/URI_STATE.yaml — no DCL violations found.` (re-run after the governance edits, §10) |
| E | Capability/executor regression: `test_multi_action_capabilities.py test_m32_capability_effect_classification.py test_m33_p1_permission_seam.py test_m33_batch_b_registry_bridge_and_dispatch.py test_canonical_execution.py test_m33_batch_a_external_capability_contract.py test_capability_directory.py test_gmail.py test_decision_gates.py test_approval_gate.py test_approval_store.py test_approval_resumption.py test_m32_1_ask_resumption_endpoint.py test_capability_authority_boundary.py test_m32_c2_c3_native_tool_loop.py test_server_capabilities_endpoint.py test_m33_batch_c_durable_primitives.py test_m33_batch_d_transports.py` | 328 passed, **3 failed**. All 3 also fail on a clean `2fa90fb` worktree (environment: `URI_EXTERNAL_CREDENTIAL_SECRET` unset ×2; `credentials.json` text in a capability-directory privacy assertion ×1). |
| F | Full tracked root suite (217 `git ls-files 'test_*.py'`, excluding `_live`, `test_qwen_coordinator*`, `test_gemma_worker_mcp`), run on the S2 tree and on a clean `2fa90fb` detached worktree concurrently | S2 tree: 2717 passed, 58 skipped, 12 failed. Baseline: 2591 passed, 59 skipped, 11 failed. The failure sets are identical except `test_m33_1_batch2_yt_dlp.py::…::test_execution_through_generic_cli_bridge_and_canonical_loop`, which calls a public URL. It then **passed on both trees in isolation** (8/8 each), so it is a network flake under concurrent load, not an S2 regression. The pass-count difference comes from untracked files that exist only in the main working tree (the clean worktree has no untracked fixtures/modules), not from S2. |

Pre-S2 baseline for the capability set (run before any code change): 219 passed, 1 failed (the same `credentials.json` privacy test).

**Adversarial checks (all converted to regression tests):** spoofed low impact set after construction (a plain `"RECOVERABLE"`/`"NONE"` string, a wrong type, an `EffectType`) → `CONSEQUENTIAL`; undeclared impact never allows `TENTATIVE`; approval (`user_approved`/`admin_approved`) never satisfies the gate; the gate runs before the approval prompt; malformed bindings (mapping, string, bare binding, set, tuples, dicts, empty or whitespace keys, raw-string or `PENDING`/`REJECTED`/`TENTATIVE_APPLIED`/lowercase/`None` status, non-string key, duplicate `ref_key`, `None` item, `ReferenceBinding` subclass) → `invalid_reference_binding`; declaration mutated between evaluations → the new value is honored (no cache); a mixed chain halts at the consequential step; a contradictory descriptor (invalid value plus table entry) → undeclared.

Reliability percentages: none claimed (deterministic battery; `UNMEASURED` is not applicable).

## 8. Protected integrity and boundary scan

| Artifact | SHA-256 (LF-normalized), after implementation |
|---|---|
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` (unchanged) |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` (unchanged) |
| `fixtures/m33_3_batch_a/battery.json` | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` (unchanged) |

- `git diff --stat HEAD -- uri_v1 fixtures uri_ui tests/test_m33_3_s1_*` → empty. S1, RAR, Batch A, and UI are untouched.
- Tracked `uri_core` diff is limited to the five `uri_core/capabilities/` files in §5 (63 insertions, 0 deletions).
- `wrong_binding.py` imports only `__future__`, `dataclasses`, `enum`, `typing` (tested). `uri_v1` still imports no `uri_core` (tested).
- No orchestrator, dispatch, canonical-execution, legacy `ApprovalGate`, provider, router, network, or UI change. No S3+ code.

## 9. Known limitations

- **L-1 Inert until S13.** No production caller supplies `reference_bindings` yet, so the gate currently changes no live behavior (U-1, by design). The S1-to-`ReferenceBinding` mapping and orchestrator/canonical wiring are S13.
- **L-2 Legacy path not gated.** Legacy capabilities (including `gmail_create_draft`) execute through `ApprovalGate.execute_tool`, which S2 does not touch (U-1). The declaration is still available through the adapter and the table.
- **L-3 Binding completeness is the caller's duty.** The executor does not know which parameters are references (per-parameter impact is deferred by R2.6), so it cannot detect an omitted binding.
- **L-4 Pre-existing, not S2:** the Gmail multi-action `create_draft` reports `effect_type=READ_ONLY` because it passes only `read_only=False`, which `Action.__post_init__` recomputes from the default `effect_type`. S2 does not fix this, because it is outside the frozen scope. It is flagged for a separate task. It shows again why impact is not derived from `effect_type` (S2-I2).
- **L-5 Not surfaced to the Brain/directory.** `describe_capability` and the external descriptor schema do not expose the field (deferred, S2 state §8).
- **L-6 Independence.** Claude planned and implemented S2. The audit must be independent.

## 10. Governance state after implementation

`S2_PLAN_FROZEN: YES`; `S2_IMPLEMENTATION_COMPLETE: YES`; `S2_AUDIT_PENDING: YES`; `S2_CLOSED_FROZEN: NO`; `S1_CLOSED_FROZEN: YES`; `M33_3_COMPLETE: NO`; `NEXT_SLICE_AUTHORIZED: NO`. No `INT-*` event. `URI-RAR` not adopted. Recorded in `docs/plans/M33_3_S2_STATE.md`, `docs/plans/M33_3_CROSS_PLAN_STATE.md`, and `docs/governance/URI_STATE.yaml` (`active_continuation`).

## 11. Next safe step

Independent S2 audit against `docs/plans/M33_3_S2_STATE.md` and the actual code, then bounded repair, requalification, and automatic close/freeze if accepted. S3 stays unauthorized until then.
