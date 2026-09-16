# M31 — Model & Brain UX + Subscription Auth Transport — Implementation Plan

**Status:** ACCEPTED (see History Log for auto-approval basis)
**Visual/Architecture Authority & Final Auditor:** Claude
**Primary Implementer:** Codex (routed via Antigravity)
**Development Loop Coordinator:** Antigravity
**Sibling state file:** `docs/plans/M31_STATE.md`

---

## 1. Objective

Resume and complete the Model & Brain UX milestone against the two User-approved Figma frames, covering provider connection UX, API-key and local provider functionality, dynamic model discovery, verified-model inventory, Active Brain selection, Auto routing, conversation-level model override, the chat model selector, attachment control, and dynamic fallback configuration, so that:

- Only discovered **and verified-usable** models are ever selectable anywhere in the product.
- Provider connection (Design 02) and the chat model selector (Design 04) match the approved frames.
- API-key providers (OpenAI, Anthropic, Gemini, Groq, OpenRouter) and local providers (Ollama, LM Studio) are fully functional Brain providers.

**Milestone boundary (direct User instruction, 2026-09-15):** this milestone (M31) does **not** implement direct subscription-backed Brain access for any provider. It builds the `subscription_oauth` transport seam (§7) so the schema/API shape never needs to change later, and documents the sourced feasibility findings (§6). Actually implementing a direct subscription-backed Brain provider — for whichever of OpenAI/Claude/Gemini opens a genuine third-party route first — is explicitly the scope of the **next milestone (M32 — Direct Subscription-Backed Brain Providers)**, not this one. This is a scope boundary, not an abandonment of the requirement (§17 records it as deferred, not dropped).

## 2. Approved Design Authority (Figma)

File: `URI — Model & Brain UX Flow` (only 2 frames exist in the file; both are in scope, nothing else is).

**Frame `02 — Connect Provider` (node 1:71)** — inspected live, content transcribed verbatim:
- Header: "Connect Provider" / "Authentication method comes first; URI only shows provider-specific options."
- Three equal-hierarchy cards, each with a tag and a "Continue" button:
  1. **Sign in with subscription** — "ChatGPT / Codex, Claude when supported" — tag "OAuth / account session"
  2. **Connect with API key** — "Groq, OpenAI API, Anthropic API, Gemini API, OpenRouter" — tag "Encrypted credential"
  3. **Run locally** — "Ollama, LM Studio" — tag "Local endpoint"
- "What happens after connection" box: "URI validates the selected provider, discovers the models available to your account, then verifies which models can actually run." Steps: 1. Authenticate/validate 2. Discover available models 3. Verify model access 4. Make models available to Brain & chat selector.
- "Fallback routing" box: "Fallbacks populate only from models URI has actually discovered and verified." Slots: Primary Brain / Fallback 1 / Fallback 2, "Edit routing" action. Footer: "Models are discovered dynamically from connected providers. A model is selectable only when URI can verify it is usable."

**Frame `04 — Chat Model Selector` (node 1:201)** — inspected live, content transcribed verbatim:
- Header: "Chat" / "Model choice can be changed from conversation without rewriting global defaults."
- Assistant message: "Good morning. What would you like URI to work on?" / caption "Conversation model: Auto"
- Removable attachment chips above composer (e.g. "hostel_list.xlsx", "email.pdf", each with an "×").
- "Choose model" popover: rows = Auto — best available (Router) / Claude Sonnet (Claude) / GPT-5 family (ChatGPT · Codex) / Gemini Pro (Gemini) / Gemma 4 12B (Local) / Groq Llama (Groq). Verified rows: teal/green dot, full-opacity text. **Groq Llama: dim text + red dot — shown as an example of discovered-but-unverified, not selectable.**
- Composer: attach icon, input "Ask URI anything…", model-selector chip (e.g. "Auto"), voice icon, Send. Caption: "Composer controls: attach files • switch conversation model • voice • send."

No Figma prototype wiring was built or is being built (explicit non-goal, this is architecture/UX inspection only).

## 3. Governing UX Rules (as directed)

1. Only discovered + verified-usable models are selectable in chat.
2. Design 02 = provider setup / pre-connection state.
3. Design 04 = post-connection chat state.
4. Auth-method detail stays in provider settings, not the chat selector.
5. Internal "Router" wording → user-facing "URI Auto" / "Auto routing".
6. The composer model selector is the single interactive model selector.
7. Connection methods have equal visual hierarchy unless the UX skill documents a reason otherwise (it does not — see §13).
8. Runtime model lists and fallback options come from backend truth, never hard-coded placeholders.

## 4. Verified Evidence: Current Architecture

Gathered by direct `Read`/`Grep` of the real source (not a prior plan's claims):

**Flutter (`uri_ui/lib`):**
- `screens/settings/providers_screen.dart` — existing settings-style provider list (Accounts/API Keys, Local Models, Custom Endpoints chips; per-provider card with model dropdown, key dialog, config dialog, Active Brain confirm). Functional but **does not match Design 02's 3-card equal-hierarchy layout, has no "what happens after connection" explainer, and has no fallback-routing UI at all.**
- `screens/ask/ask_uri_screen.dart` — composer (`_ComposerBody`, line ~254) row is `[attach][text field][mic][send]`. **No model-selector control exists anywhere in the composer — confirmed by grepping the whole file for "model"/"Model": zero hits outside the attachment-adjacent code.** Attachment chips **already exist and already match Figma**: `_AttachmentStrip` (line 413) renders a `Chip` per attachment with `deleteButtonTooltipMessage: 'Remove attachment'` (line 432-433) above the input row (line 317-321) — this is a GAP-free area.
- `services/app_state.dart` — holds `activeBrain`/`activeBrainProvider` (global default) only. No conversation-level override concept, no "Auto" concept, no fallback-chain concept anywhere in the file.
- `services/uri_client.dart` — `ProviderEntry` (line 724) mirrors the backend's `GET /providers` shape exactly (`installedModelIds`, `models`, `activeBrain`, `activeModel`); no `verified` field exists yet. `ActiveBrainInfo` (line 704) is the only "brain selection" concept — single global slot, no fallback slots.
- Grep of all of `uri_ui/lib` for `Router`/`"Auto"`/`'Auto'`: only one unrelated hit (a provider-preference question string). **The rename requirement (rule 5) is satisfied by writing the new UI with "URI Auto"/"Auto routing" from the start — there is no existing "Router" wording to rename.**

**Backend (`uri_core`):**
- `core/provider_registry.py` — `PROVIDER_CATALOGUE` (line 92) is a static list of `ProviderDescriptor`/`ModelDescriptor`. This is the **"discovered" layer only** — it is compiled into the binary, not queried live, except for Ollama.
- `app/server.py` `GET /providers` (line 2904) — for `ollama`, returns a **real, live, verified** `installed_models` list (`OllamaProvider.list_installed_models()`, line 2987). For every `openai_compatible` adapter, `available` (line 2953-2966) is a **reachability probe that deliberately never uses the stored key** ("No api_key for the health-check probe - just connectivity", line 2962) — so today there is **no per-model "verified usable with this user's real key" signal for any cloud provider.** This is the core gap behind rule 1.
- `core/model_providers/base.py` — `ModelProvider.describe()` (line 196) contract: cheap, timeout-bounded, **must never call `complete()`**, must never raise. This is the correct, existing extension seam for both the new verify action (§7) and the new subscription-harness auth-state probe (§6) — it does not need to change shape, only to be implemented by new subclasses.
- `core/model_router.py` — `ModelRouter._ordered_candidates()` (line 121) is role-config-driven (`primary` role config + always-included `ollama`); its own docstring states plainly: **"User declared fallback order (reserved slot — no per-user fallback config yet)"** (line 73). There is no Primary Brain / Fallback 1 / Fallback 2 concept anywhere in the backend today — it must be built new (§8).
- `app/server.py` `class AskRequest` (line 787) has exactly two fields, `session_id` and `text`. **No model-override field of any kind exists on `/ask` today** — confirms rule 3/6 (conversation-level model override) is a full gap (§9).
- `app/server.py` `GET /connections` / `/connections/credentials` / `/connections/{id}/authorize` (lines 2097-2609) are **Google Workspace (Gmail/Drive) OAuth only** — unrelated to LLM-provider subscription auth. Confirms "Sign in with subscription" (Design 02, card 1) has **zero existing backend support** of any kind.
- `uri_core/core/turn_state.py`, `core/conversation_history.py` (`ConversationTurn`, `ConversationHistoryStore.append_turn`, line 161) are the correct place to persist which model actually served a turn, for the "Conversation model: X" caption to show truth rather than intent.
- Standing architectural rule (memory, verified against `orchestrator.py`'s own guard comment): **`orchestrator.py` must never grow.** All new routing/override logic in §8-9 is placed in `model_router.py` and a new small carrier, never in `orchestrator.py`.

## 5. Brain Providers vs. Development Agents — Layer Separation (fixed architectural rule)

**Direct User correction, 2026-09-15, supersedes this plan's original §5-§6 draft below.** Two layers must never be conflated:

- **URI Brain = direct model providers** used for chat/reasoning: local (Ollama/LM Studio), API-key (OpenAI, Anthropic, Gemini, Groq, OpenRouter), and — as a first-class future goal, not this milestone — direct subscription/account/OAuth-backed access to OpenAI/Claude/Gemini models, **only through a mechanism each vendor officially exposes to third-party applications for that purpose.**
- **Development agents = Claude Code, Codex CLI, Antigravity**, used only to build URI itself. **URI's Brain runtime must never shell out to `claude` or `codex` as a substitute for direct model access.** This is a fixed rule, not a preference — Claude Code and Codex CLI are explicitly out of the Brain provider abstraction.

The original draft of this section proposed a `SubscriptionHarnessProvider` that would invoke `codex exec`/`claude -p` as URI's own Brain — the User reviewed this and explicitly rejected it as merging the two layers. It is recorded in the History Log as a corrected-and-superseded conclusion, not silently removed.

## 6. Direct Subscription-Backed Brain Access — Feasibility Findings & Seam

Researched live (WebSearch, sourced) on 2026-09-15. The question that matters for the Brain layer is narrower than "does an official CLI exist" — it is **"does the vendor expose a direct, third-party-usable account/session/OAuth mechanism a Brain provider could authenticate through, without impersonating or subprocessing that vendor's own first-party tool?"**

| Provider | First-party subscription surface | Direct third-party Brain-access route today | Decision this milestone |
|---|---|---|---|
| OpenAI / Codex | `codex login` (ChatGPT OAuth) — confirmed to ship **only inside Codex's own tooling** as of April 2026 ([developers.openai.com/codex/auth](https://developers.openai.com/codex/auth)) | None documented for third-party apps | **Not buildable now.** Keep the `subscription_oauth` transport seam on the `openai` provider descriptor (§7); implement only when/if OpenAI publishes a third-party OAuth client registration path for ChatGPT-subscription-backed model access. |
| Anthropic / Claude | `claude login` (subscription OAuth) — Anthropic's own Authentication and Credential Use policy explicitly restricts this **to Claude Code and claude.ai** since Jan–Feb 2026 | None — explicitly policy-blocked | **Not buildable now.** Seam only, same as above, on the `anthropic` provider descriptor. |
| Google / Gemini | Consumer "Login with Google" for individual/AI Pro/AI Ultra **deprecated June 18 2026** ([developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals)); Enterprise GCP-project OAuth still exists but requires a GCP project, not a fit for URI's individual-user model | None for individual users | **Not buildable now.** Seam only, on the `gemini` provider descriptor. |

**Result: no direct subscription-backed Brain transport is officially available for any of the three providers today.** This does not remove the product requirement — it is recorded as a real, sourced architecture finding, the seam is built (§7), and the requirement stays open for a future milestone if any vendor opens a third-party path.

**Explicit non-goals, this milestone, per direct User instruction:**
- URI's Brain never shells out to `claude` or `codex` as a model-serving mechanism, under any circumstance.
- URI never performs unofficial OAuth-token capture/reuse, browser-cookie scraping, or undocumented/private-endpoint calls for any of the three providers.
- Development agents (Claude Code, Codex, Antigravity) remain fully available as the existing AO-4 build-process layer — completely unrelated to, and never wired into, the Brain provider abstraction.

## 7. Architecture: Brain Provider Transport Seam

```
ModelProvider (existing ABC, base.py) — UNCHANGED shape, no subprocess-harness subclass
 ├─ OllamaProvider (existing)
 └─ OpenAICompatibleProvider (existing — all API-key adapters)
```

- `provider_registry.py`: `ProviderDescriptor` gains `auth_transports: List[str]`, a subset of `{"api_key", "local", "subscription_oauth"}`. Every existing catalogue entry is annotated with its real, already-supported transports (`ollama`/`lm_studio` → `["local"]`; `openai`/`anthropic`/`gemini`/`groq`/`openrouter` → `["api_key"]`), plus `"subscription_oauth"` is *declared but unimplemented* on `openai`, `anthropic`, and `gemini` — a schema-ready seam, not a working feature, so a future direct OAuth implementation slots in without another catalogue/API shape change.
- No new `ModelProvider` subclass exists this milestone for subscription access. If a vendor later opens a real third-party OAuth path, the implementation is a new `ModelProvider` subclass that performs that vendor's own documented OAuth flow directly (token exchange it owns and stores itself, scoped to that use) — never a subprocess wrapper around another application.
- `provider_keys.py` is untouched.

## 8. Verified-Model Concept (rule 1)

- `GET /providers` response gains an explicit `verified: bool` per model entry, distinct from mere presence in the catalogue/`installed_models`:
  - `ollama`: `verified` = already-live `installed_models` membership (rename/expose, no behavior change).
  - `openai_compatible` (API-key adapters): `verified` comes from §8a below — **not** from the existing keyless `available` probe, which stays as the free/cheap reachability signal it already is.
  - `subscription_oauth` (§6-7, seam only): reports `verified: false` unconditionally until a real implementation exists — never fabricated.
- **§8a — `POST /providers/{provider_id}/verify`**: a new, explicit, user-triggered endpoint (never called implicitly by a passive `GET`, to avoid spending the user's real quota/rate limit on every poll). Performs one minimal real call using the stored key, writes a short-lived (~5 min) verified-set cache consulted by `GET /providers` and by the model-selector list. This is the concrete backend behind Figma's own step 3, "Verify model access."
- Both the connect-screen fallback pickers (§9) and the chat composer's "Choose model" popover (§12) must filter to `verified == true` only — this is the single source of truth rule 1 depends on.

## 9. Fallback Routing (Primary Brain / Fallback 1 / Fallback 2)

- New per-user structure, `FallbackRoutingStore` (new module, same `user_scoped_path` pattern as `ProviderConfigStore`): `{primary: {provider_id, model} | null, fallback_1: {provider_id, model} | "auto" | null, fallback_2: {...} | null}`.
- `GET /providers/fallback-routing`, `PUT /providers/fallback-routing` — `PUT` validates every populated slot against the current verified set (§8a) and rejects (400) an unverified selection, matching the Figma caption verbatim.
- `"auto"` is a valid `fallback_1` value meaning "URI Auto" — `ModelRouter._ordered_candidates()` already holds the real fallback logic (primary role config → `ollama`); this milestone does **not** rewrite `ModelRouter`'s core algorithm. It gains one new, optional input consulted first: when a user has saved fallback-routing config, that ordered list is tried ahead of the existing static role-config chain; when no config exists (the common/legacy case), behavior is byte-for-byte unchanged — a required regression guard (§16a).

## 10. Conversation-Level Model Override + Auto Routing (rules 3, 6)

- `AskRequest` (server.py:787) gains an optional field: `model_override: Optional[dict] = None` — `{"provider_id": ..., "model": ...}` or the literal `"auto"`. `None`/omitted preserves every existing caller's behavior unchanged (additive, non-breaking).
- Threaded as a small new carrier (not added to `orchestrator.py` — respects the standing "orchestrator.py must never grow" rule) alongside the existing `principal` argument into the already-inventoried `get_router().attempt(role=..., principal=..., ...)` call sites: `decision_engine.py:547`, `model_reasoning_adapter.py:352`, `provider_semantic_interpreter.py:163`, `response_drafting.py:285`, `document_composer.py:122`. Each already accepts `principal`; the override rides alongside it rather than becoming a new parameter fanned out everywhere.
- `ConversationHistoryStore.append_turn` persists which provider/model **actually** served each turn (the real outcome, from `ModelResponse.provider`/`.model` — never the merely-requested value), so the Flutter "Conversation model: X" caption shows truth.
- Selecting a model in the composer only ever sets this per-session override for subsequent turns in that session — it never mutates the global Active Brain (`ProviderConfigStore.set_active_brain`, unaffected).
- "URI Auto" / "Auto routing" is the only user-facing name. `ModelRouter` stays the internal Python class name (never surfaced). Live-acceptance testing (§16c) includes an explicit grep for the literal string "Router" in any user-facing Flutter text.

## 11. Flutter: Design 02 — Connect Provider screen

- `providers_screen.dart` gains a new top section (new widgets, existing per-provider settings list stays reachable below/behind it — Design 02 is the entry/setup surface, it does not delete the working key-management/endpoint-config/Active-Brain affordances already there):
  - Three equal-size `ConnectionMethodCard` widgets — Subscription / API key / Local — each with its Figma tag and a "Continue" action.
  - The **Subscription** card lists OpenAI, Claude, and Gemini, each showing an honest **"Not currently available — no officially supported direct connection exists yet"** state (§6) rather than a working Continue button. Same size/position as its siblings (§14) — a state difference, never a hierarchy difference. This is not a dead end: the card explains *why* (policy/deprecation, per §6) so the user understands it is a real, sourced finding, not a bug.
  - "What happens after connection" 4-step explainer (Figma copy, verbatim), shown under the API-key and Local cards, which are the two working paths this milestone.
  - New `FallbackRoutingCard`: Primary Brain / Fallback 1 / Fallback 2 + "Edit routing", opening a picker constrained to `verified == true` models only (§8, §9), Figma caption reused verbatim.

## 12. Flutter: Design 04 — Chat composer model selector

- New `ModelSelectorChip` in `_ComposerBody`'s `Row` (`ask_uri_screen.dart`, before the Send button) — this is **the single interactive model selector** in the product (rule 6); nothing else gets one.
- Tapping opens `ChooseModelPopover`: lists `verified == true` models only, grouped/labeled by provider family. A discovered-but-unverified model (if ever surfaced at all) is rendered with **both** a dim red status dot **and** explicit trailing text such as "Not verified" (per the UX-skill accessibility finding: never convey status by color alone) and is disabled (reduced opacity, non-interactive — per the UX-skill "Disabled States" guideline: never the same style as an enabled row).
- Header caption "Model choice can be changed from conversation without rewriting global defaults." (verbatim) above the popover list.
- Selecting a model sets the session-scoped override (§10) only.
- Turn/message area gains a small "Conversation model: <label>" caption reflecting the **real, persisted** value for that turn (§10), not the current composer selection.

## 13. Attachment chips

Already implemented and already matches Figma (`_AttachmentStrip`, `ask_uri_screen.dart:413-445`; removable `Chip` with an "×"/delete affordance above the input row). This is a **GAP-free area** — verify visual treatment against the approved frame during Antigravity's pass; do not rebuild.

## 14. Equal Visual Hierarchy

The UX skill (`ui-ux-pro-max`) was queried for a documented exception to equal-hierarchy connection cards and returned none. All three Design-02 cards stay identical in size/weight/button treatment. The only allowed variation is a **state** difference (the Subscription card's honest not-available state, §11) at the same size and position as its siblings — never a hierarchy difference.

## 15. Backend/API Change Summary

| Endpoint | Change |
|---|---|
| `GET /providers` | add `verified: bool` per model; add `auth_transports` per provider (§7) |
| `POST /providers/{provider_id}/verify` | **new** — explicit real-key verification, short-lived cache |
| `GET /providers/fallback-routing` | **new** |
| `PUT /providers/fallback-routing` | **new** — rejects unverified slot selections |
| `POST /ask` (`AskRequest`) | add optional `model_override` field — additive, non-breaking |

## 16. Tests

### 16a. Backend (pytest)
- `ModelRouter`: fallback-routing config takes precedence when present; **existing role-config-only behavior is byte-for-byte unchanged when absent** (regression guard — this is the highest-risk regression surface in the whole plan).
- `/providers/{id}/verify`: rejects when unconfigured; succeeds only on a real minimal call; cache TTL behavior.
- `/providers/fallback-routing` `PUT`: rejects an unverified slot selection.
- `AskRequest.model_override`: `None` preserves existing `/ask` behavior exactly (regression guard); explicit override reaches the correct `attempt()` call; `"auto"` resolves through the existing role-config chain.
- `subscription_oauth` transport seam: `GET /providers` reports `verified: false` and an honest unavailable state for `openai`/`anthropic`/`gemini`'s subscription transport — never a fabricated connected state; no code path anywhere in `uri_core` invokes a `claude` or `codex` binary (explicit regression check — grep the backend for `subprocess`/`Popen` calls referencing either binary name and assert none exist outside the development-agent tooling, which is entirely outside `uri_core`).

### 16b. Flutter (widget/integration)
- Connect-provider screen: three equal cards render with correct tags; Subscription card shows the honest not-available state for all three providers; Continue routes correctly for API-key and Local.
- Fallback routing card: only verified models selectable; Edit routing round-trips through the new endpoints.
- Composer model selector: chip shows current value; popover lists verified models only; an unverified row (if any) is disabled with dot **and** text; selecting updates conversation-scoped state only, never the global Active Brain.
- "Conversation model: X" caption reflects the actual served model from history.
- Existing attachment-chip tests stay green (regression guard, §13).
- New lint/test asserting no literal "Router" string reaches any widget's visible text.

### 16c. Live acceptance (User-run, per the live-verification gate revision)
- Connect Ollama (existing baseline), connect one API-key provider, confirm the Subscription card shows the honest unavailable state for OpenAI/Claude/Gemini rather than a working-looking button.
- Confirm the chat composer selector only ever offers verified models against the real running backend — no placeholder/hardcoded list (grep `uri_ui/lib` for hard-coded model-name literals as an explicit regression check, rule 8).

## 17. Explicitly Deferred / Not Building

- Direct subscription-backed Brain access for OpenAI, Claude, and Gemini — no officially supported third-party route exists today for any of the three (§6); the `subscription_oauth` transport seam is built (§7) so it never needs a schema change later. **This is a milestone-boundary deferral, not an abandonment**: implementation is explicitly the scope of the next milestone, M32 — Direct Subscription-Backed Brain Providers (§1), to be planned once this milestone closes, re-checking each provider's official-support status at that time rather than reusing this milestone's dated findings unverified.
- Claude Code / Codex CLI / Antigravity as URI's Brain runtime — **explicitly rejected architecture**, corrected by direct User instruction 2026-09-15 (§5). These remain the existing AO-4 development-agent layer only, never wired into the Brain provider abstraction.
- Any Figma prototype wiring.
- Any change to `orchestrator.py`'s own body (standing rule).
- Rewriting `ModelRouter`'s core candidate algorithm — it gains one new optional input (§9), it is not replaced.

## 18. Acceptance Criteria (final-audit checklist)

- [ ] Only `verified == true` models are ever selectable in the composer popover or the fallback-routing pickers, end to end against a real backend.
- [ ] Design 02 renders three equal-hierarchy cards, the 4-step explainer, and the fallback-routing box, matching the approved frame's content and structure.
- [ ] Design 04's composer has exactly one interactive model selector; no other model-selection control exists elsewhere in chat.
- [ ] No literal "Router" string is user-facing anywhere in the Flutter app.
- [ ] The Subscription card shows an honest, sourced "not currently available" state for OpenAI, Claude, and Gemini alike — never a working-looking fake button, and never silently omitted without explanation.
- [ ] No code path in `uri_core` (Brain runtime) invokes a `claude` or `codex` binary, or any other development-agent tool, under any circumstance (code-review confirmed — this is the single most important correctness check in this milestone, per the direct User correction in §5).
- [ ] `ModelRouter`'s existing behavior is unchanged for every user with no saved fallback-routing config (regression-tested).
- [ ] `/ask` behavior is unchanged for every caller that omits `model_override` (regression-tested).
- [ ] Attachment chips remain unregressed.
- [ ] Full regression suite run, results compared against the standing baseline (per Evidence Integrity Rules — only `COMPLETED_WITH_RESULT` evidence counts).

## 19. Loop Sequencing

Claude architecture (this document, ACCEPTED) → Antigravity routes implementation to Codex → Codex implements backend (§7-10, §15) + Flutter (§11-14) + tests (§16a-b) → live backend/UI verification (§16c, User-run, per the 2026-09-12 live-verification gate revision) → Antigravity visual/UX review against Figma frames 1:71/1:201 → Claude final architectural audit (bounded-fix authority for in-scope defects; substantial remediation is defined by Claude and routed back through Antigravity) → Codex repair if needed → full regression → commit/push only after Claude's final `VERIFIED`, per standing release authority.

Per direct User instruction, this loop proceeds without a further approval checkpoint unless a genuine blocker (architecture, security, destructive change, or an unresolvable requirement) is found.

---

## History Log

- **2026-09-15 — DRAFT.** Figma frames `02 — Connect Provider` (1:71) and `04 — Chat Model Selector` (1:201) inspected live via Claude-in-Chrome; content transcribed verbatim into §2. Current-architecture evidence gathered by direct `Read`/`Grep` of `uri_ui/lib` and `uri_core` (§4) — not by trusting any prior plan document's claims. Subscription-transport feasibility researched live (WebSearch, sourced) after the User's initial framing assumed direct OAuth reuse was available; research showed it is not, for any of the three providers, and surfaced this as a genuine architecture/policy finding.
- **2026-09-15 — Superseded draft (recorded, not silently deleted).** An intermediate version of §5-§9 proposed a `SubscriptionHarnessProvider` that would invoke `codex exec`/`claude -p` as URI's own Brain-serving mechanism. The User reviewed this and issued a direct, fixed architectural correction: Brain providers (direct model access for chat/reasoning) and development agents (Claude Code/Codex/Antigravity, used only to build URI) must never be conflated, and URI's Brain must never shell out to either CLI as a substitute for direct model access. §5-§10 were rewritten accordingly to the current text.
- **2026-09-15 — Milestone boundary set.** User directed that M31 stay scoped to the approved Model & Brain UX plus API-key/local provider functionality, with direct subscription-backed Brain transport moved to the immediately following milestone (M32), while the `subscription_oauth` seam is preserved now. §1 and §17 updated to name M32 explicitly and frame this as a scope boundary rather than a dropped requirement.
- **2026-09-15 — ACCEPTED.** Auto-approved per the uri-ao4 standing rule (2026-09-11 revision, `ORCHESTRATION.md` §1.5): this is a routine engineering plan built from verified repository evidence; the architecture/security-boundary question that arose (Brain vs. development-agent layer separation) was resolved by explicit, direct, and corrected User instruction in this session rather than assumed — so no further approval gate applies. Proceeding to Antigravity handoff.
