# Scenario 2 Connection Gate Repair - State

**Plan:** `docs/plans/M30_SCENARIO2_CONNECTION_GATE_REPAIR_PLAN.md`

STATE: CLAUDE ACCEPT (2026-09-14) - implemented exactly as planned,
verified against real evidence. See the 2026-09-14 history entry below.

## Governance

Scoped strictly to Scenario 2's specific defect (Decision Engine
rejects a disconnected capability's "unsupported" self-report before
the connection gate can report real runtime state), found and
disclosed during M30.7C's resumed live verification pass
(2026-09-14). Independent of, and does not reopen, M30-PFC (closed
ACCEPTED) or M30.7C's own remaining scope. Independent of M30.8, which
remains NOT AUTHORIZED.

## History Log

- 2026-09-14: During M30.7C's resumed live verification, 4 real
  Scenario 2 attempts consistently failed to reach a clean canonical
  `DISCONNECTED` gate outcome. Root cause traced (not merely
  hypothesized): the model correctly self-reports a disconnected
  Gmail capability as `mode: "unsupported"`, `capability: null`
  (contradicting its own system prompt's explicit instruction to keep
  the capability named), and the Decision Engine's own safety net for
  this exact case (`_plausible_match_exists()`) rejects the false
  claim (`INVALID_PROPOSAL`/`false_unsupported_claim_rejected_by_
  directory`) without ever consulting the connection gate's own
  already-correct, already-generic availability classification for
  the matched candidate. See `docs/plans/M30_7C_READINESS_EVIDENCE_
  CLOSURE_REPORT.md` § Scenario 2 for the full live evidence, and
  `M30_8_BLOCKER_DISPOSITION_PLAN.md`'s updated Future Direction Notes
  for why this matters to the User's own "Canonical Cutover + Legacy
  Retirement" direction for M30.8.

- 2026-09-14: User issued a product decision (connection availability
  must be a generic, deterministic, non-model-inferred check, reusable
  across Gmail/Drive/MCP/plugins/future services; backend remains
  source of truth; UI owns reconnect UX; the Decision Engine must never
  reject/reinterpret a disconnected capability before the connection
  gate reports real state) and requested a bounded repair plan only -
  explicitly "Do NOT implement yet."

  Claude audited `capability_directory.py`, `capabilities/base.py`,
  `capability_relevance.py`, `decision_gates.py`, and `decision_
  engine.py`'s own system prompt, and found: the connection/
  availability gate itself (`decision_gates.py` Gate 5) is already
  fully generic and already correct - the defect is purely that Gate 5
  is unreachable from the "no capability named" branch that a
  non-compliant model's `"unsupported"`/`capability: null` proposal
  takes. Produced `M30_SCENARIO2_CONNECTION_GATE_REPAIR_PLAN.md`: a
  narrow, single-file (`decision_gates.py`), extract-function repair
  reusing three already-existing generic mechanisms (`plausible_
  matches()`, `CapabilityDirectory.describe()`, Gate 5's own
  classification logic) - no new mechanism invented, no Gmail-specific
  code anywhere in the fix. Recommended treating this as an earlier
  deterministic routing prerequisite inside the existing gate pipeline
  rather than a new pre-Brain-reasoning gate, with the stronger
  pre-reasoning variant recorded as a separate, higher-risk future
  option (real false-positive-hijack risk given `capability_
  relevance.py`'s own deliberately permissive threshold and its own
  prior M30.5A false-positive history). Disclosed a related, out-of-
  scope gap: no distinct `REAUTH_REQUIRED` gate outcome exists today
  (everything collapses to `DISCONNECTED`) - recommended as a separate
  future vocabulary change, not bundled here. 8 required tests
  specified (not yet written). No production code written by Claude.
  Marked ACCEPTED under the standing auto-approval rule for the
  planning work itself; **implementation is a separate authorization
  the User has not yet given.**

- 2026-09-14: User approved implementation exactly as planned. Claude
  implemented the single-file `decision_gates.py` change (extracted
  `_availability_outcome()` helper, reused verbatim for the existing
  "capability WAS named" path, new call site in the "no capability
  named"/`unsupported` branch). Verification:
  - 6 new deterministic tests (`ScenarioTwoConnectionGateTests`) all
    passing; full `test_decision_gates.py` (27/27) and
    `test_decision_engine.py` (42/42) suites re-run unchanged and
    passing - zero regression to the existing gate pipeline.
  - Live re-verification against the real, isolated disconnected-Gmail
    fixture: `gate_outcome: "DISCONNECTED"` now appears in both
    canonical and shadow telemetry (previously always
    `INVALID_PROPOSAL`), for the same `mode: "unsupported"` model
    behavior already observed pre-repair.
  - Directly confirmed the gate's own authoritative `capability_id` is
    `"Gmail"` (not the shadow log's own separate `capability_id` field,
    which by pre-existing design always echoes the model's raw claim,
    not the gate's verdict) by calling `evaluate_gates()` in-process
    against the real `CapabilityDirectory`/`GmailCapability`/
    `GmailService` stack with the same isolated invalid-token fixture
    and the exact real contract shape observed live: `{"outcome":
    "DISCONNECTED", "capability_id": "Gmail", ...}`.
  - Full regression (run in 5 batches due to real, disclosed system
    memory pressure - see below): 1743 total items, 8 pre-existing
    failures (exact name-for-name match to the established baseline:
    `step3_test.py::test_drive`, `step4_test.py::test_download`,
    `test_m20_feasibility_validation.py` x1, `test_m20_recovery_loop.py`
    x2, `test_m20_semantic_interpreter_resilience.py` x2,
    `test_usage_import_boundary.py` x1), 0 new failures, 27 subtests
    passing. One additional failure was observed transiently in one
    batch (`test_orchestrator_session_workflow.py::test_session_facts_
    are_used_for_clarification`) - independently diagnosed as caused by
    the local Ollama process being down at that moment (a real,
    disclosed side effect of Claude's own memory-management actions
    mid-session, not a code regression) and confirmed passing
    immediately upon isolated re-run with Ollama restored.
  - No `REAUTH_REQUIRED` state added (as instructed). No pre-Brain
    connection gate introduced (as instructed). No file outside
    `uri_core/core/decision_gates.py` and `test_decision_gates.py`
    modified.

  **Self-audit verdict: ACCEPT.** Scenario 2 is now genuinely closed
  with real, live, telemetry-confirmed evidence - not merely unit-
  proven. See `docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_REPORT.md`
  for the updated 12-scenario matrix and the final M30.8 readiness
  conclusion this closure enables.

## Release gate

Per the 2026-09-12 live-verification-gate revision and this session's
standing AO-4 discipline: implementation against this plan requires
its own separate, explicit User authorization. Once implemented,
Claude independently re-audits against real telemetry/test-suite
results and the required live re-verification (plan §4 item 8) before
treating the repair as closed.
