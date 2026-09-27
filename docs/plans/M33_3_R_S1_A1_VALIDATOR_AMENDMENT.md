# M33.3-R — Amendment S1-A1: RenderValidator function-word allowlist

**Authority:** User decision at the M33.3-R S5 touchpoint (2026-09-27): "Reopen S1 allowlist — Authorize a bounded S1 validator allowlist amendment inside M33.3-R. S1 and S3 need requalification, and S5 is rerun after that." This reopens frozen S1 for this one bounded change only. S1 stays otherwise frozen. The amendment was made by the implementer and has not been independently audited; the M33.3 independent closing audit covers it.

## 1. Problem (evidence)

The S5 exploratory runs (`docs/plans/M33_3_R_S5_EXPLORATORY_REPORT.md` §4) showed that `validate_render`'s `V-UNSUPPORTED-FACT` check rejects every token not in a small closed allowlist. That includes ordinary grammar words such as "or", "of", "is", "a" and "please". In round 2, 23–30 % of Capable-model outputs were rejected only for such words. Plan A §6 defines the check's intent as catching invented facts: numbers, dates, proper nouns, quoted strings and file extensions. Function words carry none of these.

## 2. Change

`uri_v1/reference_clarification/render_validator.py`: `_ALLOW` is extended (additively, with a comment citing this decision) by closed-class English words only:
- determiners and quantifiers (a, an, this, that, these, those, each, any, another, both, either, neither);
- conjunctions (or, nor, but, if);
- prepositions (of, in, on, at, from, for, with, about, between, as);
- reader pronouns (your, it, its, ones, me, my, we);
- auxiliaries and the copula (is, was, were, be, does, would, will, may, might, have, has);
- generic clarification words (meant, refer, referring, want, like, choose, select, pick, confirm, match, please, option, options, here, listed, yes, no).

No number, date, name, file extension or domain noun was added. All other checks (`V-SCHEMA`, `V-SLOT-*`, `V-EXTRA-OPTION`, `V-LABEL-DUP`, `V-CROSS-SLOT`, `V-SELECTION`, `V-EXCLUSION`, `V-LENGTH`, `V-ORDER`) are unchanged.

**Selection discipline (disclosed).** The word classes follow grammar categories, not individual rejected outputs, but the need for the change was found in exploratory evidence. The User's thresholds were frozen in `fixtures/m33_3_s5/threshold_gate.json` before the fresh final run, and the gate records the amended validator's hash.

## 3. Hash re-pin

| File | Baseline `c2f5839` (LF SHA-256) | After S1-A1 |
|---|---|---|
| `uri_v1/reference_clarification/render_validator.py` | `903ef9fe74ca307ebacd05ea1e85b52236ad9016a87462e6cc3c3faf25ad3e0e` | `4a29cc25381668a1a10cef81f39165f0f49e0709d0b40366e99c0fb08b6a29f3` |

`scripts/m33_3_r_anchors.py` records the re-pin, keeping the baseline value as history. No other S1–S4 anchor changed.

## 4. Requalification

| Check | Result |
|---|---|
| S1 suites (`tests/test_m33_3_s1_*.py`), S2 suite, S3 battery suite | all pass (in the 384-test affected run, after the uri_v1 import-boundary repair) |
| S3 frozen battery v2 (`scripts/m33_3_s3_qualify.py`) | 82/82 (L1 60/60, L2 22/22); critical gates pass; battery hash unchanged `3a0250aa…3b01` |
| S3 L2 unsupported-fact defects (ARB-069/070/071: "Mars", "Venus") | still rejected |
| S5 deterministic grid | 0 violations; template valid on 60/60 |
| S12 fixtures | unchanged (template wording does not depend on the allowlist) |
| Protected anchors | OK after the recorded re-pin |
