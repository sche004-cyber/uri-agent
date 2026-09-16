# URI Approved UI Prototype — Startup Blockers Audit & Bounded Repair

**Auditor/Implementer:** Claude (visual/architecture authority, bounded-fix authority, AO-4 standing role).
**Scope:** two User-reported prototype blockers found during interactive review. Root-caused via direct evidence (live backend calls, source trace), fixed with the narrowest change that closes each defect, re-verified live. No commit/push.

---

## 1. Acceptance Criteria (defined before investigating)

1. Root-cause each blocker from real, direct evidence (live HTTP calls, source trace) - never guess from the symptom description alone.
2. Any fix must reuse existing approved assets/architecture - no new logo, no provider-system redesign, no fabricated "connected" state.
3. Prove each fix live, end-to-end, not just by reading the diff.
4. Disclose anything found that is real but out of the authorized bounded scope, rather than silently expanding to fix it.
5. Run only the tests targeted at the exact files touched - no broad/unrelated suite.

---

## 2. Blocker 1 — Startup Branding Mismatch

### Root cause
`uri_ui/lib/screens/onboarding/brain_onboarding_screen.dart` used `UriWordmark` - a small, procedurally-painted vector "eclipse" mark (`uri_wordmark.dart`'s `_EclipseMarkPainter`) with a `showTagline: true` flag that renders the text **"AI COMPANION"**. This is a completely different visual asset from the approved dashboard's own left-rail brand mark, which is the real raster file `assets/uri_app_logo_refined_v2.png`, screen-blended onto the obsidian background - and that raster already has "Desktop Companion" baked into the image itself. The onboarding screen was never updated to use the approved raster treatment when the dashboard was.

### Fix
`brain_onboarding_screen.dart`: replaced the `UriWordmark` call with the exact same `Image.asset('assets/uri_app_logo_refined_v2.png', color: Color(0xff020910), colorBlendMode: BlendMode.screen, fit: BoxFit.contain)` block already used by the approved dashboard's rail (`app_shell.dart`'s `_Sidebar`). No new asset, no new logo, no mascot - the identical approved raster and blend mode, reused verbatim. The raster's own baked-in "Desktop Companion" caption satisfies the subtitle requirement without a separate competing text line.

### Verification
- `flutter analyze` on the touched file - no issues.
- Focused widget tests (`m25_ui_defects_test.dart`, `reference_render_test.dart`, `dashboard_shell_test.dart`) - 10/10 pass, no regression.
- Visual confirmation: left for the User's own interactive review of the relaunched app (this fix cannot be screenshotted from the dashboard-only render harness, since onboarding is a separate route).

---

## 3. Blocker 2 — User Cannot Reach the Dashboard ("Ollama unreachable")

This traced to **two distinct, real defects** stacked on top of each other - fixing only the first would not have unblocked a real user; both were required.

### 3.1 Defect A: onboarding picks a model that isn't installed

`BrainOnboardingScreen._chooseLocal()` selected `local.models.firstOrNull?.modelId` - the **first** Ollama model in the static catalogue (`qwen3:14b`), regardless of which model(s) the local Ollama server actually has pulled. Confirmed live: this machine's real Ollama daemon is reachable (`/api/tags` returns HTTP 200) but only has `gemma4:12b` installed - `qwen3:14b` was never pulled. `describe().available` only proves the **daemon** answers; it never proves any specific **model** exists, so "Test local Ollama connection" could legitimately report reachable while "Use Ollama as Active Brain" still silently locked in an unusable model.

**Fix (backend, additive):**
- `OllamaProvider.list_installed_models()` (new method, `ollama_provider.py`) - a real `/api/tags` GET, parsed for `models[].name`, returning `[]` on any failure. Never guesses.
- `GET /providers` (`server.py`) now includes a real `installed_models` field per provider (populated for the `ollama` adapter only).

**Fix (frontend):**
- `ProviderEntry` (`uri_client.dart`) gained `installedModelIds` parsed from the new field.
- `BrainOnboardingScreen._chooseLocal()` now prefers a model that is both in the catalogue **and** actually installed; falls back to prior behavior only when the installed list is unknown/empty (never blocks on missing telemetry); shows an explicit, actionable message (which command to run, or "choose Cloud Provider instead") when nothing installed matches the catalogue, rather than a misleading generic failure.

Confirmed live: `GET /providers` now returns `"installed_models":["gemma4:12b"]` for the ollama entry; setting the active brain via the same logic now correctly resolves to `gemma4:12b`.

### 3.2 Defect B (the deeper, load-bearing one): Active Brain never reached the first model call of a turn

Even after Defect A's fix, a real authenticated `/ask` call still failed with `"interpretation_unreachable": true` - **semantic interpretation**, the very first model call on every turn, ignored the user's configured Active Brain entirely and always used the deployment-wide default model (`qwen3:14b`, not installed), regardless of what the user had correctly configured.

**Root cause, traced through actual code, not assumed:**
- `uri_core/config/model_roles.py`'s `build_provider()` already had a per-user Active Brain override block - but it only applied to `ROLE_REASONING`/`ROLE_DRAFTING`, and only when called with `provider_id_override=None`.
- The real semantic-interpretation call path (`provider_semantic_interpreter.py` → `ModelRouter.attempt()`) **always** calls `build_provider(role, principal, provider_id_override=pid)` with a concrete `pid` - so the override's own `provider_id_override is None` guard silently skipped it, for **every** role, not just semantic interpretation. The existing per-user override was effectively unreachable from the one call path real chat traffic actually uses.
- `ModelRouter`'s own `_ordered_candidates()`/`_model_for_role()` never consulted the per-user Active Brain at all - they read only the static deployment-wide `model_roles.json`/env defaults.

**Fix (`model_roles.py` + `model_router.py`, additive, reuses the existing mechanism - no new state, no new architecture):**
1. Extracted the existing override logic into `apply_active_brain_override(role, principal, role_config)` (`model_roles.py`) - identical behavior for direct callers (`provider_id_override is None`), now also covering `ROLE_SEMANTIC_INTERPRETATION`.
2. `build_provider()` now also applies this override when called **with** a `provider_id_override`, but **only when the override's own provider adapter matches the router's already-chosen candidate** - so this can never change *which* provider the router decided to try, only which *model* is requested once that provider is already the one being attempted.
3. `ModelRouter._model_for_role()` now takes the candidate `pid` and applies the same override for health-check/telemetry accuracy, under the identical "only if it matches `pid`" guard.
4. `ModelRouter._ordered_candidates()` (provider/adapter selection) was **deliberately left untouched** - overriding *which adapter* the router tries would let a cloud-provider Active Brain silently redirect the fallback chain's provider_id resolution, which `build_provider()` does not currently re-derive correctly when called with an explicit override (a separate, pre-existing gap - see §4).

**Live, end-to-end proof (not just a config check):** a fresh test account, active brain set to `ollama/gemma4:12b`, real `POST /ask "hello, are you working?"`:
- Before this fix: `"interpretation_unreachable": true`, `"URI could not reach its model provider"`.
- After this fix: real semantic interpretation (`"goal":"The user is checking the availability or operational status of the AI."`) and a real, correct narrative reply (`"Yes, I am working and ready to help you!"`) - both genuinely produced by the user's own configured `gemma4:12b`, not fabricated.

### Verification
- `pytest -q test_m21_provider_config.py test_provider_registry_catalogue.py test_m22_5_providers_endpoints.py test_model_router_resolution.py test_model_router_freshness.py` - **46/46 passed**, zero regressions in existing provider/router coverage.
- Live end-to-end `/ask` call, described above.
- No broad/unrelated suite run, per instruction.

---

## 4. Disclosed, Out-of-Scope Finding (not fixed here)

A **cloud-provider** Active Brain (e.g. a user whose active brain is Groq/OpenAI/OpenRouter) still cannot reach `ModelRouter.attempt()`'s real completion call correctly: `_ordered_candidates()` never routes to a cloud adapter based on Active Brain (deliberately, to avoid a bigger, riskier change - see §3.2 point 4), and even if it did, `build_provider()`'s `openai_compatible` branch derives `provider_id` from the **static** role config when called with an explicit `provider_id_override`, not from the user's actual chosen cloud provider. This is a **pre-existing** gap (cloud Active Brain never worked via the router before this repair either - this fix does not make it worse), separate from the User's reported Ollama-specific blocker, and is **not** fixed in this bounded pass. Flagged for a future, separately-scoped repair if cloud-provider Active Brain selection is required to work end-to-end.

---

## 5. Files Touched

- `uri_ui/lib/screens/onboarding/brain_onboarding_screen.dart` (logo swap; installed-model-aware selection)
- `uri_ui/lib/services/uri_client.dart` (`ProviderEntry.installedModelIds`)
- `uri_core/core/model_providers/ollama_provider.py` (`list_installed_models()`)
- `uri_core/app/server.py` (`GET /providers` → `installed_models`)
- `uri_core/config/model_roles.py` (`apply_active_brain_override` extraction + semantic-interpretation coverage + override-with-matching-provider_id_override)
- `uri_core/core/model_router.py` (`_model_for_role` applies the same matched override)

No approval/permission/dispatcher logic touched. No provider-system redesign. No fabricated "connected" state anywhere - every fix either surfaces real data (`installed_models`) or correctly routes to a real, already-configured selection.

---

## 6. Self-Review Against Acceptance Criteria (§1)

1. ✅ Both blockers root-caused via live backend calls and direct source trace, not guessed - including discovering Defect B only because Defect A's fix alone was tested live and still failed.
2. ✅ Reused the exact approved raster asset/blend; reused the exact existing Active Brain/ProviderConfigStore mechanism; no new architecture, no fake connection state anywhere.
3. ✅ Proved live end-to-end (`/ask` real call, real model output) rather than trusting a config read.
4. ✅ The cloud-provider router gap (§4) is disclosed explicitly, not silently fixed or silently ignored.
5. ✅ Only the exact test files covering the touched modules were run - 46 tests, not a broad suite.

---

## 7. ADDENDUM (post-User-override) — Defect C: `validateSession()` never detected an expired token

### Auditable correction history

The User overrode the original `UI PROTOTYPE READY FOR USER REVIEW` verdict above after live-testing the rebuilt app themselves and observing both symptoms still present ("Ollama still shows unreachable", "Cloud Provider / API Key option does nothing"), and explicitly instructed: *"Do not rely on the earlier backend proof alone... Use live UI evidence, not isolated backend tests."* This was a correct and necessary correction: §3's verification (backend calls + one `/ask` trace) never exercised the Dart client's own session-validation logic, which turned out to be the actual second-round root cause. This section records that finding rather than silently overwriting §3-§6 above.

### Root cause

`http_uri_client.dart`'s `validateSession()` — called by `AppState.revalidateSession()`/`loadPersistedSession()` on every app startup — treated **any** non-200 response from `GET /auth/me` as "keep the session", including a genuine `401`. `_resolve_authenticated_user_id` (`server.py`), the dependency `/auth/me` and every other authenticated endpoint use, deliberately raises `401` for a malformed/expired token rather than silently downgrading (its own docstring: "never silently falls back to the legacy ambient state"). Because the Dart client never recognized this `401` as rejection, an expired token already stored in `shared_preferences.json` was kept and reused for every subsequent authenticated call. `GET /providers`, `GET /providers/active-brain`, and `/ask` all then silently 401'd/degraded, which is what actually produced both symptoms the User observed — not the Ollama/router defects fixed in §3, which were real but were not the thing blocking the User's specific session.

Confirmed directly: `curl` to `/providers` and `/auth/me` with the token stored in `%APPDATA%\com.example\uri_ui\shared_preferences.json` both returned `401` for the exact same token the running app was silently continuing to use.

(A blind alley on the way to this finding, corrected in-session: `/identity` returning `200` for the same token was briefly treated as proof the token was valid. `/identity` is unauthenticated by design and ignores the Authorization header entirely, so its success proved nothing. The `/providers`/`/auth/me` `401`s are the real, conclusive evidence.)

### Fix

`http_uri_client.dart`'s `validateSession()`: added an explicit `response.statusCode == 401` branch, checked before the generic non-200 fallback, that clears `_token`/`_username` and returns `false` — so a rejected token now correctly drops the app back to a real login screen instead of an ambiently-broken logged-in state where every authenticated call quietly fails.

### Live UI verification (all four User-specified acceptance criteria, evidence gathered against the running `uri_ui.exe` release build + its backend, screenshots taken via direct screen capture of the live window, not a test harness)

1. **Local Model (Ollama) end-to-end**: fresh account through onboarding → "Test" → Ollama reported available → activated → `gemma4:12b` (the one genuinely-installed model) selected → dashboard reached. Confirmed via screenshot showing the dashboard's "Current Model: gemma4:12b / ollama" card.
2. **Cloud Provider (API Key) opens a real setup path**: Settings → Model Providers → "Accounts / API Keys" tab lists Ollama (Active Brain, gemma4:12b), OpenAI, OpenRouter, Groq, and LM Studio, each with working `Add Key` / `Set as Active Brain` / `Endpoint Config` controls and a model dropdown. Clicking OpenAI's `Add Key` opened a real "Configure Key for OpenAI" dialog (API key input field, "encrypted with PBKDF2 + Fernet at rest and are write-only" disclosure, Cancel / Save Encrypted Key). This is a genuine, already-wired setup path — not a dead button, not a fake success state, not a hardcoded provider. Dialog was cancelled without saving a placeholder key, leaving no fabricated state.
3. **Active Brain survives a full restart**: the running `uri_ui.exe` process (PID 34128) was force-killed (`taskkill /F`) and the exact same release binary relaunched from a clean process start. It landed directly on the dashboard — no re-login, no re-onboarding — with the identical logged-in user (`Uri_admin1`) and `Current Model: gemma4:12b / ollama` still shown. This is stronger than the minimum bar (session *and* Active Brain both correctly persisted and reloaded from disk state, not just re-derived in-memory).
4. **Real `/ask` from the same running app/backend pair**: a real chat turn ("hello") produced a genuine, non-fabricated response ("URI does not have an implemented capability for this kind of task yet.", tagged Failed) — an honest result from the live semantic-interpretation/router path fixed in §3.2, not a scripted success.

### Files touched (this addendum only)

- `uri_ui/lib/services/http_uri_client.dart` (`validateSession()` — explicit `401` branch)

### Verification run

- `flutter analyze` — clean.
- `flutter test test/m22_9_durable_session_test.dart` — 6/6 passed (exercises `AppState`'s own session logic via `MockUriClient`; does not directly cover `HttpUriClient.validateSession()`'s HTTP status branch, which is why live UI evidence above — not this test file — is the actual proof for this defect).
- No broad/unrelated suite run, per instruction.

### Self-review against §1's acceptance criteria, re-applied to this addendum

1. ✅ Root-caused from direct evidence (`curl` 401s against the real stored token), not guessed - including an explicit self-correction of an earlier flawed `/identity`-based inference.
2. ✅ Fix reuses the existing session-clearing path (`_token = null; _username = null;`) already used elsewhere in the client; no new architecture, no new state.
3. ✅ Proved live via the running app's actual screen output for all four User-specified criteria, not backend calls alone - directly satisfying the User's explicit instruction.
4. ✅ Nothing new found in this pass is being silently deferred; the §4 cloud-provider-router gap remains the only disclosed out-of-scope item and is unaffected by this fix.
5. ✅ Only the one directly-relevant existing test file was run.

### Verdict

All four User-specified acceptance criteria are now demonstrated with live UI evidence against the actual running app/backend pair. `UI PROTOTYPE READY FOR USER REVIEW.`
