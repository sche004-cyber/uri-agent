# M33.3 Batch A — R4 Independent Re-Audit Report (preserved verdict)

**Purpose of this artifact:** every prior round of this batch (planning,
implementation, R1, R2, R3) lacked a durable repository record of its
independent review — each review was delivered directly to the implementer
in conversation and never committed anywhere. This file closes that gap for
the R4 round only: it records the independently established verdict and
facts exactly as delivered, as a first-class repository artifact, per the
User's explicit instruction. It is **not** written by the auditor; it is
Claude Sonnet 5, the freeze implementer, transcribing the independent
auditor's own delivered findings faithfully. No interpretation beyond what
was delivered is added, and none of the independent auditor's own wording is
softened.

**Verdict:** `ACCEPT_WITH_DOCUMENTED_LIMITATIONS`
**Audited commit:** `930c1b50a0e3a2f5643f142b1a7a9935e82c54ee` (R4, branch `m35-uri-v1-parallel-architecture`)
**Auditor:** an agent other than the implementer (delivered directly to the implementer in the conversation that authorized this freeze; not Claude Sonnet 5 or Claude Opus 5.5 in their implementer capacity for this batch)

---

## 1. Repository integrity, as independently confirmed

- Branch `m35-uri-v1-parallel-architecture` at `930c1b5`, matching origin.
- Frozen battery, plans, six raw provider outputs, M33.2 and A9 protected evidence: unchanged.
- The R4 commit contains no `uri_core/`, `uri_v1/`, or `uri_ui/` changes.
- Unrelated dirty work (`SKILL.md`) preserved untouched.

## 2. Test and validator results, as independently reproduced

- `python -m pytest test_m33_3_batch_a_battery.py test_m33_3_batch_a_scorer.py test_m33_3_batch_a_structural.py tests/governance -q` → **458 passed, 58 skipped**.
- Governance validator → **VALID**.

## 3. R4 truncation repair, as independently verified

The 2,000-character truncation defect (final_text and text_events content)
was confirmed fixed: text is now retained in full. The new test exercising
the real `required_coverage()` / quote-verification pipeline directly
against long, error-terminated text (rather than a hand-supplied
adjudication) was confirmed present and confirmed to close the specific gap
the R3 re-audit had named.

## 4. Main-Brain-avoidance result, as independently confirmed

- Verified: **0**
- Potential: **0**
- Unverified: **22**

No earlier "19 verified" or "22 unnecessary calls" claim is restored. This
is the accepted, current figure.

## 5. Safety counts, as independently confirmed

G-S1 `0 / 7 / 1 / 1`, G-S2 `0 / 12 / 0 / 3`, G-S3 `0 / 20 / 0 / 0`, G-S4 `0`
— in R-NULL / R-NEEDLE / R-9B / R-9B-SIMCONFIRM order. Unchanged by R4.

## 6. G-R1 through G-R5 status, as independently confirmed

- G-R1: reproduces (8/8, 4/4).
- G-R2: reproduces.
- G-R3: battery/fixture hash stable across all steps; the disclosed R1 scorer edit during `main9b` remains the one recorded exception.
- G-R4: passes.
- G-R5: passes per row — all 180 model-condition rows (R-NEEDLE, R-9B, R-9B-SIMCONFIRM) carry verified artifact hashes and truthful statuses; R-NULL is explicitly "no provider." The Needle hash is independently re-hashed and correctly described as post-run evidence whose run-time identity is inferred from the cache file's timestamp, not proven by a run-time hash.

## 7. Provider execution, as independently confirmed

No provider rerun occurred at any point across R1, R2, R3, or R4. All
repairs were performed offline from the same six retained raw files.

## 8. Protected-scope integrity, as independently confirmed

No product/runtime files changed at any repair round. No Stage B work, no
`INT-*` event, and no next-experiment implementation occurred as part of any
repair or this freeze.

## 9. Batch A qualifies no Edge candidate and authorizes no Stage B work

Explicitly confirmed and restated here as a permanent record: this batch is
Stage A readiness / methodology evidence only. It does not establish Needle
qualification, resident-9B Edge qualification, a production Edge route,
end-to-end URI success, or Stage B readiness. No Edge candidate is qualified
by this batch, and no Stage B work is authorized by this freeze.

## 10. Documented limitations preserved by this acceptance (unsoftened)

- **Historical text gap (mandatory, prominent):** 78 retained rows had
  multiple model calls before per-step text recording existed. Missing
  intermediate model text cannot be reconstructed from retained evidence.
  Published text-dependent outcomes describe only the retained evidence; they
  cannot prove that no earlier model commitment was overwritten. A fresh,
  separately authorized run would be required for that stronger historical
  claim. This limitation does not block the Stage A freeze, and it is not
  softened or omitted here.
- No independent pre-repair raw-file hash anchor existed historically (a
  forward anchor was first recorded at R2).
- The pre-R1 scorer source was never committed; historical before/after
  values are reconstructed where applicable, not independently authenticated.
- The Needle artifact hash was recovered post-run and relies on
  timestamp/file identity for its run-time linkage, not a run-time hash.
- Four frozen battery cases remain over-strict, per repository disclosure:
  `RWB-072`, `RWB-082`, `RWB-103`, `RWB-105`. Changing them requires a new
  battery version, not modification of the frozen Batch A battery.

## 11. Future-run diagnostic-text edge, recorded for later, not implemented now

A first-call connection exception can currently be tagged as diagnostic/
error-detail text and may be treated by the adjudication builder as text
requiring transcript adjudication, even though it did not originate from the
model. Before the adjudication builder is reused for a future provider run,
diagnostic/system/error-detail text should be excluded from model-generated
text coverage unless it genuinely originated from the model. This does not
alter any current retained Batch A result and is not implemented by this
freeze — it is recorded as a requirement for a future run's harness/builder
design.

---

**This report records only what the independent auditor delivered.** Any
question about the reasoning behind a specific finding should be directed to
that delivered record (the conversation instruction that authorized this
freeze), not to this transcription.
