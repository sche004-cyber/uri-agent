# M32 — Batch A (A1-3 + A2) + C3.4 Prerequisite: Completion Report

**Date:** 2026-09-18
**Author:** Claude (final audit, per standing AO-4 role).
**Scope of this report:** the pre-Batch-B unit only — A1-3 (per-user Gmail token scoping), A2 (model-aware context budget), and the C3.4 prerequisite (EffectType write/no-write classification). Batch B (canonical execution cutover) and Batch C (native tool path) are explicitly out of scope and untouched.
**Plan of record:** `docs/plans/M32_EXECUTION_ARCHITECTURE_PLAN.md`.

---

## 1. Acceptance criteria (defined from the frozen plan before this audit)

### A1-3 — per-user Gmail token scoping
- `credentials.json` (OAuth client secret) stays install-wide; `token.json` (mailbox grant) becomes per-user.
- The dispatch layer threads `user_id` into tool construction (closing the "open thread" the plan flagged: `dispatcher.py:65` carried no identity).
- `GET /connections`, `POST /connections/{id}/authorize`, `POST /connections/{id}/disconnect`, `GET /gmail/unread-count` all resolve per-user state, not the shared install-wide file, once a `user_id` is available.
- Cross-account isolation is demonstrated by a real test: account B cannot read account A's mailbox.
- Backward-compatible fallback to the install-wide path when no `user_id` is supplied (ambient/test fixtures), per plan's stated reversibility requirement.

### A2 — model-aware context budget
- The provider's real discovered context window (via `/api/tags`, already-existing `_model_max_context()` parsing) reaches `ModelProviderConfig.context_tokens`, not the stale `8192` default, when no role config or `OLLAMA_NUM_CTX` pins one.
- The catalogue entry for `gemma4:12b` reflects the real discovered window (`262144`), `KNOWN` not `UNAVAILABLE`.
- A real trimming mechanism exists and runs on **both** production call paths — `model_reasoning_adapter.py` (reasoning) and `response_drafting.py` (drafting) — not only on the test-injection branch.
- `system_policy` / identity / soul content is never trimmed; only evidence, attempt history, session context, and conversation window are trimmable.
- Output headroom (`max_tokens`/`num_predict`) is reserved against the window, not just the prompt.
- Overflow that cannot be fit after trimming is an explicit, honest failure (`ContextWindowExceededError`), not a silent send.
- `test_ollama_provider.py`'s literal-8192 assertion is rewritten to assert the new model-aware rule, not deleted.

### C3.4 prerequisite — EffectType classification
- A real side-effect classification (`EffectType`: `read_only` / `local_write` / `external_write`) replaces the provably-wrong `read_only = (approval == "none")` derivation.
- All 17 shipped tools are classified, cross-checked against `uri_workspace/capabilities_registry.json`.
- Unknown/unclassified tools fail safe to `local_write` (never silently treated as parallelizable read-only).
- `Action.read_only` stays strictly synchronized with `effect_type == READ_ONLY` (single source of truth, no drift).

This report does **not** certify Batch B or C3.4's actual consumer (parallel execution, C3.4 proper) — those remain future work; this is a prerequisite only.

---

## 2. Evidence inspected directly (not taken on report)

- `git diff --stat`: 24 tracked files, +700/−192.
- Full `git diff` read for every changed file relevant to A1-3, A2, and the C3.4 prerequisite (`server.py`, `dispatcher.py`, `connection_status.py`, `google_auth_common.py`, `gmail_service.py`, `gmail_search_service.py`, `drive_service.py`, the five Gmail/Drive tool wrappers, `capabilities/base.py`, `capabilities/registry.py`, `core/capability_registry.py`, `model_providers/base.py`, `model_providers/ollama_provider.py`, `model_reasoning_adapter.py`, `model_reasoning_gateway.py`, `response_drafting.py`, `config/model_roles.py`, `core/provider_registry.py`, `uri_workspace/capabilities_registry.json`, `test_ollama_provider.py`).
- Independently confirmed `uri_core/core/canonical_execution.py` and `uri_core/core/decision_gates.py` carry **zero diff** against the last commit (`698a6cb`), and `URI_ENABLE_DECISION_ENGINE_LIVE` / `URI_ENABLE_WORKFLOW_CONTINUATION_MODE` are unset everywhere in the tree — i.e., Batch B has genuinely not started, contrary to an earlier framing in this session that assumed otherwise.
- Ran, this session, directly:
  - `test_m32_a2_production_wiring_repair.py`, `test_m32_capability_effect_classification.py`, `test_m32_gmail_user_scoping.py`, `test_m32_model_aware_context_safety.py`, `test_ollama_provider.py` — **56/56 passed**.
  - `test_m21_context_window.py`, `test_m21_context_window_live.py`, `test_m21_prompt_budget.py`, `test_m21_provider_config.py`, `test_connection_status.py`, `test_gmail_connection_truth.py`, `test_gmail_search_service.py`, `test_gmail_search_tool.py`, `test_google_oauth_authorize_flow.py`, `test_gmail_unread_count_endpoint.py`, `test_multi_user_isolation.py`, `test_m21_file_store_isolation.py`, `test_canonical_execution.py` — **121 passed, 1 skipped, 0 failed**.

## 3. Findings against acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| A1-3 credentials install-wide, token per-user | MET | `resolve_google_token_path()` (`google_auth_common.py`), install-wide fallback preserved for `user_id=None` |
| A1-3 dispatcher threads user_id | MET | `dispatcher.py:execute_tool` injects `user_id` into tool `__init__` when the constructor accepts it |
| A1-3 endpoints resolve per-user | MET | `server.py`: `/connections`, `authorize_connection`, `disconnect_connection`, `/gmail/unread-count` all updated, plus a capability-grant check added ahead of the unread-count read |
| A1-3 cross-account isolation test | MET | `test_m32_gmail_user_scoping.py::MultiUserMailboxIsolationTests::test_user_a_is_connected_and_user_b_is_not` — passed |
| A2 model-aware default reaches provider | MET | `model_roles.py::build_provider` and `ModelProviderConfig.from_env` both call `resolve_model_context_tokens()` when no explicit config/env wins |
| A2 catalogue reflects reality | MET | `provider_registry.py`: `gemma4:12b` now `ConfidenceValue(262144, KNOWN)` |
| A2 trimming on both production paths | MET — this was the CRITICAL finding from the prior architecture review, now independently re-verified fixed | `model_reasoning_gateway.build_reasoning_request` and `response_drafting.py` both call `context_trimmer.trim_reasoning_request` unconditionally, not gated on test-only construction |
| A2 policy/identity never trimmed | MET | `test_m32_model_aware_context_safety.py::ProtectedContentPreservationTests::test_policy_and_soul_preserved_byte_for_byte_under_trimming` — passed |
| A2 output headroom reserved | MET | `test_m32_a2_production_wiring_repair.py::HeadroomSingleSourceTests` (both cases) — passed |
| A2 honest overflow | MET | `ContextWindowExceededError` raised and surfaced as `status: context_window_exceeded` from `model_reasoning_gateway.py`, not swallowed |
| A2 breaking test rewritten | MET | `test_ollama_provider.py::test_context_tokens_default_when_env_unset` now asserts model-aware behaviour; passed |
| C3.4-prereq: real classification | MET | `EffectType` enum, `capabilities/base.py`; `read_only` derived strictly from it in `__post_init__` |
| C3.4-prereq: 17/17 tools classified | MET | `KNOWN_CAPABILITY_EFFECTS` (10 read_only + 5 local_write + 2 external_write = 17) cross-checked against `capabilities_registry.json`'s added `effect_type` fields |
| C3.4-prereq: fail-safe default | MET | Unknown/unparseable `effect_type` falls back to `EffectType.LOCAL_WRITE`, both in the JSON-adapter path and the `except ValueError` path |

**No repair was required.** All criteria were met on first inspection; no defect was found that needed a bounded fix.

## 4. Scope-contamination check (final `git diff`, re-verified before commit)

All 24 tracked-file diffs map exactly to A1-3, A2, or the C3.4 prerequisite, or their directly associated test file. None touch `canonical_execution.py`, `decision_engine.py`, `decision_gates.py`, `orchestrator.py`, `workflow_planner.py`, `multi_action_dispatch.py`, or any Batch C module. Untracked files included in this commit are limited to: the four new `test_m32_*.py` files, the new `uri_core/core/context_trimmer.py` module, and the three M32/M33 planning documents (`M32_EXECUTION_ARCHITECTURE_PLAN.md`, `M32_LATENCY_DIAGNOSTIC_REPORT.md`, `M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`) that this unit's own plan text references as its evidence base and identifier-collision resolution.

Explicitly excluded from this commit as out of scope: `.agents/skills/grill-me/`, `.agents/skills/uri-development/` (unrelated skill additions), and the untracked `graphify-out/` artifacts (generated tool output, not source).

## 5. Verdict

**VERIFIED** for A1-3, A2, and the C3.4 prerequisite, as scoped above. PC1 (clean working tree) is closed by the commit accompanying this report. Batch B (B1.1–B1.6) remains 0/6, not started, and is the next isolated unit — routed to Codex per the plan's §12 worker table, not implemented directly by Claude (production call path, substantial implementation).
