# M30 State — URI Canonical Agent Loop Migration

**Plan:** `docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md`
(filename kept exactly as the User specified; this state file uses the
repository's standard M-numbered convention to track it)

STATE: ACCEPTED (plan only) — **Stage 4 implementation NOT authorized**

## Governance

Four-stage lifecycle per the User's own instruction: EVIDENCE → ARCHITECTURE
→ MIGRATION → IMPLEMENTATION.

- Stage 1 (EVIDENCE): `docs/research/URI_AGENT_LOOP_ROOT_CAUSE_AUDIT.md` — frozen.
- Stage 2 (ARCHITECTURE): `docs/architecture/URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md` — frozen/accepted.
- Stage 3 (MIGRATION): this plan — ACCEPTED, plan only.
- Stage 4 (IMPLEMENTATION): not started. Requires explicit separate User authorization per milestone (M30.0 through M30.10, see plan §17) — this plan does not itself authorize any implementation work.

## History Log

- 2026-09-12: Claude (Architect role) drafted Stages 1-3 across three
  sequential User-directed stages in one session: root-cause audit,
  canonical architecture design, and this migration plan. Each stage
  explicitly instructed "do not implement" and that instruction was
  followed throughout - no production code, prompts, routing, or
  capability wiring were changed by any of the three documents. Marked
  ACCEPTED under the standing auto-approval rule (routine planning), per
  ORCHESTRATION.md §1.5. Awaiting User review before any Stage 4
  milestone (M30.1 onward) may begin.

## Effect on other open plans

- M27 (`docs/plans/M27_MULTI_ACTION_LIVE_INTEGRATION_PLAN.md`): superseded
  as a standalone execution track; its built code is retained and folded
  into M30.2/M30.6 (see migration plan §18).
- M28 (`docs/plans/M28_PASSIVE_MEMORY_CANDIDATE_PIPELINE_PLAN.md`):
  absorbed into M30.9, not implemented as a separate track (see migration
  plan §9/§18). Its own STATE.md should be updated to reference this
  disposition when Stage 4 begins.
- M29 (`docs/plans/M29_BRAIN_DECISION_CONTRACT_PLAN.md`): superseded by
  Stage 2 §5 / this plan directly - M29 was this same investigation's own
  preliminary draft. Its own STATE.md should be marked superseded when
  Stage 4 begins.

## Release gate

Unchanged standing rule (2026-09-12 live-verification-gate revision):
Claude does not commit/push, and does not begin Stage 4 implementation,
until the User has personally reviewed this plan and given explicit
direction to proceed.
