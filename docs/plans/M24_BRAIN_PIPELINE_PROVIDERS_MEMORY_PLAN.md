# M24 — Brain Response Pipeline Repair, Hermes-Grade Providers UI, Memory Provider Settings, First-Run Brain Onboarding

**Status:** ACCEPTED (auto-approved, see History Log in `M24_STATE.md`)
**Author:** Claude (AO-4 Architect / Pre-Auditor)
**Date:** 2026-09-12
**Requested via:** a peer Claude Code session, relaying a User directive (screenshots of a blank Model Providers page and a chat turn that failed to surface fetched web content, plus a request to match Hermes Agent's Providers/Memory/Gateways settings UX). Audited from real, current repository source — not from the peer's characterization of the bugs — before any of its claims were accepted as fact below.

---

## §0. Scope discipline

This plan is a **repair + additive-UI** milestone, not a redesign. ADR-018 (model reasons/proposes, deterministic runtime validates/executes/persists) is not renegotiated by anything below — §2's finding is that the boundary is already intact; the defect is a **provider-role wiring gap** that silently prevents the Brain from ever being called for narrative drafting, not a runtime restriction on the Brain's authority. Nothing in this plan changes what the Brain is allowed to decide, only what the Brain is actually invoked to *phrase*, and where the User can see/fix a misconfigured Brain instead of hitting a silent, unexplained fallback.

---

## §1. Audit findings, each traced to real source

### 1.1 Root cause: why replies fall back to "URI finished processing this request."

Traced end-to-end, `uri_core/core/orchestrator.py` → `uri_core/core/response_drafting.py` → `uri_core/config/model_roles.py`:

- `orchestrator.py:110` defaults `enable_response_narrative=False`, but this is **not** the live bug: `uri_core/app/server.py:150` and `:393` both explicitly construct `UriOrchestrator(..., enable_response_narrative=True, ...)` for every real request path. Narrative drafting is enabled in production.
- The real defect is in **provider role resolution** (`uri_core/config/model_roles.py:171-192`, function `resolve_provider_for_role` — exact name may differ, resolved by role/provider lookup):
  - A user's **Active Brain** override (`ProviderConfigStore.get_active_brain()`) is consulted **only when `role == ROLE_REASONING`** (`model_roles.py:173`). `ROLE_DRAFTING` — the role `response_drafting.draft_response()` actually calls via `get_router().attempt(ROLE_DRAFTING, ...)` (`response_drafting.py:271`) to author the user-facing narrative — **never consults the Active Brain the user configured in the Providers screen at all.**
  - `load_model_roles()` reads `MODEL_ROLES_PATH = uri_workspace/model_roles.json` (`model_roles.py:87`). **This file does not exist anywhere in the repository or workspace** (confirmed by direct filesystem search). `load_model_roles()` therefore always returns `{}`, so `role_config = {}` for every role including drafting, and `provider_name = role_config.get("provider", "ollama")` (`model_roles.py:192`) **always resolves to `"ollama"` for narrative drafting, unconditionally, regardless of any Active Brain the user has ever set.**
  - If local Ollama is not running, or the configured/default model isn't pulled, `OllamaProvider.complete()` raises. `response_drafting.draft_response()` wraps any exception as `ResponseDraftingError` (`response_drafting.py:277-278`).
  - `orchestrator.py._draft_narrative_safely` (`:3227-3260`) retries once, then **silently swallows** the failure: it calls `_record_narrative_audit_safely(status="narrative_rejected"|"narrative_failed", ...)` (an internal audit-log write only) and returns, leaving `response["narrative"]` unset. Nothing about this failure is surfaced to the caller, the HTTP response, or the UI.
  - `uri_ui/lib/services/http_uri_client.dart:374-380` and `:427-448` then fall through: `narrative` is `null` → checks `responseData['message']` → checks `_bestTextualField(responseData)` (a generic longest-plain-string scrape, `http_uri_client.dart:14-19` docstring) → if none of those find a usable string, **`summary = 'URI finished processing this request.'`** (`:447`). This is exactly the string the User saw.
- **Compounding, separate issue for the "fetch NIT Sikkim website" case specifically:** even when a tool (e.g. `web_search`/`fetch_url`) executes successfully, `_bestTextualField` only surfaces a **plain string** value found somewhere in the tool's result map — it does not know how to summarize a structured result (e.g. a list of search hits, a fetched page broken into blocks/sections). Codex must confirm what shape the live `web_search`/`fetch_url` capability actually returns in `response["response"]`/`execution` and, if it is not a flat string the existing fallback can find, this is a second, independent reason the fetched content never reached the user even before considering narrative drafting at all.

**Conclusion on Audit Point 1 (Brain getting the required information):** the Brain is *not* receiving a wiring failure gracefully-in-the-good-sense — it is never being successfully invoked for drafting at all, because of the Active-Brain/role-scoping gap and the missing `model_roles.json`, and any resulting failure is invisible to the user. This is the single highest-priority fix in this plan.

### 1.2 Is the Brain restricted by the URI structure? (ADR-018 integrity)

No structural restriction found. `_draft_narrative_safely`'s own docstring and implementation (`orchestrator.py:3078-3091`) already implement the correct separation: the deterministic runtime fully decides `execution`/`response` *before* the Brain is asked to phrase anything, and the Brain's draft is validated (`validate_drafted_response`) and only **additively** merged as `response["narrative"]` — it can never override or contradict the deterministic outcome. `test_orchestrator_response_narrative.py` (referenced at `orchestrator.py:2892`) already exists to prove exactly this boundary. **No change to this boundary is needed or proposed.** The user-visible symptom is a wiring/config defect (§1.1), not an authority restriction — this plan repairs the wiring, not the boundary.

### 1.3 Model Providers UI blank-page bug — root cause confirmed

`uri_ui/lib/screens/settings/providers_screen.dart:114-115`: `ProvidersScreen.build()` returns a **`Scaffold(body: CustomScrollView(...))`** — a full-page widget that expects to own the screen's entire layout box. But `uri_ui/lib/screens/settings/settings_shell.dart`'s `_WideSettings.build()` (`:233-247`) embeds `category.builder(context)` directly inside a `Column` inside a `SingleChildScrollView` (`:234`), i.e. an **unbounded-height** ancestor. A `Scaffold` sizes itself to fill the available height constraint; nested inside an unbounded-height scrollable, this is a layout contract Flutter cannot satisfy, and the result is the blank/collapsed render the User's screenshot shows. Every sibling settings screen (`MemorySettingsScreen`, `ConnectionsSettingsScreen`, etc.) correctly returns a plain layout widget (no `Scaffold`) for exactly this reason — `ProvidersScreen` is the one outlier.

### 1.4 Memory provider / Memory & Context settings

`uri_core/core/user_memory.py` + `uri_core/core/personalization_context.py`: a single, ambient, JSON-file-backed `MemoryStore` per install/user (explicitly documented as "there is exactly one memory store per install, because there is no authentication yet" for the legacy-ambient path, and one per authenticated user under the M22 per-user store pattern). There is **no pluggable "Memory Provider" abstraction** (no interface for a vector/graph-backed alternative), **no token-budget controls**, **no compression/context-engine settings**, and **no Persistent Memory / User Profile on-off toggle** anywhere in the backend or `uri_ui/lib/screens/settings/memory_settings_screen.dart` (which is a plain CRUD list of memory entries — real and functional, but not a "Memory & Context" settings surface in the Hermes sense).

### 1.5 First-run onboarding when no Brain is configured

`uri_ui/lib/screens/onboarding/onboarding_screen.dart` exists and is gated in `uri_ui/lib/app.dart` — but it is a one-time **preference tour** (focus areas, communication style, autonomy level; see `onboarding_screen.dart:7-9`), gated on whether `UserPreferences` have been set, not on whether any provider/Active Brain is configured. `server.py`'s `get_active_brain`/`_active_brain_for_user` (`:2417-2442`) can return `active_brain: null` with zero providers configured, and the app has no gate that detects this state and routes the user to configure a Brain before landing on a chat that will silently fail every request per §1.1. This is a genuine, currently-missing gap.

---

## §2. Implementation specification (for Codex; Antigravity to route and initiate)

### Phase A — Brain response pipeline repair (highest priority; fixes the reported chat failures)

1. **`uri_core/config/model_roles.py`**: extend the Active-Brain override (currently `model_roles.py:171-190`, gated to `role == ROLE_REASONING`) to **also apply when `role == ROLE_DRAFTING`**, so a user's configured Active Brain is used for narrative authoring, not only for the primary reasoning role. Preserve the existing `provider_id_override` extension point and zero-behavior-change guarantee for any caller that passes no principal.
2. Ship a real `uri_workspace/model_roles.json` (or generate a safe default in code if the file is absent, rather than silently defaulting every unset role to `"ollama"`) so role resolution has an explicit, inspectable configuration rather than depending on an absent file. Document the schema (`{"<role>": {"provider": ..., "model": ..., "base_url": ..., ...}}`) in a short comment at the top of `model_roles.py` if not already present.
3. **Surface narrative-drafting failure to the caller**, additively: when `_draft_narrative_safely` swallows a `ResponseDraftingError`/generic exception (`orchestrator.py:3242-3260`), also set a small, non-narrative diagnostic field (e.g. `response["narrative_unavailable_reason"]`, one of a fixed small vocabulary like `"no_brain_configured"`/`"drafting_provider_unreachable"`) **only when this can be determined without violating the additive-only contract** — this is diagnostic metadata for the client to use to prompt "configure a Brain," never text presented to the user in place of a Brain-authored reply. Never invent a friendlier synthetic narrative sentence in `orchestrator.py`/`server.py` — the canonical-interaction-loop rule (URI never authors the user-facing reply) still applies; the client-side fallback string is the one already-accepted exception and stays exactly as-is.
4. **`http_uri_client.dart`**: when `narrative_unavailable_reason` is present, use it to show a distinct, actionable client message (e.g. "URI's Brain isn't configured or is unreachable — set an Active Brain in Model Providers.") **instead of** the generic `'URI finished processing this request.'` string — this is still a deterministic client-side fallback (not a Brain-authored reply), simply a more honest and actionable one than the current content-free string.
5. Confirm (write a focused test if none exists) what shape `web_search`/`fetch_url` capability results actually take in `response["response"]`/`execution`, and confirm `_bestTextualField`/the Dart-side fallback can surface real fetched content when narrative drafting is unavailable — if the tool's own result shape needs a structured-content path (not just a flat string), add the minimal reader for it, without inventing a general-purpose renderer beyond what the two named tools actually return.

### Phase B — Model Providers UI: fix blank page + Hermes-grade sub-tabs

1. **Bug fix (do first, independently testable):** `providers_screen.dart` must not return a `Scaffold`. Change `ProvidersScreen.build()` to return the same shape every sibling settings screen uses (a plain `Column`/`CustomScrollView`-free widget sized by its content), matching `MemorySettingsScreen`'s convention. Verify by rendering `SettingsShell` on a wide layout in a widget test and asserting `ProvidersScreen`'s content (provider cards) is actually present in the tree and has nonzero height — not just that no exception was thrown.
2. **Hermes-inspired reorganization**, additive over the existing working `ProviderEntry`/key/config/Active-Brain machinery already in `uri_client.dart`/`app_state.dart` (do not re-architect the working backend contract, only the presentation):
   - Sub-tabs: **Accounts / API Keys** (existing `_KeyDialog` flow, reskinned as an inline section rather than a modal-per-provider if time allows, else keep the dialog), **Local Models** (Ollama/local server status + model list, pull/refresh where the backend already exposes it), **Custom Endpoints** (existing `_ConfigDialog` base-url/model override, reskinned as its own tab), and a persistent, always-visible **Active Brain** indicator/selector (the existing `_confirmActiveBrain` flow) — this is the one element Hermes' reference screenshots and this audit agree must stay prominent regardless of which sub-tab is open.
   - No new backend endpoints required for this phase; it is a presentation-layer reorganization of already-fetched `ProviderEntry` data.

### Phase C — Memory & Context settings page (Hermes-grade)

1. New `uri_ui/lib/screens/settings/memory_context_settings_screen.dart` (additive; keep `memory_settings_screen.dart`'s existing CRUD list as a sub-section, don't discard it) with: Persistent Memory toggle, User Profile toggle, Memory token budget, Profile token budget, Compression threshold/target, Protected recent messages count.
2. Backend: extend `uri_core/core/user_memory.py`/`personalization_context.py` (or a new small `uri_core/core/memory_settings.py`, per-user, JSON-persisted, following the exact pattern `ProviderConfigStore` already uses) with a settings record for the fields above, plus read/write endpoints in `server.py` (`GET/PUT /memory/settings`), classified in `route_classification.py` like every other `/memory/*` route.
3. **"Memory Provider" concept**: introduce a single new field, `memory_provider: "builtin"` (the only value that exists today), in the new settings record — this is the **extension point**, not a working plugin system. Do not build a vector/graph backend in this milestone; the acceptance bar is that the field exists, is read/written correctly, and `personalization_context.py`'s pure/read-only/consent-respecting contract (already tested by `test_capability_authority_boundary.py`-adjacent tests) is provably unchanged by this addition.

### Phase D — First-run Brain onboarding

1. `server.py`'s existing `get_active_brain`/provider-catalogue endpoints already report whether any provider is `configured`/there is an `active_brain`. Add a small `AppState` check (client-side, using data already fetched) for "no active brain AND no provider configured" and, when true, route to a new first-run screen (reuse `onboarding_screen.dart`'s visual style) that guides the user to either configure a local Ollama model or add an API key, with a one-click "Test connection" action before letting them into the main chat shell. This gate is **in addition to**, not a replacement for, the existing preference-tour onboarding gate in `app.dart`.
2. This screen must not block a user who has a working Brain already configured (e.g. on every subsequent launch) — gate strictly on the "no provider configured at all" condition, re-checked live, not cached from first install.

---

## §3. Acceptance criteria

1. A user with a configured Active Brain (any provider) and network access, asking URI to fetch a real URL/perform a web search, receives a Brain-authored narrative reply describing what was found — not the generic fallback string — verified with a real end-to-end request against a running backend + configured provider.
2. A user with **no** provider configured sees an honest, actionable message (or the Phase D onboarding screen, if reached before their first chat) — never the unexplained `'URI finished processing this request.'` string with no indication of why.
3. `ProvidersScreen`'s content renders and is visible on both wide (master-detail) and compact layouts — widget test asserts provider card content is present and non-empty; manual `flutter run -d windows` visual confirmation before sign-off.
4. `flutter analyze` stays at 0 issues; full `flutter test` suite passes (baseline 118/118 plus any new tests added by this milestone).
5. Full Python regression suite (`python -m unittest discover -p "test_*.py"`) passes with no new failures beyond any pre-existing, independently-bisected failure already on record (see `M23_STATE.md`'s disclosed pre-existing failure).
6. AST-import boundary tests (`test_capability_authority_boundary.py` and sibling graph/authority tests) still pass unmodified — proving Phase A's role-resolution change does not grant the Brain any new authority, only a working invocation path for the role it already had.
7. No protected file (`dispatcher.py`, `approval_gate.py`, `approval_store.py`, `capability_registry.py`, `capability_resolver.py`, `capability_grants.json`, `provider_registry.py`, `provider_keys.py`) is touched by Phase A-D, except `model_roles.py` (Phase A item 1, the one deliberate, narrowly-scoped role-resolution fix this plan calls for).
8. `orchestrator.py`'s standing "must never grow" line-count rule is respected — any new logic (e.g. `narrative_unavailable_reason` derivation) lives in a separately-callable helper, not inline growth of the file.

---

## §4. What this plan explicitly does NOT do

- Does not change ADR-018 or any approval/authority/capability boundary.
- Does not build a real pluggable vector/graph memory backend (Phase C is the extension point only).
- Does not build Hermes' "Gateways" (Local/Cloud/Remote/SSH gateway registration, OS keychain, diagnostics log launcher) — the User's request lists this as a reference UI point, but no corresponding backend gateway concept exists in URI today and none of the 5 audit questions the User asked require it; recommend it as a candidate for a future, separately-scoped milestone rather than folding an unscoped new subsystem into this repair-focused one.
- Does not change how URI's user-facing reply text is authored (still Brain-authored narrative, or the one accepted deterministic-fallback exception) — consistent with the standing USER/BRAIN/URI interaction-loop architecture.
