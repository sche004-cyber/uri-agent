# M33 — External Capability Bridge: Batch A Completion Report

Blueprint: `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`
(FROZEN, §13 addendum included). Clean HEAD: `a201d2f`. Not committed/
pushed — stopping at this batch boundary per explicit instruction.

## 1. Pre-implementation inspection (required before editing)

Read the full blueprint including §13. Read current governance state
(`docs/governance/URI_ACTIVE_MILESTONE.md`). Confirmed:

- **M33.1, M34, M35: NOT STARTED** — no plan files exist for any of
  them; governance §1c/§1b explicitly record all three as reservations
  only.
- **Working tree clean** at session start (only pre-existing untracked
  `graphify-out/*` and `.agents/skills/*` artifacts, unrelated to any
  milestone).
- **Blueprint's own §2 gate** ("gated behind the Hybrid UI initiative's
  Batch 1 landing and the working tree returning to clean") — Batch 1
  landed (all 4 Hybrid UI batches report complete per governance §1a,
  150–168/168 Flutter tests passing, commit `7bb916f`), and the tree is
  clean now. Gate condition met, even though the Hybrid UI initiative
  itself remains paused/not-yet-accepted as a whole — the blueprint's
  gate is on Batch 1 landing specifically, not full initiative closure.

## 2. A finding that changes what "M33 core only" can safely mean

The blueprint's own sequencing is **P1 → P2 → M33**, not M33 standalone.
Two of its four findings (F1, F2) were independently re-verified
directly against current source before writing any code, since the
blueprint itself was frozen 2026-09-17, before M32's own D-batches ran:

- **F1 (canonical gated off) is now STALE.** `uri_core/core/canonical_
  execution.py:93-100`'s `decision_engine_live_enabled()` was changed
  under M32 B1.1 (a commit that predates this session's D3-D6 work):
  absence of `URI_ENABLE_DECISION_ENGINE_LIVE` now means **on** by
  default, not off. The canonical `/ask` path is already the live
  default in this deployment. P2's core premise ("make canonical the
  path that actually serves `/ask`") appears to already be substantially
  satisfied as a side effect of M32, though P2's FULL exit criteria
  (a recorded live-observation battery, confirmation `orchestrator.py`
  didn't grow from this specific change, full regression against a
  fresh baseline) were never formally run under that name. Recorded as
  a finding, not treated as a formal P2 closure — no completion record
  exists for it and none is claimed here.
- **F2 (permission-checker fail-open) is CONFIRMED STILL LIVE.**
  `uri_core/core/multi_action_dispatch.py:314-318`, re-read directly
  this session:
  ```python
  def _action_permitted(self, capability: str, action: str, principal: Any) -> bool:
      if self._explicit_permissions is not None or self.permission_checker is not None:
          return True
      ...
  ```
  The presence of ANY permission checker still short-circuits per-action
  authorization to unconditional `True`. This is exactly the bug the
  blueprint's F2 describes and P1 is scoped to fix. **P1 has not been
  done** — no `docs/plans/*PERMISSION_SEAM*` or `P1` plan file exists,
  and the source confirms the bug is unfixed.

**Why this matters for scope, not just as trivia:** Batch B of M33 core
explicitly says "Permission binding from descriptors to the grant
store, **on top of P1's corrected seam**." Building Batch B's external-
capability authorization binding on top of a currently-fail-open seam
would directly contradict this same instruction's own constraint:
*"permissions, grants, approvals, evidence and audit remain URI-
authoritative."* Wiring a new capability class's authorization onto a
path that returns `True` unconditionally whenever a checker is present
is not URI-authoritative — it is decorative.

**Disposition:** Batch A has no dependency on P1 — the blueprint states
plainly "no adapter is reachable from any execution path; no registry
change yet." It was safe to implement standalone and is complete below.
**Batch B is not started, and should not begin until P1 is resolved**
(as its own bounded fix, or as an explicit User-accepted risk exception
— which would itself cross this session's "material change to the
security/authority model" escape hatch and needs the User's own
decision, not an assumption on my part).

## 3. Batch A — what was built

New package `uri_core/external/` (zero existing files modified):

| File | Purpose |
|---|---|
| `contract.py` | `ExternalCapabilityDescriptor`/`ExternalActionDescriptor` dataclasses, reusing `uri_core.capabilities.base`'s `ApprovalRequirement`/`RiskLevel`/`EffectType` directly (per D1). `validate_descriptor()` — static, structural, execution-free: unknown major contract version and any unsupported bounded-schema-subset construct (`$ref`, `format`, union keywords, excess nesting) fail closed. |
| `validator.py` | `ExternalActionValidator` (per D2) — the bounded JSON-schema-subset runtime validator `ActionSchema` doesn't provide: enum, length, range, item, and nesting-depth constraints, enforced on both input and output. `invalid_output` is a distinct outcome from `no_result` (A2). |
| `qualification.py` | `Qualifier`/`QualificationRecord`, bound to exact source revision, declared dependency lock, and a SHA-256 profile digest over the descriptor's own declared content — never over anything imported or fetched. Reuses `skill_installer.py`'s digest/static-validation discipline per the blueprint's explicit instruction. |
| `lifecycle.py` | `LifecycleState` (7 orthogonal fields: presence, qualification, configuration, authentication, health, enabled, update_available) + `LifecycleController` (guarded transitions) + `derive_label()`, whose precedence is an ordered data tuple (`LABEL_RULES`), not branching logic. |
| `store.py` | `ExternalCapabilityStore` — per-user durable store via `portable_paths.user_scoped_path` (strict UUID validation, same convention every other user-scoped store in this repo uses), atomic writes (temp file + `os.replace`, never a plain `open(path, "w")`). |

Fixed during implementation (not pre-planned as a separate item): my
first `register_descriptor()` draft short-circuited before calling
`Qualifier.qualify()` on structural failure, which made `lifecycle.py`'s
own `QUALIFICATION_REJECTED` state unreachable through the store — a
rejected descriptor would silently vanish instead of producing an
observable record. Caught by the test written for exactly this case;
fixed so `register_descriptor()` always qualifies and always persists
(`qualify()` re-runs the same structural check once, not the store
duplicating it).

## 4. Test evidence

`test_m33_batch_a_external_capability_contract.py` — 37 tests, all
real collaborators (no mocks): descriptor validation (valid, unknown
major version, missing field, unsupported transport, unsupported
schema construct, `$ref`, excess nesting depth, bad id, round-trip);
`ExternalActionValidator` (valid/invalid input, missing required,
unknown parameter, length/range/type/enum/pattern bounds, nested
items/properties, `no_result` vs `invalid_output` distinction); the
`Qualifier` (qualifies, rejects with reasons, digest stability/
sensitivity, proof that qualifying a descriptor naming a nonexistent
binary never raises — nothing is ever imported or executed);
`LifecycleController` (data-driven label-derivation order exercised
through every state, guarded transitions correctly reject out-of-order
calls); the store (register/get/list round-trip, full lifecycle
round-trip, **explicit user-A/user-B isolation** — two real UUIDs,
proving one user's registration/configuration/enable is invisible to
and unaffected by the other's, non-UUID `user_id` rejected, restart-
recovery via a fresh store instance on the same file); and a structural
test proving none of the five new modules reference the real dispatch/
execution/registry surface by name (`multi_action_dispatch`,
`canonical_execution`, `capability_directory`, `capabilities.registry`,
`capabilities.executor`) — Batch A's own "no adapter reachable, no
registry change" exit criterion, checked mechanically rather than
merely asserted.

```
test_m33_batch_a_external_capability_contract.py  37 passed
```

Full-suite collection sanity: `pytest --collect-only -q` from the repo
root now collects **2046 tests** (2009 pre-existing + 37 new), zero
collection errors — confirms the new package introduces no import
breakage anywhere in the repository. `git status` confirms this batch
touched zero existing files (`uri_core/external/` and the one new test
file only) — no targeted-suite regression run was needed for existing
code since none was modified; the collection-count match is the
relevant evidence for an additive-only change.

## 5. Acceptance disposition (Batch A's own exit criteria)

| Exit criterion | Status |
|---|---|
| Contract and lifecycle tests pass | 37/37 passed |
| Explicit user-A/user-B isolation for qualification record, lifecycle store, and every path through `user_scoped_path` | `test_user_a_and_user_b_are_mutually_isolated`, `test_both_users_stores_live_under_their_own_user_scoped_path`, `test_non_uuid_user_id_is_rejected` |
| No adapter reachable from any execution path | `NoAdapterReachableFromExecutionTests` (structural, mechanical) |
| No registry change yet | Confirmed by diff — `uri_core/capabilities/registry.py` untouched |

## 6. Residual risks / not yet verified

- **P1 is an open, confirmed-live security gap** (§2 above) — not
  introduced by this session, not fixed by this session, but directly
  relevant to Batch B and disclosed here rather than discovered later.
- **F1's staleness is a finding, not a closure.** Canonical being
  live-by-default is confirmed by source, not by a recorded live-
  observation battery under P2's own exit criteria. Do not treat P2 as
  done on the strength of this report.
- Full repository-wide `pytest -q` (not just `--collect-only`) was not
  re-run this batch, since zero existing files changed and collection
  already confirms zero import-level breakage; the last full-suite
  result on record is M32.1's (1989 passed/20 failed, all 20 pre-
  existing) at HEAD `a201d2f`, one commit behind this batch's additions.
- Batches B, C, D are not started.

## 7. Verdict

**Batch A: READY** — implemented, tested, isolated, additive-only,
zero regression risk (nothing existing was touched). **Batch B: BLOCKED
on P1**, pending User decision (fix P1 as its own bounded prerequisite,
or explicitly accept and record the risk of building on the current
fail-open seam — a security/authority-model decision this session will
not make unilaterally).

Not committed. Not pushed. M33.1/M34/M35 confirmed untouched.
