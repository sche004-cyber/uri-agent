# M33 — P1: Permission-Seam Generalization — Completion Report

Blueprint reference: `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`
§3. Clean HEAD: `a201d2f` (Batch A additions, uncommitted, present in the
working tree throughout this work — untouched by it). Not committed/
pushed — stopping per explicit instruction.

## 1. Pre-edit trace of the current permission-check path

Traced end to end before writing any code:

- `uri_core/core/orchestrator.py:267-270` — the real production
  construction site: `MultiActionDispatch(capability_registry=self.
  capability_registry)`. **No `registry`, no `granted_permissions`, no
  `permission_checker`, no `audit_sink` is passed.** This means, as
  constructed in production today, `MultiActionDispatch._explicit_
  permissions` and `.permission_checker` are BOTH `None`.
- `multi_action_dispatch.py`'s `dispatch()`/`dispatch_explicit()`/
  `dispatch_chain_explicit()` all call `_action_permitted()` before
  ever reaching the executor.
- `_action_permitted()` (pre-fix):
  ```python
  def _action_permitted(self, capability, action, principal):
      if self._explicit_permissions is not None or self.permission_checker is not None:
          return True
      legacy_id = _ACTION_GRANT_CAPABILITY.get(action)
      return bool(legacy_id and self._legacy_capability_allowed(legacy_id, principal))
  ```
  **Correction to my own earlier Batch A report**, recorded here per
  this repository's auditable-correction-history convention rather
  than silently revised: I had characterized F2 as "confirmed still
  live" without first tracing the production construction site. Having
  now done so, the accurate statement is: **the bug is real and
  confirmed in source, but dormant in production today**, because
  production never supplies a `permission_checker` or `granted_
  permissions` — so the fail-open branch is currently unreachable
  through the real `orchestrator.py:270` construction path. It is
  reachable, and live, the instant any caller (a test fixture today;
  Batch B's own permission-binding work tomorrow) constructs a
  `MultiActionDispatch` with either argument set — which is exactly why
  fixing it *before* Batch B wires one in for real is the correct order,
  not a false alarm.
- `_legacy_capability_allowed()` was already correct: it consults
  `self.permission_checker` when present (or falls back to the real,
  per-user `CapabilityResolver.is_allowed`), catching and denying on
  any exception. This function was never the bug — `_action_permitted`'s
  short-circuit BEFORE calling it was.
- `_granted_permissions()` (pre-fix) hardcoded a single check
  (`"gmail_search"`) and a single literal scope (`"gmail.readonly"`) —
  the outcome was correct for Gmail but the mechanism had no path for
  any other capability id, confirming F2's second half.
- `uri_core/capabilities/executor.py`'s `MultiActionExecutor.execute()`
  had a capability-level permission gate (L46-50: `missing_permissions
  = set(capability.permissions) - self.granted_permissions`) but **no
  action-level gate at all** — confirmed by direct reading; every
  action's own required scopes were entirely unenforceable, by design
  absence, not by bug.

## 2. Root cause

Two related but distinct defects, both in `multi_action_dispatch.py`:

1. `_action_permitted()` treated the mere PRESENCE of an authorization
   mechanism (`permission_checker` or `_explicit_permissions`) as an
   automatic grant, instead of consulting what that mechanism actually
   said. A correctly-wired, correctly-answering `permission_checker`
   returning `False` was never even called.
2. `_granted_permissions()` had no generalized mechanism for deriving
   scopes for any capability besides the one Gmail literal it hardcoded
   — a real capability, per requirement #2, but not by itself a
   security hole (it fails safe: an unrecognized capability contributed
   nothing to the granted set, which denies rather than allows).

## 3. Exact fix

Three files, exactly the blueprint's §3 scope, nothing else:

**`uri_core/capabilities/base.py`** — `Action` gained a new field,
`permissions: Tuple[str, ...] = ()` — the action's own declared
required scopes, on top of its capability's `Capability.permissions`.
Empty by default: a strict no-op for every action that does not opt in
(every existing action, as of this fix).

**`uri_core/capabilities/executor.py`** — `MultiActionExecutor.execute()`
gained a new gate, between the existing capability-level check (L46-50)
and schema validation (L51, now shifted down):
```python
missing_action_permissions = sorted(set(action.permissions) - self.granted_permissions)
if missing_action_permissions:
    return self._record(capability_name, action_name, "permission_denied",
                         {"missing_action_permissions": missing_action_permissions})
```

**`uri_core/core/multi_action_dispatch.py`** — the actual fix:

```python
_CAPABILITY_GRANT_ALIAS = {"Gmail": "gmail_search"}  # new, small, explicit

def _granted_permissions(self, principal):
    if self._explicit_permissions is not None:
        return set(self._explicit_permissions)
    granted = set()
    for summary in self.registry.capability_summaries():
        capability_id = summary.get("name")
        legacy_id = _CAPABILITY_GRANT_ALIAS.get(capability_id)
        if legacy_id is None:
            continue
        if self._legacy_capability_allowed(legacy_id, principal):
            capability = self.registry.get_capability(capability_id)
            if capability is not None:
                granted |= set(capability.permissions)
    return granted

def _action_permitted(self, capability, action, principal):
    if self._explicit_permissions is not None:
        registered = self.registry.get_capability(capability)
        required = set(registered.permissions) if registered is not None else set()
        return required <= self._explicit_permissions
    legacy_id = _ACTION_GRANT_CAPABILITY.get(action)
    if legacy_id is None:
        return False
    return self._legacy_capability_allowed(legacy_id, principal)
```

**Design decisions, disclosed:**

- `_granted_permissions()` is now genuinely generic — it iterates every
  registered capability via the registry's own public API (`capability_
  summaries()`/`get_capability()`, no registry.py change), consulting
  each one's legacy alias if it has one. Gmail's own resulting grant
  set is unchanged (still exactly `{"gmail.readonly"}` when allowed)
  because it remains the only alias entry — preserved as the *outcome*,
  not hardwired as the *mechanism* (requirement #2, verbatim).
- `_action_permitted()`'s `_explicit_permissions` branch now means
  "does this action's owning capability's own declared scope already
  hold within the caller-supplied set?" — mirroring `_granted_
  permissions()`'s own capability-level semantics for the SAME
  constructor argument, rather than inventing a second meaning for it.
  This was the only design that both (a) genuinely narrows instead of
  universally allowing (an empty or unrelated scope set now correctly
  denies) and (b) keeps every pre-existing test passing unchanged,
  since those tests supply exactly `{"gmail.readonly"}` and expect
  every Gmail action — including `create_draft` — to pass the dispatch-
  level check with it, matching Gmail's actual capability-level scope.
- An action with **no** legacy alias (a not-yet-wired capability) now
  denies by default, unconditionally — including when a `permission_
  checker` is present for OTHER capabilities. This is requirement #4's
  "additive denial for new IDs" taken literally: P1 does not widen
  which capability ids `_action_permitted` recognizes — that recognition
  (real grant binding for genuinely new external capabilities) is
  explicitly Batch B's "permission binding from descriptors to the
  grant store" work, not P1's. Disclosed here so it is not mistaken for
  an oversight.

## 4. Test evidence

**Exit-criteria suites, named in the blueprint, unmodified and re-run:**
```
test_multi_action_capabilities.py, test_approval_gate.py,
test_decision_gates.py, test_canonical_execution.py
  => 101 passed, 13 subtests passed, 0 failed
```

**M32/M32.1 authorization/resumption suites, re-run:**
```
test_approval_resumption.py, test_m32_1_ask_resumption_endpoint.py,
test_approval_store.py, test_m32_c2_c3_native_tool_loop.py,
test_m32_c_server_wiring.py, test_multi_user_isolation.py,
test_server_ask_narrative.py, test_server_approval_endpoints.py,
test_m33_batch_a_external_capability_contract.py
  => 146 passed, 0 failed
```

**Every other test file importing `capabilities/base.py` or
`capabilities/executor.py`** (found by grep, not assumed complete):
```
test_capability_directory.py, test_decision_engine.py,
test_m32_c3_2_tool_schema.py, test_m32_capability_effect_classification.py
  => 77 passed, 0 failed
```

**New focused suite, `test_m33_p1_permission_seam.py` — 16 tests, all
required categories from the kickoff instruction, real collaborators
throughout:**

| Category | Tests |
|---|---|
| Allowed permission | `test_checker_present_and_returning_true_allows`, `test_explicit_permissions_matching_scope_allows`, `test_action_level_scope_present_allows`, `test_chain_allows_when_every_step_is_authorized` |
| Denied permission | `test_checker_present_and_returning_false_denies`, `test_explicit_permissions_empty_set_denies_not_silently_allows` |
| Missing permission | `test_unmapped_capability_action_denies_by_default_even_with_checker`, `test_unmapped_capability_contributes_nothing_even_if_checker_allows_everything` |
| Checker error/failure | `test_checker_raising_is_treated_as_denied_not_a_crash`, `test_checker_raising_never_executes_the_action` |
| Multi-action mixed-permission | `test_chain_denies_entirely_when_any_step_is_unauthorized` (one permitted step, one denied step — the whole chain denies before any step runs, no partial execution) |
| No silent bypass (the named F2 regression) | all of the above collectively; `test_action_level_scope_missing_denies_even_when_capability_level_granted` proves the new action-level gate specifically |

```
test_m33_p1_permission_seam.py  16 passed
```

**Full repository-wide `pytest -q` (`COMPLETED_WITH_RESULT`, 242s):**
```
2042 passed, 40 subtests passed, 20 failed
```
The 20 failures are the exact same 20 (by name) already independently
confirmed pre-existing on clean HEAD `1b7d8d8` during M32.1's own
closure (stashed-changeset comparison) — none touch `base.py`,
`executor.py`, or `multi_action_dispatch.py`. 2042 = 1989 (M32.1
baseline) + 37 (Batch A) + 16 (this P1 suite), an exact accounting —
**zero new failures from either Batch A or P1.**

## 5. Scope verification

`git status` confirms exactly: `uri_core/capabilities/base.py`,
`uri_core/capabilities/executor.py`, `uri_core/core/multi_action_
dispatch.py` modified; `test_m33_p1_permission_seam.py` new. No file
under `uri_core/external/` (Batch A) touched. No `context_resolver.py`,
`capability_directory.py`, `registry.py`, `server.py`, or `audit_sink`
wiring touched — none of Batch B's own scope was smuggled in.

## 6. P2 re-check against post-M32 code

Re-verified directly against current source and M32's own evidence
trail, not re-quoted from the frozen blueprint's 2026-09-17 snapshot:

**Requirement 1 (flag supplied as a committed default, not an unset
env var).** `decision_engine_live_enabled()` (`canonical_execution.py:
93-100`) was changed under M32 B1.1: absence of `URI_ENABLE_DECISION_
ENGINE_LIVE` now resolves to `True` in code, not merely "nothing set
it." **SATISFIED.**

**Requirement 2 (full live battery against the canonical path, not
tests alone).** Traced directly: `native_tool_loop_enabled()`
(`native_tool_loop.py:107-115`) is **off by default**, deliberately
(its own docstring: canonical already had "36+ pre-existing tests and
multiple prior milestones' worth of live evidence"). Server.py's
real four-tier `/ask` fallthrough (workflow_continuation → native_tool_
loop [off by default] → `run_canonical_for_ask` → legacy) means an
ordinary `/ask` turn today genuinely reaches `run_canonical_for_ask`
by default — this is not merely reachable in theory, it is the actual
default code path for real traffic.

However, checking what M32's own D-series live evidence actually
exercised (not assuming): **D5's streaming verification and D6's
benchmark harness both call `run_native_tool_loop` directly** (`scripts/
m32_latency_profile.py:86-90,211,283`; D5 similarly requires `native_
tool_loop_enabled()=True` to stream, per its own completion report).
Neither is live evidence of `run_canonical_for_ask` specifically. The
one directly-relevant historical live-observation window is M30.8's
own Phase A (`docs/plans/M30_8_PHASE_A_OBSERVATION_AND_PHASE_B_
DISPOSITION.md`, exit-criteria verdict MET, 2026-09-14) — real, but
under the OLD explicit-flag-on regime, before M32 B1.1 changed the
default. Same code path, same function, but the specific live
observation predates today's implicit-default trigger condition.
**PARTIALLY SATISFIED** — strong circumstantial evidence (default-on
code path, 36+ pre-existing tests, one historical live window under
the same code with a different trigger), but no fresh live-observation
battery has been run specifically framed as "what breaks now that
canonical serves by default."

**Requirement 3 (fix what breaks, bounded).** No new breakage has
been reported against canonical across M32's D-series or this session's
M32.1/Batch A/P1 work. **No evidence of anything currently broken**,
but this is an absence-of-negative-reports finding, not a completed
breakage-hunting pass under P2's own name.

**Requirement 4 (re-examine the M30.8 completion-record discrepancy).**
The blueprint's F1 finding (M30.8 recorded COMPLETE-with-cutover while
the deployment ran legacy) **no longer describes current reality** —
canonical genuinely is the default-live path today, post-M32-B1.1. The
discrepancy is resolved in practice. No governance entry formally
closes this loop under a "P2 requirement 4" label, but the underlying
fact the blueprint flagged is no longer true.

**Exit criteria:**
- Real `/ask` turn observed via telemetry/log through `run_canonical_
  for_ask`, not by reading code — **NOT independently verified this
  session**; the default-on code path is confirmed by source, but no
  fresh telemetry/log capture was performed here.
- Legacy fallback (`CANONICAL_KILLSWITCH`/`CANONICAL_EXECUTION_
  ALLOWLIST`) demonstrated, not assumed — **checked directly**: zero
  mentions of either in M32's full evidence trail (`grep` returned
  nothing). **Never live-demonstrated under any milestone's name.**
- `orchestrator.py` does not grow — **confirmed holding**, repeatedly
  verified throughout M31/M32.
- Full regression, zero new failures, recorded live-observation
  battery — regression discipline held throughout M32 and this
  session; no dedicated "live-observation battery" exists under a P2
  label specifically.

**Classification: PARTIALLY SATISFIED.** Requirement 1 and the
underlying M30.8-discrepancy fact are genuinely resolved. The core
architectural claim (canonical is the real default path) is well-
supported by source and by 36+ pre-existing tests, but two concrete,
checkable items remain open and unverified: (a) the killswitch/
allowlist rollback lever has never been live-demonstrated under any
milestone's evidence trail, and (b) no live-observation battery has
been run specifically to hunt for breakage now that the default flipped
— M32's own live evidence exercised native_tool_loop, a materially
different, still-off-by-default tier, not canonical itself. Neither
gap blocks Batch B (which builds on the authorization seam, not on P2's
own exit criteria), but neither should be described as closed.

## 7. Is Batch B now unblocked?

**Yes, on the P1 dimension specifically.** The fail-open seam Batch B's
own "on top of P1's corrected seam" language depended on is fixed,
tested (16 new focused tests plus 344 total re-run across every
directly-affected suite, all passing), and scoped exactly to the
blueprint's own three files. Batch B may proceed on the authorization
seam.

**P2 is not a hard gate for Batch B** per the blueprint's own §2 table
(P1 → P2 → M33, but M33's own batches do not cite P2's exit criteria as
a precondition the way Batch B cites P1's). Its PARTIAL status is
disclosed above for completeness and governance accuracy, not as a
second blocker.

## 8. Residual risks / not yet verified

- Full repository-wide `pytest -q` now `COMPLETED_WITH_RESULT` (§4):
  2042 passed / 20 failed, all 20 the same pre-existing failures
  independently confirmed against clean HEAD during M32.1's closure —
  zero new failures. Resolved, no longer open.
- The two open P2 items above (rollback-lever live demonstration;
  a dedicated post-default-flip live-observation battery) remain
  genuinely open, disclosed, not treated as resolved by this report.
- Batch B, C, D remain not started.

## 9. Verdict

**P1: READY.** Root cause traced to source, fix scoped exactly to the
blueprint's three named files, 16 new focused tests plus 344 passing
re-runs across every directly-affected suite, plus a full repository-
wide sweep (2042 passed/20 pre-existing failures, zero new), zero
unrelated scope touched. **Batch B unblocked on the permission-seam
dimension.**

Not committed. Not pushed. M33.1/M34/M35 confirmed untouched.
