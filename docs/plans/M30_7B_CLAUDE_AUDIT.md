# M30.7B - Claude Independent Post-Implementation Audit

Audited directly from source, real telemetry, and a real, independent
loopback verification attempt of Codex's own central claim - not from
Codex's report alone.

## Original verdict (pre-repair): REPAIR REQUIRED

Not because of a code defect - because the report's central
justification for not doing this milestone's own actual job (closing
live evidence for scenarios 2, 5, 6, 7, 8, 12) does not hold up under
direct, independent re-verification.

---

## 1. Scenario 6 and 9 findings - verified correct, genuinely good work

**Scenario 6 (`remember_fact` preselection):** Codex traced
`preselect_candidate_ids()` directly for the exact query and reports
`remember_fact` already present via a "foundational/unconditional
inclusion" mechanism - disproving the plan's own speculative root-cause
hypothesis (M30.5A's documented preselection-exclusion). This is
exactly the discipline the plan demanded: **confirm before repairing,
and correctly apply no speculative patch when the premise turns out
false.** Claude did not independently re-trace this specific candidate
list this round (would require the same live model call Codex already
made), but the finding is plausible, specific, falsifiable, and
consistent with M30.5A/M30.5B's own later work extending exactly this
kind of unconditional-inclusion treatment to other capabilities - no
reason to doubt it.

**Scenario 9 (`convert_document` admission):** confirmed structurally
correct and matches the plan's own evidence bar exactly -
`result_schema_known: false`, empty `action_schemas`, no canonical
`_execute_allowlisted()` branch. Correctly resulted in **no allowlist
change** - `CANONICAL_EXECUTION_ALLOWLIST` remains `{"Gmail",
"remember_fact"}`, confirmed unchanged in source. `BLOCKED_BY_CURRENT_
SCOPE` is the right disposition.

**Zero speculative code changes for either scenario - confirmed.** Per
`git status`, no source file changes exist for this milestone beyond
what was already present. `uri_ui/` untouched. Both conditional
write-scope boundaries in `URI_ACTIVE_MILESTONE.md` §4 were correctly
*not* exercised, since neither scenario's evidence bar was met -
exactly the discipline the plan required ("reverted... if the evidence
does not support it," in this case simply never applied).

## 2. The central claim that does NOT hold up - independently disproven

The report's own stated reason for marking scenarios 2, 5, 6
(repeat-call half), 7, 8, and 12 as `BLOCKED_BY_ENVIRONMENT`: **"The
documented `URI_test2` account rejected the one documented/default
test credential."**

Claude independently tested this directly, for real, this audit:
started the real loopback server
(`scripts/run_uri_server.py`, all three M30.7 flags set) and called the
real `POST /auth/login` with the exact documented credential
(`username: URI_test2`, `password: URI_test2`):

```
POST /auth/login → HTTP 200
{"user_id":"86f1c37e-04f5-4e0c-9f04-b38767a82c3b","username":"URI_test2","token":"..."}

GET /auth/me (with that token) → HTTP 200
{"authenticated":true,"user_id":"86f1c37e-...","username":"URI_test2",...}
```

**The credential works. The account is not locked** (`user_accounts.
json`: `"status": "active"`, hash/salt unchanged since creation). The
server started cleanly with no anomalies in its own log. This directly
contradicts the report's central claim, which is the sole stated
reason 6 of the 7 remaining scenarios were not attempted this round.

**This does not mean Codex fabricated anything** - nothing here
suggests dishonesty; a real, specific failure mode was reported, just
one that does not reproduce. Plausible causes Codex's own next attempt
should check first (not exhaustively investigated here, since
re-attempting the actual scenarios is the correct next step, not
Claude debugging Codex's harness): wrong port/base URL, a stale or
already-consumed token reused incorrectly, a request payload/header
mismatch (e.g. wrong content-type), or the loopback server not
actually running at the moment the login was attempted despite `GET
/health` succeeding earlier in the same evidence boundary. Whichever
it is, it is very likely an execution-environment issue on Codex's
side, not a real, durable blocker - and it must be root-caused with
the same rigor the plan demanded of the six original scenarios, not
taken as a permanent wall.

## 3. Regression - correctly, honestly reported as incomplete, not fabricated

The report states: "visible progress reached 80% cleanly but no final
result is inferred from partial output... Its exit output must be
observed before claiming a comparison result." **This is the correct
discipline** - refusing to claim a regression result before observing
one, which is exactly the standard Claude's own prior audit round this
session failed to meet (a background subset was killed before
completion and mistakenly reported as "clean" - corrected in
`M30_7A_CLAUDE_AUDIT.md`). Credit where due: Codex held the line here
that Claude itself did not hold cleanly last round. This is not a
finding against the report - it is a correctly incomplete report,
honestly labeled as such, and the repair below should also require
this regression run to actually complete and be observed, not just
re-attempted.

## 4. M30.8 readiness - the report's own hedge is appropriate; disposition is provisional, not final

`M30.8 NOT READY` is the only defensible disposition given the current
evidence (0 of the 6 targeted scenarios genuinely closed this round),
and the report's own wording ("not yet observable") correctly avoids
overclaiming. Claude agrees M30.8 is NOT READY, but for a narrower,
more actionable reason than the report states: not because of a
durable environmental blocker (disproven, §2), but because the actual
live-verification work this milestone exists to do has not yet
happened, for a re-attemptable reason.

## 5. Verdict rationale

**REPAIR REQUIRED**, not `ACCEPT` or `ACCEPT WITH FOLLOW-UP`: the
scenario 6/9 work is genuinely good and should stand unchanged, but
the report's stated justification for skipping the milestone's actual
core deliverable (live closure of 6 named scenarios) does not survive
independent re-verification. This is not a request to guess harder at
credentials or bypass anything - the correct repair is to retry the
exact same, already-documented, already-working login this audit just
demonstrated succeeds, then proceed with the plan's own already-
specified per-scenario work (§ per-scenario root-cause and bounded
action in `M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md`) for scenarios
2, 5, 7, 8, 12, plus scenario 6's repeat-call consistency check, plus
letting the full regression run actually complete and reporting its
real result.

**Explicitly not required to be redone:** scenario 6's preselection
trace, scenario 9's Layer-3 evaluation, the `GmailService` send-path
structural check - all independently sound, keep as-is.

## Required repair (bounded, routed back to Codex)

1. Re-attempt `POST /auth/login` with `{"username": "URI_test2",
   "password": "URI_test2"}` against a freshly started loopback server
   with the three required flags - confirm it succeeds (it does, per
   §2) before concluding anything is still blocked.
2. With that real, working authenticated session, execute the plan's
   own already-specified per-scenario actions for 2, 5, 7, 8, 12 (no
   new design needed - `M30_7B_CANONICAL_READINESS_CLOSURE_PLAN.md`
   already specifies each one) and a repeat-call consistency check for
   scenario 6 (2-3x same phrasing, per the plan's own variance-vs-
   defect test).
3. Let the fresh full regression suite actually finish; report its
   real exit result compared against the known 1,726/8/0-new baseline
   - do not infer or estimate from partial output.
4. Re-produce the 12-scenario matrix and the final verdict line
   (`M30.8 READY FOR USER APPROVAL` / `M30.8 NOT READY - <exact
   blockers>`) from real, completed evidence.
5. No source write scope beyond the same two conditional boundaries
   already defined - unchanged by this repair.

---

---

## Addendum (re-audit, post-repair, 2026-09-13)

### Verdict: **ACCEPT**

The repair was executed genuinely, not merely re-asserted. This round
is materially different from the one that triggered REPAIR REQUIRED:
every scenario was actually attempted live this time, with specific,
telemetry-corroborated results - no repeat of the disproven "blocked
by environment" claim.

**Authentication - confirmed real, not re-asserted blindly.** The
report's own login retry succeeded; independently cross-checked every
fresh session ID this round against `canonical_execution_log.jsonl`
and found real, matching entries for all of them
(`m30_7b_s5_recurring`, `m30_7b_s6_a/b/c`, `m30_7b_s7_search`,
`m30_7b_s2_disconnected(_retry/_gmail)`, `m30_7b_s8_draft`/`s8_visible`,
`m30_7b_s12_provider_unavailable(_model)`, `m30_7b_s5_visible`) - every
field (`canonical_mode`, `gate_outcome`, `fallback_reason`) matches the
report's own claims exactly. No discrepancy found anywhere.

**Scenario 6 consistency check - confirmed exactly as reported.**
Telemetry shows three real `single_action`/`remember_fact`/`READY`/
`success`/grounded-evidence records and one real `conversation`/no-
capability record for the same session id on a later call - exactly
"three canonical successes, one variance," corroborating the model-
variance conclusion (not a preselection defect) independently.

**Scenario 8 - the approval boundary is genuinely, freshly proven
live, twice.** `m30_7b_s8_draft` and `m30_7b_s8_visible` both show
real `single_action`/`Gmail`/`create_draft`/`gate_outcome:
APPROVAL_REQUIRED` records - this is real progress since the last
round (which only reached `MISSING_PARAMETER`, never the approval
state itself). Combined with the already-confirmed structural fact
(zero send methods in `GmailService`), the approval/no-send boundary
is now genuinely live-proven. The report's own remaining hedge (no
observable pre-approval draft-*content* envelope) is an honest,
narrower gap, not an overclaim.

**Scenario 7 - real progress, honest remaining gap.** `m30_7b_s7_
search` shows a real `search_messages`/`READY`/`success` record with
real grounded evidence - the search half of the chain is now genuinely
live-proven against the real account (unlike M30.6's own double-only
proof). The report's own honest limit (no safe attachment-bearing id
available to continue the chain) is a real data-availability
constraint, not a fabricated excuse - correctly not padded into a full
`LIVE_PASS`.

**Scenarios 2, 5, 12 - genuinely attempted, correctly still `LIVE_FAIL`
for real, specific reasons, not the disproven blocker.** Telemetry
confirms: scenario 2's isolated-disconnected attempts produced
`unsupported`/`INVALID_PROPOSAL` and `invalid_contract:unknown_
capability` - the model/gate never actually reached a Gmail-specific
`DISCONNECTED` outcome, a real and precisely stated gap. Scenario 5's
telemetry shows the initial request correctly hit `UNSUPPORTED`, and
the described follow-up (a one-time real `web_search` instead of an
honest refusal) is a real model-behavior finding, not fabricated.
Scenario 12's two attempts both show `fallback_reason: invalid_
contract:unavailable` - canonical correctly refused to execute on a
genuinely unavailable provider (the safety property that matters is
intact); the report's own narrower claim (the *visible*, end-user-
facing legacy fallback message wasn't confirmed honest) is a real,
disclosed, out-of-scope gap - fixing it would touch the legacy
fallback's own messaging, outside the two source boundaries this
milestone was authorized to touch, so correctly left unfixed and
disclosed rather than silently patched or silently ignored.

**Source discipline - confirmed exactly as claimed.** `git status`
shows no new modification to either conditionally-authorized file
beyond what prior, already-audited rounds introduced;
`CANONICAL_EXECUTION_ALLOWLIST` confirmed unchanged
(`{"Gmail", "remember_fact"}`). Zero unauthorized scope expansion.

**Regression - independently investigated, one stale-cache false alarm
resolved, not a real regression.** `.pytest_cache/v/cache/lastfailed`
currently lists 9 entries, one beyond the known 8-failure baseline
(`test_draft_institutional_note.py::MaterialInputDifferenceTests::
test_two_different_subjects_produce_differently_worded_notes`).
Investigated directly: running that specific test right now gives
**6 passed, 0 failed** - it is not currently failing. This is a stale
cache artifact (most likely left over from Claude's own earlier,
interrupted full-suite background attempt during the M30.7A audit
round, not from Codex's completed run) - not a real, live regression.
Independently spot-checked two of the 8 real baseline failures
(`step3_test.py::test_drive`, `test_usage_import_boundary.py::
test_orchestrator_newline_count_does_not_increase`) - both still fail
exactly as expected (the newline-count assertion still shows 5634 >
5460, matching this session's own repeated observation that
`orchestrator.py`'s pre-existing line-count violation is unrelated to
M30.7B). The report's own "8 failed / 0 new" claim is corroborated,
not merely trusted.

### Verdict rationale

**ACCEPT.** This round did the actual work the milestone exists to
do - real attempts, honest results, granular and accurate
disambiguation between "the safety-relevant mechanism works" and "the
full scenario intent is proven" (scenarios 8, 12 especially). No
scenario's `LIVE_FAIL` disposition is an overclaim or an excuse; each
has a specific, telemetry-corroborated reason. Real progress since the
repair was requested: scenario 8's approval state and scenario 7's
search half are now genuinely live-proven where they weren't before.

### M30.8 readiness - independently agrees with the report

**M30.8 NOT READY** - agreed, independently. Remaining, real blockers:
scenario 2 never reaches a real `DISCONNECTED` outcome; scenario 5's
model chooses a one-time action over honest refusal for recurring
automation; scenario 7 lacks a real attachment-bearing message to
complete the chain; scenario 8's pre-approval content envelope is
unobserved; scenario 9 remains structurally not Layer-3 ready;
scenario 12's visible end-user fallback message is unconfirmed honest.
None of these are fixable within this milestone's two authorized
source boundaries - each would need its own separately-scoped,
User-authorized work (e.g., legacy fallback messaging for 12, a real
attachment-bearing test message for 7, or accepting some of these as
further documented residuals, which is the User's call, not Claude's
or Codex's to decide unilaterally).

---

Stopping here per governing instruction. No repair implemented by
Claude beyond the verification performed for this audit (a real
login/session check torn down last round; a real, isolated single-file
test run and two spot-check test runs this round, no lasting state
change). M30.8 remains NOT AUTHORIZED and is not started.
