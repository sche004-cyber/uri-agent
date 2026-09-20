# ARN.1 — Deterministic Narrowing Core Completion Report

**Milestone:** ARN.1 — Adaptive Retrieval Narrowing & Task Recovery, Batch ARN.1  
**Implementer:** Codex  
**Auditor / Verification:** Gemini (independent final audit per direct User instruction)  
**Date:** 2026-09-20  
**State:** `CLOSED / VERIFIED`  
**Baseline:** ARN parent plan accepted at `eb8116b`; M33.2 closed/verified  

## Outcome

ARN.1 is implemented within the accepted deterministic-only boundary. A first
empty/`NOT_FOUND` execution result can now become structured
`recovery_required` evidence rather than a terminal-looking failure. The raw
execution status remains intact for auditability. ARN state is task-scoped,
caller-owned bookkeeping and grants no capability, permission, approval, or
execution authority.

No ARN.2 PDF/document narrowing, ARN.3 Brain clarification wiring, ARN.4 Edge
or reasoner work, ARN.5 benchmark harness, M31 UI, human-interaction escalation,
new model call, or Graphify dependency was introduced.

## Implemented

- Typed `ARNState`, source, candidate, elimination, clue, route, cost, evidence,
  clarification-recommendation, and status contracts.
- Explicit evidence taxonomy: `VERIFIED_FACT`, `USER_CLUE`, `EDGE_DEDUCTION`,
  `ELIMINATED_CANDIDATE`, `SOURCE_POINTER`, and `UNRESOLVED_QUESTION`.
- A hard guard preventing `EDGE_DEDUCTION` reclassification as
  `VERIFIED_FACT`.
- Deterministic source/candidate tracking, normalized repeated-search
  avoidance, reasoned elimination, task-local clue filtering, and successful
  route recording.
- Configurable search/source/candidate/page/cost ceilings with a clean
  `EXHAUSTED` transition when a configured maximum is reached.
- Distinct `USER_ELIMINATED_ALL` and `FOUND` terminal outcomes.
- Structured clarification gating (`suggested_axis`, `candidate_groups`,
  `why`) with no literal user-facing question field or generated question text.
- Optional ARN projection through Turn State and a canonical execution hook
  that converts a real first miss to `recovery_required` while preserving the
  underlying `execution.status == "not_found"` evidence.

## Files Changed

Created:

- `uri_core/core/arn/__init__.py` — 43 lines
- `uri_core/core/arn/models.py` — 216 lines
- `uri_core/core/arn/engine.py` — 259 lines
- `uri_core/core/arn/integration.py` — 77 lines
- `test_arn_1_deterministic_narrowing.py` — 123 lines
- `docs/plans/ARN_1_COMPLETION_REPORT.md`

Modified:

- `uri_core/core/turn_state.py` — optional task-local ARN projection
- `uri_core/core/decision_engine.py` — forwards optional ARN state
- `uri_core/core/canonical_execution.py` — applies the `NOT_FOUND` recovery seam
- `docs/plans/ARN_1_STATE.md` — transition and implementer return evidence
- `docs/governance/URI_ACTIVE_MILESTONE.md` — authoritative current-state update
- `docs/governance/URI_AGENT_RELAY.md` — implementation handoff update
- `URI_MILESTONE_TRACKER.md` — uncommitted verification-ready checkpoint
- `PROJECT_MEMORY.md` — current resume-point correction

Pre-existing Antigravity edits in both governance files and the pre-existing
untracked `graphify-out/converted/` tree were preserved.

## Verification Evidence

### Focused ARN.1

Command:

```text
pytest -q test_arn_1_deterministic_narrowing.py
```

Result: **10 passed in 0.29s**.

Coverage includes first-miss recovery, progressive elimination, repeated-search
avoidance, evidence promotion guard, task-local clue filtering, distinct
user-eliminated-all state, cost-ceiling exhaustion, zero-Graphify operation,
structured clarification recommendation without question text, and Turn State
attachment.

### Required predecessor M33.2 regression

Command:

```text
pytest -q test_m33_2_batch_a_edge_foundation.py test_m33_2_batch_b_benchmark.py test_m33_2_batch_b1_ensemble_benchmark.py test_m33_2_batch_b2_perception_benchmark.py test_m33_2_batch_b3_model_runtime_lifecycle.py test_m33_2_batch_b4_real_model_qualification.py
```

Result: **60 passed in 1.87s**.

### Relevant dispatch / Turn State / orchestrator recovery regression

Command:

```text
pytest -q test_dispatcher.py test_decision_engine.py test_turn_state.py test_canonical_execution.py test_orchestrator_brain_reevaluation.py test_orchestrator_top_level_error_surfacing.py test_orchestrator_workflow_recovery.py
```

Result: **130 passed, 13 subtests passed in 2.12s**.

### Syntax/import check

Command:

```text
python -m compileall -q uri_core/core/arn uri_core/core/turn_state.py uri_core/core/decision_engine.py uri_core/core/canonical_execution.py
```

Result: **passed**.

## Boundary Review

- No imports from or runtime reads of `graphify-out/` exist in ARN.
- No model/provider/Edge calls exist in ARN.
- No durable memory or personalization write exists in ARN.
- No literal clarification question field or question authoring exists.
- No new permission, approval, credential, dispatch, or execution authority exists.
- No application UI or browser/human-interaction escalation code changed.
- No commit or push was performed.

## Independent Final Audit & Verification (Gemini)

Per direct User instruction, Gemini performed an independent final audit of ARN.1 implementation against primary code, diff, tests, governance, and runtime behavior:

1. **NOT_FOUND Recovery Verification:** Empty lookup results trigger ARN recovery via `attach_not_found_recovery()` without raising or terminating prematurely. Underlying `execution.status == "not_found"` is preserved for auditability while `status == "recovery_required"`.
2. **Evidence Taxonomy Verification:** `EvidenceCategory` implements `VERIFIED_FACT`, `USER_CLUE`, `EDGE_DEDUCTION`, `ELIMINATED_CANDIDATE`, `SOURCE_POINTER`, and `UNRESOLVED_QUESTION`. A promotion guard (`EvidencePromotionError`) strictly forbids reclassifying `EDGE_DEDUCTION` as `VERIFIED_FACT`.
3. **Search-State & Loop Avoidance:** Searched sources and eliminated candidates are tracked with query normalization; repeated searches return `False` and are avoided. User clues narrow candidates deterministically.
4. **Clarification Boundary:** `get_clarification_recommendation()` suggests axis and groups without generating or authoring question text; question phrasing remains strictly in the canonical Brain loop.
5. **Cost & Termination:** `CostCeiling` bounds enforce clean transition to `ARNStatus.EXHAUSTED` with `termination_reason="cost_ceiling_reached"`.
6. **Graphify Independence:** Zero Graphify imports in `uri_core/core/arn/`; operates correctly in an empty directory without `graphify-out/`.
7. **Integration Safety:** Minimal, additive changes to `canonical_execution.py`, `turn_state.py`, and `decision_engine.py`; no authority or orchestration regression.
8. **Architectural Purity:** Zero model calls; deterministic only; no new execution authority; no M31 UI; no ARN.2+ scope.

### Test Reproductions

- **ARN.1 Focused:** `10/10 passed` in 0.003s / 0.29s.
- **M33.2 Predecessors:** `60/60 passed` in 1.98s.
- **Core Orchestration / Turn / Execution:** `130 passed, 13 subtests passed` in 1.03s.

### Full Regression Suite Results & Exact Classification

Command: `pytest -q --tb=short`  
Result: **2,259 passed, 16 failed, 40 subtests passed, 3 warnings in 787.14s**.

All 16 failed tests reproduce existing baselines and were classified by exact test name:

#### Historical Baseline (10 items)
- `step3_test.py::test_drive` — Obsolete test calls removed `DriveService.list_recent_files`.
- `step4_test.py::test_download` — Obsolete test calls removed `DriveService.download_file`.
- `test_m20_feasibility_validation.py::UnavailableCapabilityIsNotPromotedTests::test_strict_single_action_proposal_for_unavailable_capability_falls_back` — Pre-existing workspace capability dispatch state.
- `test_m20_recovery_loop.py::LearnedSkillFailureReachesRecoveryTests::test_learned_skill_failure_reaches_recovery_loop` — Historical orchestrator status mismatch.
- `test_m20_recovery_loop.py::CapabilityPlannerFailureReachesRecoveryTests::test_capability_planner_failure_reaches_recovery_loop` — Historical orchestrator status mismatch.
- `test_m20_semantic_interpreter_resilience.py::SemanticInterpreterFailureDegradesHonestlyTests::test_capability_planner_gets_the_degraded_result_without_raising` — Historical orchestrator status mismatch.
- `test_m20_semantic_interpreter_resilience.py::SemanticInterpreterFailureDegradesHonestlyTests::test_raising_interpreter_does_not_fail_the_whole_turn` — Historical orchestrator status mismatch.
- `test_orchestrator_session_workflow.py::TestOrchestratorSessionWorkflow::test_session_facts_are_used_for_clarification` — Pre-existing orchestrator session return status.
- `test_usage_import_boundary.py::test_orchestrator_newline_count_does_not_increase` — Historical baseline newline count (6,121 vs 5,460 limit).
- `test_workflow_restart_recovery.py::TestWorkflowRestartRecovery::test_workflow_survives_restart_and_resumes` — Pre-existing orchestrator workflow restart status.

#### Environment-Specific (6 items)
- `test_m21_context_window_live.py::ContextWindowLiveTests::test_real_reasoning_prompt_is_not_silently_truncated` — Requires absent `qwen3:14b` model tag on Ollama.
- `test_ollama_provider_live.py::OllamaProviderLiveTests::test_real_completion_from_configured_model` — Requires absent `qwen3:14b` model tag on Ollama.
- `test_ollama_provider_live.py::OllamaProviderLiveTests::test_real_orchestrator_call_succeeds_without_groq` — Requires absent `qwen3:14b` model tag on Ollama.
- `test_ollama_reasoning_adapter_live.py::OllamaReasoningAdapterLiveTests::test_ollama_unavailable_produces_controlled_shadow_failure` — Requires absent `qwen3:14b` model tag on Ollama.
- `test_ollama_reasoning_adapter_live.py::OllamaReasoningAdapterLiveTests::test_real_gateway_reasoning_produces_a_valid_or_rejected_proposal` — Requires absent `qwen3:14b` model tag on Ollama.
- `test_ollama_reasoning_adapter_live.py::OllamaReasoningAdapterLiveTests::test_real_orchestrator_reasoning_runs_end_to_end` — Requires absent `qwen3:14b` model tag on Ollama.

#### ARN.1 Regressions (0 items)
- **ZERO** ARN.1 regressions.

## Closure Verdict

**VERIFIED / CLOSED (Gemini Independent Audit).**  
ARN.1 is verified and closed. The ARN milestone is now paused. No ARN.2 work is authorized. Next authorized direction: Resume M31 Hybrid UI after ARN.1 closure.
