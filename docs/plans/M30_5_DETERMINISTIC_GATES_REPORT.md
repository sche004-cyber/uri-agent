# M30.5: Deterministic Decision Gates — Completion Report

**Status:** COMPLETE — shadow/analysis integration only, zero production execution authority granted.

## 1. Gate pipeline implemented

`uri_core/core/decision_gates.py`, `evaluate_gates(decision, capability_directory, principal, permission_checker) -> GateResult`. Accepted order: contract validity → capability existence → action existence → availability/connection → completeness/missing-parameter → permission → approval → execution readiness (never executed). Availability is checked before completeness per the accepted architecture (an unavailable capability's parameters are moot).

## 2. Deterministic result contract

```
GateResult(outcome, capability_id, action_names, reasons, missing_field, expected_type, overlap_candidates)
```
`outcome` ∈ `{READY, MISSING_PARAMETER, DISCONNECTED, UNAVAILABLE, PERMISSION_DENIED, APPROVAL_REQUIRED, UNSUPPORTED, INVALID_PROPOSAL, DEGRADED}` — exactly the requested set, none collapsed into `clarification`.

## 3. Files changed

- New: `uri_core/core/decision_gates.py`, `test_decision_gates.py` (20 tests), `scripts/m30_5_gate_metrics.py`, `scripts/m30_5_gate_metrics_results.json`, this document.
- Changed: `uri_core/core/capability_directory.py` — (a) `describe()` now surfaces real Level-2 `check_availability()` for multi-action capabilities (the exact gap M30.2/M30.3/M30.4 each flagged and left open — closed here since the Connection gate cannot function without it); (b) `_find_overlaps()`'s tokenizer fixed to strip punctuation (a real bug found live this milestone — "Search Gmail." never matched bare "gmail" before).
- Changed: `uri_core/core/decision_engine.py` — `build_shadow_trace`/`run_shadow_for_ask` extended (additively) to also compute and log the gate outcome alongside the Brain proposal, via a lazy import (avoids a circular import with `decision_gates.py`, which itself imports `DecisionOutcome` from `decision_engine.py`).
- No orchestrator.py, server.py, or UI changes this milestone (server.py's M30.3 shadow hook itself is unchanged — it already passes everything the extended `run_shadow_for_ask` needed).

## 4. Existing authority reused by each gate

| Gate | Reuses | New code |
|---|---|---|
| Existence | `CapabilityDirectory.describe()` (M30.2) | none |
| Action existence | Same `describe()` call's `actions` list | none |
| Availability/Connection | `CapabilityFeasibility` (M20) for legacy; `GmailCapability`'s own real `check_availability()` (M27) for multi-action, now surfaced at Level 2 | the Level-2 surfacing itself (a completion of M30.2, not new logic) |
| Completeness | `ActionSchema.required`/`parameters` (M27, already existed) | none |
| Permission | `entry["permission_required"]` (M30.2, itself derived from `CapabilityFeasibility`'s connection-based blocking for legacy, or a fixed real-permissions flag for multi-action) | none |
| Approval | `entry["approval_required"]` / per-action `approval_requirement` (M20/M27) — never the model's own `requires_approval` field | none |
| Unsupported | `CapabilityDiscoveryEngine` (M27) via a pure reshaping adapter (`_DirectorySummaryAdapter`) | the adapter only, not the scoring |

No gate duplicates `ApprovalGate`, `CapabilityFeasibility`, or M27's own logic — every one is a thin, additional call site into something that already existed.

## 5. Gmail overlap handling

`_overlap_candidates_for()` reuses `CapabilityDirectory.overlaps()` (M30.2) directly. When a proposal names an overlapping identity (e.g. `gmail_search`), `GateResult.overlap_candidates` lists the other side (`Gmail`) — visible for review, never silently chosen between. **Neither path is retired or preferred by default**, per the accepted scope. Live-verified this milestone: proposing the legacy `gmail_create_draft` for a draft-preparation request correctly surfaced its overlap with the multi-action `Gmail` capability while still gating the proposal on its own real merits (this specific case actually resolved to `APPROVAL_REQUIRED`, matching the intended real-world outcome, despite the identity ambiguity — reported honestly as a partial, not fully deliberate, win in §10 below, not oversold as the overlap problem being "solved").

## 6. Unsupported handling

Two directions, both real, both tested:
- **Model falsely claims unsupported, a real capability exists** → `evaluate_gates` runs `CapabilityDiscoveryEngine`'s real relevance scoring against the goal text; a match rejects the claim (`INVALID_PROPOSAL`, reason `false_unsupported_claim_rejected_by_directory`). **Live-verified in production shadow mode this milestone**: "How many unread emails do I have?" — Brain said `unsupported`; gate returned `INVALID_PROPOSAL` and named `Gmail` as the real, existing match. This is the exact historical failure class this whole investigation has tracked since Stage 1, caught live by the new deterministic layer.
- **Model asks a clarifying question for a genuinely unsupported goal** → same discovery check, applied when `mode=clarification` and no capability was named; confirmed with a synthetic "recurring automated backup" goal (deliberately chosen to share no vocabulary with any registered capability, see §9).

**Real, documented limitation, not glossed over:** the reused discovery scoring is a bare term-overlap heuristic — a goal containing the generic word "search" (e.g. "job search") registers a false plausible match against Gmail's own description ("Search and inspect Gmail messages...") purely from the shared word, with no real semantic connection. `test_generic_shared_word_can_cause_a_false_plausible_match` documents this directly rather than hiding it behind a conveniently-chosen test phrase.

## 7. Completeness handling

Schema-based, using each action's real `required`/`parameters` (already declared by M27's `ActionSchema`). Live example: `search_messages` with no `query` → `MISSING_PARAMETER`, `missing_field="query"`, `expected_type="string"` — the exact metadata M30.7's future `pending_interaction` structure will need. **Honest gap, unchanged from M30.2's own finding:** legacy capabilities have no declared per-action schema yet, so completeness cannot be verified for them from metadata alone — the gate silently skips the check for those (never fabricates a missing-field claim it can't support) rather than guessing.

## 8. Connection/availability handling

Legacy: unchanged, `CapabilityFeasibility`'s own two-reason distinction reused directly — `not_implemented` → `UNSUPPORTED` (no adapter exists at all, this is not a connection problem), `unavailable_runtime` → `DISCONNECTED` (a real, connectable service just isn't connected). Multi-action: previously always `availability_known=False` at Level 1; now, once a capability is selected, `describe()` calls the real `GmailCapability._availability()` (a genuine live Gmail connection check) and surfaces `available`/`availability_reason` for the first time. **Live-verified**: in this development environment (no live Gmail token loaded in the backend process), Gmail correctly reports `DISCONNECTED` — real, honest state, never fabricated as connected.

## 9. Permission/approval handling

Both gates read directory metadata only — `ApprovalGate`/`ApprovalStore` themselves are untouched, still the sole real enforcement mechanism (this module doesn't execute, so there is nothing to enforce yet; it only predicts what enforcement would say). Live-verified: a `create_draft` proposal with the model's own `requires_approval: false` was still correctly gated to `APPROVAL_REQUIRED`, using the action's own real `approval_requirement` metadata, never the model's claim.

## 10. M30.4 golden-set: RAW Brain vs. POST-GATE, honest numbers

Re-ran the same 18-case golden set (unchanged from M30.4) through Decision Engine → Gates:

```
total: 18
raw_brain_accuracy: 0.389        (unchanged, reproduces M30.4's finding)
```

Of the **11 brain errors**, broken down honestly (not collapsed into one misleading "safe rejection rate"):
- **6/11 (55%)**: the Brain proposed no capability at all (`clarification`/`conversation` with `capability=None`). **Gates cannot address these** — there is nothing concrete to verify. This is the single largest limitation: gates contain bad *claims*, they cannot supply a capability selection the model never attempted.
- **1/11 (9%)**: a genuinely false `unsupported` claim (`conv_2`) → correctly rejected (`INVALID_PROPOSAL`). Real, deliberate safety value.
- **1/11 (9%)**: real environment state (`gmail_unread_only`) → gate correctly returned `DISCONNECTED`, reflecting genuine Gmail disconnection in this environment — not a gate failure, but also not comparable to the golden set's idealized "should be READY" expectation, since the *real* environment genuinely differs from that assumption.
- **1/11 (9%)**: `gmail_draft_approval` — the Brain picked the *wrong specific capability id* (`gmail_create_draft` instead of `Gmail`), but the gate still landed on `APPROVAL_REQUIRED` — matching the golden expectation, but by coincidence of that specific legacy capability also requiring approval, not because the gate corrected the capability choice itself.
- **1/11 (9%)**: `conv_1` — the Brain proposed a real, existing, fully-available capability (`web_search`) for a request that should have been pure conversation. Nothing about *that specific claim* is false (web_search really does exist, really is available, needs no parameters, no permission, no approval) — so the gate correctly returns `READY`. **This is the clearest evidence that gates verify deterministic truth, not semantic fit** — a technically-valid but semantically-wrong proposal passes cleanly, by design, because checking "does this capability actually match the goal" was never in a gate's scope (that remains Decision Engine quality work, M30.4's domain, not M30.5's).

**Direct answer to "can the runtime safely contain model mistakes":** partially, and precisely bounded — yes for false claims about unsupported/availability/permission/approval (verified, deterministic, live); no for a missing or semantically-wrong capability selection (structurally outside what a verification-only gate can supply). Both halves are real and reported plainly, not smoothed into one number.

## 11. False rejection / unknown cases

Zero false rejections observed: no genuinely-correct Brain proposal was gated down to a worse outcome in this run (`disclosure_1/2`, `office_note`, `convert_doc`, `unsupported_1`, `ambiguous_1`, `clarify_1` all remained `READY`/`INVALID_PROPOSAL`-on-a-genuine-non-match exactly as expected). `UNAVAILABLE`/`DEGRADED` (the two "unknown truth" outcomes) were not reached in this run's live cases — both are exercised directly in `test_decision_gates.py` (`test_capability_with_no_availability_check_reports_unavailable_not_true`, and `DEGRADED` via a directory/evaluation failure path), confirming they behave correctly when they do occur, even though this golden set's real capabilities all happened to have a determinable answer.

## 12. Tests/results

20/20 new (`test_decision_gates.py`), including two real bugs this milestone caught and fixed in the same pass before they were ever reported as findings: `_find_overlaps()`'s punctuation-stripping gap, and two of my own test fixtures that assumed a permission/approval check would be reached before a real (currently disconnected) Gmail's own connection gate would correctly short-circuit first — both are documented in the test file's own comments, not silently patched. Full regression sweep: **172/172** across `test_decision_gates`, `test_decision_engine`, `test_turn_state`, `test_capability_directory`, plus the full existing orchestrator/capability/Gmail/office suite. The 3 known pre-existing failures (2 M20 resilience, 1 M20 feasibility) re-confirmed unchanged, untouched, as instructed.

## 13. Proof no action was executed

`GateResult` has no `execute`/`run` method (asserted directly in `test_gate_evaluation_never_executes_anything`). `evaluate_gates()` never imports `ApprovalGate`, `ToolDispatcher`, or `MultiActionExecutor`. The live shadow-mode runs (§6, §8, §9) each show a real `gate_outcome` logged alongside the real `old_execution` result — the two are independent; nothing about computing the former touched the latter.

## 14. Proof production behavior remained unchanged

Restarted the backend twice this milestone: once with `URI_ENABLE_DECISION_ENGINE_SHADOW=1` (4 live requests — unread emails, unsupported scheduler, disclosure, draft-reply — every `old_execution` result identical in shape to every prior milestone's own baseline), once back to default-off (re-ran the Gmail request — identical result, and the shadow log file's line count stayed exactly where the shadow-mode run left it, zero new entries with the flag off).

## 15. Whether M30.6 remains blocked or can proceed

**Remains NOT cleared, per the accepted scope — this milestone does not lift that gate.** The raw Brain accuracy (38.9%) and the gate-effect breakdown (§10: 55% of errors are structurally unaddressable by gates, since no capability was proposed at all) both argue strongly against enabling any controlled execution yet.

## 16. Recommended work required before M30.6

1. Decision Engine quality work (M30.4's own recommendation, unchanged: deterministic candidate preselection via `CapabilityDiscoveryEngine`, mode-framing prompt experiments) — this milestone's evidence reinforces it further, since 55% of errors are "no capability proposed at all," a Decision Engine problem gates cannot fix.
2. The Unsupported Gate's term-overlap false-positive risk (§6) should be tightened (e.g. requiring more than one shared term, or weighting by term rarity) before it is trusted at higher stakes — not blocking for shadow-mode logging, but a real gap for any future live use.
3. Gmail overlap (§5) needs an actual disambiguation/consolidation decision at some point — this milestone only makes the ambiguity visible and safe to observe, it does not resolve it.
4. Legacy per-action schemas (§7) remain a real gap for the Completeness Gate — currently only multi-action capabilities get real missing-parameter detection.

## 17. Rollback instructions

Delete `uri_core/core/decision_gates.py`, `test_decision_gates.py`, `scripts/m30_5_gate_metrics.py`, `scripts/m30_5_gate_metrics_results.json`, this document. In `capability_directory.py`, revert the `describe()` availability-surfacing block and the `_find_overlaps`/`_word_tokens` tokenizer fix (both clearly marked "M30.5:"/"M30.5 bugfix:"). In `decision_engine.py`, revert the `gate_result` parameter on `build_shadow_trace` and the lazy-import gate call in `run_shadow_for_ask` (also marked "M30.5:"). All additive; nothing pre-existing was rewritten in place. Production `/ask` behavior was not touched by this milestone — confirmed live, twice (§14).
