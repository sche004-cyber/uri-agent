# M33.3 Batch A — Bounded Repair R4 Report

**Status:** `VERIFICATION_READY_FOR_M33_3_A_R4_REAUDIT`. Not accepted. Not frozen. No Stage B authorization.
**Batch:** `M33.3-A` — Edge Intelligence Stage A Qualification Readiness
**Authorized action:** `BOUNDED_M33_3_A_REPAIR_R4`, per the independent R3 re-audit's verdict `REPAIR_REQUIRED`.
**Implementer:** Claude Sonnet 5, bounded repair implementer. This report is an implementation report, **not** an audit.
**Baseline:** `0d759137a5517cceac59d96bdcd59fd200896daa` (R3, committed and pushed).

Preserved, not rewritten: `M33_3_BATCH_A_COMPLETION_REPORT.md`,
`M33_3_BATCH_A_REPAIR_REPORT.md` (R1), `M33_3_BATCH_A_R2_REPAIR_REPORT.md`,
`M33_3_BATCH_A_R3_REPAIR_REPORT.md`.

---

## 0. The finding, independently reproduced before fixing

Per Verification-First, I reproduced the finding before writing any repair.

`scripts/m33_3_batch_a_run.py:527-528` (pre-R4) truncated both `final_text`
and every `text_events[].content` to 2,000 characters before they entered
retained telemetry. I built a synthetic RWB-104 response: an ambiguity
question, 2,100 filler characters, then "I'll delete the old draft version
(F-102). Should I proceed?" — a genuine committed-target statement placed
past the cutoff. Running it through the real (pre-fix) harness:

```
full response length:        2,186
retained final_text length:  2,000
commitment present in full response:            True
commitment present in retained final_text:      False
commitment present in any retained text_event:  False
```

R3's own fix (retaining every step's text) was defeated by a truncation
applied at the moment that text was written into the returned telemetry
dict — R3 fixed *which* text survives across steps and errors, but not *how
much* of any single piece of text survives.

---

## 1. Repository integrity

| Item | Value |
|---|---|
| Branch / starting HEAD | `m35-uri-v1-parallel-architecture` / `0d75913` |
| Frozen battery | unchanged, LF SHA-256 `06d0dfff…c3fa` (test-verified) |
| Frozen plans, M33.2/A9 artifacts, `uri_core/`, `uri_v1/`, `uri_ui/` | unchanged — empty diff against `0d75913` |
| Retained raw provider outputs | unchanged — all six SHA-256 values match the anchor recorded since R2 |
| Provider inference in R4 | **none** |

| File | SHA-256 |
|---|---|
| `env.json` | `3da72e1c…` |
| `needle.json` | `2a392727…` |
| `det.json` | `b289935f…` |
| `gr2.json` | `b549bc8a…` |
| `main9b.json` | `dbd96498…` |
| `main9b_simconfirm.json` | `dce3f01d…` |

(unabridged values match `M33_3_BATCH_A_AGGREGATES.json`
`raw_evidence_sha256_at_r2`, unchanged since R2.)

---

## 2. Fix

`scripts/m33_3_batch_a_run.py`: `final_text[:2000]` → `final_text`, and
`[dict(e, content=e["content"][:2000]) for e in text_events]` →
`text_events` (no truncation). Safety-relevant text is retained in full;
the response is already bounded by the request's own `max_tokens=4096`, so
this adds no unbounded-growth risk. A comment records why, citing the R3
re-audit's exact reproduction (character ~2,090).

No other truncation exists in the pipeline — checked
`scripts/m33_3_batch_a_run.py`, `scripts/m33_3_batch_a_scorer.py`, and
`scripts/m33_3_batch_a_adjudications.py` for any other `[:N]` slice on
model-produced text; the only other hit (`lms_models[:2000]` at line 277) is
an LM Studio inventory listing used for a diagnostic string, not
safety-relevant text.

Re-verified after the fix, using the same synthetic response: retained
`final_text` length now equals the full 2,186 characters, and the commitment
is present in both `final_text` and `text_events[0]`.

---

## 3. Addressing the coverage-path critique

The R3 re-audit separately noted: *"Their claimed full coverage path is
narrower than stated: the test helper supplies an adjudication itself rather
than invoking `required_coverage()` and `build()`."* This is fixed by a new
test (`test_real_coverage_and_quote_pipeline_finds_commitment_past_2000_chars`)
that:

1. runs the real (fixed) harness against a mocked response containing the
   long committed-guess text, ending in a `TIMEOUT`;
2. writes that output into a synthetic raw file shaped exactly like the real
   retained files;
3. calls `m33_3_batch_a_adjudications.required_coverage()` directly against
   it and asserts the row is flagged as needing an adjudication;
4. calls `adj_mod.captured_text_events()` and confirms the exact quote
   `build()` would need to verify is present in the returned text union —
   the same check `build()` itself performs, not a re-implementation;
5. only then constructs an adjudication and scores the row, confirming
   `UNSAFE_RESOLUTION` with `committed_guess: True`.

This exercises the coverage/quote-verification machinery itself against
long, error-terminated text, not a hand-fed shortcut around it.

---

## 4. New tests

Added to `test_m33_3_batch_a_structural.py`:

- `test_full_response_past_2000_chars_is_retained_untruncated` — the harness alone, no error: full 2,186-character response retained verbatim in both `final_text` and `text_events`.
- `test_commitment_past_2000_chars_survives_a_later_timeout` — the same commitment, past the old cutoff, followed by a `TIMEOUT`: present in `text_events` after the fix.
- `test_real_coverage_and_quote_pipeline_finds_commitment_past_2000_chars` — the real `required_coverage()`/quote-union path (§3), not a hand-supplied adjudication; ends in `UNSAFE_RESOLUTION`.
- `test_retained_evidence_has_no_row_at_the_old_truncation_boundary` — an evidentiary check that none of the 240 currently retained rows' `final_text` values are anywhere near the old 2,000-char cutoff (all under 1,900), which is why this repair changes no published number.

---

## 5. Offline rescore

Rebuilt `M33_3_BATCH_A_R2_TRANSCRIPT_ADJUDICATIONS.json` and reassembled
`M33_3_BATCH_A_TELEMETRY.json` / `_AGGREGATES.json` from the same six
unmodified raw files. **Zero change to any outcome, safety-gate, or
Main-Brain-avoidance value.** The only diff versus the R3 commit is the
`adjudications.adjudicator` label wording (an R3-authored, never-before-committed
edit — see §7) and its cascading hash. This is expected and confirmed by
`test_retained_evidence_has_no_row_at_the_old_truncation_boundary`: no
retained row's text was ever close to the old cutoff, so no retained row's
score could have changed.

Reported gate counts, unchanged since R2: G-S1 `0 / 7 / 1 / 1`, G-S2
`0 / 12 / 0 / 3`, G-S3 `0 / 20 / 0 / 0`, G-S4 `0` (R-NULL / R-NEEDLE / R-9B /
R-9B-SIMCONFIRM order).

---

## 6. Test and validator results

- `test_m33_3_batch_a_battery.py` + `test_m33_3_batch_a_scorer.py` + `test_m33_3_batch_a_structural.py` + `tests/governance`: **458 passed, 58 skipped**.
- `python scripts/governance/uri_state_validator.py`: `VALID`.
- M33.2 six-file regression: 58 passed, 2 failed — the same two pre-existing CRLF failures documented since R1.
- `scripts/m33_3_batch_a_battery.py --check`: `"ok": true`.
- `git diff 0d75913` over the full protected-scope file set: empty.

---

## 7. Incidental correction carried from R3

R3's local edit renaming the adjudicator label (dropping the stale "requires
independent R2 review" wording to a round-neutral "requires independent
re-audit") had not yet been committed. It is included in this commit's diff
alongside the R4 fix; it changes no scoring value, only the label text.

---

## 8. Remaining limitations (disclosed, not resolved)

- The R3-disclosed residual stands unchanged: the 78 already-retained
  multi-step rows were produced before R3's per-step capture existed, so no
  audit of the current raw files can prove an earlier step's text was never
  lost to overwriting. This repair fixes truncation; it does not and cannot
  retroactively add per-step history to files that never recorded it.
- A later, explicitly authorized rerun would be needed for a clean historical
  determination on those 78 rows, exactly as the R3 re-audit stated. No rerun
  is authorized by this repair.
- All limitations disclosed in the completion report (L-1..L-15) and the R1,
  R2, R3 repair reports still apply unchanged.
- Per the auditor's note, the independent acceptance audit itself still has
  no durable repository artifact from any round; that should be recorded at
  freeze, by whoever performs the accepting audit, not by this implementer.

---

## 9. Files changed in R4

- `scripts/m33_3_batch_a_run.py`: removed the 2,000-character truncation on `final_text` and `text_events` content.
- `test_m33_3_batch_a_structural.py`: 4 new tests (§4).
- Regenerated offline (label-only diff, no value change): `M33_3_BATCH_A_R2_TRANSCRIPT_ADJUDICATIONS.json`, `M33_3_BATCH_A_TELEMETRY.json`, `_AGGREGATES.json`.
- New: this report.
- No change to `uri_core/`, `uri_v1/`, `uri_ui/`, the frozen battery, the frozen plans, or any M33.2/A9 artifact.

---

**Next authorized action:** `INDEPENDENT_M33_3_A_R4_REAUDIT`.
