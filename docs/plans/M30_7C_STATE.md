# M30.7C State - Canonical Readiness Evidence Closure (Final Pass)

**Plan:** `docs/plans/M30_7C_READINESS_EVIDENCE_CLOSURE_PLAN.md`

STATE: LIVE_VERIFICATION_COMPLETE (2026-09-14) - resumed directly by
Claude per explicit User instruction after M30-PFC's closure. See the
new 2026-09-14 history entry below and `docs/plans/M30_7C_READINESS_
EVIDENCE_CLOSURE_REPORT.md` for full evidence. Prior state (below) is
preserved for history.

PRIOR STATE: STOPPED_FOR_SCOPE_APPROVAL - Claude independently REPRODUCED
Scenario 12's defect live (not merely trusted the report) and confirms
it is real: a totally-unreachable-reasoning turn causes an unrelated
statement to be executed and persisted via `remember_fact`, falsely
tagged `consent: "user_provided"`. Zero model calls succeeded during
the reproduction (confirmed via real usage-log records) - this is a
deterministic code defect, not model variance. Five candidate
mechanisms were ruled out by direct source inspection; the exact line
was not pinpointed (would need debug instrumentation, itself a source
change requiring its own approval). Per the binding protocol, no
source repair, Scenario 7 attempt, or full regression run may proceed
without a new explicit scope decision. See
`docs/plans/M30_7C_CLAUDE_AUDIT.md`.

## Governance

Scope: mandatory real-evidence closure for scenarios 2 (corrected
DISCONNECTED fixture), 8 (approval content-envelope capture), 12
(visible fallback capture); best-effort for scenario 7 (real chain, no
fabrication). Scenarios 4, 5, 9 explicitly not reopened. No source
changes unless a real defect is found, and even then only after a new,
explicit approval - never auto-repaired. No M30.8 implementation, no
global cutover.

## History Log

- 2026-09-13: `docs/plans/M30_8_BLOCKER_DISPOSITION_PLAN.md` produced
  at User request - read-only, per-scenario root-cause classification
  for the 6 remaining M30.8 readiness gaps (2, 5, 7, 8, 9, 12) -
  CLOSE NOW (2, 7, 8, 12), DEFER (9), ACCEPT AS LIMITATION (5).
- 2026-09-13: User approved a bounded evidence-closure pass exactly
  matching the disposition plan's own CLOSE-NOW/BEST-EFFORT findings,
  explicitly excluding 4/5/9 from reopening and requiring a stop-and-
  ask (not auto-repair) if any real defect is found. Claude produced
  `M30_7C_READINESS_EVIDENCE_CLOSURE_PLAN.md`: precise fixture guidance
  for scenario 2 (an isolated, invalid-but-present token - not the
  empty-credentials-dir shape that caused the prior attempt's own
  failure, per the disposition plan's own root-cause finding),
  evidence-capture requirements for scenarios 8/12 (real response
  body, not telemetry alone), and the binding defect-handling protocol
  restated exactly. Marked ACCEPTED under the standing auto-approval
  rule - the User had already fully specified scope directly. Handed
  back to Antigravity (`docs/governance/URI_AGENT_RELAY.md`) for
  routing to Codex. No production code written by Claude.

- 2026-09-13: Codex executed Scenario 2's corrected fixture exactly as
  specified (pre-check independently confirmed the fixture correctly
  produces `{"connected": false, "reason": "invalid_token"}` and
  `missing_preconditions: ["gmail_connected"]`), but the live `/ask`
  call fell back with `invalid_contract:unknown_capability` -
  `gate_outcome: null` - never reaching Gate 1's `DISCONNECTED` branch
  at all. Per the binding protocol, Codex stopped immediately, applied
  no speculative fix, cleanly tore down the isolated server/fixture,
  and returned for a scope decision.

  Claude traced the exact mechanism: `decision_engine.py`'s contract
  validation (`known_ids = capability_directory.summaries()`) rejects
  a proposed capability not in that set, **before** `evaluate_gates()`
  ever runs. Confirmed `summaries()` is deliberately availability-blind
  (per its own docstring) - the disconnected fixture does not, by
  design, remove Gmail from `known_ids`, ruling out the most obvious
  guess. The real candidate: `_suppressed_legacy_ids()` (M30.5A's
  Gmail-overlap policy) deliberately excludes the legacy `gmail_search`
  alias from `known_ids` so only `Gmail` is visible - if the model
  proposed the legacy name instead of the canonical one, that alone
  explains the rejection, with no code defect. The raw model text that
  would confirm which name was proposed
  (`DecisionOutcome.raw_text`) is not persisted to telemetry
  (privacy-safe by design) and was not separately captured this round.

  **Verdict: not a confirmed defect - one more diagnostic live attempt
  required**, capturing the raw proposed capability name this time.
  This is read-only evidence gathering on an already-approved scenario,
  not a source change or scope expansion - no new User approval is
  needed for it. Full findings in `docs/plans/M30_7C_CLAUDE_AUDIT.md`.
  Scenarios 7, 8, 12, and the regression pass were not reached this
  round (Codex correctly stopped before them) - **no 12-scenario
  matrix or M30.8 readiness conclusion can be produced yet**. No
  production code written or modified by Claude.

- 2026-09-13: Codex executed the corrected Scenario 2 fixture and
  fresh Scenario 8/12 attempts. Scenario 12 (controlled provider
  failure) exposed a real visible-fallback defect: canonical
  telemetry correctly recorded `invalid_contract:unavailable`, but the
  actual `/ask` response returned success and saved an unrelated
  weather question to memory via `remember_fact`
  (`memory_id: 7d166b15-...`). Codex stopped immediately per the
  binding protocol, applied no fix, cleaned up, and returned for a
  scope decision.

  Claude independently reproduced the defect live (own fresh server,
  own `/ask` call, own `memory_id: 0f93646a-...`) rather than trust
  the report alone - **confirmed real**. Real usage-log records for
  the reproduction show every model role (`semantic_interpretation`,
  `reasoning` x2, `drafting` x2) as `outcome: unreachable` - zero
  model calls succeeded, proving this is a deterministic code defect,
  not model hallucination or ordinary model-quality variance. Directly
  tested and ruled out, with source-level evidence:
  `capability_planner.py`'s disclosure scoring (empirically returns
  `planning_required` for the exact degraded input), `provider_
  semantic_interpreter.py`'s disclosure regex (no match, and
  structurally unreachable on total-unavailability anyway),
  `_recover_capability_mentions()` (no matching keys in a `reasoning_
  failed` dict), `MultiActionDispatch.dispatch()` (its registry only
  ever contains Gmail, never `remember_fact`), and `skill_memory`'s
  learned-skill path (advisory-only in current code, requires a
  successful model read). The most likely remaining candidate,
  `_run_acceptance_retention_step`/`_model_retention_candidate`, was
  not confirmed or ruled out via static reading alone - stated
  explicitly as unverified rather than guessed.

  Removed the two spurious, falsely-consent-tagged memory entries this
  investigation and Codex's own reproduction created (real-data
  correction, not a source change - transparently disclosed). Test
  server cleanly shut down.

  Also audited this round's fresh Scenario 2 (`INVALID_PROPOSAL` again
  - consistent with ongoing model-naming variance already diagnosed
  last round, not a new defect) and Scenario 8 (model selected a
  different, legitimate draft capability - `draft_institutional_note`
  - rather than `Gmail`/`create_draft`; structural no-send proof
  re-confirmed; the specific canonical evidence remains uncaptured).

  **Recommendation: treat the Scenario 12 defect as a separate,
  dedicated, User-approved investigation-and-repair milestone** given
  its real privacy/consent severity - do not fold it into M30.7C's
  own narrower evidence-closure mandate. M30.7C's own remaining scope
  (fresh Scenario 2/8 canonical evidence, best-effort Scenario 7, the
  regression pass) can proceed independently of that decision. Full
  findings in `docs/plans/M30_7C_CLAUDE_AUDIT.md`. No production
  source code modified by Claude.

- 2026-09-14: User closed M30-PFC as ACCEPTED and directly instructed
  Claude to resume M30.7C's remaining scope with focused live
  verification, performed by Claude directly: Scenario 2 (Gmail
  DISCONNECTED), Scenario 7 (real search→read→attachment chain,
  genuine test-account data only, no fabrication), Scenario 8 (draft
  approval content-envelope), Scenario 12 (provider-failure fallback
  confirmation post-M30-PFC), plus one focused Scenario 6 consistency
  check. Scenarios 4, 5, 9 not reopened.

  **Scenario 2:** 4 live attempts (isolated invalid-token fixture,
  varying wording) all failed to reach a clean canonical `DISCONNECTED`
  gate outcome - but this round found and disclosed the actual reason,
  superseding the prior "fixture design gap" hypothesis: the model
  correctly recognizes the genuine disconnection and reports it via
  `mode: "unsupported"`, which the Decision Engine's contract
  validation rejects as presumptively false (`capability_directory.
  summaries()` is deliberately availability-blind) *before* Gate 1's
  own availability check ever runs. The legacy fallback path
  independently and correctly detects and reports the disconnection
  today (confirmed via `old_path.tool_name: "gmail_search"` executing
  and returning an honest auth-failure message) - so current end-to-end
  behavior is safe, but canonical Gate 1's `DISCONNECTED` branch may be
  structurally unreachable for this exact, correct model behavior. Not
  repaired (binding protocol) - reported for User decision. Directly
  relevant to the User's own new "M30.8 as Canonical Cutover + Legacy
  Retirement" direction (see `M30_8_BLOCKER_DISPOSITION_PLAN.md`'s
  updated Future Direction Notes).

  **Scenario 6:** one fresh check, canonical `remember_fact` selection
  confirmed stable post-M30-PFC (no regression from the new Scenario 2
  finding bleeding into other capabilities).

  **Scenario 7:** upgraded from `LIVE_FAIL` to fully real mechanism
  proof - `search_messages` and `read_message` both independently
  proven against genuine attachment-bearing messages in the connected
  test account (real `Hall Ticket.pdf` attachments, real message
  bodies). 7 total live attempts at a fully autonomous NL-narrated
  grounded answer; one succeeded at the search step for real, none
  produced the final narrated answer in one turn (model asked
  clarifying questions or misrouted instead) - genuine model variance,
  not fabricated, not a code defect. Reported as a real, honest,
  non-blocking limitation per the disposition plan's own escape valve.

  **Scenario 8:** closed - fresh live call captured full canonical
  `Gmail`/`create_draft`/`APPROVAL_REQUIRED` evidence including the
  real HTTP response body's content envelope (to/subject/body entities,
  action_id, risk, description) - the exact gap the disposition plan
  identified.

  **Scenario 12:** closed - fresh post-M30-PFC live re-run confirms the
  honest, deterministic visible fallback message, zero learned-skill/
  remember_fact execution, zero new memory entries, and (new this
  round) that the legacy path itself (not just the canonical shadow
  layer) now correctly fails closed too.

  Rebuilt the full 12-scenario matrix (`M30_7C_READINESS_EVIDENCE_
  CLOSURE_REPORT.md`) and ran one final full regression suite to a
  real terminal result. See that report and `URI_ACTIVE_MILESTONE.md`
  for the exact final readiness conclusion line. No production source
  code modified - only `uri_workspace/m30_7c_evidence_capture.py` (a
  workspace evidence harness) was extended, consistent with this
  milestone's write scope.

## Release gate

Per the 2026-09-12 live-verification-gate revision: Codex implements/
verifies against this plan; Claude independently re-audits the
resulting report against real telemetry/session-state/response-body
artifacts before either `M30.8 READY FOR USER APPROVAL` or `M30.8 NOT
READY` is treated as final - exactly as for every prior milestone this
session. If a real defect is found, Codex stops and reports it rather
than repairing automatically; Claude does not authorize any repair
under this milestone's own scope. M30.8 authorization remains the
User's own, non-delegable decision regardless of this milestone's
outcome.
