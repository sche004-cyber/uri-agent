# M32 — Execution Architecture: Tiered Brain Path (Implementation Plan)

**Date drafted:** 2026-09-17. **Status:** ACCEPTED (User accepted 2026-09-17) — **the architecture itself**; see the 2026-09-18 correction below for what this does and does not mean about implementation readiness.
**Author:** Claude (planning role). Implementation by Antigravity.
**Evidence base:** `docs/plans/M32_LATENCY_DIAGNOSTIC_REPORT.md` (measured, User-accepted 2026-09-17).

---

## Correction — Sonnet architecture review, A2 repair, and status reconciliation (added 2026-09-18)

**This correction is recorded per this repository's auditable-correction-history convention: preserved alongside, not in place of, §14's original BLOCKED recommendation below.**

**1. ACCEPTED vs. BLOCKED reconciled.** The header's `ACCEPTED` and §14's `BLOCKED` were never actually contradictory, but the plan left that ambiguous. `ACCEPTED` (header) means the User approved the *target architecture* — the Tier 0/1/2 design and batch ordering in §1–§11. `BLOCKED` (§14) means Claude's own pre-audit found that *starting implementation* was not yet safe, pending PC1/A1/C3.4/§0 — an implementation-readiness gate on an already-accepted design, not a rejection of the design. Both statements were true simultaneously and remain true in their original scope; this note exists only because the plan did not say so explicitly.

**2. Sonnet (Claude, this session) ran the requested M32 architecture review** of Batch A2 (context safety), the canonical cutover, Tier 0/1/2 design, safety boundaries, and architectural assumptions, per the User's review brief. **Verdict: PASS WITH CHANGES.** Full findings are in the review transcript; the one CRITICAL finding is repaired below.

**3. CRITICAL finding, repaired same session:** the context-trimming mechanism built for A2.3 (`context_trimmer.trim_reasoning_request`) never ran on the real production path. `OllamaReasoningAdapter.__call__` gated its trim call on `self._explicit_provider is not None` (`model_reasoning_adapter.py`, pre-repair) — the *test* branch — while every production construction site (`server.py:164`, `:433`, `:1329`) constructs the adapter with no injected provider, so production hit only `OllamaProvider.complete()`'s raw hard refusal, with zero trim attempt first. The drafting call (`response_drafting.draft_response`) had no trimming coverage on either path. Both are fixed: `model_reasoning_adapter.py` now resolves the router's actual candidate (`ModelRouter.resolve()`) and trims before send regardless of path; `response_drafting.py` gained the equivalent budget-fitting for its own (differently-shaped) payload, protecting `user_request`/`outcome`/`personalization` unconditionally. A negative-control test run (temporarily reintroducing the old gating) confirmed the new tests fail against the pre-repair code and pass against the repair — see `test_m32_a2_production_wiring_repair.py`. Currently inert in this deployment (gemma4:12b resolves to 262,144 tokens via A2.1/A2.2), exactly like the A1 Gmail-scoping finding was inert before its fix — latent, not active, but real.

**4. PC1 restated accurately.** The working tree is **still dirty**: 24 modified files + 18 untracked entries as of this correction (`git status --short`), including this plan and the diagnostic report themselves, which have never been committed. Batch A (A1 Gmail credential scoping via A1-3, and A2 context safety) implementation has in fact proceeded substantially ahead of PC1 formally clearing — that is a real deviation from this plan's own stated gate, recorded here rather than silently resolved. It does not block this repair (a bounded fix to code already in the working tree), but PC1 remains open and should be closed — by committing this batch of work — before Batch B begins.

**5. Batch B (canonical enablement) has NOT started.** `canonical_execution.py` is untouched; `URI_ENABLE_DECISION_ENGINE_LIVE` and `URI_ENABLE_WORKFLOW_CONTINUATION_MODE` remain unset. Batch C's P1 prerequisite (`multi_action_dispatch._action_permitted`) is also untouched, so C3.3/C3.4 remain correctly blocked. The EffectType classification (C3.4's own prerequisite) landed correctly ahead of schedule — 17/17 tools classified, JSON-registry-first with a fail-safe `LOCAL_WRITE` default for unknowns — verified against `uri_workspace/capabilities_registry.json`.

---

## 0. Identifier collision — RESOLVED (2026-09-17)

The roadmap milestone sequence was authoritatively decided by the User:
- **M32** — Brain Latency & Core Execution Architecture (this document)
- **M33** — External Capability Bridge (blueprint moved to `docs/plans/M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md`)
- **M34** — Model-Native Capability Preservation & Adaptive Scaffolding

The collision is resolved. `M32` unambiguously refers to Execution Architecture.

---

## 1. Target architecture

**The invariant, stated once and binding on every batch:**

> **The model chooses the tool. URI authorises and executes it.**

Nothing in this plan may weaken grants, schema checks, authentication, approvals, audit, or dispatch controls. Selection changes; authorisation does not.

| Tier | Trigger | Path | Model calls |
|---|---|---|---|
| **Tier 0 — direct chat** | No tool needed | User → Brain → **streamed** response | **1**, streamed |
| **Tier 1 — native tool loop** | Brain emits tool call(s) | Brain → native tool call(s) → **URI deterministic gates** → execute → results → Brain → streamed answer | **2** (call + continuation), tools executed in parallel where independent |
| **Tier 2 — managed workflow/recovery** | Durable, failed, resumable, approval-heavy or genuinely multi-step | Existing planner / `WorkflowExecutor` / recovery / evidence ledger | as today |

Tier 2 is **escalation**, not the default. Today it is the default, which is the core defect.

### Why this is safe to attempt (measured, not assumed)

- Gates are deterministic and sit at the **dispatch boundary**, independent of how a tool was chosen (`approval_gate.py:120-144`, `decision_gates.py:170`). Only 2 of 17 tools require approval.
- The Brain already does native tool calling, including **multiple calls in one response** with correct argument extraction: 0.42–1.36 s per step measured on the operator's own `gemma4:12b`.
- The canonical path already has the `conversation` mode Tier 0 needs and the gate seam Tier 1 needs, and already answers correctly the two requests the shipped path fails.

### Before / after flow

**BEFORE — what ships today** (legacy, measured):

```
POST /ask (sync def, blocking)
  └─ personalization context (all memory rows)
  └─ new SemanticInterpreter + ReasoningAdapter per request
  └─ [canonical branch SKIPPED — flag unset]
  └─ orchestrator.process_user_input
       ├─ MODEL CALL 1  semantic_interpretation      1,858 chars
       ├─ SkillMemory / CapabilityPlanner / WorkflowPlanner   ← keyword routing, 2 templates
       ├─ MODEL CALL 2  reasoning                   28,508 chars   (policy+soul re-read, uncapped)
       ├─ dispatch → gates → execute        (only if a template matched)
       ├─ MODEL CALL 3+ brain evaluation loop        ≤3 more rounds
       └─ MODEL CALL n  drafting                    24,329 chars   (≤2 attempts)
  └─ one JSON dict returned          ⇒ user sees nothing for 14–35 s
```

**AFTER — target**:

```
POST /ask/stream (SSE)            [/ask retained until UI soaks]
  └─ canonical turn state + gates (deterministic, no model)
  └─ MODEL CALL 1 — streamed, compact prompt, tools=[17 schemas]
       │
       ├── no tool call  ─────────────────► TIER 0: stream tokens straight to UI
       │                                     first token ≤0.5 s
       │
       └── tool_call(s) ─► translate to Decision Contract
                            └─ evaluate_gates            ← UNCHANGED
                            └─ grants / approval / audit ← UNCHANGED
                            └─ execute (parallel iff read-only + approval-free)
                            └─ per-branch results (successes AND failures)
                                 └─ MODEL CALL 2 — streamed continuation  ⇒ TIER 1
                                     │
                                     └─ escalate only on durable/failed/
                                        resumable/approval-heavy  ⇒ TIER 2
```

Model calls per trivial turn: **3–4 → 1**. Per tool turn: **4+ → 2**. Prompt volume per trivial turn: **~56,000 chars → target ~2–3,000**.

### What this plan explicitly preserves

- **Brain-authored words.** URI must never compose, rewrite or template the user-visible reply. Tier 0/1 *strengthen* this: the user reads the Brain's own streamed tokens. The only permitted URI-authored text remains a deterministic fallback when the Brain's output is unavailable or fails validation, restating already-decided facts only.
- **The USER → BRAIN → URI loop.** URI supplies context, capability, evidence, execution and the authorisation boundary; the Brain reasons, chooses and re-evaluates. Tier 1's tool-result continuation **is** the re-evaluation step of that loop, not a bypass of it.
- **Honest failure.** No fabricated success, ever. The existing `prepare_output`-style honest failure remains; what changes is that far fewer requests reach it.

---

## 2. Preconditions (hard gates before any implementation begins)

| # | Precondition | Current state | Why it blocks |
|---|---|---|---|
| **PC1** | **Clean working tree** | ❌ **46 files modified (+3,116/−1,763), 31 untracked.** The entire Hybrid UI initiative plus backend edits to `server.py`, `model_router.py`, `model_roles.py`, `provider_registry.py`, `connection_status.py` are uncommitted | Batch A edits `connection_status.py`, which **already has uncommitted Live-UX-Repair changes** (token refresh semantics). Starting Batch A here risks losing or conflicting with in-flight work. The frozen blueprint sets the same precondition |
| **PC2** | Identifier collision resolved (§0) | ❌ open | State files and audit records need one unambiguous ID |
| **PC3** | Latency baseline committed as a repeatable battery | ❌ probe scripts live only in a session scratchpad | Every batch's exit criteria are latency-measured; without a committed battery the numbers are not reproducible by another worker |
| **PC4** | `orchestrator.py` no-growth rule acknowledged by the implementing worker | standing rule; file is **6,153 lines** and has already grown past its M21 baseline | All new behaviour must land in new modules. This plan is designed so orchestrator.py **shrinks or stays flat** |

**PC1 is the one that actually stops work.** Recommended resolution: land/commit the Hybrid UI batch work first (it is already User-live-tested), then start M32 from a clean tree.

---

## 3. Batch A — security and context

### A1 — Gmail credential scoping — **a User decision, not a bug fix**

**This is the most important correction in this plan.** The diagnostic report (§8.1) described install-wide Google access as a latent isolation *defect*. That framing was incomplete. Verified directly in source:

- `server.py:2379-2384` — *"Atomically configure the **install-wide** Google OAuth client secret. Open to any authenticated user (**User directive, 2026-09-12**)… any signed-in user can now replace it for everyone on this install."*
- `server.py:2702-2706` — *"opened this ADMIN-only; open to any authenticated user (User directive, 2026-09-12)… This remains an install-host-scoped action, not a per-user one."*
- `server.py:2785-2789` — *"any signed-in user can now disconnect Gmail/Drive for every user on this install."*

The shared-connection model is **deliberate, documented and User-directed**. Reversing it is an architecture change to the security/authority model, which this project's governance requires be put to the User explicitly rather than "fixed" by an implementer.

**What was demonstrated in the diagnostic is still true and still matters:** a throwaway account created minutes earlier read the operator's live mailbox with no consent step of its own. The *sharing* was decided; it is not evident that this *consequence* was, now that it has been shown working.

#### The decision (User must pick before A1 is implementable)

| Option | What it means | Cost |
|---|---|---|
| **A1-1 — Reaffirm install-wide, harden the edges** | Sharing stays. Re-restrict who may `authorize`/`disconnect`/replace `credentials.json` (the 2026-09-12 directive opened all three to any authenticated user), and surface "this connection is shared across all accounts on this install" in the UI so it is never a surprise | Small — endpoint guards + UI copy |
| **A1-2 — Full per-user credentials** | Every account holds its own token; no shared mailbox access | **Large** — see cost map below |
| **A1-3 — Split (recommended for discussion)** | `credentials.json` (the OAuth *client secret*, an app identity) stays install-wide; `token.json` (the actual *mailbox grant*) becomes per-user | Medium — token path + flow only |
| **A1-4 — Restrict by capability grant (added by review, finding SR-11)** | Leave credential storage entirely alone; instead restrict *who may invoke* Gmail/Drive capabilities at all, using the **already-built and already-enforced** `CapabilityResolver.is_allowed` + `CapabilityGrantsStore` (`approval_gate.py:108-136`, `capability_resolver.py:36-45`, `:213`). Grants are already per-user (`{user_id: [capability_ids]}`) | **Smallest** — no new store, no OAuth change, no signature churn |

**Note on A1-4:** it does not make credentials per-user — a granted account still reaches the shared mailbox. It closes the *demonstrated* hole (a brand-new account silently reading the operator's mail) at a fraction of the cost, and is compatible with doing A1-2/A1-3 later. It should be evaluated first precisely because it is cheap and reversible.

**Correction to this plan's own cost map (finding SR-12):** A1-2/A1-3 are somewhat *less* blocked than stated below — `GmailSearchTool` / `GmailCreateDraftTool` / `DriveUploadTool` already accept injectable `service=` / `gmail_service=` / `drive_service=` constructor parameters (currently used only by tests). If the dispatcher is taught to build and inject a user-scoped service the way it already injects `file_store`, the churn is smaller than the signature-by-signature map implies. This also largely closes the "open thread" flagged at the end of this section.

#### Cost map for A1-2 / A1-3 (verified, not estimated)

Every one of these currently takes **zero** `user_id` parameters and would need a signature change plus call-site updates:

| Module | Sites |
|---|---|
| `connection_status.py` | `_repo_root()` `:42-51`, `list_connection_status()` `:111-175` (takes no args at all) |
| `google_auth_common.py` | `_repo_root()` `:10-15`, `load_usable_credentials()` `:18-46` |
| `gmail_service.py` | `__init__` `:60-73`, `connect()` `:76-137` (**the only interactive site** — `InstalledAppFlow.run_local_server`, writes the token), `ensure_connected_from_token()` `:149-176` |
| `gmail_search_service.py` | `:27-51` |
| `drive_service.py` | `:20-44` |
| `linked_document_service.py` | `_get_drive_service()` `:273-291` |
| `dispatcher.py` | `execute_tool(tool_name, **kwargs)` `:65` — the dispatch layer carries **no identity into tool execution at all**; this is the structural blocker |

Edge-level changes are trivial by comparison: `GET /connections` (`server.py:2257`) takes no user param and needs one; `GET /gmail/unread-count` (`:1614-1624`) already resolves `user_id` and simply drops it.

**Three further design decisions A1-2/A1-3 force, each needing an explicit answer:**

1. **Token adoption.** 390 account directories exist, all riding on one shared `token.json`. Who adopts it — the operator's account, the ADMIN, nobody (everyone re-authorises)? No adoption code exists. `portable_paths.migrate_legacy_file_if_needed()` (`:67-91`) is the existing copy-once primitive and is the natural tool, but it is currently used only for profile/memory/growth-ledger at startup.
2. **The OAuth flow lock is process-global** (`server.py:2651-2652`). Per-user tokens require a per-user lock, or two users signing in concurrently collide.
3. **Encryption at rest.** `ProviderKeyStore` (`provider_keys.py:56-169`) encrypts per-user secrets with Fernet/PBKDF2 and refuses to run when `URI_PROVIDER_KEY_SECRET` is unset — **and that variable is unset in this deployment** (an independent finding already recorded as F4 in the frozen blueprint). An OAuth refresh token is equivalent-sensitivity material, but unlike an API key it must stay directly consumable by the Google client library. Decide explicitly whether tokens get the same treatment — and note that adopting `ProviderKeyStore`'s pattern inherits its unset-secret failure mode.

**Reusable pattern if the User picks A1-2/A1-3:** `user_scoped_path(user_id, filename)` (`portable_paths.py:47-64`, validates UUID shape) is the one helper every per-user store already builds on; `ProviderKeyStore`/`ProviderConfigStore` are the shape to copy; `test_m21_file_store_isolation.py` is the isolation-test template, and `server.py:2286-2299` already names it as the template for exactly this class of fix.

#### A1 tests (apply to whichever option is chosen)

| Test | Asserts |
|---|---|
| New: cross-account isolation (A1-2/A1-3) | Account B **cannot** read account A's mailbox — the exact scenario demonstrated in the diagnostic, as a permanent regression guard. `test_multi_user_isolation.py` currently has **zero** Google/Gmail/token coverage |
| New: shared-connection visibility (A1-1) | The shared nature is reported truthfully by `GET /connections`, not implied to be personal |
| New: concurrent authorise (A1-2/A1-3) | Two users authorising simultaneously do not collide on the flow lock |
| New: token adoption | The chosen adoption rule happens exactly once and never grants a second account access |
| **Update (breaking)** | `test_gmail_unread_count_endpoint.py:26` asserts `get_unread_count.assert_called_once_with()` (**no args**) — breaks the moment `user_id` is threaded |
| **Update** | `test_connection_status.py`, `test_gmail_connection_truth.py` (**already modified uncommitted — see PC1**), `test_gmail_search_service.py`, `test_gmail_search_tool.py`, `test_google_oauth_authorize_flow.py` |
| Note, not a test | `test_gmail.py` is **not automated** — no `def test_`, no assertions; it calls `GmailService().connect()` and would launch a real interactive OAuth flow if executed. Do not wire it into CI |

**Open thread this map did not close:** how `gmail_search` / `gmail_create_draft` / `drive_upload` tool instances are constructed inside the orchestrator — the trace stopped at `dispatcher.py:65`. A1-2/A1-3 cannot be scoped to the hour without closing it; it is the first task of A1 implementation, not something to assume.

### A2 — Model-aware context budget, with policy/identity never silently dropped

**Defect.** Three separate facts combine into one failure:

1. `DEFAULT_CONTEXT_TOKENS = 8192` (`model_providers/base.py:94`) was deliberately sized at M21 **for `qwen3:14b`'s measured prompts**, with `gemma4:12b` not yet in play. The comment at `base.py:81-93` says so. This is a stale default, not a considered limit for the current Brain.
2. **The real per-model window never reaches the live call.** Precedence is `uri_workspace/model_roles.json` → `OLLAMA_NUM_CTX` → `8192` (`model_roles.py:301-313`, `base.py:142-153`). `uri_workspace/model_roles.json` **does not exist** in this deployment and no role sets `context_tokens` (`model_roles.py:78-80`), so **8192 always wins**. The catalogue's real numbers (`provider_registry.py:96-208`) are read only by `GET /providers` for display (`server.py:3204`) and are never wired into `ModelProviderConfig`.
3. **The overflow guard is detection-only.** `ollama_provider.py:93-105` logs a warning and sends the prompt anyway. No trimming, no reordering, no protection of the leading content. `context_budget.fit_within_budget` / `bound_json_value` exist and work, but are **never invoked on `system_policy`, `soul`, or the assembled request** — only on per-item evidence (`orchestrator.py:2246`, 4,000 chars/item) and attempt history (`:2780`).

Net effect: policy (10,141 bytes) and identity (6,259 bytes) are read whole, uncapped, every call, and are the **first** content dropped when Ollama truncates.

**Also note:** `gemma4:12b`'s catalogue entry is `context_tokens=ConfidenceValue(value=None, confidence=UNAVAILABLE)` (`provider_registry.py:109-112`) even though Ollama's `/api/tags` reports `context_length: 262144` for it. The catalogue is wrong about the operator's actual Brain.

**Fortunately, the discovery plumbing is ~90 % built:** `ollama_provider._model_max_context()` (`:192-220`) already parses the real `context_length` from the **same `/api/tags` call `describe()` already makes** — it is simply discarded after being used to compose a warning string (`:280-289`).

#### A2 work items

| # | Change | Where |
|---|---|---|
| A2.1 | Feed the discovered real window into configuration: make `_model_max_context()`'s value available to `build_provider()` so `context_tokens` defaults to the **model's actual window** when no role config pins one. Explicit role config and `OLLAMA_NUM_CTX` keep winning | `ollama_provider.py:192-220`, `config/model_roles.py:301-313` |
| A2.2 | Populate the catalogue from live discovery rather than leaving `gemma4:12b` `UNAVAILABLE`, using the existing `ConfidenceValue` KNOWN/UNAVAILABLE semantics — a discovered value is KNOWN, a guess is not | `provider_registry.py:96-208` |
| A2.3 | **Build the trimming mechanism that does not exist**: a prompt-assembly budget that fits the request under the live `context_tokens`, with a fixed priority order — **policy, identity and tool rules are never trimmable**; evidence, attempt history, session context and conversation window are trimmed first, using the already-tested `fit_within_budget`/`bound_json_value` | new module (NOT `orchestrator.py`, per PC4), called from `model_reasoning_gateway.build_reasoning_request` |
| A2.4 | Cap the currently-uncapped `available_capabilities` catalogue in the prompt (`model_reasoning_gateway.py:275-313`) — it is a list with no bound today | `model_reasoning_gateway.py` |
| A2.5 | Escalate the overflow guard from **log-only** to **enforced**: if the assembled prompt still exceeds budget after trimming, that is a defect to surface honestly, not a warning to emit and then overflow anyway | `ollama_provider.py:93-105` |
| A2.6 | Reserve output headroom: budget must account for `max_tokens`/`num_predict` (up to 800 today) on top of the prompt, which the current check ignores | budget module |
| A2.7 | **Specify the small-window failure shape (finding SR-16).** A2.5 turns overflow from a warning into an enforced failure — but nothing says what happens when policy + identity + tool schemas **alone** exceed a small model's window, i.e. when there is nothing budgetable left to trim. This must have a designed answer (degrade to a reduced-capability mode? refuse with a specific, honest message naming the model?) and a test that pins an **artificially small** window. All measurement so far used `gemma4:12b`'s 262,144-token window, so this path is entirely unexercised | budget module + new test |

#### A2 tests

| Test | Asserts |
|---|---|
| New: model-aware default | With no role config and no `OLLAMA_NUM_CTX`, a provider built for a model whose real window is discoverable uses **that** window, not 8192 |
| New: policy/identity survive | Given an oversized assembled request, `system_policy` and identity are present **in full** in the transmitted payload, and only budgetable sections were reduced |
| New: output headroom | prompt budget + `num_predict` never exceeds the window |
| New: honest overflow | If trimming cannot fit the request, the failure is explicit, not a silent send |
| **Update (breaking)** | `test_ollama_provider.py::test_context_tokens_default_when_env_unset` asserts the literal 8192 default and **will fail by design** — it must be rewritten to assert the new model-aware rule, not deleted |
| Re-run unchanged | `test_m21_context_window.py`, `test_m21_context_window_live.py`, `test_m21_prompt_budget.py`, `test_m21_provider_config.py` — M21's guarantees must all still hold |

**M21 relationship, stated explicitly so it is not re-litigated:** M21 established "always send `num_ctx` explicitly" and built `context_budget.py`. It deliberately did **not** build model-aware discovery or whole-prompt trimming, and it never claimed 8192 would survive a model swap. A2 completes what M21 scoped out; it does not reverse an M21 decision.

---

## 4. Batch B — canonical path

### B1 — Enable and validate canonical execution

**Current state.** `server.py:1385-1415` calls `run_canonical_for_ask` only when `decision_engine_live_enabled()` is true, i.e. `os.environ.get("URI_ENABLE_DECISION_ENGINE_LIVE") == "1"` (`canonical_execution.py:85-86`). Nothing sets it. Measured consequence and the empirical result of turning it on are in the diagnostic report §10.

**What B1 must deliver:**

| # | Change | Note |
|---|---|---|
| B1.1 | Make canonical the **actual** default — a committed default in code or checked-in config, not an env var somebody must remember. The blueprint's own words: *"An env var that nothing sets is not a cutover."* | `server.py:1385-1415`, `canonical_execution.py:85-86` |
| B1.2 | **Fix the rollback lever** (see §10): `CANONICAL_EXECUTION_ALLOWLIST` is a source constant (`:76`) and `canonical_killswitch_enabled()` just tests it for non-`None` (`:99-105`). Make both runtime-settable so rollback does not require a redeploy | `canonical_execution.py` |
| B1.3 | Run the **live** battery against canonical — not the unit tests, which already pass against a path production does not use | `scripts/m32_latency_battery.py` |
| B1.4 | Record the **M30.8 correction**: M30.8 is recorded COMPLETE with "canonical cutover", and commit `0da36df` is titled "…through Canonical Cutover + Legacy Retirement", while the live deployment has been serving legacy the whole time. Preserve the history, record the correction | `docs/plans/` correction note |

| B1.5 | **Decide the second flag (finding SR-8).** `URI_ENABLE_WORKFLOW_CONTINUATION_MODE` is a **second unset flag** (`canonical_execution.py:64`, `decision_gates.py:42`, `server.py:1346`). With it unset, `decide_fallback_reason` returns `"mode_not_executable:workflow_continuation"` (`canonical_execution.py:262-263`) and **every resumed/paused multi-step turn falls back to legacy forever** — safely, but silently. "Canonical is the default" is therefore untrue for that whole traffic class until this flag is decided too | `canonical_execution.py`, `decision_gates.py:225-234` |
| B1.6 | **Close the narrative-failure path (finding SR-3, corrected).** After a successful canonical execution, `_draft_narrative_safely` runs inside a bare `try/except Exception: pass` (`canonical_execution.py:493-499`) and the envelope returns regardless — there is **no** legacy fallback once execution has happened. The draft's phrase "legacy remains reachable through the `_canonical_fallback` marker path" was **too broad** and is corrected here | `canonical_execution.py:488-506` |

**Known behaviour under canonical, measured, so it is not discovered as a surprise:**

- Greetings resolve as `canonical_mode: "conversation"` → `_canonical_nonexecution_envelope` (`:269-309`) returns `status: success`, `execution.status: not_applicable`. Correct.
- Two failures become successes (report §10). One real Gmail dispatch executed.
- **Not fixed by B1:** T4's two-part request still resolves as `single_action` and still drops the second half. That is Tier-1 work (C3), not a canonical regression.
- Legacy is reachable through the `_canonical_fallback` marker path (`:481-486`, `server.py:1417-1436`) **for pre-execution failures only** — see B1.6 for the post-execution narrative path where it is not.
- **Honest degradation is already end-to-end, verified:** when a narrative is unavailable, `mark_narrative_unavailable` (`response_drafting.py:204-215`) attaches a reason *"without synthesising a reply"*, and the Flutter client walks an explicit ladder — narrative → tool's own real output → honest "Brain isn't configured or unreachable" → generic confirmation — and *"deliberately never dumps the raw map as JSON"* (`http_uri_client.dart:558-580`). So B1.6 is a **gap in fallback coverage, not a user-facing fabrication risk**.

**Evidence gaps B1 must close before cutover (findings SR-9, SR-10)** — the canonical evidence base is only 4 inputs:

| Untested scenario | Why it matters |
|---|---|
| An **attachment** turn | `turn_state.py:85-89` deliberately excludes attachment *bytes*. The Brain can still call `read_attached_file` (session-scoped), so this is not structurally blocked — but it has never been exercised under canonical |
| The **"insurance/renewal/note" keyword-template workflow** (`workflow_planner.py:120-181` → a real `draft_output`) | This is the one behaviour legacy uniquely performs today. It is the single most likely silent regression when canonical becomes default |
| A **resumed approval** across turns | De-risked by inspection: `POST /approve` (`server.py:1531`) matches a deterministic `action_id` and is structurally separate from `/ask`'s decision path — but still untested under canonical |
| `remember_fact` and **multi-action Gmail** | Covered by `test_canonical_execution.py` unit tests, not by a live turn |

**B1 exit criteria**

1. A real live `/ask` turn is observed handled by `run_canonical_for_ask`, evidenced by a new `canonical_execution_log.jsonl` line — telemetry, not code reading. (The diagnostic already demonstrates this signal works: 0 new lines across 9 flag-off turns, 1 per turn with it on.)
2. Full battery re-run, all scenarios recorded, none worse than baseline.
3. Full regression suite green.
4. The rollback lever is **exercised in a test**, proving legacy still serves when narrowed.
5. `orchestrator.py` line count unchanged or lower.

### B2 — Legacy demotion

From the moment B1 lands, `process_user_input` is a rollback path only: **no new features, no new branches, no newly-wired capabilities**. Retirement criteria and the fact that retirement is its own separate milestone are in §10.

---

## 5. Batch C — fast/native path

### C1 — Provider-level native tool calling (additive)

| # | Change | Additive? |
|---|---|---|
| C1.1 | `tools: Optional[list] = None` kwarg on `ModelProvider.complete()` and each adapter (`base.py:189-196`, `ollama_provider.py:42`, `anthropic_provider.py:40`, `openai_compatible_provider.py:68`) | **Yes** — new kwarg with default; no existing caller breaks |
| C1.2 | `ModelResponse.tool_calls: Optional[list] = None`, normalised across providers (`base.py:53-74`) | **Yes** — dataclass field with default |
| C1.3 | Router needs **no change** to carry tools: `attempt(role, principal, **complete_kwargs)` forwards verbatim to `complete()` (`model_router.py:232-278`) | **Yes** |
| C1.4 | **Not additive, must be handled:** `attempt()` catches a *closed* exception set (`ProviderUnavailableError, ProviderTimeoutError, ModelNotFoundError, UnknownModelProviderError`, `:265-273`). Any new tool-calling error type must subclass one of those or the except clause must be widened, or it propagates uncaught | requires explicit change |
| C1.5 | Anthropic/OpenAI tool formats differ from Ollama's; normalise at the adapter boundary so only `ModelResponse.tool_calls` is seen upstream | — |

### C2 — Tier 0: direct chat, streamed

Built **on canonical's existing `conversation` mode**, not beside it. When the Brain returns no tool calls, its own streamed tokens are the reply — which also strengthens the Brain-authored-words rule, since no separate drafting call re-renders them.

**Design constraint:** Tier 0 is selected by **the Brain declining to call a tool**, never by a URI-side classifier or keyword rule. URI must not re-introduce the keyword routing that `workflow_planner._create_steps` (`:120-181`) is being demoted for.

### C3 — Tier 1: native tool loop through unchanged gates

**The central safety property — REVISED after review (finding SR-4), now scoped to what is actually verified:**

> A native tool call is **translated into the existing Decision Contract dict** (`mode`, `capability`, `actions[{name, inputs}]`) *before* it reaches `evaluate_gates()`. The gates and `_execute_canonical` never learn that "native tool calling" exists.

This holds **for a single-capability contract** — one capability, one action (or a same-capability multi-action set on the Gmail branch). For that shape, `_validate_contract` (`decision_engine.py:466-492`: object shape, mode, capability ∈ known ids, action names ∈ directory), `evaluate_gates` (`decision_gates.py:170`), `ApprovalGate.execute_tool` → `CapabilityResolver.is_allowed` (`approval_gate.py:108-136`, `capability_resolver.py:213`), and the executor's own chain (`capabilities/executor.py:37-58`: capability → action → availability → permissions → **`action.parameters.validate(inputs)`** → user approval → admin approval) all run exactly as today. Model-authored *inputs* are schema-checked at the same point contract-authored ones are.

**What the draft oversold, corrected here:** the Decision Contract's `capability` is a **single string**. It cannot represent one Brain response containing tool calls against *different* capabilities — which is precisely the diagnostic's own headline case (`gmail_search` **+** `list_tasks` in one response, report §7.2). `_execute_canonical` (`:312-334`) special-cases only `"Gmail"` (→ `multi_action_dispatch`) and `"remember_fact"`; everything else falls to `_execute_legacy_capability`, which hard-requires `len(actions)==1` and `actions[0].name == capability_id` (`:198-204`). **Cross-capability multi-tool has no execution path today and is a new, un-audited trust boundary — not an extension of the existing one.** It must be designed and audited on its own, not smuggled in under "the gates are unchanged."

**Two additional binding constraints from review:**

- **Principal provenance (SR-5).** `ApprovalGate` skips the capability-granted check entirely when `grants_store` **and** `principal` are both `None` (`approval_gate.py:112-119`, the legacy ambient-fixture path). The translator must therefore **always** populate `principal` from the authenticated request context, never from anything the model's tool call can influence. This must be an explicit, tested invariant.
- **Prerequisite: the frozen blueprint's P1.** Multi-tool routing lands on `multi_action_dispatch`, whose `_action_permitted` (`:314-318`) returns `True` unconditionally the moment a `permission_checker` is supplied — the blueprint's F2 defect. Today production passes **no** checker (`orchestrator.py:270` constructs `MultiActionDispatch(capability_registry=…)` only) and the Gmail-only alias map (`:24-30`) fails *closed* for other capabilities, so this is not a live hole — it is a **trap for exactly this implementer**, since wiring a checker is the natural first step of generalising dispatch. `M33_EXTERNAL_CAPABILITY_BRIDGE_BLUEPRINT.md` §3 **P1** already specifies the correct fix. **C3.3 must not begin until P1 has landed.**

| # | Change | Note |
|---|---|---|
| C3.1 | Tool-call → contract translator, with strict validation: unknown tool name ⇒ **error result returned to the Brain**, never a dispatch | new module |
| C3.2 | Tool schemas generated **from the existing capability registry** (17 tools) so there is one source of truth, not a second hand-maintained list | `uri_workspace/capabilities_registry.json` |
| C3.3 | **Multi-tool:** `_execute_legacy_capability` requires exactly one action matching the capability id (`canonical_execution.py:198-203`). Multiple tool calls must route through the multi-action path, or dispatch must be extended explicitly — this is the single largest unknown in Batch C and must be designed before coding | `canonical_execution.py:312-334` |
| C3.4 | **Parallel execution — BLOCKED pending a real write/no-write classification (finding SR-1, the most serious of the review).** A `read_only` flag *does* exist — `Action.read_only: bool = True` (`capabilities/base.py:137`, **defaulting to True**) — and it is derived as **`read_only = (approval == "none")`** (`capabilities/registry.py:110`), via the exact adapter C3.2 would use. That derivation is **provably wrong for at least 5 shipped tools**: `remember_fact` (writes durable memory), `generate_document`, `convert_document`, `draft_institutional_note`, `draft_institutional_order` are all `approval=none` and therefore all labelled `read_only=True` while mutating state. `risk` is uniformly `controlled` across all 15 non-approval tools, so it carries no signal either. Parallelising on this flag would schedule **concurrent writes with no ordering guarantee**. **C3.4 does not proceed until a genuine side-effect classification is added to the registry and audited.** Interim option if parallelism is wanted sooner: an explicit, hand-verified allowlist of pure reads (`gmail_search`, `gmail_find_draft`, `drive_search`, `recall_memory`, `system_performance`, `read_attached_file`) — never the `read_only` flag as computed today | `capabilities/base.py`, `capabilities/registry.py`, registry schema, new executor wrapper |
| C3.8 | **Mixed-approval batches (finding SR-6).** `decision_gates.py` computes `approval_required = any(...)` across a contract's action names, so one approval-required action blocks the **whole** batch. Fail-closed and therefore safe — but it means C3.5's "let the safe branches proceed" is **not** current behaviour and needs new code that this plan must describe rather than assume | `decision_gates.py` + wrapper |
| C3.9 | **Idempotency for Brain-initiated retries (finding SR-7).** C3.5 hands partial failures back to the Brain and lets it decide. `gmail_create_draft` has no dedup key — a confused retry of an already-approved, already-executed draft creates a second draft. Audit ordering (S5) proves *when*, not *that it happened once*. Tier 1 needs an execution-identity/dedup key for side-effecting calls **before** C3.5 ships | new wrapper + approval store |
| C3.7 | **Loop bound (new — review finding SR-2).** `canonical_execution.py` has **no iteration bound of any kind**; it is single-shot. The `max_brain_iterations=3` cap exists only in legacy `orchestrator.py:119`. Tier 1's continuation loop therefore inherits **no** bound and must declare its own explicit cap, plus behaviour on hitting it (report honestly, never silently truncate) | new module |
| C3.5 | **Branch preservation:** today `MultiActionExecutor.execute_chain` (`capabilities/executor.py:71-89`) halts on first non-success, preserving completed steps but never attempting remaining independent ones. Tier 1 must return **per-branch results — successes and failures alike — to the Brain** and let it decide. This is a genuine behavioural change and needs its own tests | `capabilities/executor.py` + new wrapper |
| C3.6 | Continuation: tool results go back to the Brain, which produces the final streamed answer. This **is** the re-evaluation step of the USER→BRAIN→URI loop | — |

### C4 / C6 — Streaming, end to end

**Constraint discovered in research — streaming cannot be bolted onto existing methods:**

| Layer | Why not in place | Additive path |
|---|---|---|
| Provider | `complete()` returns a single `ModelResponse` and every adapter hardcodes `"stream": False` (`ollama_provider.py:57`) | **New method** (e.g. `complete_stream()`) yielding chunks; `complete()` untouched, so all 5 router call sites keep working |
| Backend | `/ask` is a sync `def` returning a plain dict (`server.py:1286-1291`); no SSE/WebSocket/streaming endpoint exists anywhere; only `CORSMiddleware` is registered, so nothing buffers a stream | **New endpoint**; `/ask` remains until the UI has shipped and soaked. Auth DI (`_resolve_authenticated_user_id`) works unchanged on a streaming endpoint |
| Flutter | `UriClient.ask()` returns `Future<UriTurn>`; `MockUriClient` and every widget test implement/expect that | **New interface method** (e.g. `askStream`), trivially implementable by `MockUriClient` as one synthetic chunk; `AppState` opts in separately; existing `ask()` path and tests keep passing |

`AppState.ask()` currently appends a pending turn, awaits once, then replaces it (`app_state.dart:483-519`) — there is no incremental-update path, so the streamed variant adds one rather than modifying that flow.

### C5 — Tier 2 escalation only

Planner / `WorkflowExecutor` / recovery / evidence ledger are entered only on genuine escalation: durable multi-step work, a failure needing recovery, a resumable or approval-paused turn. The keyword routing in `workflow_planner._create_steps` (`:120-181`) is retired as the default route.

### C7 — Prompt reduction, measured, last

Only after the tiered path works, and only against the battery: trim what demonstrably does not change behaviour. **Policy, identity and tool rules are never in the trimmable set** (A2.3). Any trim that changes refusal or honesty behaviour is reverted.

---

## 6. Migration order and dependency graph

```
PC1 clean tree ──> PC3 latency battery (scripts/m32_latency_battery.py)
                        │
                        ├─> A1 Gmail credential scoping ──────┐
                        │                                     │  (independent; ship first)
                        ├─> A2 model-aware context budget ────┤
                        │                                     │
                        └─> B1 canonical enablement ──────────┤
                                    │                         │
                                    └─> B2 legacy demotion     │
                                              │               │
                                              v               v
                            C1 provider tools= + ModelResponse.tool_calls
                                              │
                            C2 Tier 0 direct chat ──> C4 streaming (backend)
                                              │            │
                            C3 Tier 1 tool loop ───────────┤
                              (parallel, branch-preserving) │
                                              │            v
                            C5 Tier 2 escalation only   C6 streaming (Flutter)
                                              │
                            C7 prompt reduction (measured, last)
```

**Ordering rationale:**

1. **A1 first and alone.** It is a security defect, independent of everything else, and should not be sequenced behind an architecture change.
2. **A2 before C.** Making context limits model-aware removes the silent-truncation risk *before* prompts start carrying tool schemas.
3. **B before C.** Tier 0/1 are built **on** the canonical path. Building them beside a path that is off would create a third execution route — the outcome the frozen blueprint warns against.
4. **C7 last — and this deliberately reverses the diagnostic's own suggested ordering** (finding SR-15, acknowledged rather than left silent). The diagnostic's §12 put prompt reduction second, as "a pure win with no architectural commitment". Two reasons for moving it: (a) Tier 0/1 **delete** whole prompts rather than trim them — the drafting call disappears, the semantic call disappears — so trimming them first is work thrown away; (b) prompt content is the plan's single highest-risk edit (R8: trimming something that was genuinely constraining behaviour), and it is far safer to measure against a stable tiered path.
   **The honest consequence, stated plainly:** §9's Tier-0/Tier-1 latency targets are asserted for batches that ship *before* C7, while the diagnostic's numbers show canonical alone still costs ~14–17 s. If C2/C3 do not hit their targets without C7, the correct response is to pull a **bounded** slice of C7 forward (the fixed policy/identity/catalogue portion of the Tier-0 prompt only) rather than to declare the targets met.

---

## 7. Tests per batch

Conventions, verified: backend tests are `test_*.py` at **repo root** (182 files), run with `./.venv/Scripts/python.exe -m pytest <file> -v`. The established way to fake a model is `model_callable` injection (`decision_engine.py:507`, and 27 other modules/tests). Flutter tests live in `uri_ui/test/`.

| Batch | New tests | Tests that must be updated (breaking, by design) | Suites re-run unchanged |
|---|---|---|---|
| **A1** | cross-account mailbox isolation; shared-connection truthfulness; concurrent authorise; token adoption once-only | `test_gmail_unread_count_endpoint.py:26` (asserts no-arg call); `test_connection_status.py`; `test_gmail_connection_truth.py`; `test_gmail_search_service.py`; `test_gmail_search_tool.py`; `test_google_oauth_authorize_flow.py` | `test_multi_user_isolation.py`, `test_m21_file_store_isolation.py` |
| **A2** | model-aware default; policy/identity survive trimming; output headroom; honest overflow | `test_ollama_provider.py:70` and `:300` (both hardcode 8192) | `test_m21_context_window.py`, `test_m21_context_window_live.py`, `test_m21_prompt_budget.py`, `test_m21_provider_config.py` |
| **B1** | live-turn-served-by-canonical (telemetry-evidenced); rollback lever actually restores legacy | none expected — canonical tests already pass | full regression; `test_decision_engine.py`, `test_workflow_continuation.py` |
| **C1** | provider `complete(tools=…)` per adapter; `ModelResponse.tool_calls` normalisation across the three adapters; tool-error exception classification through `attempt()` | none — additive | all 5 router call-site suites |
| **C2** | Tier 0 selected only by the Brain declining tools; no URI-side keyword routing reachable | — | canonical conversation-mode tests |
| **C3** | tool-call→contract translation; unknown tool ⇒ error to Brain, never dispatch; **gates unchanged** (approval still fires, grants still enforced); parallel only for read-only/approval-free; **per-branch results preserved on partial failure** | `capabilities/executor.py` halt-on-first-failure semantics are extended, so its existing tests need companions rather than edits | `test_m22_4_capability_resolver.py`, `test_orchestrator_decision_priority.py`, `test_orchestrator_model_driven_workflow.py`, `test_orchestrator_model_workflow_approval_resume.py` |
| **C4/C6** | provider `complete_stream()` chunking; SSE endpoint contract; approval-pause mid-stream; Flutter `askStream` + `MockUriClient` single-chunk implementation | none — new method/endpoint, old paths untouched | every `uri_ui/test/*.dart` suite must pass **unchanged** — that is the proof streaming was additive |
| **C7** | before/after refusal and honesty behaviour on identical inputs | — | full regression + battery |

## 8. Security and approval regression matrix

Run at **every** batch boundary, not only in Batch A. Each row is a property that must hold identically before and after.

| # | Property | Evidence today |
|---|---|---|
| S1 | A high-risk tool still requires approval and returns `awaiting_approval` **before** any side effect | `gmail_create_draft`, `drive_upload` are the only two `approval_requirement: user_approval_required` of 17 tools; measured correct in diagnostic T5 |
| S2 | An ungranted capability is refused for that principal | `CapabilityResolver.is_allowed` via `approval_gate.py:120-136` |
| S3 | Auth: no header ⇒ ambient/unauthenticated behaviour; bad header ⇒ 401, never a silent downgrade | `server.py:487-515` |
| S4 | `ProviderAuthenticationError` is **never** swallowed by router fallback | `model_router.py:265-267` — explicitly never caught |
| S5 | Every dispatch leaves an audit record, with ordering preserved under parallel execution | `approval_gate.py` `_record_audit_safely` |
| S6 | Failure is reported honestly — no fabricated success | `prepare_output`, `mark_narrative_unavailable` |
| S7 | User-visible words are Brain-authored; the deterministic fallback restates decided facts only | `_draft_narrative_safely` / streamed Brain tokens |
| S8 | Per-user state isolation holds for profile/memory/sessions/files | `test_multi_user_isolation.py`, `test_m21_file_store_isolation.py` |
| S9 | **(A1-dependent)** Google/mailbox access matches whatever scoping the User decides in §3 A1 | currently install-wide by directive |
| S10 | Rate limits and the pre-parse body-size guard still fire | `edge.py:112-152` |

**Rule:** a batch that changes any S-row's behaviour without an explicit User decision is blocked, not merged.

---

## 9. Latency benchmarks

Baselines are the measured figures in the diagnostic report, re-recorded by `scripts/m32_latency_battery.py` (PC3) before any change. **Exit criteria are latency-measured, not asserted.**

| Scenario | Baseline (shipped legacy, HTTP) | After B | After C target |
|---|---|---|---|
| "Hi" — total | 13.65–15.86 s | ~14 s, 2 calls | **≤ 3 s**, 1 streamed call |
| "Hi" — time to first UI token | = total (no streaming) | = total | **≤ 0.5 s** |
| No-tool question | **30.58 s → `failed`** | success, 2 calls | **≤ 4 s** |
| Single read-only tool | **19.49 s → `failed`** | success | **≤ 5 s** |
| Two-part tool request | 31.13 s, 1 tool, half dropped | 1 tool, half dropped | **≤ 6 s, both tools executed** |
| Approval-required action | 35.51 s → correct gate | correct gate | **≤ 6 s**, gate unchanged |
| Model floor (reference) | 0.27 s total / 0.074 s first token | — | — |

Every batch records: total latency, time to first model token, time to first UI token, model-call count, tool-call count, parallel vs sequential, URI overhead, gates traversed — the same columns as the diagnostic report, so results are directly comparable.

**Regression rule:** no batch may be declared complete if any scenario's latency or call count is **worse** than the previous batch's recorded figure, unless the User accepts the trade explicitly.

---

## 10. Rollback and legacy retirement

### Per-batch rollback

| Batch | Rollback lever | Reversible without data loss? |
|---|---|---|
| A1 | Per-user credential store falls back to read-only adoption of the existing token; revert = restore repo-root resolution | Yes — no token is destroyed, only relocated/copied |
| A2 | Context limits are configuration: revert to the previous constant | Yes |
| B1 | `CANONICAL_EXECUTION_ALLOWLIST` narrowing lever + legacy remains reachable. **Defect to fix as part of B1:** that lever is a *module-level source constant* (`canonical_execution.py:76`, default `None`), and `canonical_killswitch_enabled()` merely tests whether it is non-`None` (`:99-105`). Rolling back therefore requires **editing and redeploying source**, which is not an operational rollback. B1 must expose it as runtime configuration alongside the enablement flag | Yes, but only after B1 makes the lever runtime-settable |
| C1–C3 | Tier routing behind an explicit toggle; toggle off ⇒ canonical JSON decision contract path. **The toggle must be runtime-settable, not a module constant** (finding SR-13) — B1.2 fixes exactly that defect for the canonical allowlist, and Batch C must not reintroduce the same class of problem. **Also required:** a stated answer for a session whose state was written by the tiered path when the toggle flips mid-conversation — persisted session/workflow state migration is not currently addressed | Yes, once the toggle is runtime and the mid-conversation case is specified |
| C4/C6 | Streaming endpoint is **additive**; the blocking `/ask` remains until the UI has shipped and soaked | Yes |
| C7 | Prompt composition is data; revert restores prior content | Yes |

**Rule:** every batch ships with its toggle **and a test that proves the toggle actually restores prior behaviour** — a rollback lever that has never been exercised is not a rollback lever.

### Legacy retirement criteria

Legacy `process_user_input` is a **temporary rollback path only**: no new features, no new branches, no new capabilities wired into it from the moment Batch B lands. It may be retired only when **all** hold:

1. Canonical has served **100 %** of live `/ask` turns, evidenced by `canonical_execution_log.jsonl`, with `fallback_used: false` throughout — over a **concretely specified window** (finding SR-14: "a sustained period agreed with the User" is not objectively checkable, unlike criteria 2–5). **Proposed concrete bar, for the User to accept or change: ≥200 consecutive live turns and ≥14 days, covering at least one turn of each class in §4's evidence-gap table.**
2. Zero legacy-fallback telemetry events in that window (`record_shadow_trace` "legacy_fallback").
3. The full regression suite passes with legacy **disabled**, not merely unused.
4. Every behaviour still unique to legacy is either reproduced under canonical or explicitly recorded as intentionally dropped, with User sign-off.
5. The M30.8 completion-record correction (§4) is written, since M30.8 is recorded COMPLETE with a cutover that never took effect.

Retirement itself is a **separate milestone**, not the tail of this one, and deleting `orchestrator.py` code is the one change that would let the no-growth rule finally reverse.

---

## 11. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Local model chooses tools unreliably on inputs harder than the 5 probed | High | Build a tool-selection eval battery (extends PC3) before C3 cutover; keep the JSON decision contract as an automatic fallback for models without tool support |
| R2 | Provider tool-call formats diverge (Ollama / Anthropic / OpenAI-compatible) | Medium | Normalise into one `ModelResponse.tool_calls` shape; one adapter change each; cloud paths cannot be live-tested here (no key configured) — disclose as unverified |
| R3 | Streaming interacts badly with approval pauses | Medium | Approval emits a terminal stream event; the turn resumes as a **new** streamed continuation; never stream a side effect before its gate |
| R4 | Parallel execution breaks per-user isolation or audit ordering | **High** | Only independent, **read-only, approval-free** calls run concurrently; anything side-effecting or approval-gated stays strictly serial; audit records carry explicit ordering |
| R5 | A1 collides with uncommitted `connection_status.py` changes | High | PC1 — do not start until the tree is clean |
| R6 | Tier 0 misroutes a request that genuinely needed a tool | Medium | Tier 0 is chosen by the **Brain declining to call a tool**, not by URI's own classifier; if the Brain calls a tool, it is Tier 1 by definition. No keyword routing anywhere in the decision |
| R7 | Three execution paths coexist during migration (legacy, canonical, tiered) | High | Strict ordering (§6): B completes before C begins; C replaces canonical's contract call rather than adding a route beside it |
| R8 | Prompt trimming removes content that was actually constraining behaviour | **High** | C7 is last, is measured, and A/B's refusal/honesty behaviour before and after; policy/identity are **never** in the trimmable set (§3 A2) |
| R9 | `orchestrator.py` grows again | Medium | All new code in new modules; batch exit criteria include a line-count check |
| R10 | Scope creep into the External Capability Bridge M32 | Medium | §0 identifier split; external transports are explicitly out of scope |
| **R11** | **Parallelising on `Action.read_only`, which is wrong today** (`base.py:137` defaults True; `registry.py:110` derives it from `approval == "none"`) — would schedule concurrent writes | **BLOCKER** | C3.4 blocked until a real write/no-write classification exists and is audited |
| **R12** | **Cross-capability multi-tool has no execution path** and would be a new trust boundary | **High** | Scope the C3 safety claim to single-capability; design cross-capability dispatch separately, after P1 |
| **R13** | **Duplicate side effects** from Brain-initiated retry after partial failure (`gmail_create_draft` has no dedup key) | High | C3.9 execution-identity key before C3.5 ships |
| **R14** | Translator supplies a `principal` the model can influence, or none at all (ambient bypass, `approval_gate.py:112-119`) | High | Principal always taken from the authenticated request; tested invariant |
| **R15** | Canonical becomes default while `URI_ENABLE_WORKFLOW_CONTINUATION_MODE` stays unset ⇒ every resumed workflow silently routes to legacy | High | B1.5 decides the second flag explicitly |

---

## 12. Worker routing and approval gates

Per the standing AO-4 development cycle:

- **Claude** — this plan, independent pre-audit, final audit, bounded fixes, release authority.
- **Antigravity** — loop manager: prepares task-initiation packages and routes each batch.
- **Codex** — preferred implementer for A1 (security-sensitive), B1 (production call path), C1–C3 (architectural, multi-file).
- **Gemma** — bounded work only: test scaffolding, mechanical edits, fixture creation.

**Stops for explicit User approval (not auto-approved):**

1. §0 identifier collision resolution.
2. PC1 resolution — how the uncommitted Hybrid UI work is landed.
3. Batch B1 cutover itself (changes which engine serves every live turn).
4. Any decision to retire legacy (separate milestone).
5. Batch A1's migration choice for the operator's existing Google token.

This plan is **DRAFT** until the User approves.

---

## 13. Independent review record

Two independent adversarial reviewers (Sonnet, per the User's constraint) reviewed the draft against source, plus the author's own verification pass. **Every reviewer claim below was re-verified against source before being accepted** — three were found overstated and are recorded as such rather than adopted.

### Findings adopted (revisions applied above)

| ID | Severity | Finding | Where applied |
|---|---|---|---|
| SR-1 | **BLOCKER** | `Action.read_only` exists, defaults `True` (`base.py:137`), and is derived as `approval == "none"` (`registry.py:110`) — wrong for ≥5 shipped mutating tools. Parallelising on it schedules concurrent writes | C3.4, R11 |
| SR-4 | **High** | "Gates unchanged" was oversold: cross-capability multi-tool has **no** execution path (`canonical_execution.py:198-204`, `:312-334`) and is a new trust boundary | C3 safety claim, R12 |
| SR-5 | High | Ambient bypass: grant check skipped when `principal` and `grants_store` are both `None` (`approval_gate.py:112-119`) | C3 constraints, R14 |
| SR-7 | High | No idempotency for Brain retries after partial failure; `gmail_create_draft` has no dedup key | C3.9, R13 |
| SR-8 | High | Second unset flag `URI_ENABLE_WORKFLOW_CONTINUATION_MODE` sends every resumed workflow to legacy silently (`canonical_execution.py:262-263`) | B1.5, R15 |
| SR-2 | High | No loop bound anywhere in `canonical_execution.py`; `max_brain_iterations=3` is legacy-only (`orchestrator.py:119`) | C3.7 |
| SR-9/10 | High | Canonical evidence base is 4 inputs; attachments and the legacy keyword-template workflow were never exercised | B1 evidence-gap table |
| SR-11 | High | A missing fourth, cheapest A1 option: restrict *invocation* via the already-enforced per-user capability grants | A1-4 |
| SR-13 | Medium | Batch C toggle must be runtime-settable, and mid-conversation state migration is unaddressed | §10 |
| SR-14 | Medium | Retirement criterion 1 was not objectively checkable | §10 (concrete bar proposed) |
| SR-15 | Medium | C7-last silently reversed the diagnostic's own ordering | §6 (acknowledged + consequence stated) |
| SR-16 | Medium | A2.5's enforced overflow has no designed small-window failure shape | A2.7 |
| SR-6 | Medium | Mixed-approval batches already fail closed via `any(...)`; C3.5's intent needs new code | C3.8 |
| SR-12 | — | Cost map was **too pessimistic**: tools already accept injectable services | A1 correction note |

### Reviewer claims found overstated, corrected rather than adopted

| Claim | Verdict after verification |
|---|---|
| "Canonical returns raw tool JSON as the reply if drafting fails, violating Brain-authored-words" | **Overstated.** `mark_narrative_unavailable` attaches a reason *"without synthesising a reply"* (`response_drafting.py:204-215`), and the client never dumps raw JSON and never invents text (`http_uri_client.dart:558-580`). Real residue — no legacy fallback post-execution — kept as B1.6 |
| "Attachments are structurally invisible to canonical" | **Overstated.** `turn_state.py:85-89` excludes attachment *bytes* by design, but `read_attached_file` is a registered session-scoped capability the Brain can call. Real residue — never tested under canonical — kept as an evidence gap |
| "`test_ollama_provider.py` / `test_canonical_execution.py` do not exist" | **False.** Both exist at repo root; the latter has exactly the 36 tests the frozen blueprint cites. Author verified counts directly (36/27/18/12). This is why no reviewer claim was adopted unverified |

---

## 14. Recommendation

**BLOCKED** — for specific, closeable reasons, not as a rejection of the architecture.

The architecture is sound and the evidence supports it. What is not yet true is that it is *safe to start implementing*, on four counts:

| # | Blocking item | Closeable by |
|---|---|---|
| **1** | **PC1 — the working tree is dirty** (46 files, +3,116/−1,763, 31 untracked), and `connection_status.py` — which Batch A edits — already carries uncommitted Live-UX-Repair changes | Landing the Hybrid UI work first. User decision on how |
| **2** | **A1 is a User decision, not an engineering task.** The install-wide model is an explicit, documented 2026-09-12 User directive. Four options now exist (A1-1…A1-4) | User picks an option |
| **3** | **C3.4 rests on a flag that is provably wrong** (`read_only = approval == "none"`) | Adding a real write/no-write classification — small, self-contained, and worth doing regardless |
| **4** | **§0 identifier collision** — two live milestones named M32 | User picks a label |

**What is GO the moment PC1 clears, with no further decisions needed:** **PC3** (commit the latency battery) and **B1** (canonical enablement) — B1 now has measured evidence, 36 existing tests covering exactly its safety properties, a working rollback lever once B1.2 lands, and two named evidence gaps to close first. A2 is GO as soon as A2.7's failure shape is designed.

**What must not start yet:** C3.3/C3.4 (pending P1, the classification, and the cross-capability design) and any legacy retirement (its own milestone).
