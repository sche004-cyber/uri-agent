# M30.7 - Claude Independent Post-Implementation Audit

Audited directly from source (`server.py`, `orchestrator.py`,
`decision_gates.py`, `canonical_execution.py`, `turn_state.py`,
`multi_action_dispatch.py` all read in full or by targeted diff/grep),
real telemetry (`canonical_execution_log.jsonl`), and an independent
re-run of the test suite - not from Codex's report alone.

## Verdict: **ACCEPT WITH FOLLOW-UP**

---

## 1. Plan (REVISION v2) compliance

**§2F (precedence fix, Gap 1) - correctly implemented.** `git diff
uri_core/app/server.py` confirms exactly the design: a new guarded
`try/except Exception: pass` block before `process_user_input()`,
active only when `URI_ENABLE_WORKFLOW_CONTINUATION_MODE == "1"` and
`session.active_workflow is not None and session.active_workflow_status
== "waiting_for_input"`. It calls `run_canonical_for_ask(...,
decision_observer=_observe_decision)` (a new optional observer
parameter, not a forked function - a cleaner reuse than the plan's own
"wrapper" suggestion). Three real outcomes, all matching plan §2F
exactly: (1) `mode == "workflow_continuation"` and `gate_outcome ==
"READY"` -> use the early result, set `early_executed = True`, skip
the later M30.6 hook (`if decision_engine_live_enabled() and not
early_executed`) - no double execution; (2) `mode` present and not
`workflow_continuation` -> `context.orchestrator._clear_active_workflow
(session)`, fall through to `process_user_input()` fresh; (3) anything
else (exception, no observed mode) -> silent fall-through, today's
exact legacy resume behavior. Flag off or no pending workflow -> block
never runs, `/ask` is byte-for-byte pre-M30.7 - confirmed structurally,
not just asserted.

**§2B/§2C (gate resolution + execution, Gap 1 continued) - correctly
implemented.** `decision_gates.py` lines 177-208: a real
`workflow_continuation` branch (only when
`workflow_continuation_mode_enabled()`) resolves `capability_id` from
the contract or `active_pointer.capability_id` (never free text),
refuses `INVALID_PROPOSAL` when `active_pointer.kind == "none"` or no
capability can be resolved (never guesses), pulls `known_inputs`/
`missing_field` from `active_pointer`, then falls through into the
*same* general capability-resolution/permission/schema-checking code
`single_action` already uses (lines 212+) - exactly the "same checks"
discipline the plan required. The old placeholder (`READY`/
`capability_id=None`/`continuation_no_capability_named`, now lines
251-252) survives untouched as the flag-off/unresolved fallback -
confirmed this is still reachable and correct for that case.
`canonical_execution.py`'s `EXECUTABLE_MODES` now includes
`workflow_continuation` unconditionally, but `decide_fallback_reason()`
has an explicit separate `workflow_continuation_mode_enabled()` check
(line 188-189) before admitting it - a different but equally safe
implementation of the plan's intent (membership-gated by capability
resolution, in the plan's own wording; flag-gated by an explicit check,
in Codex's actual implementation) - not a deviation worth objecting to.

**§2D (durable metadata, Gap 2) - correctly implemented as a
mechanism, but currently unreachable from any real trigger - see §3
below, this is the one real finding.** `_apply_clarification_pause`
gained `capability_id`/`action`/`known_inputs`/`missing_field`
parameters (all optional, defaulting to `None`/`{}`), threaded into
the `attempt_history` proposal dict additively.
`turn_state.py::_project_active_pointer()`'s attempt_history branch
was updated to read these instead of hardcoding `None` (confirmed via
`test_workflow_continuation.py::
test_attempt_history_projection_preserves_paused_action_metadata`,
which passes). The 3 real call sites were individually inspected by
Claude, not merely trusted: the one at ~line 4633 (`initial_clarification`)
is confirmed, directly in its own surrounding comment, to fire at a
point where "action and workflow both null" - i.e., genuinely no
capability/action exists yet to thread through. Codex's own claim ("no
metadata was fabricated") is accurate, not an excuse.

**Consolidation (§2D, read side) - partial, acceptable.** Only the two
read sites directly gating recovery/resume
(`orchestrator.py` ~4225/~4247) were replaced with the new
`_pending_interaction(session)` accessor; the other ad hoc
`active_workflow`/`active_workflow_question` reads named in v1's plan
(~2485, ~3968, ~5093, ~5235) were left untouched. This is sufficient
for M30.7's own correctness (those two are the only sites that matter
for the precedence fix), and the plan explicitly left the exact scope
of this refactor to Codex's judgment - not a defect, just narrower
than v1's aspirational full sweep.

## 2. Security assessment

No new credential, token, or permission surface. `workflow_continuation`
execution reuses the identical `CapabilityResolver`/
`CapabilityGrantsStore`/`ApprovalGate`/`MultiActionExecutor` path
`single_action` already goes through - confirmed by reading
`decision_gates.py`'s shared downstream code (§1 above) and
`canonical_execution.py`'s reuse of the existing execution branch.
`_clear_active_workflow` is an existing, unchanged, already-tested
method - reused, not reimplemented. No token/credential value appears
in any new code path, telemetry field, or the completion report.

## 3. Live-evidence assessment - the one real finding

**Gap 1 (Scenario 11) - genuinely, fully proven live.** Independently
cross-checked `uri_workspace/canonical_execution_log.jsonl` against
the report: session `m30-7-live-s11-20260913-a` has exactly two real
telemetry records, in the order the code structurally produces them -
first `mode: unsupported`/`gate_outcome: INVALID_PROPOSAL` (the new
early precedence-check call, judging non-continuation), second
`mode: clarification`/`fallback_reason: capability_not_allowlisted`
(the pre-existing M30.6 hook running afterward on the same turn, since
`early_executed` stayed `False`). This is exactly what `server.py`'s
diff says must happen, and it happened for real. The report's own
claim that persisted session state showed `active_workflow: null`
afterward is consistent with this trace and not contradicted by
anything found.

**Gap 2 (Scenario 4) - the resume half is genuinely proven; the
create/pause half is not.** Telemetry for the claimed session
(`m30-7-live-s4-20260913-c`) has exactly **one** record: the
continuation turn itself (`workflow_continuation`/`Gmail`/
`search_messages`/`READY`/`success`/real evidence/grounded response -
this part is real and matches the report exactly). There is **no**
telemetry record, for that session or any related one, showing a real
prior `/ask` turn that itself decided to pause with
`capability=Gmail`/`action=search_messages`/`missing_field=query`. The
report's own phrasing - "a pending interaction was set up" - is
accurate but, combined with the missing setup-turn telemetry and the
confirmed fact that no `_apply_clarification_pause` call site
currently has this information available (§1), makes it near-certain
the precondition state was written directly into session storage by
the verification script rather than produced by a real, organic first
turn. **This is not a fabricated result** - the continuation/execution
half is completely real, live, and correctly proven - but it means
the *originally specified* Scenario 4 (a natural two-turn conversation
in which the Brain itself decides to pause, and that pause durably
carries the resolvable capability) has not yet been observed to occur
end-to-end in this codebase, because nothing in production currently
populates the metadata `_apply_clarification_pause` is now capable of
carrying. The fix is real and correct; it is currently dead code from
the perspective of any live conversation.

This mirrors, in miniature, the exact class of gap Claude's own
M30.6A audit flagged for a bypassed principal - a live proof that
demonstrates the downstream mechanism correctly, using a precondition
that the current system cannot yet produce on its own.

## 4. Regression audit - independently re-run, not trusted from the report

```text
.venv\Scripts\python.exe -m pytest test_workflow_continuation.py \
  test_decision_engine.py test_decision_gates.py test_turn_state.py \
  test_canonical_execution.py test_multi_action_capabilities.py \
  test_gmail_connection_truth.py -q
135 passed in 18.48s

.venv\Scripts\python.exe -m pytest test_server_ask_narrative.py \
  test_capability_planner.py test_capability_directory.py -q
36 passed in 21.88s
```

All passing, including `test_server_ask_narrative.py` (the direct
regression surface for the modified `/ask` handler). The report's own
figure (123 via `python -m unittest`) differs numerically from this
session's 135 via `pytest` over the same seven modules - almost
certainly a discovery/counting difference between the two runners
(unittest vs. pytest), not a real discrepancy: both independent runs
show zero failures. Full 1710-test baseline not re-run this audit
(out of scope/time, and this session's own targeted set already covers
every file M30.7 touched); nothing found here suggests it would surface
anything new.

## 5. Whether M30.8 is safe to begin

**Not yet - and Claude does not decide this alone regardless.**
M30.7's core mechanism (precedence fix, gate resolution, execution
reuse, flag-off safety) is real, correct, safely defaulted-off, and
covered by both unit tests and genuine live telemetry for Scenario 11
in full and for Scenario 4's execution half. The recommended follow-up
before treating M30.7 as fully, organically proven: identify or wire a
real production trigger that populates `_apply_clarification_pause`'s
new metadata fields for at least one genuine conversational path (or
confirm and document that the *actual* real-world continuation trigger
for structured capabilities is the pre-existing `active_workflow`-based
pause mechanism, not `_apply_clarification_pause` at all, in which case
Gap 2's fix should be understood as forward-looking/defensive rather
than closing an active gap) - then re-run Scenario 4 driven by a real
first turn, not seeded state. This is a bounded follow-up, not a
blocker to using M30.7's flag-gated mechanism as built; M30.8
authorization is the User's decision in any case, not Claude's.

## 6. Verdict rationale

**ACCEPT WITH FOLLOW-UP**, not `REPAIR REQUIRED`: nothing found is
unsafe, incorrect, or regressive - the implementation matches the
accepted plan closely, defaults are safe, execution reuses existing
authority-checked paths, and every claim in the completion report that
could be independently checked (telemetry, source, tests) checked out
as either fully accurate (Scenario 11, Scenario 4's execution half) or
honestly, if incompletely, described (Scenario 4's precondition,
"set up" rather than claimed as organic). The one real gap is a
disclosed evidence-completeness issue, not a functional defect.

---

## Addendum (REVISION v4 audit, 2026-09-13)

### Verdict: **ACCEPT WITH FOLLOW-UP** (unchanged category, gap narrowed)

**7. v4 source fix - correctly implemented, verified directly against
code, not the report.** `orchestrator.py:2790-2805` (`post_execution_
reevaluation` call site):

```python
last_capability = None
if attempt_history and isinstance(attempt_history[-1], dict):
    last_proposal = attempt_history[-1].get("proposal") or {}
    if last_proposal.get("type") == "capability":
        last_capability = last_proposal.get("capability")

self._apply_clarification_pause(
    ..., capability_id=last_capability,
)
```

Exactly matches plan REVISION v4's spec - real data
(`attempt_history[-1]`, the same shape independently confirmed
elsewhere in the file at line 2882-2889), never guessed, `None`
exactly as before whenever the last attempt wasn't a capability
proposal. The OTHER clarification call site
(`orchestrator.py:4654-4669`, code name `stage="initial_reasoning"` -
the report/task text calls it `"initial_clarification"`, a label
mismatch worth a one-word doc fix, not a defect) correctly still
passes no `capability_id`, since nothing has been proposed yet at that
point - untouched, as it should be.

**8. Regression - independently re-run.**
```text
.venv\Scripts\python.exe -m pytest test_workflow_continuation.py \
  test_decision_engine.py test_decision_gates.py test_turn_state.py \
  test_canonical_execution.py test_multi_action_capabilities.py \
  test_gmail_connection_truth.py -q
137 passed in 11.70s
```
Zero failures (report's own count, 125 via `unittest`, differs from
this session's 137 via `pytest` for the same reason noted in §4 above
- a runner-discovery difference, not a real discrepancy).

**9. Live-evidence assessment - telemetry independently cross-checked,
confirms the report honestly.** `canonical_execution_log.jsonl`'s
newest records (`m30-7-v4-gmail-organic-*`, `m30-7-v4-organic-gmail-*`,
`m30-7-v4-organic-thread-*`) all show `canonical_mode: "clarification"`,
`selected_capability: null` - consistent with the "Search my email."
turns pausing at `initial_reasoning`, not `post_execution_
reevaluation`, exactly as the report states. Four separate real live
attempts now (v3's `extract_student_records`/roll-number attempt, and
three v4 Gmail phrasings across two sessions) have all landed on the
same first-call clarification site rather than the one this milestone
actually repaired. This is a consistent pattern, not a fluke, and is
directly explained by M30.4's own documented finding (this model
defaults to asking a clarifying question upfront in the large majority
of ambiguous cases, rather than attempting a capability first and
re-evaluating afterward) - the `post_execution_reevaluation` path
requires the model to try something first, which this model rarely
does for an information-poor request.

**One incidental, pre-existing, non-blocking observation (not a v4
regression):** `decide_fallback_reason()` (`canonical_execution.py:
184-191`) checks `is_allowlisted(capability_id)` before checking mode
executability, so a `clarification`/`conversation` decision with no
capability at all is reported as `fallback_reason: "capability_not_
allowlisted"` rather than `"mode_not_executable:<mode>"` - technically
imprecise telemetry labeling, unchanged since M30.6, not introduced or
worsened by M30.7. Not worth a repair on its own.

**10. Verdict rationale, updated.** The mechanism this milestone set
out to build - a real, gate-consumed, executed `workflow_continuation`
path, safely gated, with durable pause metadata threaded from every
real source that can supply it without guessing - is complete,
correct, unit-tested, and has *most* of its load-bearing parts already
proven live (Scenario 11 fully; Scenario 4's resolve-and-execute half
fully, per the original audit). The one remaining gap is narrower than
before REVISION v4 (the specific `post_execution_reevaluation` call
site's threading is now source-correct and unit-tested) but still not
organically triggered live, after four honest, non-seeded attempts.

**Recommendation - stop the open-ended retry loop, decide explicitly:**
further blind rephrasing of "search my email"-style prompts is
unlikely to converge, since the blocker is the model's own documented
clarification-first bias (M30.4), not anything in this milestone's
code. Two real options, either acceptable, neither requiring more
guessing:
- **(a) Accept as sufficiently proven.** The mechanism is unit-tested
  and every other part of the continuation pipeline it depends on is
  independently, live-proven (via the earlier Scenario 4/11 rounds).
  Document the organic-trigger gap for `post_execution_reevaluation`
  specifically as a known, tracked, non-blocking residual - not
  fabricated as closed, but not gating further progress either.
- **(b) One deliberately-shaped live attempt**, not another guess: a
  request that gives the model just enough to *attempt* a real Gmail
  action first (e.g. naming a specific but unresolvable sender/subject
  so a `search_messages`/`read_message` call is plausible and can
  return empty/inconclusive), so the model's own post-execution
  re-evaluation - not its first-call instinct - is what asks the
  follow-up question. This is still organic (real model, real
  execution, no seeding) but targets the actual code branch instead of
  hoping to land on it.

Both are legitimate; picking between them is a scope/patience
decision, not an architectural one - Claude does not decide it
unilaterally here.

**11. Whether M30.8 is safe to begin:** unchanged from the original
audit - not yet, and not Claude's decision regardless of verdict.

---

Stopping here per governing instruction. No repair implemented, no
production code written by Claude. M30.8 remains NOT AUTHORIZED and is
not started.
