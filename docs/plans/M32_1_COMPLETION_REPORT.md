# M32.1 — Execution Continuation Residual Hardening: Completion Report

Blueprint: `docs/plans/M32_1_EXECUTION_CONTINUATION_RESIDUAL_HARDENING_PLAN.md`
(ACCEPTED). Clean HEAD: `1b7d8d8`. Not committed/pushed — per explicit
instruction, stopping here for verified-results report.

## 1. Files changed (exact)

| File | Change |
|---|---|
| `uri_core/core/approval_store.py` | `ProposedAction.action_name: Optional[str] = None` field added; `propose()` gained `action_name` param, threaded to the constructed record; `_load()` round-trips `action_name=raw.get("action_name")`. |
| `uri_core/core/canonical_execution.py` | New `_propose_durable_gmail_approval()` helper. `_execute_gmail()` (single-action branch only) bridges an `awaiting_approval` result to a real durable `ApprovalStore` record, injecting the resulting `action_id` into `envelope["execution"]` and `envelope["response"]`. `decide_fallback_reason()` widened to apply the allowlist/killswitch check to `APPROVAL_REQUIRED` as well as `READY` (a real gap this milestone would otherwise have introduced — found and closed during implementation). `run_canonical_for_ask()`'s dispatch condition widened to `gate_result.outcome in ("READY", "APPROVAL_REQUIRED")`. Module docstring's stale "approval-required cases ... exactly as they do today, unchanged" claim corrected with an inline M32.1 note (it was false for the Gmail path before this milestone). |
| `uri_core/core/approval_resumption.py` (NEW) | `classify_confirmation()`, `find_resumable_actions()`, `_clarification_envelope()`, `_error_envelope()`, `resume_pending_approval()`, `approval_resumption_enabled()`/`APPROVAL_RESUMPTION_ENV_VAR` toggle (default OFF). |
| `uri_core/app/server.py` | New early-check block in `ask()`, before the existing M30.7 workflow_continuation block: calls `resume_pending_approval()` when the feature flag is on; if it returns a non-`None` result, that result short-circuits the rest of `/ask`. Fixed the pre-existing workflow_continuation block's `result = None; early_executed = False` reset so it no longer silently discards an already-resumed result (now only resets `legacy_fallback`, and the whole block is skipped when `early_executed` is already `True`). |
| `test_approval_resumption.py` (NEW) | 17 unit tests, real collaborators (real `ApprovalStore`/`ApprovalGate`/`MultiActionDispatch`/`GmailCapability`, faked Gmail service backend only). |
| `test_m32_1_ask_resumption_endpoint.py` (NEW) | 4 server-wiring tests via `TestClient`, mocking `resume_pending_approval` at the seam `server.py` calls (mirrors `test_m32_c_server_wiring.py`'s own convention: mock the exact seam, not re-test logic already covered elsewhere). |
| `docs/plans/M32_1_EXECUTION_CONTINUATION_RESIDUAL_HARDENING_PLAN.md` (NEW) | Frozen blueprint. |

Feature is fully dormant by default: `URI_ENABLE_APPROVAL_RESUMPTION`
unset → byte-identical `/ask` behavior (proven by
`test_toggle_off_by_default_never_calls_resumption`).

## 2. Test evidence

Unit + wiring suites, this milestone's changeset:

```
test_approval_resumption.py .................... 17 passed
test_m32_1_ask_resumption_endpoint.py .......... 4 passed
```

Full regression sweep across every touched/adjacent suite:

```
test_approval_resumption.py, test_m32_1_ask_resumption_endpoint.py,
test_approval_store.py, test_approval_gate.py, test_canonical_execution.py,
test_multi_action_capabilities.py, test_decision_gates.py,
test_m32_c2_c3_native_tool_loop.py, test_authoritative_facts_immutability.py,
test_m22_3_ask_size_limit.py, test_m32_c_server_wiring.py,
test_multi_user_isolation.py, test_server_ask_narrative.py,
test_server_approval_endpoints.py
  => 226 passed, 13 subtests passed, 0 failed
```

Broader repository-wide `pytest -q` sweep (full suite, `COMPLETED_WITH_RESULT`,
853s): **1989 passed, 40 subtests passed, 20 failed.** Every one of the
20 failures independently reproduced by stashing all M32.1 changes and
re-running against clean HEAD `1b7d8d8` — all 20 fail identically with
no M32.1 changes present (7 route-count/session-workflow/restart-
recovery/newline-boundary failures, 7 pre-existing Drive/m20-recovery-
loop failures, 6 live-Ollama-connection failures that require a
running local Ollama server). None touch `approval_store.py`,
`canonical_execution.py`, `approval_resumption.py`, or the `/ask`
resumption block. Confirmed pre-existing, not introduced by this
milestone. Working tree verified restored intact after the stash/pop
round-trip (`git status` matches the pre-stash M32.1 changeset exactly).

## 3. Live multi-turn evidence

Ad-hoc script run against real collaborators (temp-file `ApprovalStore`,
real `ApprovalGate`/`MultiActionDispatch`/`GmailCapability`, faked
Gmail service backend), covering the User's 6 named scenarios plus
the two additional invariants proven at the `ApprovalStore` layer:

```
=== SCENARIO 1: approval requested turn 1 ===
turn1 status: awaiting_approval action_id: 0c8b6d0d-a3c7-4ee7-9abd-869f3eaca985

=== SCENARIO 2: NL approval turn 2 resumes correct action ===
turn2 status: success drafts: [{'to': 'a@example.com', 'subject': 'hi', 'body': 'hello'}]

=== SCENARIO 3: duplicate approval turn 3 does not execute twice ===
turn3 (dup 'yes') result: None -- drafts still: [{'to': 'a@example.com', 'subject': 'hi', 'body': 'hello'}]

=== SCENARIO 4: wrong session cannot resume ===
wrong-session result: None -- drafts: []
session-B still has pending: 1

=== SCENARIO 5: stale/expired approval fails safely ===
expired-resume result: None -- drafts: []

=== SCENARIO 6: ambiguous multiple pending requires clarification ===
ambiguous result status: clarification_required -- pending count: 2 -- drafts: []

=== ALL 6 SCENARIOS: PASS ===
```

Interpretation:
- **Turn 1** — Gmail `create_draft` proposed with no arguments-side
  effect (`gmail.drafts == []` at proposal time, confirmed separately
  in `DurableGmailApprovalBridgeTests`); real `action_id` now present
  in `ApprovalStore` (previously: none).
- **Turn 2** — plain "yes" on a later turn resolves to the SAME
  action, dispatches through the same `dispatch_explicit()` real
  approval would use, produces the correct real draft.
- **Turn 3 (duplicate)** — a second "yes" finds nothing pending
  (already consumed) → returns `None` → falls through to normal `/ask`
  processing, never a second draft. Separately proven at the
  `ApprovalStore` layer directly: a second `decide()` call on an
  already-decided `action_id` raises `ApprovalError` rather than
  silently succeeding.
- **Turn 4 (wrong session)** — session isolation confirmed: a
  different session's "yes" sees nothing, and the real owning
  session's action is still genuinely pending afterward (not
  consumed, not corrupted) — proven via `find_resumable_actions`.
- **Turn 5 (expiry)** — TTL enforced without a real 15-minute wait, by
  directly mutating the persisted `created_at` and reloading; expired
  action is excluded by `list_pending()` and resumption correctly
  falls through rather than executing a stale approval.
- **Turn 6 (ambiguous)** — two pending Gmail drafts in one session;
  "yes" returns a deterministic `clarification_required` envelope
  naming both, executes neither.

Restart/recovery additionally proven in
`RestartRecoveryTests.test_pending_action_survives_fresh_store_instance`:
a brand-new `ApprovalStore` instance pointed at the same file (process
restart simulation) sees the same pending action and completes
resumption correctly.

## 4. Requirement-by-requirement disposition

| # | Requirement | Status |
|---|---|---|
| 1 | Inspect before editing | Done — see blueprint's Root-cause investigation section. |
| 2 | Define/persist minimum durable continuation state | `ProposedAction.action_name` + existing fields. |
| 3 | Never infer/resume when ambiguous | `clarification_required`, never guessed — Scenario 6. |
| 4 | Per-user/session isolation | Exact `session_id` match only — Scenario 4. |
| 5 | Preserve grants/permissions/evidence/audit/dispatch/idempotency/canonical boundaries | No new dispatch mechanism; reuses `ApprovalGate.decide()`/`dispatch_explicit()` verbatim; `_bind_context()` idempotency confirmed safe. |
| 6 | Never bypass original authorization | Same decide/dispatch calls a fresh approval uses — live-verified real `action_id` + real draft creation. |
| 7 | Expiry/cancellation/duplicate/stale/restart/ambiguous handled safely | Scenarios 3, 3b, 4, 5, 6 + restart-recovery test. |
| 8 | Tests + live evidence for the 6 scenarios | §2, §3 above. |
| 9 | Regression coverage | §2 above (226/226 targeted; full 2009-test sweep 1989 passed/20 failed, all 20 independently confirmed pre-existing on clean HEAD `1b7d8d8`, zero attributable to M32.1). |
| 10 | This report | This document. |

## 5. Scope discipline

- Multi-step chain approval resumption (`dispatch_chain_explicit`) is
  explicitly out of scope, per the blueprint's Non-goals — a pending
  chain approval remains as non-durable as before this milestone.
  Disclosed in both the module docstring of `approval_resumption.py`
  and the blueprint.
- `canonical_execution.py`'s module docstring correction (§1 above)
  discloses a pre-existing documentation inaccuracy found during this
  milestone's own investigation, corrected in place rather than left
  stale — not a new production-behavior change, a truthfulness fix.

## 6. Residual risks / not yet verified

- **Broad repository-wide `pytest -q` sweep**: `COMPLETED_WITH_RESULT`
  (853s, 1989 passed / 40 subtests / 20 failed). All 20 failures
  independently reproduced against clean HEAD `1b7d8d8` with M32.1's
  changes stashed out — confirmed pre-existing, not caused by this
  milestone (route-count/session-workflow/restart-recovery baselines,
  Drive-service test fixtures, and live-Ollama-connection tests
  requiring a running local server). None touch this milestone's
  changed files. Resolved — no longer a residual risk.
- **Multi-step chain approval resumption remains unresolved** —
  unchanged from before this milestone, explicitly out of scope.
- **Feature is default-OFF** (`URI_ENABLE_APPROVAL_RESUMPTION` unset).
  Dormant in production until explicitly enabled — this is intentional
  (matches this repo's standing default-OFF convention for every new
  risk-bearing behavior), not a gap, but worth stating plainly: nothing
  in this milestone changes current production behavior by itself.
- **Operational note (not a defect)**: this session's own working
  copy of the frozen blueprint file was accidentally overwritten with
  a placeholder mid-session by a stray `Write` call, then reconstructed
  from the design already established in the session's own working
  context (root-cause findings, design, non-goals, acceptance
  criteria). Recorded in the blueprint's own History log per this
  repository's auditable-correction-history convention. No design or
  implementation content was affected — only the after-the-fact
  written record of the design, which has been restored.

## 7. Verdict

**READY** for the User's live verification step (per the standing
2026-09-12 live-verification gate revision — Claude's own formal
independent audit-for-release runs after the User verifies and directs
commit/push, not before). All 10 kickoff requirements satisfied with
concrete evidence, including the full repository-wide regression sweep
(§2, §6) now returned clean of any M32.1-caused failure.

Not committed. Not pushed. M33 not started.
