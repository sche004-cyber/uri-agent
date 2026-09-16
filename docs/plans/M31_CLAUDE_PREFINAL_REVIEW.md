# M31 — Model & Brain UX — Claude Pre-Final Technical Review

**This is NOT the final audit.** No `ACCEPT`/`REPAIR REQUIRED` verdict is issued here, per direct User instruction (2026-09-15): the formal final audit happens only after the User's own live UI/provider acceptance pass. This is a read-only, informational technical review to give the User (and Antigravity/Codex) a head start before that live pass. No code was modified during this review.

**Method:** independent inspection of the actual current source (not the implementation report's claims), plus direct execution of every test suite named in the audit handoff. Every claim below is tagged with how it was established.

---

## 1. Verified complete (independently confirmed, `COMPLETED_WITH_RESULT`)

| Item | Evidence |
|---|---|
| Backend M31 test suite | `./.venv/Scripts/python.exe -m pytest tests/test_m31_model_brain_ux.py -v` → **8 passed**, 0 failed. Matches the implementation report's claim. |
| `flutter analyze` | **0 errors**, 2 pre-existing info-level lints (`deprecated_member_use` in `providers_screen.dart:552`, `use_null_aware_elements` in `http_uri_client.dart:392`, neither M31-introduced logic). Matches report. |
| `chat_lifecycle_test.dart` | Re-run independently: **11 passed, 0 failed** — see §4 for why this contradicts one line in the implementation report. |
| No CLI/harness subprocess calls in `uri_core` | Direct `grep -r "subprocess" uri_core` → **zero matches anywhere in the backend**. Stronger evidence than the shipped test (`test_brain_runtime_does_not_shell_out_to_development_agents`), which only substring-matches `"claude -p"`/`"codex exec"`/`"antigravity"` and would miss a list-form `subprocess.run(["claude", "-p", ...])` call — the shipped test is weak, but the direct grep confirms the actual invariant holds today regardless. |
| `subscription_oauth` schema seam | `provider_registry.py`: `openai`/`anthropic`/`gemini` carry `auth_transports=["api_key", "subscription_oauth"]`; `ollama`/`lm_studio` carry `["local"]`; `groq`/`openrouter` carry `["api_key"]`. No provider subclass implements it — seam only, matches plan §7 exactly. |
| `GET /providers/{id}/verify`, `GET`/`PUT /providers/fallback-routing`, `AskRequest.model_override` | All three endpoints exist and are wired as specced (server.py:3086, 3123, 3131, 795). `PUT /providers/fallback-routing` genuinely rejects an unverified model selection (400) — confirmed by direct code read and the passing `test_fallback_routing_endpoint_rejects_unverified_models`. |
| Composer model selector, popover, verified/unverified presentation, "Conversation model: X" caption | All structurally present: `ask_uri_screen.dart:380` (`_ModelSelectorChip`), `:513` (`detail: model.verified ? provider.displayName : 'Not verified'` — correctly pairs text with the status dot, not color-alone), `turn_card.dart:172` (`'Conversation model: ${turn.servingModel ?? 'URI Auto'}'`). Not yet visually verified against the Figma frame (needs the User's live pass). |
| Attachment chips | `_AttachmentStrip` in `ask_uri_screen.dart:435-455` — same shape as before M31, untouched. Confirmed by direct read. |
| No literal "Router" in Flutter user-facing text | `grep -rniE "\bRouter\b" uri_ui/lib` → zero hits. |
| Design 02 structural pieces | `providers_screen.dart` contains `_ConnectionMethodCard` × 3 ("Sign in with subscription" / "Connect with API key" / "Run locally"), the subscription card's detail text reads *"OpenAI, Claude, Gemini\nNot currently available — no officially supported direct connection exists yet"* (matches plan §11's honest-unavailable-state requirement), a "What happens after connection" section, and a `_FallbackRoutingDialog` with "Edit routing". Not yet visually verified against the Figma frame's exact layout/spacing (needs the User's live pass). |

---

## 2. Defects / mismatches (confirmed, in-scope, not yet fixed — no fix applied in this pass)

### 2.1 — HIGH — Fallback-routing config silently drops the `ollama` install-default safety net
**File:** `uri_core/core/model_router.py:121-164` (`_ordered_candidates`)

Once a user saves *any* fallback-routing config with at least one concrete (dict) slot, `_ordered_candidates` returns **only** the provider_ids drawn from those dict slots (line 143-147) and returns early — it never reaches the pre-existing `role_cfg`/`"always include 'ollama' as install default"` fallback logic below it (lines 150-164), and the class's own docstring (line 74: *"5. Install default: 'ollama' always permitted"*) is now false whenever a user has configured routing.

Concretely: the plan's own reference example (and the shipped default, `test_fallback_routing_store_defaults_and_round_trips`) is `Primary=<some provider>, Fallback 1="auto", Fallback 2=None`. Because `"auto"` is a **string**, the list comprehension at model_router.py:145 (`isinstance(item, dict)`) silently filters it out. If the user's Primary provider fails (unhealthy, over budget, or errors), **there is no fallback candidate left at all** — `AllProvidersUnreachableError` is raised instead of falling through to Ollama, even though Ollama was always installed as the local safety net before this milestone.

**Confirmed, not just plausible:** `attempt()` (the real production path, line 210-222) calls the same `_ordered_candidates`, so this reaches live traffic, not just `resolve()`.

**Test-coverage gap that let this through:** the shipped `test_router_prefers_validated_custom_routing_before_role_config` (tests/test_m31_model_brain_ux.py:88-97) only exercises `fallback_1` as a concrete `{"provider_id": "ollama", ...}` dict — it never exercises the `"auto"` literal case, which is the actual default value and the one that triggers this bug.

**Also stale:** the class docstring (model_router.py:73) still reads *"User declared fallback order (reserved slot — no per-user fallback config yet)"* — no longer true.

### 2.2 — HIGH — `anthropic` provider catalogue entry uses the wrong adapter; real API-key calls will fail
**File:** `uri_core/core/provider_registry.py:175-180`

`provider_id="anthropic"` is declared `adapter="openai_compatible"` with `base_url="https://api.anthropic.com/v1"`. `OpenAICompatibleProvider.complete()` (`openai_compatible_provider.py:91`) always POSTs to `{base_url}/chat/completions` with an `Authorization: Bearer <key>` header. Anthropic's real API has no `/chat/completions` route at all — its actual endpoint is `/v1/messages`, with a completely different request/response JSON shape and an `x-api-key` header, not `Authorization: Bearer`. Every real completion or `/providers/anthropic/verify` call against a genuine Anthropic key will fail (404/401), meaning **Anthropic can never actually be verified or used as a Brain provider in production**, despite appearing fully wired in the catalogue and in the connect-screen's "Connect with API key" card. This directly contradicts the plan's own objective ("API-key providers … are fully functional Brain providers") and the User's explicit requirement list (Anthropic API key access).

By contrast, the new `gemini` entry (`base_url="https://generativelanguage.googleapis.com/v1beta/openai"`) is very likely correct — Google publishes a genuine, documented OpenAI-compatibility layer at exactly that path shape, so `{base_url}/chat/completions` is a real, intentional Google endpoint. I did not make a live network call to confirm this (no real key available in this review, and an unnecessary real call would spend the User's quota) — flagged in §4 as needing live confirmation, not as a defect.

**Not caught by the shipped tests** because `test_m31_model_brain_ux.py` never exercises the real HTTP layer for any provider (by design — its own module docstring says "provider network calls are never made here").

### 2.3 — MEDIUM/HIGH (severity to be confirmed live) — `m22_5_providers_test.dart` regressed: 1 passed, 5 failed
**File:** `uri_ui/test/m22_5_providers_test.dart`, independently re-run just now.

This suite is one of the three explicitly named in Antigravity's audit handoff and the User's own list — the Codex implementation report never mentions its result at all. Actual run:
```
renders catalogue providers with display names and adapters   FAILED (find.text('OpenAI') found 0 widgets)
shows the three connection methods and verified-only routing entry point   PASSED (new test, added this milestone)
key entry input is masked (obscureText: true)   FAILED (Bad state: No element)
submitting a key updates configured status with last-4...   FAILED (Bad state: No element)
shows explicit error message when key submission fails   FAILED (Bad state: No element)
allows saving endpoint config overrides   FAILED (Bad state: No element)
```
Most likely root cause (not yet confirmed): the pre-existing per-provider catalogue list is rendered inside a `ListView.builder` (lazy-built), and the new Design-02 front section (3 cards + explainer + fallback-routing box) is now large enough to push that list below the initially-built viewport — so `find.text('OpenAI')` finds nothing because the old items are not merely off-screen but not yet *built*, and the old tests never scroll before asserting. If so, this is **test debt from a layout change the plan itself authorized** ("existing per-provider settings list stays reachable below/behind it") rather than a real functional break — but I have not confirmed the underlying functionality (key submission, error display, endpoint-config saving) still genuinely works for a real user who scrolls to it. Treat as HIGH until confirmed otherwise; this is exactly the kind of thing the User's live pass should specifically check (§4).

### 2.4 — LOW — `AskRequest.model_override` / `FallbackRoutingRequest.fallback_1` typed as `Optional[object]`
**File:** `uri_core/app/server.py:795, 800`

Using bare `object` instead of a real `Union[dict, Literal["auto"]]`/similar means Pydantic/FastAPI performs no shape validation at the API boundary — any JSON value (int, list, bool) is accepted and only later code (`model_roles.py:176`, defensively `isinstance`-checked) decides what to do with it. Not a security or correctness bug — downstream code is defensive — but it means a malformed client request is silently accepted and silently ignored rather than rejected with a clear 422, and it produces a useless OpenAPI schema for this field. Cosmetic/API-quality issue, not blocking.

### 2.5 — LOW — `apply_active_brain_override`'s explicit-`model_override` branch is not role-gated
**File:** `uri_core/config/model_roles.py:175-182`

The per-turn `model_override` dict is applied unconditionally to *any* role calling this function (the `role not in ACTIVE_BRAIN_OVERRIDE_ROLES` gate at line 183 only applies to the *stored Active Brain* fallback path, not to an explicit per-request override). This may be intentional (a user's explicit chat-turn choice arguably should apply everywhere it can), but it was not explicitly specified in the plan and is broader than the four call sites (`decision_engine.py`, `model_reasoning_adapter.py`, `provider_semantic_interpreter.py`, `response_drafting.py`) the plan named. Flagging for a deliberate decision, not asserting it's wrong.

---

## 3. Claims that cannot be independently verified in this pass

- **Gemini API-key completion/verification actually working** — the URL shape is consistent with Google's real, documented OpenAI-compatibility endpoint, but I did not make a live call (no key on hand, would spend real quota). Needs a live check.
- **Design 02 / Design 04 pixel/layout fidelity to the Figma frames** — I confirmed the right *pieces* exist in code (three cards, explainer, fallback dialog, composer chip, popover, caption) but did not run the app and compare against the rendered Figma frames captured earlier this session. That is explicitly the User's/Antigravity's job, not something a source read can confirm.
- **`orchestrator.py` "must never grow" guard** — file is currently 6,153 lines. The working tree already had unrelated uncommitted changes before M31 started, so a clean before/after diff isn't available to me; the implementation report claims "kept orchestrator.py byte-count unchanged." I did not find any M31-related edits to `orchestrator.py` in my reading, which is consistent with that claim, but I did not byte-diff it against a real pre-M31 commit.
- **`m22_5_providers_test.dart` failures: test-debt vs. real functional regression** — see §2.3. Needs either a deeper code read or (better) the User's own live pass through the provider settings' key/endpoint-config flows.

## 4. Items that need the User's own live UI/provider pass

1. Connect-screen visual match to Figma frame 1:71 (card spacing/equal hierarchy, subscription card's honest-unavailable copy, fallback-routing box, Edit routing dialog).
2. Chat composer visual match to Figma frame 1:201 (chip placement, popover row styling, dot+text treatment for an unverified model, attachment chips still correct).
3. **Specifically**: after connecting a real provider, scroll the provider settings screen and confirm the existing key-submission / error-display / endpoint-config-override flows still work (this is the functionality `m22_5_providers_test.dart` says it can no longer find — confirm it's really just scrolled out of the test's view, not actually broken).
4. Set Primary Brain to a provider, leave Fallback 1 as the default "URI Auto," then make the Primary fail (e.g. disconnect it) and confirm whether the app actually falls back to Ollama or errors out — this directly exercises defect §2.1 live.
5. If an Anthropic key is available: connect it and hit "Verify" — expect it to fail per §2.2; if it unexpectedly succeeds, that changes §2.2's finding and should be reported back.

---

## 5. Discrepancy reconciliation (report vs. state vs. relay vs. reality)

- `M31_IMPLEMENTATION_REPORT.md`'s "Verification performed" section (10 passed / 1 failed for `chat_lifecycle_test.dart`) is **stale**, not a live current failure: I independently re-ran the suite and got 11/0, matching the relay's number. The report's "Continuation completion" section (above it) describes the exact fix that resolved it, but the older "Verification performed"/"Remaining audit items" sections beneath were never removed or updated after that fix landed — the report is two passes glued together without reconciliation, which is why it self-contradicts (`Status: IMPLEMENTED PARTIALLY — NOT VERIFICATION_READY` immediately followed by `Status (superseding above): VERIFICATION_READY`).
- Neither the report nor the relay mentions `m22_5_providers_test.dart`'s actual result (1 passed / 5 failed) at all, despite it being one of the three suites the audit handoff explicitly named — this should have been run and disclosed before the `VERIFICATION_READY` status was posted.

---

**Bottom line for this pre-final pass:** two HIGH-confidence, unfixed, in-scope backend defects (§2.1 fallback safety net, §2.2 Anthropic adapter), one regressed and undisclosed Flutter test suite needing root-cause determination (§2.3), and no code changes made. Recommend Antigravity route §2.1/§2.2 back to Codex now (they don't require the User's live pass to fix — they're deterministic code defects), while the User's live pass separately confirms §2.3's real severity and the visual/UX fidelity items in §4. No verdict issued.

---

# Round 2 — Pre-Final Audit of the Live-Acceptance Repair Pass (2026-09-15)

**Context:** the User's own live acceptance (after §1-§5 above) returned `REPAIR REQUIRED` with 8 defects (5.1-5.8, recorded in `M31_IMPLEMENTATION_REPORT.md` §5). Codex repaired all 8. This section is the independent pre-final technical audit of that repair pass, per direct User instruction. **No ACCEPT/REPAIR REQUIRED verdict is issued here** — formal verdict stays gated on the User's own short live re-test, per the standing live-verification gate. No code was modified during this review.

**Method:** direct re-execution of every named test suite, plus direct reading of the actual current source for each of the 8 claimed repairs (not the implementation report's prose).

## R2.1 — Test suites, independently re-run

| Suite | Report claim | Independently confirmed |
|---|---|---|
| `pytest tests/test_m31_model_brain_ux.py -v` | 14 passed | **14 passed** — exact match, including the 5 new Anthropic tests and the new `"auto"`-primary-failure fallback test. |
| `flutter test test/m22_5_providers_test.dart` | 6 passed | **6 passed** — exact match. |
| `flutter test test/chat_lifecycle_test.dart` | 11 passed | **11 passed** — exact match. |
| `flutter analyze` | "0 errors... two informational notices remain" | **0 errors, 3 info-level notices** (a new `curly_braces_in_flow_control_structures` at `providers_screen.dart:442` alongside the two previously-known ones). Minor discrepancy — cosmetic, non-blocking, but the report's count is off by one. |

## R2.2 — Verified repaired (confirmed by direct code read, not just passing tests)

1. **Defect 2.1 / fallback `ollama` safety net (original §2.1) — genuinely fixed.** `model_router.py:121-172`: a saved `"auto"` slot now expands to `[role_primary, "ollama"]`, and whenever any routing slot is configured, `"ollama"` is unconditionally appended if not already present before dedup (line 152-154). This is a real fix, not just a passing test — read directly.
2. **Defect 2.2 / Anthropic adapter (original §2.2) — genuinely fixed, verified at the implementation level.** New `uri_core/core/model_providers/anthropic_provider.py`: posts to `{base_url}/v1/messages` (catalogue `base_url` correctly changed to `https://api.anthropic.com`, no more double-`/v1` risk), `x-api-key` + `anthropic-version: 2023-06-01` headers, correct request shape (`model`/`max_tokens`/`messages`/top-level `system`), correct response parsing (`content[0].text`), correct error mapping (401/403→`ProviderAuthenticationError`, 429→`ProviderRateLimitError`, 5xx→`ProviderUnavailableError`). This is a real, correct native implementation — not a superficial patch.
3. **Defect 5.4 / fallback routing save — genuinely fixed.** New `_selectable_models_for()` (`server.py:818-834`): for `ollama`, always includes live `list_installed_models()` in addition to the verify-cache, so a saved Ollama model never depends on a fresh `/verify` hit. `update_fallback_routing` now validates against this, not the stricter `_verified_models_for`.
4. **Defect 5.5 / model inventory sync — genuinely fixed.** `GET /providers` (`server.py:~3118-3145`): builds one `inventory_ids` list merging catalogue models with any live-verified model not already in the catalogue (e.g. a locally-installed Ollama model like `qwen3.5:9b`), and marks `verified` per model from that same merged set. Active Brain, fallback routing, and chat selector now read from this one endpoint's output — a single source of truth, as required.
5. **Defect 5.6 / HTTP 500 on `/ask` — genuinely fixed.** `server.py:1423-1446`: `serving_provider`/`serving_model` are now computed via `_serving_model_for_turn()` strictly *after* `result` is fully resolved, never referencing an undefined variable mid-flow. Direct code read confirms the old bug's shape (a pre-computation reference) is gone.
6. **Defect 5.7 / override-caption sync — genuinely fixed, with an honest disclosed limitation.** The real served model/provider (`_serving_model_for_turn`, sourced from `ModelRouter`'s own post-success usage record — real observed execution, not intent) is the primary source; the manual `model_override` is used as the caption's source **only** when no router observation exists for that session yet **and** the turn genuinely completed with a narrative — a deliberate, narrow, and correctly-reasoned fallback, not a blanket "trust whatever was requested." One low-severity theoretical note: `_serving_model_for_turn` picks the *latest* success record for the session in the current month (`server.py:837-858`) — in a rapid-fire multi-turn scenario this could theoretically pick up a different turn's record; unlikely to matter for a single interactive user, not blocking.
7. **Defect 5.2 / provider-state truthfulness — genuinely fixed.** `GET /providers` now reports `configured`, `available`, and per-model `verified` as fully independent signals; `active_brain` is only ever reported `true` when `active_brain["model"] in verified_models` (server.py, same block as R2.2.4); in Flutter, `_ProviderConnectionGroup` only renders an Active-Brain-selectable `ActionChip` for models where `model.verified == true` (`providers_screen.dart:501-521`) — an unverified/catalogue-only model is never presented as selectable anywhere in the primary UI path.
8. **Defect 5.1 / Figma legacy-layout removal — the literal complaint is fixed, but see R2.3 below for a new concern this repair introduced.** The old `_ProviderCard`-list + `ChoiceChip` tab block (`providers_screen.dart`, formerly lines ~147-189) is now entirely commented out and confirmed unreachable (`_ProviderCard(` is never instantiated anywhere in the file — grep-confirmed) — the User's literal complaint ("legacy UI still primary") is resolved. It was replaced with a new structure, not merely hidden.

## R2.3 — New concern found in this repair pass (not one of the original 8, not yet fixed)

**MEDIUM/HIGH — the replacement Design-02 layout is not actually 3 equal-hierarchy cards.** `providers_screen.dart:230-257`: the primary layout is now `_ConnectionMethodCard` (Subscription — fixed, ~3 lines, disabled) + `_ProviderConnectionGroup` (API Key) + `_ProviderConnectionGroup` (Local Models). `_ProviderConnectionGroup` (`providers_screen.dart:447-548`) renders a `for` loop over every provider in its group — a full block (name, 3 status lines, a model-chip row, action buttons, a divider) **per provider**, with no height cap or internal scroll (`SizedBox(width: 310)` only constrains width). With 5 providers in "API Key" (OpenAI/Anthropic/Gemini/Groq/OpenRouter) and 2 in "Local" (Ollama/LM Studio), these two cards will organically grow far taller than the fixed 3-line "Subscription" card. This is a structural, code-verifiable departure from the approved Figma frame's 3-cards-of-equal-weight design (plan §14 / rule 7), not merely a spacing nit. I did not run the live app to see the actual rendered heights (that's the User's/Antigravity's job), but the code shape makes an equal-hierarchy render implausible. **Recommend the User's live re-test specifically look at whether the three top-level cards actually appear equal in size** — if they don't, this needs one more bounded repair (cap height + internal scroll, or restructure to a genuine 3-card layout with the per-provider detail moved to a secondary/expandable view) before final ACCEPT.

## R2.4 — Claims not independently verified (need the User's live re-test)

- **Defect 5.3 / Groq key connection — code is plausible but explicitly untested against a real key.** `providers_screen.dart:981-1017`: storage and verification are now correctly split into two distinct stages with distinct error messages surfaced from the real backend response. However, `M31_IMPLEMENTATION_REPORT.md` §6 itself discloses: *"A real Groq secret was not available to this repair run."* The original live-tested failure was never reproduced or confirmed resolved — only the error-message granularity was generically improved. **This is exactly what the User's live re-test with their real Groq key needs to confirm.**
- **New finding, not in the original 8: the Anthropic catalogue model id may be invalid.** `provider_registry.py:178`: `ModelDescriptor("claude-3-5-sonnet", ...)` — Anthropic's real Messages API requires a fully-versioned model string (e.g. `claude-3-5-sonnet-20241022`) or a documented `-latest` alias; a bare `claude-3-5-sonnet` is likely to be rejected with a 400 from the real API even though `AnthropicProvider`'s request/response handling is itself correct (R2.2.2). I have no live key to confirm this. **Recommend the User's live re-test specifically try verifying/using Anthropic, not just Groq**, since the client code is right but the configured model string may not be.
- **Duplicate-fallback prevention (Defect 5.8) is client-side only.** The Flutter routing dialog rejects duplicate non-`auto` selections before calling save, but `update_fallback_routing` on the backend (`server.py:3213-3226`) has no equivalent server-side check. Low severity (a personal-preference setting, not a security boundary) but worth noting as a defense-in-depth gap, not a blocking defect.
- Visual/pixel fidelity of both frames against the live app — not checked in this pass (source-code review only); this is squarely the User's/Antigravity's job.

## R2.5 — Disposition

**`READY_FOR_USER_LIVE_RETEST.`**

All 8 originally-reported live defects have a genuine, code-verified repair (7 fully confirmed by direct source read; the 8th — Figma fidelity — has its literal complaint resolved but introduced a new equal-hierarchy concern, R2.3, that is itself exactly the kind of thing a short live re-test is positioned to catch). All 4 named test suites independently re-run and match the reported counts (with one trivial off-by-one info-lint discrepancy). No blocking code defect was found that would make a live re-test premature or wasteful.

**Specifically worth checking in the short re-test**, beyond the general pass:
1. Do the three top-level connect-provider cards actually look equal in size/weight (R2.3)?
2. Does the real Groq key now connect end-to-end (R2.4)?
3. Does Anthropic connect/verify end-to-end, or does it fail on the model-id string (R2.4)?

No ACCEPT/REPAIR REQUIRED verdict issued — that remains the User's call after this re-test, per the standing gate.
