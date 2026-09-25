# M33.3 Batch A — Bounded Repair R3 Report

**Status:** `VERIFICATION_READY_FOR_M33_3_A_R3_REAUDIT`. Not accepted. Not frozen. No Stage B authorization.
**Batch:** `M33.3-A` — Edge Intelligence Stage A Qualification Readiness
**Authorized action:** `BOUNDED_M33_3_A_REPAIR_R3`, per the independent R2 re-audit's verdict `REPAIR_REQUIRED` (delivered directly by the User; this is the first genuinely independent audit artifact this batch has received — R1 and R2 both preceded any external review).
**Implementer:** Claude Sonnet 5, bounded repair implementer. This report is an implementation report, **not** an audit.
**Baseline:** `f8b7e49c870fcfbbc5a074c80c6af96614a066a3` (R2, committed and pushed).

Preserved, not rewritten: `M33_3_BATCH_A_COMPLETION_REPORT.md`,
`M33_3_BATCH_A_REPAIR_REPORT.md` (R1), `M33_3_BATCH_A_R2_REPAIR_REPORT.md`.

---

## 0. The finding, independently reproduced before fixing anything

Per Verification-First, I reproduced the auditor's finding directly before
writing any repair.

1. `scripts/m33_3_batch_a_adjudications.py:147` (pre-R3):
   `if o.get("error_class"): continue` inside `required_coverage()` — any row
   with an error was skipped, so a committed-guess statement made earlier in
   that trace never got an adjudication entry at all.
2. Feeding `RWB-104`'s real text with a synthetic `TIMEOUT` through
   `score_row()` with no adjudication (the exact state the coverage skip would
   produce): outcome `TIMEOUT`, `committed_guess: False` — the auditor's
   reproduction, confirmed byte-for-byte. Supplying the adjudication by hand
   gives `UNSAFE_RESOLUTION`, also confirmed.
3. `scripts/m33_3_batch_a_run.py`'s `run_main_brain_case` (pre-R3): `final_text
   = msg.get("content") or ""` was reassigned on *every* loop iteration,
   including iterations that also carried tool calls and let the loop
   continue. If step *N*'s message carried a committed-guess statement
   alongside a tool call, and step *N+1* produced any further content, step
   *N*'s text was silently discarded before anything ever adjudicated it —
   whether the trace subsequently errored or completed cleanly. This is a
   broader defect than "after a later error": it can lose text after **any**
   subsequent step, error or not.
4. Consequence check: 78 of the 240 retained rows (28 in `main9b`, 50 in
   `main9b_simconfirm`) made more than one model call, so every one of them
   is a row where an earlier step's text *could* have been silently
   overwritten by this defect. The currently retained raw JSON stores only
   the final `final_text` value, never a per-step history, so **it is not
   possible to retroactively determine, for any of those 78 rows, whether an
   earlier step actually carried committed-guess text that was lost.** This
   is disclosed as a residual limitation in §5, not resolved by this repair.

---

## 1. Repository integrity

| Item | Value |
|---|---|
| Branch / starting HEAD | `m35-uri-v1-parallel-architecture` / `f8b7e49` |
| Frozen battery | unchanged, LF SHA-256 `06d0dfff…c3fa` (test-verified) |
| Frozen plans, M33.2/A9 artifacts, `uri_core/`, `uri_v1/`, `uri_ui/` | unchanged — `git diff f8b7e49` over the full protected-scope file set is empty |
| Retained raw provider outputs | unchanged — all six SHA-256 values match R2's forward anchor exactly (below) |
| Provider inference in R3 | **none** |

| File | SHA-256 |
|---|---|
| `env.json` | `3da72e1c0185a150c3567f0ced76662156966f49bde3fc978d877615abb9c1fa` |
| `needle.json` | `2a39272752575964f69ab29d9189afc0fcba791cccb5df6b9e68ba3d1045b413` |
| `det.json` | `b289935ff633959b529105dcd64ef1d131e4abf8f4cc6067e930f1dd7f026a05` |
| `gr2.json` | `b549bc8ab29800d36de07aee4e3243ff5bf7fb184181689c20f0eb64563272b2` |
| `main9b.json` | `dbd96498788df72efa005c996b11767039b66224e5b6b984d5860d004c605d45` |
| `main9b_simconfirm.json` | `dce3f01d12bfe22c63a7fc8ac1a34635304c51ca1874a4e29dbcacea34fd5375` |

---

## 2. Fixes

### R3-1 — Harness: retain every step's text, not just the last

`scripts/m33_3_batch_a_run.py`, `run_main_brain_case`. A new `text_events`
list records `{step, content, had_tool_calls, is_error_detail}` for **every**
non-empty message content the trace produces, appended, never overwritten —
including the content of a step that also carried tool calls and let the
loop continue, and including the exception-detail text captured on a
`RUNTIME_UNAVAILABLE`. `final_text` is kept unchanged for backward-compatible
display only; nothing downstream may treat it as the sole source of text
evidence. `text_events` is published in `telemetry`.

This is a forward-looking fix. It changes what **future** runs capture; it
cannot recover text the **already-retained** six files never stored (§0.4,
§5).

### R3-2 — Adjudication coverage: never skip an error row that has captured text

`scripts/m33_3_batch_a_adjudications.py`:
- New `captured_text_events(output)` returns the union of every
  `text_events` entry's content plus `final_text` (deduplicated), for both
  old-format (final-text-only) and new-format (with `text_events`) raw data.
- `required_coverage()` no longer skips a row merely because
  `error_class` is set. A row needs an adjudication whenever it has **any**
  captured text and its rule is ask/escalate-relevant (or it's a
  `PROPOSE_OR_ASK` row with no proposal) — error or not. An error row with
  genuinely no captured text (e.g. a bare `TIMEOUT` on the very first call,
  before any content exists) correctly still needs none — there is nothing
  to adjudicate.
- `build()`'s quote check now verifies each evidence quote against the union
  of all captured text for that row, not `final_text` alone.

Rebuilding the adjudication file against the current six retained raw files
produces the **same 67 entries**, since none of them has both an error and
non-empty text_events (they predate the harness fix and only ever had
`final_text`, and no retained row combines an error with a proposal). This
confirms the fix changes coverage logic correctly without altering any
currently published result.

### R3-3 — End-to-end regression tests (not scorer-only)

The R2 tests exercised only `score_row()` with a hand-constructed
adjudication — exactly the gap the auditor named ("the passing adversarial
tests exercise that latter, scorer-only path"). New tests in
`test_m33_3_batch_a_structural.py` drive the **full** harness → coverage →
scorer path with a mocked HTTP layer:

- `test_mid_trace_text_survives_a_later_step_that_overwrites_final_text` — a step-0 committed-guess statement (alongside a tool call) is retained in `text_events` even though step 1 produces different final text.
- `test_mid_trace_text_survives_a_later_timeout` / `_runtime_error` / `_malformed_output` — the same statement survives each of the three error classes.
- `test_end_to_end_mid_trace_commitment_is_unsafe_regardless_of_later_state` (parametrized over `continue`/`timeout`/`runtime_error`/`malformed`) — runs the mocked harness, derives `text_channel`/`adjudication`/`execution_evidence` exactly as `assemble()` does, scores the row, and asserts `UNSAFE_RESOLUTION` with `committed_guess: true` in all four cases.
- `test_end_to_end_clean_trace_with_no_commitment_stays_bare_error` — the required negative control: a trace with genuinely no committed text anywhere, followed by a `TIMEOUT`, scores the bare error class with `committed_guess: false`. No false positive.
- `test_required_coverage_no_longer_skips_error_rows_with_captured_text` / `test_required_coverage_skips_error_rows_with_no_captured_text` — unit-level confirmation of the coverage predicate itself, both directions.

All new and existing tests pass; see §4.

---

## 3. Offline rescore

Rebuilt `docs/plans/M33_3_BATCH_A_R2_TRANSCRIPT_ADJUDICATIONS.json` and
reassembled `M33_3_BATCH_A_TELEMETRY.json` / `_AGGREGATES.json` from the same
six unmodified raw files. **Zero changes to any published outcome, safety
gate, or Main-Brain-avoidance count** — expected, since no currently
retained row exercises the error+captured-text combination the fix newly
covers (§2, R3-2). The repair corrects the scoring machinery's soundness for
future and hypothetical inputs; it does not alter the current 240-row result
set, which the R2 report already established.

---

## 4. Test and validator results

- `test_m33_3_batch_a_battery.py` + `test_m33_3_batch_a_scorer.py` + `test_m33_3_batch_a_structural.py`: **all pass** (structural file alone: 27 passed, 0 failed).
- Same three files + `tests/governance`: **454 passed, 58 skipped**.
- `python scripts/governance/uri_state_validator.py`: `VALID`.
- M33.2 six-file regression: 58 passed, 2 failed — the same two pre-existing CRLF line-ending failures documented since R1; unrelated to this repair.
- `scripts/m33_3_batch_a_battery.py --check`: battery hash intact, `"ok": true`.
- `git diff f8b7e49` over the full protected-scope file set (`uri_core/`, `uri_v1/`, `uri_ui/`, the frozen plans, the frozen battery, the M33.2 fixtures/bridge/tests): **empty**.

---

## 5. Remaining limitations (disclosed, not resolved)

- **The core residual from this finding is not fully closed.** The six
  currently retained raw files were produced before the R3-1 harness fix
  existed, so they carry only a single `final_text` value per row, never a
  per-step history. For the 78 rows that made more than one model call
  (listed by case ID in `scripts/m33_3_batch_a_run.py`'s test coverage and
  reproducible via `len(telemetry["usage"]) > 1`), it is **not possible** to
  determine from retained evidence whether an earlier step carried a
  committed-guess statement that a later step's content silently overwrote
  before this repair existed to capture it. No such loss was found in any of
  the terminal texts already adjudicated in R2 (each was independently
  confirmed genuinely terminal for its row), but this is an unprovable
  negative given the data available — it is not a clean bill of health, and
  it is stated as such rather than implied away.
- Per the auditor's own instruction, this does **not** trigger
  `RERUN_REQUIRED_BY_REPAIR`: the fix is forward-looking, applies to any
  future run, and the current 240-row result set is unaffected because no
  retained row exercises the newly-covered combination.
- This R2 re-audit is the first genuinely independent audit artifact this
  batch has received. It should be retained as such (the auditor's own point,
  repeated here) before any eventual freeze.
- All limitations disclosed in the completion report (L-1..L-15), the R1
  repair report, and the R2 repair report still apply unchanged.

---

## 6. Files changed in R3

- `scripts/m33_3_batch_a_run.py`: `text_events` capture in `run_main_brain_case`.
- `scripts/m33_3_batch_a_adjudications.py`: `captured_text_events()`, corrected `required_coverage()`, quote check against the full text union.
- `test_m33_3_batch_a_structural.py`: 10 new tests (§2, R3-3).
- Regenerated offline (no content change): `docs/plans/M33_3_BATCH_A_R2_TRANSCRIPT_ADJUDICATIONS.json`, `M33_3_BATCH_A_TELEMETRY.json`, `_AGGREGATES.json`.
- New: this report.
- No change to `uri_core/`, `uri_v1/`, `uri_ui/`, the frozen battery, the frozen plans, or any M33.2/A9 artifact.

---

**Next authorized action:** `INDEPENDENT_M33_3_A_R3_REAUDIT`.
