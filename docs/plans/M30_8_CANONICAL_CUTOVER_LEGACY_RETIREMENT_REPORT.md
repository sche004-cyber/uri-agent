# M30.8 Canonical Cutover + Legacy Retirement — Implementation Report

**State:** IMPLEMENTED; awaiting independent Claude audit and the Phase A live
observation window required before any further destructive Phase B retirement.

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
