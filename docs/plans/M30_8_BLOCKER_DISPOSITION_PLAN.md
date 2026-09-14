# M30.8 - Blocker Disposition Plan (Read-Only)

STATE: DISPOSITION PLAN ONLY - NOT A PLAN TO IMPLEMENT, NOT ACCEPTED
AS AN IMPLEMENTATION AUTHORIZATION, M30.8 NOT AUTHORIZED. Produced by
Claude (Architect role) at the User's explicit request. No production
code was written or modified to produce this document.

## Acceptance criteria for this document (defined before drafting, per
the repository's standing Verification-First Audit and Planning
Standard, `CLAUDE.md`)

1. Every one of the 6 named scenarios gets all 9 required elements the
   User specified - no scenario may be skipped or merged with another.
2. Every root-cause claim must cite a real artifact (telemetry record,
   source line, or a prior audit's own independently-verified finding)
   - never restated assumption.
3. The four closing buckets must be a strict, non-contradictory
   partition of the six scenarios' individual dispositions - no
   scenario may appear in two buckets or be silently dropped.
4. Scenarios requiring genuinely different kinds of work (a live
   re-test vs. real schema/implementation work) must never be
   collapsed into one recommended action, per the User's own "do not
   group unrelated blockers into one broad milestone" instruction.
5. Where evidence is incomplete or aging, that must be stated
   explicitly, not smoothed over.

**Primary evidence used** (re-consulted directly for this document,
not recalled from memory alone): `uri_workspace/canonical_execution_
log.jsonl` (re-read for the exact M30.7B session records cited below),
`docs/plans/M30_7B_CLAUDE_AUDIT.md` (both the original and re-audit
addendum), `docs/plans/M30_7B_CANONICAL_READINESS_CLOSURE_REPORT.md`,
`docs/plans/M30_7A_CLAUDE_AUDIT.md`, `uri_core/core/decision_gates.py`,
`uri_core/core/canonical_execution.py`, `uri_core/services/gmail_
service.py`, `uri_core/core/connection_status.py`, `docs/plans/
URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md` §3/§11.

---

## Product Decisions from User Review (2026-09-13) - ratifying and refining this plan

This section records the User's own product-level review of this
plan's findings, applied below to ratify, refine, or defer each
scenario's disposition. **No production source change is authorized
by this section** - it is a planning/alignment update; any item
requiring code remains gated behind its own existing or future
milestone authorization.

**1. Provider-failure fail-closed rule - confirms and broadens
M30-PFC's already-approved scope, no new source scope implied.**
Under `MODEL_TERMINALLY_UNAVAILABLE` (the only state that gates,
per the already-approved `M30_PROVIDER_FAILURE_FALSE_CONSENT_REPAIR_
PLAN.md`), the User requires: no learned-skill execution, no
`remember_fact`, no persistence, **no approval execution, no side-
effecting capability execution** - the last two are a broader
articulation than the plan's original remember_fact/learned_skill-only
framing. Checked directly: this broader guarantee is **already
structurally satisfied** by `capability_planner.py`'s own,
independently-verified behavior for a genuinely degraded/empty
semantic result (returns `"planning_required"`, `tool_name: None` -
tested empirically this session) - a capability_planner-selected path
is the only *other* route into approval-gated execution besides
`learned_skill`, and it already fails closed correctly. **Recommend
adding one confirming test** (within M30-PFC's already-approved test
budget, not new source scope) asserting no approval-gated capability
executes either during a `MODEL_TERMINALLY_UNAVAILABLE` turn - a
completeness check on already-correct behavior, not a new code path.
"Do not solve this with one arbitrary global timeout" - consistent
with M30-PFC's own approach (a status-based distinction, not a
timeout value).

**2. Model health/timeout direction - recorded for future refinement,
explicitly not folded into M30-PFC.** See "Future Direction Notes"
at the end of this document.

**3. Scenario 2 - backend/UI responsibility split, ratifies existing
scope.** Backend stays narrow and deterministic
(`CONNECTED`/`DISCONNECTED`/`REAUTH_REQUIRED`/`CHECKING`/`UNKNOWN`);
UI owns reconnect UX. Checked directly: `connection_status.py` already
reports a three-state model (`connected`/`needs_authorization`/
`not_connected`) - `needs_authorization` is the existing analog of
`REAUTH_REQUIRED` for "credentials exist but no usable token," though
not currently distinguishing "never authorized" from "token expired
and needs re-auth" as two separate labels. This distinction, if wanted
precisely, is a small, separate naming/state refinement - **not
required to close Scenario 2's own readiness evidence**, which only
needs a real, observed `DISCONNECTED` gate outcome (unchanged
requirement, no new code implied by this product direction alone).

**4. Scenario 7 - real-data-only, ratifies existing scope exactly.**
Already this plan's own position (§ Scenario 7 below) - the User
additionally offers to provide/use a real test account with a genuine
attachment-bearing email if needed. No change to the technical
requirement; removes the "no suitable message may exist" blocker if
the User supplies one.

**5. Scenario 8 - informed-approval envelope, checked directly: already exists, evidence-only.**
Checked `uri_core/core/approval_store.py`'s `ProposedAction` dataclass
directly: it already carries `capability_id`, `arguments: Dict[str,
Any]` (which for a real `create_draft` proposal already includes `to`/
`subject`/`body`/`in_reply_to_thread_id`, per `GmailCapability`'s own
action schema), and `status`. **The envelope already exists** - this
confirms the User's own instinct ("do not redesign... if the required
envelope already exists"). Scenario 8's own remaining work is
therefore evidence capture only (show these fields are genuinely
populated in a real `APPROVAL_REQUIRED` response), not new code.

**6. Memory product rule (explicit task / self-reference / corrections
/ confirmed consent hierarchy) - recorded for a future, separately-
approved memory-policy milestone, explicitly not folded into M30-PFC.**
See "Future Direction Notes." Directly relevant context: this
hierarchy, if implemented, would have structurally prevented the
M30-PFC defect's *class* of problem at a different layer (durable
writes gated on real intent signals) - but M30-PFC's own narrower,
already-approved fix (gate the specific broken code path) remains the
correct immediate remedy; this broader policy is real, separate,
future work, not a substitute or a scope expansion for M30-PFC.

**7. Graphify/M30.9 direction - recorded for future M30.9 planning.**
See "Future Direction Notes." Not relevant to M30.8 readiness.

**8. Remaining readiness classification - ratifies this plan's own
original recommendations almost exactly**, with two refinements: (a)
Scenario 7 gets an explicit "may remain non-blocking if fixture
unavailable and mechanism proof is otherwise sufficient" escape valve
(this plan's own original text already allowed for this - now
User-confirmed as the deciding call rather than left as an open
question), and (b) Scenario 12 is explicitly sequenced as **CLOSE NOW
only after M30-PFC repair is accepted** (mechanically true already -
Scenario 12 *is* the live proof of the M30-PFC fix, cannot be honestly
attempted before that repair exists). See the updated Summary section
below for the finalized bar.

---

## Scenario 2 - Gmail disconnected → `DISCONNECTED`

**1. Exact remaining gap:** no live attempt has ever produced a real
`gate_outcome: DISCONNECTED` for Gmail. M30.7B's three isolated-
disconnected attempts (`canonical_execution_log.jsonl`:
`m30_7b_s2_disconnected` → `unsupported`/`INVALID_PROPOSAL`;
`m30_7b_s2_disconnected_retry` → `fallback_reason: invalid_contract:
unknown_capability`; `m30_7b_s2_disconnected_gmail` → `unsupported`/
`INVALID_PROPOSAL`) never even reached a Gmail-specific availability
check - the model/gate classified the request as having no valid
capability at all, before Gate 1 (availability) could ever fire.

**2. Classification:** infrastructure/test-fixture issue.

**3. Root cause:** the isolated-disconnected fixture used
(`URI_GOOGLE_CREDENTIALS_DIR` pointed at an empty temp directory) most
likely produces `connection_status.py`'s `not_connected` state (no
`credentials.json` at all) rather than a "was connected, token now
invalid" state. Reading `decision_gates.py`'s own structure directly:
the availability/`DISCONNECTED` branch (§6 gate 1) only runs *after* a
capability_id has been resolved from the contract; if the Directory
itself never surfaces Gmail as a plausible capability under a
completely credential-less fixture, the model has nothing to name, and
the flow correctly falls to `INVALID_PROPOSAL`/`unsupported` instead -
never reaching the `DISCONNECTED` branch at all. This is a fixture-
design gap (the wrong kind of "disconnected" was simulated), not a
defect in `GmailCapability._availability()` or `decision_gates.py`
itself - both of these were already independently verified correct in
`M30_6A_CLAUDE_AUDIT.md`.

**4. Evidence that would close it:** one real live attempt using a
fixture that mimics "previously connected, now invalid" (e.g. an
expired/corrupted `token.json` still present, with `credentials.json`
still present, rather than an empty directory) - so the Directory
still lists Gmail as a real capability, the model can still propose
it, and Gate 1 has a real chance to evaluate and return `DISCONNECTED`
with the honest connection-guidance message.

**5. Source changes required:** none anticipated - this is a test-
fixture correction, not a code fix.

**6. Scope estimate:** small - one corrected live `/ask` attempt,
using the real, already-working credential-swap mechanism
`URI_GOOGLE_CREDENTIALS_DIR` already provides.

**7. Risks/architectural consequences:** none from a code perspective.
The only risk is repeating the same fixture mistake without first
confirming the corrected fixture actually produces an invalid-but-
present token before spending another live cycle on it.

**8. Recommended disposition: CLOSE NOW.**

**9. Must it close before M30.8:** **Yes.** Connection-truth
correctness under `DISCONNECTED` was the entire subject of M30.6A, and
Gate 1 is the first, most safety-relevant deterministic check in the
whole canonical pipeline (§6). M30.8 makes this gate authoritative for
every turn, not an allowlist-scoped subset - it should be observed to
actually fire correctly at least once for real before that happens.

---

## Scenario 5 - Recurring job search → clean `UNSUPPORTED`, no clarification loop

**1. Exact remaining gap:** the canonical Decision Contract correctly
classifies the initial request as `UNSUPPORTED` (`m30_7b_s5_recurring`
and `m30_7b_s5_visible`, both `gate_outcome: UNSUPPORTED`/
`INVALID_PROPOSAL`, confirmed real). But a documented follow-up
("do this automatically every day") caused the **legacy fallback
path** (not canonical - `web_search` was never in
`CANONICAL_EXECUTION_ALLOWLIST` and could not have executed
canonically regardless) to perform a real, one-time `web_search`
rather than an honest refusal of the recurring-automation request.

**2. Classification:** model-quality issue (specifically: a pre-
existing property of the *legacy* fallback path, not the canonical
path).

**3. Root cause:** the legacy priority chain has no deterministic
"this names a scheduling/recurrence capability that does not exist"
check of its own - unlike the canonical Unsupported Gate
(`decision_gates.py`), which is a canonical-only mechanism per the
migration plan's own design (§6: gates are wired to the Decision
Engine's output, not to the legacy chain). The legacy path relies
entirely on the Brain's own free-form judgment, which chose to
interpret an ambiguous "make this recurring" request maximally
helpfully (do the one-time version) rather than flag the unsupported
scheduling aspect. This is consistent with, not contradicted by, the
canonical path's own separate, correct `UNSUPPORTED` classification -
the two paths were never expected to share a gate; only canonical has
one.

**4. Evidence that would close it (if pursued):** would require
either (a) accepting that canonical's own classification is what
matters for M30.8's purposes (the legacy path is what M30.8 demotes to
fallback-only, invoked rarely), or (b) adding a deterministic
recurrence/scheduling-request check to the legacy path itself - real,
non-trivial implementation work with its own regression surface.

**5. Source changes required:** only if (b) above is pursued - real
changes to the legacy Brain-reasoning path's own judgment, not a
bounded fix.

**6. Scope estimate:** if pursued as a fix, **not small** - touches
the free-form Brain-reasoning path this session's own standing rule
already flags as sensitive (`orchestrator.py` must not grow further),
and risks exactly the "reintroduce a second decision owner" failure
mode this whole migration exists to remove, for a path M30.8 itself
is actively demoting to rare-fallback status.

**7. Risks/architectural consequences:** attempting to "fix" legacy
judgment quality risks (a) wasted investment in a mechanism M30.10
eventually deletes, (b) scope creep into the exact multi-decision-
owner risk class this migration guards against, per this session's own
M30.8 pre-audit (§6, "risks of reintroducing multiple decision
owners").

**8. Recommended disposition: ACCEPT AS LIMITATION.**

**9. Must it close before M30.8:** **No.** The canonical path - the
one M30.8 makes globally authoritative - already correctly and
repeatedly classifies this request as `UNSUPPORTED`. The residual
concerns the legacy fallback's own separate judgment on an
unallowlisted capability (`web_search`), which by M30.8's own design
becomes a rare, exceptional path (invoked only when the Decision
Engine is unreachable or its contract is malformed/rejected) - not the
path whose safety M30.8 is being gated on.

---

## Scenario 7 - Real Gmail chain (search → read → attachment)

**1. Exact remaining gap:** the search half is now genuinely live-
proven for real (`m30_7b_s7_search`: `single_action`/`Gmail`/
`search_messages`/`READY`/`success`/grounded evidence, confirmed real
in `M30_7B_CLAUDE_AUDIT.md`'s re-audit). No safe, real, attachment-
bearing message exists (or has been found) in the connected test
account to continue the read → attachment half of the chain.

**2. Classification:** infrastructure/test-fixture issue (specifically
real-data availability in the live test account), not a code defect.

**3. Root cause:** the underlying grounding mechanism
(`CapabilityContextResolver`) was already proven correct twice by
different means - via a fake-connected double in M30.6 (§9/§11 of the
M30.6 report) and now via the real search half in M30.7B. What remains
is not a mechanism gap but a **data** gap: no message with a real
attachment has been located (or confirmed to exist) in the connected
account for a live 3-turn chain to complete against.

**4. Evidence that would close it:** a real, read-only Gmail search
for a message that has an attachment in the connected account (the
User may need to confirm one exists, or send a real test email with an
attachment to the connected mailbox first), then a genuine 3-turn live
chain (search → read → attachment) against it.

**5. Source changes required:** none.

**6. Scope estimate:** small - a live-verification/data-discovery
task, not code work. Depends on real mailbox contents, which Claude
cannot manufacture (and must not - fabricating test data in the real
account is an explicit standing prohibition from the M30.7B plan).

**7. Risks/architectural consequences:** none, provided no synthetic
data is ever created in the real account.

**8. Recommended disposition: CLOSE NOW** - but flagged as depending
on real mailbox contents outside Claude's or Codex's control; if no
such message can be found or produced by the User, this degrades to
**DEFER** (not **ACCEPT AS LIMITATION** - the mechanism is sound, only
the proof is pending real data), not a synthetic-data workaround.

**9. Must it close before M30.8:** **Should close, but not an absolute
hard blocker.** The mechanism has already been proven correct twice by
independent means (fake-double + half-real). A full real closure is
the strongest possible confirmation before Gmail becomes part of a
globally-authoritative canonical default, but the redundant existing
proof means this is the single softest "must-close" item among the
six, not equivalent in risk to scenario 2's Gate-1 gap.

---

## Scenario 8 - "Prepare a reply but do not send it." (draft/approval boundary)

**1. Exact remaining gap:** `APPROVAL_REQUIRED` now proven live twice,
for real (`m30_7b_s8_draft`, `m30_7b_s8_visible`: both `single_action`/
`Gmail`/`create_draft`/`gate_outcome: APPROVAL_REQUIRED`). The
structural no-send fact is independently confirmed (`gmail_service.py`
grep: zero `send`-named methods, `create_draft()` calls only
`users().drafts().create()`). What remains unobserved: the actual
drafted **content** returned to the user for review before approval -
prior live captures only recorded canonical telemetry fields, not the
full HTTP response body.

**2. Classification:** evidence-only closure.

**3. Root cause:** not a defect - simply never inspected. Every prior
live attempt for this scenario captured `canonical_execution_log.jsonl`
fields only (which do not include response body content), not the raw
`/ask` response the end user would actually see.

**4. Evidence that would close it:** re-run the same successful
`create_draft`/`APPROVAL_REQUIRED` live call once more and capture +
read the full HTTP response body, confirming the composed draft
content (to/subject/body) is genuinely shown for review, not merely
that a pause occurred.

**5. Source changes required:** none anticipated.

**6. Scope estimate:** trivial - one more live call with fuller
evidence capture (a capture-methodology fix, not new work).

**7. Risks/architectural consequences:** none.

**8. Recommended disposition: CLOSE NOW.**

**9. Must it close before M30.8:** **Yes, but very low effort** - this
is the last mile of an already ~95%-proven scenario; cheap to finish
before relying on it as part of a global-default justification.

---

## Scenario 9 - `convert_document` per-capability admission

**1. Exact remaining gap:** `convert_document` is confirmed, twice
independently (M30.7A and M30.7B audits), not Layer-3 ready for
canonical wrapping - `result_schema_known: false`, empty
`action_schemas`, no branch in `canonical_execution.py`'s
`_execute_allowlisted()`.

**2. Classification:** capability-admission issue.

**3. Root cause:** `convert_document` was built as a plain legacy
tool, never migrated into the M27/Directory schema-validated shape.
This is a known, disclosed, pre-existing architectural gap, not new -
the migration plan's own component matrix (§3) explicitly marks
"parameter requirements" and "result schema" as `❌ initially` for the
Legacy adapter, and states this gap is "explicitly acceptable... closed
incrementally, per capability, not as a blocking prerequisite."

**4. Evidence that would close it:** would require actually building
a real result schema and action schema for `convert_document` inside
the Capability Directory's legacy adapter, plus a real canonical
execution branch, plus a genuine Layer 3 live proof - i.e., real
implementation work, not an evidence-capture task.

**5. Source changes required:** **Yes, real ones** - Directory schema
authoring, a `canonical_execution.py` dispatcher branch, and
allowlist admission, each requiring its own review.

**6. Scope estimate:** **medium, not bounded** - this is a genuine,
multi-file implementation task with its own test/live-verification
requirements, structurally different in kind from every other scenario
in this document (which are re-tests or fixture corrections). It must
never be folded into a "blocker closure" pass alongside the others.

**7. Risks/architectural consequences:** rushing this without the
schema rigor the Directory interface was designed around risks exactly
the "under-schema'd capability wrapped canonically" failure the
migration plan's own gaps table (§3) was written to prevent.

**8. Recommended disposition: DEFER** - to its own future, separately-
scoped, explicitly-authorized milestone, not bundled here.

**9. Must it close before M30.8:** **No.** M30.8's own stated scope is
making the Decision Engine authoritative for the capabilities that
already have Layer 3 coverage (`Gmail`, `remember_fact`) - it does not
require every legacy capability to be canonically admitted first.
`convert_document` remaining `BLOCKED_BY_CURRENT_SCOPE` and continuing
to execute via its own unchanged legacy mechanics (exactly as the
migration plan's own original scenario 9 text describes: "executes
exactly as it does today, unchanged legacy mechanics") is a
permanently acceptable state, not a blocker.

---

## Scenario 12 - Provider failure → honest fallback

**1. Exact remaining gap:** canonical correctly refuses to execute
under a genuinely unavailable provider, confirmed twice
(`m30_7b_s12_provider_unavailable`, `m30_7b_s12_provider_unavailable_
model`: both `fallback_reason: invalid_contract:unavailable`). What
remains unconfirmed: whether the actual **visible**, end-user-facing
response (produced by the legacy fallback, since canonical always
defers to it here) is an honest "could not reason about this right
now" message, or something else (a raw error, a silent empty response,
or a fabricated answer).

**2. Classification:** evidence-only closure (with a small,
conditional possibility of a real defect - unknown until observed).

**3. Root cause:** same pattern as scenario 8 - every prior attempt
captured only canonical telemetry, never the actual `/ask` response
body text a user would see. The migration plan's own failure-handling
table (§11) already describes a dedicated "Model provider unavailable"
honest-template mechanism as existing ("Same as 'model timeout'
above"); the safety-relevant refusal-to-fabricate property is already
proven at the canonical layer - only the final rendered message was
never read.

**4. Evidence that would close it:** re-run the same unreachable-
provider condition once more and capture + read the full `/ask`
response body/narrative text; confirm it reads as an honest,
non-fabricated refusal rather than a raw exception or empty body.

**5. Source changes required:** none anticipated, **unless** the
captured message turns out to be genuinely bad (a raw stack trace, an
empty response, or a fabricated answer) - in which case a small,
bounded fix to the existing honest-fallback template (already
described as existing per §11) would be in scope; this cannot be
determined without first observing it.

**6. Scope estimate:** small - one more live call with fuller evidence
capture; a bounded template fix only if evidence reveals a real
problem (not yet known to exist).

**7. Risks/architectural consequences:** low. If a real defect is
found, fixing an existing message template is inherently narrow and
low-risk.

**8. Recommended disposition: CLOSE NOW.**

**9. Must it close before M30.8:** **Yes, but low effort** - an
unverified honest-fallback message for a condition that will
definitely still occur occasionally in a globally-canonical world is
worth confirming cheaply before relying on it at global scale.

---

## Summary (finalized per User product-decision review, 2026-09-13)

### Blockers recommended to CLOSE NOW
- **Scenario 2** - re-run with a corrected "invalid-but-present token"
  fixture (not empty-credentials-dir) to actually observe
  `DISCONNECTED`. No code change anticipated.
- **Scenario 8** - evidence capture only: the required envelope
  (`ProposedAction.capability_id`/`arguments`/`status`) already exists
  - confirmed by direct source check (§ Product Decisions, item 5).
  Show it populated in a real `APPROVAL_REQUIRED` response.
- **Scenario 12** - CLOSE NOW **only after `M30-PFC` repair is
  accepted** - this scenario *is* the live proof that repair worked
  (real provider-failure visible fallback, zero side effects). Cannot
  be honestly attempted before that repair exists.

### Blocker recommended as BEST-EFFORT CLOSE NOW
- **Scenario 7** - real Gmail search → read → attachment chain, real
  data only (User may provide a real test account/message). **No
  fabricated Gmail data may count as `LIVE_PASS`.** If no suitable
  real message exists even with the User's help, document that fixture
  limitation honestly and it **may remain non-blocking** - the
  underlying mechanism is already proven twice by other means (M30.6's
  fake-double, M30.7B's real search half) - User's own explicit call,
  not a default Claude/Codex may assume unilaterally.

### Blocker recommended to DEFER
- **Scenario 9** - real, multi-file implementation work (Directory
  schema authoring + canonical dispatcher branch + its own Layer 3
  proof) - structurally different in kind from the others, belongs in
  its own future, separately-scoped, explicitly-authorized milestone.
  Not an M30.8 prerequisite - `convert_document` stays out of the
  allowlist, unaffected.

### Blocker that may be ACCEPTED AS DOCUMENTED LIMITATION
- **Scenario 5** - canonical's own classification is already correct
  and repeatedly proven (`UNSUPPORTED`); the residual is specifically
  the legacy fallback path's own judgment on an unallowlisted
  capability (`web_search`), a pre-existing property of a path M30.8
  itself demotes to rare-fallback status. Accepted as a documented
  limitation unless new evidence changes this.

### Exact minimum remaining bar for `M30.8 READY FOR USER APPROVAL`

Per the User's own explicit statement, all three must hold:

1. **`M30-PFC` receives independent Claude `ACCEPT`** (all 8 repair
   tests + the 6 existing learned-skill tests unbroken + live
   re-reproduction + healthy-path disclosure re-confirmed + real
   terminal regression - per `docs/plans/M30_PROVIDER_FAILURE_FALSE_
   CONSENT_REPAIR_PLAN.md` §6/§8, unchanged by this update).
2. **Mandatory remaining readiness evidence closes**: Scenarios 2, 8,
   and 12 (12 sequenced after #1). Scenario 7 closes if real data is
   available; otherwise documented as a non-blocking limitation per
   the User's own explicit allowance above. Scenarios 5 and 9 do not
   need to close (accepted limitation / deferred, respectively).
3. **Regression reaches a real, completed terminal result** - the full
   suite run to actual completion and observed (never an unobserved or
   killed run treated as a result, per this session's own established
   discipline), compared against the known 1,726/8/0-new baseline.

Once all three hold, and the full 12-scenario matrix is rebuilt one
final time to confirm nothing else has drifted, M30.8 would have a
legitimate case for `READY FOR USER APPROVAL` - the User's own final
review and explicit authorization remain required regardless; this
document does not substitute for either.

## Future Direction Notes (recorded for later milestones - NOT actioned in M30-PFC or M30.8)

**Model health/timeout direction (future refinement, item 2 of the
User's review):** distinguish `model/service not required` /
`running normally` / `slow but active` / `responded but invalid` /
`terminally unavailable` / `fallback exhausted` using explicit
provider errors, process/service health, request progress/heartbeat/
streaming signals, and model-/task-specific bounded adaptive
thresholds - never one arbitrary global timeout. A possible future
**Model Behaviour Profile** (latency, first-token time, task/reasoning
level, success/failure and timeout rates, provider reliability) is
named explicitly as **operational telemetry, not another decision
engine** - it must never become a second, competing source of decision
authority alongside the Decision Engine/deterministic gates. **Not
folded into M30-PFC** - the existing status-based signals
(`reasoning_disabled`/`reasoning_failed`/`reasoning_completed`,
`AllProvidersUnreachableError`) are sufficient for that repair.

**Memory product rule (future, separately-approved memory-policy
milestone, item 6):** durable memory should not come from arbitrary
conversation by default. Preferred hierarchy: (A) an explicit memory
task ("Remember that...") may persist directly; (B) conversational
self-reference (I/me/my/we/our) may become session context or a
memory *candidate*, never automatically durable; (C) user corrections/
repeated choices build preference evidence/confidence, confirmed
before becoming durable; (D) confirmed conversational consent
("Would you like me to remember that?" → "Yes") makes durable memory
allowed. **Principle: self-reference creates eligibility for
consideration, not permission.** No explicit retention intent or
confirmed consent → no durable write. This is real, separate,
future-scoped work - explicitly not an M30-PFC scope expansion; a
dedicated plan would need its own approval before any implementation.

**Graphify/M30.9 direction (future M30.9 planning, item 7):** Graph
Intelligence framed as "URI's cognitive index and GPS" - indexing and
relating facts, memories, entities, workflows, capabilities, internal
and external/imported skills, dependencies, provenance, reliability,
and pointers to authoritative sources - storing compact metadata and
resolvable pointers, never copying the whole system. Purpose:
progressive context reduction (user request → Graphify finds the small
relevant subset → Brain receives only needed tools/skills/memories/
documents/dependencies → deterministic gates validate → execution).
**Graphify must never become a planner, executor, authorization
authority, approval authority, or a replacement for the Capability
Directory.** Not relevant to M30.8 readiness; recorded here purely as
input for whenever M30.9 planning begins.

**Sequencing and cutover-shape direction (recorded 2026-09-14, User
instruction - not actioned, input for the next planning pass only):**

- **Graphify foundation must come before canonical cutover.** The
  Graph Intelligence layer above is sequenced as a *prerequisite* to
  M30.8's own cutover, not a parallel or later-arriving M30.9 concern -
  the next planning pass should treat "Graphify foundation in place"
  as a precondition to check before recommending canonical cutover,
  not an independent milestone track.
- **Graphify loads at startup as URI's cognitive index/GPS.** Framed as
  an always-available, in-memory-resident index from process start
  (not something built lazily per-request or per-session) - consistent
  with, and a sharpening of, the "progressive context reduction"
  purpose already recorded above.
- **M30.8 itself should be re-planned as "Canonical Cutover + Legacy
  Retirement"**, not merely "make the Decision Engine authoritative."
  This changes the milestone's own shape from a pure additive/parallel-
  shadow cutover to one that also includes a deliberate retirement step
  for the mechanisms the migration plan's own component matrix (§1)
  already lists as superseded (Brain proposal direct-plan authority,
  `MultiActionDispatch`'s own legacy trigger, `skill_memory`'s direct-
  plan authority, `capability_planner.py`, `WorkflowPlanner`) - not
  simply leaving them in place indefinitely as an always-available
  fallback once canonical coverage is proven sufficient.
- **Duplicate legacy authority should be removed once canonical
  coverage is proven**, not retained indefinitely "just in case." This
  is a direct, explicit refinement of - and takes priority over - this
  document's own current §5 stop-condition ("Do NOT retire legacy
  mechanisms") for the *next* planning pass specifically: that stop
  condition remains correctly binding for every milestone up through
  and including this one (M30.7C), but the next M30.8 plan should be
  drafted to include a real, scoped legacy-retirement step once its own
  cutover evidence proves canonical coverage is sufficient for the
  capabilities being retired - not as an open-ended "keep both forever"
  design. **Directly informed by this pass's own Scenario 2 finding**
  (see the M30.7C readiness report): retiring the legacy fallback
  before the Decision Engine's "unsupported claim" contract-validation
  gap is addressed would turn a genuinely disconnected Gmail account
  into a raw `INVALID_PROPOSAL` failure instead of today's honest
  fallback message - so any legacy-retirement step in the next M30.8
  plan must explicitly sequence Scenario 2's own gap closure (or an
  equivalent safeguard) ahead of retiring the specific legacy path that
  currently absorbs it.

---

Stopping here per explicit instruction. No plan drafted for
implementation, no production code touched, M30.8 not authorized and
not started.
