# M33.3 Batch A — State

**Status:** ACCEPTED (planning only). Implementation not started.
**Milestone:** M33.3 — Edge Intelligence Qualification & Integration
**Batch:** `M33.3-A` — Edge Intelligence Stage A Qualification Readiness
**Plan:** `docs/plans/M33_3_BATCH_A_STAGE_A_QUALIFICATION_READINESS_PLAN.md`
**Parent plan (frozen, unchanged):**
`docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md` (`47af60a`)
**Baseline:** `1fa24fca97dec34e431e82062b27b3da222b87cd`
**Integration authority:** none. No `INT-*` event. No research component promoted.

## History log

- **2026-09-25 — DRAFT → ACCEPTED (Claude, standing auto-approval,
  `ORCHESTRATION.md` §1.5).** Planned from primary repository evidence at
  baseline `1fa24fc`. Verified in this session: governance validator `VALID`;
  governance suite 37 passed; M33.2 Edge contracts unchanged since the B.4
  release (`git diff --stat 340a009 HEAD` over the Edge packages, Needle
  bridge, and Edge benchmark fixtures is empty); M33.2 regression set 58
  passed, 2 failed, both failures traced to CRLF working-tree conversion
  (`core.autocrlf=true`) with committed LF blobs matching their manifests;
  `evaluate_routing` has no production caller and
  `DEFAULT_EDGE_RUNTIME_INVENTORY` has no runtimes, so no Edge model is
  dispatched in production (static finding; runtime confirmation stays a
  Stage B precondition). Batch scope is Stage A readiness only: battery
  freeze, scorer, reference baselines (R-NULL, R-9B, R-NEEDLE, R-DET), Rung 0
  as-is characterization, documentary M33.2 contract mapping, Rung 1
  eligibility record. No mechanism change, no model download, no `uri_core`
  import, no change under `uri_core/`, `uri_v1/`, or `uri_ui/`.

## Routing

Antigravity: route WP-A0..WP-A7 to Codex under standing AO-4 routing. The
implementation task package must quote these plan boundaries verbatim:

1. No Batch A module may import `uri_core` (plan G-R4).
2. `scripts/m33_2_needle_bridge.py` must not be modified; build a new sibling
   bridge (plan WP-A3).
3. No model download, pull, or install (plan §6, G-S4).
4. All side-effecting tools are mocks (plan G-S4).
5. Battery is frozen and reviewed by Claude before any baseline runs (plan
   WP-A1 checkpoint).
6. Fixture hashes use LF-normalized bytes (plan WP-A1, G-R3).
7. Any new Python dependency is flagged in the completion report.

## Checkpoints

| Checkpoint | Owner | Status |
|---|---|---|
| WP-A0 evidence pins re-verified | Codex | NOT STARTED |
| WP-A1 battery frozen (hash recorded here) | Codex, then Claude review | NOT STARTED |
| WP-A2 scorer and telemetry schema with tests | Codex | NOT STARTED |
| G-R1 Needle bridge reproduction (8/8, 4/4) | Codex | NOT STARTED |
| G-R2 deterministic RAR reproduction | Codex | NOT STARTED |
| WP-A3 baselines R-NULL / R-9B / R-NEEDLE / R-DET | Codex | NOT STARTED |
| WP-A4 Rung 0 as-is characterization | Codex | NOT STARTED |
| WP-A5 contract mapping document | Codex | NOT STARTED |
| WP-A6 Rung 1 eligibility record and draft conditions | Codex | NOT STARTED |
| WP-A7 completion report, `VERIFICATION_READY` | Codex | NOT STARTED |
| Independent audit, `VERIFIED` / `NOT VERIFIED` | Claude | NOT STARTED |

Battery hash (LF-normalized SHA-256): not yet frozen.

## Recovery state

None. No pause recorded.

## Next action

`READY_FOR_M33_3_BATCH_A_EXECUTION` — Antigravity picks up this ACCEPTED plan
and routes it to Codex.
