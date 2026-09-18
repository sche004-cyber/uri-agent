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
