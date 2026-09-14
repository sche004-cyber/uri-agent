# M30.7A Canonical Live Evidence Report

## Evidence boundary

Live attempts used isolated loopback URI port 8765 with the three required
flags enabled. Real `POST /auth/login`, authenticated `GET /auth/me`, and
`GET /connections` succeeded for `URI_test2`; Gmail reported `connected`.
No executor, principal, Gmail service, grant, or model output was mocked.

| Scenario | Expected behavior | Evidence type | Live status | Canonical path used? | Real external system used? | Residual/blocker | Artifact/log reference |
|---|---|---|---|---|---|---|---|
| 1 Connected unread | Gmail grounded result | authenticated `/ask` | LIVE_PASS | `single_action`, Gmail/`list_labels`, READY, success | Gmail | None | telemetry `m30_7a_s1_unread` |
| 2 Disconnected unread | DISCONNECTED guidance | fresh live test | LIVE_FAIL | No fresh proof | No | Token invalidation/restart not completed; stale evidence does not close it | prior `m306-live-gmail-1` only |
| 3 Labels + search | two real Gmail actions | authenticated `/ask` | LIVE_PASS | `multi_action`, both actions, READY, success | Gmail | None | telemetry `m30_7a_s3_multi` |
| 4 Student continuation | accepted residual | prior audited evidence | DOCUMENTED_ACCEPTED_RESIDUAL | Prior only | Prior Gmail | Do not re-run per directive | `M30_7_STATE.md`, `M30_7_CLAUDE_AUDIT.md`, `m30-7-live-s4-20260913-c` |
| 5 Recurring job | unsupported/no tool | authenticated `/ask` | LIVE_FAIL | Gate UNSUPPORTED, no execute | No | Mode was clarification; no-clarification-loop criterion unproven | telemetry `m30_7a_s5_unsupported` |
| 6 Remember fact | canonical persistence | authenticated `/ask` | LIVE_FAIL | Contract was conversation, no capability | No | Exact mandated phrasing did not execute/persist canonically | telemetry `m30_7a_s6_remember` |
| 7 Gmail chain | grounded IDs/read/attachment | authenticated `/ask` | LIVE_FAIL | Initial clarification, no action | No execution | No safe grounded ID for follow-ups | telemetry `m30_7a_s7_chain` |
| 8 Draft/no send | awaiting approval/no send | `/ask` + source | LIVE_FAIL | MISSING_PARAMETER | No draft claimed | Canonical approval-pending state unproven | telemetry `m30_7a_s8_draft`; `gmail_service.py` |
| 9 PDF conversion | allowlisted canonical conversion | allowlist inspection | BLOCKED_BY_CURRENT_SCOPE | No | No | `convert_document` not allowlisted | `canonical_execution.py:74` |
| 10 Career advice | conversation/no tool | authenticated `/ask` | LIVE_PASS | conversation, no actions/no execution | No | None | telemetry `m30_7a_s10_conversation` |
| 11 Topic switch | pointer clears/fresh turn | prior live evidence | LIVE_PASS | Prior guarded canonical path | Prior Gmail setup | Closed evidence reused | `M30_7_WORKFLOW_CONTINUATION_REPORT.md`, `m30-7-live-s11-20260913-a` |
| 12 Provider failure | honest fallback | fresh live failure test | LIVE_FAIL | Not freshly exercised | No | Unreachable-provider condition not applied | No new artifact |

## Allowlist / M30.8 recommendation

The allowlist remains `{"Gmail", "remember_fact"}`. Reject A (no
per-capability evidence barrier) and B (new capability auto-reach). C alone is
premature while evidence is incomplete. Endorse C-refined for a separately
authorized M30.8: human-reviewed per-capability canonical admission with
Layer-3 proof; do not change it here.

## Structural demotion audit

Successful allowlisted/READY `run_canonical_for_ask()` returns from
`server.ask()` before legacy `process_user_input()`. Canonical Gmail uses only
`MultiActionDispatch.dispatch_explicit()`/`dispatch_chain_explicit()`;
canonical `remember_fact` uses `ApprovalGate.execute_tool()`.

Fallback (`invalid`, non-READY, non-allowlisted, non-executable, dispatch
error) returns `None`, after which legacy `process_user_input()` calls
`skill_memory.find_matching_skill()`, computes `capability_planner.plan()`,
and prioritizes model capability, model workflow, skill-memory direct plan,
then CapabilityPlanner. `planning_required` reaches model workflow or legacy
`WorkflowPlanner`/`WorkflowCapabilityRouter`; legacy model shapes can reach
`MultiActionDispatch.dispatch()`. These mechanisms do not compete after a
successful canonical return, but remain active fallback mechanisms. No scoped
M30.2 template-inventory artifact was found.

## Repair and verification

`orchestrator.py` now passes `capability_id=model_capability_proposal` in the
pre-execution clarification branch. New focused orchestrator-path regression
proves a `remember_fact` proposal persists that capability in the resulting
pause. `.venv\\Scripts\\python.exe -m pytest -q test_workflow_continuation.py`:
**9 passed**.

`GmailService.create_draft()` calls only `users().drafts().create()`; there is
no send method or `users().messages().send()` path in that class.

## Full regression

A fresh full repository `pytest -q` run was executed across the entire repository in 1562.19s (26:02):
- **Total Passed:** 1,726 passed (plus 27 subtests passed, 2 warnings)
- **Total Failed:** 8 failed
- **Baseline Comparison:** All 8 failures are exact matches to the known pre-existing baseline:
  1. `step3_test.py::test_drive` (AttributeError: 'DriveService' object has no attribute 'list_files')
  2. `step4_test.py::test_download` (AttributeError: 'DriveService' object has no attribute 'download_file')
  3. `test_m20_feasibility_validation.py::UnavailableCapabilityIsNotPromotedTests::test_strict_single_action_proposal_for_unavailable_capability_falls_back`
  4. `test_m20_recovery_loop.py::LearnedSkillFailureReachesRecoveryTests::test_learned_skill_failure_reaches_recovery_loop`
  5. `test_m20_recovery_loop.py::CapabilityPlannerFailureReachesRecoveryTests::test_capability_planner_failure_reaches_recovery_loop`
  6. `test_m20_semantic_interpreter_resilience.py::SemanticInterpreterFailureDegradesHonestlyTests::test_capability_planner_gets_the_degraded_result_without_raising`
  7. `test_m20_semantic_interpreter_resilience.py::SemanticInterpreterFailureDegradesHonestlyTests::test_raising_interpreter_does_not_fail_the_whole_turn`
  8. `test_usage_import_boundary.py::test_orchestrator_newline_count_does_not_increase`
- **New Regressions:** 0 (zero new failures across 1,734 total tests).

## Final disposition

**M30.8 NOT READY — scenarios 2, 5, 6, 7, 8, and 12 lack required live canonical closure under current allowlist-scoped execution.**

