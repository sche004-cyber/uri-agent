# M30.7B - Canonical Readiness Closure (Plan)

STATE: ACCEPTED (plan only) - implementation NOT yet performed. Claude
(Architect/Planner) output per the standing AO-4 development cycle, at
the User's explicit direct request. Produced from direct inspection of
`docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_REPORT.md`,
`docs/plans/M30_7A_CLAUDE_AUDIT.md`, real telemetry
(`canonical_execution_log.jsonl`), and cross-referenced against
`M30_4_DECISION_QUALITY_ANALYSIS.md`/`M30_5A_DECISION_QUALITY_
REMEDIATION_REPORT.md`/`M30_5B_CANDIDATE_RECALL_MULTI_ACTION_REPORT.md`
for scenario 6's own documented history. Sibling state file:
`docs/plans/M30_7B_STATE.md`.

Scope authority: exactly the User's own verbatim request - close the
6 still-`LIVE_FAIL` scenarios (2, 5, 6, 7, 8, 12) and resolve
scenario 9's admission decision, under the current allowlist-scoped
system. No global canonical-default flip, no M30.8 implementation.

---

## Governing discipline (binding on Codex)

**Root-cause before repair, for every scenario, no exceptions.** Per
the User's own instruction and this session's own established
practice (M30.6A's "trace first, then choose" pattern, M30.7's v3/v4
corrections): no scenario may receive a code change until Codex has
established, from direct evidence, *why* it failed. Several scenarios
below already have a strong root-cause candidate from this session's
own prior evidence - Codex must **confirm, not assume**, each one
before acting on it.

**No fake-double evidence counts as `LIVE_PASS`** - identical bar to
M30.7A: real `/ask`, real authenticated principal, real external
service where the scenario names one.

**Preserve M30.7's accepted residual.** Scenario 4 stays
`DOCUMENTED_ACCEPTED_RESIDUAL`, citing `M30_7_STATE.md`/
`M30_7_CLAUDE_AUDIT.md` - do not re-open it, do not re-attempt it live,
regardless of how this milestone's other scenarios resolve.

---

## Per-scenario root-cause hypothesis and bounded action

### Scenario 2 - Gmail disconnected → `DISCONNECTED`

**M30.7A's own finding:** "Token invalidation/restart not completed;
stale evidence does not close it" - the live attempt never actually
produced a disconnected state; nothing was disproven or confirmed.

**Root-cause classification: test-execution gap, not a code defect.**
M30.6A already fixed the underlying connection-truth mechanism
(`GmailService.ensure_connected_from_token()`); nothing since has
touched it. There is no candidate code defect to root-cause here -
only an incomplete test.

**Bounded action:** no code change anticipated. Execute a real,
isolated disconnected attempt - e.g. point `URI_GOOGLE_CREDENTIALS_DIR`
at a temporary directory with no usable `token.json` for one real
`/ask` call (never delete or overwrite the real, working
`token.json`), confirm `gate_outcome: DISCONNECTED` and a real
connection-guidance message (not a generic error), then restore normal
operation. If this reveals a real defect in the guidance message
itself, root-cause *that* specifically before patching.

### Scenario 5 - Unsupported recurring job search

**M30.7A's own finding:** telemetry confirms `gate_outcome:
UNSUPPORTED` - the deterministic Unsupported Gate correctly overrode
the model's own `clarification` mode claim (exactly the architecture's
"propose, never trust" design, working as intended). What was **not**
verified: the actual end-user-visible `/ask` response text, and
whether the legacy fallback path (since canonical fell back per
`fallback_reason: gate_not_ready:UNSUPPORTED`) produces one honest
"cannot do this" message rather than an actual repeating clarification
loop.

**Root-cause classification: test-completeness gap, likely no code
defect** - the gate itself is proven correct; only the fallback path's
own final response was never inspected.

**Bounded action:** re-attempt with the same request, this time
capturing and reading the full `/ask` response body (not just
canonical telemetry). If a genuine single clarifying question then an
honest "unsupported" resolution occurs, that satisfies the scenario's
intent (§14 wording: "no clarification loop", not "zero clarification
ever"). If a real repeating loop is observed, root-cause it against
the legacy fallback's own clarification call sites before proposing
any fix - do not assume the shape of the defect in advance.

### Scenario 6 - "I work at NIT Sikkim." → `remember_fact`

**M30.7A's own finding:** the live Decision Contract classified this
turn as `conversation`, no capability - a regression from M30.6's own
repeated, real, live success on this exact phrasing (§10 of the M30.6
report, three separate real traces).

**Root-cause candidate, from documented session history (must be
confirmed, not assumed): candidate preselection exclusion.**
`M30_5A_DECISION_QUALITY_REMEDIATION_REPORT.md` (§ "Real,
newly-introduced regression") documents this *exact* case
(`disclosure_1`/`disclosure_2`, "I work at NIT Sikkim") regressing to
`conversation` for a specifically diagnosed reason: `decision_engine.
preselect_candidate_ids()`'s term-overlap scoring shares almost no
vocabulary between a personal-disclosure sentence and `remember_fact`'s
own summary text, so `remember_fact` is silently excluded from the
candidate set the model ever sees. `M30_5B_CANDIDATE_RECALL_MULTI_
ACTION_REPORT.md` reports this case fixed for the offline golden set
after unioning three recall signals - but M30.7A's fresh live attempt
shows it can still fail for real. Two live possibilities, **both must
be checked, not guessed between:**
1. Genuine per-call model-sampling variance (M30.6 succeeded 3/3;
   this is a 4th, independent live call, not a repeat of the same
   seed/context) - if a 2-3x same-phrasing re-attempt this milestone
   is inconsistent, this is the likely explanation, and no code
   change is warranted (variance is not a defect).
2. A real, still-present preselection gap for this phrasing - if the
   same phrasing fails consistently across repeated attempts, Codex
   must trace `preselect_candidate_ids()`'s actual candidate set for
   this exact input (log or inspect it directly, do not infer) and
   confirm whether `remember_fact` is present or silently excluded.

**Bounded action, only if (2) is confirmed:** the smallest fix
consistent with M30.5A's own already-accepted design pattern (which
already carves out an unconditional inclusion for `active_pointer.
capability_id` "so a pending continuation's own capability can never
vanish") - extend the same unconditional-inclusion treatment to
`remember_fact` specifically (a cheap, always-relevant, read-adjacent,
already-low-risk capability by original design) rather than widening
the general scoring threshold, which would risk exactly the
Gmail-overlap-suppression side effects M30.5A's own report had to
manage elsewhere. Do not implement this speculatively - only if (2) is
confirmed over (1).

### Scenario 7 - Real Gmail chain (search → read → attachment)

**M30.7A's own finding:** "No safe grounded ID for follow-up chain" -
either no real, suitable multi-message/attachment-bearing thread
exists in the live test account, or the model paused for clarification
before a chain could start.

**Root-cause classification: most likely a real data-availability
limitation of the test account, not a code defect** - M30.6 already
proved the underlying grounding mechanism
(`CapabilityContextResolver`) works correctly via a fake-connected
double; M30.7A's gap is specifically about proving it against the
*real* account, which requires the real account to actually contain
matching data.

**Bounded action:** Codex must first **identify** (read-only,
real Gmail search) whether any real message with a real attachment
exists in the account at all, before attempting the chain. If one
exists, attempt the real 3-turn chain and report real grounded IDs. If
genuinely none exists, this is an honest environmental limit - record
it precisely (not as `LIVE_FAIL` implying a defect, but as a specific,
named data-unavailability note) rather than forcing a pass or
fabricating a case. Do not create synthetic test data in the real
account.

### Scenario 8 - "Prepare a reply but do not send it."

**M30.7A's own finding:** the live attempt hit `MISSING_PARAMETER`
(telemetry: `Gmail`/`create_draft`) before ever reaching an
approval-pending state - the phrasing didn't supply enough for the
gate to resolve `to`/`subject`/`body`.

**Root-cause classification: test-phrasing gap, not a code defect** -
the gate behaved exactly as designed (refusing an incomplete draft
request); the scenario's own approval-boundary behavior was simply
never reached.

**Bounded action:** no code change anticipated. Re-attempt with a
complete, real, explicit draft request (naming a real recipient,
subject, and body content) so the gate can resolve to
`APPROVAL_REQUIRED`; confirm the approval-pending state, the drafted
content shown, and - structurally, already confirmed in M30.7A's own
audit - that no send-capable path exists anywhere in `GmailService`.

### Scenario 12 - Provider failure → honest fallback

**M30.7A's own finding:** never attempted ("Unreachable-provider
condition not applied").

**Root-cause classification: not yet investigated at all** - this is
the one scenario with zero prior attempt, honest or otherwise.

**Bounded action:** before inventing a new mechanism, Codex must check
for an existing, safe way to induce a genuine provider-unavailable
condition for exactly one real call - `ModelRouter`'s own health-
tracking/fallback code and its existing tests
(`test_ollama_reasoning_adapter_live.py` and any `ModelRouter`-specific
test module) are the first place to look, per the migration plan's own
"no new plumbing" principle (§12). Only if no existing safe hook is
found should Codex propose the smallest possible temporary
condition (e.g. a real, reversible provider-endpoint misconfiguration
for one call, restored immediately after) - never a mocked/fake
response standing in for the honest-fallback proof itself.

### Scenario 9 - `convert_document` per-capability admission decision

**Not a "failure" to root-cause - a decision to make**, per M30.7A's
own already-produced recommendation (C-refined: human-reviewed
per-capability admission with mandatory Layer 3 proof).

**Framing, explicit:** admitting one additional, individually-reviewed
capability to `CANONICAL_EXECUTION_ALLOWLIST` - exactly the same
bounded action M30.6 already took twice (`Gmail`, `remember_fact`) - is
**not** the global cutover M30.8 performs, and is not prohibited by
"no M30.8 implementation." It is the migration's own established,
ongoing, per-capability growth mechanism. This plan treats it as
in-scope *only if* the evidence below actually supports it.

**Required evidence before any admission:** a real, live Layer 3 `/ask`
trace of "Convert this PDF to Word." exercising `convert_document`
through the **canonical** path once (hypothetically) allowlisted -
i.e., Codex should first evaluate whether `convert_document`'s own
execution semantics are deterministic, side-effect-bounded, and
already schema-validated enough to be canonically wrapped safely (the
same bar `ActionSchema.validate()` already applies to Gmail/
`remember_fact`). If yes, and a real live trace after a *temporary,
Codex-scoped* allowlist addition succeeds cleanly with no regression,
record the addition as a real, bounded, human-reviewed capability
addition (not a global change) and report it as such. If the
capability's execution semantics are not yet directory-schema-ready
(per the M30.7A structural audit's own broader finding that legacy
capabilities have gaps here, migration plan §3), record
`BLOCKED_BY_CURRENT_SCOPE` honestly instead of forcing it.

---

## Requirements (restated, binding)

- Root-cause each failure before proposing repair - no scenario gets a
  code change without a confirmed, evidenced cause first.
- Bounded changes only - the one plausible code change in this plan
  (scenario 6, conditional) is narrowly scoped and mirrors an
  already-accepted design pattern; every other scenario is expected to
  need a properly-executed test, not new code.
- No global canonical-default flip; no M30.8 implementation.
- Real `/ask` live proof required wherever a scenario is exercised
  through `/ask` - no bypassed principal, no directly-constructed
  executor.
- No fake-double evidence counted as `LIVE_PASS`.
- Rerun the **full** 12-scenario matrix afterward (not only the 7
  scenarios touched this round) - confirm 1, 3, 4, 10, 11 have not
  regressed.
- Fresh full regression suite required, compared against the same
  known 8-failure baseline used in every prior round this session.
- Scenario 4 stays `DOCUMENTED_ACCEPTED_RESIDUAL` - not reopened.

## Output required from Codex

`docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_REPORT.md`, containing:
per-scenario root-cause findings (confirmed cause, not the hypothesis
alone), the action taken (test-only or bounded code change, with the
change shown if any), the full re-run 12-scenario matrix, the
scenario 9 admission decision and its evidence, the fresh regression
comparison, and one final, explicit verdict line - exactly as the
User specified:

**"M30.8 READY FOR USER APPROVAL"** or **"M30.8 NOT READY - `<exact
remaining blockers>`"** - no other conclusion is acceptable.

## Write scope

`docs/plans/M30_7B*`, `docs/governance/URI_ACTIVE_MILESTONE.md`,
`docs/governance/URI_AGENT_RELAY.md`, plus source changes **only** for:
(a) scenario 6's conditional preselection fix if and only if root-cause
confirms it, (b) a temporary, reversible allowlist addition for
scenario 9 if and only if its evidence bar is met (reverted to today's
`{"Gmail", "remember_fact"}` if the evidence does not support keeping
it, never left in an ambiguous state). No other source scope is
authorized.

## Stop conditions

Do NOT make canonical execution global. Do NOT start or implement
M30.8. Do NOT retire any legacy mechanism. Do NOT touch `uri_ui/`. Do
NOT commit or push. Do NOT reopen scenario 4. Do NOT fabricate test
data in the real Gmail account for scenario 7. Do NOT treat a decision
gate correctly rejecting a bad proposal as a defect (Stage 2 §1's own
principle - the architecture working as designed is not a failure).

## Process note

Marked ACCEPTED under the standing auto-approval rule
(`ORCHESTRATION.md` §1.5) - routine verification/closure planning
within an already-authorized track (M30.7A's own direct successor,
requested directly by the User this round - no relay-channel deviation
this time). Claude does not implement or perform live verification
itself; hands off to Antigravity for routing to Codex. Claude will
independently re-audit the resulting report against real telemetry/
session-state artifacts before treating either verdict line as final -
exactly as for every prior milestone this session.

---

Stopping here. M30.7B plan is ready for Antigravity to route to Codex.
M30.8 is not started and not authorized.
