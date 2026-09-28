# M33.3-R independent closing audit evidence

Original implementation evidence is preserved outside this directory. This directory records the independent audit, September 27-28, 2026.

- `initial_status.txt`: unrelated work inventory, excluded from release.
- `candidate-original-full.*`, `baseline-original-full.*`: identical tracked-file test selection in independent CRLF checkouts.
- `repaired-crlf-full.*`: intermediate repaired suite, before the final stale-lease revocation assertion. The attempted checkout-index normalization did not eliminate CRLF; do not label this LF evidence.
- `tracked_test_files.json`: 248 original tracked pytest files; final run additionally includes `tests/test_m33_3_r_closing_audit.py`.
- `repaired_source_overlay.json`: LF-normalized SHA-256 of the final code/test overlay used in the clean LF export. Governance-only finalization may follow that checkpoint.
- `failure_comparison.json`, `failure_adjudication.json`: per-test baseline comparison, not a blanket waiver.
- `candidate_threshold_gate.json`: original immutable gate; current gate changes input pins only, not numeric criteria.
- `S5_FINAL_*`, `s5-independent-recomputation.json`: fresh prompt-v4 qualification and independently recalculated scores.
- `M33_3_R_S10_RESIDENCY_*`: first independent repaired study. `s10-final/` repeats the study after the final stale-permission revocation fix.
- `S8_REPLAY_RESULTS.json`: current-gate replay; one qualified route, with a separate seeded held-out method check.
- Flutter logs retain full tests, scoped analysis, and the independently reproduced baseline full-app analyzer INFO.
- `durable-isolated-configured.log`: clean baseline isolated regression with a synthetic test-only credential secret; unconfigured isolation is separately retained as an environment setup failure.

Reproduction: export candidate `d1feaf72f7b1322fe30cc21e2808d5eab09bcdf4` with `git -c core.autocrlf=false archive`, apply the recorded audit patch, run `python scripts/m33_3_r_anchors.py`, then `python -m pytest` with the recorded test-file list plus the audit regression. On the release commit, export that commit directly. S8 runs with `python scripts/m33_3_r_s8_replay.py`; live S5/S10 require the recorded local provider/model environment and must run serially.

Text log/XML views normalize trailing whitespace and line endings for repository diff hygiene. Exact captured originals are preserved in `raw_test_output.zip`, with raw and display hashes in `raw_test_output_manifest.json`. Findings, assertions and counts are unchanged.
