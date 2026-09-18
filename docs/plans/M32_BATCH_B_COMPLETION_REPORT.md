# M32 Batch B — Canonical Execution Cutover: Completion Report

**Date:** 2026-09-18
**Author:** Claude, implementing directly for this milestone per an explicit, one-time User override of the standing AO-4 §12 routing (Batch B is normally routed to Codex; the User confirmed direct Claude implementation for this milestone only — see conversation record).
**Baseline:** clean HEAD `ea6af67` (M32 Batch A + C3.4 prerequisite, VERIFIED and pushed).
**Scope:** B1.1–B1.6, B1.5's flag decision, and the four §4 evidence-gap closures (attachment turn, keyword-template workflow, resumed approval, multi-action Gmail). Batch C explicitly out of scope and not started.
**Plan of record:** `docs/plans/M32_EXECUTION_ARCHITECTURE_PLAN.md` §4.
**Status:** NOT YET COMMITTED — awaiting User review per this task's own instruction to stop before commit/push.

---

## 1. B1.1–B1.6, item by item

| # | Requirement | Status | Evidence |
|---|---|---|---|
| **B1.1** | Canonical is the committed production default — not an env var nothing sets | **DONE** | `decision_engine_live_enabled()` (`canonical_execution.py`) now returns `True` when `URI_ENABLE_DECISION_ENGINE_LIVE` is unset; `"0"` is the explicit rollback lever. `test_flag_enabled_by_default`, `test_flag_explicit_zero_is_the_rollback_lever` |
| **B1.2** | Rollback lever (`CANONICAL_EXECUTION_ALLOWLIST`) made runtime-settable, no redeploy | **DONE** | New `URI_CANONICAL_EXECUTION_ALLOWLIST` env var, read by `_current_allowlist()`, takes precedence over the module constant when set (including an explicit empty string = full narrow). `RuntimeAllowlistRollbackLeverTests` (4 tests), including one that exercises the lever through `decide_fallback_reason` end to end, not just at the `is_allowlisted()` unit level |
| **B1.3** | Run the live battery against canonical | **PARTIAL** — no committed `scripts/m32_latency_battery.py` exists (PC3 was never closed by an earlier milestone); ad hoc live evidence was gathered instead (§4 below) using a direct `TestClient`-driven script, not a committed, repeatable battery. This is a residual gap, not a Batch B code defect — see §7 |
| **B1.4** | Record the M30.8 correction | **DONE** | Correction section added to `docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_REPORT.md`, preserved alongside the original report per this repository's auditable-correction-history convention |
| **B1.5** | Decide the second flag (`URI_ENABLE_WORKFLOW_CONTINUATION_MODE`) | **DONE**, plus one latent bug found and fixed | `workflow_continuation_mode_enabled()` now defaults `True` the same way as B1.1. **Found during implementation:** `decision_gates.py` carried its own, independent, still-hardcoded-off copy of this exact flag/function (lines 42–48, pre-existing since M30.7) — completely out of sync with `canonical_execution.py`'s copy the moment B1.1/B1.5 changed the latter's default. Fixed by making `decision_gates.py` import the flag and function from `canonical_execution.py` (the single source of truth) instead of duplicating them. `server.py:1346`'s own separate raw `os.environ.get(...) == "1"` check was also replaced with a call to the shared helper, closing the same class of duplication risk the plan's SR-13 finding warned about for Batch C |
| **B1.6** | Close the narrative-failure fallback gap | **DONE, correctly scoped** | The old bare `except Exception: pass` around `_draft_narrative_safely` is now defense-in-depth: `_draft_narrative_safely` already guarantees (by its own docstring and internal except clauses) that it never raises — it always calls `mark_narrative_unavailable` on failure. Falling back to legacy here would be unsafe (real execution has already happened; a second dispatch would risk a duplicate side effect), so the fix does not add a legacy fallback. It instead ensures that if `_draft_narrative_safely` were ever to raise anyway (a defect in that guarantee, not assumed away), the envelope still gets an honest `narrative_unavailable_reason` instead of silently having neither narrative nor record. `NarrativeDefenseInDepthTests::test_narrative_safely_raising_still_marks_envelope_unavailable` proves this with a real remember_fact execution and a narrative call forced to raise |

---

## 2. Exact files changed

```
 docs/plans/M30_8_CANONICAL_CUTOVER_LEGACY_RETIREMENT_REPORT.md |  36 +++++
 test_canonical_execution.py                                    | 157 ++++++++++++++++++++-
 test_workflow_continuation.py                                  |  19 ++-
 uri_core/app/server.py                                         |   4 +-
 uri_core/core/canonical_execution.py                           |  72 ++++++++--
 uri_core/core/decision_gates.py                                |  18 +--
 6 files changed, 281 insertions(+), 25 deletions(-)
```

Plus this report itself (new, untracked). No other file is modified or untracked as a result of this work — `git status --short` shows exactly these 6 tracked changes; the only other untracked entries (`.agents/skills/grill-me/`, `.agents/skills/uri-development/`, `graphify-out/*`) are unrelated tooling artifacts, not part of this change and not staged.

---

## 3. Focused test results

- `test_canonical_execution.py` alone: **44 passed, 13 subtests passed** (includes new `RuntimeAllowlistRollbackLeverTests` ×4, extended `AllowlistAndFlagTests`/`FallbackDecisionTests` for the default-on flip, and new `NarrativeDefenseInDepthTests`).
- `test_canonical_execution.py test_decision_engine.py test_decision_gates.py test_workflow_continuation.py test_server_ask_narrative.py` together: **129 passed, 13 subtests passed, 0 failed.**
- Two pre-existing tests broken **by design** by the B1.1/B1.5 default-flip, rewritten rather than deleted (per this repository's own convention for intentional breaking changes): `test_flag_disabled_by_default` → `test_flag_enabled_by_default` (+ new explicit-zero test), and `test_workflow_continuation.py::DurableMetadataTests::test_flag_off_retains_placeholder_continuation_result` → `test_flag_explicit_off_retains_placeholder_continuation_result` (+ new `test_flag_enabled_by_default_requires_durable_capability`, which proves the *new* default-on behavior correctly enters continuation validation instead of silently passing through).

## 4. Full regression result

`./.venv/Scripts/python.exe -m pytest -q` (full repository): **1844 passed, 18 failed, 40 subtests passed in 940.59s (15:40).**

18 failures decompose into two groups, both independently verified by inspecting each traceback — none are Batch B code defects:

**Group 1 — exact match to the pre-existing baseline (8 failures).** Identical to the 8 failures M30.7A's own full-suite run recorded (`docs/plans/M30_7A_CANONICAL_LIVE_EVIDENCE_REPORT.md`): `step3_test.py::test_drive`, `step4_test.py::test_download`, `test_m20_feasibility_validation.py::…test_strict_single_action_proposal_for_unavailable_capability_falls_back`, `test_m20_recovery_loop.py::LearnedSkillFailureReachesRecoveryTests`, `test_m20_recovery_loop.py::CapabilityPlannerFailureReachesRecoveryTests`, `test_m20_semantic_interpreter_resilience.py` ×2, `test_usage_import_boundary.py::test_orchestrator_newline_count_does_not_increase` (`orchestrator.py` is untouched by Batch B — 6153 lines, same pre-existing over-budget count as before this work).

**Group 2 — 10 new failure names, both traced to verified, pre-existing local-environment state, not to this session's code:**

- **8 of the 10** (`test_m21_context_window_live.py`, `test_ollama_provider_live.py` ×2, `test_ollama_reasoning_adapter_live.py` ×3, `test_orchestrator_session_workflow.py::test_session_facts_are_used_for_clarification`, `test_workflow_restart_recovery.py::test_workflow_survives_restart_and_resumes`) all raise or surface the identical root cause, confirmed directly in the traceback: `ModelNotFoundError: Model 'qwen3:14b' was not found on this Ollama server`. `DEFAULT_OLLAMA_MODEL = "qwen3:14b"` (`model_providers/base.py:99`) predates this session; the actually-installed local models are `gemma4:12b` and `qwen3.5:9b` (confirmed via `/api/tags`). This full-suite run did not set `OLLAMA_MODEL`, so any code path building a provider with no explicit role/env override hits this. **This is the same pre-existing environment/runtime finding called out separately below — not a Batch B scope change**, and not something B1.1–B1.6 touches.
- **2 of the 10** (`test_m19_office_readiness.py::GmailDraftAndDriveUploadSafetyTests` ×2) fail because a real, `.gitignore`d `token.json` currently sits at the repo root (confirmed: `git check-ignore -v token.json` → matched, never tracked, no git history) — these tests assert `"unavailable"` assuming no credentials exist locally, and now get `"success"` because a real install-wide Gmail token is genuinely present. Verified this is unrelated to A1-3: both tests construct `DriveUploadTool`/`GmailCreateDraftTool` directly (bypassing `ToolDispatcher` entirely, so the A1-3 `user_id`-injection change never runs), and `resolve_google_token_path(user_id=None)` is byte-for-byte identical to the pre-A1-3 code path for the no-`user_id` case. Pure local-machine state, not a code regression.

**Net: 0 new failures attributable to this session's Batch B code changes.**

## 5. Live evidence — all four §4 gap scenarios

Gathered via `fastapi.testclient.TestClient` against the real app (no mocked model output), ambient/unauthenticated path (no `Authorization` header — real, currently-supported production traffic per `server.py`'s own `_resolve_authenticated_user_id` docstring), real local Ollama (`gemma4:12b`), with `URI_ENABLE_DECISION_ENGINE_LIVE`/`URI_ENABLE_WORKFLOW_CONTINUATION_MODE` **both left unset** — proving the default-on behavior, not a flag-forced one.

| Scenario | Result | Detail |
|---|---|---|
| **Attachment turn** | **LIVE_PARTIAL** | Canonical itself behaved correctly: `mode=single_action`, `gate_outcome=MISSING_PARAMETER`, terminal `awaiting_user_response` envelope, honest clarification, no fabricated result. However the Brain selected capability `Gmail` instead of the registered `read_attached_file` for "what is the secret probe phrase in the file I just attached?" — a Brain tool-selection reliability issue (matches the plan's own R1 risk), not a canonical dispatch defect. |
| **Keyword-template workflow (institutional note)** | **LIVE_PASS** | `mode=single_action`, `capability=draft_institutional_note`, `gate_outcome=READY`, `canonical_execution_attempted=True`, executed successfully end to end under canonical (unset flags). This is the single scenario the plan flagged as "the most likely silent regression when canonical becomes default" (§4) — closed cleanly. |
| **Resumed approval across turns** | **LIVE_FAIL — genuine, disclosed finding** | Turn 1 (Gmail create-draft request) correctly returns `status=approval_required`, `gate_outcome=APPROVAL_REQUIRED`, honest narrative ("Your approval is required…"), `execution.status=not_executed` — no side effect, gate held. But this canonical terminal envelope carries **no durable action_id and sets no workflow-continuation state** on the session. A follow-up "Yes, please go ahead and create that draft" in the same session was **not** resumed — the Brain re-interpreted it as an unrelated fresh `content_generation` request and asked for unrelated clarification. See §7 for disposition — this is pre-existing, Tier-1/Batch C territory (durable cross-turn approval state), not something B1.1–B1.6 was ever scoped to build. |
| **Multi-action Gmail** | **LIVE_PARTIAL** | Dispatch mechanics genuinely proven live: `mode=multi_action`, `gate_outcome=READY`, `canonical_execution_attempted=True`, a real 2-action contract reached `_execute_gmail`'s chain-dispatch path. Full success was blocked by a **correct** grants-boundary refusal (`execution.status=permission_denied` on `search_messages`) — the ambient/unauthenticated probe has no granted `gmail_search` capability, which is S2 (an ungranted capability is refused) working as intended, not a defect. A fully-granted authenticated account would be needed for an end-to-end success; that is an access-provisioning matter, not a code question. |

## 6. Default-on confirmation, rollback confirmation, boundary integrity

- **Canonical is live without any env var set**, demonstrated directly: the live-evidence script printed `LIVE_ENV default: None` / `WORKFLOW_CONTINUATION default: None` immediately before every scenario above, and every scenario shows real `canonical_mode`/`gate_outcome` telemetry (not the fallback marker), proving canonical actually ran, unforced.
- **Rollback/override confirmed**, per the frozen plan's own rule ("a lever that has never been exercised is not a rollback lever"): `test_flag_explicit_zero_is_the_rollback_lever` (B1.1), `test_workflow_continuation_mode_disabled_falls_back` (B1.5), and `RuntimeAllowlistRollbackLeverTests::test_rollback_lever_restores_legacy_via_decide_fallback_reason` (B1.2) each exercise the lever and assert it actually restores the prior legacy-first outcome — not merely that the flag reads back correctly.
- **Grants, approvals, audit, and dispatch boundaries are unchanged**, verified two ways: (1) `git diff --stat` against `approval_gate.py`, `capability_resolver.py`, `capabilities/executor.py`, `multi_action_dispatch.py`, `dispatcher.py`, `orchestrator.py`, `decision_engine.py` — **zero diff on every one of them**; (2) live-demonstrated, not just inspected: the approval-required scenario above genuinely held the gate (no side effect until approval), and the multi-action Gmail scenario genuinely enforced the grants boundary (`permission_denied`) rather than silently succeeding.

## 7. Residual risks and unresolved items

1. **Resumed approval across turns does not work end-to-end** (§5). Real, disclosed, live-demonstrated. Not a B1.1–B1.6 defect — it requires durable cross-turn approval/pending-action state, which is Tier-1 continuation work explicitly scoped to Batch C (C3.7 loop bound, C3.9 idempotency/execution-identity). This should be treated as a concrete requirement Batch C must address, not a surprise discovered there.
2. **B1.3's live battery was not a committed, repeatable script** (`scripts/m32_latency_battery.py` still does not exist — PC3 was never closed by an earlier milestone). Live evidence was gathered ad hoc instead. Recommend PC3 be closed before or alongside Batch C so latency regressions are measurable, not just individually observed.
3. **Attachment-turn tool selection is unreliable** (Brain chose `Gmail` over `read_attached_file`) — a model-reliability finding for Batch C's tool-selection eval battery (R1), not a canonical code defect.
4. **Full multi-action Gmail success was not demonstrated** — blocked by a correct grants boundary in this ambient probe, not a defect; closing this fully needs a real granted account, an access-provisioning step outside this milestone.
5. Full-suite failures: 8 pre-existing baseline + 10 attributable to two verified, pre-existing local-environment conditions (§4, §8) — none attributable to this session's code.

## 8. Environment/runtime finding — not a Batch B scope change

**`DEFAULT_OLLAMA_MODEL = "qwen3:14b"` (`uri_core/core/model_providers/base.py:99`) is stale relative to this local environment.** The actually-installed/pulled Ollama models are `gemma4:12b` and `qwen3.5:9b` (confirmed via a real `/api/tags` call); `qwen3:14b` is not present, so any router/provider call relying on the unset-env-var default fails immediately with `ModelNotFoundError`. This predates this session (Batch A's own §3 A2 defect writeup already flagged `DEFAULT_CONTEXT_TOKENS` as stale for the same reason — this is the sibling default-model-name staleness, not previously documented). It was worked around for live evidence gathering by setting `OLLAMA_MODEL=gemma4:12b` explicitly; it was **not** changed in code, since it is an environment/deployment fact, not part of Batch B's scope (B1.1–B1.6 govern execution routing, not model selection defaults). Recommend a follow-up (outside this milestone) to either update the code default or, better, make role-default model resolution live-discovery-aware the same way A2.1/A2.2 already made context-window resolution.

## 9. Batch C status

**Untouched.** Confirmed: zero diff on every Batch-C-relevant module (`capabilities/executor.py`, `multi_action_dispatch.py`, `model_router.py`, `model_providers/base.py`'s `tools=` kwarg surface, `decision_engine.py`). Not started.

## 10. Final disposition

**Batch B code (B1.1–B1.6): READY.** All six items implemented, tested (129 focused, 0 failed), and the one latent flag-duplication bug found during implementation is fixed. Full regression is clean of any change attributable to this work (1844 passed; all 18 failures independently traced to a pre-existing baseline or pre-existing local-environment state, not to this session's diff).

**Evidence-gap closure: 2 of 4 cleanly closed (keyword-template workflow, multi-action-Gmail dispatch mechanics), 2 of 4 closed with a disclosed, real residual finding (attachment-turn Brain selection, resumed-approval cross-turn state).** The resumed-approval finding is the one that matters most going forward — it is real, live-demonstrated, and squarely Batch C's job to solve, not evidence that B1.1–B1.6 is incomplete.

**Batch C: READY to begin, motivated by (not blocked by) the resumed-approval finding above.** Not started in this session, per instruction.

**Awaiting your review before commit/push**, per this task's explicit instruction.
