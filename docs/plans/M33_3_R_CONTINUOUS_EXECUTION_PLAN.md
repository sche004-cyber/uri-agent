# M33.3-R — Continuous Remaining-Milestone Execution Plan

**Identity:** M33.3-R (the remaining work of product milestone M33.3).
**Authority:** User task package "URI M33.3-R — Continuous Remaining-Milestone Execution" (2026-09-27). The package authorizes S5, S6, S7, S8, S10, S11 and S12 as one continuous bounded milestone, with one planned User touchpoint (S5 thresholds) and one independent closing audit.
**Baseline:** worktree `C:\Users\cheta\Development\Uri\_V1`, branch `m35-uri-v1-parallel-architecture`, HEAD `c2f583909a3d13d295c997c038b0ac724f787755` (equal to `origin`, 0 ahead / 0 behind).
**State file:** `docs/plans/M33_3_R_STATE.md`.
**Author:** Claude (implementer). This plan and its self-review are not an independent audit.

## 0. Acceptance criteria for this plan (defined before drafting)

1. Every authorized slice has a design that reuses existing URI mechanisms first and names the residual gap only.
2. Every slice records internal precedent, legacy precedent, external research, and a reuse/adapt/wrap/build decision with licensing/dependency outcome.
3. The execution order preserves the true dependencies (S5 harness → exploratory → threshold freeze → final; S8 after S5/S6/S7; S11 plan before implementation; S5 and S10 hardware windows serialized).
4. No slice modifies a frozen S1–S4 artifact, wires into `/ask` or the agent loop, adopts URI-RAR, or opens S9/S13.
5. Every FROZEN_REQUIRED gate from Plan A §11 and R1.9 that falls in this scope is testable, and no candidate threshold is set before exploratory evidence.
6. Stop conditions and continuation conditions are explicit.

## 1. Scope

**Authorized:** S5, S6, S7, S8, S10, S11, S12.
**Excluded:** S9 (re-homed to URI-Memory / D4); S13 (separate future INT-* gated integration milestone). S12 stays fixture-backed until S13. No `/ask` wiring, no agent-loop wiring, no URI-RAR adoption, no INT-* event, no research promotion.
**Closure:** M33.3 closes after S5, S6, S7, S8, S10, S11 and S12 pass and one independent closing audit accepts the integrated candidate. The implementer does not close or freeze M33.3.

## 2. Frozen inputs and protected anchors

| Anchor | SHA-256 (raw bytes unless stated) | Role |
|---|---|---|
| `uri_v1/turn/rar_deterministic.py` | `4db775666868e09a9f7232707d67ec3b4070970a30145ad3c5b41bb86b5e1b95` | **current active RAR (GD-3)**; M33.3-R pins this value |
| same file, historical | `e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649` | historical Batch A / A9 anchor; kept as history only |
| `uri_v1/turn/rar_contracts.py` | `4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819` | frozen RAR contracts |
| `fixtures/m33_3_batch_a/battery.json` | `06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa` | frozen Batch A battery |
| `fixtures/m33_3_arn/battery.json` (LF) | `3a0250aa92af755e64151a08dca0a5ea3f42f8cd767560471d720fb10af83b01` | frozen S3 battery v2 |
| the five other S4 anchors | as in `scripts/m33_3_s4_replay.py` `ANCHORS` | frozen S4 replay inputs |
| S1 modules, S2 gate | recorded at baseline by `scripts/m33_3_r_anchors.py` | frozen S1/S2 code |

`scripts/m33_3_r_anchors.py` holds the full M33.3-R anchor set and is verified before and after every stage.

## 3. Research-before-build decisions

### S5 — Clarification-wording qualification harness
- **Internal precedent:** S1 `RenderRequest` / `make_render_request` (slot-only, IDs hidden), `render_template`, `validate_render` (already accepts a model JSON string `{"question","labels":{slot:label}}` and fails closed); S3 battery schema and `scripts/m33_3_s3_qualify.py` (hash-anchored manifest, deterministic telemetry); M33.3 Batch A runner (LF hash anchor, per-row telemetry, untruncated text); M33.2 B4 real-model qualification (LM Studio OpenAI-compatible calls, cold/warm latency). The A2.8B "scaffolding confusion" finding requires a flat minimal prompt.
- **Legacy precedent:** none for clarification wording in `uri-agent`; `QuestionFramingEngine.frame_method_a` / `_clarification_envelope` are the template precedent (already adopted in S1).
- **External:** LM Studio `/v1/chat/completions` `response_format: {type: json_schema, json_schema: {strict, schema}}`, enforced for GGUF through llama.cpp grammar-based sampling (lmstudio.ai/docs/developer/openai-compat/structured-output); llama.cpp GBNF/JSON-schema grammar; Outlines/XGrammar constrained decoding; promptfoo / inspect_ai / arena-style blind pairwise comparison.
- **Decision:** WRAP + ADAPT. Constrained decoding is obtained from the provider-native LM Studio `response_format` (llama.cpp grammar), so no Outlines/XGrammar dependency is added. Blind comparison follows the arena pattern (shuffled anonymized arms, key stored separately) without adopting promptfoo/inspect_ai (a Node or large Python framework would add a dependency for what is ~100 lines of deterministic code). **Build only:** the `RendererPort` and two adapters (template, LM Studio chat) named by Plan A §12.5, the `ClarificationWordingPolicy` need-class function (Plan A R2.5), the L3 battery, telemetry, and the blind sheet.
- **Licensing:** no new dependency. LM Studio is called over its local HTTP API with the standard library.

### S6 — Unified router extension
- **Internal precedent:** `uri_core/core/edge/routing_policy.py` `evaluate_routing` (pure, deterministic, unwired), `EdgeSettings` (`enabled`, `intelligence_mode`), `EdgeRuntimeInventory` (`selection_status`, `assistance_qualified`), M33.2 amendments G1/G2 and D2 truth table.
- **Legacy precedent:** `uri_core/core/model_router.py` selects providers/models, not Edge/Capable layers; it is not a routing authority for intelligence layers and is not touched.
- **External:** RouteLLM (router as a cost/quality classifier), LiteLLM router (fallback chains), Martian/NotDiamond. All learn or score routes; none encodes URI's authority-mode constraints (EDGE_ONLY never calls the Capable Brain).
- **Decision:** ADAPT (extend in place). Patterns only; no code or dependency. **Build only:** a second pure entry point `evaluate_intelligence_route` in the same module (same authority, same inputs, plus work role and model choice), the clarification-wording projection `route_clarification_wording`, and the EDGE_ONLY limitation outcome. `evaluate_routing` behaviour is preserved except that it must never return `ESCALATE` under `EDGE_ONLY` (D2 violation found in pre-audit; see §5).

### S7 — `trace_id` and the evaluation event stream
- **Internal precedent:** `uri_core/core/edge/trace.py` (`EdgeRoutingTraceEvent.redacted()` whitelist, `EdgeRoutingTraceStore` month-partitioned `_locked_append`, never-raising record), `UsageMeter` layout, `user_scoped_path`. No `trace_id` exists anywhere.
- **External:** W3C Trace Context (`trace-id` = 32 lowercase hex, not all zero; `parent-id` 16 hex); OpenTelemetry GenAI semantic conventions `gen_ai.evaluation.result` event (metric name, label, score, explanation; parented to the evaluated span or keyed by `gen_ai.response.id`; status Development as of 2026-08).
- **Decision:** ADAPT. `trace_id` uses the W3C 32-hex format so a later OTel exporter can adopt it unchanged. Event field names map onto `gen_ai.evaluation.*` where meaning matches (`evaluation_name`, `label`), but free-text `explanation` is excluded (no raw text). No OpenTelemetry SDK dependency (unwired, conventions still Development). **Build only:** versioned `EvaluationEvent` schema, validator, redacted store with learning ON/OFF, inspect, delete and reset, and `trace_id` on the M33.3-R response contracts (wording result, clarification presentation). Production `/ask` response `trace_id` is S13.

### S10 — Lease ownership and residency
- **Internal precedent:** `RuntimeLease(lease_id, runtime_id)` with no owner; `EdgeRuntime.load/unload` protocol; M33.2 §10 `EdgeResourceGovernor` contract (documented, **not implemented** in code); M33.2 B3 lifecycle evidence; Plan B R1.6; A2.7 resident 9B evidence (6.08 s cold load, ~7.3 GB GPU).
- **External:** LM Studio JIT loading, idle TTL (JIT default 60 min), auto-evict (one JIT model at a time), `lms load --ttl`, `lms ps`, `/api/v0/models` `state`; Ollama `keep_alive` and `/api/ps`; llama.cpp server model load and `--n-gpu-layers` placement.
- **Decision:** WRAP provider-native controls. URI does not implement its own eviction timer. **Build only:** additive owner provenance on `RuntimeLease` (defaults keep the old two-argument constructor), a `LeaseOwnershipLedger` that records the leases URI itself created and refuses to unload any lease URI does not own, an LM Studio observer that classifies loaded instances as URI-owned or external, and the study protocol/runner.

### S11 — Result-version ownership
- **Internal precedent:** S1 `BindingService.authorize_redo(edited_result_status=...)` already fails closed ("result-version owner (S11) required"); no result versioning in `uri_core` (`file_store.py` has only a schema version); `uri_ui` has no result editing (only memory entries are editable, `PUT /memory/{id}`); Gmail drafts can be edited by the user outside URI.
- **Legacy precedent:** none in `uri-agent`.
- **External:** append-only revision logs (Git objects, CouchDB `_rev`, Google Docs revisions), event-sourced history, content addressing (hash of content identifies a version).
- **Decision:** CLONE the proven concept (append-only, content-addressed revisions). **Build only:** a `ResultVersionLedger` with content-hash edit detection (a result counts as user-edited when its current content hash differs from the hash URI produced, which also covers edits made outside URI), and a redo path that appends and never replaces an edited version. See `docs/plans/M33_3_R_S11_RESULT_VERSION_PLAN.md`.

### S12 — Fixture-backed clarification UI
- **Internal precedent:** `uri_ui` Flutter app (`turn_card.dart`, `uri_theme.dart`, `mock_uri_client.dart`), S1 contract (`ClarificationContract`, slot keys `s*`, attribute keys `a*`, `ESCAPE_LABEL`, `ClarificationResponse` kinds CANDIDATE / ATTRIBUTE / FREE_INPUT), R4.12 display cap vs round scope.
- **External:** Material 3 `ChoiceChip` / `ListTile` radio patterns, Slack/Teams disambiguation cards, Google Assistant suggestion chips.
- **Decision:** REUSE Flutter Material widgets inside a new stand-alone widget; no new package. The widget emits only typed response payloads (`candidate_id` + `candidate_set_fingerprint`, `option_key`, or free text). Fixtures are JSON exported from real S1 contracts.

### S8 — Route-performance store and offline replay
- **Internal precedent:** S6 router (eligibility), S7 evaluation stream (outcomes), S5 frozen routes (qualification), M33.2 G3 (learning is not calibration), Plan B §11–12 (separate per-user store; ON/OFF, inspect, delete, reset; decay/invalidate on version change).
- **External:** RouteLLM offline evaluation; inverse propensity scoring (IPS), self-normalized IPS and doubly robust estimators for contextual-bandit logs; replay method (Li et al. 2011).
- **Decision:** ADAPT. The replay uses the replay/IPS family on logged events with known logging propensities; the store is a new per-user JSONL keyed by route version. **Build only:** the store, a pure preference function restricted to qualified routes, and the offline replay harness that compares fixed routing to learned preference.

## 4. Execution order (dependencies)

Governance → S5 harness/L3 battery → S6 → S7 → S10 lease + protocol → S11 discovery + plan → S12 → S5 exploratory run → **User touchpoint** → S5 threshold freeze → S5 fresh requalification → S10 residency study (separate hardware window) → S11 implementation → S8 → integrated qualification → candidate commit/push → stop for independent closing audit.

S5 measurements and the S10 study never share a hardware window.

## 5. Pre-audit findings against current code (fixed within S6)

- **PA-1:** `evaluate_routing` returns `ESCALATE` ("the Main Brain answers") for complex tasks, resource limits and ineligible replies regardless of mode; under `EDGE_ONLY` that silently calls the Capable Brain, violating D2 and M33.2 §3. It also returns `SUPPRESS` ("continue with the selected Main Brain") under `EDGE_ONLY` when Edge is disabled or not ready. Fix: under `EDGE_ONLY` these outcomes become `LIMITATION` with reason `edge_only_capable_forbidden`.
- **PA-2:** `evaluate_routing` treats `explicit_main_brain` as `SUPPRESS` for everything, with no notion of supporting work (G2). Fix: supporting work is a separate role in `evaluate_intelligence_route`; `evaluate_routing` keeps its substantive-only meaning.

## 6. FROZEN_REQUIRED gates in scope

- S5: every presented output is valid after validation (fallback to template on any reject); zero invented slots or candidate IDs after validation; Edge OFF never invokes an Edge model; SIMPLE and EXPLAIN wording never cold-loads a model; template passes the validator on every L3 contract.
- S6: D2 truth table; `EDGE_ONLY` never routes to the Capable Brain; M33.2 regression unchanged except PA-1.
- S7: no raw text in events; unknown fields rejected; OFF writes nothing durable.
- S10: URI never unloads a lease it does not own.
- S11: an edited result is never overwritten by a redo.
- S12: selections bind grounded IDs, never display strings; escape and free input always present.
- S8: replay never selects an unqualified route; OFF/reset honoured; version change invalidates evidence; offline only.

Candidate thresholds (latency, fallback rate, noticeable-improvement rate, wording preference) are `CANDIDATE_THRESHOLD_TO_BE_ESTABLISHED` until the User touchpoint.

## 7. Stop conditions

As listed in the task package §25: the S5 touchpoint; any need to modify a frozen S1–S4 artifact; an unresolved architecture/governance decision; an external solution that would change URI architecture; an S11 discovery that changes architecture; a gate that passes only by weakening it; any need for `/ask`/agent-loop, S13, INT-* or URI-RAR adoption; host disruption by a model run; an out-of-scope blocker.

## 8. Self-review (implementer, not independent)

- AC-1/AC-2: each slice in §3 names internal, legacy and external precedent and a decision; S10's `EdgeResourceGovernor` was checked in code and found documented only, so it is not claimed as reused.
- AC-3: §4 keeps S8 after S5/S6/S7 and serializes hardware windows.
- AC-4: no stage edits S1–S4 files; S11 uses the existing S1 `authorize_redo` seam rather than editing `binding.py`; S7 adds `trace_id` to M33.3-R contracts only.
- AC-5: §6 lists only gates already FROZEN_REQUIRED in Plan A §11 / R1.9 or directly stated in the task package; no numeric candidate threshold appears.
- Gap disclosed: external research was performed by documentation fetch and search; no external code was run or vendored.
