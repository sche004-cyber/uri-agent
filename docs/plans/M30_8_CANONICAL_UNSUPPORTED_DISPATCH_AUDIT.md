# M30.8 Canonical Dispatch Audit — Valid `unsupported` Decisions Routed to Legacy Fallback

**Status:** Audit only. No implementation performed, per explicit instruction.
**Trigger:** the Gemma 4 evaluation (`docs/research/GEMMA4_EVALUATION_REPORT.md`
§4) observed two well-reasoned canonical `unsupported` decisions land on
`gate_outcome: INVALID_PROPOSAL`, which unconditionally triggers legacy
fallback under the current dispatch logic.

---

## 1. Acceptance Criteria (defined before drafting this audit)

1. Identify the exact function and line(s) that decide whether a canonical
   outcome triggers legacy fallback — not a paraphrase, the real code path.
2. Reproduce the specific gate branch that produced `INVALID_PROPOSAL` for
   the two Gemma eval scenarios, from actual source, not inference from the
   eval's JSON output alone.
3. Enumerate every mode/outcome pair that currently terminates through
   canonical without fallback, and every one that currently falls back,
   citing source.
4. State precisely which valid outcomes are missing terminal treatment,
   and why (root cause, not symptom).
5. Propose the narrowest possible repair — smallest blast radius, no
   Decision Contract schema change, no change to any outcome/mode
   currently working correctly.
6. Name the specific tests that repair would need.
7. State plainly whether this blocks Phase A's own exit criteria (and
   therefore Phase B legacy retirement), with the plan's own text as the
   basis for that judgment, not a new opinion.
8. Implement nothing.

---

## 2. The Exact Dispatch Branch

**File:** `uri_core/core/canonical_execution.py`
**Function:** `decide_fallback_reason()` (line 225), called from
`run_canonical_for_ask()` (line 371).

```python
def decide_fallback_reason(*, gate_outcome, capability_id, mode):
    if gate_outcome in {"INVALID_PROPOSAL", "DEGRADED"}:      # line 240
        return f"engine_failure:{gate_outcome}"
    if gate_outcome != "READY":
        return None
    if mode not in EXECUTABLE_MODES:                           # single_action, multi_action, workflow_continuation
        return None
    if mode == "workflow_continuation" and not workflow_continuation_mode_enabled():
        return "mode_not_executable:workflow_continuation"
    if not is_allowlisted(capability_id):
        return "canonical_killswitch_not_allowlisted"
    return None
```

**This is the exact dispatch branch.** Line 240 treats **every**
`INVALID_PROPOSAL` gate outcome as an engine failure, unconditionally,
regardless of the contract's own `mode` or of *why* the gate produced
`INVALID_PROPOSAL`. `run_canonical_for_ask()` then routes any non-`None`
`fallback_reason` straight to legacy (`server.py:1300`), never reaching
`_canonical_nonexecution_envelope()` (line 253) for that turn.

## 3. Root Cause — Where `INVALID_PROPOSAL` Actually Comes From

`INVALID_PROPOSAL` is not one thing. Reading `uri_core/core/decision_gates.py`
directly, it is produced by **eight distinct code paths**, only one of
which is the defect:

| Path (file:line) | Genuinely a proposal/engine defect? |
|---|---|
| `evaluate_gates()`:186-191 — `decision.status != "ok"` (malformed model output) | **Yes** — real parse/engine failure |
| `_evaluate_gates_inner()`:228-231 — workflow continuation with no active pointer | **Yes** — real state defect |
| `_evaluate_gates_inner()`:234-237 — continuation with no durable capability | **Yes** |
| `_evaluate_gates_inner()`:327-330 — a mode other than unsupported/clarification/conversation/workflow_continuation named no capability | **Yes** — the model was required to name one and didn't |
| `_evaluate_gates_inner()`:342-346 — capability named does not exist in the Directory | **Yes** — hallucinated capability name |
| `_evaluate_gates_inner()`:351-355 — action named does not exist on the capability | **Yes** — hallucinated action name |
| `evaluate_gates()`:199-203 — any internal exception (actually `DEGRADED`, not `INVALID_PROPOSAL` — listed for completeness) | **Yes** |
| **`_evaluate_gates_inner()`:296-300 — "false unsupported claim rejected by directory"** | **NO — this is a real, decided, non-engine outcome** |

The defective path, in full:

```python
# decision_gates.py, inside the "no capability named" branch, mode == "unsupported":
if matches:                                    # a plausibly-related capability exists in the Directory
    top_candidate = matches[0]
    candidate_entry = capability_directory.describe(top_candidate)
    if candidate_entry is not None:
        candidate_outcome = _availability_outcome(candidate_entry, top_candidate, action_names, matches)
        if candidate_outcome is not None:      # candidate is DISCONNECTED/UNAVAILABLE/UNSUPPORTED — already terminal, not the bug
            return candidate_outcome
    # candidate exists AND is connected/available:
    return GateResult(
        outcome="INVALID_PROPOSAL", capability_id=None, action_names=action_names,
        reasons=["false_unsupported_claim_rejected_by_directory"],
        overlap_candidates=matches,
    )
```

This branch exists for a real, legitimate reason (Scenario 2's own repair:
catch a model that says "unsupported" when the real capability is simply
disconnected, or wrongly self-reports a gap that doesn't exist). But its
only check is **capability-level existence + connection**, never
**action/schema-level fit**. It cannot distinguish:

- *The model was simply wrong* (the capability genuinely handles this,
  legacy's own keyword match would likely also find it) — a real defect
  worth re-routing.
- *The model was right for a reason the gate can't see* (the capability
  exists and is connected, but does not support the **specific** action/
  format requested) — exactly the Gemma eval's two failures:
  - Scenario 5: `convert_document` exists and is available, but only
    supports PDF→DOCX, not DOCX→LaTeX. Gemma's `unsupported_reason` said
    exactly this. The gate's capability-level check cannot see it.
  - Scenario 8: `Gmail` exists and is connected, but has no send action —
    only drafts. Gemma's `unsupported_reason` said exactly this. Same
    blind spot.

In both cases the gate's own verdict ("the model's unsupported claim is
false") is itself questionable — but regardless of whether the verdict is
right or wrong, **the outcome it produces is a real, decided classification,
not an engine/parse failure**, and must not be dispatched as one.

## 4. Current Allowed Terminal Outcomes (as actually implemented)

Terminal without fallback today (verified by direct trace of
`decide_fallback_reason()` + `_canonical_nonexecution_envelope()`):

| Gate outcome | Terminates how | Verified against |
|---|---|---|
| `READY` + mode not in `{single_action, multi_action, workflow_continuation}` | Non-execution envelope (e.g. `conversation`→success, `clarification`-no-capability→`awaiting_user_response`) | `test_valid_non_execution_outcomes_do_not_request_legacy` |
| `READY` + mode in `{single_action, multi_action}` + allowlisted | **Real execution** | `test_ready_gmail_single_action_is_eligible` etc. |
| `READY` + `workflow_continuation` + flag enabled + allowlisted | Real execution | plan §B.2 |
| `MISSING_PARAMETER` | Non-execution envelope (`awaiting_user_response`) | Gemma eval scenario 4 |
| `DISCONNECTED` | Non-execution envelope (`unavailable`) | prior Scenario 2 evidence |
| `UNAVAILABLE` | Non-execution envelope (falls into the `{UNSUPPORTED,UNAVAILABLE,PERMISSION_DENIED}` branch) | source read |
| `PERMISSION_DENIED` | Non-execution envelope | source read |
| `APPROVAL_REQUIRED` | Non-execution envelope | prior M30 evidence |
| `UNSUPPORTED` (genuine — no plausible match at all) | Non-execution envelope | Gemma eval scenario 2 |

**Not terminal today, despite being a valid decided outcome:**

| Gate outcome | What actually happens | Should be |
|---|---|---|
| `INVALID_PROPOSAL` from the "false unsupported claim rejected by directory" branch **only** (`decision_gates.py:296-300`) | `engine_failure:INVALID_PROPOSAL` → **legacy fallback** | Terminal — `_canonical_nonexecution_envelope()` already renders this correctly today (its `contract.get("mode")=="unsupported"` check does not care what the raw `outcome` string is), it is simply never reached because dispatch intercepts it first |

## 5. Missing Valid Outcomes — Precise Answer

**None of the eight modes the User listed (`conversation`, `clarification`,
`unsupported`, `disconnected`, `approval_required`, `single_action`,
`multi_action`, `workflow_continuation`) is categorically missing terminal
treatment.** Seven of the eight are already correctly terminal in every
code path that produces them (§4, verified). The single gap is narrower
than "a whole mode is missing": it is **one specific gate-outcome-producing
branch within the `unsupported` mode's own handling** —
`decision_gates.py:296-300` — whose result is real and decided but is
mislabeled with the same enum value (`INVALID_PROPOSAL`) used for genuine
engine/proposal defects, and the dispatch function cannot tell the two
apart because it only receives the outcome string, never *why* the gate
produced it.

`workflow_continuation`'s own `mode_not_executable:workflow_continuation`
fallback (line 244-245) was already identified and independently
confirmed correct/intentional in the M30.8 Claude audit
(`docs/plans/M30_8_CLAUDE_AUDIT.md` §2) — not re-litigated here.

## 6. Narrowest Repair (identified, not implemented)

**Single function, additive signature change, zero effect on any other
outcome/mode:**

1. `decide_fallback_reason()` (`canonical_execution.py:225`) gains one more
   keyword parameter, `reasons: Sequence[str] = ()`.
2. Its one call site (`run_canonical_for_ask()`, where it is invoked with
   `gate_outcome=gate_result.outcome, capability_id=capability_id, mode=mode`)
   is updated to also pass `reasons=gate_result.reasons`.
3. One new condition, checked before the existing blanket
   `INVALID_PROPOSAL`/`DEGRADED` → `engine_failure` rule:

```python
if gate_outcome == "INVALID_PROPOSAL" and "false_unsupported_claim_rejected_by_directory" in reasons:
    return None  # a real, decided outcome - let the non-execution envelope render it
```

**Why this is the narrowest option, not the alternatives considered:**

- **Rejected: relabel `decision_gates.py:296-300`'s outcome as
  `UNSUPPORTED`.** Semantically backwards — the gate is asserting the
  model's unsupported claim is *false* (a real, available candidate
  exists); calling the result `UNSUPPORTED` would contradict the gate's
  own `reasons` field in telemetry and be actively misleading to a future
  auditor reading `canonical_execution_log.jsonl`.
- **Rejected: broaden the carve-out to `mode == "unsupported"` generally**
  (not reason-string-scoped). This would also suppress fallback for a
  genuinely hallucinated-capability-name `unsupported` proposal (a real
  model defect, correctly fallback-worthy today) — over-broad, violates
  "smallest blast radius."
- **Rejected: give the gate action-level plausible-matching** (checking
  whether the candidate's specific action schema actually covers the
  request, not just capability-level existence+availability) so the
  `false_unsupported_claim_rejected_by_directory` verdict itself becomes
  more accurate. This is the *semantically* more complete fix and may be
  worth doing eventually, but it is **not** the narrowest repair: it adds
  a new deterministic check to `capability_relevance.py` and
  `decision_gates.py`, changes what the gate *decides* (not just how it
  is *dispatched*), and needs its own separate evidence/test pass. Flagged
  here as a follow-up candidate, explicitly out of scope for the narrowest
  fix.
- **This repair changes zero bytes in `decision_gates.py`.** The gate's
  own classification, telemetry, and `reasons` string are untouched —
  only `canonical_execution.py`'s dispatch decision changes, and only for
  this one, already-uniquely-named reason string.

## 7. Tests Needed (not yet written)

1. **Unit, `decide_fallback_reason()` directly:** `gate_outcome=
   "INVALID_PROPOSAL"`, `reasons=["false_unsupported_claim_rejected_by_
   directory"]` → asserts `None` (no fallback).
2. **Regression, same function:** every other `INVALID_PROPOSAL`-producing
   reason string (`unknown_capability`, `unknown_action:...`,
   `continuation_without_active_pointer`, `continuation_no_durable_
   capability`, `mode_<x>_requires_a_capability_reference`) still returns
   `engine_failure:INVALID_PROPOSAL` — proves the carve-out does not
   overreach.
3. **Integration, `run_canonical_for_ask()`:** a fixture reproducing
   Gemma eval scenario 5's shape exactly (mode=`unsupported`, no capability
   named, a real, available, differently-scoped candidate capability) —
   asserts the returned envelope has no `_canonical_fallback` key and its
   `response.message` reflects the honest unsupported reason, not a
   legacy-drafted response.
4. **Telemetry shape:** `build_canonical_telemetry()`'s output for this
   case still records `gate_outcome: "INVALID_PROPOSAL"` (the gate's own
   honest classification is preserved for audit) while `fallback_used:
   False` and `fallback_reason: None` — proves this is a dispatch fix, not
   a telemetry cover-up.
5. **Live re-run of the two Gemma eval scenarios** (5 and 8, same prompts,
   same `model_roles.json` override methodology as
   `docs/research/GEMMA4_EVALUATION_REPORT.md`) after the fix, confirming
   `canonical_gate_outcome` still reads `INVALID_PROPOSAL` in the raw
   telemetry trace but the actual returned envelope is now the
   non-execution one, not a `_canonical_fallback` dict.
6. **Full regression suite**, per this project's standing practice — no
   new failures beyond the current disclosed baseline
   (`docs/plans/M30_8_CLAUDE_AUDIT.md` §5).

## 8. Does This Block M30.8 Legacy Retirement?

**Yes — it blocks Phase A's own exit criteria, which are themselves the
precondition for Phase B.** Quoting the plan directly
(`docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_PLAN.md` §B.3, item
3): *"the legacy fallback path is invoked, over that window, **only for
genuine model-unavailability/malformed-output/engine-failure reasons**...
A real disagreement of this second kind is not a Phase A failure to
silently tolerate — it is a signal to pause and investigate before
proceeding to Phase B."*

The defect in §3 produces exactly that second kind of disagreement: a
structurally valid, well-reasoned `unsupported` decision is mislabeled as
an engine failure and routed to legacy. Left unfixed, it would:

- Pollute the Phase A live-observation window's own fallback-reason
  telemetry with false `engine_failure:INVALID_PROPOSAL` entries for
  turns that were never actually engine failures — undermining the
  observation window's entire purpose (proving legacy is invoked *only*
  for genuine failures).
- Make it impossible to honestly certify §B.3 item 3 as holding, since at
  least one confirmed, reproducible non-genuine-failure fallback path
  exists in the current code.

It does **not** block Phase A's *mechanical* correctness for every other
mode (§4-5 confirm the other seven modes are already correctly terminal),
and it does not, by itself, invalidate anything already `ACCEPT`ed in
`docs/plans/M30_8_CLAUDE_AUDIT.md` (that audit's own regression suite did
not happen to exercise this exact branch — a real, disclosed evidence gap,
not a contradiction of that audit's findings).

**Recommendation:** fix (§6) before starting or continuing the Phase A
live-observation window — otherwise its own output cannot be trusted for
the purpose the plan itself defines it for.

---

## 9. Self-Review Against Acceptance Criteria (§1)

1. ✅ Exact function/line cited (§2), not paraphrased.
2. ✅ The specific branch reproduced from actual source, cross-checked
   field-by-field against both Gemma eval scenarios' real output (§3).
3. ✅ Every mode/outcome pair enumerated with source citation (§4).
4. ✅ Missing treatment narrowed to one specific branch, not a whole mode,
   with the root cause (capability-level check standing in for
   action-level fit) stated explicitly (§5).
5. ✅ Narrowest repair identified with two rejected alternatives and why
   each was rejected (§6) — no schema change, no change to
   `decision_gates.py`, single function touched.
6. ✅ Six concrete tests named, including a live re-run of the exact
   triggering scenarios (§7).
7. ✅ Blocking judgment grounded in the plan's own quoted text, not a new
   standard invented for this audit (§8).
8. ✅ No implementation performed.

**Gap disclosed:** the deeper question of whether `decision_gates.py`'s
plausible-match-based "false unsupported claim" heuristic should itself
gain action-level checking (§6, rejected alternative) is a legitimate,
separate follow-up question this audit does not resolve — flagged, not
silently dropped.

---

## 10. Repair Implemented and Verified — CLAUDE ACCEPT (2026-09-14)

User approved the exact narrow repair in §6; implemented precisely as
scoped, nothing broader.

**Change:** `canonical_execution.py`'s `decide_fallback_reason()` gained
one additive `reasons: Sequence[str] = ()` parameter and one new
condition, checked before the existing blanket rule:
`if gate_outcome == "INVALID_PROPOSAL" and "false_unsupported_claim_
rejected_by_directory" in reasons: return None`. Its one call site
(`run_canonical_for_ask()`) now passes `reasons=getattr(gate_result,
"reasons", ())` (defensive `getattr`, not direct attribute access - keeps
every existing hand-built `SimpleNamespace` gate fixture in the test suite
working unchanged, since none of them previously set `.reasons`).
**Zero bytes changed in `decision_gates.py`.** No schema change. No other
`INVALID_PROPOSAL` cause affected.

**All 6 planned tests run, all pass:**

1. Unit (`test_false_unsupported_claim_rejected_is_a_completed_decision_
   not_a_fallback`) — `reasons=["false_unsupported_claim_rejected_by_
   directory"]` → `None`. PASS.
2. Regression (`test_other_invalid_proposal_reasons_still_fall_back`) —
   6 sub-cases (empty reasons, `unknown_capability`, `unknown_action:...`,
   both continuation-error reasons, a generic mode-requires-capability
   reason) all still return `engine_failure:INVALID_PROPOSAL`. PASS.
3. Integration (`test_false_unsupported_claim_rejected_terminates_
   through_canonical`) — both exact Gemma eval reason strings (DOCX→LaTeX,
   Gmail send) run through the real `run_canonical_for_ask()` dispatch;
   neither carries `_canonical_fallback`; both return `status: "unavailable"`
   with the original `unsupported_reason` as the message. PASS.
4. Telemetry (`test_false_unsupported_claim_telemetry_records_no_
   fallback`) — real telemetry record read back from a temp JSONL file:
   `gate_outcome: "INVALID_PROPOSAL"` preserved (the gate's own honest
   classification stays in the audit trail), `fallback_used: false`,
   `fallback_reason: null`. PASS.
5. **Live re-run, real `gemma4:12b` output, exact original prompts**
   ("convert my thesis docx into a properly formatted LaTeX file"; "send
   that email"), through the real `run_canonical_for_ask()` end-to-end
   (same `uri_workspace/model_roles.json` override methodology as
   `docs/research/GEMMA4_EVALUATION_REPORT.md`, written and deleted for
   this verification only — no source touched, no production default
   changed): both scenarios now return `is_fallback: false`,
   `fallback_reason: null`, with the identical honest messages observed
   in the original eval. **Confirms the fix closes the real, originally-
   observed defect, not just a hand-built fixture.**
6. **Full regression**, `pytest -q --ignore=test_evidence_pipeline.py`:
   **1,759 passed, 16 failed, 40 subtests passed** — the exact same
   16-item baseline (the standing 8-item pre-existing baseline + the 8
   `qwen3:14b`-removal `ENVIRONMENT_CHANGED` failures already disclosed in
   `docs/plans/M30_8_CLAUDE_AUDIT.md` §5, `qwen3:14b` still absent from
   this environment) by exact test name, **zero new failures**. The +4
   passed / +8 subtests over that prior run are exactly this repair's own
   4 new test methods (2 of which are parameterized with sub-cases).

**`decision_gates.py` diff confirmed empty** (`git diff --stat` — no
output) before and after this repair, per the User's explicit "do not
modify decision_gates.py" instruction.

**Verdict: ACCEPT.** The repair is bounded, verified against real
production code paths and real Gemma output (not just synthetic
fixtures), introduces zero regressions, and closes the defect identified
in §3-§8 exactly as scoped — no broader "unsupported" handling change, no
capability-matching redesign, no schema change.

**Per the User's own instruction, M30.8 observation/retirement work may
now continue** (this repair was the blocking item identified in §8) —
not resumed automatically in this same turn; awaiting the User's specific
direction on how to proceed with the Phase A live-observation window.
**No commit or push has been performed** — awaiting separate, final User
approval for that, per the User's explicit instruction.

