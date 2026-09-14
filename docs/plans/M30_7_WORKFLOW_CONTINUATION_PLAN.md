# M30.7 - Workflow Continuation & Active Pointer (Plan)

## REVISION v2 (2026-09-13) - PLAN_REVISION response to Codex's halt

Codex began implementation against v1 of this plan and safely halted
before making unauthorized or unsafe edits, correctly identifying two
real architectural gaps v1 did not account for. Both were independently
re-verified against source by Claude (not taken on Codex's word alone)
before this revision:

**Gap 1 (blocks Scenario 11) - confirmed real.** `server.py:1149` calls
`context.orchestrator.process_user_input(...)` *before*
`run_canonical_for_ask(...)` (line 1199). Inside
`process_user_input`, `orchestrator.py:4223-4240` unconditionally
resumes any pending `session.active_workflow` (status
`waiting_for_input`) via `_resume_active_workflow()` and returns
immediately - before canonical execution, or any model judgment about
whether this new message is actually a continuation or a topic switch,
ever runs. v1's §2E assumed a "deterministic recency/goal-continuity
check" could gate this independently of the model; re-checked directly
against `decision_engine.py` and `M30_5D_TEMPORARY_CONTEXT_INTENT_
SHIFT_REPORT.md` §2-3, **this was wrong** - continuation-vs-topic-switch
is, by explicit M30.5D design, a judgment the *model* makes inside the
Decision Contract (`DECISION_CONTRACT_SYSTEM_PROMPT`'s 1a-1d sequence),
never a separate deterministic pre-model function
(`classify_agreement()` is an offline, post-hoc shadow-comparison
label, not a live gate - citing it as reusable "the same one" in v1
was an error). §2E and §2F below are corrected accordingly.

**Gap 2 (blocks Scenario 4) - confirmed real.** `_apply_clarification_
pause` (`orchestrator.py:1747`) records only `{"goal": user_text,
"proposal": {"type": "clarification", "question": question}, ...}` in
`attempt_history` - no capability, action, inputs, or missing_field.
`turn_state.py`'s attempt_history-sourced `active_pointer` branch
(lines 227-256) confirms this exactly: `capability_id`, `action`, and
`missing_field` are hardcoded `None` there, "honestly None, never
guessed." v1's §2B assumed the gate could resolve
`active_pointer.capability_id` for this (the far more common) pause
path - it cannot, because that field is never populated. §2D/§3 below
are corrected to require durable metadata at the point of pause.

Corrections are confined to §2B-F and §3 below; §1, §2A, §2C, §4, and
§7-9 are unaffected and stand as v1 wrote them (re-verified, still
accurate).

## REVISION v3 (2026-09-13) - organic first-turn trace, per User directive

Following ACCEPT WITH FOLLOW-UP (`docs/plans/M30_7_CLAUDE_AUDIT.md`),
the User asked Claude to trace the real pause path before writing any
more code, per five specific questions. Answered directly from source:

**1. Which live path currently asks the user for missing information
on a known capability (e.g. "Find the student." → missing roll
number)?** `_save_paused_workflow`/`session.active_workflow` - a
separate, pre-existing (pre-M30.7) mechanism from `_apply_
clarification_pause`. `workflow_capability_router.py`'s question-
generation step (lines 316-341) returns `{"status":
"waiting_for_input", "message": ..., "required_field": ...}`;
`_save_paused_workflow` (`orchestrator.py:3532-3571`) writes this into
`session.active_workflow_status`/`active_workflow_required_field`/
`active_workflow_question`, and `session.active_workflow` itself holds
the workflow dict passed in from wherever the pause originated
(Brain-composed workflows carry `"source": "model_reasoning"` and a
`capability`/`task` key, per `_create_workflow_executor`'s own
docstring, `orchestrator.py:3478-3488`).

**2. At that exact point, does URI know capability_id/action/
missing_field/expected_type/known_inputs?** Partially, and this was
already true *before* M30.7: `capability_id` - yes, via `active_
workflow.get("capability") or active_workflow.get("task")`
(`turn_state.py:208-209`, unchanged since M30.5A). `missing_field` -
yes, via `active_workflow_required_field` (`turn_state.py:200`,
unchanged). `action` - no, `turn_state.py`'s active_workflow branch
hardcodes `"action": None` (line 220) even though nothing prevents
reading it from the workflow dict if present. `known_inputs` - no,
never read at all in this branch, even though `SessionState.
current_facts` (`state.py:19`, already persisted/restored) is exactly
this data: the partial answers a multi-field workflow like `extract_
student_records` has already collected before pausing on the next
missing one.

**3. Why is `_apply_clarification_pause`'s metadata not populated by
this real path?** Because it is the wrong function - `_apply_
clarification_pause` and `_save_paused_workflow` are two different,
independent pause mechanisms (confirmed in the original v1/v2 trace).
Re-checking all 3 `_apply_clarification_pause` call sites again this
revision confirms each fires only when the Brain has proposed *no*
capability/workflow at all (`next_capability is None and next_workflow
is None`, `orchestrator.py` ~2725-2778, and the equivalent first-call
site) - genuinely nothing to thread through, by construction, not an
oversight. §2D's fix to that function remains correct and safe, but it
was never going to be the mechanism Scenario 4 exercises for a
structured capability like `extract_student_records`.

**4. Which earlier canonical object contains the missing metadata,
then?** `session.active_workflow` (capability/task, already-known) and
`session.current_facts` (already-collected field values) - both
pre-existing, both already persisted, neither invented by this
revision.

**5. Is `active_workflow` already the real production source of
continuation state instead of `_apply_clarification_pause`?** **Yes -
Outcome B.** It already is, and has been since before M30.7. No second
workflow/pause engine is needed or being proposed.

### Decision: Outcome B, with one small bounded completion (not outcome A, not a new mechanism)

`active_workflow` is confirmed as the real canonical pause source. The
one real, bounded gap: `turn_state.py::_project_active_pointer()`'s
active_workflow branch (lines 198-225) does not project `action` or
`known_inputs`, even though both are available from data already on
`session` (the workflow dict's own `action`/`task_action`-shaped key if
present, and `session.current_facts` respectively) - unlike the
attempt_history branch (§2D, already fixed), which projects both. This
is the smallest possible completion, not a new capability:

- `uri_core/core/turn_state.py` - in the active_workflow branch, set
  `"action": (active_workflow or {}).get("action")` (mirrors the
  existing `capability_id` line exactly - `None` when the workflow
  dict genuinely has no action key, never guessed) and `"known_inputs":
  dict(getattr(session, "current_facts", None) or {})`.
- No change to `_save_paused_workflow`, `WorkflowCapabilityRouter`, or
  any Brain-composed-workflow construction - this is a read-side
  projection completion only, exactly like §2D's own attempt_history
  fix was.
- `decision_gates.py`'s `workflow_continuation` branch (§2B, already
  built) needs no change - it already reads `active_pointer.get
  ("action")`/`active_pointer.get("known_inputs")` generically; it will
  simply start receiving real values from this branch instead of
  `None`/`{}`.

### Mandatory live scenario (for Codex to execute for real - Claude does not fabricate this evidence)

Two-turn, fully organic, no seeded state:

**Primary:** "Find the student." (real `/ask`, real authenticated
principal) → URI must genuinely ask for the missing identifier via the
real `extract_student_records`/`WorkflowCapabilityRouter` path (not
constructed by a test fixture) → inspect real, persisted session state
to confirm `active_workflow`/`current_facts` were set organically →
"B250012CS." (second real `/ask`, same session) → required: `canonical_
mode: workflow_continuation`, real capability/action resolution, gate
`READY`, real execution, grounded response. Sanitized telemetry only -
no student record content in the report.

**Topic-switch regression:** "Find the student." → (without answering)
"How many unread emails do I have?" → required: newest intent wins,
NOT `workflow_continuation`, Gmail path taken instead, pending
workflow cleared - re-proving the M30.5D rule is not broken by this
completion.

**Regression:** re-run `test_workflow_continuation.py` plus the full
M30.7-adjacent set (§7) - the new turn_state.py fields are additive
(`None`/`{}` when absent, exactly today's behavior for any session
without them), so no existing test should need to change.

### Acceptance

M30.7 reaches `LIVE_VERIFIED + CLAUDE ACCEPT` (no follow-up qualifier)
only when: the primary scenario above passes organically (not seeded),
the topic-switch regression re-passes, flag-off behavior is
unchanged, and the full regression set stays green. Claude re-audits
against real telemetry and session-state artifacts, exactly as for
M30.6A and M30.7's first audit - not against a report's narrative
alone.

## REVISION v4 (2026-09-13) - pause-persistence trace, per Antigravity/Codex escalation

Codex's real, organic live attempt (per `claude_m30_7_trace_task.txt`)
disproved v3's premise for the specific "Find the student." example:
`session.active_workflow`/`active_workflow_status`/`current_facts` all
stayed empty after turn 1, even though the response genuinely said
`waiting_for_input`. Traced directly from source, answering the 5
task questions:

**1. Which component produced the `waiting_for_input` response?**
`extract_student_records` (`uri_core/tools/extract_student_records.py`)
is a plain, single-call regex tool - it extracts a roll number
directly from request text via `_extract_all_candidates()`; it has no
`get_next_question`/`WorkflowCapabilityRouter` registration at all
(confirmed: no match for `extract_student_records` in `workflow_
capability_router.py` except an unrelated comment). When it finds no
candidate, the free-text Brain reasoning loop itself decides to ask -
this is `_apply_clarification_pause`'s "post_execution_reevaluation"
call site (`orchestrator.py:2790-2798`), not `_save_paused_workflow`.
**This confirms REVISION v3's Outcome B was wrong for this specific
capability** - v3 answered the general question correctly (`active_
workflow` is real and does carry structured info when it's the
mechanism actually used) but did not verify that `extract_student_
records` specifically routes through it. It does not; it routes
through the ad hoc path, exactly as `M30_5A_DECISION_QUALITY_
REMEDIATION_REPORT.md` already documented for this exact example
("Find the student." → pending roll number → `session.last_goal_
attempt_history`, never `active_workflow`) - a finding Claude had
already read this session but did not re-apply carefully enough when
writing v3's decision. Corrected here, not hidden.

**2. Why wasn't `_save_paused_workflow()` called, or the session not
persisted?** Not a persistence bug - `_save_paused_workflow()` was
never supposed to be called for this capability; nothing is broken in
how sessions are saved. The real gap is exactly what v2/v3 already
fixed for the *mechanism* (`_apply_clarification_pause` can now carry
`capability_id`) but did not yet fix at the *call site*: the
`post_execution_reevaluation` call (`orchestrator.py:2790-2798`)
still passes no `capability_id` even though one is available - see #3.

**3. Minimal, bounded fix.** `attempt_history` (the local variable
already passed as `attempt_history_so_far` at this exact call site,
line 2797) already contains the just-executed attempt in the same
shape confirmed elsewhere in this file (`orchestrator.py:2882-2889`):
`{"goal": ..., "proposal": {"type": "capability", "capability":
next_capability}, "result": ...}`. Before calling `_apply_
clarification_pause` at line 2790, derive:
```python
last_capability = None
if attempt_history and isinstance(attempt_history[-1], dict):
    last_proposal = attempt_history[-1].get("proposal") or {}
    if last_proposal.get("type") == "capability":
        last_capability = last_proposal.get("capability")
```
and pass `capability_id=last_capability` into the call. This is
real, already-available data - never guessed, never fabricated,
`None` exactly as today whenever the last attempt was a workflow or
nothing ran yet (e.g. the true first-call clarification site,
`orchestrator.py` ~4633, which has no prior attempt and correctly
stays `None`). `action`/`known_inputs`/`missing_field` remain `None`/
`{}` at this site - `extract_student_records`'s own free-text regex
tool has no structured schema to draw them from, and none should be
invented.

**Scope note - flagged, not actioned:** `extract_student_records` is
not in `canonical_execution.py`'s `CANONICAL_EXECUTION_ALLOWLIST`
(`frozenset({"Gmail", "remember_fact"})`, from M30.6). Even with
`capability_id` correctly resolved and the gate returning `READY`,
canonical execution would refuse it (`capability_not_allowlisted`) -
the same deliberate, per-capability control M30.6 established for
Gmail. Expanding that allowlist is a real decision with its own
blast-radius consideration (Strict Boundary #6, `URI_ACTIVE_
MILESTONE.md` §7) - Claude is not making that decision inside this
bounded-repair plan revision. **Recommended default: prove the
mandatory organic scenario against an already-allowlisted capability**
(Gmail's `search_messages`, missing `query`, is the closest real
analog - a genuine "search my email" request with no further detail)
instead of `extract_student_records`, so the fix is proven end-to-end
without an undisclosed scope expansion. If the User specifically wants
`extract_student_records` proven canonically, that is a separate,
explicit scope decision, not bundled here.

### Mandatory live scenario (v4, revised target capability)

Same shape as v3's, but using an already-allowlisted capability so no
scope expansion is implied:

**Primary:** a real `/ask` request that plausibly triggers Gmail
`search_messages` without a usable query (e.g. "Search my email.") →
URI must genuinely ask what to search for, via the now-fixed `post_
execution_reevaluation` `_apply_clarification_pause` call (or
whichever real call site fires - Codex should inspect and report which
one, since the Brain's own behavior here is not fully predictable per
M30.4's own documented clarification-bias finding) → inspect real
session state to confirm the pause carries `capability_id: "Gmail"`
this time → second turn supplies a real search term → required:
`workflow_continuation`, `READY`, real execution, grounded response.

**Fallback if Gmail does not organically produce this exact shape:**
Codex may substitute `remember_fact` or report back to Claude with
whatever real capability the Brain does organically pause on missing a
parameter for - do not force a scripted scenario onto the live model's
actual behavior, and do not seed state to make a specific capability
name appear.

**Topic-switch regression:** unchanged from v3 - already re-proven
live by Codex, no need to repeat unless the primary fix changes
behavior there (it should not - the fix is additive to a different
call site).

---

STATE: ACCEPTED (plan only) - implementation NOT yet performed. Claude
(Architect/Planner) output per the standing AO-4 development cycle and
the already-accepted Stage 2/3 architecture
(`docs/architecture/URI_CANONICAL_AGENT_LOOP_ARCHITECTURE.md`,
`docs/plans/URI_CANONICAL_AGENT_LOOP_MIGRATION_PLAN.md` §7/§14/§16
row M30.7). Produced from direct inspection of current source, not
assumed. Sibling state file: `docs/plans/M30_7_STATE.md`.

Scope authority: exactly the migration plan's own M30.7 row (§16):
"`active_pointer` promoted to first-class, topic-change/stale-context
checks" against `orchestrator.py` (clarification-pause call sites
consolidated) and `state.py` (Session field promotion), gated by
`enable_workflow_continuation_mode`, proven via Layer 3 scenarios 4
and 11 (§14). M30.8 (canonical default cutover) is explicitly out of
scope and must not be started from this plan.

---

## 1. Current state (traced directly from source)

**`active_pointer` already exists as a read-only shadow projection,
not yet authoritative.** `turn_state.py::_project_active_pointer()`
(lines 175-256) already computes `active_pointer` from two real
sources, discovered and fixed as an M30.5A bugfix (its own docstring,
lines 176-189):
1. `session.active_workflow`/`active_workflow_question`/
   `active_workflow_required_field`/`active_workflow_status` - set
   only by a genuine `WorkflowExecutor`-based pause
   (`orchestrator.py::_save_paused_workflow`, 6 call sites: lines
   2482, 4026, 5087, 5224, 5456, plus the read sites at 3968-3974,
   4202-4231, 5093-5094, 5235-5238).
2. `session.last_goal_attempt_history`'s last entry - set by the far
   more common ad hoc Brain clarification pause
   (`orchestrator.py::_apply_clarification_pause`, one function, 3
   call sites: lines 2764, 4563, 4633) - which never touches
   `active_workflow*` at all, only appends a
   `{"proposal": {"type": "clarification", ...}}` attempt_history
   entry.

This dual-source read is correct and already tested, but `active_pointer`
is currently consumed only as **prompt context** for the Decision
Engine's shadow-mode Decision Contract (`decision_engine.py`) and as
an **offline comparison signal** (`classify_agreement()`, lines
617-673: `WORKFLOW_CONTINUATION_MISMATCH`/`_MISSED`). It is never
consulted by the deterministic gate or canonical execution to decide
whether to actually continue and execute a paused goal - that is the
literal meaning of "first-class" this milestone must deliver.

**`decision_gates.py`'s `workflow_continuation` handling is a
placeholder, not a real gate.** Lines 201-202:
```python
if mode == "workflow_continuation":
    return GateResult(outcome="READY", capability_id=None, reasons=["continuation_no_capability_named"])
```
This unconditionally returns `READY` with `capability_id=None` -
it never resolves, validates, or availability-checks the actual
capability/action the continuation is supposed to resume. Nothing
downstream can safely execute from this today.

**`canonical_execution.py`'s `EXECUTABLE_MODES` (line 79) is
`frozenset({"single_action", "multi_action"})`** -
`workflow_continuation` always falls back
(`mode_not_executable:workflow_continuation`, confirmed live in
M30.6A's own telemetry for the unrelated `clarification` mode case,
same mechanism). No canonical execution path for a resumed workflow
exists yet.

**Feature flag status:** `enable_workflow_continuation_mode` does not
yet exist as a real flag anywhere in the codebase (confirmed: only
named in the migration plan's own flag table, §12/row M30.6/M30.7).
It must be introduced by this milestone, default off, following the
exact naming/gating convention of `URI_ENABLE_DECISION_ENGINE_LIVE`/
`URI_ENABLE_DECISION_ENGINE_SHADOW` (env-var gated, checked at the
call site, never a constructor flag).

## 2. Target design

**A. Promote `active_pointer` to a first-class, authoritative Turn
State field consumed by the deterministic gate, not only the prompt.**
No new persisted field is required in `state.py`
(`SessionState`, not `Session` - the migration plan's own naming is
approximate; the real class is `uri_core/core/state.py::SessionState`,
confirmed at line 10) - `_project_active_pointer()`'s existing
dual-source computation is already correct and already covers both
pause mechanisms. "Promotion" means: `decision_gates.py` and
`canonical_execution.py` must read `turn_state.data["active_pointer"]`
as ground truth for whether a continuation is legitimate, instead of
`active_pointer` being read only for prompt construction.

**B. Give `workflow_continuation` mode a real capability/action to
resume.** (Revised v2 - depends on §2D's durable-metadata fix, since
`active_pointer.capability_id` is `None` today for the `_apply_
clarification_pause` path.) When the Decision Contract's
`mode == "workflow_continuation"`, the contract must resolve to the
paused capability - either the model names it directly (it already
has `active_pointer.capability_id` in its own context,
`decision_engine.py` line 429/437, once §2D populates that field for
real) or, if the model omits it but `active_pointer.capability_id` is
present, the gate resolves it deterministically from that field
(never guessed from free text - and never resolved at all when
`active_pointer.capability_id` is genuinely absent, e.g. an older
pre-M30.7 session or a pause path §2D's audit could not enrich: the
gate must fall back safely, same as today, not guess).
`decision_gates.py`'s `workflow_continuation` branch must then run the
*same* availability/permission/schema checks `single_action` already
runs (§6 gate structure, `decision_gates.py` lines ~234-264) against
that resolved capability/action, using the now-complete inputs (the
paused `missing_field` plus this turn's answer) - never a bare
unconditional `READY`.

**C. Extend canonical execution to actually resume.** Simplest,
lowest-risk shape (consistent with "no second execution mechanism," ,
M30.6's own accepted principle): once the gate resolves a
`workflow_continuation` proposal to a concrete
`capability`/`action`/complete `inputs`, `canonical_execution.py`
treats it exactly like a `single_action` execution for that resolved
capability - i.e., `EXECUTABLE_MODES` should include
`workflow_continuation` only when the gate has already produced a
real, non-`None` `capability_id` (the `continuation_no_capability_named`
placeholder reason must never reach execution). Do not invent a
parallel "resume" executor; reuse `MultiActionExecutor`/`ApprovalGate`
exactly as `single_action` already does.

**D. Consolidate the write/read call sites AND add durable paused-
action metadata (Revised v2 - Gap 2 fix).** The two existing pause
mechanisms (`_apply_clarification_pause` for ad hoc Brain
clarifications, `_save_paused_workflow` for genuine `WorkflowExecutor`
pauses) are each already single functions - "consolidated to one"
(migration plan §16) means the ~10 scattered direct reads of
`session.active_workflow`/`active_workflow_question`/
`active_workflow_status` inside `orchestrator.py` (lines 2485-2486,
3968-3974, 4202-4231, 5093-5094, 5235-5238) should be audited and,
where they are making the same "is there a pending interaction"
judgment `_project_active_pointer()` already makes correctly, replaced
with one shared accessor so there is exactly one place that answers
"is a workflow/clarification currently pending, and what is it" -
never two logics that could silently disagree.

Additionally, and this is the real Gap 2 fix: `_apply_clarification_
pause` (`orchestrator.py:1747`) must accept and persist optional
`capability_id`/`action`/`known_inputs`/`missing_field` parameters,
defaulting to `None`/`{}` so its 3 existing call sites (lines 2764,
4563, 4633) remain valid unmodified unless that specific call site
already has this information available at the point it decides to
pause - Codex must audit each of the 3 call sites individually for
what it already knows there and thread it through; a call site with
genuinely nothing to offer stays `None`, exactly as today, never
fabricated. These fields get appended into the existing
`attempt_history` proposal dict (`{"type": "clarification", "question":
question, "capability_id": ..., "action": ..., "known_inputs": ...,
"missing_field": ...}` - additive keys only). `turn_state.py`'s
attempt_history-sourced `active_pointer` branch (lines 227-256) is
updated to read these new keys instead of hardcoding `None` - when an
older attempt_history entry (pre-M30.7, or from a call site that had
nothing to offer) lacks them, behavior is unchanged from today
(`None`, safe fallback). Codex should determine the least-risky
concrete refactor for the read-side consolidation (e.g. a small
`_pending_interaction(session)` helper reusing `turn_state._project_
active_pointer`'s logic) rather than rewriting `_apply_clarification_
pause`/`_save_paused_workflow`'s own existing, already-tested pause
behavior, which must stay byte-for-byte unchanged except for the new
additive metadata fields.

**E. Topic-change / stale-context handling (Revised v2 - corrected).**
v1 incorrectly proposed a separate deterministic pre-model
"goal-continuity comparison" reusing `classify_agreement()`. Per
`M30_5D_TEMPORARY_CONTEXT_INTENT_SHIFT_REPORT.md` §2-3 (re-verified
this revision), continuation-vs-new-intent is, by explicit and
deliberate design, the **model's own judgment** inside the Decision
Contract's 1a-1d sequence (`decision_engine.py`'s
`DECISION_CONTRACT_SYSTEM_PROMPT`) - not a function to reinvent, and
not something to route around with a separate deterministic check,
consistent with this project's standing canonical-interaction-loop
principle that URI must never narrow the Brain's cognition into a
rigid, predefined pre-model check to force conformance. `classify_
agreement()` remains what it always was: an offline, post-hoc shadow-
comparison label (M30.4 evidence gathering), never a live gate.

What §2F below actually needs from this is narrower: not a new
comparison function, but the *right point* in the request flow for the
model's already-correct 1a-1d judgment to run before the legacy
unconditional resume can act on stale grounds (see §2F). Expiry: reuse
whatever session-expiry convention already bounds
`session.active_workflow`'s lifetime today (confirm the exact
mechanism during implementation - do not invent a new TTL field if an
existing one already bounds session state).

**F. `/ask` entry-point precedence for a pending workflow (New in v2 -
Gap 1 fix, requires `server.py` write-scope expansion).** Today,
`server.py:1149` always calls `process_user_input()` (whose own
`orchestrator.py:4223-4240` unconditionally resumes any pending
`active_workflow`) before canonical execution ever runs (line 1199) -
so canonical continuation logic can never even see, let alone
correctly judge, a pending-workflow turn. The fix is narrowly scoped
to the one case that matters, leaving every other `/ask` case (no
pending workflow) in today's exact, already-verified M30.6 order:

1. In `server.py`'s `/ask` handler, before calling
   `context.orchestrator.process_user_input(...)`, add a new guarded
   block (mirroring the exact isolation discipline - `try`/`except
   Exception: pass` - of the two existing M30.3/M30.6 guarded blocks)
   that runs **only when `enable_workflow_continuation_mode` is on
   AND** `context.orchestrator.session_manager.get_session(session_id)`
   shows a pending workflow (`session.active_workflow is not None and
   session.active_workflow_status == "waiting_for_input"`).
2. In that case, call canonical execution (`run_canonical_for_ask()`
   or a small continuation-specific wrapper around it in
   `canonical_execution.py` - Codex's choice, reusing the existing
   function rather than forking it if the shapes align) *before*
   `process_user_input()`. This is where the model's real 1a-1d
   judgment (§2E) actually runs, now early enough to matter.
   - If it resolves `mode == "workflow_continuation"` and the gate (§2B)
     is `READY`: execute now (§2C), return that result -
     `process_user_input()` is not called this turn (no double
     execution, no second mechanism).
   - If it resolves anything else (a genuine new goal, `conversation`,
     etc. - the model judged this is NOT a continuation): the pending
     workflow is stale by the model's own authoritative judgment -
     clear it (reuse the existing, unchanged `_clear_active_workflow`)
     so the immediately-following `process_user_input()` call does not
     also blindly resume it, then fall through to `process_user_input()`
     exactly as today so the message is processed fresh.
   - If canonical falls back for any other reason (flag considerations
     aside - gate not READY, invalid contract, capability not
     allowlisted, model unreachable): do nothing; fall through to
     `process_user_input()` unchanged - today's exact resume behavior
     is the safe default whenever canonical cannot make a confident
     call.
3. With the flag off, or with no pending workflow, this new block is
   never reached (or is a no-op) - `/ask`'s behavior is byte-for-byte
   identical to pre-M30.7 in both cases, by construction, matching
   every prior milestone's own flag-off discipline.

This is the one place this milestone's write scope must expand beyond
`docs/governance/URI_ACTIVE_MILESTONE.md` §4's current list to include
`uri_core/app/server.py` (narrowly: the `/ask` handler's pending-
workflow branch only) - Claude is recommending this scope expansion
here; Antigravity records the actual scope-list update per the
Write Ownership rule, not Claude.

## 3. Files expected to change (Revised v2)

**Modified:**
- `uri_core/app/server.py` - **new in v2** (§2F): a new guarded block
  in `/ask`, before `process_user_input()`, for the pending-workflow
  case only. Every other `/ask` case is untouched.
- `uri_core/core/decision_gates.py` - replace the
  `workflow_continuation` placeholder (lines 201-202) with a real
  gate that resolves the paused capability/action (from `active_
  pointer.capability_id`, now populated per §2D) and runs the same
  checks `single_action` runs.
- `uri_core/core/canonical_execution.py` - `EXECUTABLE_MODES`
  extended to admit a gate-resolved `workflow_continuation` proposal;
  execution reuses the existing `single_action` execution path, not a
  new one; **new in v2** - a continuation-specific entry point/wrapper
  callable from `server.py`'s new §2F block, if the existing
  `run_canonical_for_ask()` shape doesn't already fit called earlier.
- `uri_core/core/orchestrator.py` - **revised in v2** (§2D):
  `_apply_clarification_pause` gains optional `capability_id`/
  `action`/`known_inputs`/`missing_field` parameters, threaded through
  from each of its 3 call sites where already known (audited
  individually, never fabricated); consolidate the scattered
  `active_workflow*` read call sites behind one shared accessor.
- `uri_core/core/turn_state.py` - **revised in v2** (was "none
  anticipated" in v1): `_project_active_pointer()`'s attempt_history
  branch (lines 227-256) reads the new `capability_id`/`action`/
  `missing_field` proposal keys instead of hardcoding `None`,
  falling back to `None` exactly as today when absent.
- A new focused test module (naming at Codex's discretion, following
  this repo's `test_decision_gates.py`/`test_canonical_execution.py`
  convention) covering: the real `workflow_continuation` gate/
  execution path with real durable metadata (Scenario 4), the
  precedence fix's three branches - continue/clear-and-fresh/fallback
  (Scenario 11, §2F) - and flag-off byte-for-byte equivalence.

**Not expected to change:** `state.py`/`SessionState` (no new
persisted field - §2A), `_apply_clarification_pause`'s/`_save_paused_
workflow`'s existing pause behavior for callers that supply no new
metadata (byte-for-byte unchanged - §2D), `multi_action_dispatch.py`/
`executor.py` (reused unchanged execution mechanics, §2C),
`capability_directory.py`.

## 4. Feature flag

`enable_workflow_continuation_mode` (env var, e.g.
`URI_ENABLE_WORKFLOW_CONTINUATION_MODE`, naming convention mirrored
from `URI_ENABLE_DECISION_ENGINE_LIVE`). **Default: unset/off.**
Per the migration plan's own §12 table: "off until Layer 3 tests for
scenario 4/11 pass." With the flag off, `decision_gates.py`/
`canonical_execution.py` behave exactly as today (placeholder
`READY`/`capability_id=None`, always falls back) - zero behavior
change is possible while off, by construction, mirroring M30.3's own
shadow-mode safety discipline.

## 5. Mandatory live verification (Codex + real backend, not fabricated)

Both of the migration plan's own named scenarios (§14 items 4 and 11),
live, with the flag on:

**Scenario 4:** "Find the student." (missing `roll_number`) ->
`clarification`/`missing_parameter`, `active_pointer` set with
`missing_field="roll_number"` -> "B250012CS." -> continuation match
confirms this answers the pending field -> `mode=workflow_continuation`
-> gate resolves the original capability -> real execution with the
now-complete input -> grounded response naming the real result.

**Scenario 11:** a pending workflow exists (`active_pointer` set), then
the user sends a message that is clearly a different goal -> the
deterministic topic-change check (§2E) clears `active_pointer` -> the
new message is treated as fresh (`single_action`/`multi_action`/
`conversation` as appropriate) - newest intent wins, never forced into
the stale continuation.

Required evidence chain for both (mirroring M30.6A's own acceptance
discipline): real `/ask` HTTP calls, real authenticated principal
(learned from M30.6A's own audit - a directly-constructed
executor/bypassed principal does NOT satisfy this bar), real
canonical telemetry (`canonical_execution_log.jsonl`) showing the
real `gate_outcome`/`canonical_execution_result` for each turn, cross-
checked against independently-inspected artifacts (session state,
telemetry, usage logs) - not merely asserted in a completion report.

## 6. Security / safety constraints

- Continuation must never be honored on a stale or expired
  `active_pointer` (§2E) - an unmeasured false-positive rate was
  explicitly flagged as a real risk in the migration plan's own risk
  register (§ "active_pointer continuation false-positives"); this
  milestone's Layer 3 evidence is what that risk register named as
  the resolution.
- The deterministic gate, not the Brain's own mode claim, remains
  authoritative for whether `workflow_continuation` executes -
  identical discipline to M30.6's `decide_fallback_reason()` never
  trusting the contract's own `requires_approval` claim.
- No new credential, token, or permission surface is introduced by
  this milestone - `workflow_continuation` execution reuses the exact
  same `CapabilityResolver`/`CapabilityGrantsStore`/`ApprovalGate`
  path `single_action` already goes through (§2C) with no new
  privilege.

## 7. Regression requirements

Preserve unchanged: `test_decision_engine.py` (42, including every
M30.5D continuation/topic-switch/cancellation test - the "latest user
intent wins" rule must not regress), `test_decision_gates.py` (21),
`test_turn_state.py` (18), `test_canonical_execution.py` (29),
`test_multi_action_capabilities.py` (14), M30.6A's own
`test_gmail_connection_truth.py` (7) plus the wider Gmail-adjacent set
this session already verified clean (133/133). Flag-off behavior must
be byte-for-byte identical to pre-M30.7 (§4). No new failures beyond
the session's known 8-failure baseline (Drive `AttributeError`, M20
resilience tests, orchestrator line-count - unrelated, not to be
fixed under this milestone).

## 8. Rollback instructions

Unset `enable_workflow_continuation_mode` (or never set it) - the
entire `workflow_continuation` execution path is inert;
`decision_gates.py`/`canonical_execution.py` revert to today's
placeholder/fallback behavior exactly. To fully revert: remove the
`workflow_continuation` branch additions in `decision_gates.py` and
`canonical_execution.py`'s `EXECUTABLE_MODES` extension; remove the
new shared `active_pointer`-read accessor in `orchestrator.py` if
introduced (the two underlying pause mechanisms are untouched and
need no reversal); delete the new focused test module. No data
migration - no new persisted field was added (§2A/§3).

## 9. Process note

Per the standing AO-4 development cycle and the User's explicit
2026-09-13 approval of M30.7 (recorded in
`docs/governance/URI_ACTIVE_MILESTONE.md` §6a), this plan is marked
ACCEPTED under the standing auto-approval rule (`ORCHESTRATION.md`
§1.5) - routine engineering planning within an already User-approved
milestone, not a constitutional-boundary change. Claude does not
implement this milestone itself; per
`docs/governance/URI_AGENT_RELAY.md`'s current handoff, this plan and
`docs/plans/M30_7_STATE.md` are handed back to Antigravity for routing
to Codex. M30.8 remains explicitly out of scope and NOT authorized -
nothing in this plan should be read as starting or presupposing it.

---

Stopping here. M30.7 plan is ready for Antigravity to route to Codex.
M30.8 is not started and not authorized.
