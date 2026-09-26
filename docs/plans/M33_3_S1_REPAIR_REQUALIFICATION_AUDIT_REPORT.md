# M33.3 S1 — bounded repair, independent requalification, and freeze

**Date:** 2026-09-26
**Verdict:** `S1_REPAIR_REQUALIFICATION_ACCEPTED`
**Scope:** S1 isolated `uri_v1` reference clarification only. M33.3 remains incomplete; S2–S13 remain unauthorized.

## 1. Baseline and independence

- Branch: `m35-uri-v1-parallel-architecture`; starting HEAD and S1 implementation commit: `3cd5c03262e332684efc2c8c396fde7b585a032b`.
- Earlier implementation range supplied by the User: `ad9e2a6fef7b12c4aa4ecfde93fa06d397de7682..3cd5c03262e332684efc2c8c396fde7b585a032b`.
- Original audit verdict `S1_REPAIR_REQUIRED` and findings K-B1 through K-B4 were supplied in the User's repair package. The full original audit report is not stored in the repository. This run reproduced the failures from executable source before changing production code and reviewed repaired production paths rather than accepting the implementation report as proof. Codex also authored the earlier implementation, so this is an independent *evidence-based requalification of the repaired code*, not an auditor-identity separation from the original implementer; the supplied prior audit is the separate review.
- The pre-existing dirty `SKILL.md` and unrelated untracked M35/research/scratch files were preserved. Only the S1 files listed below were staged for closure.

## 2. Original defect reproduction and repair

| Finding | Before repair | Repair and verification |
|---|---|---|
| K-B1 Change source authority | X could still execute after X→Y; X could open another Change; two open Change rounds could both confirm. | `BindingRecord.superseded_by` preserves X's historical state/result while disabling its execution and further Change authority. The source claim and binding are atomic under the service lock. Sequential and simultaneous Change regressions pass; no redo executor was added. |
| K-B2 safeguard ownership | One `ClarificationSafeguards` instance charged session A and session B together. | Counters are keyed by `(session_id, turn_id)` and charged atomically. Same-turn accumulation still reaches the limit; another session or turn has its own budget. |
| K-B3 failed next-round build | Attribute builder exception left `PENDING`, `used=True`, and a premature clue. | Build completes before the old round is consumed or session clue recorded. A governed builder `ValueError` closes the round as `REJECTED` with `used=False`; `rebuild_rejected` remains usable. Attribute and free-input failures are tested. |
| K-B4 protected hash portability | The protected Python hash test read raw bytes and failed on CRLF worktrees. | The test uses Batch A's LF canonicalization. Synthetic LF and CRLF forms of both protected sources hash to the unchanged §13 anchors. |

Pre-repair probe output included `K-B1 X execution after rebind: TENTATIVE_APPLIED`, `K-B1 repeated Change: CHANGE_PENDING`, two `CONFIRMED` concurrent rebinds, session B's first action `REJECTED` at shared cost 2, and K-B3 `PENDING True [('owner', 'Alice')]` after a forced builder error. The F-4 case-only attribute probe raised `ValueError: duplicate attribute values`. The red regression run was **6 failed, 1 passed** before production repair.

## 3. Closely coupled findings and observations

The supplied package names F-4 explicitly but gives topics rather than exact ID-to-topic mapping for F-5 through F-9. The classifications below use the topics and do not invent an absent audit artifact.

| Topic | Classification | Disposition |
|---|---|---|
| F-4 case-only attribute values | `MUST_FIX_FOR_S1` | Group by normalized value. With distinct grounded labels, fall back to `CHOOSE_ONE`; when candidates have no grounded distinguishing facts, fail closed until a source supplies such facts. |
| Forged direct `BuildResult(CONFIRMED, ...)` | `MUST_FIX_FOR_S1` | `BindingService.register` reruns deterministic RAR and requires the same candidate and certainty class before storing a direct confirmation. Other direct binding states are rejected. |
| Stricter invalidation when an unclicked candidate changes | `NOT_A_DEFECT` | Plan A §7 explicitly allows a click on a still-fresh concrete item when another candidate changes. The clicked candidate's fingerprint and `ACTIVE_UI` rerun remain required. |
| Session adjunct only records evidence | `ACCEPTED_LIMITATION` | S1 stores session-local selections, clues, and corrections without promoting them to authority. R2.1 permits reordering among RAR ties and optional contribution to TENTATIVE; the frozen RAR resolution exposes no general tie equivalence signal. No ungrounded reorder or new certainty path was added. |
| Grounded title word rejected by renderer | `MUST_FIX_FOR_S1` | A title such as “Recommended Report” no longer triggers `V-SELECTION` merely because the exact phrase is grounded in that slot; unsupported selection claims still fail. |
| Bundle authority and presentation | `DEFERRED_BY_PLAN` for live presentation/integration; S1 contract `SATISFIED` | Contract validates dependencies, cycles, session/turn, and `COMBINED`/`SEQUENTIAL`; pending children stay hidden and a caller-supplied fresh query rebuilds a dependent. UI and production orchestration belong to S12/S13. |
| Truthy string in `fresh_authorized` | `MUST_FIX_FOR_S1` | Only literal `True` records `REDO_AUTHORIZED`; the string `"false"` remains `REDO_NOT_EXECUTED`. S1 still never executes redo. |
| Adversarial test gaps | `MUST_FIX_FOR_S1` where tied to repaired paths | Added source supersession, simultaneous competing Change, per-turn budget, both builder failures, CRLF hashes, case-only axis, forged confirmation, truthy authorization, and grounded render-word regressions. |

## 4. Files changed

Production: `uri_v1/reference_clarification/binding.py`, `store.py`, `attribute_narrowing.py`, `render_validator.py`.

Tests: `tests/test_m33_3_s1_repair.py`, `tests/test_m33_3_s1_governance_and_parity.py`.

Freeze/evidence: this report, `docs/plans/M33_3_S1_STATE.md`, `docs/plans/M33_3_CROSS_PLAN_STATE.md`, `docs/governance/URI_STATE.yaml`.

No frozen RAR source, Batch A fixture, `uri_core`, `uri_ui`, dependency manifest, model/provider code, or later-slice code changed.

## 5. Deterministic qualification and adversarial probes

All commands ran with `PYTHONDONTWRITEBYTECODE=1` and pytest cache disabled. No live provider/model test ran.

| Command | Result |
|---|---|
| `python -m pytest -p no:cacheprovider tests/test_m33_3_s1_core.py tests/test_m33_3_s1_binding_and_bundle.py tests/test_m33_3_s1_render.py tests/test_m33_3_s1_governance_and_parity.py tests/test_m33_3_s1_repair.py -q` | **61 passed** |
| `python -m pytest -p no:cacheprovider test_m35_uriv1_a2_5_rar_stage4_refinements.py test_m35_uriv1_a2_5_rar_contracts.py test_m35_uriv1_a2_5_rar_adversarial_safety.py test_m35_uriv1_a2_5_deterministic_rar.py test_arn_1_deterministic_narrowing.py test_m33_3_batch_a_structural.py test_m33_3_batch_a_scorer.py test_m33_3_batch_a_battery.py -q` | **501 passed, 58 skipped, 48 subtests passed** |
| `python scripts/governance/uri_state_validator.py` | `VALID: docs/governance/URI_STATE.yaml — no DCL violations found.` |
| `python -m pytest -p no:cacheprovider tests/governance/test_uri_state_validator.py -q` | **37 passed** |

Adversarial results: X execution and repeated Change after X→Y now fail; exactly one of two open or simultaneous Change confirmations succeeds. Session B and a new turn each retain a fresh budget after session A/old turn exhausts theirs. Forced attribute and free-input builder failures leave a closed, unused round with successful rebuild. LF and CRLF forms of protected sources canonicalize to the same hash. Existing S1 tests also cover stale click/fingerprint, wrong session, replay/expired round, candidate/attribute namespace, hidden overflow, free input outside RAR-returned scope, Change with edited/unknown result, malformed bundle, and provenance. No unexpected S1 failures remained.

## 6. Frozen integrity and architecture boundary

LF-normalized SHA-256 values (identical to `M33_3_S1_STATE.md` §13):

| Artifact | SHA-256 |
|---|---|
| `uri_v1/turn/rar_deterministic.py` | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` |
| `fixtures/m33_3_batch_a/battery.json` | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` |

`git diff --name-only 3cd5c03262e332684efc2c8c396fde7b585a032b -- uri_v1/turn/rar_deterministic.py uri_v1/turn/rar_contracts.py fixtures/m33_3_batch_a/battery.json uri_core uri_ui pyproject.toml requirements.txt` returned no paths. The S1 import-boundary test found no `uri_core` import in `uri_v1` and no model/provider/network dependency in the S1 package. State is process-memory only. A repository-wide `git diff --check` sees two trailing-space lines in the unrelated pre-existing `SKILL.md`; the staged S1 transaction is checked separately.

## 7. Independent contract re-audit

| Requirement | Status | Evidence and practical limit |
|---|---|---|
| D5 BindingService authority | `SATISFIED` | Direct certainty revalidated; click requires `ACTIVE_UI`; heuristic free input cannot confirm. |
| Change lifecycle and redo boundary | `SATISFIED` | Source supersession, atomic competing rebind, historical result preserved, literal positive redo authorization only; no redo executor. |
| Freshness, replay, expiry, session isolation | `SATISFIED` | Per-candidate fingerprint, one-use round, wrong-session rejection, per-session/turn safeguard ownership. |
| Builder failure and rebuild | `SATISFIED` | No partial clue/use commit; rejected round rebuilds from fresh query. |
| Free input, click, attribute narrowing | `SATISFIED` | Scope and `ACTIVE_UI` checks; normalized axis groups; attribute narrowing never directly confirms. |
| Bundle contract | `SATISFIED` | Deterministic dependency and presentation validation; live UI/orchestration is later-slice work. |
| Template and RenderValidator | `SATISFIED` | Template-kind tests and grounded selection-word regression; validator still rejects unsupported text. |
| Session-evidence influence | `PARTIALLY_SATISFIED` | Session-local records exist; no tie reorder or TENTATIVE promotion without a sound tie/evidence signal. R2.1 says these effects **may** occur; their absence creates no authority bypass. |
| Process-memory and architecture boundary | `SATISFIED` | No persistence, `uri_core`/`uri_ui`, model, provider, network, or new dependency. |
| Full milestone/live user behavior | `NOT_APPLICABLE` | S1 is fixture-only by frozen scope; S2–S13 and end-to-end acceptance remain open. |

## 8. Freeze state and commit/push evidence

The accepted transition is `S1_REPAIR_REQUIRED → S1_REPAIR_REQUALIFICATION_ACCEPTED → S1_CLOSED_FROZEN`. The authoritative S1 state, cross-plan state, and `URI_STATE.yaml` record:

`S1_IMPLEMENTATION_AUDITED: YES` · `S1_REPAIRS_REQUIRED: YES` · `S1_REPAIRS_VERIFIED: YES` · `S1_CLOSED_FROZEN: YES` · `M33_3_COMPLETE: NO` · `LATER_SLICE_IMPLEMENTATION_AUTHORIZED: NO`.

Batch A remains frozen, RAR remains frozen, and there is no S2 authorization or INT event. Commit and remote verification are recorded in the post-push addendum below so the evidence cites an actual Git object rather than a predicted hash.

## 9. Post-push addendum

The S1 repair/test/audit/freeze transaction was committed as `04cc35f896ded739b0f032eb0e498480a3ce2f0b` (`fix(m33.3): requalify and freeze S1 clarification`) on `m35-uri-v1-parallel-architecture`. `git push origin m35-uri-v1-parallel-architecture` succeeded with `3cd5c03..04cc35f`. A subsequent `git ls-remote origin refs/heads/m35-uri-v1-parallel-architecture` returned exactly `04cc35f896ded739b0f032eb0e498480a3ce2f0b`, matching local `git rev-parse HEAD` at that checkpoint. This addendum is an evidence-only follow-up commit; it changes no production code, tests, frozen artifact, or authorization state.
