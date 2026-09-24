# M35 URI v1 — A2.8J: RAR-SAFE Evidence-Safety Hardening Qualification (PLAN)

Status: ACCEPTED (auto-approved per ORCHESTRATION.md §1.5 standing rule — routine engineering experiment, no core architecture/security-model change; Claude self-accepts and hands off to Antigravity → Codex per AO-4 roles).

Role note: Claude (this session) is Architect/Pre-Auditor only for this batch. Implementation (RAR-SAFE variant, harness, scorer, telemetry, execution) is substantial multi-file work and is routed to Codex via Antigravity, not built by Claude directly. Claude performs the final independent audit after Codex reports completion, per standing AO-4 roles.

## 0. Evidence Base (carried forward, not re-derived)

Source: independent Explore-agent evidence recovery against actual repository files (A2.8C–A2.8I reports, `rar_deterministic.py`, `rar_contracts.py`, RAR test suite, candidate-construction code). No prompt-supplied claim is treated as authoritative without repo confirmation. Corrections explicitly carried forward, per A2.8I:

- The one C2 `INCORRECT_CONFIDENT_BINDING` is **`NB-B-05:r1`** (not `NB-H-06`, which is `CORRECT_ABSTENTION` at C2).
- `NB-A-04`'s block is a **span-prefix** issue (`"file "` intro word defeats Level 0's exact-match), not an identifier-system mismatch.
- D1RQ carries one undisclosed, non-material deviation (`re.IGNORECASE` on `_POSSESSIVE_RE`).
- RAR invocation counts in A2.8H (31/63/83/83) did not reproduce (15/63/82/82); flagged non-material, unresolved.

## 1. RAR Cascade — Existing Evidence Semantics (repo-verified)

File: [uri_v1/turn/rar_deterministic.py](uri_v1/turn/rar_deterministic.py), entry `resolve_rar_deterministic_extended`. Ordered cascade, first match wins:

| Level | Lines | Can RESOLVE? | Evidence used | Known unsafe mechanism |
|---|---|---|---|---|
| 0 Exact ID/alias | 280-313 | yes | verbatim ID/alias match | — |
| 1 Active anchor | 316-347 | yes | selected UI/current attachment/unique title | — |
| 2 Verbatim title | 350-378 | yes/AMBIGUOUS | title/stem match | — |
| 3 Active pointer | 381-425 | yes/UNKNOWN | `"same"` recency hint | — |
| 4a Negation/contrast elim | 428-496 | yes (contrast shortcut) | lexical overlap elimination, then binds sole survivor | **Known B**: binds survivor even when elimination matched nothing (`NB-H-06`, active/unsafe) |
| 4b Type filter | 508-562 | yes (1-match branch, 526-558) | type hint, singleton pool | **New G**: singleton type match binds on zero substantive query evidence (`NB-B-05:r1`@C2, active/unsafe) |
| 5 Temporal/version | 565-692 | yes | `recency_rank` ordinal | **Known A**: commits before Level 6 validates; currently masked (`recency_rank` always 0 in production/candidate harness), latent per counterfactual probe (+3 ICB @C1, +5 @C2) |
| 5.5 Attachment | 694-741 | yes | `is_attachment` metadata | — |
| 6 Discriminating terms | 742-921 | yes/AMBIGUOUS/UNKNOWN | TF-IDF-style overlap incl. domain-tag bonus (line ~167-168), absent-entity all-or-nothing check (line 786) | **New F**: domain-tag bonus scores a person's name higher on an associated email than on their own contact record — latent T2 hazard (3/7 T2 cases would flip to ICB @C2 if bare-name detection existed) |
| 7 Residual classify | 923-955 | never (final UNKNOWN/AMBIGUOUS) | — | — |

Per A2.8I §10: on the real corpus, only Levels 2, 4b, and 6 have ever produced a *correct* resolution. Levels 0, 1, 3, 5, and 4a's contrast path have never produced a correct resolution — 4a's contrast path has only ever produced the one active unsafe binding.

## 2. Hypothesis Under Test

RAR's cascade lacks a single, consistent evidence-sufficiency invariant. Formalized per A2.8I §16 as one rule with two clauses:

> No level may commit a binding that the resolver's own Level-6 lexical/absent-entity evidence contradicts, and no binding may be committed on zero substantive evidence.

This is the direct unification of Known A (masked/latent), Known B (active), New G (active), New F (latent) — four previously-separate findings — into one candidate invariant. Not assumed correct; A2.8J must verify it against implementation, tests, and counterfactual cases before treating it as validated.

## 3. Frozen Scope Boundaries (non-negotiable, carried directly from the mission brief)

Do NOT in this batch:
- wire recency into production;
- implement T2 bare-name detection;
- add session state, aliases, morphology/stemming, or semantic knowledge;
- modify D1RQ or any detector;
- repair Known C/D (partial-credit, plural/stemming, abbreviation normalization, `St`/`Street`, `Aug`/`August`) — these are coverage improvements, out of scope for a safety-only experiment;
- integrate RAR-SAFE into production;
- commit or push.

Stop condition: `VERIFICATION_READY`. Existing `rar_deterministic.py` must remain byte-identical and continue to back the production path and all existing tests.

## 4. Deliverables (Codex builds; file boundaries)

All new files — no existing production file is modified. Suggested paths (Codex may adjust names to repo convention, must not touch existing `rar_deterministic.py`/`rar_contracts.py`):

1. `uri_v1/turn/rar_safe_experimental.py` — the RAR-SAFE variant. Structural requirement: same cascade order and same evidence contract (`RARQuery`/`RAREvidence`/`RARCandidate`/`RARDeterministicAnchor`) as existing RAR, so `D1RQ → RAR-SAFE` is a drop-in substitution for `D1RQ → RAR (existing)` in the harness. Implements only the smallest change set needed to test S1/S2/S3 below — must not introduce new scoring systems, new metadata fields, or new detection.
2. `scripts/m35_a2_8j_rar_safe_battery.py` (or equivalent) — natural-boundary corpus runner against both existing RAR and RAR-SAFE, same 79-case corpus, same three C-conditions used in A2.8H/A2.8I.
3. `scripts/m35_a2_8j_counterfactual_battery.py` (or equivalent) — the three probe batteries (recency truthful-rank, T2 perfect-span diagnostic, exclusion/contrast), run against both variants, without touching D1RQ or production candidate construction. Reuses `build_candidate_pool(oracle_recency=True)` from `scripts/m35_rar_natural_boundary_harness.py` for the recency probe exactly as A2.8I's own P3/P4 probes did.
4. `docs/plans/M35_URIV1_A2_8J_TELEMETRY.json`, `..._AGGREGATES.json` — schema-compatible with A2.8H/A2.8I's telemetry (same field set, add `variant: "RAR"|"RAR-SAFE"`).
5. `docs/plans/M35_URIV1_A2_8J_EXECUTION_REPORT.md` — the mission brief's 17-point report (evidence recovered, hypothesis verification, exact invariant implemented, diff boundaries, before/after tables per §6/§7/§9/§10, existing-test results, resource impact, corpus hashes, reproducibility, unresolved mechanisms, files touched, next-experiment recommendation).

## 5. Invariant Design Guidance (for Codex — starting point, not prescriptive of final code)

Investigate before coding (per mission §2): for each level, what counts as "substantive evidence" under RAR's own existing semantics — i.e. do not invent a new scoring system. Two candidate mechanical hooks already exist in the codebase to build from:

- **S1 (zero-substantive-evidence binding)**: Level 4b's 1-match branch (526-558) already has a "substantive-token safety check" per the cascade table above — investigate why it doesn't block `NB-B-05:r1`@C2 (query `"that in an email"` has zero substantive tokens after `"in"` NP-crossing) and whether tightening that existing check (not adding a new one) closes it.
- **S2 (commit against contradictory lexical evidence)**: requires Level 5 to consult Level 6's absent-entity/lexical-overlap evidence *before* committing, without reordering the cascade (mission explicitly forbids moving Level 6 earlier) and without special-casing recency. Likely shape: extract Level 6's absent-entity check as a reusable pre-commit gate callable from Level 5 (and any other commit point), rather than duplicating logic.
- **S3 (contrast/exclusion must demonstrate actual exclusion)**: Level 4a's contrast shortcut (486-496) currently checks pool size == 1 without checking that the elimination step actually removed a candidate. Require the elimination step to report whether it eliminated ≥1 candidate; gate the shortcut on that, not on pool size alone. Must not special-case `"the other"` string literal.

## 6. Acceptance Criteria (defined before Codex begins, per Verification-First standard)

A2.8J's implementation is complete and ready for Claude's final audit when ALL of the following hold, with evidence in the execution report:

1. Existing `rar_deterministic.py`, `rar_contracts.py`, and D1RQ (`scripts/m35_a2_8h_detector_d1rq.py`) are byte-unmodified (diff against HEAD).
2. RAR-SAFE variant exists as isolated code; existing RAR remains reachable and behaviorally unchanged.
3. All existing RAR tests pass unchanged against existing RAR (regression proof): `test_m35_uriv1_a2_5_deterministic_rar.py`, `test_m35_uriv1_a2_5_rar_adversarial_safety.py`, `test_m35_uriv1_a2_5_candidate_invention_fix.py`, `test_m35_uriv1_a2_5_rar_contracts.py`, `test_m35_uriv1_a2_5_rar_stage4_refinements.py`. Any test that conflicts with the new invariant is flagged, not silently edited — the report states whether the invariant, the test, or the contract is wrong, and escalates if genuinely architectural (per mission §13).
4. Full 79-case natural-boundary corpus run under both existing RAR and RAR-SAFE, all three C-conditions, with per-level `correct before → correct after → unsafe before → unsafe after → new abstentions` reported (mission §9).
5. Counterfactual batteries executed for all three named hazards (recency, T2 perfect-span, exclusion/`NB-H-06`), each reporting before/after ICB counts, without wiring recency, T2 detection, or D1RQ changes into production.
6. Every `RESOLVED` outcome under RAR-SAFE answers the 7 mechanical questions in mission §10 (positive evidence / rejected competitors / contradictory evidence present / consumed / singleton-only / metadata-only / would Level 6 have contradicted).
7. Every coverage loss (correct resolution → abstention) is individually audited and disclosed, not hidden in aggregates (mission §6, §15).
8. Measurements report uses `UNMEASURED` where genuinely not measured; no fabricated figures (mission §14).
9. Report answers all 7 next-step questions in mission §17, including an explicit recommendation on whether RAR is now safe enough to qualify recency wiring and/or T2 detection.
10. No commit, no push. Report ends at `VERIFICATION_READY`.

## 7. Handoff

Antigravity routes deliverable set (§4) to Codex per AO-4 standing roles (complex/multi-file/production-adjacent work → Codex, not Gemma). On Codex's `VERIFICATION_READY` report, Claude performs the independent final audit against §6 acceptance criteria (tracing actual code and telemetry, not trusting the report), then determines VERIFIED/NOT VERIFIED and any bounded fix. No release action applies to this batch (no commit/push authorized in scope).

## 8. History Log

- 2026-09-24: Claude drafted this plan from independently recovered repository evidence (Explore agent, 28 tool uses, evidence dossier covering A2.8C-A2.8I, rar_deterministic.py, rar_contracts.py, RAR test suite, candidate construction). Self-accepted per ORCHESTRATION.md §1.5 standing auto-approval (routine engineering experiment; no core-architecture/security-model change). Handed to Antigravity for Codex routing. Claude did not implement any part of the deliverable set, per AO-4 role boundary (substantial implementation → Codex, not Claude).
