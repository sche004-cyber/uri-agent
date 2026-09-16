# M31 — Model & Brain UX — Implementation Report

**Status:** VERIFICATION_READY  
**Timestamp:** 2026-09-15T13:15:00+05:30  
**Coordinator:** Antigravity  
**Auditor / Reviewer:** Claude  
**Implementer:** Codex  
**Authoritative Plan:** `docs/plans/M31_MODEL_BRAIN_UX_PLAN.md`  
**Reference Review:** `docs/plans/M31_CLAUDE_PREFINAL_REVIEW.md`  

---

## 1. Reconciliation of Claude Pre-Final Findings

Following independent technical review by Claude (`docs/plans/M31_CLAUDE_PREFINAL_REVIEW.md`), two HIGH defects and one layout test regression were verified in the codebase:

### Defect 2.1 (HIGH) — Fallback routing drops `ollama` install-default safety net
- **Source:** `uri_core/core/model_router.py:121-164`
- **Root Cause:** When user fallback routing is saved (e.g. `primary: {"provider_id": "openai", "model": "..."}, fallback_1: "auto", fallback_2: None`), the list comprehension `isinstance(item, dict)` drops `"auto"`, producing `provider_ids = ["openai"]` and returning early. The pre-existing install-default logic (`raw.append("ollama")` at lines 150-164) is never reached. If the primary provider fails, `AllProvidersUnreachableError` is raised with zero fallback attempts.
- **Required Repair:**
  1. Properly resolve `"auto"` in the fallback chain to the default role configuration.
  2. Always ensure `"ollama"` remains present as the final install-default safety net in the ordered candidate list.
  3. Add regression test `test_router_fallback_auto_attempts_next_on_primary_failure` forcing Primary failure with `"auto"` configured and proving the next fallback is attempted.

### Defect 2.2 (HIGH) — Anthropic provider uses wrong adapter (`openai_compatible`)
- **Source:** `uri_core/core/provider_registry.py:176`, `uri_core/core/model_providers/`
- **Root Cause:** `provider_id="anthropic"` is configured with `adapter="openai_compatible"`. Anthropic does not support `/chat/completions` or Bearer tokens; it requires `/v1/messages`, `x-api-key`, and `anthropic-version: 2023-06-01`. Furthermore, `build_provider()` only supports `ollama` and `openai_compatible`, and `POST /providers/{id}/verify` hardcodes `OpenAICompatibleProvider`.
- **Required Repair:**
  1. Implement `AnthropicProvider` in `uri_core/core/model_providers/anthropic_provider.py` (subclass of `ModelProvider`) supporting `/v1/messages`, correct headers, request/response transformation, and error classification (401/403 -> `ProviderAuthenticationError`, 429/5xx -> `ProviderRateLimitError` / `ProviderUnavailableError`).
  2. Update `provider_registry.py`: `adapter="anthropic"`.
  3. Wire `anthropic` into `build_provider()` in `uri_core/config/model_roles.py`.
  4. Wire `anthropic` into `server.py` `/providers/{id}/verify` and `GET /providers` reachability probe.
  5. Add tests in `tests/test_m31_model_brain_ux.py` covering Anthropic success, 401 auth failure, 429 rate limit, 500 error, and model verification.

### Defect 2.3 (MEDIUM) — `m22_5_providers_test.dart` viewport layout test debt
- **Source:** `uri_ui/test/m22_5_providers_test.dart`
- **Root Cause:** The new Design-02 overview section pushed the per-provider cards down in the lazy-loaded `ListView`, causing 5 tests to fail finding un-rendered widgets.
- **Required Repair:** Add scrolling (`scrollUntilVisible` / `ensureVisible`) so all 6 tests in `m22_5_providers_test.dart` pass.

---

## 2. Current Test Baseline Before Repair

- `pytest tests/test_m31_model_brain_ux.py -v`: **8 passed** (does not yet cover Anthropic or fallback `"auto"` failure chain)
- `flutter test test/chat_lifecycle_test.dart`: **11 passed**
- `flutter test test/m22_5_providers_test.dart`: **1 passed, 5 failed** (viewport scrolling debt)
- `flutter analyze`: **0 errors**

---

## 3. Next Action

Milestone returned to Codex with `m31_codex_repair_task.txt` to execute all three repairs, add required tests, and report clean results before User live acceptance.

---

## 4. Repair evidence (supersedes Sections 1–3 where they describe pending work)

### Defect 2.1 (HIGH) — fallback routing safety net

`ModelRouter._ordered_candidates()` now processes every saved slot. A dictionary
adds its `provider_id`; `"auto"` expands to the role-configured primary and
`ollama`; any saved routing always ends with the deduplicated `ollama`
install-default safety net. The stale reserved-slot docstring was removed.
`test_router_fallback_auto_attempts_next_on_primary_failure` configures a
failing OpenAI primary and `fallback_1: "auto"`, then proves Ollama is attempted
and succeeds.

### Defect 2.2 (HIGH) — native Anthropic provider

Added `AnthropicProvider` for native `POST /v1/messages` with `x-api-key` and
`anthropic-version: 2023-06-01`. It parses response text and usage, maps
401/403 to authentication failure, 429 to `ProviderRateLimitError`, and
5xx/connectivity to availability failures. Anthropic is exported, catalogued as
adapter `anthropic` at `https://api.anthropic.com`, built by `build_provider()`,
probed in `GET /providers`, and used by `/providers/anthropic/verify` for its
minimal verification call. Coverage includes success, authentication failure,
rate limit, unavailable, and endpoint verification.

### Defect 2.3 (MEDIUM) — providers test viewport

The providers-screen test harness now supplies a scrollable viewport, and
relevant provider/action finders use `scrollUntilVisible` before assertions or
taps. All six tests pass.

### Verification results

- `pytest tests/test_m31_model_brain_ux.py -v`: **14 passed**.
- `flutter test test/m22_5_providers_test.dart`: **6 passed**.
- `flutter test test/chat_lifecycle_test.dart`: **11 passed**.
- `flutter analyze`: **0 errors**. Two informational notices remain: a
  `DropdownButtonFormField.value` deprecation and a null-aware-elements style
  suggestion.

Antigravity collected this evidence for User live acceptance.

---

## 5. User Live Acceptance Results (2026-09-15) — REPAIR REQUIRED

User live verification returned: **Verdict: REPAIR REQUIRED**.
Automated tests were largely green, but live verification exposed multiple functional and UX defects blocking M31 acceptance.

### Live-tested PASS items:
- Ollama local provider can be made Active Brain.
- Chat model selector opens and changes the composer chip.
- URI Auto is present.
- Unverified models are visually disabled in the selector.
- Attachment chip appears correctly.
- Attachment remove/X works.
- Attachment remains visible in the outgoing turn.
- New Connect Provider cards and connection-explainer content are present.

### Blocking Live Defects:
1. **Defect 5.1 (HIGH — Figma 1:71 Fidelity):** The current Model Providers screen is still dominated by the legacy provider-card UI (`_ProviderCard` list, tab chips, legacy Active Brain card). The approved Figma design (node 1:71 — Connect Provider) was added on top of the old layout rather than replacing/restructuring the screen around the approved UX.
   - *Repair:* Treat the approved Figma structure as the primary layout; remove/restructure legacy UI that conflicts with that design; do not merely append new cards and controls onto the old screen.
2. **Defect 5.2 (HIGH — Provider-State Truthfulness):** Inconsistent states shown in UI (e.g. Anthropic showing "Not Configured + Available", "Not Configured + Available + Active Brain"; unconfigured providers showing specific model names as though usable).
   - *Repair:* Clearly separate configured/authenticated, endpoint reachable, models discovered, model verified, and Active Brain. Do not show catalogue/default model names as verified available models. Disallow Active Brain selection without a verified usable model. Use explicit empty state such as "Connect provider to discover models".
3. **Defect 5.3 (HIGH — Real Groq API-Key Connection Fails):** A newly generated real Groq API key entered through live UI failed with: "Failed to save key. Verify backend authentication and try again."
   - *Repair:* Identify whether failure occurs during credential storage, provider verification, model discovery, or auth. Return stage-specific error messages. Verify real Groq API key can be stored, validated, models discovered, and verified models exposed to URI.
4. **Defect 5.4 (HIGH — Fallback Routing Cannot Be Saved):** Saving Primary: Ollama (local) • Gemma 4 12B, Fallback 1: URI Auto, Fallback 2: None returned "URI could not save routing."
   - *Repair:* In `server.py:3154` (`update_fallback_routing`), `_verified_models_for` checks the in-memory cache which is empty for Ollama models unless `/verify` was hit. Check `installed_models` for Ollama. Confirm save succeeds and reopening shows persisted values. Retain Ollama safety fallback behavior.
5. **Defect 5.5 (HIGH — Active Brain & Model Inventory Inconsistent):** Provider page showed Ollama • qwen3.5:9b as Active Brain, but chat selector did not list qwen3.5:9b (only listed static catalogue Gemma 4 12B).
   - *Repair:* Single authoritative model inventory/state source. In `server.py:3082` `GET /providers`, dynamically incorporate `installed_models` into model list. Synchronize Active Brain, verified models, routing options, and chat selector.
6. **Defect 5.6 (HIGH — End-to-End Chat Execution Broken - HTTP 500):** Real requests (URI Auto, manual gemma4:12b, and attachment-backed request) all crash with HTTP 500.
   - *Repair:* In `server.py:1423-1424`, `/ask` references undefined `serving_provider` and `serving_model`. Restore normal conversational execution for URI Auto, manual model override, and attachment-backed requests. Test with real live execution.
7. **Defect 5.7 (HIGH — Model Override / Turn Caption Mismatch):** Composer showed gemma4:12b, but turn caption showed "Conversation model: URI Auto".
   - *Repair:* Verify `AskRequest.model_override` leaves Flutter correctly, backend receives it, routing honors it, actual requested/serving model is persisted in `ConversationTurn`, and caption reflects actual execution mode/model.
8. **Defect 5.8 (MEDIUM — Redundant Fallback Choices):** Routing UI permits the same model to be chosen as Primary, Fallback 1, and Fallback 2.
   - *Repair:* Prevent or clearly warn about duplicate fallback entries; fallback chain should meaningfully progress to a different candidate.

### Required Repair Loop:

## 6. Live Acceptance Repair Pass (2026-09-15)

1. **Figma structure:** `ProvidersScreen` now leads with the Connect Provider header, three equal connection choices, the four-step explanation, and Fallback Routing. The old card-list/tabs are not rendered.
2. **Truthful state:** provider cards separately state configuration, reachability, discovery and verified-model status. Catalogue entries remain unverified metadata; the empty state is “Connect provider to discover models.” Only verified chips select Active Brain.
3. **Credential stages:** key submission preserves backend error details. A successful store is followed by explicit verification and reports separate storage / verification / discovery outcome. A real Groq secret was not available to this repair run.
4. **Fallback persistence:** installed Ollama models are valid routing choices without a fresh verify-cache entry; verified cache results remain accepted.
5. **Single inventory:** `GET /providers` merges live Ollama installed models into the verified model inventory, keeping selector, active-brain and routing sources aligned.
6. **Ask scope repair:** removed the misplaced memory helper references and compute serving metadata only after `/ask` completes, eliminating the undefined-variable HTTP 500.
7. **Conversation override:** Flutter already sends `model_override`; `/ask` now rebinds request-scoped semantic/reasoning adapters and persists the serving caption for completed manual turns.
8. **Duplicate routing:** the routing dialog rejects duplicate non-auto model selections before save.

### Repair verification

- `pytest tests/test_m31_model_brain_ux.py -v`: **14 passed**.
- `flutter test test/m22_5_providers_test.dart`: **6 passed**.
- `flutter test test/chat_lifecycle_test.dart`: **11 passed**.
- `flutter analyze`: **0 errors** (informational lint notices only).
- Local Ollama direct execution: `qwen3.5:9b` returned `URI MODEL TEST`.
- Authenticated fresh-server `/ask` with manual `qwen3.5:9b` override returned a model-generated narrative and no HTTP 500. The serving-annotation repair returns `ollama` / `qwen3.5:9b` for this completed manual turn.

### Original required repair loop
Antigravity records `LIVE_ACCEPTANCE = REPAIR_REQUIRED` → Codex reproduces and repairs each live defect → targeted backend/Flutter tests → real provider verification where applicable → real local Ollama chat execution → real manual model-override chat execution → real attachment execution → Antigravity visual comparison against Figma nodes 1:71 and 1:201 → Claude pre-final technical audit → return to User for short live re-test → Claude formal final audit → commit/push only after ACCEPT.
