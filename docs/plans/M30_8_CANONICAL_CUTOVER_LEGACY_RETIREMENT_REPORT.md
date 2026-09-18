# M30.8 Canonical Cutover + Legacy Retirement — Implementation Report

**State:** IMPLEMENTED; awaiting independent Claude audit and the Phase A live
observation window required before any further destructive Phase B retirement.

---

## Correction (added 2026-09-18, per M32 Batch A/C3.4-prerequisite audit, B1.4)

**This correction is recorded per this repository's auditable-correction-history
convention: preserved alongside, not in place of, the original report below.**

This report is titled "M30.8 COMPLETE: canonical unsupported-dispatch repair,
Phase A live observation, Phase B disposition" (commit `698a6cb`), and the
migration commit itself (`0da36df`) is titled "…through Canonical Cutover +
Legacy Retirement." Both titles are correct about the *code that was written*:
the canonical branch, the allowlist killswitch, the narrowed-allowlist
rollback, and the engine-failure-only fallback boundary were all genuinely
implemented and tested (38 + 22 passed, cited above) exactly as this report
describes.

What neither title makes clear is that **the cutover was never actually
enabled in the live deployment**. `URI_ENABLE_DECISION_ENGINE_LIVE` (the flag
`server.py:1385-1415` gates the entire canonical branch behind) was never set
anywhere in this repository — not in `.env`, not in any committed config, not
by any code path — from M30.8's commit through the M32 latency diagnostic
(`docs/plans/M32_LATENCY_DIAGNOSTIC_REPORT.md`, measured 2026-09-17) that
found live traffic still served entirely by legacy `process_user_input`. "M30.8
COMPLETE" and "canonical cutover" were true of the implementation, not of
production traffic — an env var nothing sets is not a cutover.

M32 Batch B (`docs/plans/M32_EXECUTION_ARCHITECTURE_PLAN.md` §4) closes this
gap: `decision_engine_live_enabled()` and `workflow_continuation_mode_enabled()`
now default to `True` when their env vars are unset, with an explicit `"0"`
as the operational rollback lever (B1.1/B1.5), and the allowlist rollback
lever (`CANONICAL_EXECUTION_ALLOWLIST`) is now runtime-settable via
`URI_CANONICAL_EXECUTION_ALLOWLIST` rather than requiring a source edit and
redeploy (B1.2). See `docs/plans/M32_BATCH_B_COMPLETION_REPORT.md` for the
evidence that canonical is now actually the default authority for live
traffic, not merely for the code path.

## Phase A

- `/ask` now invokes canonical evaluation before `process_user_input` when
  `URI_ENABLE_DECISION_ENGINE_LIVE=1`.
- Valid canonical non-execution outcomes are terminal envelopes.  Clarification,
  unsupported, disconnected, approval-required, permission, and conversation
  outcomes do not invoke legacy.
- Only `MODEL_TERMINALLY_UNAVAILABLE`, `INVALID_PROPOSAL`, `DEGRADED`, or an
  execution-boundary failure request legacy fallback.  Each actual fallback is
  appended to the existing decision-shadow log with `event`, `fallback_reason`,
  and `gate_outcome`.
- `CANONICAL_EXECUTION_ALLOWLIST=None` means unrestricted canonical authority.
  Replacing it with any concrete set, including empty, is the emergency
  killswitch and restores legacy-first dispatch.
- Canonical legacy-capability execution now enters the existing `ApprovalGate`;
  it does not recreate permission, approval, or dispatcher authority.

## Phase B inventory

1. `WorkflowPlanner` task-type dispatch was retired. `_create_steps()` now
   always emits the one documented `generic_evidence_drafting_workflow`.
2. The legacy `uri_core/core/semantic_interpreter.py` has no production module
   or production importer; the existing AST reachability test confirms that
   status.
3. `MultiActionDispatch` was already migrated: `dispatch_explicit()` and
   `dispatch_chain_explicit()` consume the Decision Contract's explicit
   capability/actions while preserving executor, permission, and binding logic.
4. The large legacy `orchestrator.py` priority block is retained only as the
   narrow engine-failure fallback.  It cannot be safely deleted before the
   mandatory real Phase A observation window proves its remaining branches have
   canonical coverage.  No line-count reduction is claimed.

## Focused verification

- `pytest -q test_canonical_execution.py test_server_ask_narrative.py`:
  **38 passed**.
- `pytest -q test_workflow_planner.py test_workflow_durability.py
  test_workflow_capability_router.py test_orchestrator_model_driven_workflow.py
  test_shadow_provider_unreachable.py`: **22 passed**.

The M30.8 tests cover terminal canonical handling for missing parameter,
disconnected, approval-required, unsupported, and conversation outcomes; the
engine-failure-only fallback boundary; and narrowed/empty allowlist killswitch
semantics. Full-suite and live 12-scenario evidence remain audit gates, not
claims in this implementation report.
