# M30.5C - Pending Interaction Boundary & Evaluation Cleanup Report

Status: Stage 4 (IMPLEMENTATION), milestone M30.5C. Shadow-only. No
canonical execution authority. No `/ask` routing change.
`server.py`/`orchestrator.py` diffs confirmed unchanged since their
last-recorded milestone (M30.3/pre-existing respectively) via `git
diff --stat` - nothing in this milestone touched either file.

---

## 1. Topic-switch/cancellation root cause

The M30.5B prompt only ever asked "does this message plausibly answer
the pending question" - a single yes/no test. A cancellation ("Never
mind.") and a new, unrelated intent ("Actually, check my unread
email.") both correctly fail that lone test in the sense that they
don't look like an answer, but the prompt had no THIRD outcome for
"this message isn't an answer, but active_pointer.kind still isn't
none" - so the model's only path back to a normal mode required first
admitting `active_pointer.kind` was somehow irrelevant, which nothing
told it how to do. In practice it defaulted to `workflow_continuation`
anyway, on weak evidence, simply because a pending question existed.

## 2. Boundary solution (structural, not phrase-specific)

`DECISION_CONTRACT_SYSTEM_PROMPT`'s checklist step 1 was rewritten to
require a three-way judgment whenever `active_pointer.kind` is not
`"none"`, before mode is picked at all:

- **ANSWER** - the message plausibly supplies the missing value:
  short/concrete, shaped like `active_pointer.expected_type` when
  given, or names one of the pending question's own offered choices.
- **CANCEL** - the message's role is to end or withdraw the pending
  request, not to supply a value and not to start a new goal -
  "regardless of the exact words used for that" (no keyword list).
- **NEW_INTENT** - the message plausibly starts a different goal that
  a *different* capability summary fits better than the pending
  question's own `originating_goal` does.

`ANSWER` -> `workflow_continuation` (capability set in the same step,
unchanged from M30.5B). `CANCEL` -> `conversation`. `NEW_INTENT` ->
`active_pointer` is treated as no longer relevant, and mode is decided
from question 2 onward exactly as if nothing were pending. One generic
worked example was added for each of the CANCEL and NEW_INTENT
branches (using phrasing never reused in the golden set) to anchor the
distinction, mirroring the M30.5B "foundational capability" worked
example technique.

**Live-verified against the M30.5C spec's own 5 boundary sentences:**

| Pending question | Message | Expected | Result |
|---|---|---|---|
| "What is the student's roll number?" | "B250012CS" | continuation, `extract_student_records` | **correct** |
| "What is the student's roll number?" | "Never mind." | conversation | **correct** (real fix) |
| "What is the student's roll number?" | "Actually, check my unread email." | new intent, `Gmail` | capability correct, mode still `workflow_continuation` (**not fixed**) |
| "Which email do you mean?" | "The SBI one." | continuation, `Gmail` | **correct** |
| "Which email do you mean?" | "Forget it, prepare an office note." | new intent, `draft_institutional_note` | capability correct, mode still `workflow_continuation` (**not fixed**) |

**CANCEL is solved: 3/3 across both pending-subject variants**
(`boundary_cancel_roll_number`, `pending_email_choice_cancellation`,
plus the isolated spec sentence above) - a real, generalized fix, not
tuned to one exact sentence (the two golden cases use different
pending subjects and different cancellation wording).

**NEW_INTENT is NOT solved.** Two independent prompt iterations were
tried this milestone:
1. Inline capability-recovery + 3-way framing (this section's version)
   - CANCEL fixed, NEW_INTENT still misclassified as continuation in
     both spec examples.
2. A stricter variant requiring the model to first restate the pending
   question's literal subject before judging the relationship - this
   was **strictly worse** (it broke the already-working CANCEL and
   `boundary_answer_email_choice` cases without fixing NEW_INTENT) and
   was reverted immediately after being measured; this is disclosed
   rather than hidden, per standing practice.

The model consistently gets the *capability* right for NEW_INTENT
cases (it correctly identifies `Gmail`/`draft_institutional_note` as
the real target of the new request) while still labeling the *mode*
`workflow_continuation` - the mode label appears to be anchored on
"a pending question exists" more strongly than the actual boundary
reasoning can override, at least for this local model. This is a
genuine, disclosed limitation, not a hardcoding gap: the fix attempted
was fully generic (structural roles, generic worked examples, no
sentence-specific routing) and still did not close it.

## 3. multi_action robustness findings

Tested 5 new phrasings (spec section 3) beyond the two previously-
passing mandated sentences:

| Phrasing | Result |
|---|---|
| "How many unread emails are there, and which matter?" | multi_action, correct |
| "Check unread mail and tell me what is important." | single_action - **wrong** |
| "Find the latest insurance message, read it, and inspect the attachment." | multi_action, correct |
| "Open the newest SBI email and check its PDF." | multi_action, correct |
| "Look at unread messages, then summarise the important ones." | multi_action, correct |

**4/5 new phrasings correct.** Combined with the two prior golden
cases (`gmail_multi_1` correct, `gmail_multi_2` still wrong) and the
two originally-mandated M30.5B sentences (both correct), the
multi_action group across all 7 distinct phrasings tested to date is
**5/7 (0.714)**. The two failures share a structural pattern: a
compressed "`<action>` and tell me `<qualifier>`" phrasing
("Check unread mail and tell me what is important.",
"Find my latest insurance email and tell me if it has an
attachment.") is read as one action with a qualifier, not two actions
- versus an explicit list ("read it, and check its attachment") or a
"which/what" question form, both of which correctly parse as two real
sub-asks. This is a real, repeatable phrasing sensitivity, not noise -
disclosed as a residual gap; no further prompt change was attempted
this milestone given the improvement already achieved (0/2 in M30.5B's
own mandated pair -> 5/7 across the full varied set).

## 4. Hallucinated-capability root cause and fix

Root cause: the prompt described `capability_action_affordances` as a
map of `{capability_id: {action_name: description}}` but never told
the model these were two different vocabularies - for "Check the
attachment on that message." the model picked the *action* name
`read_attachment` and returned it as `capability`, which
`_validate_contract()`'s `unknown_capability` check correctly rejected
(status `invalid`), but the underlying cause was a genuine prompt
ambiguity, not a stale alias or a comparison-fixture artifact.

Fix (generic, no blacklist): added one sentence to the `capability`
field's own definition - "never use an action name (from `actions` or
from `capability_action_affordances`'s inner keys) as a capability -
those are two different vocabularies; a capability_id never matches
one of its own action names."

Re-tested the exact failing case 3 times after the fix: **3/3
consistently returns `capability: "Gmail"`, `actions: [{"name":
"read_attachment", ...}]`, `status: "ok"`** - the hallucination is
gone. Across both full evaluation passes this milestone (40-case and
50-case, 90 total case-runs), `invalid_capability_rate = 0.0` in both.

## 5. Golden-set cleanup

`PENDING_ROLL_NUMBER` (in `scripts/m30_4_decision_quality_analysis.py`,
shared by every downstream eval script) was corrected in place - not
removed, since its case ids (`continue_1`/`continue_2`) and their
expected outcomes are unchanged and still used by every pass. Its
`active_pointer` dict previously had only `kind`/`question`/
`missing_field`/`reference` (a pre-M30.5A shape); it now carries the
same enriched fields `turn_state.py`'s real `_project_active_pointer()`
actually produces for this exact scenario: `originating_goal: "Find
the student."`, `capability_id: None`, `expected_type: "identifier"`,
etc. **No expected mode/capability was changed** - only the input
fixture's shape, to match reality.

Effect, measured directly: `continue_1`/`continue_2` now correctly
recover `capability: "extract_student_records"` (previously
`recall_memory` or `None`, depending on the pass) purely from this
fixture fix - the M30.5B/M30.5C capability-recovery logic was already
correct, it simply had nothing usable to recover from before.

## 6. Full before/after metrics (16 categories, never combined)

Two passes, same M30.5C pipeline, live model (local qwen3:14b, no
frontier provider configured - same disclosed limitation as every
prior report):

| Metric | 40-case (M30.5B set, fixture corrected) | 50-case (+5 boundary +5 multi_action phrasing) |
|---|---|---|
| candidate Recall@3 | 0.889 | 0.917 |
| candidate Recall@5 | 0.963 | 0.972 |
| mode accuracy | 0.825 | 0.800 |
| capability accuracy | 0.925 | 0.940 |
| workflow_continuation mode accuracy | 0.800 | 0.857 |
| workflow_continuation capability accuracy | 0.600 | 0.714 |
| topic-switch accuracy | n/a (0 cases) | **0.000** |
| cancellation accuracy | n/a (0 cases) | **1.000** |
| multi_action accuracy | 0.500 | 0.714 |
| memory-disclosure accuracy | 1.000 | 1.000 |
| conversation/no-tool accuracy | 1.000 | 1.000 |
| unsupported accuracy | 1.000 | 1.000 |
| invalid-capability rate | 0.000 | 0.000 |
| invalid-contract rate | 0.000 | 0.000 |
| avg prompt size (chars) | 9457 | 9473 |
| avg latency (s) | 3.63 | 3.78 |

Direct delta from the golden-set fixture fix alone (identical 40
cases, only `PENDING_ROLL_NUMBER` corrected): mode accuracy 0.800
(M30.5B, stale fixture) -> **0.825** (M30.5C, corrected fixture).

**Disclosed measurement caveat:** the local model's output is not
fully deterministic. Two cases that failed in the 50-case batch run
(`continuation_real_session`, `continuation_email_choice_capability_
recovery`) were immediately re-run in isolation, identical input, 3
times each - both came back **correct 3/3** outside the batch. This
means the true reliability of `workflow_continuation_capability_
accuracy` is better than the single-pass 0.714 suggests, but a
single-pass automated run does carry real sampling noise at the
margins; a future milestone should consider majority-vote-over-N-
samples for the noisier metrics rather than trusting one pass exactly.
The `multi_action` phrasing failures (Section 3) and the NEW_INTENT
failures (Section 2), by contrast, were re-checked directly and are
**repeatable**, not noise.

Raw results: `scripts/m30_5c_results.json`.

## 7. Remaining failures (disclosed, not solved this milestone)

1. **NEW_INTENT during a pending interaction is still misclassified as
   `workflow_continuation`** (Section 2) - two independent, fully
   generic prompt attempts did not close this; the capability is
   correctly identified even when the mode is wrong.
2. **multi_action phrasing sensitivity persists** for the "`<action>`
   and tell me `<qualifier>`" compressed form (2/7 tested phrasings).
3. `gmail_draft_approval` still resolves to `single_action` instead of
   `approval_required` - a pre-existing gap, out of this milestone's
   explicit scope, unchanged.
4. `gmail_attachment_chain` and `continuation_topic_switch_new_intent`
   remain `false_continuation` - both are instances of the Section 2
   NEW_INTENT gap (recent-conversation-driven and active_pointer-
   driven respectively), not new failures.
5. Nine `under_tooling` cases (mostly memory-disclosure): mode and
   capability both correct, `actions` list empty - unchanged from
   M30.5B, out of this milestone's explicit scope.

## 8. M30.6 clearance - is it CLEARED or BLOCKED?

**M30.6 remains BLOCKED.**

## 9. Exact evidence supporting that decision

| # | Criterion | Evidence | Verdict |
|---|---|---|---|
| A | Memory-disclosure behavior intact | 1.000 / 1.000 mode accuracy, both passes | **MET** |
| B | Candidate recall remains strong | Recall@3 0.889/0.917, Recall@5 0.963/0.972 - improved via fixture fix | **MET** |
| C | multi_action works across varied phrasings | 5/7 (0.714) across all phrasing tested; 2 fail on one repeatable pattern | **PARTIALLY MET** |
| D | workflow_continuation mode reliable | 0.800/0.857 single-pass; isolated re-check of the only miss was 3/3 correct (Section 6) | **CONDITIONALLY MET** - noisy single-pass number, underlying behavior verified reliable |
| E | workflow_continuation preserves correct originating capability | 0.600/0.714 single-pass; both misses independently re-verified 3/3 correct in isolation | **CONDITIONALLY MET** - same noise caveat as D |
| F | Topic switches not treated as continuation | **0/2 (0.000)** - NOT fixed, both spec-mandated NEW_INTENT sentences fail, two generic fix attempts made | **NOT MET** |
| G | Cancellation not treated as continuation | **3/3 (1.000)** across both pending-subject variants | **MET** |
| H | Gmail overlap remains resolved | Re-verified directly this milestone: `gmail_search` suppressed, `Gmail` present, unfiltered view still resolvable | **MET** |
| I | Pure conversation doesn't routinely invoke tools | 1.000/1.000 | **MET** |
| J | Hallucinated capability references eliminated/rejected | Root cause fixed generically; 0.000 invalid-capability rate across 90 case-runs; specific failing case re-verified 3/3 fixed | **MET** |
| K | Invalid contract rate near zero | 0.000/0.000 | **MET** |
| L | Production `/ask` unchanged | `git diff --stat` confirms `server.py` unchanged this milestone (diff identical to M30.3's); 97/97 regression suite green | **MET** |

10 of 12 criteria are met or conditionally met with direct
counter-evidence for the "conditional" label. Criterion **F fails
outright** - a spec-mandated behavior (topic switch not misread as
continuation) was tested with the exact spec sentences and is wrong
100% of the time in this run, after two distinct, fully generic prompt
designs were tried and measured. Per standing instruction, this alone
is sufficient to keep M30.6 blocked - no threshold is being lowered to
force a CLEARED result over one clearly failing, spec-named criterion.

## 10. Files changed

- `uri_core/core/decision_engine.py`: `DECISION_CONTRACT_SYSTEM_PROMPT`
  checklist step 1 rewritten to the ANSWER/CANCEL/NEW_INTENT
  three-way judgment (with one worked example per CANCEL and
  NEW_INTENT); `capability` field definition extended with the
  action-name-vs-capability-id distinction.
- `scripts/m30_4_decision_quality_analysis.py`: `PENDING_ROLL_NUMBER`
  fixture corrected to the real enriched `active_pointer` shape
  (Section 5) - expected outcomes unchanged.
- `scripts/m30_5c_boundary_cleanup_eval.py` (new): 2-pass evaluator
  (40/50-case), `NEW_CASES_M305C_BOUNDARY` (5 cases, spec-verbatim),
  `NEW_CASES_M305C_MULTI_ACTION` (5 cases), 16-metric `summarize()`
  including `topic_switch_accuracy`, `cancellation_accuracy`,
  `invalid_capability_rate`.
- `scripts/m30_5c_results.json` (new): raw per-case results, both
  passes.

**Not changed:** `server.py`, `orchestrator.py`, `capability_
directory.py`, `decision_gates.py`, `turn_state.py`,
`capability_relevance.py` - confirmed via `git diff --stat` (identical
to their pre-M30.5C state).

## 11. Tests/results

`test_decision_engine.py` (42), `test_decision_gates.py` (21),
`test_turn_state.py` (18), `test_capability_directory.py` (16) -
**97/97 passing**, reconfirmed after every prompt edit this milestone
(including the reverted second boundary attempt, which was tested,
measured, and rolled back within this same session before being
recorded as a permanent change).

## 12. Rollback instructions

Revert the `DECISION_CONTRACT_SYSTEM_PROMPT` checklist-step-1 and
`capability` field edits in `decision_engine.py` to the M30.5B wording
(three-way judgment removed, action-name-vs-capability sentence
removed). Revert `PENDING_ROLL_NUMBER` in
`scripts/m30_4_decision_quality_analysis.py` to its pre-M30.5C shape
if the corrected fixture is ever found to be wrong (not expected -
it now matches real `turn_state.py` output exactly). No data
migration, no schema change, no session-format change, no production
file touched.

---

Stopping here per governing instruction. M30.6 is not started.
