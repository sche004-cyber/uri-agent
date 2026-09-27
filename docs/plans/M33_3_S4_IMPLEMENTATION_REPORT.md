# M33.3 S4 — implementation and qualification report

**Implementer status:** `IMPLEMENTATION_COMPLETE_AWAITING_INDEPENDENT_AUDIT`; safety/promotion gate **not passed**. No independent implementation verdict is asserted.
**Starting HEAD:** `0caf3dd5d11a7b5c8b7f18133955a785707505d7` on `m35-uri-v1-parallel-architecture`.
**Governing plan:** `M33_3_S4_OFFLINE_SOURCE_TO_CANDIDATE_PLAN.md` (PG-5 independent pre-audit accepted after F1/F2 repair and final input-allowlist check; §5 scorer correction independently accepted). Audit records: `M33_3_S4_PLAN_INDEPENDENT_PREAUDIT.md`, `M33_3_S4_PLAN_FOCUSED_INDEPENDENT_REAUDIT.md`.

## Implementation

- `scripts/m33_3_s4_source_to_candidate.py`: one offline, fail-closed producer over raw turn, session attachment IDs, and the C1/C2 authorized inventory. It constructs normalized source records with fixture provenance and projects them to the unchanged `RARQuery` contract. Source inputs are positively allowlisted; scorer fields cannot enter the producer. ID/title/current-attachment anchors require explicit grounded conditions, with conflicting or nonunique anchors suppressed. Candidate cap 16 and canonical source-record budget 16,384 UTF-8 bytes fail closed.
- `scripts/m33_3_s4_replay.py`: D0, D1R, D1RQ × C1/C2/C3 replay against unchanged `resolve_rar_deterministic_extended`, paired with a same-pool no-producer control. It verifies eight frozen hashes before and after, records provenance, outcomes, per-stage and full-boundary timings, case-level scorer classes, and grouped aggregates. No production caller imports this module.
- `tests/test_m33_3_s4_replay.py`: source isolation/provenance, invalid/over-budget input, anchor admission/rejection, frozen-corpus projection and replay, and wrong-binding scorer guards.
- Telemetry: `M33_3_S4_TELEMETRY.json` (2,442 rows) and `M33_3_S4_AGGREGATES.json` (18 arm/condition/path groups). Synthetic fixture IDs are retained; raw turns and source content are not included.

## Scorer correction during implementation

The first replay classified unannotated extra detector spans as false bindings. NB-A-02 annotates the filename while the raw turn also says "it"; NB-A-04 annotates the file ID while the turn also says "that's the scanned contract." Those extra spans lack ground truth and cannot be judged wrong. Plan §5 records this finding and the independent focused `ACCEPT`: retain them as `UNATTRIBUTED_DETECTOR_FIND` with semantic correctness `UNMEASURED`. No-reference K cases remain actual false-positive controls. The first telemetry is superseded by the corrected rerun; no detector, producer, RAR, or corpus was tuned to the result.

## Results and error analysis

The final replay ran 79 cases, 3 arms, 3 source conditions, and paired control/producer paths. On C1/C2, each arm has 76 annotated intended-target rows whose target IDs occur in its supplied inventory (76/76). This is **inventory-conditional coverage**; the authored variant inventory is not a live retrieval result. The producer yields +1 correct resolution per C1/C2 D0 arm and +2 per C1/C2 D1R/D1RQ arm versus the paired control. Those are small within-corpus differences, not independent generalization evidence. C3 supplies no candidates and serves only as an absence control.

There are **two distinct wrong confident-binding cases on annotated references**, present in both control and producer; no new annotated wrong-binding case is introduced by the producer:

| Case | Cell(s) | Observed failure | Disposition |
|---|---|---|---|
| `NB-B-05` | D1R/D1RQ × C2, both paths | `TYPE_FILTER` resolves `obj-c06f97` while the annotated target is `obj-d58a27`. | Existing detector/RAR-boundary failure; no S4 repair of frozen mechanisms. |
| `NB-H-06` | D1R/D1RQ × C1, both paths | `CONTRAST_FILTER` resolves a file ID although the expected outcome is `UNKNOWN`. | Existing unsafe resolution; no promotion claim. |

Those appear as 8 path/arm/condition rows. An additional 792 path/condition rows are `UNATTRIBUTED_DETECTOR_FIND` and are **excluded** from correct/incorrect binding counts because the corpus does not annotate their intent. Case-level rows, source provenance, anchor origin and rule attribution are retained for independent inspection. The timing fields are measured in microseconds on this local run; no governed threshold exists, and model/provider, live UI, CPU/RAM and real-source coverage remain `UNMEASURED`. Timings are neither deterministic nor a production latency prediction.

**Safety gate:** fails because the two annotated wrong bindings remain. The experiment is complete as negative evidence; S4 is not safe for adoption. A9 and frozen RAR were not changed to make the result pass. The current source producer enumerates a curated authorized inventory. It does not discover records from live session/files/Gmail/Drive, so it cannot answer live source coverage or provider-permission behavior. That is a material limitation for the independent auditor.

## Verification and integrity

- Focused S4 tests: **6 passed**.
- Combined S1/S2/S3/S4, A9/ARN/RAR, and governance regression after the state update: **441 passed, 112 subtests passed**.
- Runner pre/post hashes matched all eight anchors, including `rar_deterministic.py` `e02af25b…8fb649`, `rar_contracts.py` `4cc9aa43…6819`, Batch A `06d0dfff…d1c3fa`, the frozen corpus, A9 mechanism/fixtures, and D1R/D1RQ detectors. No protected file was edited.
- Governance validator after the state update: **VALID**, no DCL violations. Unrelated dirty M35 research files and `SKILL.md` were left untouched and will not enter the slice commit.

## Exact stop point

`S4_IMPLEMENTATION_COMPLETE: YES`; `S4_IMPLEMENTER_QUALIFICATION_RUN: YES`; `S4_SAFETY_GATE_PASSED: NO`; `S4_AUDIT_PENDING: YES`; `S4_CLOSED_FROZEN: NO`; `M33_3_COMPLETE: NO`; `NEXT_SLICE_AUTHORIZED: NO`. Independent audit must examine plan fidelity, scorer attribution and unknowns, source-inventory external validity, false-bind cases, timing, and governance before any acceptance or future slice.
