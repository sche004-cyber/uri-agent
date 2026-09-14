# M30-PFC Provider-Failure False-Consent Repair Report

**Implementation status:** COMPLETE — pending Claude's independent audit.

## Bounded implementation

- `UriOrchestrator._interpret_semantic_result_safely()` now walks the
  caught exception chain and adds `interpretation_unreachable: true`
  only when it contains `AllProvidersUnreachableError`. A malformed
  response remains the existing empty degraded result without that
  marker.
- The learned-skill selection branch is gated by the terminal-provider
  state. When gated, it returns a deterministic unavailable response
  before `ApprovalGate.execute_tool()`, learned-skill execution, or
  session persistence.
- `SkillMemory.find_matching_skill()` now rejects an empty task type
  plus empty domain before scanning persisted skills.

No changes were made to `remember_fact.py`, `MemoryStore`, provenance
or consent models, `capability_planner.py`, `WorkflowPlanner`, or the UI.

## Automated verification

`test_provider_failure_false_consent_repair.py` adds nine focused
tests covering:
1. Terminal provider failure + unrelated request cannot execute `remember_fact`.
2. No persistent memory side effect occurs (`MemoryStore.add()` never called).
3. No false `user_provided` provenance is created.
4. Empty degraded task/domain cannot resolve to an executable learned skill.
5. Confident non-empty match cannot bypass live-turn terminal failure.
6. Healthy explicit disclosure still executes `remember_fact` with `consent: user_provided`.
7. Reached-but-malformed response does not set unavailable marker.
8. Reasoning fallback exhaustion also gates learned execution.
9. Terminal provider failure blocks approval execution and any other side-effecting capability execution, returning the deterministic model-unavailable response instead.

Together with the unchanged learned-skill regression suite:

```
.venv/Scripts/python.exe -m pytest -q \
  test_provider_failure_false_consent_repair.py \
  test_orchestrator_skill_memory_execution.py
15 passed in 22.29s
```

`test_m20_semantic_interpreter_resilience.py` was also run beside those
tests. Its two failures are the documented repository baseline failures
for that module; they predate this repair and do not exercise the new
terminal-provider gate.

## Live verification

Both checks used a real loopback server, a fresh bearer token from real
`POST /auth/login` for `URI_test2`, and authenticated `POST /ask`.
No executor, principal, or model result was mocked.

| Scenario | Observed result |
|---|---|
| `OLLAMA_BASE_URL=http://127.0.0.1:19999`; weather request | HTTP 200; top-level `status: unavailable`, `execution.status: unavailable`, `execution.tool: null`; response: “URI could not reach its model provider, so it did not execute this request.” The authenticated user's memory count remained **14 → 14**. |
| Healthy provider; `I work at NIT Sikkim.` | HTTP 200; `execution.status: success`, `execution.tool: remember_fact`; response confirmed saving the disclosure; memory count **14 → 15** and the persisted entry carried `consent: user_provided`. |

Both temporary loopback servers were stopped after verification. The
healthy-path write is a genuine explicit disclosure and was retained.

## Full regression

The full `pytest -q` run completed to an observed terminal result:

```
.venv/Scripts/python.exe -m pytest -q
8 failed, 1734 passed, 2 warnings, 27 subtests passed in 1463.09s (0:24:23)
```

The 8 failures exactly match the established repository baseline:
- `step3_test.py::test_drive`
- `step4_test.py::test_download`
- `test_m20_feasibility_validation.py::test_strict_single_action_proposal_for_unavailable_capability_falls_back`
- `test_m20_recovery_loop.py::test_learned_skill_failure_reaches_recovery_loop`
- `test_m20_recovery_loop.py::test_capability_planner_failure_reaches_recovery_loop`
- `test_m20_semantic_interpreter_resilience.py::test_capability_planner_gets_the_degraded_result_without_raising`
- `test_m20_semantic_interpreter_resilience.py::test_raising_interpreter_does_not_fail_the_whole_turn`
- `test_usage_import_boundary.py::test_orchestrator_newline_count_does_not_increase`

**Zero new failures introduced.** 1,734 tests passed.

## Handoff

This report is implementation evidence only. It does not declare the
milestone verified, and M30.8 remains not authorized pending Claude's
independent audit.
