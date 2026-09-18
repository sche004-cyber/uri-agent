# M32 — URI Brain Latency / Core Execution Diagnostic Report

**Date:** 2026-09-17. **Status:** INVESTIGATION COMPLETE — findings and recommended architecture presented for review. **No production code was modified. Nothing was committed or pushed.**
**Author:** Claude (planning/investigation role).
**Scope boundary:** this is the latency/core-execution investigation the User authorised. It does **not** advance `M32_CANDIDATE_BLUEPRINT.md` (External Capability Bridge), which remains frozen and out of scope, and it does **not** continue Hybrid UI work.

---

## 0. Acceptance criteria for this report (defined before the findings)

Per the repository's Verification-First standard, this report is only acceptable if:

1. Every latency number comes from a **measured** run against the real code path, not an estimate.
2. The execution path described is the one that **actually executes in this deployment**, verified at runtime, not the one the design documents describe.
3. Model-added latency, URI-added latency, and transport/UI latency are **separated** with evidence.
4. Every architectural claim cites `file:line` or a measured artifact.
5. Anything not verified is **explicitly disclosed** as such, with its effect on the conclusions stated.
6. The recommendation distinguishes what is **mandatory** (safety/authorisation) from what is merely **current implementation**.

All six are met. §11 lists the disclosed unverified items.

---

## 1. Headline findings

| # | Finding | Evidence |
|---|---|---|
| **L1** | **"Hi" costs ~14 seconds and three sequential blocking model calls.** | Measured, §4 |
| **L2** | **The model is not slow — URI's prompts are.** The same local model answers "Hi" in **0.27 s** (74 ms to first token when streamed). URI turns that into ~14 s. | Measured, §5 |
| **L3** | **URI sends ~54,700 prompt characters (~13,000–14,000 tokens) to answer "Hi".** Two of the three calls carry ~6,400–6,900 tokens each. | Measured, §4.2 |
| **L4** | **The canonical M30.8 decision path never executes.** It is gated behind `URI_ENABLE_DECISION_ENGINE_LIVE`, which is set nowhere. Every live turn runs the legacy 6,153-line orchestrator. | Verified at runtime, §3.1 |
| **L5** | **There is no streaming anywhere** — not in any provider adapter, not in `/ask`, not in the Flutter client. Time-to-first-UI-token **equals** total latency. | Static + measured, §6 |
| **L6** | **No native tool calling exists anywhere in URI**, wired or dormant. Tool choice is a JSON-contract round trip. | Static, §7.1 |
| **L7** | **Both local models already support native tool calling**, including **multiple tool calls in a single response**, with correct argument extraction — at **0.4–1.4 s** per step. | Measured, §7.2 |
| **L8** | **A plain knowledge question fails on the shipped path.** "What is the difference between a list and a tuple in Python?" → 30.6 s → `failed`, `"URI does not have an implemented capability for this kind of task yet."` The **already-built, disabled** canonical path answers it correctly (§10). | Measured, §4.1 + §10 |
| **L9** | **Capability routing is keyword-based and has exactly two templates.** Anything not matching `insurance/renewal/note/noting` falls into a generic bucket that terminates in a hardcoded failure. | `workflow_planner.py:120-181`, §3.3 |
| **L10** | **Multi-part requests execute one tool and silently drop the rest**, passing the entire raw user sentence as the tool argument. | Measured, §4.1 (T4) |
| **L11** | **The safety machinery is deterministic, correct, and cheap.** Approval, grants and honest-failure reporting all behaved correctly under test and require **no** model call. | Measured + static, §8 |
| **L12** | **URI runs at the edge of its own self-imposed context window, and its own overflow guard fires in normal use.** `DEFAULT_CONTEXT_TOKENS = 8192` while real prompts reach 7,060 measured tokens — and URI logged its own *"exceeding the configured context_tokens (8192)… Ollama will silently drop the earliest content (typically the system prompt)"* warning **twice** during one 7-turn battery. The model's real context is **262,144**. | Measured, §4.5 |
| **L13** | **Optimising I/O would buy nothing.** Policy/soul disk reads, memory scans and session writes measure at **1–3 milliseconds combined**. The cost is prompt size and call count, nothing else. | Measured, §4.3 |
| **S1** | **Out-of-lane security finding: Gmail access is not user-scoped.** A probe account created minutes earlier successfully searched and returned the real operator's live email. Google credentials are process-global, at the repository root. | Measured + `connection_status.py:40-50`, §8.1 |

The single most important structural fact: **URI has no path in which the Brain simply answers.** Every message — including "Hi" — is forced through semantic interpretation, capability planning, and a separate drafting call.

---

## 2. Method

- **Live HTTP battery** against the real running backend (`scripts/run_uri_server.py --port 8000`), driving the real `/ask` endpoint exactly as the Flutter client does, on a throwaway probe account configured with the User's own Active Brain (`ollama` / `gemma4:12b`). 9 turns.
- **In-process instrumented battery**: the same `server.ask()` entry point called directly with timing wrappers around `ModelRouter.attempt`, the orchestrator's internal stages, and the reasoning gateway — giving per-call prompt sizes, per-stage durations, and exact model-call counts.
- **Direct provider benchmark** against Ollama with URI-shaped payloads, to establish the raw model floor and separate prefill from decode.
- **Native tool-calling probe** against both installed local models, using URI-shaped tool schemas from the real capability registry.
- **Static verification** of every code path cited, by direct file reading.

Probe scripts are in the session scratchpad (not committed): `m32_probe.py`, `m32_probe2.py`, `m32_http.py`, `m32_ollama_bench.py`, `m32_tools_probe.py`.

**Environment:** Windows 11; `gemma4:12b` (11.9 B, Q4_K_M) served by local Ollama; backend and model on the same machine. Measured model rates: **prefill ≈ 900–1,400 tok/s, decode ≈ 47–55 tok/s**, cold model load ≈ 15.8 s.

---

## 3. The execution path that actually runs

### 3.1 The canonical path is dead code in this deployment

`server.py:1385-1415` only calls `run_canonical_for_ask` when `decision_engine_live_enabled()` is true, which is `os.environ.get("URI_ENABLE_DECISION_ENGINE_LIVE") == "1"` (`canonical_execution.py:85-86`). That variable is set in no committed config, no launcher (`Launch URI.bat`, `scripts/launch_uri.ps1`, `scripts/uri_server_ctl.ps1`), and no `.env`.

Two independent runtime confirmations:

1. The instrumented in-process run of a real `/ask` turn recorded **zero** canonical stages and one `LEGACY process_user_input` stage covering the entire turn.
2. `uri_workspace/canonical_execution_log.jsonl` — which `run_canonical_for_ask` writes on **every** invocation, including fallbacks — has its newest entry at **2026-09-14T13:21:09**. The 9 live turns run for this report on 2026-09-17 added **nothing** to it.

This independently reproduces finding **F1** of the frozen `M32_CANDIDATE_BLUEPRINT.md`, and satisfies (negatively) the exit criterion its P2 phase sets: *"A real `/ask` turn is observed being handled by `run_canonical_for_ask`, evidenced by telemetry or log."* It is not.

**Consequence:** M30.8 is recorded COMPLETE with "canonical cutover", but production serves legacy. Per this repository's auditable-correction-history convention, that discrepancy must be recorded as a correction rather than quietly resolved.

### 3.2 The live path, stage by stage

For every `/ask` turn, authenticated, with no pending workflow:

| Order | Stage | Location | Model call? |
|---|---|---|---|
| 1 | `_resolve_context` (orchestrator **is** cached per user) | `server.py:463`, `:457-460` | no |
| 2 | `build_personalization_context` — reads **all** memory rows, filters, caps to 10 | `server.py:1309`, `personalization_context.py:65-118` | no |
| 3 | New `OllamaReasoningAdapter` + new `ProviderSemanticInterpreter` constructed **per request** | `server.py:1328-1335` | no |
| 4 | Canonical branch skipped (§3.1) | `server.py:1385-1415` | no |
| 5 | `process_user_input` (legacy) | `orchestrator.py` | — |
| 5a | `_interpret_semantic_result_safely` → **model call 1** | `orchestrator.py:371-380`, `:4766` | **yes** |
| 5b | `SkillMemory.find_matching_skill`, `CapabilityPlanner`, `WorkflowPlanner` | `orchestrator.py:4770+` | no |
| 5c | `_build_query_context` — capabilities, audit trail, known gaps, experience, files, evidence | `orchestrator.py:3397-3456` | no |
| 5d | `ModelReasoningGateway.reason` → **model call 2** (`policy.md` + `soul.md` re-read from disk) | `model_reasoning_gateway.py:319`, `:62-95` | **yes** |
| 5e | capability dispatch through gates, if a capability was chosen | `approval_gate.py:46+` | no |
| 5f | `_continue_brain_evaluation_loop`, up to `max_brain_iterations=3` further rounds | `orchestrator.py:3038`, `:119` | **yes, 0–3×** |
| 5g | `_record_conversation_turn_safely` — synchronous file write | `orchestrator.py:4616` | no |
| 6 | `_draft_narrative_safely` → **model call 3**, up to **2 attempts**; rebuilds `_build_query_context` a second time | `orchestrator.py:3605`, `:3740-3774` | **yes** |
| 7 | `_serving_model_for_turn` — reads the month's usage log | `server.py:854`, `:1465` | no |

**Minimum three sequential blocking model calls for any message.** Nothing is concurrent: `ask()` is a plain `def` and every stage above awaits the previous one.

### 3.3 Why non-"noting" work fails

`WorkflowPlanner._create_steps` (`workflow_planner.py:120-181`) branches on a substring match over `task + goal + requested_output`:

- matches `insurance` / `renewal` / `note` / `noting` → the 6-step evidence-drafting workflow, which ends in `draft_output` (a real, registered tool);
- **everything else** → a 4-step generic workflow ending in `prepare_output`, which returns `{"status": "failed", "error": "URI does not have an implemented capability for this kind of task yet."}` unconditionally (`workflow_capability_router.py:414-436`).

That hardcoded failure is deliberate and honest — the docstring explains it must not fake success — but it means the entire cost of the turn is paid **before** URI discovers it cannot proceed.

---

## 4. Measured latency

### 4.1 Test matrix — real HTTP, real backend, real Brain

| Test | Input | Total | HTTP | Outcome | Capability reached |
|---|---|---|---|---|---|
| T1 | "Hi" (cold) | **15.86 s** | 200 | `success` | — |
| T1b | "Hi" (warm) | **14.20 s** | 200 | `success` / `waiting_for_input` | — |
| T1c | "Hello" (warm) | **13.65 s** | 200 | `success` | — |
| T2 | list vs tuple in Python | **30.58 s** | 200 | **`failed`** — no implemented capability | — |
| T3 | search email for invoices | **19.49 s** | 200 | **`failed`** — no implemented capability | — (though `gmail_search` exists) |
| T4 | unread email **and** pending tasks | **31.13 s** | 200 | `not_found` | `gmail_search` only |
| T5 | create a draft email to a recipient | **35.51 s** | 200 | `awaiting_approval` ✅ | `gmail_create_draft` |
| T6 | fetch an unreachable URL | **29.88 s** | 200 | `unavailable` ✅ | `fetch_url` |
| T7 | three-step weekly review | **17.39 s** | 200 | `waiting_for_input` | — |

Notes on individual results:

- **T2/T3 are correctness failures, not just latency.** T3's own semantic analysis correctly said *"Search the user's email account for the keyword 'invoice'"*, and `gmail_search` is a registered, available tool — yet routing landed in the generic bucket (§3.3). *(Caveat: the probe account has no Gmail credentials, so a correctly-routed T3 would still have failed — but with a credential/connection error, not "no implemented capability". Routing never reached the tool.)*
- **T4**: the two-part request produced exactly one tool call, and the tool argument was the **entire raw sentence** — `query = "Check my unread email and also list my pending tasks"`. The task half was silently dropped. No decomposition, no argument extraction, no parallelism.
- **T5 and T6 are the good news.** The approval gate intercepted a high-risk action correctly (`action_id`, `tool_name`, `risk: high`), and an unreachable host produced an honest `unavailable`. The safety and honesty properties hold.
- **T1b vs T1c**: the same greeting produced a clarification question on one run and a capability summary on another — the greeting path is non-deterministic.

### 4.2 Where the ~14 s of a trivial turn goes

Instrumented in-process run of `"Hi"` (warm model):

| Model call | Prompt (system + user) | Duration |
|---|---|---|
| 1 — `semantic_interpretation` | 1,856 + 2 = **1,858 chars** | 2.84–2.89 s |
| 2 — `reasoning` | 18,561 + 9,947 = **28,508 chars** | 7.07–7.18 s |
| 3 — `drafting` | 21,885 + 2,444 = **24,329 chars** | 1.75–3.22 s |
| **Total model** | **54,695 chars** | **11.8–13.1 s** |
| **URI overhead (non-model)** | | **2.9–3.2 s** |
| **Total turn** | | **14.7–16.3 s** |

Ollama's own server log reports the real tokenised size of calls 2 and 3 at **6,381–6,884 tokens each**.

The static content alone is `URI_AI_OPERATING_POLICY.md` (10,141 bytes) + `soul.md` (6,259 bytes) = **16.4 KB re-read from disk and re-sent on every reasoning call and again on every drafting call**, with no caching at any level (`model_reasoning_gateway.py:62-95`).

### 4.3 Separating the three latency sources

| Source | Per trivial turn | Notes |
|---|---|---|
| **Model/provider latency** | ~12 s | but only ~0.3 s of it is *necessary* — see §5 |
| **URI-added latency (non-model)** | ~3 s | disk reads, store scans, JSON assembly, synchronous writes |
| **UI/streaming latency** | ~0.1 s transport, **but +100 % perceived** | no streaming; the user sees a spinner for the entire turn |

**Where the URI overhead is *not*.** A static reading of `model_router.py:121-278` and `config/model_roles.py` suggests the per-call disk work should be expensive: `load_model_roles()` re-reads `model_roles.json` three or more times per `attempt()`, and `ProviderConfigStore`, `UsageCeilingStore` and `UsageMeter` are each constructed and read fresh per candidate. **Measurement contradicts that hypothesis** and it is recorded here as a correction rather than repeated as fact:

| Instrumented stage | Calls | Total time |
|---|---|---|
| `load_policy` (disk) | 3 | **0.001 s** |
| `load_soul` (disk) | 1 | **~0.000 s** |
| `build_query_context` | 2 | **0.003 s** |
| `personalization_context` (all memory rows) | 1 | **~0.000 s** |
| `record_conversation_turn` (write) | 1 | 0.001 s |
| `persist_session` (write) | 1 | 0.001 s |
| `serving_model_for_turn` (usage log) | 1 | 0.023 s |
| `ModelRouter.attempt` total | 3 | 35.50 s — of which **35.49 s is the HTTP POST itself** |

The OS file cache makes all of this effectively free. The router adds essentially nothing around the HTTP call. The remaining **~3 s** sits in legacy-orchestrator code that none of these wrappers covered — the deterministic planning and bookkeeping between the model calls (`SkillMemory.find_matching_skill`, `CapabilityPlanner`, `WorkflowPlanner`, `_pending_interaction`, dispatch and evidence assembly). §4.4 localises it further.

This matters for the plan: **prompt-size and call-count reduction are the levers, not I/O caching.** A "cache the config reads" optimisation would buy nothing measurable.

### 4.4 Model-call count per turn (instrumented)

| Test | Model calls | Model time | Non-model time | Total prompt volume sent |
|---|---|---|---|---|
| T1 "Hi" | **3** | 35.50 s | 2.96 s | **56,139 chars** |
| T2 knowledge question | **4** | 62.96 s | 4.32 s | **99,915 chars** |
| T3 read-only tool request | **3** | 26.02 s | 4.15 s | **64,900 chars** |
| T4 two-part tool request | **4** | 47.36 s | 8.15 s | **85,073 chars** |
| T5 approval-required action | **4** | 48.13 s | 8.96 s | **84,365 chars** |
| T6 unreachable URL | **4** | 44.74 s | 6.98 s | **85,784 chars** |

Note that the two turns which **failed** (T2, T3) sent 99,915 and 64,900 prompt characters respectively before reporting that URI has no capability for the task. Note also that non-model overhead roughly **triples** (2.9 s → 7–9 s) as soon as a capability dispatch is attempted.

T4 is the clearest single illustration in this report. Its four calls were:

| Call | Prompt | Duration |
|---|---|---|
| `semantic_interpretation` | 1,908 chars | 6.01 s |
| `reasoning` | 28,534 chars | 16.82 s |
| `reasoning` again, inside `_continue_brain_evaluation_loop` | 29,949 chars | 21.52 s |
| `drafting` | 24,682 chars | 3.01 s |
| **total** | **85,073 chars (~21,000 tokens)** | **47.36 s + 8.15 s overhead** |

…to run one email search that returned nothing, while silently dropping the "list my pending tasks" half of the request.

The same two-part request, given to the same model as native tool calls (§7.2), produced **both** correct tool calls with correct arguments in **0.74 s**, and synthesised both results in a further **1.36 s** — about **2.1 s** of model time against **~640 prompt tokens**.

*(Absolute wall times in this instrumented battery are inflated relative to §4.1 because the model had just been evicted by the second model used in §7.2 and was reloaded cold. The **call counts**, **prompt sizes** and **non-model time** are the meaningful figures here; §4.1's HTTP numbers are the authoritative user-experience latencies.)*

The fourth call in T2 is the `_continue_brain_evaluation_loop` round (`orchestrator.py:3038`, capped at `max_brain_iterations=3`, `:119`). A turn that engages that loop fully can therefore reach **six or more** sequential model calls.

### 4.5 URI is at the edge of its own context window

`DEFAULT_CONTEXT_TOKENS = 8192` (`model_providers/base.py:94`), passed explicitly as `num_ctx` (`ollama_provider.py:86`). During the instrumented battery URI logged its own guard **twice**:

```
Prompt to http://localhost:11434/gemma4:12b is ~8694 tokens (rough estimate),
exceeding the configured context_tokens (8192). Ollama will silently drop the
earliest content (typically the system prompt) to fit - the model may not see
the full request.
```

(`ollama_provider.py:93-105`; the estimate is a deliberate `len(text)//4` proxy, `context_budget.py:19-25`.)

Measured against Ollama's real tokeniser, the largest prompt actually observed in these runs was **7,060 tokens** against `n_ctx_slot = 8192`, with up to **800** further tokens budgeted for the reply — so real truncation is **not** confirmed to have occurred in these particular runs, but the margin is thin and URI's own guard is already tripping on longer turns.

Two things follow:

1. **This is a safety-relevant failure mode, not only a performance one.** The content Ollama drops first is the *earliest* content — which is `URI_AI_OPERATING_POLICY.md` and `soul.md`, i.e. the operating policy and identity. A prompt that overflows silently degrades exactly the part that constrains behaviour.
2. **The 8,192 limit is self-imposed and 32× smaller than the model's real capability.** `gemma4:12b` reports `context_length: 262144` via Ollama's own `/api/tags`. The same class of bug was found and fixed once already in M21 (the comment at `ollama_provider.py:80-86` records a 4,096-token default silently discarding most of every Brain prompt); the prompt has since grown into the new ceiling.

Reducing prompt size (§9) fixes the latency and this correctness risk with one change.

---

## 5. The model is not the bottleneck

Direct Ollama benchmark, same model, same options URI uses:

| Case | Prompt tokens | Prefill | Decode | Total |
|---|---|---|---|---|
| Tiny prompt, short answer | 30 | 0.07 s | 0.18 s (10 tok) | **0.27 s** |
| Tiny prompt, **streamed** | 30 | 0.07 s | 0.18 s | **0.26 s — first token at 0.074 s** |
| URI-sized semantic prompt | 339 | 0.37 s | 0.18 s | 0.58 s |
| URI-sized reasoning prompt | 2,051 | 1.47 s | 4.85 s (226 tok) | 6.41 s |
| URI-sized drafting prompt | 3,734 | 2.65 s | 4.33 s (205 tok) | 7.81 s |

`gemma4:12b` answers "Hi" in **0.27 seconds**, with the **first token at 74 milliseconds**. URI turns the same question, to the same model, on the same machine, into ~14 seconds — a **~50× penalty** that is entirely self-inflicted: prompt size (prefill) plus the number of sequential calls plus verbose structured output (decode).

Cold model load costs 15.8 s, but `keep_alive: "60m"` is already set (`ollama_provider.py:67`), so this is correctly a first-turn-only cost.

---

## 6. Streaming: absent end to end

- Ollama adapter sends `"stream": False` (`ollama_provider.py:57`); the OpenAI-compatible adapter sends no `stream` field at all (`openai_compatible_provider.py:76-83`).
- `server.py` contains no `StreamingResponse`, no SSE, no WebSocket. `/ask` is a synchronous `def` returning a complete `dict`.
- The Flutter client does a single blocking `POST /ask` with a **120 s** timeout (`http_uri_client.dart:393-416`), whose own comment acknowledges the backend runs "a multi-step reasoning chain against a local LLM".
- The UI's only affordance during the wait is a `CircularProgressIndicator` on the send button (`ask_uri_screen.dart:437`, `:514`). There is no partial text, no staged progress.

**Therefore time-to-first-UI-token is identical to total latency in every test above.** This is the single largest *perceived* latency lever: the model can produce a first token in 74 ms, and the user currently waits 14–35 s to see anything at all.

---

## 7. Tool-calling architecture

### 7.1 What exists today

- `ModelProvider.complete()` (`model_providers/base.py:189-197`) takes `system`, `user`, `temperature`, `max_tokens`. **There is no `tools` parameter in the interface**, and none of the three adapters (`ollama_provider.py:42`, `anthropic_provider.py:40`, `openai_compatible_provider.py:68`) accept or forward tool schemas.
- `ModelResponse` (`base.py:54-74`) has no field capable of carrying a tool call.
- The recent "Native tool pilots" commit (`fb02c92`) is a **naming collision** — per `docs/plans/URI_NATIVE_TOOL_AUDIT.md` it means "a real implementation rather than a placeholder stub" (e.g. real PDF→DOCX conversion), not provider function calling.
- Multi-action execution is strictly sequential and halts on first failure: `MultiActionExecutor.execute_chain` (`capabilities/executor.py:71-89`) loops `for index, step in enumerate(steps)` and returns `{"status": "halted", "halted_at": ..., "steps": completed}` on the first non-success. Successful earlier branches **are** preserved; remaining independent branches are never attempted.
- There is no concurrency anywhere in the request path — no `asyncio.gather`, no thread pool. The only `async def`s in `server.py` are the lifespan hook and an unrelated upload endpoint.

### 7.2 What the models can already do — measured

Both installed local models advertise `tools` capability via Ollama, and both delivered it. URI-shaped schemas for four real capabilities were supplied; results:

| Case | `gemma4:12b` (the User's Brain) | `qwen3.5:9b` |
|---|---|---|
| "Hi" — tools available but unnecessary | **no tool call**, direct answer, **0.42 s** | no tool call, 14.30 s (incl. load) |
| Single tool | `gmail_search{query: "invoice"}` — **0.52 s** | `gmail_search`, 5.07 s |
| **Two tools in one turn** | `gmail_search{query: "is:unread invoice"}` **+** `list_tasks{}` — **0.74 s** | both, 6.79 s |
| Continue from tool results | correct synthesis of both results, **1.36 s** | correct synthesis, 4.62 s |
| Side-effecting action | `send_email{to, subject, body}` structured — **0.94 s** | `send_email`, 10.45 s |

Every capability the tiered proposal depends on is therefore **already available and already fast**:

1. the Brain can decline to use tools for conversation (Tier 0);
2. it selects the right tool and **extracts proper arguments** (contrast T4, where URI passed the whole sentence);
3. it issues **multiple tool calls in a single response** — the basis for parallel execution;
4. it continues coherently from tool results;
5. it proposes side-effecting actions in a structured form that URI's existing `ApprovalGate` can intercept before anything happens.

A full Tier-1 round trip on `gemma4:12b` — decide, call two tools, synthesise the answer — measured **~2.1 s** of model time, against the **31.13 s** URI currently spends on the equivalent request (T4) while dropping half of it.

---

## 8. The safety machinery (and why it is not the problem)

Every gate on the path is **deterministic** — none requires a model call:

| Gate | Location | Needs a model? | Needed for trivial chat? |
|---|---|---|---|
| Auth / session resolution | `server.py:487-515` | no | yes |
| Content-length precheck, rate limits | `app/edge.py:100-150` | no | yes |
| Capability grants (`CapabilityResolver.is_allowed`) | `approval_gate.py:120-136` | no | no — only before execution |
| Approval requirement | `approval_gate.py:138-144` | no | no — only before a side effect |
| Availability / connection state | `decision_gates.py:170` | no | no |
| Audit trail record | `approval_gate.py` (`_record_audit_safely`) | no | yes (cheap) |

Only **2 of 17** registered tools require approval — `gmail_create_draft` and `drive_upload`, both `risk: high`. The other 15 are `approval_requirement: none`.

This is the key enabler for the recommendation: **because gating happens at the dispatch boundary and is independent of how a tool was chosen, the selection mechanism can change without weakening a single gate.**

### 8.1 Out-of-lane finding: Gmail access is not user-scoped

This was not what the investigation was looking for, and it is reported here because it was found rather than because it belongs to the latency question.

Canonical test T3 ("search my email for messages about invoices") was run under a **throwaway probe account created minutes earlier**, which had never connected a Google account. It returned **the real operator's live email content** — a genuine thread with real correspondent names, subjects and dates. The dispatch was recorded as `{"status": "success", "capability": "Gmail", "action": "search_messages"}`.

The cause is that Google credentials are resolved from a single process-global location, not per user: `_repo_root()` returns the repository root (or `URI_GOOGLE_CREDENTIALS_DIR`), and `credentials.json` / `token.json` are read from there (`connection_status.py:40-50`, `:119-141`). Both files exist at the repository root of this install. Nothing in that path consults `user_id`, and the per-user directory (`uri_workspace/users/<uid>/`) contains no Google credential material at all.

**Consequences.** Any authenticated account on this install can read the mailbox that whoever ran the OAuth flow authorised. `uri_workspace/users/` currently holds **390** account directories. Per-user isolation is an explicit architectural commitment of this repository, and the frozen blueprint's Batch A/C criteria assume it; this path does not honour it.

**Mitigating context, stated honestly:** this is a single-operator desktop deployment, so there is presently one human behind those accounts, and the capability itself still passed through its normal grants/approval gates — the gates worked, they simply gated access to a credential that was never user-scoped in the first place. That makes this a **latent** isolation defect rather than an active breach, but it is a real one and it is trivially reachable, as demonstrated.

> **Correction added 2026-09-17, after this section was first written** (recorded rather than overwritten, per this repository's auditable-correction convention).
>
> Calling this simply a "defect" was **incomplete**. Follow-up source verification for the implementation plan found that the shared, install-wide model is **explicit, documented and User-directed**:
> - `server.py:2379-2384` — *"Atomically configure the **install-wide** Google OAuth client secret. Open to any authenticated user (**User directive, 2026-09-12**)… any signed-in user can now replace it for everyone on this install."*
> - `server.py:2702-2706` — *"This remains an install-host-scoped action, not a per-user one."*
> - `server.py:2785-2789` — *"any signed-in user can now disconnect Gmail/Drive for every user on this install."*
>
> So the **sharing was decided deliberately**, and reversing it is an architecture change to the security/authority model — not a bug fix an implementer should make unilaterally. What this investigation adds is the demonstrated *consequence*: a brand-new account inherits full mailbox read access with no consent step of its own. That consequence is worth an explicit User decision now that it has been shown working, but it is a **decision**, not an unambiguous defect. See `M32_EXECUTION_ARCHITECTURE_PLAN.md` §3 A1 for the three options and their verified costs.

**This report does not reproduce any of the returned email content**, and no further mailbox queries were run after the behaviour was identified. Recommended: treat as its own security item, separate from and ahead of the latency work; it should not be folded into the tiering milestones.

---

## 9. Recommended target architecture

The recommendation is the tiering the User proposed, and the evidence supports it directly.

### Tier 0 — conversation: User → Brain → streamed response

One streamed model call. System prompt = compact identity + a **list of capability names**, not the full policy + soul + catalogue + audit + evidence bundle. No semantic interpretation call, no planner, no separate drafting call.

Projected: **first token ~0.1–0.3 s, complete in 1–3 s** (from §5's measured floor), against 14 s today.

### Tier 1 — native tool calls with deterministic guards

The same single streamed call, now carrying `tools=[…]` built from the existing capability registry (17 schemas). When the Brain returns tool calls:

1. validate each tool name against the registry — unknown names return an error result to the Brain rather than failing the turn;
2. run the **existing** guards per call, unchanged: grants → availability → schema validation → `ApprovalGate`;
3. execute **independent** calls concurrently;
4. return all results — including failures — to the Brain as tool results, and let it continue, streamed.

Projected: **2–4 s** for a read-only tool, **~3–5 s** for a parallel multi-tool turn, versus 19–31 s today.

### Tier 2 — structured planner / workflow / recovery, on demand only

Entered only when genuinely required: a durable multi-step workflow, a turn paused on approval that must resume later, or recovery of a persisted interrupted workflow. Keeps `WorkflowExecutor`, session workflow state and the evidence ledger.

### What stays mandatory in every tier

- authentication, session resolution, per-user state isolation;
- edge protections (content-length, rate limits);
- capability grants and the approval requirement, enforced at dispatch;
- audit trail records;
- **Brain-authored user-visible words** — URI must never compose the reply itself. Tiers 0 and 1 *strengthen* this: the user reads the Brain's own streamed tokens, not a URI-assembled envelope;
- honest failure reporting — never fabricate success.

### What becomes fallback / recovery only

| Component | New role |
|---|---|
| `ProviderSemanticInterpreter` (model call 1) | removed from the hot path; the Brain's own tool choice replaces it |
| Separate `drafting` call (model call 3) | removed; the same streamed call produces the words |
| `WorkflowPlanner` keyword templates | Tier 2 only, and the keyword matching should be retired outright |
| Decision Contract JSON (`propose_decision`) | fallback for models **without** tool support |
| Legacy `process_user_input` | explicit rollback lever, not the default |
| `_continue_brain_evaluation_loop` | replaced by the native tool-result continuation loop, with the same iteration cap |

### The canonical-vs-legacy question must be decided, not inherited

`M32_CANDIDATE_BLUEPRINT.md` P2 plans to enable the canonical path and states *"nobody currently knows what flipping this flag does to live behavior."* §10 of this report answers that empirically. But note that Tier 0/1 makes much of the Decision Contract redundant — so enabling canonical and adopting native tools are **competing** directions, and shipping both would build a third path beside two existing ones. This needs an explicit User decision before any implementation milestone.

---

## 10. Canonical path — empirical answer to P2's open question

`M32_CANDIDATE_BLUEPRINT.md` §4 states: *"nobody currently knows what flipping this flag does to live behavior. That is precisely why P2 is a milestone rather than a line item."* This investigation flipped it and measured. Same account, same model, same machine, same inputs; only `URI_ENABLE_DECISION_ENGINE_LIVE=1` differs.

| Test | Legacy (shipped) | Canonical (flag on) |
|---|---|---|
| T1 "Hi" | 3 calls, 56,139 chars, `success` | **2 calls**, **41,450 chars**, `success` (`conversation`) |
| T2 knowledge question | 4 calls, 99,915 chars, **`failed`** — "no implemented capability" | **2 calls**, **41,144 chars**, **`success`, correct answer** |
| T3 read-only tool request | 3 calls, 64,900 chars, **`failed`** — "no implemented capability" | **2 calls**, 62,328 chars, **`success`** — `Gmail / search_messages` actually executed |
| T4 two-part tool request | 4 calls, 85,073 chars, `not_found` | **2 calls**, 58,684 chars, `success` — but still **one** capability; the "list my pending tasks" half is still dropped |

Canonical used **exactly 2 model calls on every turn**, against legacy's 3–4, and never once fell back to legacy (`fallback_used: false` throughout). Non-model overhead also drops on conversation turns, from ~3.0 s to **1.0–1.4 s** — which incidentally localises §4.3's unattributed overhead: roughly 2 s of every legacy turn is its semantic-interpretation/skill-memory/workflow-planner machinery, which canonical simply does not run.

Canonical's own telemetry for T1 records `canonical_mode: "conversation"`, `gate_outcome: "READY"`, `canonical_execution_attempted: false`, `fallback_used: false` — i.e. it recognised a greeting as **conversation** and correctly declined to force it through capability selection. Legacy has no such mode; that is precisely why T2 fails there.

T2's canonical answer was verified as substantive, not a fabricated success: *"In Python, a list is mutable… while a tuple is immutable and cannot be modified once defined…"*

**Four conclusions:**

1. **Flipping the flag is a correctness fix, not merely a refactor.** It converts two hard failures (T2, T3) into successes — including actually executing the Gmail capability that legacy claimed did not exist — and removes one to two model calls per turn.
2. **It is not, by itself, the latency fix.** Canonical still costs ~14–17 s for a trivial turn, because it still sends a ~17 KB decision-contract prompt and still makes a **separate** ~24 KB drafting call. It cuts prompt volume ~26 % and call count by one; it does not approach the 0.27 s floor.
3. **It does not fix decomposition.** T4's second request half is dropped under canonical exactly as under legacy — `canonical_mode: single_action`. Only native tool calling produced both calls (§7.2).
4. **Canonical is the right foundation for the tiering.** It already has the `conversation` mode Tier 0 needs, and deterministic `evaluate_gates` at precisely the boundary Tier 1 needs. Tier 0/1 should be built **on** canonical rather than beside it — which resolves §9's "competing directions" concern: enable canonical first, then replace its JSON decision contract with native tool calls while keeping its gates untouched.

**Also note:** the telemetry file grew by exactly one line per canonical turn during this run, having grown by **zero** lines across the 9 flag-off turns in §4.1. That is the positive control confirming §3.1's negative finding.

---

## 11. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Small local models may choose tools unreliably on harder inputs than the 5 probed here | Build a tool-selection eval battery before cutover; keep the Decision Contract as fallback |
| R2 | Provider tool formats differ (Ollama / Anthropic / OpenAI) | Normalise into `ModelResponse.tool_calls`; one adapter change per provider |
| R3 | Streaming interacts badly with approval pauses | Approval emits a terminal stream event; the turn resumes as a new streamed continuation |
| R4 | Parallel execution could break per-user isolation or audit ordering | Only independent, read-only calls run concurrently; anything approval-gated or side-effecting stays serial |
| R5 | Losing the deterministic capability-selection audit trail | Tool calls are recorded exactly as capability dispatches are today |
| R6 | Three code paths (legacy, canonical, tiered) | Force the §9 decision before implementation; delete or demote one |
| R7 | Trimming policy/soul from prompts could change behaviour or safety posture | Trim by measurement: A/B the same battery with and without, and keep whatever demonstrably changes refusals/honesty |
| R8 | `orchestrator.py` must never grow (standing rule) | All new work lands in new modules; the tiering should **shrink** it |

---

## 12. Proposed implementation plan (not authorised — for review)

Each phase is independently shippable, independently reversible, and ends in a measured re-run of the same battery.

| Phase | Work | Expected effect on "Hi" |
|---|---|---|
| **P0** | Commit the latency battery as a repeatable harness; record this report's numbers as the baseline | measurement only |
| **P0.5 — enable canonical** | The frozen blueprint's existing P2, now de-risked by §10: supply `URI_ENABLE_DECISION_ENGINE_LIVE` as a real default, run the full live battery, record the M30.8 correction | 3–4 calls → **2 calls**; **fixes T2 and T3 outright** |
| **P1 — prompt reduction, no architecture change** | Cut what goes **into** the two large prompts: send capability *names* rather than the full catalogue, trim `policy.md`/`soul.md` to what actually constrains behaviour, drop redundant query-context blocks, and cap structured-output verbosity. Also raise `DEFAULT_CONTEXT_TOKENS` off 8192 (§4.5). **Explicitly not** an I/O-caching exercise — §4.3 shows I/O is ~1 ms | 14 s → **~8–10 s**, and removes the silent-truncation risk |
| **P2 — streaming transport** | `stream=True` in the provider adapters; an SSE `/ask` variant; Flutter client consumes it | first token **14 s → <1 s** |
| **P3 — Tier 0** | A direct conversational path: one streamed call, compact prompt, no interpretation/planner/drafting calls | "Hi" → **1–3 s** |
| **P4 — Tier 1** | `tools=` in the provider interface, `ModelResponse.tool_calls`, a guard that runs the existing gates per call, concurrent independent calls, tool-result continuation | tool turns **19–31 s → 2–5 s** |
| **P5 — Tier 2 demotion** | Planner/workflow/recovery become on-demand; retire keyword routing; resolve the canonical/legacy decision | correctness fix for T2/T3 |

**Sequencing note:** P0.5, P1 and P2 are pure wins with no architectural commitment — P0.5 in particular is already an approved milestone in the frozen blueprint, and §10 has now removed its "known unknown". P3–P5 require the User's architectural decision first.

**Separately and ahead of all of it:** the Gmail credential-scoping defect (§8.1) is a security item, not a latency item, and should not be sequenced behind this plan.

---

## 13. Disclosed unverified items

1. **Corrected mid-investigation:** this item originally read "the probe account has no Gmail credentials, so T3/T4/T5 exercised routing and gating but not real third-party execution." That was **wrong**, and the correction is §8.1: the probe account *did* reach real Gmail, because credentials are process-global rather than user-scoped. The correction is recorded rather than silently replaced, per this repository's convention. The latency findings are unaffected either way; the original caveat on T3's legacy failure still holds (it failed at routing, before any credential was consulted).
2. **`qwen3.5:9b` timings include a model load** (it was swapped in after `gemma4:12b`), so its absolute numbers overstate steady-state latency. Its tool-calling *correctness* results are unaffected.
3. **Projected post-change latencies in §9 and §12 are derived** from the measured model floor (§5) and the measured tool round trip (§7.2). They are arithmetic from real measurements, not measurements of a built system.
4. **Cloud providers were not exercised.** Anthropic/OpenAI-compatible paths were read statically only; no key was configured for the probe account. `URI_PROVIDER_KEY_SECRET` is also unset in this deployment (an independent finding, F4, already recorded in `M32_CANDIDATE_BLUEPRINT.md`).
5. **Operational note, disclosed for completeness:** during this investigation the User's already-running backend was terminated by a console Ctrl-C originating from this session's own piped command teardown (`uri_server.log` ends with `^C` immediately after a probe request). No data was lost; the backend was restarted, and all subsequent measurement used a detached instance. Later probe runs stopped and restarted the backend deliberately to avoid contention.
6. **The stall observed in the first in-process run** (a turn blocked >4 minutes with no model activity, while a second server process held the same user's state) was not root-caused before the approach changed to a throwaway account and a stopped server. It did not recur. If two URI processes are ever run against one user's state in production, this deserves its own investigation.
7. **Environment changes made during this investigation, all reversed:** the backend was stopped and restarted (it is running again, healthy, on port 8000 as found); Ollama was started (it was not running at the outset — note that this means the User's own app could not have reached a Brain at all before that point); and a throwaway account `m32probe_f5664e40` (`056ef9fc-…`) was created, with its own `uri_workspace/users/<uid>/` directory and probe sessions. That account was **left in place rather than deleted**, because removing user data is a higher-risk action than leaving an inert test account; it can be deleted on request.
8. **Canonical-mode measurements were taken in-process, not over HTTP.** They exercise the same `server.ask()` entry point with the same account and model, but do not include FastAPI serialisation. Comparisons in §10 are therefore legacy-in-process vs canonical-in-process (like for like); §4.1's HTTP figures remain the authoritative user-experience numbers for the shipped path.
9. **Absolute wall-clock times vary by up to ~2× between batteries** depending on whether the model was resident, had just been evicted by the other local model, or was cold. Call counts, prompt volumes and relative comparisons are stable and are what the conclusions rest on.

---

## 13a. Reproduction artifacts

All measurements in this report are reproducible from the session scratchpad (deliberately **not** committed — P0 in §12 proposes promoting them to a permanent battery):

| Artifact | Produces |
|---|---|
| `m32_http.py` | §4.1 — end-to-end HTTP matrix against a live backend, using a throwaway account set to `ollama`/`gemma4:12b` |
| `m32_probe2.py legacy` / `canonical` | §4.4, §10 — instrumented in-process runs with per-call prompt sizes, stage timings and exact model-call counts |
| `m32_ollama_bench.py` | §5 — direct provider benchmark, prefill/decode split, streamed TTFT |
| `m32_tools_probe.py` | §7.2 — native tool-calling probe across both installed local models |
| `m32_probe3.py` | §4.3 — non-model overhead localisation |

Supporting runtime evidence read directly, not inferred: `uri_workspace/canonical_execution_log.jsonl` (§3.1), `uri_workspace/logs/uri_server.log`, Ollama's own server log (real tokenised prompt sizes, `n_ctx_slot`, KV-cache checkpoint churn), and `uri_workspace/capabilities_registry.json` (risk/approval per tool, §8).

---

## 14. Conclusion

URI's latency is not a model problem, a hardware problem, or a provider problem. The Brain on this machine answers "Hi" in **0.27 seconds** and completes a two-tool round trip in about **2 seconds**. URI takes **14 seconds** for the former and **31 seconds** for the latter — while dropping half the request — because every message, regardless of triviality, is routed through three sequential blocking model calls carrying ~55,000 characters of prompt, a keyword-matching planner with two templates, and a separate drafting call, with no streaming at any layer and no concurrency anywhere.

The safety architecture that must be preserved — authentication, grants, approval, audit, honest failure — is deterministic, cheap, correct under test, and **entirely independent of the tool-selection mechanism**. That is what makes the proposed tiering safe to pursue: the gates do not need to move.

Two things are already built and simply not switched on. The canonical decision path — disabled by an unset environment variable — uses two model calls instead of three or four, treats a greeting as conversation, and correctly answers and routes the two requests the shipped path fails outright (§10). And the Brain itself already does native tool calling, in parallel, with correct arguments, at a fraction of the cost (§7.2).

**Recommended next steps, in order:**

1. **Treat §8.1 (Gmail credentials are not user-scoped) as a separate security item**, ahead of and independent of this plan.
2. **Enable the canonical path** (P0.5 — the frozen blueprint's own P2, whose "known unknown" §10 has now answered): two fewer failures, one fewer model call, no new architecture.
3. **Decide §9's question** — tiering built *on* canonical, replacing its JSON decision contract with native tool calls while keeping its gates — after which P1 (prompt reduction) and P2 (streaming) proceed as unconditional wins.

Nothing in this report has been implemented. No production code was modified, and nothing was committed or pushed.
