# M36 closing-audit repair verification

State: `M36_AUDIT_REPAIRED_AWAITING_FREEZE_DECISION`. Date: 2026-09-28.
Audited commit: `be4451c6fda7803a742e0ad48c7fec63140ec30b`. Audit report: [M36_INDEPENDENT_CLOSING_AUDIT_REPORT.md](M36_INDEPENDENT_CLOSING_AUDIT_REPORT.md).

**Independence disclosure:** the same Claude session that performed the closing audit made these repairs and ran the re-verification below. The re-verification is focused self-verification, not an independent audit. The User authorized repair, commit and push; freeze is not authorized.

## Repairs

| Finding | Change | Regression tests (`tests/test_m36_memory_audit_repairs.py`) |
|---|---|---|
| F-1 wrong CONFIRMED on negation | `contracts.negated()`: a closed deterministic cue set (not, no, never, skip, except, excluding, exclude, without, avoid, don't-family contractions, "other than", "instead of", "rather than", "apart from"). `envelope.ground()` applies it to the whole trusted raw turn instead of only the ref span. | `test_f1_negation_anywhere_in_turn_never_confirms` (8 forms, including a cropped span); `test_f1_positive_literals_are_not_negations` |
| F-2 negated status keywords | `recorder.task_state` rejects a user transition whose raw turn is negated (`EXPLICIT_USER_TRANSITION_REQUIRED`). | `test_f2_negated_status_words_are_not_user_transitions` (5); `test_f2_explicit_transitions_still_accepted` |
| F-3 verifier-registry mismatch on reload | `index.VerifierRegistryMismatch` (an `OSError`) is raised when a verdict with a *valid* receipt names a verifier/version that is not bootstrapped. The whole load fails closed: writes return `VERIFIER_REGISTRY_MISMATCH` and retrieval degrades with the same reason. Tampered receipts are still quarantined. | `test_f3_registry_mismatch_fails_closed_not_quarantined` (absent, v2); `test_f3_verified_completion_does_not_reopen_without_registry`; `test_f3_tampered_receipt_is_still_quarantined` |
| F-4 forget hides verdicts | A TOMBSTONE may not target a `VERIFIER_RESULT` outcome or a `TASK_STATE` record. A whole task is hidden through its `TASK_OPENED` record. | `test_f4_forget_cannot_hide_verdict`; `test_f4_forget_cannot_strand_task_but_can_hide_whole_task`; updated `test_hide_and_cross_user` |
| F-5 stem lineage | `retrieval.stem_title` uses the frozen `[_\.\-\/]` separator class. | `test_f5_dot_separated_stem_is_a_collision` |
| F-6 hidden files | Hidden/system *files* are listed in `ScanResult.hidden_names` and no longer make the scan incomplete. A hidden file whose name matches the expression makes the collision receipt incomplete (`HIDDEN_NAME_MATCH`), and the adapter rechecks it. Hidden *directories* remain whole-scan exclusions. | `test_f6_unrelated_hidden_file_does_not_block_exact_title`; `test_f6_hidden_file_with_matching_name_still_blocks`; `test_f6_hidden_directory_still_makes_scope_incomplete` |
| D-1 governance history | `URI_STATE.yaml` restores `pg_m1_verdict: PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS` and appends `pg_m1_final_verdict`. The A4 "PG-M2 blocked" scope text is annotated as historical. Closing-audit fields are added. | Governance validator |

The predeclared battery gains three negated forms (`negated_dont_title`, `negated_skip_title`, `negated_other_than_title`). Thresholds (`threshold_gate.json`, SHA-256 `e5fdeff5…af24af`) are unchanged.

## Re-verification (Linux, Python 3.11.15)

| Check | Result |
|---|---|
| M36 tests | 118 passed, 1 skipped (Windows junction test; platform) |
| `tests/` directory | 734 passed, 1 skipped, 130 subtests passed |
| Qualification driver | 72 cases × 2 runs, wrong_confirmed 0, invented_ids 0, deterministic; F-A/F-B E2E unchanged ([aggregates](M36_REPAIR_AGGREGATES.json)) |
| Full repository suite | 3,373 passed, 15 failed, 67 skipped. The 15 failures are the identical node IDs that failed at `be4451c` on this Linux host before repair (network/package-staging and pre-existing baseline tests; none touch Memory). The +28 passes are the new tests. On the User's Windows host, `be4451c` had the 11 baseline failures only. |
| Governance validator | VALID |
| Frozen anchors | ok=True, changed=[], 8 S4 + 24 LF, RAR SHA-256 `4db77566…5e1b95` |
| Frozen scope vs `291c9da` | No change under `uri_v1/turn`, `uri_v1/reference_clarification`, `uri_v1/evaluation`, `uri_v1/results`, `tests/test_m33_3*`, `uri_core` |
| `git diff --check` | Clean |
| Original audit probes ([m36_audit_probes](m36_audit_probes/)) | All 7 negation rows now PENDING; negated transitions raise; a registry mismatch raises instead of dropping verdicts; forget of a FAILED verdict is not persisted and the verdict stays in the package |

The Windows-only assertions (junction, reparse attributes, `MoveFileExW`) were not re-executed after repair.

## Accepted costs and residual advisories

- Whole-turn negation is conservative. Turns such as "update budget.xlsx, not the old one", and filenames tokenizing to a cue (for example `no-reply.docx`), clarify rather than confirm. They are never CONFIRMED.
- A registry mismatch makes the user's Memory unavailable until the matching verifier is bootstrapped. Whether retired verifier versions should stay registered is an open User architecture decision.
- Hidden file names are part of the scan snapshot digest, so an Office lock file appearing mid-round invalidates that round. This is conservative, and the behaviour is unchanged from before the repair.
- Audit advisories A-2..A-5 and A-8 are unchanged (see the report).
