# M30.7B State - Canonical Readiness Closure

**Plan:** `docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md`

STATE: LIVE_VERIFIED + CLAUDE ACCEPT - M30.7B's own scope (root-cause,
one bounded decision each for scenarios 6/9, and genuine live attempts
for 2/5/7/8/12) is complete, honest, and independently verified.
Resulting finding, independently confirmed: M30.8 NOT READY - real,
specific, per-scenario blockers remain, none fixable within this
milestone's two authorized source boundaries.

## Governance

Scope: root-cause and, only where confirmed necessary, bind a bounded
fix for the 6 scenarios M30.7A left `LIVE_FAIL` (2, 5, 6, 7, 8, 12);
resolve scenario 9's per-capability admission decision for
`convert_document`; rerun the full 12-scenario matrix; fresh full
regression. Scenario 4 remains `DOCUMENTED_ACCEPTED_RESIDUAL`, not
reopened. No global canonical-default flip, no M30.8 implementation.

## History Log

- 2026-09-13: Codex completed the bounded repair. Fresh `URI_test2` login and
  `/auth/me` authenticated. Scenario 6 had three canonical successes plus one
  variance call; Scenario 8 reached `APPROVAL_REQUIRED`; Scenario 7 ran real
  Gmail search. Scenario 2 did not reach `DISCONNECTED`, Scenario 5's
  follow-up performed a one-time search rather than refusing recurrence,
  Scenario 7 could not safely continue to attachment data, and Scenario 12
  did not yield an honest visible provider-unavailable message. No source
  changes were authorized or made. Full `pytest -q` completed; the eight
  established failures were re-listed by `pytest -q --last-failed`. See
  `M30_7B_CANONICAL_READINESS_CLOSURE_REPORT.md`.

- 2026-09-13: Codex completed the M30.7B root-cause trace without source
  changes. Exact Scenario 6 preselection already includes `remember_fact` via
  foundational inclusion, so no duplicate conditional patch was justified.
  Scenario 9 remains non-admissible: no result schema/action schemas and no
  canonical executor branch. The loopback server/provider were healthy, but
  the documented live account could not authenticate with the one
  documented/default credential; no guessing, token inspection, fake
  principal, or account creation was used. See
  `M30_7B_CANONICAL_READINESS_CLOSURE_REPORT.md`.

- 2026-09-13: M30.7A closed `LIVE_VERIFIED + CLAUDE ACCEPT` with
  independently-confirmed disposition `M30.8 NOT READY` - 4 scenarios
  `LIVE_PASS` (1, 3, 10, 11), 1 `DOCUMENTED_ACCEPTED_RESIDUAL` (4), 1
  `BLOCKED_BY_CURRENT_SCOPE` (9), 6 `LIVE_FAIL` (2, 5, 6, 7, 8, 12).
- 2026-09-13: User directly requested Milestone M30.7B - Canonical
  Readiness Closure, to close the remaining 6 `LIVE_FAIL` scenarios and
  resolve scenario 9's admission decision. Claude produced
  `M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md`: for each of the 6
  scenarios, a root-cause classification grounded in direct evidence
  (M30.7A's own report/telemetry, cross-referenced against
  `M30_5A_DECISION_QUALITY_REMEDIATION_REPORT.md`'s already-documented
  preselection-exclusion finding for scenario 6's exact phrasing) -
  five of six classified as test-execution/test-completeness gaps
  requiring no code change, only a properly executed live attempt;
  scenario 6 given one conditional, narrowly-scoped candidate fix
  (extend the existing `active_pointer.capability_id` unconditional-
  inclusion pattern to `remember_fact`) to be applied only if Codex's
  own re-trace confirms the preselection-exclusion cause over the
  alternative (benign model-sampling variance). Scenario 9 framed as a
  real, bounded, human-reviewed single-capability admission decision
  (the same class of action M30.6 already took for `Gmail`/
  `remember_fact`), not a global cutover - conditional on real Layer 3
  evidence, reverted if evidence does not support it. Marked ACCEPTED
  under the standing auto-approval rule. Handed back to Antigravity
  (`docs/governance/URI_AGENT_RELAY.md`) for routing to Codex. No
  production code written by Claude.

- 2026-09-13: Claude independently audited M30.7B. Confirmed scenario
  6's preselection trace and scenario 9's Layer-3 evaluation are sound
  (zero speculative code changes, both write-scope conditions correctly
  left unexercised). **Independently disproved the report's central
  claim** that the documented `URI_test2` credential was rejected:
  started a real loopback server with the three required flags and
  successfully logged in (`POST /auth/login` → HTTP 200) and
  authenticated (`GET /auth/me` → HTTP 200) with the exact documented
  credential, immediately torn down afterward (no lasting state
  change). The account is `"status": "active"`, hash/salt unchanged.
  Verdict: **REPAIR REQUIRED** (`docs/plans/M30_7B_CLAUDE_AUDIT.md`) -
  not a code defect, but the milestone's actual core deliverable (live
  closure of scenarios 2, 5, 7, 8, 12, plus a repeat-call consistency
  check for 6) was not attempted this round because of a blocker that
  does not reproduce. Routed back to Codex: retry the same login (it
  works), complete the plan's own already-specified per-scenario work,
  let the fresh full regression suite actually finish and report its
  real result, then re-produce the 12-scenario matrix and final verdict
  line. No new source write scope - same two conditional boundaries.
  M30.8 remains NOT AUTHORIZED.

- 2026-09-13: Claude independently re-audited M30.7B's repair. Cross-
  checked every fresh session ID this round against `canonical_
  execution_log.jsonl` field-by-field - every claim matched exactly
  (real login retry, scenario 6's 3-success/1-variance pattern,
  scenario 8 reaching real `APPROVAL_REQUIRED` twice - genuine progress
  since the last round, scenario 7's real `search_messages` success,
  scenarios 2/5/12's specific real failure telemetry). Confirmed zero
  unauthorized source changes and the allowlist unchanged. Investigated
  a `.pytest_cache/lastfailed` discrepancy (9 entries vs. the known 8)
  directly - the 9th (`test_draft_institutional_note.py`) is a stale
  cache artifact, not a real failure (independently re-ran it: 6
  passed, 0 failed); spot-checked two real baseline failures, both
  still genuinely fail as expected. Verdict: **ACCEPT**
  (`docs/plans/M30_7B_CLAUDE_AUDIT.md` addendum) - this round did the
  actual work honestly, with specific, telemetry-corroborated reasons
  for every remaining `LIVE_FAIL`, none an overclaim or excuse.
  Independently agrees: **M30.8 NOT READY** - remaining blockers
  (scenarios 2, 5, 7, 8's content envelope, 9, 12's visible fallback)
  are real and not fixable within this milestone's two authorized
  source boundaries; each would need its own separately-scoped,
  User-authorized follow-up. M30.8 remains NOT AUTHORIZED - the User's
  decision. No production code written by Claude.

## Release gate

Per the 2026-09-12 live-verification-gate revision: Codex implements/
verifies against this plan; Claude independently re-audits the
resulting report against real telemetry/session-state artifacts before
either `M30.8 READY FOR USER APPROVAL` or `M30.8 NOT READY` is treated
as final - exactly as for every prior milestone this session (M30.6A,
M30.7, M30.7A). Claude does not perform live verification itself and
does not simulate Antigravity or Codex. M30.8 authorization remains
the User's own, non-delegable decision regardless of this milestone's
outcome.
