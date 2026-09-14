# M30.4: Offline Decision Comparison & Quality Analysis

**Status:** COMPLETE (analysis only — zero production authority granted, per accepted scope)
**Method:** real model calls (local Ollama-resolved model, the only reachable provider in this environment — see §7), a comparison-heuristic extension to `decision_engine.py` (comparison tooling, not routing), and a real 18-case golden set + a 3-variant Gmail-summary experiment, both run for real and captured in `scripts/m30_4_results.json`.

## 1. Root cause of the Gmail selection failure — REVISED from the M30.3 hypothesis

M30.3's live evidence suggested the cause was **insufficient capability-summary semantics** ("Level-1 summaries did not give enough affordance to connect 'unread emails' to Gmail"). This milestone tested that hypothesis directly and it does **not** hold: three Gmail summary variants — (A) the real, current one-line description, (B) a deliberately rich affordance-listing description, (C) explicit structured affordance/domain tags appended to the description — were fed to the real Decision Engine for the same three Gmail-related cases. **All three variants produced the identical outcome** (`clarification`, never `single_action`/`multi_action`). Richer capability metadata measurably made **zero difference**.

**Actual root cause, evidenced across the full 18-case golden set:** the model defaults to `mode=clarification` far more often than any input property justifies — it was the actual output for **9 of 18 cases (50%)**, spanning cases that should have been `conversation`, `workflow_continuation`, `multi_action`, and a plain resolvable `single_action`. This is a **mode-selection bias**, not a missing-information problem specific to Gmail. The Gmail mismatches are one visible symptom of a general pattern, not a Gmail-specific gap.

## 2. Root cause of the workflow_continuation failure

Both continuation cases (`continue_1`: "B250012CS", `continue_2`: "22CS045", each following a real pending `active_pointer` with `missing_field="roll_number"`) came back as `clarification`/`single_action`, never `workflow_continuation`. Inspection of `DECISION_CONTRACT_SYSTEM_PROMPT`'s continuation guidance ("this message plausibly answers it") shows it states the RULE but gives the model no way to recognize WHAT an answer to this specific pending field would look like — it never sees the field's expected shape/type, only its bare name. Combined with the same general clarification-bias from §1, the model has no strong signal pulling it toward `workflow_continuation` specifically.

**Proposed change (NOT implemented, per accepted M30.4 scope — analysis only):** promote `active_pointer` to the richer structure named in the request:

```
pending_interaction: {
  originating_goal: "...",
  capability: "extract_student_records",
  pending_field: "roll_number",
  expected_type: "identifier",       # new
  prompt_asked: "What is the student's roll number?",  # verbatim, already have this
  created_at: "...",                 # new, for expiry
  state: "awaiting_answer",
}
```

`expected_type` is the load-bearing addition: telling the model "the pending field expects an identifier/number/name" gives it a concrete pattern-match target ("B250012CS" looks like an identifier) instead of an abstract "plausibly answers" instruction. This is a Turn State schema change (M30.1's `active_pointer`), not a decision_engine.py prompt change alone — flagged for M30.5+ to design properly, not built here.

## 3. Capability-summary / affordance findings

- Affordance richness (verbs, domains, explicit tag lists) measurably does **not** move classification quality for this model at Level-1, at least for the Gmail case tested. This is real, negative evidence — it argues against investing further in richer Level-1 summaries as the primary lever, and argues *for* investigating the mode-selection bias (§1) and/or the two other options below (§8) instead.
- The overlap flagged by M30.2 (`gmail_create_draft` vs. multi-action `Gmail`) is not just a taxonomy curiosity — it caused a real, live selection error: `gmail_draft_approval` (a draft-preparation request) was answered with capability `gmail_create_draft` (the legacy overlap), never `Gmail`, and the mode came back `single_action`, never the expected `approval_required`. This is concrete evidence that the un-consolidated overlap actively confuses capability selection today, strengthening the case for consolidating it in a later milestone (not this one).

## 4. Comparison-heuristic improvements (implemented — this is tooling, not routing)

`classify_agreement()` (old-path-vs-new, used when there is no ground-truth label) now detects `WORKFLOW_CONTINUATION_MISSED` in addition to the M30.3-era `WORKFLOW_CONTINUATION_MISMATCH` (false positive) — both directions are distinct categories now, never merged, per the M30.3 finding.

New `evaluate_against_golden()` (ground-truth-aware, used against a human-labeled golden set) distinguishes, for every mode: `false_unsupported`/`missed_unsupported`, `false_clarification`/`missed_clarification`, `false_continuation`/`missed_continuation`, `false_capability`/`missed_capability`, `over_tooling`/`under_tooling`, plus `invalid` and `correct`. 5 new tests added (`test_decision_engine.py`, `M304ComparisonHeuristicTests`), all passing, including a regression proof that a genuine topic-switch case is correctly labeled `correct` by the ground-truth-aware evaluator even though the old-path-comparison heuristic alone would flag it as a `WORKFLOW_CONTINUATION_MISSED` *candidate* (expected — that heuristic cannot know intent without a label; this is documented in-code, not silently inconsistent).

## 5. Golden decision set — size and coverage

18 cases, `scripts/m30_4_decision_quality_analysis.py` (`GOLDEN_SET`), covering every category requested: 2× conversation, 2× clarification, 2× workflow_continuation, 2× unsupported, 4× single_action (disclosure ×2, office note, file conversion), 2× multi_action, 1× approval_required, 1× topic-switch, 1× ambiguous, 1× Gmail-unread (a second single_action Gmail case, separate from the multi_action pair). Varied phrasing used throughout (e.g. two differently-worded conversation openers, two differently-worded unsupported requests) rather than one phrasing repeated. Not exhaustive — see §11 for what a larger set would still need.

## 6. Metrics — current Decision Engine, real run, 18 cases

```
total: 18
mode_accuracy: 0.389   (7/18 correct)
invalid_rate: 0.0      (0/18 malformed/invalid — confirms M30.3's schema-compliance finding held)
avg_latency_seconds: 5.13
avg_request_size_chars: 11139  (~2.8k tokens estimated)

by_category:
  correct: 7
  false_clarification: 5   <- the dominant failure mode
  missed_continuation: 2
  false_unsupported: 1
  missed_clarification: 1
  missed_unsupported: 1
  false_capability: 1
```

**Do not read 38.9% as "the architecture doesn't work"** — every one of these 18 real decisions was still correctly *validated* (0 invalid), and every wrong classification is visible, typed evidence rather than a silent bad outcome (the entire point of shadow mode). It does mean the Decision Engine is not yet ready to be trusted with real capability selection at controlled-execution scope (M30.5/M30.6) without either a stronger model, better prompt/mode framing, or both.

## 7. Model-comparison findings

**Not available in this environment — stated plainly, per the accepted scope.** Checked `GET /providers` directly: `ollama` (`configured: false`, `available: true` — used for every call in this analysis), `openai`/`groq`/`lm_studio` (`configured: false`, unusable), `openrouter` (`configured: false`, `available: true` but unusable without a key). No frontier/stronger model has a real API key configured anywhere in this repository's current state. This means §1/§6's findings cannot yet be separated into "model capability limitation" vs. "prompt/metadata deficiency" with a controlled comparison — the Gmail summary-richness experiment (§1/§3) is the closest substitute this milestone could run, and it isolated metadata as *not* the cause, which is real (if partial) evidence toward "this is at least partly a model/prompt framing limitation," not proof the architecture itself is at fault.

## 8. Level-1 vs. Level-2 cost tradeoff

Average request size at Level-1 alone is already ~11.1k characters (~2.8k tokens) — driven mostly by the number of registered legacy capabilities (14+) each carrying a full description, not by any one capability's richness. Given §1/§3's finding that summary richness didn't move accuracy, the more promising levers for a later milestone, in order of estimated cost:

1. **Deterministic preselection of a small candidate set** (per the accepted architecture's own option 3): use `CapabilityDiscoveryEngine`'s existing relevance scoring (already built, M27) to narrow `capability_summaries` to the top ~3-5 relevant entries before the one decision call, rather than all 14+ — reduces request size without a second model call, and may also reduce the "everything looks equally plausible, ask a clarifying question" pressure that could be contributing to §1's bias.
2. **Mode-selection framing changes** (few-shot examples inside the system prompt showing a clarification-vs-single_action distinction, or reordering/re-weighting the mode descriptions) — cheap to try, needs real measurement, not assumed to work given §1's negative result on the metadata-richness hypothesis.
3. Richer Level-1 summaries or structured affordance tags: **deprioritized** per §1/§3's negative finding, not recommended as the next investment.

No second model classifier was introduced or considered — option 1 above reuses an existing deterministic scoring component, not a new LLM round-trip, consistent with the frozen architecture.

## 9. Recommended changes before M30.5

1. Do not raise `enable_decision_engine_live`'s scope (M30.5/6) until mode accuracy is substantially improved — 38.9% is not a safe basis for controlled execution even on an allowlist.
2. Prioritize deterministic candidate preselection (§8.1) and mode-framing prompt experiments (§8.2) over further capability-metadata investment (§8.3, evidenced not to help).
3. Design the `pending_interaction` structure (§2) as a real Turn State schema change for a future milestone — not built here.
4. Consolidate or at least prompt-disambiguate the Gmail legacy/multi-action overlap (§3) — it caused a real, observed selection error in this run, not just a theoretical duplicate.
5. Re-run this exact golden set (unchanged, for a fair before/after) once any of the above lands, to measure real improvement rather than anecdote.

## 10. Whether M30.5 deterministic gates can safely proceed

**Yes, with a scope caveat.** M30.5's own accepted scope is building the deterministic gates (availability/completeness/unsupported/connection/permission/approval/execution-validation) — none of which execute anything or trust the model's classification; they exist specifically to catch exactly the kind of misclassification this milestone measured. Building the gates does not require the Decision Engine to already be accurate — it requires the gates to correctly REJECT a bad proposal, which can be tested and proven independently of today's 38.9% accuracy. **M30.6's own controlled-execution scope, however, should not proceed on the current numbers** — that is a separate milestone gate, not this one.

## 11. Files changed

- `uri_core/core/decision_engine.py` — extended `AGREEMENT_CATEGORIES`/`classify_agreement()` (added `WORKFLOW_CONTINUATION_MISSED`); added `GOLDEN_CATEGORIES`/`evaluate_against_golden()`. Both are comparison/evaluation tooling only — no change to `propose_decision()`'s validation or the live `DECISION_CONTRACT_SYSTEM_PROMPT`.
- `test_decision_engine.py` — 5 new tests (`M304ComparisonHeuristicTests`), 2 pre-existing test bugs of my own caught and fixed during this same milestone (a missing capability_directory argument, an elif-ordering assumption) before they were reported.
- New: `scripts/m30_4_decision_quality_analysis.py` (golden set + runner + Gmail-variant experiment, standalone, zero production imports beyond the already-accepted M30.1-M30.3 modules), `scripts/m30_4_results.json` (raw real results), this document.
- No orchestrator.py, server.py, capability_directory.py, or turn_state.py changes.

## 12. Rollback instructions

Delete `scripts/m30_4_decision_quality_analysis.py`, `scripts/m30_4_results.json`, this document. Revert the two additive blocks in `decision_engine.py` (clearly marked "M30.4:") and the 5 added test classes in `test_decision_engine.py` — both are pure additions, nothing pre-existing was rewritten in place. Production `/ask` behavior was not touched by this milestone in any way (analysis-only, per accepted scope) — there is nothing to roll back on the live path.
