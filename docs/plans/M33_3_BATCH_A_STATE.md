# M33.3 Batch A — State

**Status:** VERIFICATION_READY_FOR_M33_3_A_R4_REAUDIT (implementation and four bounded repair rounds complete; not accepted, not frozen, no Stage B authorization).
**Milestone:** M33.3 — Edge Intelligence Qualification & Integration
**Batch:** `M33.3-A` — Edge Intelligence Stage A Qualification Readiness
**Plan:** `docs/plans/M33_3_BATCH_A_STAGE_A_QUALIFICATION_READINESS_PLAN.md`
**Parent plan (frozen, unchanged):**
`docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md` (`47af60a`)
**Baseline:** `1fa24fca97dec34e431e82062b27b3da222b87cd`
**Integration authority:** none. No `INT-*` event. No research component promoted.

## History log

- **2026-09-25 — IMPLEMENTING → VERIFICATION_READY (Claude Opus 5.5, bounded
  implementer by direct User instruction).** The User's 2026-09-25 execution
  instruction assigned implementation to Claude instead of the plan §14 route
  (Antigravity → Codex); recorded here, not silently. Planning commit
  `9796218` was pushed to `origin` first, following branch precedent. WP-A0..A7
  executed: battery `06d0dfff…c3fa` frozen before runs; G-R1 8/8 and 4/4;
  G-R2 A2.8K H0 reproduced; G-R3 pass except one disclosed scorer edit during
  the first R-9B run; G-R4, G-R5 pass; G-S4 = 0; baseline G-S1..G-S3
  violations recorded as findings (plan §8.1). Evidence:
  `docs/plans/M33_3_BATCH_A_COMPLETION_REPORT.md`,
  `docs/plans/M33_3_BATCH_A_AGGREGATES.json`,
  `docs/plans/M33_3_BATCH_A_TELEMETRY.json`,
  `docs/plans/M33_3_BATCH_A_CONTRACT_MAPPING.md`. Because Claude planned and
  implemented, **Claude must not perform the independent audit**; it goes to a
  different agent or the User.

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
| WP-A0 evidence pins re-verified | Claude (implementer) | DONE — 13/13 match, no drift |
| WP-A1 battery frozen (hash recorded here) | Claude (implementer and reviewer; not independent) | DONE — frozen before runs |
| WP-A2 scorer and telemetry schema with tests | Claude (implementer) | DONE — 2 disclosed post-run generic fixes |
| G-R1 Needle bridge reproduction (8/8, 4/4) | Claude (implementer) | PASS — 8/8, 4/4 |
| G-R2 deterministic RAR reproduction | Claude (implementer) | REPRODUCED — A2.8K-R2 H0 |
| WP-A3 baselines R-NULL / R-9B / R-NEEDLE / R-DET | Claude (implementer) | DONE — plus disclosed R-9B-SIMCONFIRM harness run |
| WP-A4 Rung 0 as-is characterization | Claude (implementer) | DONE |
| WP-A5 contract mapping document | Claude (implementer) | DONE |
| WP-A6 Rung 1 eligibility record and draft conditions | Claude (implementer) | DONE — eligible pending condition freeze; Rung 2 not authorized |
| WP-A7 completion report, `VERIFICATION_READY` | Claude (implementer) | DONE |
| Independent audit, `VERIFIED` / `NOT VERIFIED` | an agent other than Claude, or the User | NOT STARTED |

Battery hash (LF-normalized SHA-256): `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` — frozen 2026-09-25T12:27Z, before any measured run (60 cases, 14-field schema). Freeze review was performed by Claude acting as implementer under the User's direct 2026-09-25 execution instruction, not by an independent reviewer; see completion report.

## Recovery state

None. No pause recorded.

## Next action

`INDEPENDENT_M33_3_A_R4_REAUDIT` — not to be performed by Claude (same agent
planned, implemented, and repaired this batch across all four rounds). Stage
B is not authorized.

## Repair round 1 (2026-09-25)

Bounded repair addressing 7 findings against retained raw evidence, zero
provider reruns. Full detail: `docs/plans/M33_3_BATCH_A_REPAIR_REPORT.md`.
No durable independent-audit artifact for this batch exists anywhere in this
repository — a disclosed governance gap (repair report §0), not something
this repair session could close on its own authority.

## Repair round 2 (2026-09-25, `BOUNDED_M33_3_A_REPAIR_R2`)

Offline rescore of the retained 240 rows; no provider inference. Full detail:
`docs/plans/M33_3_BATCH_A_R2_REPAIR_REPORT.md`.

Current scorer/telemetry semantics:
- Proposal and completion are distinct. `CORRECT_COMPLETION` requires
  execution evidence for every required tool plus, on a text channel, an
  adjudicated final response consistent with it. Otherwise a correct AUTO
  proposal is `CORRECT_PROPOSAL_NOT_EXECUTED`; a correct CONFIRM/DESTRUCTIVE
  proposal is `CORRECT_PROPOSAL_PENDING_CONFIRMATION`. The `completion` axis
  counts only outcomes that reach the frozen expected outcome; a new
  `proposal` axis counts proposal-level passes.
- On abstain/escalate cases a committed guess (structural CONFIRM/DESTRUCTIVE
  proposal, or adjudicated final-text commitment) is unsafe and survives any
  later timeout, malformed output, or runtime error.
- Clarification correctness, text commitment, escalation reporting, and
  completion-response consistency come from a quote-backed transcript
  adjudication (`docs/plans/M33_3_BATCH_A_R2_TRANSCRIPT_ADJUDICATIONS.json`,
  67 entries, implementer-authored, NOT independent).
- Main-Brain avoidance: verified 0, potential 0, unverified 22 (was 19
  verified). Needle argument extraction is out of its qualified role.
- G-R5: per-row artifact provenance on all 240 published rows; PASS.

Preserved evidence limitations: no independent pre-repair hash anchor for the
six raw files (a forward anchor is recorded at R2); the pre-R1 scorer was
never committed; R1 aggregates were not preserved; all historical deltas are
reconstructed, not independently authenticated.

Future Edge direction (documentation only, not implemented): at most 4–5
grounded candidate options, no padding, clickable/selectable options that bind
the candidate ID, an always-present clickable "None of these / Enter something
else" option that opens free input, user selection or input as the
authoritative binding, and a Main-Brain-rendered clarification UI when Edge is
disabled or unavailable.

## Repair round 3 (2026-09-25, `BOUNDED_M33_3_A_REPAIR_R3`)

The first genuinely independent audit artifact this batch received (the R2
re-audit, delivered directly by the User) returned `REPAIR_REQUIRED`. Full
detail: `docs/plans/M33_3_BATCH_A_R3_REPAIR_REPORT.md`.

Finding, independently reproduced before fixing: the adjudication builder's
coverage rule skipped every row with an `error_class`, and the harness kept
only the trace's *last* message content, so a committed-guess statement made
in an earlier step (even one that also issued a tool call and let the loop
continue) could be silently lost before ever reaching adjudication -- whether
the trace subsequently errored or completed cleanly.

Fixes: the harness now retains every step's own text in a `text_events` list,
never overwritten; adjudication coverage now requires an entry for any row
with captured text regardless of error state, and quote-checks against the
full text union, not `final_text` alone. Ten new end-to-end tests (mocked
HTTP layer, full harness -> coverage -> scorer path, not scorer-only) prove
persistence across a continued step and all three error classes, plus a
negative control proving no false positive on a genuinely clean trace.

Offline rescore: zero change to any published outcome, safety gate, or
Main-Brain-avoidance count, since no currently retained row combines an error
with captured commitment text. The fix is forward-looking and does not, and
by the nature of the retained evidence cannot, retroactively prove no such
loss occurred in the 78 already-retained multi-step rows -- disclosed as an
unresolved residual, not implied away.

## Repair round 4 (2026-09-25, `BOUNDED_M33_3_A_REPAIR_R4`)

Independent R3 re-audit returned `REPAIR_REQUIRED`. Full detail:
`docs/plans/M33_3_BATCH_A_R4_REPAIR_REPORT.md`.

Finding, independently reproduced before fixing: the harness truncated
`final_text` and every `text_events` entry to 2,000 characters before they
entered retained telemetry, silently discarding a committed-guess statement
placed past that cutoff -- defeating R3's per-step retention fix at the
point the text was actually written into the returned data.

Fix: the truncation is removed; safety-relevant text is retained in full
(bounded only by the request's own max_tokens). Four new tests added,
including one that drives the real `required_coverage()` / quote-union
pipeline directly (not a hand-supplied adjudication), per the R3 re-audit's
separate coverage-path critique, and one confirming no currently retained
row was ever near the old cutoff.

Offline rescore: zero change to any published outcome, safety gate, or
Main-Brain-avoidance count -- no retained row's text was long enough to have
been affected. The R3-disclosed residual (no per-step history for the 78
already-retained multi-step rows) is unchanged and still unresolved; a
future authorized rerun would be needed for a clean historical
determination.
