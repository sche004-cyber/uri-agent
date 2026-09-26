# M33.3 S2 — independent audit, bounded repair, requalification, and freeze

**Date:** 2026-09-26
**Verdict:** `S2_AUDIT_REPAIR_REQUALIFICATION_ACCEPTED`
**Scope:** S2 only. S1 remains closed/frozen; M33.3 remains incomplete; S3–S13 remain unauthorized.

## 1. Audit identity and authority

- Repository: `C:\Users\cheta\Development\Uri\_V1`; branch: `m35-uri-v1-parallel-architecture`; remote: `origin` (`https://github.com/sche004-cyber/uri-agent.git`). The independent audit began at local and remote HEAD `d8735dbf2f471e3c9e63389b30d66e60718bf2d0`; pre-S2 baseline is `2fa90fbbb1fc00ceca828adbdc90a5442c263892`.
- The pre-existing modified `SKILL.md` and extensive untracked M35/research work were left untouched and unstaged. A managed, detached baseline checkout at `2fa90fb` supplied comparison evidence.
- Normative sources: `M33_3_S2_STATE.md` §§1–12; Plan A R2.6 and R3.2/R4; Plan B R1.4; cross-plan audit §8; cross-plan state D1 and S2 U-1/U-2/U-3; frozen S1 state and its independent requalification; production `Action`, `LegacyCapabilityAdapter`, `MultiActionExecutor`, and `ApprovalGate` paths. The S2 implementation report was a claim to test, not audit evidence.
- D1 declares an unsent Gmail draft `RECOVERABLE` independently of `EffectType`. U-1 selects an opt-in `MultiActionExecutor` gate and defers caller wiring and the legacy `ApprovalGate` path. U-2 covers both draft actions. U-3 permits only those D1 declarations. S2 does not authorize S3 or production integration.

## 2. Finding, reproduction, and bounded repair

| Finding | Reproduction at `d8735db` | Frozen contract | Repair and regression |
|---|---|---|---|
| S2-F1: malformed binding could raise instead of failing closed | `object.__new__(ReferenceBinding)` inside a binding list raised `AttributeError` at `_valid_binding` when `ref_key` was absent. A foreign object with a raising `ref_key` property was read before type validation. | G3 requires malformed objects and missing fields to return `INVALID_REFERENCE_BINDING`; the executor must not call the handler. | In `wrong_binding.py`, require exact `ReferenceBinding` type, read each field with a missing-field fallback, and construct duplicate keys only after every item validates. Added cases for each missing field, a mixed valid/invalid list, a foreign raising property, and executor handler non-execution in `test_m33_3_s2_wrong_binding_impact.py`. |
| S2-F2: foreign string enum accepted as a low-impact declaration | A foreign `str, Enum` member with value `RECOVERABLE` was accepted by `Action.__post_init__` and by the adapter. | S2 state §4.2 permits a `WrongBindingImpact` or an exact value string; another enum type is invalid. Invalid descriptor metadata must remain undeclared without table fallback. | `coerce_declared_impact` now accepts only the S2 enum or `type(value) is str`; the adapter uses that same validator. Added an Action rejection and adapter fail-closed regression. |

The repairs change no policy or gate outcome for a valid binding or valid declared impact. The post-repair focused S2 battery is **146 passed**; S2 plus frozen S1 is **207 passed**. No further S2 defect was found in re-audit.

## 3. Independent contract matrix

| Requirement | Status | Evidence / limit |
|---|---|---|
| Three-value `Action.wrong_binding_impact` and optional undeclared state | SATISFIED | `WrongBindingImpact` has exactly `NONE`, `RECOVERABLE`, `CONSEQUENTIAL`; `Action` defaults to `None`; exact strings coerce at construction, invalid declarations reject. |
| Undeclared and tampered impact fail closed; no `EffectType` inference | SATISFIED | `effective_wrong_binding_impact` reads the live action on each call, returns `(CONSEQUENTIAL, False)` for `None`/invalid; all `EffectType` variants remain undeclared absent explicit declaration. Mutation and copied-action probes observe current values. |
| G1: absent bindings | SATISFIED | `None` yields `NOT_APPLICABLE`; executor continues its pre-S2 permission, schema, approval, handler, and audit path. |
| G2/G3: invalid bindings | SATISFIED after repair | Only list/tuple of exact, complete, valid bindings is accepted; unknown states, raw strings, subclasses, missing fields, mixed invalid lists, and duplicate keys return `INVALID_REFERENCE_BINDING`. |
| G4/G5/G6: empty, confirmed, safe tentative | SATISFIED | Empty list allows; all `CONFIRMED` allows even undeclared; tentative with declared `NONE`/`RECOVERABLE` allows, still subject to approval. |
| G7: consequential or undeclared tentative | SATISFIED | Blocks with `CONFIRM_ONE` and every tentative key; approval flags do not override; handler is not called. |
| Approval independence | SATISFIED | Wrong-binding confirmation grants no approval; approved consequential tentative remains blocked; legacy `ApprovalGate` source and behavior are unchanged. |
| Adapter propagation and D1-only declarations | SATISFIED | Explicit table contains only `gmail_create_draft`; Gmail multi-action `create_draft` is `RECOVERABLE`; every other Gmail action is undeclared. Valid descriptor value wins; invalid descriptor value stays undeclared without table fallback. |
| Per-action chains and freshness | SATISFIED | Each step gates its own action and supplied bindings; blocked step halts before later execution. Impact is not cached. |
| Caller completeness and production visibility | NOT_APPLICABLE to S2 acceptance | U-1 deliberately makes the gate opt-in; S13 owns complete S1 binding-state mapping and production wiring. Capability description/schema exposure is deferred by frozen S2 §8. |
| Protected boundary | SATISFIED | No S2 diff in `uri_v1`, `uri_ui`, Batch A fixtures, frozen S1 tests, legacy approval, orchestrator, or provider code. |

## 4. Regression, baseline, and adversarial evidence

- `python -m pytest -q -p no:cacheprovider tests/test_m33_3_s2_wrong_binding_impact.py` after repair: **146 passed**.
- The same S2 file plus all `tests/test_m33_3_s1_*.py` files, expanded by PowerShell: **207 passed**.
- Deterministic RAR/ARN and Batch A structural plus `tests/governance`: **153 passed, 48 subtests passed** before the repair. Governance after closure: **37 passed**; `python scripts/governance/uri_state_validator.py`: **VALID, no DCL violations**.
- The capability/executor sweep defined in the S2 implementation report §7 reproduced **328 passed, 3 failed, 13 subtests passed** before and after repair. Each failure was independently rerun on clean `2fa90fb` and failed identically: one capability-directory privacy assertion serializes the text `credentials.json`; two production-composition tests need an unset `URI_EXTERNAL_CREDENTIAL_SECRET`. These are pre-existing/environment failures, not S2 regressions.
- The widest practical tracked-root sweep selected the 217 tracked `test_*.py` files except `_live`, `test_qwen_coordinator*`, and `test_gemma_worker_mcp`. On the S2 tree it returned **2591 passed, 58 skipped, 12 failed, 77 subtests passed** in 437.31 seconds; on clean `2fa90fb`, **2591 passed, 59 skipped, 11 failed, 77 subtests passed** in 426.66 seconds. Eleven failure IDs matched exactly: capability-directory privacy; five M20 feasibility/recovery/semantic-interpreter cases; two perception-corpus hash cases; orchestrator session workflow; usage import boundary; workflow restart recovery. The sole apparent extra failure was `test_m33_1_batch2_yt_dlp.py::TestM33_1Batch2YtDlp::test_execution_through_generic_cli_bridge_and_canonical_loop`, which invokes a public Wikimedia URL. An isolated rerun failed **identically on both trees** (`unavailable` versus expected `success`, ~19 seconds each), establishing an environment/network-sensitive failure rather than a new S2 regression. No failing root test exercises the S2 repair path. The pass-count parity is exact.
- Post-repair requalification: S2 + S1 **207 passed**; deterministic RAR/ARN + governance **153 passed, 48 subtests passed**; capability/executor **328 passed, the same 3 baseline failures, 13 subtests passed**; standalone governance **37 passed** and URI_STATE validator **VALID**. The broad root comparison began before the bounded repairs and served as baseline and regression classification; all changed production paths were rerun after repair in the focused and capability suites.

Adversarial probes covered invalid/tampered impact, foreign impact enum, undeclared impact, approved consequential tentative action, malformed/unknown status, foreign binding subclass and malformed object, duplicate key, missing fields, mixed invalid list, `None` and empty inputs, descriptor contradiction, impact mutation, copied Action, descriptor mutation after adaptation, a mixed-impact chain, and the legacy path boundary. The newly reproduced violations are now permanent regressions.

## 5. Accepted limitations and out-of-scope observation

- **Accepted/deferred:** U-1 means no current production caller supplies complete bindings. S13 must supply them and wire the live agent loop. Legacy `ApprovalGate.execute_tool` remains ungated under U-1. `describe_capability` and the external descriptor schema do not expose the field under S2 §8. These limits do not imply that live end-to-end behavior is already delivered.
- **`OUT_OF_SCOPE_PREEXISTING`:** Gmail multi-action `create_draft` still reports `effect_type=READ_ONLY`. This does not set wrong-binding impact; D1 explicitly separates the two classifications. No S2 repair to `EffectType` is authorized.

## 6. Protected integrity and governance

LF-normalized SHA-256 values, independently recomputed:

| Artifact | SHA-256 |
|---|---|
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `fixtures/m33_3_batch_a/battery.json` | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` |

`git diff 2fa90fb d8735db -- uri_v1 uri_ui fixtures/m33_3_batch_a tests/test_m33_3_s1*` was empty, as was the protected-path diff after repair. The S2 implementation adds no model/provider/network dependency and no `uri_v1` import from `uri_core`. `git diff --check` on this transaction is clean; the unrelated modified `SKILL.md` has two pre-existing trailing-space lines and is excluded from staging.

The closure transaction updates `M33_3_S2_STATE.md`, `M33_3_CROSS_PLAN_STATE.md`, and `URI_STATE.yaml`: `S2_IMPLEMENTATION_AUDITED: YES`; `S2_REPAIRS_REQUIRED: YES`; `S2_REPAIRS_VERIFIED: YES`; `S2_CLOSED_FROZEN: YES`; `M33_3_COMPLETE: NO`; `NEXT_SLICE_AUTHORIZED: NO`. S1 stays frozen. The implementation report remains a historical submission and is not rewritten as an audit.

## 7. Final transaction

The audit accepts S2 after the bounded repairs and requalification. Only the two production repair files, the S2 regression test, this report, and the three S2 governance/state files belong in the closure commit. The final response records the resulting commit and remote-head verification; the commit cannot contain its own hash. Stop before S3.
