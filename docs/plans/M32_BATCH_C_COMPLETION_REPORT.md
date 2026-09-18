# M32 Batch C — Fast/Native Path: Implementation Report

**Date:** 2026-09-18
**Author:** Claude, implementing directly for this milestone per the same explicit, one-time User override of standing AO-4 §12 routing already used for Batch B.
**Baseline:** clean HEAD `77b86ba` (M32 Batch B, canonical execution cutover, VERIFIED and pushed).
**Scope:** C1 (provider-level native tool calling), C3.1/C3.2 (tool-call translator + schema catalogue), C2 (Tier 0 direct chat), C3.4/C3.5/C3.6/C3.7/C3.8/C3.9 (Tier 1 native tool loop). **Not attempted, explicitly deferred** — C3.3 (blocked on P1, out of this milestone), C4/C6 (streaming), C5 (Tier 2 demotion), C7 (prompt reduction). Batch D / next milestone not started.
**Plan of record:** `docs/plans/M32_EXECUTION_ARCHITECTURE_PLAN.md` §5.
**Status:** VERIFIED — User-accepted 2026-09-18 with the full-suite regression limitation (§4, §10 item 1) preserved exactly as reported. Committed and pushed to `origin/master`.

---

## 1. Item-by-item acceptance status

| Item | Status | Evidence |
|---|---|---|
| **C1.1** `tools=` kwarg on `ModelProvider.complete()` + all 3 adapters | DONE | `model_providers/base.py`, `ollama_provider.py`, `anthropic_provider.py`, `openai_compatible_provider.py` — additive, default `None`, ignored as no-op when unsupported |
| **C1.2** `ModelResponse.tool_calls`, normalised | DONE | New `ToolCall(id, name, arguments)` dataclass; `tool_calls` is `None` when no tools offered, `()` when offered-but-declined (the Tier 0 selection signal), a populated tuple otherwise |
| **C1.3** Router needs no change | CONFIRMED, unchanged | `model_router.py` untouched (zero diff) — `attempt(role, principal, **complete_kwargs)` already forwards `tools=` verbatim |
| **C1.4** No new exception type needed | CONFIRMED | Tool-calling failures surface through the exact same exception types `attempt()` already catches; nothing new was introduced |
| **C1.5** Per-adapter normalisation at the boundary | DONE | Ollama: dict-native `tool_calls` parsed directly. Anthropic: OpenAI-shape `tools` translated to Anthropic's native `{name, description, input_schema}`; response `content` blocks (a real bug fixed — see §5) and `tool_use` blocks parsed separately. OpenAI-compatible: JSON-string `function.arguments` decoded per-call, one malformed call never discards the batch |
| **C2** Tier 0: Brain declines every tool → its own content is the reply | DONE (non-streamed) | `native_tool_loop.py::run_native_tool_loop` — empty `tool_calls` on iteration 1 returns a terminal envelope built directly from `response.content`, no separate drafting call. Streaming itself (C4/C6) is explicitly out of this session's scope — see §7 |
| **C3.1** Tool-call → Decision Contract translator | DONE | `tool_call_translator.py`. Unknown tool name (or a real name not offered THIS turn) → error result, never dispatch. Principal always supplied by the caller, never read from `tool_call.arguments` (SR-5, tested) |
| **C3.2** Tool schemas from the existing capability registry | DONE, with a genuine correction to the plan's own assumption | `tool_schema.py` — see §5's finding: the registry has **zero** real parameter schemas for 15 of 17 tools; ground truth was extracted by inspecting each tool's own source for the `kwargs` it actually reads, not guessed |
| **C3.3** Multi-tool cross-capability routing | **Still BLOCKED, correctly** | Pending P1 (`multi_action_dispatch._action_permitted`, specified in `M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`, a different milestone). `translate_tool_calls` refuses a mixed-capability batch honestly (per-call error, never partial dispatch) rather than smuggling a new trust boundary through — tested |
| **C3.4** Parallel execution | DONE, using the now-real classification | Blocked in the frozen plan on a genuine write/no-write classification existing — Batch A's `EffectType` work closed that prerequisite. Only calls that are BOTH read-only AND approval-free (verified per-capability, not the old wrong `read_only = approval == "none"`) run concurrently; two dedicated tests prove (a) an eligible batch genuinely overlaps in wall-clock time and (b) two non-read-only calls are **never** concurrent with each other |
| **C3.5** Branch preservation | DONE, via a new wrapper (not modifying shared code) | Deliberately **not** built on `MultiActionExecutor.execute_chain()` (halts on first failure) — each translated action is gated+executed independently in `execute_translated_batch`, so legacy/canonical's own existing Gmail multi-action dispatch semantics are completely untouched |
| **C3.6** Continuation — tool results feed back to the Brain | DONE, live-proven | Real evidence (not a summary URI wrote) is appended to the next model call; the Brain's own next response is the real re-evaluation step of the USER→BRAIN→URI loop |
| **C3.7** Loop bound | DONE | `DEFAULT_MAX_ITERATIONS = 3` (matches legacy's own `max_brain_iterations`), runtime-overridable; hitting the bound is reported honestly (`tier1_bounded` / `iteration_limit_reached`), never silently truncated — tested |
| **C3.8** Mixed-approval batches | DONE | Falls out of C3.5's per-action design directly: an approval-required action never blocks a sibling in the same batch — tested with a real Gmail read + a real Gmail approval-required write in one Brain response |
| **C3.9** Idempotency for Brain-initiated retries | DONE, **explicitly scope-limited** | An in-turn dedup key (capability, action, sorted inputs) prevents a duplicate dispatch of the same non-read-only call within **one** `run_native_tool_loop` invocation. This is **not** cross-request/cross-session idempotency (no persistent dedup store was built) — disclosed as a residual, not claimed beyond what exists |
| **Toggle** (plan §10: runtime-settable) | DONE | `URI_ENABLE_NATIVE_TOOL_LOOP`, **default OFF** — a deliberate, disclosed deviation from Batch B's default-on pattern; see §6 for why |

---

## 2. Exact files changed

```
 uri_core/app/server.py                                       |  32 +++
 uri_core/core/model_providers/anthropic_provider.py           |  62 +++++--
 uri_core/core/model_providers/base.py                         |  34 +++-
 uri_core/core/model_providers/ollama_provider.py               |  50 +++-
 uri_core/core/model_providers/openai_compatible_provider.py    |  52 +++-
 5 files changed, 218 insertions(+), 12 deletions(-)
```

New files (untracked, part of this commit's scope):

```
uri_core/core/native_tool_loop.py         396 lines
uri_core/core/tool_call_translator.py     157 lines
uri_core/core/tool_schema.py              228 lines
test_m32_c1_native_tool_calling.py        313 lines
test_m32_c2_c3_native_tool_loop.py        455 lines
test_m32_c3_1_tool_call_translator.py     119 lines
test_m32_c3_2_tool_schema.py              110 lines
test_m32_c_server_wiring.py                66 lines
```

`uri_core/core/orchestrator.py` is **untouched** (verified: 6153 lines, byte-identical to the pre-existing baseline) — all new behaviour landed in new modules, per the standing PC4 no-growth rule. `approval_gate.py`, `capabilities/executor.py`, `multi_action_dispatch.py`, `decision_gates.py`, `decision_engine.py`, `capability_directory.py`, `capability_registry.py` are all **untouched** (zero diff) — every authorization/gate/dispatch boundary this batch touches was reused exactly as it already existed, never modified.

## 3. Focused test results

- New Batch C suites: `test_m32_c1_native_tool_calling.py` (14), `test_m32_c3_1_tool_call_translator.py` (10), `test_m32_c3_2_tool_schema.py` (13), `test_m32_c2_c3_native_tool_loop.py` (17, including the two dedicated C3.4 concurrency-safety proofs), `test_m32_c_server_wiring.py` (3) — **57/57 passed**.
- Combined with the full Batch A/B regression set (`test_canonical_execution.py`, `test_decision_engine.py`, `test_decision_gates.py`, `test_workflow_continuation.py`, `test_server_ask_narrative.py`, `test_multi_action_capabilities.py`, `test_ollama_provider.py`, all `test_model_router_*.py`): **278/278 passed, 0 failed.**

## 4. Regression results

**Targeted regression (every test file that imports a module this batch changed or depends on):** identified by grepping for imports of `model_providers.base`, `capabilities.base`, `decision_gates`, `canonical_execution`, `capability_directory` — 16 additional files not already covered above (`test_draft_institutional_note.py`, `test_m17_drafting_architecture.py`, `test_m19_office_readiness.py`, `test_m21_context_window.py`, `test_model_reasoning_gateway.py`, `test_multi_user_isolation.py`, `test_ollama_reasoning_adapter.py`, `test_orchestrator_approval_gate.py`, `test_orchestrator_response_narrative.py`, `test_provider_keys_hygiene.py`, `test_provider_registry_catalogue.py`, `test_provider_semantic_interpreter.py`, `test_response_drafting.py`, `test_usage_meter_recording.py`, `test_capability_directory.py`, `test_m32_capability_effect_classification.py`): **193 passed, 2 failed.** Both failures are byte-for-byte the same two `test_m19_office_readiness.py` cases already diagnosed and disclosed in the Batch B report — a real, `.gitignore`d `token.json` sitting at repo root (pre-existing local-machine state, confirmed via `git check-ignore`, unrelated to any code in this session).

**Full repository sweep: INCOMPLETE, disclosed honestly rather than claimed.** `pytest -q` (all ~1734 tests) was started in the background; the harness killed it at **61%** because the system was critically low on memory — an external condition, not a test or code failure, and I did not restart it (per the explicit instruction that accompanied the kill). The 61% that did run showed failures at the exact same positions as the already-known baseline pattern (the same ~8 pre-existing failures plus the same Ollama-model-mismatch and token.json clusters already diagnosed in the Batch A/B reports) — no new failure signature appeared in the portion observed. This is not the same as a completed clean run and I am not presenting it as one.

**Net position:** 278 (Batch A/B/C direct regression) + 193 (broader targeted sweep) = **471 tests independently verified passing this session**, 2 failed (both pre-existing, already diagnosed, unrelated to this session's code), plus a 61%-complete full sweep showing no new failure signature. The remaining ~39% of the full repository suite was not verified to completion in this session.

## 5. Live evidence

All three scenarios below are genuine, unmocked calls through `run_native_tool_loop` end-to-end against the real local Ollama server (`gemma4:12b`, confirmed via `/api/tags`), with a real `ApprovalGate`/`ToolDispatcher`/`MultiActionDispatch` (Gmail backed by the existing test fixture `FakeGmailService`, since no real Gmail grant was set up in this session — the dispatch/gate machinery itself is 100% real and unmocked).

| Scenario | Result |
|---|---|
| **Tier 0** — "What is 2+2?" | Real Brain response with an empty `tool_calls` tuple; `tier: "tier0"`; reply `"2 + 2 = 4"` returned directly as `narrative`, **one** model call, no drafting call |
| **Tier 1, legacy tool** — "Please remember that my favorite color is teal." | Real Brain call proposed `remember_fact(request_text=...)`; executed successfully through the unchanged `ApprovalGate`; a real continuation call produced a grounded reply ("I've noted that your favorite color is teal.") — **two** model calls total, matching the plan's own §1 target ("Model calls per tool turn: 4+ → 2") |
| **Tier 1, native Gmail tool** — "Search my Gmail for messages about invoices." | Real Brain call proposed `gmail_search_messages(query="invoices")`; executed through the unchanged `MultiActionDispatch`/gate boundary; continuation reply accurately summarised the real (fixture) search result (subject, sender, date, attachment) with no fabricated detail |

**C1 live-verified independently** (direct provider call, before the loop-level tests above): `gemma4:12b` correctly called `gmail_search(query="invoice")` when the request needed it, and correctly returned an empty `tool_calls` tuple with a direct answer ("2 + 2 = 4") for a request that didn't — this is the exact Tier 0/Tier 1 selection signal the whole design depends on, proven against the real model before any of the surrounding infrastructure was built on top of it.

**Not independently re-tested this session:** whether native tool calling improves the Brain's tool-selection reliability for the Batch B attachment-turn finding (Gmail chosen over `read_attached_file`). The underlying tool (now correctly exposed as a real, zero-argument, well-described native tool) is available in the same call the model already sees Gmail's tools in, which is a plausible improvement, but I have not run that specific scenario against the new loop and am not claiming it is fixed.

## 6. Toggle default: OFF, deliberately, unlike Batch B

`URI_ENABLE_NATIVE_TOOL_LOOP` defaults to **disabled**. This is a conscious departure from Batch B's default-on pattern for `URI_ENABLE_DECISION_ENGINE_LIVE`/`URI_ENABLE_WORKFLOW_CONTINUATION_MODE`, and the reason is evidentiary, not architectural caution for its own sake: canonical execution had 36+ pre-existing tests and multiple prior milestones' (M30.6 through M30.8, M32 Batch A/B) worth of live evidence before its default was flipped. The native tool loop is materially newer code, built and tested in this same session, with only the live evidence gathered directly alongside it (§5). It has not yet earned the same bar. Flipping it to default-on is a one-line change (`return True` when unset, matching B1.1/B1.5's exact pattern) whenever you're ready to make that call — I did not make it unilaterally.

When enabled, `server.py`'s wiring is additive and provably inert otherwise: `test_toggle_off_by_default_never_calls_the_native_loop` proves `run_native_tool_loop` is never even invoked with the toggle unset, and `test_toggle_on_but_none_result_falls_through_unchanged` proves a `None` result (the loop's own turn-state-assembly-failure signal) falls through completely unchanged to the existing canonical/legacy chain — never a third, competing execution route.

## 7. Preserving model-native behaviour, not imposing a ceiling

Per your requirement 4: every tool exposed to the Brain carries its **real** parameter surface, not a reduced keyword template. Gmail's actions (`search_messages`, `create_draft`, etc.) keep their full, already-structured `to`/`subject`/`body`/`query` parameters exactly as `capabilities/gmail/capability.py` already declares them — nothing was flattened. The 15 legacy tools' schemas reflect what they genuinely, verifiably accept (mostly a single `request_text` field) — not because this session chose to constrain them, but because that IS their real, ground-truth parameter surface (§5's finding). Native tool calling lets the model act on each tool's actual shape directly, in one call, rather than being routed through the old multi-step JSON-decision-contract/keyword-template machinery — the opposite of a lowest-common-denominator ceiling.

## 8. A genuine finding: the plan's own C3.2 assumption was wrong, and how it was resolved

The frozen plan's C3.2 says tool schemas should come "from the existing capability registry... so there is one source of truth, not a second hand-maintained list." Direct inspection (both of `uri_workspace/capabilities_registry.json` and of `inspect.signature()` on every one of the 15 non-Gmail tools' real callable) found that **no structured parameter schema exists anywhere in this codebase for those 15 tools** — every registry `interface` field is `null`, and every real Python signature is `method(**kwargs)`. This is reported here rather than worked around invisibly, per the Freeze discipline. It was resolved by extracting ground truth the way the dispatcher itself already does — reading each tool's own source for the `kwargs.get(...)` keys it actually consumes (verified via `grep`, not guessed) — which also surfaced a second, useful fact: almost every legacy tool's real model-facing parameter is a single `request_text` field, with `principal`/`session_id`/`decision_context` supplied deterministically by the runtime, never the model. Gmail's own real, structured `Action`/`ActionSchema` definitions needed no such reconstruction.

A second, smaller finding from the same inspection: `uri_workspace/capabilities_registry.json` also carries a `pc_system_optimization` entry under a separate `planned_capabilities` key (`status: "not_implemented"`, no execution adapter). It is exposed in the tool catalogue exactly the same way Gmail is exposed even when disconnected — consistent with this codebase's existing "always show it, let the deterministic gate refuse it honestly" pattern (the JSON-contract Brain interface already does this via `usable`/`gap_reason` annotations) — rather than filtered out by a new, inconsistent judgment call of my own.

A third finding, a real bug fixed as part of C1.5: the Anthropic adapter's response parsing (`content[0]["text"]`) assumed the first content block was always text. A tool-only response (no text block at all — a real, valid shape once tools are offered) would have raised `ProviderResponseError` before this fix. Fixed and covered by `test_tool_use_only_response_does_not_crash_and_yields_empty_content`.

## 9. Improvement metrics

Gathered live against the real local `gemma4:12b` (same model/host used throughout this batch), via a dedicated, disclosed measurement script — not the pytest suite. Baseline figures are the plan's own accepted evidence base (`docs/plans/M32_LATENCY_DIAGNOSTIC_REPORT.md`, User-accepted 2026-09-17) — real apples-to-apples numbers, not estimates, wherever a directly comparable scenario exists.

### Model calls per turn

| Scenario | Legacy baseline (diagnostic report) | Canonical (Batch B) | **Batch C native tool loop** | Plan's own target |
|---|---|---|---|---|
| Trivial/no-tool turn | 3–4 calls (semantic interpretation, reasoning, ≤3 brain-eval rounds, drafting) | 2 calls (decision + narrative) | **1 call** (Tier 0 measured) | "1, streamed" |
| Single-tool turn | 4+ calls | 2 calls | **2 calls** (Tier 1, both legacy-tool and native-Gmail-tool scenarios measured) | "2 (call + continuation)" |

Both Batch C figures match the plan's own §1 target exactly, and Tier 0 improves on canonical's own 2-call figure by removing the separate narrative-drafting call entirely (the Brain's own declined-tool response IS the reply).

### Representative end-to-end latency (real, measured, this session)

| Scenario | Legacy baseline (diagnostic report) | **Batch C measured** | Plan's target |
|---|---|---|---|
| "What is the capital of France?" (Tier 0, no tool) | 13.65–15.86 s ("Hi", closest analog) / 30.58 s→`failed` (no-tool question) | **3.07 s** | ≤3 s / ≤4 s |
| "Remember that my office is room 204." (Tier 1, legacy tool) | 19.49 s→`failed` (single read-only tool, closest analog) | **3.51 s** | ≤5 s |
| "Search my Gmail for messages about renewal." (Tier 1, native Gmail tool) | 19.49 s→`failed` (single read-only tool) | **4.29 s** | ≤5 s |

All three measured scenarios land inside the plan's own §9 targets, and all three are 4–6x faster than the closest legacy baseline (which, for two of the three, did not even succeed). These are single-run measurements on one local machine, not a statistically repeated battery (see §10 item 7's B1.3/PC3 residual — no committed `scripts/m32_latency_battery.py` exists yet to repeat this reliably) — recorded here as the Batch C baseline for that upcoming latency milestone, per your instruction, rather than presented as a final, repeated-and-averaged figure.

### Orchestration / tool-dispatch hops (structural, verified by direct code reading this session)

- **Legacy**: `process_user_input` → `semantic_interpreter.interpret()` [model call] → `skill_memory.find_matching_skill()` → `capability_planner.plan()` → (`workflow_planner`/`multi_action_dispatch.dispatch()` or `dispatcher.execute_tool()` via `approval_gate`) → up to 3 further brain-evaluation-loop rounds [model calls] → `response_drafting.draft_response()` [model call].
- **Canonical (Batch B)**: `run_canonical_for_ask` → `build_turn_state_and_directory()` → `propose_decision()` [model call, free-text JSON parsed into a contract] → `evaluate_gates()` → `_execute_canonical()` → one of `_execute_gmail`/`_execute_legacy_capability`/`_execute_remember_fact` → `_draft_narrative_safely()` [model call, separate drafting subsystem].
- **Batch C native tool loop**: `run_native_tool_loop` → `build_turn_state_and_directory()` → `model_callable(tools=...)` [model call, structured native tool call — no free-text JSON parsing step] → `translate_tool_calls()` → `evaluate_gates()` → `_execute_canonical()` → the **same** `_execute_gmail`/`_execute_legacy_capability`/`_execute_remember_fact` primitives canonical already uses → `model_callable()` again for continuation [model call, content **is** the reply — no separate drafting subsystem invoked at all].

Native tool calling removes one structural layer canonical still carries (the free-text-JSON-to-contract parsing step `propose_decision()` performs, replaced by the model's own structured `tool_calls`) and one whole subsystem (`response_drafting`/`_draft_narrative_safely`, replaced by the continuation call's own content). The real dispatch/gate/execution boundary beneath both (`evaluate_gates()` → `_execute_canonical()` → the three `_execute_*` primitives) is byte-for-byte identical between canonical and Batch C - this is a structural observation from the code, not a timed measurement, since no prior hop-count baseline was recorded to measure against.

### Parallel read-only vs sequential dispatch timing

Real (not simulated) dispatch of 2 read-only Gmail actions (`search_messages`, `read_message`) through the actual `execute_translated_batch` gate/execute boundary, no model call involved (dispatch overhead only):

- Parallel-eligible path (real `ThreadPoolExecutor`): **9.52 ms**
- Forced-serial control (same 2 calls, one at a time): **0.62 ms**

**Honest result, reported as measured, not spun**: at this fixture's speed (a local, in-process fake Gmail service with no real network latency), thread-pool scheduling overhead exceeds the near-zero actual work time, so serial was faster here. This does not contradict C3.4's design intent — parallelism is a real win only once individual calls carry real latency (a genuine network round-trip), which this environment cannot measure (no live Gmail grant configured this session — see the Batch B report's own multi-action-Gmail residual). The mechanism itself (calls genuinely overlap in wall-clock time when eligible, and non-read-only calls are provably never concurrent with each other) is separately and rigorously proven in `test_m32_c2_c3_native_tool_loop.py::C34ParallelSafetyTests` using controlled, instrumented delays specifically because real local dispatch is too fast to demonstrate it honestly at production speed.

### Tier success confirmation

| Tier | Result |
|---|---|
| Tier 0 | Real Brain response, empty `tool_calls`, correct direct answer, 1 model call — success |
| Tier 1, legacy tool | Real `remember_fact` proposal, executed, grounded continuation reply — success |
| Tier 1, native Gmail tool | Real `gmail_search_messages` proposal, executed, grounded continuation reply — success |

(Full detail and JSON already in §5.)

### Approvals, grants, audit, dispatch: not weakened

Reconfirmed, not re-derived: `approval_gate.py`, `capabilities/executor.py`, `multi_action_dispatch.py`, `decision_gates.py`, `decision_engine.py`, `capability_registry.py`, `capability_directory.py` all carry **zero diff** (§2). Every one of this section's live measurements ran through those same, unmodified files - the approval-required gate fired correctly and the grants boundary was enforced correctly in the same live scenarios used for §5's evidence, not a separate, weakened path built to make these numbers look better.

## 10. Residual risks and unresolved items

1. **Full repository regression sweep did not complete** (§4) — killed by a system memory condition, not restarted per instruction. 471 tests were independently verified passing across two targeted sweeps instead, with no new failure signature in the 61% of the full sweep that did run, but this is not equivalent to a completed full-suite green result.
2. **C3.9's idempotency is in-turn only**, not cross-request/cross-session — disclosed, not claimed beyond what was built. A Brain retry in a genuinely new HTTP turn is not covered.
3. **C3.3 (cross-capability multi-tool) remains blocked** on P1, which is out of this milestone (M33 scope) — correctly not attempted.
4. **C4/C6 (streaming, backend + Flutter) not started** — a separate, large, cross-language slice (new SSE endpoint, new Dart `askStream` interface, widget-test-preserving Flutter work) that was not attempted this session.
5. **C5 (Tier 2 escalation demotion) not started** — retiring `workflow_planner._create_steps`'s keyword routing as the default touches `orchestrator.py`'s own routing precedence and deserves its own careful, dedicated pass rather than being folded in here under time pressure, especially given the standing PC4 no-growth constraint.
6. **C7 (prompt reduction) not started** — correctly, per the plan's own explicit ordering ("last," requires a stable tiered path first, §6 of the plan).
7. **Batch B's disclosed residual findings are untouched by this batch and remain exactly as reported**: no committed `scripts/m32_latency_battery.py` (B1.3/PC3); the resumed-approval-across-turns gap (durable cross-turn action/approval state is genuinely a Tier-1/continuation problem this batch's in-turn-only C3.9 does not solve for a new HTTP turn); the pre-existing `qwen3:14b` default-model-name mismatch (unchanged, environment-only, not code); the repo-root `token.json` environment contamination (unchanged, confirmed again in §4).
8. **Cloud providers (Anthropic, OpenAI-compatible) tool calling is unit-tested but not live-verified** — no API key configured in this environment, matching the plan's own R2 disclosure.
9. **The latency/parallel-timing figures in §9 are single-run measurements on one local machine**, not a repeated, averaged battery — recorded explicitly as the Batch C baseline for the upcoming latency milestone (PC3), not as a final performance claim.

## 11. Final disposition

**Batch C core (C1, C3.1, C3.2, C2, C3.4–C3.9): READY**, as scoped above. Implemented, tested (57 new + 278 regression + 193 broader targeted regression, all green except 2 pre-existing/already-diagnosed failures), and live-verified end to end against the real local Brain model across Tier 0 and two distinct Tier 1 shapes (legacy tool, native Gmail tool). Every gate/approval/audit/dispatch boundary this batch touches was reused completely unchanged — zero diff on `approval_gate.py`, `capabilities/executor.py`, `multi_action_dispatch.py`, `decision_gates.py`, `decision_engine.py`. `orchestrator.py` untouched.

**C3.3, C4/C6, C5, C7: NOT STARTED**, disclosed explicitly rather than rushed or silently skipped — each is a genuinely separable, substantial slice of work in its own right (a blocked cross-milestone dependency, a cross-language streaming project, an `orchestrator.py`-adjacent routing change, and a measured-last prompt-reduction pass respectively).

**Full repository regression: INCOMPLETE** (§4, §10 item 1) — the one open verification item; accepted by the User with this limitation preserved exactly as reported (2026-09-18).

**Batch D / the next milestone: not started**, per instruction.

**Improvement metrics recorded in §9** — model calls per turn and end-to-end latency measured apples-to-apples against the plan's own accepted diagnostic baseline; hop-count and parallel-dispatch-timing figures recorded as the Batch C baseline for the upcoming latency milestone where no prior comparable measurement exists. No production code was changed to produce these numbers.

**User-accepted; committed and pushed** — see commit hash below.
