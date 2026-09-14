# M30.5A: Decision Quality Remediation — Completion Report

**Status:** COMPLETE — shadow/offline only, zero production execution authority. M30.6 verdict: **REMAINS BLOCKED** (see §11).

## 1. Candidate-preselection design

`decision_engine.preselect_candidate_ids()` reuses the same directory-derived, discriminating-term scorer built for the Unsupported Gate (`capability_relevance.py`) rather than a second classifier — deliberately generous (`min_discriminating_score=0.0`, i.e. any real discriminating overlap counts), because under-inclusion here silently hides a valid capability from the model, which is worse than a slightly larger prompt. `build_decision_request()` narrows `capability_summaries` to the preselected set **plus** whatever `active_pointer.capability_id` already names, so a pending continuation's own capability can never vanish because this turn's raw text didn't happen to mention it. Validation (`_validate_contract`) always checks a proposal against the **full** directory regardless of preselection — narrowing only affects what the model sees, never what a correct answer is allowed to name. `conversation`/`unsupported` remain reachable unconditionally (neither requires a capability at all).

## 2. Mode-framing changes

Rewrote `DECISION_CONTRACT_SYSTEM_PROMPT`'s mode section as an explicit, ordered checklist (pending-continuation check → conversation → capability-plausibility → completeness → sensitivity) with one load-bearing rule stated directly: **"clarification" is not a safe default for general uncertainty** — being unsure *which* capability applies, when at least one plausibly does, must be answered by picking a best candidate, not by asking a question. General, structural rules only, no phrase-specific examples added (per the explicit instruction).

**A real bug I introduced and caught in the same pass:** the prompt rewrite accidentally dropped the `goal:` field definition and the "return exactly these keys" instruction entirely — the very first live test run came back **100% invalid** (`missing_fields:goal`). Found immediately via a single direct debug call, fixed before any golden-set run was recorded, confirmed via existing test suites (184/184) before proceeding. Disclosed here rather than silently corrected.

## 3. pending_interaction schema — and a bigger, real bugfix found while building it

`turn_state.py`'s `active_pointer` now carries `originating_goal`, `capability_id`, `action`, `expected_type`, `prompt_asked`, `created_at`, `state` alongside the existing `kind`/`question`/`missing_field`/`reference`. `expected_type` is inferred generically from the missing field's own name morphology (identifier/email_address/date/integer/string patterns) — never a phrase-specific rule, applicable to any future capability's schema fields.

**The real finding, found while building this:** a genuine, on-disk session file (inspected directly this milestone) proved that `session.active_workflow_question` — the field `_project_active_pointer` had read since M30.1 — **stays `null` for the ordinary ad hoc Brain-clarification pause** (`orchestrator.py`'s `_apply_clarification_pause`). Only a rarer, genuine `WorkflowExecutor`-based pause ever sets it. The real pending-state signal for the common case ("Find the student." → pending roll number) is `session.last_goal_attempt_history`'s last entry instead. **This means `active_pointer.kind` was silently "none" for the single most common continuation scenario in every prior milestone's live testing** — not a model reasoning failure as M30.4 partly characterized it, but a Turn State bug that gave the Decision Engine no signal to reason from at all. Fixed by checking both real session shapes; proven against the exact real on-disk data structure in a new test (`test_real_ordinary_clarification_pause_shape_is_now_detected`).

## 4. Gmail-overlap policy

Stated explicitly, implemented deterministically (never by registration order): `CapabilityDirectory.summaries()` (Brain-visible, default) suppresses a legacy capability from view when `overlaps()` shows a richer multi-action equivalent exists — the Brain sees exactly one `Gmail` identity, never `gmail_search`/`gmail_find_draft`/`gmail_create_draft` simultaneously. **Nothing is deleted or made unreachable**: `describe()`/`_all_entries()` still resolve every legacy id fully (execution/gate/fallback unaffected), and `summaries(resolve_overlaps=False)` gives the complete, unfiltered view when needed. M30.2's own overlap test updated to assert both properties explicitly (visible-set narrowing *and* full resolvability), not silently broken.

## 5. Unsupported-matching changes

`capability_relevance.py` (new): term "genericness" is computed **from the directory's own current contents** (any term appearing in 2+ registered capabilities is generic for that directory, right now) — never a fixed English word list. Live-verified this directly solves M30.5's own reported failure: "job search" no longer falsely implicates Gmail once legacy capabilities (web_search, gmail_search, etc.) are present to make "search" correctly recognized as generic. **Real, documented residual limitation:** in a narrow directory (Gmail alone, no legacy siblings), the same term can still look falsely discriminating — a corpus-relative method is only as good as its corpus; both the fix and its limit are proven by separate, explicit tests, not merged into one misleadingly-clean result.

## 6. Over-tooling evaluation

`decision_engine.detect_over_tooling()` — offline only, explicitly separate from `decision_gates.py`'s safety verification (a technically READY proposal can still be flagged here). Uses the same discriminating-term scorer as §5. Live-verified: `web_search` proposed for a pure-conversation goal is flagged; `Gmail` proposed for a genuine Gmail question is not.

## 7. Golden-set size

Expanded from 18 to **30** cases (12 new: two additional conversation phrasings, an office-order variant, two additional memory-disclosure phrasings, system performance, three additional Gmail-family phrasings including one deliberately legacy-worded, a spreadsheet-fetch case, a CGPA lookup, and one continuation case built against a **real** `_FakeSession` object exercising the actual §3 bugfix end-to-end rather than a hand-built `active_pointer` dict). Varied phrasing throughout, no sentence reused verbatim from the original 18.

## 8. Before/after metrics — real, both directions reported

**Pass 1 — identical 18 M30.4/M30.5 cases, remediated pipeline (direct, apples-to-apples):**
```
BEFORE (M30.4/M30.5 recorded): mode_accuracy = 0.389
AFTER  (this run):              mode_accuracy = 0.611   (+22.2 points)
invalid_rate: 0.0 (unchanged - schema compliance was never the problem)
```

**Pass 2 — expanded 30-case set, remediated pipeline (new baseline):**
```
mode_accuracy: 0.633
invalid_rate: 0.0
over_tooling_flagged: 2/30
```

**Genuine wins, not overstated:**
- `workflow_continuation` is now **reachable at all** — 3/3 continuation cases correctly identified the mode (0/2 in M30.4). This is the direct payoff of the §3 bugfix, not a prompt-wording effect.
- `unsupported_1`/`unsupported_2`, `topic_switch`, and most straightforward `single_action` cases (office note, file conversion, system performance, CGPA lookup, a legacy-worded Gmail search) now resolve correctly.

**Real, newly-introduced regression — reported, not hidden:** `disclosure_1`/`disclosure_2` (the exact "I work at NIT Sikkim" case this whole investigation has tracked since Stage 1) and the two new memory-preference cases **now regress to `conversation`**, missing `remember_fact` entirely. Root cause: candidate preselection's term-overlap scoring shares almost no vocabulary between a personal disclosure sentence and `remember_fact`'s own summary text ("save a fact... explicitly asked... profile"), so preselection silently excludes it from what the model sees. This was previously working (M30.3 live-verified it) and is now broken by this milestone's own preselection change — a real cost of the new mechanism, not swept under the 61%/63% headline number.

**Other real remaining gaps:** `multi_action` mode has **0% accuracy** across both passes (both Gmail multi-step cases still resolve to `clarification`, now at least correctly naming `Gmail` as the capability - progress, but the mode itself never fires). Continuation cases get the mode right but the capability wrong in 3/3 (`missed_capability` - the model says `workflow_continuation` but doesn't yet also name `extract_student_records`). One new false positive: `gmail_attachment_chain` was misclassified as `workflow_continuation` from recent-conversation context alone, with no real `active_pointer` set — the mode-framing rewrite made continuation more reachable but also, in this one case, over-eager.

## 9. Prompt-size / latency impact

Preselection measurably shrinks the prompt for a real Gmail query (`test_preselection_reduces_prompt_size`, real assertion, not simulated). Average latency across both real 18/30-case runs: ~2.9-3.3s/call, consistent with M30.3-M30.5's own recorded range — no material latency regression from the added checklist prompt or the preselection step (which is pure local computation, no extra network call).

## 10. Remaining failure categories (explicit, for the next pass)

1. **Disclosure/preference regression (§8)** — needs candidate preselection to always keep a small "core" set (e.g. `remember_fact`, `recall_memory`) visible regardless of term-overlap score, since personal statements inherently share little vocabulary with a memory tool's own description. Not fixed here — flagged for the next iteration.
2. `multi_action` mode never fires (0/2) — needs targeted investigation independent of the preselection/prompt work done here.
3. Continuation capability-naming (3/3 `missed_capability`) — the mode fix (§3) did not, by itself, also teach the model to name the right capability for a continuation; likely needs `pending_interaction.capability_id` more prominently surfaced when it *is* known (today it's usually `None` for the common ad hoc pause path, per §3's own honest gap).
4. One new continuation false-positive (`gmail_attachment_chain`) worth a closer look before any further prompt tuning.
5. The Gmail-overlap policy (§4) measurably helped capability naming (`gmail_draft_approval` now correctly picks `Gmail`, not the legacy alias) but did not fix the missed `approval_required` mode itself — a separate gap.

## 11. Whether M30.6 is now cleared or remains blocked

**REMAINS BLOCKED.** Explicit, data-derived threshold (not invented to pass): before M30.6 is reconsidered, this milestone's own evidence requires, at minimum, (a) no known regression on a previously-working category (§8's disclosure regression currently violates this), (b) `multi_action` accuracy above 0% (currently 0/2), and (c) continuation capability-selection above roughly half (currently 0/3). None of the three hold yet. The genuine, real improvement (38.9% → 61.1%/63.3%, `workflow_continuation` newly reachable) is significant progress, not sufficient progress — reported as exactly that, neither inflated nor dismissed.

## 12. Tests/results

New: 5 comparison/gate tests already counted in M30.5's own 20 remain green; this milestone adds 5 preselection tests, 3 over-tooling tests, 4 `pending_interaction`/real-session tests, 2 discriminating-term-limitation tests, plus the M30.2 overlap test's update — all passing. Full regression sweep: **184/184** across every M30.1-M30.5 suite plus the existing orchestrator/capability/Gmail/office regression set. The 3 known pre-existing failures (2 M20 resilience, 1 M20 feasibility) re-confirmed unchanged, untouched, as instructed.

## 13. Files changed

- New: `uri_core/core/capability_relevance.py`, `scripts/m30_5a_remediation_eval.py`, `scripts/m30_5a_results.json`, this document.
- Changed: `uri_core/core/decision_engine.py` (prompt rewrite + the goal-field bugfix, `preselect_candidate_ids`, `build_decision_request`/`propose_decision`'s new `preselect` param, `detect_over_tooling`), `uri_core/core/decision_gates.py` (Unsupported Gate now uses `capability_relevance.plausible_matches` instead of the bare M27 scorer), `uri_core/core/capability_directory.py` (Gmail-overlap suppression policy in `summaries()`), `uri_core/core/turn_state.py` (`_project_active_pointer` bugfix + `pending_interaction` field enrichment).
- Test files updated/extended: `test_decision_engine.py`, `test_decision_gates.py`, `test_turn_state.py`, `test_capability_directory.py` (one M30.2 assertion updated to reflect the new, intentional overlap-suppression policy).
- No orchestrator.py, server.py, or UI changes.

## 14. Rollback instructions

Delete `uri_core/core/capability_relevance.py`, `scripts/m30_5a_remediation_eval.py`, `scripts/m30_5a_results.json`, this document. In `decision_engine.py`, revert `DECISION_CONTRACT_SYSTEM_PROMPT` to its M30.5 text, remove `preselect_candidate_ids`/the `preselect` parameter/`detect_over_tooling`. In `decision_gates.py`, revert `_plausible_match_exists` to its M30.5 `CapabilityDiscoveryEngine`-based form. In `capability_directory.py`, revert `summaries()` to its unconditional M30.2 form (drop `_suppressed_legacy_ids`). In `turn_state.py`, revert `_project_active_pointer` to its M30.1 form (loses the pending_interaction fields and the last_goal_attempt_history fix). All additive/isolated; nothing pre-existing was rewritten destructively. Production `/ask` behavior was not touched by this milestone at all (confirmed live, shadow flag off, unchanged before and after every change).
