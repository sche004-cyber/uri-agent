# M33.3 S4 — independent recovery audit, bounded repair, and requalification

**Verdict:** `S4_INDEPENDENT_AUDIT_REPAIR_REQUALIFICATION_ACCEPTED`; **state:** `S4_CLOSED_FROZEN` (2026-09-27). This closes the offline S4 experiment only. M33.3 remains incomplete; S5–S13, integration, component promotion, and production RAR adoption are not authorized.

## A. Baseline and independence

The actual checkout is `C:\Users\cheta\Development\Uri\_V1`, branch `m35-uri-v1-parallel-architecture`. Starting local and remote HEAD were both `5b23e2634b1251d96063d63ad25eb550c8c9ddac`; ancestry includes audited S4 baseline `851c521` and exact-byte detector addition `59b6013`. This audit was performed separately from the recovery implementer session that authored `5b23e26`. The auditor previously authored the original S4 implementation, disclosed here; the subsequent upstream recovery was authored by another implementer. Pre-existing modified `SKILL.md` and numerous unrelated untracked M35 files were left untouched.

Evidence read: M33.3 cross-plan/S4/Batch A plans and states, URI_STATE, original implementation and first independent audit reports, recovery report, A2.8I/J/K/L reports and batteries, S4 R1/R2 telemetry and aggregates, frozen corpus, S4 producer/scorer/runner, D1R/D1RQ, deterministic RAR, S1 authority, changed tests, governance validator, and Git history/diffs.

## B. Recovery diff audit

`851c521..5b23e26` changes 15 files: three mechanism files, S4 runner, five tests, two R2 evidence files, three state/governance files, and the recovery report. D1R/D1RQ add one closed-class preposition stop set to noun-phrase scanning. RAR RC-5 requires a nonempty actual `eliminated_ids` list before the singleton contrast shortcut may bind. The three S1/S2 protected-hash tests change only the RAR hash line and add a historical-hash comment. The scorer, corpus, producer, S1 authority, A9 fork, Batch A battery, and prior telemetry remain unchanged. No unrelated tracked changes appear in the recovery commits.

## C. Focused reproduction and repair

Historical code was loaded directly from `59b6013` (D1R) and `851c521` (D1RQ/RAR), then run against the committed corpus and candidate pools with `oracle_recency=False`. For `NB-B-05:r1`, both old detectors emit `that in an email`, type `email`; old RAR C2 binds `obj-c06f97` through `TYPE_FILTER` and C1 abstains. New detectors emit `that`, no type; C1/C2 abstain `AMBIGUOUS` in both control and producer. The stop set extends an existing preposition boundary without fixture text or IDs; preserved temporal constructions such as `the one before` pass focused tests.

For `NB-H-06:r1`, the old unchanged span `the other scan` carries `('no', 'the other')`. Old RAR C1 binds the sole scan through `CONTRAST_FILTER` despite zero eliminated candidates. RC-5 makes C1 abstain `UNKNOWN`; C2 remains `UNKNOWN`. Control and producer agree. Positive contrast after actual term or structural `rejected_in_turn` elimination and zero-elimination singleton cases pass the 17 generalized recovery tests. No fallback rebind appeared in the focused traces.

## D. Governance adjudication

- **PG-6 re-pin: accepted.** PG-6 requires the RAR hash to be verified before/after RAR-touching work, and the User expressly authorized Option B upstream repair and full requalification. The historical `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` pin is retained for the old A9/Batch A evidence; the repaired current mechanism is `4db775666868e09a9f7232707d67ec3b4070970a30145ad3c5b41bb86b5e1b95`. This is an audited version change, not a silent rewrite of historical results.
- **D1R tracking: accepted.** The exact `59b6013` blob hashes to `0347977372a3dfefa9d42780168b7724ce857eb8941696ec21e590fbff41be75`, the pre-repair S4 anchor. That commit added the file without a semantic edit; `5b23e26` then makes the bounded stop-set change to `0986503dd46e87773f2303e612ed8b552500588f9a027b5c9aab6795615ec8b3`.
- **Untracked A2.8F runner: repaired.** `scripts/m35_a2_8f_run.py` was genuinely untracked and had two further untracked imports. A fresh checkout could not import S4. The S4 runner now uses equivalent tracked A2.8J helpers and local D0/D1R adapters. All 79 corpus cases had exact adapter-output parity against the old helpers; two full replays retained the committed R2 decisions. All 33 locally loaded S4 modules used by the replay are tracked. The untracked script was not added or modified.
- **Batch A: historical evidence retained with explicit drift.** Its frozen Stage A evidence is a record of the old mechanism, not a claim that the changed RAR has the old hash. Fresh `run_det` decisions match all 96 frozen rows after excluding timing. Fresh G-R2 reports `REPRODUCTION_BASELINE_UNMATCHED` because the mechanism hash and A2.8K H0 counts changed. The Batch A plan permits this reported limitation and does not require re-freezing historical Stage A evidence before an independently requalified S4 experiment can close. Any future use of Batch A as a current-mechanism baseline must version/requalify it separately.

## E. Affected-layer requalification

The full relevant tracked regression suite passed: 625 tests and 178 subtests, covering S1–S4, RAR, ARN, A9, L5, and governance-facing tests. Fresh A2.8K L5 battery: 3,636 records plus 19 supplemental records, H0 wrong bindings 26→22 and H0 correct resolutions 160→160 versus frozen R2. Across all variants, 14 old wrong records become safe abstentions, no new wrong records appear, and all 926 correct records remain correct. Its six Phase 0 RAR safety invocations each passed 24/24. The implementer's exact 1/1,031 shared-query and 29/538 utterance sweep is supported by its evidence and the source diff but was not independently reconstructed in full; the focused historical comparison, full S4 replay, L5 battery, and affected tests were independently executed. Batch A G-R2 drift is disclosed above.

## F. S4 independent rerun

Two fresh in-process replays after the audit repair each produced 79 cases, 2,466 rows, 18 groups, and 1,512 scored rows. Decision fields matched each other and the committed R2 telemetry structurally; only elapsed-time fields were excluded. R1 had 2,442 rows. The 24 added rows are unscored detector finds caused by split spans in `NB-B-01` and `NB-C-04` across D1R/D1RQ, three conditions, and both paths; they abstain. The R1→R2 scored decision changes are confined to `NB-B-05` and `NB-H-06` (12 C1/C2 rows); C3 rule provenance also changes without outcome or classification change. Correct resolutions remain 130; target coverage remains 76/76 under the frozen scorer. Paired control/producer outcomes agree in the repaired cases.

## G. Safety gates

Independently recomputed R2 gates: wrong confident scored bindings **0**; producer-only wrong **0**; certainty wrong on scored rows **0**; candidate invention/unauthorized source **0** (enforced by replay); protected hashes unchanged before/after replay **true**; unscored certainty bindings **8**; attachment-anchor certainty **18** (8 unattributed, in NB-C-01/NB-C-02); `safety_gate_passed: true`. All 30 scored certainty rows are correct resolutions, and authority class is measured for every resolved row by the unchanged S1 classifier. The scorer and annotations were not changed.

## H. Residual limitations

Level 4b still has a singleton type path if another detector emits a wrong type. Level 5 may bind temporal `earlier/previous` when genuine recency ranks are supplied; the S4 production-shaped pool supplies no oracle ranks. The possessive scanner can still emit `Maya's copy in email` with an `email` type, but a direct two-candidate probe abstained under RAR due to unmatched substantive terms; this is a reachable detector limitation without a demonstrated S4 wrong binding. The turn-scoped attachment anchor produces the documented 18 certainty rows, including 8 unrelated unscored finds, under the User's experimental decision; it is not production approved. Curated candidate inventories and 816 unscored rows limit generalization. A-F4 acceptable alternatives and A-F5 attachment metadata remain historical limitations.

## I. Regression and anchors

`pytest -q tests` passed 550 tests/130 subtests; adding the five tracked root RAR tests gave 625 tests/178 subtests, zero failures or skips and one benign collection warning. The 17 implementer recovery tests and one audit-added fresh-checkout dependency test passed. The eight S4 anchor SHA-256 values exactly match the runner; non-target corpus/contracts/Batch A/A9 hashes are unchanged. D1RQ current SHA-256 is `42332d28eca4db3533a54174a3386e573b4e5495120ad3d537dd918d8aa80862` (old `49f5faa9b37051fec876f5523383b4e965422976562c52e12fc38c970bfa6b82`); S1 authority remains `3393b5bbe61616b6682de9e211e85d4e564ab8d55100a736adc97af8757e02cd`. Governance validator: `VALID`. Scoped `git diff --check` passed.

## J. Audit repair

The committed S4 replay imported an untracked A2.8F harness with untracked transitive dependencies. This blocked fresh-checkout reproduction. The bounded repair replaced only those helper imports in `scripts/m33_3_s4_replay.py` with behavior-equivalent tracked helpers and local adapters, preserving corpus, scorer, and mechanism code. Adapter parity (79/79 cases), two full replays, and the 625-test regression suite verified the repair.

## K. State and continuation

S1, S2, S3, and S4: `CLOSED_FROZEN`. M33.3: incomplete. Next slice authorization: **NO**. Subsequent planning/implementation requires its own repository-governed authorization; no production RAR adoption or integration event follows from this offline freeze.

## L. Commit/push

This report, the bounded runner repair, its fresh-checkout regression test, and the three S4 state/governance updates form the audit commit. Final commit ID and push equality are reported in the user-facing audit handoff after commit.

## M. Final verdict

`S4_INDEPENDENT_AUDIT_REPAIR_REQUALIFICATION_ACCEPTED`; `S4_CLOSED_FROZEN` for the offline experiment, with the Batch A historical pin drift and experimental limitations above preserved explicitly.
