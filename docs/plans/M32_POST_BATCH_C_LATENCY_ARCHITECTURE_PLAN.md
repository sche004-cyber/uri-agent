# M32 — Post-Batch-C Latency Measurement and Architecture Plan

**Date:** 2026-09-18. **Status:** DRAFT — measurement and analysis complete, presented for User review/approval. **No production code was modified. Nothing was committed or pushed.**
**Author:** Claude (architect/pre-auditor role, per standing AO-4).
**Checkpoint:** builds on `docs/plans/M32_LATENCY_DIAGNOSTIC_REPORT.md` (2026-09-17, pre-Batch-A/B/C baseline) and `docs/plans/M32_BATCH_C_COMPLETION_REPORT.md` §9 (2026-09-18, Batch C's own self-reported metrics). This report re-measures the **as-built, post-Batch-C** system (commit `9a483b4`) and finds new bottlenecks that did not exist, or were not exercised, in either earlier document.
**Scope boundary:** measurement and architecture analysis only, per explicit User instruction. Does not begin M33 / the External Capability Bridge (`M32_EXTERNAL_CAPABILITY_BRIDGE_PLAN.md`, `M32_STATE.md` — untouched, different sub-initiative). No implementation batch in §7 below is authorized to start without a separate User go-ahead.

---

## 0. Acceptance criteria for this report (defined before the findings)

Per the repository's Verification-First standard, this report is acceptable only if:

1. Every number comes from a **measured** run against the real, unmocked code path (`ApprovalGate`, `ToolDispatcher`, `CapabilityRegistry`, `MultiActionDispatch`, real local Ollama), not an estimate.
2. Where the real production path differs from what a probe script exercises, that difference is stated explicitly, not glossed over (this sank part of Batch C's own §9: its metrics probe bypassed `ModelRouter`/`build_provider` entirely).
3. Every architectural claim cites `file:line` or a measured artifact.
4. Model inference time and URI-added overhead are separated with evidence, per category, matching the ten categories the User asked for.
5. Anything not verified in this phase is disclosed explicitly, with its effect on the conclusions stated.
6. No production code is changed to make a number look better (User's explicit instruction).
7. The report distinguishes confirmed root causes (profiled, `file:line`-cited) from correlated-but-unconfirmed effects.

All seven are met. §8 lists disclosed unverified items.

---

## 1. Method

- **Real-router probe** (`m32_latency_profile.py`, scratchpad, not committed): exercises the actual production call chain — `ModelRouter.get_router().attempt()` → `build_provider()` → real `OllamaProvider` → real local `gemma4:12b` — through `native_tool_loop.run_native_tool_loop()`, with the real `ApprovalGate`, `CapabilityRegistry`, `MultiActionDispatch` + `FakeGmailService` (the same fixture Batch C's own test suite uses), and a real `SessionManager` on a throwaway temp directory. This is a materially different (and more representative) probe than Batch C's own `c_metrics_probe.py`, which constructed a raw `OllamaProvider` directly and never touched `ModelRouter`/`build_provider` at all.
- **Repeat-call isolation** (`m32_repeat_check.py`): calls the same context-assembly/tool-schema/approval functions 5× in one warm process, to distinguish a one-time (import/JIT/disk-cache) cost from a per-call cost paid every turn.
- **`cProfile` root-causing** (`m32_cprofile_check.py`): line-level profiling of the three functions found expensive in the repeat-call pass, to attribute the cost to a specific call chain rather than a black-box millisecond figure.
- **Direct source verification** of every cited claim, by reading the actual file.
- **Live system check**: `psutil.virtual_memory()` run at measurement time, and a static read of the thread-pool sizing code, for the RAM/concurrency category.

**Environment:** same machine as Batch C (Windows 11, local Ollama). Installed models: `qwen3.5:9b`, `gemma4:12b` (confirmed via `ollama list`). **`qwen3:14b` — the packaged default model name — is not installed.** All real-router measurements in this report set `OLLAMA_MODEL=gemma4:12b` as a process environment variable only (no repo file touched) so the real `ModelRouter`/`build_provider` path is exercised correctly; §2.1 measures what happens without that variable, which is the deployment's actual current unconfigured state.

Probe scripts are in the session scratchpad (not committed): `m32_latency_profile.py`, `m32_repeat_check.py`, `m32_cprofile_check.py`, `router_probe.py`.

---

## 2. Measured baseline, by category

### 2.1 Model/provider selection and routing

| Measurement | Result | Evidence |
|---|---|---|
| `ModelRouter.attempt("reasoning", principal=None)` with the **packaged default** model name (`qwen3:14b`, not installed), no env override, no per-user Active Brain configured | **Fails in 24.4 ms** with `AllProvidersUnreachableError`; chain attempted: `['ollama(failed:ModelNotFoundError)']` | `router_probe.py` live run; confirmed root cause below |
| `probe_model_max_context()` live `/api/tags` HTTP GET (context-window discovery) | 24.0 ms first call, 4.3 ms second call — **never cached**, paid on every `build_provider("ollama")` call when `OLLAMA_NUM_CTX` is unset | `ollama_provider.py:79-108` (no cache); measured |
| `build_provider("reasoning")` **without** `OLLAMA_NUM_CTX` set (current deployment state — confirmed unset in `.env`) | 31.7 ms | measured |
| `build_provider("reasoning")` **with** `OLLAMA_NUM_CTX` set | 0.08 ms | measured — confirms the probe is the entire cost |

**Confirmed root cause — the production default routing path does not work at all right now, for any anonymous or non-Active-Brain-configured caller.** `model_providers/base.py:120` sets `DEFAULT_OLLAMA_MODEL = "qwen3:14b"`. This machine has `qwen3.5:9b` and `gemma4:12b` installed — not `qwen3:14b`. No `OLLAMA_MODEL` env var is set (`.env` has no `OLLAMA_*` keys), and no `uri_workspace/model_roles.json` deployment override exists (confirmed: file absent). No stored Active Brain exists for any user either (confirmed: no `*active_brain*`/`*provider_config*` file anywhere under `uri_workspace/`). Tracing `ModelRouter._ordered_candidates()` (`model_router.py:121-179`) for `principal=None`: candidates = `["ollama"]`; `_model_for_role` resolves to the packaged default via `build_provider`'s own `env_config.model` fallback, i.e. `"qwen3:14b"`. Ollama rejects it with `ModelNotFoundError`, the single candidate is exhausted, `AllProvidersUnreachableError` is raised.

This is the "Ollama model-name mismatch" the User asked to be treated as runtime evidence, not assumption — it now is: **empirically reproduced, with an exact stack, not inferred.** It is fast to fail (24 ms, not a hung timeout), so it is not itself a *latency* bottleneck — but it means **every measurement in this report, in Batch C's §9, and in every prior live-evidence probe this milestone, that "worked," worked only because the probe script explicitly hardcoded a real model name** (`gemma4:12b`), bypassing this broken default. The real, as-shipped default path is currently non-functional for any user without a manually configured Active Brain. This is a config-drift/correctness finding, not a Batch A/B/C code defect — `build_provider`/`ModelRouter`'s own logic is correct and behaves exactly as designed; the packaged default value is simply stale against what is actually installed on this machine.

### 2.2 Context assembly / tool schema exposure — the dominant bottleneck

| Function | Cost, every call, no caching | Evidence |
|---|---|---|
| `build_turn_state_and_directory()` (`decision_engine.py:941`) | **~1000–1140 ms**, every call, 5/5 repeat calls | `m32_repeat_check.py`: 993, 1012, 1021, 994, 1039 ms |
| `build_tool_schemas()` (`tool_schema.py:177`) | **~965–1030 ms**, every call, 5/5 repeat calls | `m32_repeat_check.py`: 997, 1012, 987, 1030, 990 ms |

**Root cause, confirmed by `cProfile` line trace, not inferred:** both functions independently construct a fresh `CapabilityDirectory` (`capability_directory.py:344`), whose `__init__` calls `_legacy_entries()` → `capability_feasibility.py:183 snapshot()` → `_connection_status_by_service()` → `connection_status.py:111 list_connection_status()` → `_google_service_status()` (called once per checked service — Gmail and Drive, `capability_feasibility.py:60-64`) → `_token_is_usable()` → `google_auth_common.py:34 load_usable_credentials()`. That function calls `creds.refresh(Request())` — **a real, blocking network round trip to Google's OAuth token endpoint** — whenever the stored token's access token is expired.

**Why it refreshes on literally every call, not just when actually near expiry:** `load_usable_credentials()` (`google_auth_common.py:63-64`) refreshes in memory (`creds.refresh(Request())`) but **never writes the refreshed credential back to `token_path`**. The on-disk `token.json` therefore keeps its stale, already-expired access token forever; the next call re-loads that same stale token from disk, sees it expired again, and pays another live refresh. This was confirmed with a `cProfile` trace over 3 repeated calls to each function: `google.oauth2.credentials.refresh` accounted for essentially 100% of cumulative time (2.95s / 2.950s and 3.069s / 3.068s respectively), 6 refresh calls for 3 outer calls each (2 services × 3 calls), consistent with the per-call ~500–1000 ms figure.

**Compounding factor — this cost is paid twice per turn, not once, regardless of tool-call count.** `run_native_tool_loop()`'s own top-level `build_turn_state_and_directory()` call (`native_tool_loop.py:314`) and `build_tool_schemas()`'s own independent internal `CapabilityDirectory` construction (`native_tool_loop.py:321` → `tool_schema.py:177-196`) each build a separate `CapabilityDirectory` for the exact same turn, describing the exact same real-world state. A Tier 0 turn (no tool call) therefore pays it **twice** — measured directly: `run_native_tool_loop` total for a no-tool "What is the capital of France?" turn was **2463 ms**, of which the actual model call was **470 ms**; the remaining **1993 ms is essentially all context-assembly/tool-schema overhead**, matching the ~2000 ms combined B1+B2 figure almost exactly. **This count does not scale with executed tool-branch count** — `_execute_canonical` (`canonical_execution.py:351-373`, and its `_execute_gmail`/`_execute_remember_fact`/`_execute_legacy_capability` helpers) does not construct a `CapabilityDirectory` at all; it dispatches directly through `ApprovalGate.execute_tool`/`MultiActionDispatch.dispatch_explicit`. A follow-up ground-truth check with an exact call-count instrument (§10) confirmed exactly 2 constructions for both a Tier 0 turn and a 1-branch Tier 1 turn alike. *(An earlier version of this paragraph claimed a per-branch multiplier attributed to `_execute_canonical`; that claim was traced to a misreading during the measurement phase and is retracted in §4's correction note below — this paragraph now states the corrected, re-verified mechanism.)*

**This is the single most load-bearing finding in this report.** It dominates total latency for every scenario measured, including the fastest possible one (Tier 0, no tool), and it dominates independently of which model or provider answers the prompt — a hypothetical instant, zero-latency model would still leave a ~2 second URI-side tax on every single turn under the current architecture. It was not visible in `M32_LATENCY_DIAGNOSTIC_REPORT.md` (§4.3 measured `build_query_context` at 0.003 s) because that measurement was of the **legacy** orchestrator's own context-building function, a different code path that does not go through `CapabilityDirectory`/`capability_feasibility.snapshot()` the same way; this is a cost specific to the Batch A–C canonical/native-tool-loop code, not a regression in anything that old report measured.

### 2.3 Model inference — isolated, real Ollama `gemma4:12b`, via the real `ModelRouter`

| Scenario | Total turn | Model-call time (sum) | Non-model overhead | Model calls |
|---|---|---|---|---|
| Tier 0, no-tool chat | 2463 ms | 470 ms | ~1993 ms | 1 |
| Tier 1 legacy tool (`remember_fact`) | 3791 ms | 1510 ms (800+710) | ~2281 ms | 2 |
| Tier 1 native single Gmail tool (search) | 5155 ms | 2290 ms (650+1640) | ~2865 ms | 2 |
| Tier 1 native multi-tool (search + read) | 5001 ms | 3050 ms (670+960+1420) | ~1951 ms | 3 |

Individual model-call latencies ranged 0.47–1.64 s — consistent with Batch C's own §9 figures (which used the same model, bypassing the router). **In every scenario, URI-side overhead (context assembly + tool schema build + dispatch) is comparable to or larger than model inference time** — for Tier 0, it is **81% of the total turn**. This directly contradicts the naive assumption that a local 12B model is the latency ceiling; per §2.2, it is not.

### 2.4 Orchestration / tool-dispatch hops

| Measurement | Result |
|---|---|
| 3-action real parallel-eligible dispatch (2 Gmail search + 1 read, all read-only) | 3.92 ms |
| Same 3 actions, forced-serial control (dispatch-only) | 0.87 ms |

Confirms Batch C's own 2-action finding at a larger N: at this fixture's near-zero per-action work time, thread-pool scheduling overhead exceeds the actual work, so parallel dispatch is slower in absolute terms than serial — **negligible either way against the ~2000 ms context-assembly tax and ~500-1600 ms model calls.** Dispatch/orchestration hops are not a meaningful bottleneck at current scale. (A genuinely network-bound tool call, e.g. a real Gmail API round trip rather than this fixture, would very plausibly reverse this — still unmeasurable in this environment, exactly as Batch C disclosed.)

### 2.5 Tool execution

Same mechanism as §2.4 — tool execution *is* the dispatch call measured there. No separate execution-only cost was found; `_execute_one_branch` (`native_tool_loop.py:122-206`) gate-evaluation plus `_execute_canonical` dispatch is what §2.4 timed end to end.

### 2.6 Approvals / grants / audit overhead

| Measurement | Result | Attribution |
|---|---|---|
| `ApprovalGate.execute_tool()` full path (grants check + dispatch + audit write), `system_performance` tool | 568 ms (first call), then 221–389 ms (repeat calls) | **Misleading if read as gate overhead — see cProfile below** |
| `ApprovalGate._record_audit_safely()` alone (in-memory audit write) | 0.02 ms | Real gate/audit-boundary cost |

**Corrected attribution, confirmed by `cProfile`:** the 200–400 ms figure is **not** the approval/grants/audit machinery. It is the specific tool payload chosen for the probe: `system_performance.report()` calls `psutil.cpu_percent()`, which blocks on `time.sleep()` internally (psutil's sampling-interval design) — 600 ms of literal `time.sleep` across 3 calls — plus `psutil.swap_memory()` costing ~67 ms per call on Windows. **The actual gate/grant/audit boundary itself (`CapabilityResolver.is_allowed`, `dispatcher.execute_tool`'s dispatch, `_record_audit_safely`) is near-zero**, matching the prior diagnostic report's own §8 finding ("the safety machinery is deterministic and cheap") and Batch C's own confirmation that authorization was not weakened. Production's `AuditTrail()` is also confirmed in-memory-only by default (`server.py:234,410` both construct `AuditTrail()` with no store argument → `InMemoryAuditEventStore`) — cheap, but non-persistent across process restarts, an existing characteristic unrelated to this milestone's scope, noted for completeness only.

### 2.7 Retries / fallbacks

`ModelRouter.attempt()`'s fallback chain (`model_router.py:232-278`) is fast to fail (§2.1: 24 ms to exhaust a single unhealthy candidate) rather than slow — the risk here is **total failure, not added latency**, when no working candidate exists (§2.1). A correctly configured deployment (working default model, or a configured Active Brain) never engages this path in the measurements above. `ProviderHealthTracker`'s 60-second cooldown (`model_router.py:37,59-60`) is a reasonable, unmeasured-but-structurally-sound guard against repeatedly retrying a known-broken candidate within one 60 s window — not exercised in this phase's scenarios since only one candidate was ever configured.

### 2.8 Streaming / time-to-first-token

**Not implemented.** Confirmed by source: `ollama_provider.py` sends `"stream": False`; no `StreamingResponse`/SSE exists in `server.py`; this matches Batch C's own explicit scope (C4/C6 deferred) and the original diagnostic report's §6 finding, unchanged. Time-to-first-UI-token is architecturally identical to total turn latency in the current system. **Not independently re-measured in this phase** — no new evidence beyond re-confirming the code is unchanged; disclosed in §8.

### 2.9 Backend-to-UI handoff

**Not measured in this phase.** No live Flutter UI harness was run. `/ask` returns a single synchronous JSON `dict` (unchanged from the prior diagnostic report's §6 finding); FastAPI serialization cost was not isolated. Disclosed as unverified in §8 — the in-process measurements in §2.2–2.6 do not include HTTP transport or client-side rendering.

### 2.10 RAM / resource pressure and concurrency overhead

| Measurement | Result |
|---|---|
| Live `psutil.virtual_memory()` at measurement time | **total=25.7 GB, available=0.8 GB, 97.0% used** |
| `execute_translated_batch`'s `ThreadPoolExecutor` sizing (`native_tool_loop.py:258`) | `max_workers=len(eligible)` — **no fixed upper bound.** A turn with N parallel-eligible read-only tool calls spawns N live worker threads, unbounded by any cap in the source. |

**This machine is currently under severe, real memory pressure (97% used, well under 1 GB headroom) at the moment of measurement** — independently corroborating the Batch-C-segment finding that a background full-suite `pytest` run was killed by the harness due to critically low system memory. This is not a one-off fluke; it is the current, measured state of the development machine. Combined with the unbounded thread-pool finding, a turn where the Brain proposes an unusually large number of parallel-eligible read-only tool calls (not exercised by any scenario in this report, since the largest tested was 3) is a plausible, currently-unbounded resource-pressure risk on a machine already this close to its memory ceiling — flagged as a risk (R-New-1, §6), not confirmed as having occurred, since no scenario with a large N was run.

---

## 3. Benchmark scenarios (§ per User's numbered list)

| Scenario | Result | Source |
|---|---|---|
| No-tool chat | 2463 ms total, 470 ms model, 1993 ms overhead | §2.3 |
| Tier 0 tool (tools offered, declined) | same as no-tool chat — Tier 0 by definition never calls a tool | §2.3 |
| Tier 1 tool (single legacy write, single native read) | 3791 ms (legacy `remember_fact`) / 5155 ms (native Gmail search) | §2.3 |
| Multi-tool (2–3 actions, parallel-eligible + serial) | 5001 ms (2 successful branches, 3 model calls); dispatch-only overhead 0.87–3.92 ms | §2.3, §2.4 |
| Approval/resume | **Not exercised end to end in this phase.** `_execute_one_branch` (`native_tool_loop.py:159-164`) correctly returns `not_executed`/`gate_outcome` for a non-`READY` gate and feeds it back to the Brain for the next iteration (§ code trace), but this in-turn path never calls `ApprovalGate.request()`/creates a durable pending approval — matching Batch B's already-disclosed "resumed approval across turns" gap exactly. The isolated `ApprovalGate.execute_tool()`/`_record_audit_safely()` timings in §2.6 are the closest real measurement available; a true cross-turn approval-then-resume HTTP round trip was not run this phase (would require the canonical path, not native-tool-loop, per that same disclosed gap) |
| Representative drafting/search work | Tier 1 native Gmail search (§2.3, 5155 ms) stands in for representative search work; no document-drafting scenario was run this phase (would exercise `document_composition` role / `DocumentComposer`, out of this phase's measured scope) |

---

## 4. Confirmed vs. correlated findings

**Confirmed (measured + `cProfile`-attributed to an exact call chain, `file:line` cited):**
- F1: packaged default model (`qwen3:14b`) is not installed; the real production routing path fails for any principal without a manually configured Active Brain (§2.1).
- F2: `build_turn_state_and_directory()` and `build_tool_schemas()` each independently construct a `CapabilityDirectory`, whose `__init__` triggers a live, uncached Google OAuth token refresh per checked service, costing ~1 second per call, every call, no caching (§2.2).
- F3: the refreshed credential is never persisted back to `token.json`, so every subsequent call refreshes again from the same stale disk state (§2.2, `google_auth_common.py:63-64`).
- F5: for the fastest possible turn (Tier 0), URI-side overhead (F2) is 81% of total latency; model inference is a minority contributor (§2.3).
- F6: the approval/grants/audit boundary itself is not a bottleneck; a prior probe misattributed a slow tool's own blocking `psutil` call to the gate architecture (§2.6, corrected here).
- F7: dispatch/orchestration-hop overhead is negligible (single-digit milliseconds) at the scale tested (§2.4).
- F8: streaming remains entirely unimplemented, unchanged from the pre-Batch-C diagnostic report (§2.8).
- F9: this machine is currently at 97% memory utilization with an unbounded parallel-dispatch thread pool (§2.10).

> **Correction, recorded 2026-09-18 during D1/D2 implementation verification (not overwritten, per this repository's auditable-correction convention).** The original **F4** above read: *"`_execute_canonical` independently repeats the same `build_turn_state_and_directory` construction per executed tool branch (`canonical_execution.py:456`), compounding F2/F3 with tool-call count."* This was **wrong**. Direct re-reading of `canonical_execution.py` during implementation found that `build_turn_state_and_directory` is called exactly once in that file, inside `run_canonical_for_ask` (the separate, legacy-fallback `/ask` HTTP entry point) — never inside `_execute_canonical`/`_execute_gmail`/`_execute_remember_fact`/`_execute_legacy_capability`, none of which construct a `CapabilityDirectory` at all. A follow-up ground-truth check (`m32_d_root_cause2.py`, scripted fake model, exact call counting via `cProfile` and a patched `load_usable_credentials`) confirmed **exactly 2** `CapabilityDirectory` constructions and **4** `load_usable_credentials` calls per turn, for both Tier 0 and a single-branch Tier 1 turn alike — not a per-branch multiplier. The two real construction sites are `native_tool_loop.run_native_tool_loop`'s own top-level `build_turn_state_and_directory` call and `build_tool_schemas`'s own internal, independent `CapabilityDirectory` construction — both inside `native_tool_loop.py`, not `canonical_execution.py`. §7's D2 batch is scoped to these two real sites; see §10 for the implemented fix and its verification. The correlated-but-unconfirmed note originally here (about F4's per-branch scaling not being perfectly linear) is retracted along with F4 itself — the apparent scaling was ordinary run-to-run network jitter across exactly 2 constructions in every scenario, not evidence of a 3rd or 4th.

---

## 10. D1 + D2 implementation and verification (2026-09-18, User-approved batches only)

Per User approval, **D1** (persist refreshed Google OAuth credentials) and **D2** (share one `CapabilityDirectory` per turn) were implemented and verified. **D3–D6 were not started**, per explicit instruction. No commit/push has been made; this section reports the verified result for review.

### 10.1 What changed

- **D1** — `google_auth_common.py`: `load_usable_credentials()` now calls a new `_persist_refreshed_credentials()` helper after a successful `creds.refresh()`, writing `creds.to_json()` back to the exact `resolved_path` the credential was loaded from (atomic write: `tempfile.NamedTemporaryFile` + `os.replace`, matching this repo's existing convention in `usage_ceiling_store.py`/`fallback_routing_store.py`/`provider_registry.py`). Write failures are swallowed (never turn a successful refresh into a failure). `resolved_path` was already user-scoped by the existing `resolve_google_token_path(user_id)` — the persist step writes to that same path and no other, so per-user isolation is structurally preserved, not newly added.
- **D2** — `tool_schema.py`: `build_tool_schemas()` gained an optional `directory: Optional[CapabilityDirectory] = None` keyword parameter; when supplied, it is used directly instead of constructing a second `CapabilityDirectory`. Every existing caller that omits it (all of them, before this change) sees byte-for-byte unchanged behavior. `native_tool_loop.py`: `run_native_tool_loop()` now passes its own already-built `directory` (from `build_turn_state_and_directory`) into `build_tool_schemas(directory=directory, ...)`. The directory is a local variable scoped to one `run_native_tool_loop` call — never cached at module or process level, never shared across turns or users.
- No change to `canonical_execution.py`, `decision_gates.py`, `approval_gate.py`, `dispatcher.py`, or `multi_action_dispatch.py` — gate evaluation, grants checks, approval requirement checks, and audit recording all still run exactly where and how they did before; D2 only changes which `CapabilityDirectory` object is passed to `build_tool_schemas`, not what is passed to gate evaluation or execution (those already used the shared directory).

### 10.2 Tests added

- `test_gmail_connection_truth.py` (`LoadUsableCredentialsTests`), 4 new tests: successful refresh persists to disk; persistence is scoped to the exact resolved path only (a second, unrelated token file is proven untouched — direct proof of per-user isolation); a persist failure (`to_json()` raising) does not break the refresh result; and an end-to-end round trip using the **real** `google.oauth2.credentials.Credentials` class (only `Request`/network is mocked) proving a second `load_usable_credentials()` call after a persisted refresh does **not** call `.refresh()` again.
- `test_m32_c2_c3_native_tool_loop.py` (`D2DirectoryReuseTests`), 4 new tests: a Tier 0 turn builds exactly 1 `CapabilityDirectory` (previously 2); a single-branch Tier 1 turn builds exactly 1; a **2-branch** Tier 1 turn still builds exactly 1 (proves the count does not scale with branch count, directly superseding the retracted F4 claim); and `build_tool_schemas(directory=X)` builds zero additional directories when one is passed in. All 4 use real `CapabilityDirectory.__init__` counting (a wrapped real constructor, not a mock that replaces construction), so the real object is still built and used — only the redundant second build is what is asserted absent.

### 10.3 Regression

Targeted sweep, real collaborators throughout (no new mocking of gates/dispatch/approval): `test_capability_directory.py`, `test_decision_engine.py`, `test_decision_gates.py`, `test_gmail_connection_truth.py`, `test_m32_c_server_wiring.py`, `test_m32_c2_c3_native_tool_loop.py`, `test_m32_c3_2_tool_schema.py`, `test_m32_gmail_user_scoping.py`, `test_workflow_continuation.py`, `test_canonical_execution.py`, `test_gmail_search_service.py`, `test_m32_c1_native_tool_calling.py`, `test_m32_c3_1_tool_call_translator.py` — **223 passed, 0 failed** (13 subtests). Approval/grants/audit/dispatch behavior is unchanged by construction (§10.1's third bullet) and this is additionally confirmed by every pre-existing gate/approval/dispatch test in this sweep still passing unmodified.

### 10.4 Before / after, measured

**Structural counts (scripted fake model — `m32_d_root_cause2.py` — no real-model timing noise, exact call counting):**

| Metric | Before | After |
|---|---|---|
| `CapabilityDirectory` constructions per turn (Tier 0 or Tier 1, any branch count) | **2** | **1** |
| `load_usable_credentials` calls per turn | **4** | **2** |
| Elapsed, Tier 0 (scripted) | 2091 ms | 5.2 ms |
| Elapsed, Tier 1 single Gmail tool (scripted) | 1966 ms | 2.8 ms |

*(The scripted "after" elapsed figures reflect a token already persisted-valid from an earlier call in this same session by the time this specific script ran — a real, expected effect of D1 working across processes/turns, not an isolated first-refresh measurement. The isolated, controlled proof that a persisted refresh specifically prevents the very next `.refresh()` call — independent of any such timing confound — is the unit test in §10.2, which mocks only the network boundary and asserts `.refresh()` call counts directly: 1, then still 1.)*

**Real-router, real local `gemma4:12b` (`m32_latency_profile.py`), representative (warm-model) figures — model inference time is unaffected by D1/D2 by construction (neither change touches the provider/model call), shown here to demonstrate total-turn impact:**

| Scenario | Total, before | Model time | URI overhead, before | Total, after | URI overhead, after |
|---|---|---|---|---|---|
| Tier 0, no-tool chat | 2463 ms | 470 ms | 1993 ms (81%) | **476 ms** | **~6 ms (1%)** |
| Tier 1 legacy (`remember_fact`) | 3791 ms | 1510 ms | 2281 ms (60%) | **1454 ms** | **~24 ms (2%)** |
| Tier 1 native single Gmail tool | 5155 ms | 2290 ms | 2865 ms (56%) | **2237 ms** | **~7 ms (0.3%)** |
| Tier 1 native multi-tool (2 branches) | 5001 ms | 3050 ms | 1951 ms (39%) | **2608 ms** | **~0 ms** |

**Disclosed:** one repeated Tier-0 run in this same session measured a 13.62 s total turn, entirely attributable to a single slow model call (13.62 s of the 13.62 s total — URI overhead was still ~4 ms in that same run). This is model cold-load/scheduling variance (consistent with §2.10's independently-measured 97%-memory-utilization finding on this machine), not a D1/D2 regression — a 3-run repeat immediately after measured 470–770 ms model calls, and is the figure used above as representative.

### 10.5 Requirements check

- Per-user credential isolation: preserved — `_persist_refreshed_credentials` writes only to the caller's already-resolved, already-user-scoped path (§10.1, §10.2's isolation test).
- Grants/approvals/audit/dispatch behavior: unchanged — no file in that boundary was touched; confirmed by full regression pass (§10.3).
- No global cross-user capability state introduced: the shared `CapabilityDirectory` in D2 is a local variable scoped to one `run_native_tool_loop` invocation, never cached at module/process scope (§10.1).
- Tests proving refresh persistence and per-turn directory reuse: added, §10.2.
- Focused regression: run, §10.3.
- Benchmark re-run with before/after reported: §10.4.

**D3–D6 not started, per instruction. No commit or push has been made.**

---

## 11. D3 implementation and verification (2026-09-18, User-verified, commit authorized)

**D3 — default-model-resolution correctness fix** (§5 item 3 / §7 table row / risk R-New-3). Implemented, tested, User live-verification accepted, commit/push authorized.

### 11.1 Live-reproduced root cause

Traced the full failure path (`model_router.py`, `model_roles.py`, `ollama_provider.py`, `orchestrator.py`) and reproduced the defect directly against this repository's real `ModelRouter`, on this machine (Ollama installed, `OLLAMA_MODEL` unset, no `uri_workspace/model_roles.json` override, installed models `qwen3.5:9b`/`gemma4:12b` — NOT the packaged default `qwen3:14b`):

```
>>> get_router().resolve('reasoning', None)
ProviderPlan(provider_id='ollama', model='')
```

`ModelRouter._model_for_role()` returned `""` (empty string) instead of the real default model, whenever a role had no explicit `"model"` key and no override applied — i.e. every packaged-default role, on every deployment that has not set `OLLAMA_MODEL` or a per-role config. `build_provider()` itself was already correct (its own `"ollama"` branch already fell back to `OLLAMA_MODEL` env, else `DEFAULT_OLLAMA_MODEL` = `"qwen3:14b"`) — only the router's own internal bookkeeping diverged from what was actually constructed. Confirmed impact:

- Health-tracker cooldown keyed on `("ollama", "")` instead of the real model name.
- `response_drafting._resolve_context_budget()` / `model_reasoning_adapter._resolve_router_context_budget()` — both "peek without calling" consumers of `router.resolve()` — silently used the wrong (empty) model name, degrading their context-window lookup to the conservative `8192`-token fallback instead of the real, catalogue-known `40960` tokens for `qwen3:14b`. This was a real, live-confirmed regression of the M21 context-budget-safety work for exactly the packaged-default case.
- The top-level failure the User/Brain actually sees was **already clear** before this fix: `ModelNotFoundError("Model 'qwen3:14b' was not found on this Ollama server (...). Pull it first.")`, correctly propagated up through `AllProvidersUnreachableError`. D3 did not need to invent new error text — it needed to make the router's own internal model identity stop lying about what it had actually resolved.

### 11.2 Fix

`uri_core/core/model_router.py`, `_model_for_role()`: when no role config, Active Brain override, or explicit per-request override names a model, and the resolved candidate is `"ollama"`, fall back to `os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)` — the exact same precedence `build_provider()`'s own `"ollama"` branch already applies. No machine-specific model name hardcoded anywhere; only the existing env var and the existing packaged constant are used. Explicit override precedence (per-request `model_override`, Active Brain, static role config) all still win over this fallback, unchanged — verified in §11.3.

Verified live, post-fix:

```
>>> get_router().resolve('reasoning', None)
ProviderPlan(provider_id='ollama', model='qwen3:14b')
>>> response_drafting._resolve_context_budget(ROLE_DRAFTING, None)
(40960, 'qwen3:14b')
>>> model_reasoning_adapter._resolve_router_context_budget(ROLE_REASONING, None)
(40960, 'qwen3:14b')
```

### 11.3 Tests added

New file `test_model_router_default_model_selection.py`, 10 tests in 4 groups:

- **Missing default model** — resolves to the real default (not `""`); `_model_for_role()` agrees with `resolve()`; `OLLAMA_MODEL` env override wins over the packaged `DEFAULT_OLLAMA_MODEL` constant.
- **Valid configured model** — an explicit role-config model always wins over the default; a valid configured model completes successfully through `attempt()`.
- **Explicit override precedence** — a per-request `principal.model_override` wins over the packaged default, both directly (`_model_for_role`) and through `resolve()`.
- **Fail-clear / no silent substitution** — an unavailable resolved model still raises `AllProvidersUnreachableError` naming the real model; the health tracker marks the *real* model unhealthy (not an empty-string key that could collide with an unrelated model); with only the one "ollama" install-default candidate, a failure is never silently retried against some other, different model — the router has no such authority and did not invent one.

Also updated 3 pre-existing test files (`test_model_router_resolution.py`, `test_model_router_degraded_mode.py`, `test_model_router_auth_failure_boundary.py`) — 7 assertions there hardcoded `("ollama", "")` as the expected health-tracker key, which was itself an artifact of the bug this milestone fixes, not an intended contract. Updated to assert against the real resolved default key (`OLLAMA_MODEL` env override, else `DEFAULT_OLLAMA_MODEL`) so they now verify correct behavior instead of encoding the defect.

### 11.4 Regression

- **Full `ModelRouter` suite** (pre-existing 6 files + the 1 new file): **58 passed, 0 failed.**
- **Broader focused sweep** (`-k "model_router or model_roles or provider or drafting or reasoning_adapter or decision_engine or native_tool_loop or document_composer or m31 or m32"`, 382 collected): **377 passed, 5 failed.**
- The 5 failures (`test_ollama_provider_live.py` x2, `test_ollama_reasoning_adapter_live.py` x3) were verified pre-existing and unrelated to this change: the working tree was stashed back to clean HEAD (`054df23`) and the same 2 files re-run — **identical 5 failures reproduced on unmodified HEAD.** Root cause: these are live-integration tests that call the real local Ollama server and require the packaged default model `qwen3:14b` to be pulled; it is not, on this machine (§11.1). This is the deployment/environment condition D3 diagnoses, not something D3's code change causes or is required to fix in-place (see §11.5).

### 11.5 Deployment/config recommendation (not implemented — operator action, not a code change)

To make the packaged default actually resolve to a working model on this machine, either:

- `ollama pull qwen3:14b` (matches the packaged default and the provider catalogue's `KNOWN` context-window entry, `provider_registry.py`), or
- set `OLLAMA_MODEL` to an already-installed model (`qwen3.5:9b` or `gemma4:12b` on this machine).

Deliberately not automated or hardcoded: picking a specific installed model on the operator's behalf would itself be "silently choosing an arbitrary replacement model" — exactly what this fix's own architecture (R-New-3) forbids.

### 11.6 Requirements check

- Provider/model-agnostic architecture: preserved — fix reads only `OLLAMA_MODEL`/`DEFAULT_OLLAMA_MODEL`, no machine-specific model name added anywhere (§11.2).
- Explicit user/provider/model override precedence: preserved and tested (§11.3, `TestExplicitOverridePrecedence`).
- Fail clearly when the configured/default model is unavailable: already true for the user-visible error before this fix; strengthened by making the router's own internal model identity (health-tracker key, context-budget lookups) consistent with the real failing model (§11.1–§11.2).
- No silent substitution of an arbitrary replacement model: preserved and tested (§11.3, `TestUnavailableModelFailsClearly`).
- Tests for missing default model, valid configured model, and explicit override paths: added (§11.3).
- Focused regression: run (§11.4); pre-existing environmental failures isolated and confirmed via clean-HEAD comparison, not silently absorbed into this milestone's pass count.

**D4–D6 not started, per instruction.**

---

## 12. D4 implementation and verification (2026-09-18, from clean HEAD `a6fe87c`)

**D4 — context-probe skip + bounded parallel-tool-dispatch worker cap** (§5 items 4/5, §7 table row, risk R-New-1). Two independent sub-items, reported separately since one required no code change and the other did.

### 12.1 Item 1 — skip the Ollama context probe when `OLLAMA_NUM_CTX` is already set

**Finding: already correctly implemented — no production code change made.** Traced all three real call paths (`ModelProviderConfig.from_env()`, `build_provider("ollama")`, and the direct `resolve_model_context_tokens()` call `response_drafting.py`/`model_reasoning_adapter.py` use) and verified empirically, by spying on `probe_model_max_context` (the actual `/api/tags` HTTP call), that **all three already perform zero probe calls** when `OLLAMA_NUM_CTX` is set — each checks the env var first and returns immediately:

```
build_provider probe calls: 0   (context_tokens=8192, from OLLAMA_NUM_CTX)
from_env probe calls:       0
resolve_model_context_tokens probe calls: 0
```

This was a real, structurally sound implementation from an earlier milestone (`resolve_model_context_tokens()`'s own docstring already documents "1. Explicit OLLAMA_NUM_CTX environment variable override" as priority one). No defect was reproduced. The one real gap was **test coverage**: no existing test asserted "zero probe calls" specifically — `test_explicit_env_override_always_wins` (`test_m32_model_aware_context_safety.py`) and `test_context_tokens_reads_override_from_env` (`test_ollama_provider.py`) both only asserted the returned *value*, which would still pass even if a wasted probe call happened before the override took effect. Closed that gap (§12.2).

**Measured latency win from setting `OLLAMA_NUM_CTX`** (this is a deployment-config effect, not a code change - `build_provider(ROLE_REASONING)`, this machine, Ollama reachable):

| Condition | Elapsed |
|---|---|
| `OLLAMA_NUM_CTX` unset (probe attempted) | 15.6 ms |
| `OLLAMA_NUM_CTX` set (probe skipped) | 0.1 ms |

Consistent in direction and order of magnitude with the original report's own ~30 ms estimate (§5 item 4). This win is already available today by setting the env var — restated as the deployment recommendation (§12.5), not something this batch needed to implement.

### 12.2 Item 1 tests added

`test_ollama_provider.py`: `test_from_env_skips_probe_when_num_ctx_set`, `test_from_env_does_probe_when_num_ctx_unset` (control), and a new `BuildProviderContextProbeSkipTests` class with `test_build_provider_skips_probe_when_num_ctx_set` and `test_resolve_model_context_tokens_skips_probe_when_num_ctx_set` — all assert `probe_model_max_context` is never called (not just that the final value is correct), closing the coverage gap identified in §12.1.

### 12.3 Item 2 — bounded, configurable worker cap for parallel tool dispatch

**Finding: real, confirmed gap.** `native_tool_loop.execute_translated_batch()` built its `ThreadPoolExecutor` with `max_workers=len(eligible)` - unbounded, growing with however many read-only + approval-free tool calls the Brain requested in a single turn. Under this machine's independently measured 97% RAM utilization (R-New-1), this is a real, structurally demonstrable resource-exhaustion risk on a turn with an unusually large parallel-eligible batch (not yet observed in production, but not hypothetical either — nothing in the code prevented it).

**Fix** (`uri_core/core/native_tool_loop.py`): added `DEFAULT_MAX_PARALLEL_TOOL_WORKERS = 4` and env var `URI_MAX_PARALLEL_TOOL_WORKERS`, read via `_max_parallel_tool_workers()` (falls back to the safe default for anything that isn't a positive integer - unset, non-numeric, zero, or negative). `execute_translated_batch` now uses `worker_count = min(len(eligible), _max_parallel_tool_workers())`. This bounds only **how many run at once** — every eligible branch still executes exactly once; which branches are eligible for concurrency at all (`_read_only_and_approval_free`, C3.4's safety classification) is completely untouched, so approvals/grants/audit/dispatch and the existing "never two non-read-only calls concurrently" (R4/SR-1) invariant are unaffected by construction, not just by test result.

### 12.4 Item 2 tests added

`test_m32_c2_c3_native_tool_loop.py`:

- `C34ParallelSafetyTests.test_worker_cap_bounds_concurrency_below_eligible_count` — 6 eligible read-only branches, cap=2: peak concurrency measured (lock-protected counter around a faked `_execute_one_branch`) never exceeds 2, and is `>1` (proves the cap allows real parallelism up to itself, not accidental full serialization).
- `test_worker_cap_still_executes_every_eligible_branch` — same 6-branch/cap=2 batch, real dispatch (not faked): all 6 branches complete with `status="success"` — the cap bounds concurrency, never how much work actually runs.
- `test_worker_cap_does_not_relax_non_read_only_serial_safety` — cap set permissively high (8) with two non-read-only (`remember_fact`) calls: peak concurrency still exactly 1. Proves the cap cannot be used to accidentally widen the serial-safety boundary (R4/SR-1) — it only ever bounds the size of the already-safe read-only pool.
- New `MaxParallelToolWorkersTests` class: default when unset, configurable via env var, falls back to the safe default on a non-integer value, on `"0"`, and on a negative value; and a sanity bound (`1 <= DEFAULT_MAX_PARALLEL_TOOL_WORKERS <= 8`) so the packaged default itself cannot silently drift toward "arbitrarily large."

Both eligible-batch tests had to be built against **the same capability** (`Gmail`, `search_messages`, called 6 times with distinct query arguments) rather than 6 distinct legacy tool names. **Disclosed, out of D4 scope:** while building these, found that `test_eligible_read_only_batch_executes_concurrently_not_serially` (pre-existing, `C34ParallelSafetyTests`, written for an earlier milestone) is a false positive — it uses three *different* legacy tool names in one batch, which `translate_tool_calls`'s R12/SR-4 cross-capability guard refuses outright (`"Multiple tool calls in one turn must target the same capability"`) before any dispatch or concurrency ever happens; the test's own elapsed-time assertion passes trivially because nothing runs. Confirmed via direct branch-result inspection, not by running the test itself. This is a test-quality defect in earlier C3.4 coverage, not a production defect, and is not something D4 asked to fix — flagged here rather than silently repaired or silently left unmentioned.

### 12.5 Regression

Broad focused sweep (`-k "native_tool_loop or ollama_provider or model_aware_context_safety or a2_production_wiring or tool_schema or tool_call_translator or canonical_execution or multi_action or model_router or model_roles"`, 239 collected): **237 passed, 2 failed, 13 subtests passed.** The 2 failures (`test_ollama_provider_live.py::test_real_completion_from_configured_model`, `::test_real_orchestrator_call_succeeds_without_groq`) are the same pre-existing, environment-caused failures already isolated and root-caused in §11.4 (`qwen3:14b` not pulled on this machine) — not new, not caused by D4. `test_model_router_*` suite (58 tests, including the D3 additions) re-run separately and unaffected: 37/37 relevant files passed (the model-router-specific subset of the sweep above).

### 12.6 Before/after, measured — resource-risk reduction, explicitly NOT a demonstrated RAM improvement

**Distinguishing actual RAM improvement from risk reduction only, as required:** no before/after RAM measurement is claimed, because no real URI turn in this codebase's own evidence (this report's own benchmark scenarios, §3) has ever produced more than 3 parallel-eligible tool calls in one batch — well under the new cap of 4. For every observed real scenario, **this change has zero effect**: `worker_count = min(len(eligible), 4)` equals `len(eligible)` exactly as before. There is nothing to measure as an "improvement" under normal, observed load.

What was measured is the **structural bound itself**, under a synthetic pathological batch (20 eligible calls, exceeding anything ever observed) — a direct proxy for the risk R-New-1 describes, not a production measurement:

| Configuration | Peak concurrent OS threads (20-call batch) | Elapsed (20 calls × 50 ms simulated work) |
|---|---|---|
| OLD (`max_workers=len(eligible)`, unbounded) | ~20 | 0.057 s |
| NEW (`max_workers=4`, capped) | ~4 | 0.252 s |

This is the honest trade-off the fix makes, and only for a batch size that has not been observed in production: **peak concurrent OS threads bounded 5× lower** (reducing exactly the resource-exhaustion surface R-New-1 names), at the cost of **proportionally longer wall-clock time for that same unusually large batch** (each excess call queues behind the 4-worker pool instead of running immediately). For any batch at or below the default cap (4) - which is every real scenario measured in this report - there is no latency cost and no behavior change at all.

### 12.7 Requirements check

- Provider/model-agnostic behavior: preserved — item 1 touched no provider-selection code; item 2 touched no model/provider code at all.
- No change to model-selection semantics: confirmed — `test_model_router_*` (58 tests) unaffected (§12.5).
- Approvals/grants/audit/dispatch/non-read-only concurrency safety: unweakened — `_read_only_and_approval_free` classification untouched; `test_worker_cap_does_not_relax_non_read_only_serial_safety` (§12.4) proves the cap cannot be used to widen the serial boundary; full existing C3.4/gate/dispatch regression suite still passes (§12.5).
- Worker cap safe/configurable, not arbitrarily large: `DEFAULT_MAX_PARALLEL_TOOL_WORKERS = 4`, env-configurable via `URI_MAX_PARALLEL_TOOL_WORKERS`, always falls back to the safe default rather than 0/negative/unparseable (§12.3–12.4).
- Tests for probe-skip, fallback probing, worker-cap enforcement, unsafe-concurrency prevention: all added (§12.2, §12.4); fallback probing itself was already covered by pre-existing tests (`test_context_tokens_fallback_when_model_unknown`, `test_unknown_model_offline_falls_back_to_8192`, `test_live_probe_overrides_catalogue_if_different`) and re-verified passing, not duplicated.
- Focused regression: run (§12.5).
- Before/after measured, RAM-improvement vs risk-reduction distinguished: §12.6.

**D5–D6 not started, per instruction.**

---

## 13. D5 design/verification phase (2026-09-18, from clean HEAD `5d76a40` — design only, nothing implemented)

**D5 — streaming**, scoped per §7's own table row ("requires the User's transport/approval-interaction decision"). This section is the requested design document: acceptance criteria, risks, and test scenarios for a future implementation batch. No production code changed in this phase.

### 13.1 Current response path, traced end-to-end

- **`POST /ask`** (`server.py:1287`) is a **synchronous `def` returning a plain `dict`** — no `async def`, no streaming response type, no SSE/WebSocket infrastructure anywhere in `server.py` (confirmed by direct search: zero matches for `StreamingResponse`/`EventSourceResponse`/`text/event-stream`). Four-tier fallthrough, in order: (1) an early `workflow_continuation` check when `session.active_workflow_status == "waiting_for_input"` (`:1337-1379`); (2) `native_tool_loop.run_native_tool_loop()` (Tier 0/Tier 1, **off by default** via `native_tool_loop_enabled()`, `:1392-1411`); (3) `canonical_execution.run_canonical_for_ask()` (`:1419-1449`); (4) legacy `orchestrator.process_user_input()` (`:1451-1470`, the terminal fallback). Whichever tier produces a non-`None` `result` short-circuits the rest.
- **`native_tool_loop.run_native_tool_loop()`** (`native_tool_loop.py:291-398`): each iteration calls `model_callable(system=..., user=..., tools=tools)` once, synchronously, returning one complete `ModelResponse`. `tool_calls = response.tool_calls or ()`; empty ⇒ `_terminal_envelope(content=response.content, ...)` (Tier 0 — **the Brain's own content IS the reply**, no separate drafting/validation call). Non-empty ⇒ translate → `evaluate_gates()` → `_execute_canonical()` (existing, unmodified since M32 Batch C), results fed back to the Brain for another iteration (bounded by `DEFAULT_MAX_ITERATIONS = 3`).
- **`response_drafting.draft_response()`** (canonical/legacy paths only, used when `native_tool_loop` is off — today's actual default production path): a **separate** narrative-phrasing call whose output is passed through `validate_drafted_response()` **after** the full text returns, before being trusted (`orchestrator.py:3761-3774`). This is a materially different shape from Tier 0's "content is the reply" contract.
- **`ModelProvider.complete()`** (`model_providers/base.py:239-255`, the ABC every adapter implements): returns **one complete `ModelResponse`**, always. None of the 3 adapters (`OllamaProvider`, `AnthropicProvider`, `OpenAICompatibleProvider`) has any streaming parameter or method; `OllamaProvider.complete()` explicitly hardcodes `"stream": False` in its request payload (`ollama_provider.py:131`).
- **Approval**: gate evaluation (`decision_gates.evaluate_gates()` → `ApprovalGate.execute_tool()`) runs synchronously, **inside the same `/ask` call**, strictly before any response is returned. An approval-required outcome ends that `/ask` call immediately with a **structured, non-prose** `"approval_required"` status plus a persisted `ApprovalStore` proposal (`approval_store.propose(...)`). Resumption is `POST /approve` (`server.py:1564-1607`) — an entirely separate, later HTTP request/connection, never inside the same stream.
- **Persistence**: `UriOrchestrator._record_conversation_turn_safely()` (`orchestrator.py:4624-4676`) is called with the **fully-completed** `result` dict — never incrementally, never before the turn is fully decided. `native_tool_loop`'s own envelope construction follows the identical discipline (full envelope built, then returned).
- **Resumability** (`workflow_continuation`): checked at the very top of `/ask`, before any model call — also a structured, non-prose turn.
- **Prior art, re-verified**: `M32_EXECUTION_ARCHITECTURE_PLAN.md` §"C4/C6 — Streaming, end to end" already researched this exact question and found the same 3 hard blockers this trace reconfirms today: provider layer hardcodes non-streaming; `/ask` is sync with no SSE infra; the Flutter `UriClient.ask()` returns `Future<UriTurn>` with no incremental-update path (`app_state.dart:483-519`). Nothing has changed since that finding; this section extends it with the concrete design those blockers require, not a re-derivation.

### 13.2 Where token streaming can safely begin

**Scope decision:** streaming applies only to the terminal, already-decided narrated text of a turn — **never** to a call whose result might still need gate evaluation. Two theoretically eligible call sites exist; only one is in scope for a first batch:

1. **`native_tool_loop`'s per-iteration `model_callable()` call** — in scope, via the mechanism below.
2. **`response_drafting.draft_response()`** — explicitly **out of scope** for a first batch (§13.12/R-D5-5): its output is validated *after* full generation, which conflicts with "shown live" unless a separate buffer-then-validate-then-flush strategy is designed, which this phase does not attempt.

**Mechanism — "buffer-until-classified, then flush":** consume the provider's stream chunk by chunk server-side. Forward nothing to the client until the first non-empty chunk classifies the response as content-only (not a `tool_calls` delta) — this matches the OpenAI-compatible wire convention every provider here already follows for non-streaming tool calling (a tool-calling completion's *first* delta already carries `tool_calls`, never prose first, when chain-of-thought is suppressed — see R-D5-1 for the caveat). Once classified content-only, forward every subsequent chunk live. If a `tool_calls` delta ever appears — including, defensively, after some content deltas already arrived — **abort streaming display and fall back to the buffered, non-streaming completion path for that call.** The translation/gate/execution pipeline never learns streaming was attempted for that turn.

### 13.3 Behavior when a tool call or approval interrupts a streamed response

- **Tool call appears mid-stream:** abort-and-fallback, never partial-commit. The buffered chunks are reassembled into the exact same `ModelResponse` shape `run_native_tool_loop()` already expects; execution proceeds byte-for-byte as it does today from that point on. The client is explicitly told the in-progress display is superseded (a distinct SSE event, e.g. `tool_call_detected`) — never left to guess from a silently-stopped stream.
- **Approval required:** by construction, this never happens mid-stream (§13.1) — approval evaluation is downstream of a *completed* tool-call decision, which (per §13.2) never streams prose in the first place. No new design surface here; this is a confirmed non-interaction, not an assumed one.

### 13.4 Cancellation/error semantics

- **Client disconnects mid-stream:** server detects it (Starlette `request.is_disconnected()` / `CancelledError` on the async generator) and cancels the outstanding upstream provider HTTP call — avoids burning model compute for nobody, and avoids leaving an orphaned connection under the 97%-RAM-pressure condition D4 already measured (R-New-1). The turn is marked `client_disconnected`, never recorded as a normal completed narrative (`mark_narrative_unavailable`'s existing "never fabricate success" discipline, extended — not reinvented).
- **Provider-side stream error/timeout mid-generation:** whatever partial content the client already received stays visible in the UI (best-effort, never retracted), but is **never persisted as a complete, successful narrative** — persisted with an honest, distinct status (§13.5).
- **Iteration cap:** unaffected — `DEFAULT_MAX_ITERATIONS` governs `native_tool_loop`'s tool-loop iterations, not token generation within a single streamed call.

### 13.5 What is persisted if a stream stops mid-turn

Persistence remains a **single, after-the-fact write** of the real, complete (or honestly-marked-partial) text the Brain actually produced server-side — never driven by what the client happened to receive, exactly mirroring `_record_conversation_turn_safely`'s existing "full result dict only" discipline (§13.1):

- The server always fully drains (or explicitly times out) the provider's stream, independent of client connection state, before the existing persistence step runs.
- A stream that completes normally persists **identically** to today's non-streaming path — zero format change to `conversation_history`/audit records.
- A stream that is interrupted (client disconnect, provider error) persists a **distinct, additive** partial marker (never a repurposed existing status value — R-D5-4) — extends `mark_narrative_unavailable`'s "diagnostic metadata, no synthesized reply" pattern rather than inventing a parallel one.
- `ApprovalStore`/`CapabilityRegistry`/`AuditTrail` persistence is entirely unaffected — those only ever run against a *complete* decision (§13.3), before any prose streaming could have started.

### 13.6 Compatibility with native tool loop and resumed approval

- **`native_tool_loop`:** `run_native_tool_loop()`'s public contract (inputs, return envelope shape, iteration cap, per-branch execution, audit points) stays **unchanged**. The only new thing is an optional streaming variant of the `model_callable` seam it already takes as a parameter — one that can progressively yield chunks while still returning the identical final `ModelResponse` shape at the end, so `run_native_tool_loop`'s own logic (`response.tool_calls`, `response.content`) needs no change. Streaming happens strictly *around* this function (a new caller-side wrapper), never inside it — this is what "compatible with native tool loop" means concretely here, and it is enforced by not touching the function at all.
- **Resumed approval (`POST /approve` / `decide_action`):** unaffected by construction — approval always resumes a structured proposal record, never streamed prose (§13.3). No new interaction surface between the two exists to design.
- **`workflow_continuation` resumability:** same reasoning — a resumed workflow's turn is evaluated by the deterministic Decision Contract path before any model content call.

### 13.7 TTFT and end-to-end latency metrics

- **TTFT** (time to first token): server-side wall-clock from the streaming endpoint's request receipt to the first content byte flushed to the client *after* §13.2's classification resolves "content" (not the raw first provider byte, which could still turn out to be a tool call). Measured server-side (authoritative); a client-perceived variant may differ by real network/serialization time and must not be conflated with it.
- **End-to-end/total duration:** unchanged in meaning from today's existing `duration_seconds` (`ModelResponse`/`UsageRecord`) — total wall-clock for the model call to fully complete, independent of client delivery timing.
- **New field:** `ttft_seconds` (`Optional[float]`, `UNAVAILABLE` confidence when not measured — e.g. a fallback single-chunk or aborted-to-non-streaming turn), added using the same `ConfidenceValue`-wrapped numeric-field convention `UsageRecord` already uses (M21 self-knowledge discipline). Additive only — no existing field renamed or removed.
- Reuse the existing `m32_latency_profile.py`/`m32_repeat_check.py` instrumentation harness (§7's own D6 charter: "promote to a committed, repeatable harness... re-measure against this report's numbers") rather than building a parallel one. Adding TTFT to that harness is D6's job, once D5 is actually implemented — not this design phase's.

### 13.8 Provider/model-agnostic behavior, preserved

- New **optional, non-abstract** method on the `ModelProvider` ABC, e.g. `complete_stream(...)`, with a **default implementation on the base class** that calls the provider's existing `complete()` and yields the whole response as one terminal chunk. This is the mechanism that keeps every provider that hasn't been individually upgraded (at implementation time: possibly all three, on day one) working correctly and identically to today, with zero required code change in those adapters. Real token-by-token streaming becomes an opt-in per-adapter override — Ollama is the best first real target (already sends `"stream": False` explicitly; `/api/chat` accepts `"stream": true` natively).
- `ModelRouter.attempt()`/`resolve()` need no change to carry streaming — mirrors the prior, already-verified finding for tool-calling support (C1.3: `attempt(role, principal, **complete_kwargs)` forwards verbatim). A streaming call is routed, health-tracked, and budget-checked exactly like today's `complete()` call; it just returns/yields a different shape.
- No model-selection semantic change: which provider/model is chosen is entirely unaffected — this is purely a delivery-mechanism change for an already-selected candidate's output.

### 13.9 Acceptance criteria

1. A new streaming endpoint (e.g. `/ask/stream`) exists, additive; `/ask` is unchanged, byte-for-byte, in both behavior and response shape.
2. `ModelProvider.complete_stream()` exists with a correct, tested default fallback for every adapter not individually upgraded — proven to produce output identical to that adapter's existing `complete()` result, delivered as one chunk.
3. Tier 0 (no tool call) turns stream live, chunk by chunk; TTFT is measured and materially lower than full-response latency for the same turn (same before/after rigor as D1/D2's own methodology).
4. A tool-calling response is never partially streamed as prose to the client — a test asserts **zero** content bytes reach the client for a tool-calling turn, proving abort-and-fallback triggers on the first `tool_calls`-shaped delta.
5. `run_native_tool_loop()`'s own source is unmodified, or if a seam is added, its existing non-streaming call sites are provably byte-for-byte unchanged — the full existing D2/D4/C3.x suites pass unmodified.
6. Full existing approval/grants/audit/dispatch regression suite (`decision_gates`, `approval_gate`, `canonical_execution`, `multi_action_dispatch`, C3.4 concurrency, D3/D4 model-router/worker-cap suites) passes unmodified.
7. Client disconnect and provider-stream-error are both explicitly tested: correct upstream cancellation, correct honest persistence (§13.5), no orphaned provider connection.
8. A stream that completes normally persists an identical `conversation_history`/audit record shape to today's non-streaming completion of the same turn (diffed directly in a test, not merely asserted).
9. Provider-agnostic: the same streaming endpoint and client code path work correctly (falling back to single-chunk delivery) against a provider with no real streaming implementation.
10. No model-selection semantic change: `test_model_router_*` (58 tests, D3/D4) and the D4 worker-cap suite pass unmodified as-is.

### 13.10 Risks

| # | Risk | Mitigation |
|---|---|---|
| R-D5-1 | A model/provider that interleaves prose before a tool call (breaking the OpenAI-compatible convention §13.2 relies on) could let real prose reach the client before abort-and-fallback triggers | Ollama's own `"think": False` (`ollama_provider.py:150`) already suppresses the most likely real-world source of this; verify empirically against real Ollama tool-calling stream output before enabling by default; keep abort-and-fallback as defense-in-depth, not the sole protection |
| R-D5-2 | A streaming endpoint becomes a second, independently-drifting implementation of `/ask`'s 4-tier fallthrough, doubling maintenance surface | Refactor the routing decision into one shared internal helper both `/ask` and the streaming endpoint call, rather than re-implementing tier selection — an implementation-time task, flagged now so it is not missed |
| R-D5-3 | Incorrect disconnect detection/upstream cancellation leaks an open provider connection per abandoned turn, compounding D4's own measured 97% RAM pressure (R-New-1) | Explicit test requirement (§13.9 item 7); reuse the same `requests` timeout/cancellation discipline already established in `ollama_provider.py` |
| R-D5-4 | A new partial/interrupted persistence marker, if implemented as a repurposed existing status value rather than a new additive field, could be silently mis-rendered as a normal successful turn by a consumer that doesn't recognize it | Strictly additive field (e.g. `narrative_interrupted: bool` alongside the existing `narrative_unavailable_reason`), never a repurposed status — matches this repo's additive-field discipline throughout M21/M22/M32 |
| R-D5-5 | `response_drafting.draft_response()` streaming, if a future batch naively extends today's design to it without addressing `validate_drafted_response()`'s post-hoc rejection, could show the user text URI itself has since disowned | Explicitly descoped here (§13.2/§13.12), not silently deferred; any future batch touching `draft_response()` must design its own buffer-then-validate-then-flush strategy rather than inherit Tier 0's design unmodified |
| R-D5-6 | Unbounded concurrent open streaming connections under the same 97% RAM condition D4 measured | Apply the same "safe, configurable cap" discipline D4 established for `ThreadPoolExecutor` workers — an explicit, deployment-configurable max-concurrent-stream cap is a required implementation-time deliverable, not an afterthought |

### 13.11 Test scenarios (for the implementation batch — not run in this design phase)

1. Tier 0 plain-chat turn: content streams live in order; concatenated chunks match non-streamed `complete()` output exactly.
2. Tier 1 tool-calling turn: zero content bytes reach the client before abort; final result identical to today's non-streaming Tier 1 path (existing C3.x/D4 assertions re-run against the streaming code path too).
3. Provider without real streaming support (default `complete_stream()` fallback): single-chunk delivery; TTFT ≈ total latency, never a false improvement claim.
4. Client disconnects mid-stream: upstream provider call cancellation asserted directly (spy/mock, not a timing race); turn persisted as `client_disconnected`, never as normal success.
5. Provider stream errors/times out mid-generation: partial content never persisted as a complete narrative; distinct honest status recorded, `mark_narrative_unavailable`-style reason present.
6. Concurrent requests against the same session while a stream is in flight: no double-persistence, no corrupted `conversation_history` ordering (reuses `test_multi_client_runtime.py`/`test_multi_user_isolation.py`'s existing discipline).
7. Approval-required turn reached via the streaming endpoint: response is the same structured, non-prose `approval_required` status as today's `/ask`, never partially streamed.
8. Workflow-continuation-paused session hitting the streaming endpoint: routed identically to today's `/ask` (§13.1's early-path check), never bypassed by the new endpoint.
9. TTFT measurement: `ttft_seconds` populated and `< duration_seconds` for a genuinely streamed turn; absent/`UNAVAILABLE` for a fallback or aborted-to-non-streaming turn — never a fabricated number.
10. Max-concurrent-stream cap (R-D5-6): exceeding the configured cap degrades safely (documented policy, e.g. fall back to non-streamed `/ask` or queue) rather than exhausting resources.

### 13.12 Explicitly out of scope for the D5 implementation batch

- `response_drafting.draft_response()` (canonical/legacy narrative) streaming — R-D5-5.
- Flutter client (`UriClient`/`AppState`) implementation — a separate, sequenced follow-on per the original plan's own finding (`app_state.dart:483-519` has no incremental-update path today); this design commits only to the server-side contract (SSE event shapes) such a client change would consume.
- Cross-capability multi-tool streaming interactions — inherits whatever `M32_EXECUTION_ARCHITECTURE_PLAN.md` §C3.3's own still-unresolved scope is; not widened here.
- Anthropic/OpenAICompatible real token-by-token streaming — only their safe fallback behavior (§13.8) is required on day one.

**This is a design/verification record only. No code was implemented in this phase. D6 not started.**

---

## 14. D5 implementation and verification (2026-09-18, from clean HEAD `5d76a40`, against the frozen §13 design)

**User clarification incorporated before implementation:** a first content chunk never proves a turn is terminal. Streamed prose is provisional UI output only — never persisted as completed narrative, never treated as authoritative completion — until a "done" event arrives. If a tool call appears at any later point, the prose stream is terminated, the turn is marked `narrative_interrupted`, and execution continues through the existing buffered canonical/tool path with gates and approvals unweakened. §14.3 covers how this is enforced end to end, not merely asserted.

### 14.1 What changed

- **`uri_core/core/model_providers/base.py`**: new `StreamChunk` dataclass (`content`, `is_tool_call`, `done`, `final_response`, `ttft_seconds`); new **non-abstract** `ModelProvider.complete_stream()` with a default implementation that calls the provider's own `complete()` and yields the whole result as one terminal chunk. Exported from `uri_core/core/model_providers/__init__.py`.
- **`uri_core/core/model_providers/ollama_provider.py`**: real token-by-token `complete_stream()` against Ollama's `/api/chat` with `"stream": true` — live-confirmed NDJSON wire shape (§14.2). Refactored `complete()`'s payload construction and context-window check into two shared helpers (`_build_chat_payload`, `_check_context_window`) reused by both methods — a mechanical, behaviour-preserving extraction, verified via the full pre-existing `test_ollama_provider.py` suite passing unmodified before adding anything new. A stream that ends without ever sending a `"done": true` line now raises `ProviderResponseError` explicitly — found and fixed during this batch's own testing (§14.4); previously this path did not exist at all.
- **`uri_core/core/model_router.py`**: new `ModelRouter.attempt_stream()`, mirroring `attempt()`'s ordered-candidate/health-tracking/budget-gating structure exactly. New safety property beyond `attempt()`: once any content has been yielded to the caller for a candidate, that candidate is **committed** — a later, mid-stream failure from that same candidate is re-raised, never silently retried against a different provider (the caller has already been shown some of its own words). A failure *before* any content is yielded may still advance to the next candidate, identical to `attempt()`. `attempt()`/`resolve()` themselves are untouched.
- **`uri_core/core/stream_tool_loop.py`** (new module): `stream_first_turn()`, the streaming wrapper around `run_native_tool_loop()`'s Tier 0 fast path. **`native_tool_loop.py` itself has zero diff** — confirmed by `git diff --stat` before every commit in this batch. The wrapper supplies a specialized `model_callable` closure (the function's own documented injectable seam) that streams iteration 1's content live via a queue/background-thread producer pattern while still returning the identical `ModelResponse` shape the function already expects; only iteration 1 is eligible for live streaming (§13.2/§13.12 scope decision) — any later iteration uses the existing, unmodified `router.attempt()`. Includes `DEFAULT_MAX_CONCURRENT_STREAMS`/`URI_MAX_CONCURRENT_STREAMS` (R-D5-6), mirroring D4's own worker-cap discipline exactly.
- **`uri_core/app/server.py`**: new `POST /ask/stream` endpoint. Extracted `_resolve_ask_context()` (identity/personalization/principal resolution) and `_finalize_ask_response()` (serving-model annotation + trimmed response shape) out of `ask()` verbatim, so the new endpoint can reuse them with zero duplication risk — both extractions verified behaviour-preserving via the full pre-existing `/ask`-touching test suite passing unmodified before adding anything new (§14.4). The new endpoint streams live **only** when `native_tool_loop_enabled()` is true and no `workflow_continuation` pause is pending for the session (`_ask_stream_eligible`); every other case — including a `StreamCapacityExceededError` or `stream_first_turn` reporting `envelope=None` (the same "None means fall back" convention `/ask`'s own native-tool-loop branch already follows) — delegates to the existing, completely unmodified `ask()` function and re-emits its single dict as one terminal `message` SSE event. `/ask` itself is unchanged in behaviour (§14.4).

### 14.2 Real Ollama streaming evidence (live server, this deployment)

Probed directly against this machine's real Ollama server before writing the adapter, using the actually-installed `gemma4:12b` (`qwen3:14b`, the packaged default, is not installed here — see D3):

```
--- tool-calling completion, streamed ---
{"message":{"content":"","tool_calls":[{"id":"call_976zxqu5","function":{"name":"get_weather","arguments":{"city":"Paris"}}}]},"done":false}
{"message":{"content":""},"done":true,...}

--- plain-content completion, streamed ---
{"message":{"content":"Hello"},"done":false}
{"message":{"content":","},"done":false}
... (token-by-token) ...
{"message":{"content":""},"done":true,"prompt_eval_count":20,"eval_count":10,...}
```

Confirms the design's central assumption empirically: a tool-calling response's first line already carries the full `tool_calls` array with `content: ""` — no prose precedes it for this real model. `complete_stream()`, `ModelRouter.attempt_stream()`, `stream_first_turn()`, and the full `/ask/stream` HTTP endpoint were each re-verified end to end against this same live server after implementation (not just unit-tested) — both the plain-content case and a real Gmail tool-call case (via the real `_Fixture`'s wired `FakeGmailService`, exercising the genuine gate/dispatch path):

```
=== plain content, via stream_first_turn() ===
CONTENT: 'Hello' / ',' / ' I' / ' am' / ' your' / ' assistant' / '.'
done ttft=0.649s narrative_interrupted=False
envelope narrative: Hello, I am your assistant.

=== real Gmail tool call, via stream_first_turn() ===
tool_call_detected ttft=None narrative_interrupted=False
done ttft=None narrative_interrupted=True
envelope status: success
envelope execution: {..., "capability": "Gmail", "action": "search_messages", "status": "success", ...}

=== full HTTP endpoint, POST /ask/stream, plain content ===
event: content  data: {"text": "Hello"}
... (7 content events) ...
event: done  data: {"response": {...,"narrative":"Hello, I am your assistant."}, "ttft_seconds": 1.618, "narrative_interrupted": false}
```

Zero content bytes ever reached the client for the tool-call turn; the real Gmail search executed correctly through the completely unmodified gate/dispatch pipeline.

### 14.3 Enforcement of the User's clarification (provisional-until-done, late tool call)

- `TurnStreamEvent(kind="content", ...)` is documented and treated as provisional — the module docstring and `TurnStreamEvent`'s own docstring state this is never to be persisted on its own.
- Every chunk of iteration 1 (not just the first) is checked for `chunk.is_tool_call` inside `stream_first_turn`'s closure — `test_tool_call_in_first_chunk_also_works_with_zero_content_events` and `test_content_then_tool_call_marks_narrative_interrupted_and_executes_for_real` (`test_m32_d5_stream_tool_loop.py`) prove both orderings work identically.
- The instant a tool call is detected, `TurnStreamEvent(kind="tool_call_detected")` fires exactly once (`state["tool_call_signaled"]` guards against duplicates), and the turn continues through `run_native_tool_loop()`'s **completely unmodified** translate → gate → execute path — proven with the real `_Fixture` (real `ApprovalGate`/`ToolDispatcher`/`MultiActionDispatch`), not a mock, so gates/approvals were genuinely exercised, not assumed unweakened.
- The terminal `envelope["narrative"]` on a late-tool-call turn reflects the REAL post-execution answer (`"I found it."` in the test, the real Gmail search result live), never the provisional prose shown before the tool call (`"Let me check your inbox..."`) — asserted directly, not inferred.
- `narrative_interrupted: True` is carried on the `done` event/SSE payload whenever this happened, so a client can distinguish "this was always plain prose" from "the prose shown was provisional and superseded."

### 14.4 Tests added and regression

**37 new tests**, all passing:

| File | Count | Covers |
|---|---|---|
| `test_ollama_provider.py` (+10) | 10 | `complete_stream()`: content deltas, TTFT-on-first-content-only, tool-call parsing, 404/timeout/connection/malformed-JSON errors, context-window pre-check, response closed on success and on 404 |
| `test_model_router_stream.py` (new, 9) | 9 | `attempt_stream()`: happy path, tool-call chunks, fallback-before-content, commit-once-content-shown (never silently retries after showing real words), auth-error propagation before/after content, `ModelNotFoundError` marks unhealthy + falls back, non-streaming-provider default fallback with `ttft_seconds == duration_seconds` |
| `test_m32_d5_stream_tool_loop.py` (new, 12) | 12 | Content-only turn + envelope-identity-to-non-streaming-call proof (persistence integrity), late-tool-call-after-content, tool-call-in-first-chunk control, cancellation (mid-stream + consumer-stops-early), provider-error-mid-stream honest degrade, connection/thread cap (default bound, configurable, invalid-value fallback, immediate rejection without starting a thread), only-iteration-1-streams |
| `test_m32_d5_ask_stream_endpoint.py` (new, 6) | 6 | Toggle-off fallback (byte-shape match to a direct `/ask` call), content+done events, tool-call-detected forwarding, `envelope=None` fallback, `StreamCapacityExceededError` fallback |

**Broad focused sweep** (`-k "model_router or model_roles or ollama_provider or stream_tool_loop or ask_stream or native_tool_loop or m32_c or drafting or reasoning_adapter or decision_engine or document_composer or canonical_execution or approval or dispatcher or multi_action or capability_directory or m22_5 or ask_narrative or ask_size or authoritative_facts or multi_user_isolation or m32_c_server_wiring"`, 566 collected): **561 passed, 5 failed, 13 subtests passed.** The 5 failures are the identical pre-existing `qwen3:14b`-not-installed environment failures already root-caused in D3/D4 (`test_ollama_provider_live.py` x2, `test_ollama_reasoning_adapter_live.py` x3) — not new, not caused by D5.

**Bugs found and fixed by this batch's own testing (verification-first, not assumed correct):**

1. A stream ending without a terminal `done` chunk previously returned nothing usable — `OllamaProvider.complete_stream()` now raises `ProviderResponseError` explicitly instead of silently truncating (§14.1).
2. `stream_tool_loop._streaming_model_callable` could return `None` in the same scenario, which would have crashed `run_native_tool_loop()`'s own (unmodified) `response.tool_calls` access with an opaque `AttributeError` instead of its existing, honest `"status": "unavailable"` degrade — fixed by raising instead of returning `None`, so the existing exception-handling path in `run_native_tool_loop()` (unmodified) produces the correct, already-audited outcome.
3. `POST /ask/stream`'s `await loop.run_in_executor(None, next, stream_iter)` violated PEP 479 (`StopIteration` cannot propagate out of a `Future`) — fixed with a sentinel-based `next(iterator, default)` wrapper instead of catching `StopIteration` around the awaited call.

All three were caught by the tests in this same batch, not discovered later — each is disclosed here rather than silently folded into "tests passed."

**Discovered, not caused by D5, not fixed (disclosed):** a mid-stream provider failure or a client-disconnect cancellation, when it happens during iteration 1's streamed call, is caught by `run_native_tool_loop()`'s own existing `except Exception as exc: return {"status": "unavailable", ...}` handling (unmodified) — meaning `stream_first_turn`'s own `TurnStreamEvent(kind="error", ...)` path is reachable only for failures *outside* that call (e.g. a bug in this wrapper itself, or `StreamCapacityExceededError` before the thread starts). This was verified directly (`ProviderErrorTests`/`CancellationTests` in `test_m32_d5_stream_tool_loop.py` assert a `"done"` event with `envelope["status"] == "unavailable"`, not an `"error"` event) rather than assumed from the design. This is a **better** outcome than the original design anticipated, not a gap: it means streamed failures reuse the exact same, already-audited honest-degrade path a non-streamed provider failure already used — zero new failure-reporting surface was needed.

### 14.5 Before/after TTFT and total latency, measured (real Ollama, this machine, warm model)

| Run | Streamed TTFT | Streamed total duration | Non-streamed total (`complete()`) | TTFT improvement |
|---|---|---|---|---|
| 1 | 0.152 s | 0.295 s | 0.221 s | 31% faster to first visible text |
| 2 | 0.097 s | 0.238 s | 0.223 s | 56% faster |
| 3 | 0.079 s | 0.222 s | 0.221 s | 64% faster |

**Cold-model run** (consistent with D1/D2's own previously-documented cold-load variance on this machine): TTFT 13.80 s, total 13.95 s — cold-load dominates both figures equally; not representative, shown for completeness rather than omitted.

**Honestly reported trade-off:** streamed total duration is modestly higher (≤0.07 s / ≤15% in these runs) than non-streamed `complete()` total — real overhead from NDJSON line-by-line parsing/accumulation versus a single JSON parse. TTFT is the metric this batch's design targets (perceived latency to first content), and it improves substantially (31–64% in these warm runs); total end-to-end generation cost is not reduced and is not claimed to be.

### 14.6 Requirements check

- `run_native_tool_loop()` unchanged unless evidence proved necessary: confirmed unchanged (`git diff --stat` shows zero delta); the streaming/cancellation bugs found (§14.4) were fixed entirely in `stream_tool_loop.py`/`ollama_provider.py`, never by touching that function.
- Provider/model-agnostic `complete_stream()` fallback preserved: `TestAttemptStreamProviderAgnosticFallback` proves a provider with no real streaming implementation still works correctly through `attempt_stream()`, with `ttft_seconds == duration_seconds` (never a fabricated improvement).
- Approval/resume/grant/audit semantics preserved: the late-tool-call test exercises the real, unmodified `ApprovalGate`/`ToolDispatcher`/`MultiActionDispatch` chain; `workflow_continuation`/approval-pending sessions are routed identically to today's `/ask` via `_ask_stream_eligible`'s own pending-workflow check, never bypassed.
- TTFT measurement: added (`ttft_seconds` on `StreamChunk`/`TurnStreamEvent`, surfaced in the `done` SSE event), measured real (§14.5).
- Tests for cancellation, provider error, late tool call after content, persistence integrity, fallback providers, connection/thread bounds: all added (§14.4 table).
- Focused regression run: run (§14.4).
- Real Ollama streaming evidence: gathered before, during, and after implementation, at every layer (provider, router, wrapper, HTTP endpoint) (§14.2).
- Before/after TTFT and total latency reported: §14.5.

**D6 not started, per instruction. No commit or push has been made.**

---

## 5. Proposed architectural changes (not authorized — for review)

These follow directly from §4 and are ordered by measured impact. None has been implemented.

1. **Share one `CapabilityDirectory` per turn**, built once by `run_native_tool_loop`'s own `build_turn_state_and_directory` call and passed into `build_tool_schemas` instead of it constructing a second, independent one (see §4's correction: these are the only two real construction sites in this path — `_execute_canonical` does not build one). This alone would cut F2/F3's ~2-second-per-turn tax to a single ~1 second cost (or near-zero, combined with #2 below).
2. **Persist the refreshed Google credential back to `token_path` after a successful `creds.refresh()`** in `load_usable_credentials()` (`google_auth_common.py`), so a token refreshed once stays valid (typically ~1 hour for Google access tokens) instead of being re-fetched from Google on every single call. This is a small, bounded, well-understood fix (write the refreshed `creds.to_json()` back to disk) that directly removes the root cause of F2/F3, independent of #1.
3. **Fix or reconfigure the default model resolution** (F1) — either ship a packaged default that matches what a fresh install would actually have (impossible to guarantee in general), or, more robustly, fail loudly and early with an actionable error message distinguishing "no model configured" from a silent `AllProvidersUnreachableError`, and/or document `OLLAMA_MODEL`/`OLLAMA_NUM_CTX` as required deployment configuration. This is a correctness/operability fix, not purely a latency one.
4. **Set `OLLAMA_NUM_CTX` explicitly in deployment configuration** to skip the live `/api/tags` context-length probe on every `build_provider("ollama")` call (§2.1) — a small (~30 ms) but free win once #1/#2 make the dominant cost visible.
5. **Bound the `ThreadPoolExecutor` in `execute_translated_batch`** (`native_tool_loop.py:258`) with a fixed `max_workers` cap, given the measured current memory pressure (§2.10) — a defensive change with no measured incident behind it yet, proposed because the risk is now visibly real on this machine, not hypothetical.
6. **Streaming (`stream=True` + SSE `/ask`)** remains the single largest *perceived*-latency lever per the original diagnostic report §6/§9 (P2) and is unaffected by anything found this phase — still recommended, still not started, still requires the User's go-ahead on transport/approval-pause interaction (risk R3 in the original report, unchanged).
7. **Prompt-size reduction** (the original report's P1) remains valid and unexercised this phase — not re-measured, since this phase's scenarios all used the compact Tier 0/1 system prompt already (`native_tool_loop.py:392-396`), which is already far smaller than the legacy 3-call prompt volume documented in the original report §4.2. No new evidence for or against P1 was gathered this phase.

---

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| R-New-1 | Unbounded `ThreadPoolExecutor` sizing under measured 97%-memory-utilization conditions could exhaust resources on a turn with many parallel-eligible tool calls (not yet observed, only structurally possible) | §5 item 5; bound `max_workers` |
| R-New-2 | Persisting refreshed OAuth credentials (§5 item 2) touches the same credential file the disclosed-but-not-yet-actioned `M32_LATENCY_DIAGNOSTIC_REPORT.md` §8.1 install-wide-Gmail-sharing finding also touches — any change here should be scoped to "persist the refresh," not extended into re-scoping credential storage, which is the User's separate, undecided architecture question (§8.1 of that report) | Keep #2 minimal and mechanical; do not fold in credential re-scoping |
| R-New-3 | Fixing F1's default-model resolution incorrectly (e.g., silently substituting a different model) could violate the User's explicit Active-Brain-choice model | Prefer "fail loudly and early" over "silently substitute" (matches this repo's own established discipline, `model_roles.py:27-38`) |
| R-New-4 | Caching a `CapabilityDirectory`/connection-status snapshot per turn (§5 item 1) must not let a stale "connected" status survive past the point a user actually disconnects a service mid-turn | Scope the cache to one turn only (already the natural lifetime of `run_native_tool_loop`'s single invocation); never cache across turns without a separate, explicit TTL decision |
| R1–R8 (original report) | Unchanged — still apply to the tiering work now shipped (Batches A–C); not re-litigated here | See `M32_LATENCY_DIAGNOSTIC_REPORT.md` §11 |

---

## 7. Recommended implementation batches (sequenced, not authorized)

| Batch | Work | Expected effect |
|---|---|---|
| **D1 — OAuth refresh persistence** | §5 item 2 alone: persist refreshed credentials back to `token.json`. Smallest, most isolated, highest-confidence fix. | Removes the repeated-refresh cost on the *second and later* calls within a short window; first call per token lifetime still pays one refresh. |
| **D2 — single shared `CapabilityDirectory` per turn** | §5 item 1: thread one directory instance from `run_native_tool_loop`'s own top-level build into `build_tool_schemas`, instead of it building a second one. | Combined with D1, collapses the 2 independent constructions per turn found in §2.2/§4 (F2, corrected) to one. This is the single highest-impact, best-evidenced batch in this report. |
| **D3 — default-model-resolution correctness fix** | §5 item 3: loud, actionable failure (or documented required config) instead of a silent `AllProvidersUnreachableError` for the packaged default. | Correctness/operability, not raw latency — but blocks any of the other numbers in this report from being real for an unconfigured install. |
| **D4 — context-probe skip config + thread-pool bound** | §5 items 4 and 5: cheap, independent, low-risk. | Small (~30 ms) win + a defensive resource cap under measured memory pressure. |
| **D5 — streaming** | Original report's P2, unchanged, still the largest perceived-latency lever, still requires the User's transport/approval-interaction decision (R3). | first token latency ≈ model TTFT instead of full-turn latency. |
| **D6 — re-run this phase's full benchmark battery after D1–D4** | Promote `m32_latency_profile.py`/`m32_repeat_check.py`/`m32_cprofile_check.py` (currently scratchpad-only) to a committed, repeatable harness (mirrors the original report's own P0 recommendation, never actioned) and re-measure against this report's numbers as the recorded baseline. | Closes the loop with real before/after evidence, not projection. |

**Sequencing note:** D1 and D2 are the two changes this report's own evidence most directly supports — they are the only ones backed by an exact `cProfile`-attributed root cause rather than a structural observation. D3–D4 are small and independent and could ship alongside D1/D2. D5 is unchanged in status from the original report and still needs the User's decision on streaming-vs-approval-pause interaction before it is scheduled. D6 should close whichever of D1–D4 the User approves, not be skipped.

---

## 8. Disclosed unverified items

1. **§2.3's non-model-overhead figures for multi-branch scenarios are not perfectly linear** with branch count (F4's precise scaling curve) — the qualitative mechanism is confirmed by source (`canonical_execution.py:456`), the exact per-branch cost is not isolated from run-to-run jitter in this phase.
2. **Streaming/TTFT (§2.8) and backend-to-UI handoff (§2.9) were not independently re-measured this phase** — both are re-confirmed unchanged by source reading only, carried forward from the original diagnostic report, not newly measured.
3. **No approval/resume end-to-end HTTP scenario was run** — the in-turn native-tool-loop path does not create durable approvals at all (matches Batch B's already-disclosed gap); a true resume test would need to exercise the canonical path over real HTTP, not done this phase.
4. **No representative document-drafting scenario was run** (`document_composition` role/`DocumentComposer` untouched this phase).
5. **Cloud providers (Anthropic/OpenAI-compatible) were not exercised** this phase — local Ollama only, matching every prior M32 measurement session's own disclosed scope limit.
6. **The RAM-pressure figure (§2.10) is a point-in-time snapshot** of this specific development machine at measurement time, not a controlled or repeated series — presented as real, current evidence per the User's instruction to treat it as runtime evidence rather than assumption, not as a permanently-fixed characteristic of every deployment.
7. **This report's probe scripts are not yet committed** — same disclosed gap as the original diagnostic report's own P0 recommendation (§12 there), never actioned; D6 above proposes finally closing it.

---

## 9. Conclusion

Batches A–C's tiering (Tier 0/Tier 1, native tool calling, canonical execution) genuinely works and genuinely shipped — the architecture itself is sound, gates are intact, and model inference on a local 12B model is fast (0.47–1.64 s per call, consistent with the original diagnostic report's measured model floor). But **the as-built system today pays roughly 2–3 seconds of URI-side overhead on every single turn, dominated by a single, precisely root-caused mechanism**: every turn independently constructs one or more `CapabilityDirectory` instances, each of which performs a live, uncached round trip to Google's OAuth token endpoint because a refreshed credential is never written back to disk. This cost is present even for a turn that never touches Gmail or Drive at all, and it is larger than model inference time for the simplest possible turn (Tier 0: 81% of total latency).

Separately, and independently of latency: the packaged default model name does not match what is actually installed on this machine, and no deployment configuration currently bridges that gap — meaning the real production default-routing path is non-functional today for any caller without a manually configured Active Brain. This did not affect the validity of Batch A/B/C's own test suites (which use fakes/mocks) but does mean their own live-evidence probes, and this report's own measurements, all had to explicitly work around it to produce a working measurement at all.

Nothing in this report has been implemented. No production code was modified, and nothing was committed or pushed. §7's batches are presented for the User's review and explicit approval before any implementation begins.
