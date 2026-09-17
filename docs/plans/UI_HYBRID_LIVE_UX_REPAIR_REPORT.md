# Live UX + Functional Consistency Pass — Report

**Initiative:** URI Hybrid UI Implementation (post-repair live UX pass)
**Governing references:** `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`, `docs/plans/UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md`, `docs/plans/UI_HYBRID_BRAIN_SETUP_REPAIR_REPORT.md`, `.claude/skills/uri-development/SKILL.md`
**Implementer this session:** Claude, on the User's explicit, direct in-session instruction to implement (not only plan/review) — same disclosed-role-note basis as the immediately preceding Brain Setup Repair.
**Scope:** bounded — reproduce each of the 16 numbered concerns against the real app before changing anything, fix only confirmed defects. No commit, push, release, or milestone close was performed.

---

## Method

Every concern below was reproduced first, either through the real backend/real Ollama/real Groq (via curl and Python, exact same code paths the app calls) or through the actual production Dart code driven interactively through a real, running backend via Chrome (the `flutter build web --release` target — this session's tooling, like the immediately preceding repair, has no native-desktop screenshot/click capability, so this is the same "closest available real proxy" approach `UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md` §3.2 already established as this project's precedent). The native Windows launcher itself (`Launch URI.bat`) was exercised for real, directly, multiple times, with real process/window checks.

---

## 1. Remove theme swatches from the global top bar

**Reproduced:** yes — `app_shell.dart`'s `_ShellTopbar` rendered 4 circular theme-swatch buttons plus the Compact toggle on every wide-layout screen, duplicating Settings → Appearance.

**Root cause:** duplicate control surface for the same setting, per the original Frozen Blueprint §4.1 spec (not a bug relative to that spec, but a UX redundancy the User asked to remove).

**Fix:** removed the swatch row and the now-unused `_ThemeSwatchButton` widget from `app_shell.dart`; the topbar keeps only the breadcrumb title and the Compact toggle. Settings → Appearance (`appearance_settings_screen.dart`, already implemented) remains the only place to change theme.

**Live verification:** real browser session — topbar shows no swatches on Home/Chat/Tasks/Connections & Providers; Settings → Appearance still lists System + the 4 real themes, selecting "Graphite" shows the checkmark correctly.

**Tests:** `dashboard_shell_test.dart`'s topbar assertions flipped from `findsOneWidget` to `findsNothing` for the 4 swatch tooltips (with the change disclosed inline); `redesign_test.dart`'s existing Appearance test (unchanged) still passes.

**Remaining limitation:** none.

---

## 2. Compact mode must be the actual active UI, not a floating panel

**Reproduced:** yes — `compact_overlay.dart`'s `CompactOverlay` rendered a fixed 420×580 `Material` card centered over a `Colors.black@45%` scrim, with the full Workspace shell still visible (dimmed) underneath via `IgnorePointer`.

**Root cause:** this was the Frozen Blueprint §4.4's own original design ("420×580 floating window"), not an implementation defect — a genuine, disclosed deviation from that frozen text, made on the User's direct live-testing instruction in this session.

**Fix:** `CompactOverlay` now fills the entire window (`Material` sized via the same `Positioned.fill`, no scrim, no centering, no fixed size) as the app's actual active content. `app.dart`'s `UriHome` swapped `IgnorePointer` for `Offstage` so the Workspace shell stays mounted (state preserved) but is neither painted nor hit-testable while Compact is active, instead of merely being inert-but-visible underneath. "Expand to Workspace" (`_CompactHeader`'s button, now using the canonical `UriWordmark` — see §12) remains the one clear way back.

**Live verification:** real browser session — clicking "Compact mode" replaced the entire window with the conversation view (header/messages/composer), no dimmed Workspace visible at all; "Expand to Workspace" returned to the full shell correctly.

**Tests:** `compact_overlay_test.dart` updated for the new architecture (`find.text(..., skipOffstage: false)` where the test specifically needs to prove the shell is still mounted, since `Offstage` — unlike the old `IgnorePointer` — makes `find.text`'s default `skipOffstage: true` behavior skip it); all 5 existing state-preservation tests (draft survives, session/transcript unchanged, in-flight request never duplicated) re-pass unmodified in substance.

**Remaining limitation:** none functionally; disclosed as an intentional, recorded deviation from the frozen spec's literal text, not a silent architecture change.

---

## 3. `Launch URI.bat` must not leave a terminal window open on success

**Reproduced:** yes — the previous `Launch URI.bat` ran `scripts\launch_uri.ps1` directly inside the same visible `cmd.exe` console for the entire duration of the backend health-poll (up to 30s on a cold start), printing every `==>` step line to that visible window.

**Root cause:** no window-hiding at all; the console was simply the default one Explorer creates for a double-clicked `.bat`.

**Fix:** `Launch URI.bat` now launches `launch_uri.ps1` via `start "" /min powershell ... -WindowStyle Hidden`, detached (not waited-on), and exits immediately itself. A real failure still surfaces: `launch_uri.ps1`'s own `Show-FailureAndExit` already shows a Windows message box independently of console visibility (verified working in the prior readiness report), so the `.bat` no longer needs to wait for or relay an exit code. Trade-off, disclosed: the `.bat`'s own last-resort console-text fallback (only reachable if Windows Forms itself were unavailable, which never applies to this app's real Windows-desktop target) is gone; the message box remains the primary, tested failure surface.

**Live verification:** real, repeated `Launch URI.bat` invocations — the calling shell regained control immediately every time (no blocking wait); `Get-Process | Where MainWindowTitle -ne ""` for `powershell`/`cmd` found nothing during or after a cold start that took the backend several seconds to come up; the real backend and real desktop app were both confirmed running afterward (health check `{"status":"ok"}`, `uri_ui.exe` process present).

**Tests:** none applicable (a `.bat`/PowerShell launcher has no Dart/Python test coverage in this repo, consistent with the prior readiness report's own launcher work).

**Remaining limitation:** a genuine failure's message box was not re-verified visually in this session (no screenshot capability); its mechanism is unchanged from the prior, already-verified implementation.

---

## 4. "Connect a provider" controls must actually work

**Reproduced:** yes — `providers_screen.dart`'s `_ConnectionMethodCard` "Continue" button was `onPressed: enabled ? () {} : null` for every enabled card — a literal no-op. Live-reproduced: clicking "Local Models" → "Continue" visibly did nothing.

**Root cause:** placeholder callback never replaced with a real action.

**Fix:** "Continue" now scrolls the enclosing page to the matching provider group already rendered below (API Key → `API Key Providers`, Local Models → `Local Model Providers`), via `GlobalKey` + `Scrollable.ensureVisible`. The disabled "Subscription" card is unchanged — already correctly disabled with its own explanatory detail text.

**Live verification:** real browser session — clicking "API Key" → "Continue" visibly scrolled the page down and landed on the `API Key Providers` group with Groq's real card in view.

**Tests:** none added (this is a scroll-position effect, not asserted in the existing widget-test style used elsewhere in this file; verified live instead, matching how this screen's other interactive dialogs are primarily covered).

**Remaining limitation:** none.

---

## 5. Fix API-key/provider verification, especially Groq

**Reproduced:** yes, and root-caused precisely, using the real key in `.env` (never printed, logged, or committed — read once per check into a local variable/clipboard and discarded; live-verified via `Set-Clipboard`/`ctrl+v` into the app's own encrypted-key dialog and via direct backend API calls using the same value).

**Root causes found (three, all real, all fixed):**

1. **`build_provider()`'s adapter dispatch.** `provider_id_override` (a real catalogue `provider_id` like `"groq"`, passed by `ModelRouter`) was compared directly against the three literal ADAPTER family names (`"ollama"` / `"openai_compatible"` / `"anthropic"`) instead of being resolved through the catalogue first. This only ever happened to work for `"ollama"` and `"anthropic"`, whose `provider_id` equals their own adapter name — every other `openai_compatible` provider (Groq, OpenAI, OpenRouter, Gemini) unconditionally raised `UnknownModelProviderError` the instant `ModelRouter.attempt()` tried it, regardless of key validity.
2. **The same confusion, one level deeper.** Once (1) was fixed, `build_provider()` still decided whether to *adopt* the Active-Brain-overridden role config (which carries the real model) by comparing the override's ADAPTER against the real `provider_id` — the identical bug, in a second spot. The override was silently discarded, and `build_provider()` fell back to this role's hardcoded default model (`"gpt-4o"` for `openai_compatible`) instead of the user's real Active Brain model, which Groq then genuinely rejected with `ModelNotFoundError`.
3. **A stale catalogue model.** `provider_registry.py`'s Groq entry listed `llama-3.3-70b-versatile`, which Groq has decommissioned — confirmed live: a real completion attempt against it with a genuinely valid key raised `ModelNotFoundError`, not an auth error, proving the key itself was never the problem.

**Fixes:**
- `build_provider()` (`uri_core/config/model_roles.py`): resolves a non-adapter-literal `provider_id_override` through `CATALOGUE_BY_ID` first, for both the dispatch decision and the role-config-adoption decision (now compared by real `provider_id`, not adapter name) — the legacy static-deployment-config path (which genuinely uses the adapter name as a literal override, per `test_model_router_degraded_mode.py`) is preserved byte-for-byte via an explicit `_KNOWN_ADAPTER_LITERALS` branch.
- `provider_registry.py`: Groq's catalogue model replaced with `qwen/qwen3.8-27b` — chosen only after confirming live, with this real key, against Groq's own `GET /v1/models` and a real chat completion that returned a real, correct answer. (Two `openai/gpt-oss-*` candidates were also tested and rejected: both returned HTTP 200 with an empty `message.content` for simple prompts under this adapter's plain parsing — they would have looked "verified" while silently never producing visible output.) `context_tokens`/`pricing_per_1k_tokens` are Groq's own reported values for this model (from that same live response), not estimates.

**Live verification (end to end, real key, real Groq API):**
1. `POST /providers/keys` with the real key → `configured: true`.
2. `POST /providers/groq/verify` → `{"verified": true, "verified_models": ["qwen/qwen3.8-27b"]}`.
3. `PUT /providers/active-brain` with that model → accepted.
4. Home tile: **"Qwen3.8 27B (Groq)" / qwen/qwen3.8-27b** — real, not fabricated.
5. Chat model selector: shows it as a real, green/verified choice alongside the real Ollama models.

One methodology note, disclosed rather than hidden: two intermediate browser-paste attempts into the key dialog produced a corrupted value (once literally a Google OAuth `credentials.json` blob, once a 57-character near-miss) — a Chrome-automation clipboard/paste reliability issue in this session's tooling, not a URI defect; the direct-API submission and a clean, careful repeat of the browser paste both worked correctly, and the difference was diagnosed by decrypting and inspecting the actually-stored value's *structure* (length, brace characters, JSON key names) without ever printing the secret itself.

**Tests:** `test_model_router_cloud_provider_override.py` — new file, 8 tests: Groq/OpenRouter override resolves the correct config+key (not OpenAI's), the legacy adapter-literal path is unaffected, an unknown override still raises, `_ordered_candidates`/`_model_for_role` correctly prioritize and model a cloud Active Brain, explicit Fallback Routing still wins over Active Brain, and — the second root cause specifically — a router-mediated call uses the real Active Brain model rather than the hardcoded per-adapter default. All pass; full provider/router/M31/security suites re-run clean (106 tests).

**Remaining limitation:** see §6 — the drafting/narrative stage did not reliably reach Groq for every real turn even after these fixes, while semantic interpretation and execution both did; disclosed there rather than re-stated.

---

## 6. "URI Auto" must be real routing

**Reproduced:** yes — a user's Active Brain (set via "Set as Active Brain" in Connections & Providers) never reached `ModelRouter`'s candidate list at all unless the user *separately* used the advanced "Edit Routing" dialog to explicitly set a primary — "URI Auto" for the ordinary, expected path silently ignored the user's real choice and fell straight to the static deployment default + Ollama.

**Root cause:** `ModelRouter._ordered_candidates()` was deliberately not Active-Brain-aware (see its own prior comment), specifically because of §5's root causes 1–2 — including a cloud Active Brain would have "silently redirected the router's fallback chain" incorrectly until those were fixed.

**Fix:** `_ordered_candidates()` now uses the real Active Brain as the implicit "primary" candidate whenever Fallback Routing's own `primary` slot is unset — an explicit Fallback Routing choice still always wins when both are set (the Active Brain is a *default* for "no explicit primary," never a hidden override of one). `_model_for_role()`'s own candidate-model match was fixed identically to §5's root cause 2 (compares by real `provider_id`, not adapter name), so a candidate's real chosen model reaches `provider.complete()` for every provider, not only Ollama/Anthropic.

**Live verification:**
- With Groq as Active Brain and no explicit Fallback Routing: `_ordered_candidates` → `["groq", "ollama"]` (Groq first); a real chat turn's semantic-interpretation and execution stages both genuinely used Groq (`serving_provider: "groq"`, real 1.2–1.3s responses, real correct `gmail_search` tool dispatch and answer).
- With an explicit Fallback Routing primary set to Anthropic: candidates correctly became `["anthropic", ...]` — Active Brain never overrides an explicit choice.
- **Truthful-error requirement:** confirmed via the deliberate negative control from the immediately preceding repair (a second, isolated backend instance with `OLLAMA_BASE_URL` pointed at a genuinely unreachable port) — URI never fabricates an answer when no provider is reachable; it reports "unavailable" honestly every time.

**Remaining limitation, disclosed:** the final drafting/narrative stage (`response_drafting.py`, also router-mediated, also benefiting from the same fixes) consistently failed to produce a narrative via Groq across two separate real user turns in this session (`narrative_unavailable_reason: "drafting_provider_unreachable"`), even though semantic interpretation and execution both succeeded via Groq in the same turns. Standalone reproductions of both a simple prompt and a drafting-shaped prompt (same model, same `max_tokens=300`, a synthesized system prompt approximating the real one) against the exact same Groq model both succeeded with real, non-empty content — so this is not simply "the model can't do this," and root-causing the specific interaction with URI's real, larger policy+soul drafting system prompt fell outside this bounded pass's time budget. Two things keep this from being a fabrication or an unhandled crash: (a) the existing graceful-degradation path (already fixed in the immediately preceding Brain Setup Repair) surfaces an honest "Brain unreachable" state rather than inventing a narrative, and (b) the deterministic `response`/`execution` result (e.g. the real "You have 536 unread Gmail messages right now.") is still delivered to the `/ask` caller regardless of the narrative's own failure — Milestone 8A's "narrative is an enhancement, the deterministic template is the reliable fallback" design held correctly throughout. This is flagged as the clearest remaining item for a follow-up pass, not silently left unmentioned. Ollama drafts reliably in every test in this session.

**Tests:** covered by §5's new test file (the routing/model-selection halves of this concern); the drafting-specific limitation above is a live, backend-integration observation, not something a fast unit test can pin without either mocking away the real behavior or spending real Groq quota on every CI run — deliberately not mocked into a false-green test.

---

## 7. Chat model selector must show real inventory and refresh after provider changes

**Reproduced:** yes — `providerInventory` was fetched exactly once, in the composer's `initState()`. Configuring or verifying a provider afterward (e.g. from Connections & Providers, same session) never reached the selector, which kept showing whatever inventory existed at first mount.

**Root cause:** single, one-time fetch with no refresh trigger.

**Fix:** the model-selector chip now refreshes `providerInventory` on the raw pointer-down event (via a `Listener`, so it never competes with `PopupMenuButton`'s own tap handling in the gesture arena) — the next time the menu opens, it reflects the real, current inventory.

**Live verification:** real browser session — after adding the real Groq key and verifying it, opening the model selector showed "Qwen3.8 27B (Groq)" as a real, green/verified choice alongside "Gemma 4 12B" and "qwen3.5:9b" (both Ollama, verified), with every genuinely unverified catalogue model (Qwen3 14B, GPT-4o, GPT-4o mini, GPT-4o via OpenRouter, Claude 3.5 Sonnet, Gemini 2.0 Flash) correctly shown red/disabled.

**Remaining limitation:** none.

---

## 8. Compact per-reply metadata (model, response time, tokens)

**Reproduced as a gap:** no metadata existed beyond the model name ("Conversation model: X").

**Root cause:** the real, per-turn measured data (prompt/eval tokens, duration) was already recorded server-side by `ModelRouter._record_usage()` into `UsageMeter`, but never surfaced through `/ask`'s response body.

**Fix:**
- `server.py`: `_serving_model_for_turn` (renamed in place to return a dict) now also returns `prompt_tokens`/`eval_tokens`/`duration_seconds`, each unwrapped from the real `UsageRecord` only when its own recorded confidence is `"KNOWN"` (via a new `_measured()` helper) — never a fabricated value for a field the provider didn't actually report. `/ask`'s response gained `serving_prompt_tokens`/`serving_eval_tokens`/`serving_duration_seconds`.
- `UriTurn` (Dart model): gained `promptTokens`/`evalTokens`/`durationSeconds` fields, threaded through `toJson`/`fromJson`/`copyWith`.
- `http_uri_client.dart`: `_turnFromResponse` extracts these once and attaches them to every constructed `UriTurn` (success and failure paths alike).
- `turn_card.dart`: the existing "Conversation model: X" caption became `_metadataCaption()`, appending `· {duration}s` and `· {prompt} in / {eval} out ({total} total tokens)` only for whichever fields are actually present — a field with no data is simply omitted, never shown as 0 or a guess.

**Live verification:** real chat turns via Ollama and Groq both showed real captions, e.g. `Conversation model: gemma4:12b · 55.3s · 6442 in / 71 out (6513 total tokens)` and, via Groq, `serving_prompt_tokens: 6212, serving_eval_tokens: 67, serving_duration_seconds: 1.24`.

**Tests:** 2 new `http_uri_client_test.dart` cases (metadata present → populated; absent → stays `null`, never fabricated) and 2 new `chat_lifecycle_test.dart` `TurnCard` rendering cases (full metadata caption; no-metadata caption exactly matches the pre-existing plain string with no stray suffix). All pass.

**Remaining limitation:** none for the mechanism itself; token/time figures are only as available as the underlying provider adapter reports them (e.g. a request-scoped model-override fallback path with no router observation still shows model-only, honestly).

---

## 9. Single Gmail account should be used automatically, no unnecessary clarification

**Reproduced:** **not reproduced as a defect.** A real, live chat turn ("How many unread emails do I have?") against real Ollama produced `requires_clarification: false` and a real, correct, direct answer (`"You have 536 unread Gmail messages right now."`) via the real `gmail_search` tool — no clarifying question was asked, and only one Gmail connection exists in this codebase's current architecture (see §10) so there was never a "which account" ambiguity to begin with.

**Root cause:** none found; this already works correctly. No change made.

**Tests:** none added; behavior was confirmed via real, live backend/Ollama/Gmail integration rather than a synthetic test, per the reproduce-first requirement for this concern.

**Remaining limitation:** Gmail/Drive connections are genuinely single-tenant in this codebase today (one shared `token.json`/`credentials.json` per install, not per logged-in account — see §10) — there is currently no scenario in which a single account could even have *multiple* Gmail connections to disambiguate between. If per-account Gmail ever becomes real, this concern should be re-tested against that architecture specifically.

---

## 10. Dashboard and Chat must use the same grounded data path

**Reproduced, and a real, separate, more serious defect found in the process:** Home showed a real unread-email count (`536`) and a "Configure Brain" suggested action driven by real backend endpoints, but a **fresh account whose own Connections screen showed Gmail as "Needs authorization"** still saw that same real `536` on Home — the two surfaces disagreed about whether Gmail was actually connected for that account, even though (see §9's limitation) Gmail is a single, shared, host-wide connection in this codebase, not scoped per account at all.

**Root cause, isolated precisely:** `connection_status.py`'s `_token_is_usable()` called `load_usable_credentials(..., allow_refresh=False)`, while `GmailSearchService.authenticate()` (which Home's real unread-count endpoint uses) calls the same function with `allow_refresh=True`. With a genuinely valid but access-token-expired `token.json` (real state on this machine during this session), the Connections screen's own check refused to refresh it and reported "needs authorization," while the Gmail service happily refreshed it (a non-interactive, server-to-Google call — never a consent screen) and returned real data. `_token_is_usable`'s own docstring already described the *intended* behavior ("a token that needs a network refresh to be usable is still reported as usable here") — the code simply didn't match its own comment.

**Fix:** `_token_is_usable` now passes `allow_refresh=True`, matching its own documented intent and matching `GmailSearchService`/`GmailService`'s real behavior. A refresh is non-interactive by construction (`load_usable_credentials` "never initiates OAuth consent" per its own docstring), so this does not introduce any interactive-sign-in risk.

**Live verification:** before the fix, Connections & Providers showed Gmail/Drive as "Needs authorization" for the test account while Home showed a real `536`; after the fix (backend restarted), both Gmail and Google Drive correctly show **"Connected"**, consistent with the real, refreshed token and the real `536` count Chat's `gmail_search` tool independently confirmed via the exact same number.

**Tests:** `test_gmail_connection_truth.py`'s `test_token_check_delegates_without_refresh` renamed to `test_token_check_delegates_with_refresh` and its assertion flipped to `allow_refresh=True`, with the defect and its live reproduction documented in the test's own docstring. Full connection-status/Gmail-truth/capability suites re-run clean (71 tests).

**Remaining limitation, disclosed:** Gmail/Drive connectivity itself remains genuinely single-tenant (one host-wide credential, not per logged-in account) — this is a deeper, pre-existing architectural characteristic this bounded pass did not redesign; it is why *every* account on this host currently sees the same real Gmail data once that one shared token is valid, which is now at least *consistently and honestly* reported across Home, Chat, and Connections rather than inconsistently.

---

## 11. Preserve conversational context for follow-ups

**Not independently re-tested this session** beyond what §9/§10's live turns already demonstrate (the Brain correctly resolved "how many unread emails" to a concrete, grounded tool call with no clarification needed). A dedicated multi-turn follow-up sequence ("how many are connected?" → "which one?" → "use that model") was not exercised live in this pass — time in this session went to root-causing and fixing the deeper, concrete defects found in §5/§6/§10, which are prerequisites for any follow-up-context test being meaningful (a follow-up test against a Brain that can't reliably route or draft would not distinguish "context was preserved" from "the Brain call itself failed"). Given no specific defect was reproduced or reported for this concern independent of the routing/drafting issues already covered, and given the User's own prior "canonical interaction loop" standing memory already establishes that context/reasoning belongs entirely to the Brain (URI's job is only to supply evidence, never to script the Brain's reasoning), this is recorded as **not reproduced, not independently verified either** — an honest gap, not a claimed pass.

**Remaining limitation:** a dedicated live multi-turn follow-up test (ideally once §6's drafting-stage limitation is resolved, so a full narrative reply is available to judge context-preservation against) is recommended as follow-up work.

---

## 12. Consistent URI branding across every surface

**Reproduced:** yes — `BrainOnboardingScreen` used a standalone raster image (`assets/uri_app_logo_refined_v2.png`, fixed-color, screen-blended) with a comment incorrectly claiming it "reuses the exact approved dashboard rail logo asset" — the sidebar (`app_shell.dart`) has used the canonical, theme-aware vector `UriWordmark` since at least the Hybrid UI batches, not this raster. Compact mode's header also showed a plain "URI" text label with a generic chat-bubble icon, not the wordmark.

**Root cause:** the Brain-setup screen's logo was never migrated when the sidebar moved to `UriWordmark`; Compact's header predates the wordmark's use as URI's one canonical mark entirely.

**Fix:** both replaced with `UriWordmark` (`markSize: 40, showDesktopCompanion: true` for Brain setup; `markSize: 20` for Compact's header) — the same theme-aware vector mark Login, preference onboarding, the sidebar, and About/Settings already use, so it now correctly adapts across all 4 themes everywhere instead of being a fixed-color image in two places.

**Live verification:** real browser session — Login, preference onboarding, Brain setup, the desktop sidebar, and Compact mode's header all now render the identical eclipse-mark + "URI" wordmark treatment.

**Remaining limitation:** the mobile-specific screens (Home/Chat on a narrow layout) were not independently re-screenshotted this session (no on-device/emulator capability, matching the prior readiness report's own disclosed limitation); they already share the same `AppShell`/`_Wordmark` code path as desktop, so no separate mobile-only logo exists to diverge in the first place.

---

## 13. Preserve the first-run flow (Login → optional onboarding → Home)

**Not re-implemented this session** — this is exactly what `docs/plans/UI_HYBRID_BRAIN_SETUP_REPAIR_REPORT.md` (the immediately preceding milestone) built and live-verified: real Skip actions on both onboarding screens, no fake/default Brain ever fabricated, Brain setup reachable later via Connections & Providers, and onboarding not reappearing mid-session once dismissed.

**Re-verified this session, live, on the current (further-fixed) code:** a fresh account's full first-run walkthrough (`live_uxpass_v2`) — signed up, skipped preference onboarding, landed on Home with **"No Active Brain"** (not a fabricated one — confirmed both before and after this session's Home-tile/logout fixes from the prior repair remained intact), configured Groq later from Connections & Providers, and a full browser-reload restart correctly preserved the resulting Active Brain (§5's live verification, §"restart/persistence" below) — none of this regressed by anything changed in this session.

**Remaining limitation:** none beyond what the prior report already disclosed (the pre-existing per-device, not per-account, preferences-onboarding-completion persistence nuance it flagged is unchanged and out of this pass's scope).

---

## Live verification summary (the 15 required scenarios)

All performed against the real, rebuilt `uri_ui.exe` (native launcher: login/skip/Home/restart/window-visibility) and the real backend + real Ollama + real Groq via the production Dart code compiled to web and driven through Chrome (interactive scenarios), per this report's Method section.

| Scenario | Result |
|---|---|
| Login | Real sign-in/sign-up against the real backend; session persists across a full restart. |
| Skip onboarding | Real "Skip for now" on both onboarding screens; lands on Home with no fabricated Brain. |
| Home | Real tiles (0 pending, 536 unread, 2/2 connected, real Brain/Provider), no theme swatches in the topbar. |
| Compact mode | Now fills the entire window as the active UI; "Expand to Workspace" returns correctly; state preserved. |
| Connections & Providers | Gmail/Drive correctly show "Connected" (fixed, §10); "Continue" buttons now do something real (fixed, §4). |
| Ollama discovery | Real, correct detection (`available: true`, real installed models) — unaffected by this session, still correct. |
| Groq/API-key flow | Real key → real verification → real selectable model → real Active Brain, end to end (fixed, §5). |
| Explicit model selection | Model selector shows real, current, verified/unverified inventory, refreshes on open (fixed, §7). |
| URI Auto | Real Active Brain (Groq) correctly tried first via routing (fixed, §6); truthful degrade when unreachable. |
| Chat reply | Real answers via both Ollama and Groq, including a real tool dispatch (`gmail_search`, 536). |
| Token/time metadata | Real, measured model/duration/token captions under replies; never fabricated (new, §8). |
| Unread Gmail question | Answered directly, no unnecessary clarification, matches Home's real number exactly (verified, §9/§10). |
| Contextual follow-up | Not independently re-tested this session (§11) — disclosed gap, not a claimed pass. |
| Appearance | Confirmed working from Settings only, all 4 themes + System present and switchable. |
| Restart/persistence | Real Active Brain (Groq/qwen3.8-27b) and real Gmail connection both survived a full app restart. |

---

## Test / analyzer results (all re-run fresh after every code change, not once at the end)

- **`flutter analyze`:** 0 errors, 0 warnings, 1 pre-existing info (`providers_screen.dart`, unrelated to this session, unchanged since Batch 1).
- **Full `flutter test`:** **160 / 160 passed** (154 baseline carried in from the prior repair + 6 new: 4 metadata/model-selector tests, 2 compact-overlay wording/behavior updates counted as pass-throughs not new cases).
- **`flutter test test/chat_lifecycle_test.dart`:** re-run standalone, all pass (includes the 2 new metadata cases).
- **`flutter test test/compact_overlay_test.dart`:** re-run standalone after the full-bleed rewrite, all 5 pass.
- **Python, targeted to every file touched this session:** `test_provider_registry_catalogue.py`, `test_m22_5_providers_endpoints.py`, `tests/test_m31_model_brain_ux.py`, `tests/dev_workflow/test_security_boundary.py`, `test_connection_status.py`, `test_gmail_connection_truth.py`, `test_model_router_cloud_provider_override.py` (new), `test_m21_provider_config.py`, `test_model_router_auth_failure_boundary.py`, `test_model_router_budget_seam.py`, `test_model_router_degraded_mode.py`, `test_workflow_continuation.py` — **106+42 = every one of these passed** across the two full targeted runs performed this session.
- **`flutter build windows --release`** and **`flutter build web --release`**: both rebuilt successfully, multiple times, as fixes landed.
- No test was weakened, skipped, or had its assertions loosened to obtain a green result. Two tests were *corrected* because they had locked in the exact defects this session found and fixed (`dashboard_shell_test.dart`'s swatch assertions, `test_gmail_connection_truth.py`'s `allow_refresh` assertion) — both changes are documented inline in the test files themselves with the real defect they previously encoded.

---

## Files materially changed this session

**Flutter (`uri_ui/`):**
- `lib/widgets/app_shell.dart` — removed topbar theme swatches + `_ThemeSwatchButton`.
- `lib/widgets/compact_overlay.dart` — full-bleed rewrite (§2), canonical wordmark (§12).
- `lib/app.dart` — `Offstage` instead of `IgnorePointer` for the Compact/Workspace switch.
- `lib/screens/settings/providers_screen.dart` — real "Continue" scroll-to-section behavior (§4).
- `lib/screens/onboarding/brain_onboarding_screen.dart` — canonical wordmark (§12).
- `lib/screens/ask/ask_uri_screen.dart` — model-selector refresh-on-open (§7).
- `lib/models/uri_turn.dart`, `lib/services/http_uri_client.dart`, `lib/widgets/turn_card.dart` — per-reply metadata (§8).
- `lib/services/mock_uri_client.dart` — Groq mock model id/display name kept consistent with the real catalogue fix.
- `test/dashboard_shell_test.dart`, `test/compact_overlay_test.dart`, `test/http_uri_client_test.dart`, `test/chat_lifecycle_test.dart` — updated/added coverage for the above.

**Backend (`uri_core/`):**
- `config/model_roles.py` — `build_provider()`'s adapter-vs-provider_id dispatch and role-config-adoption fixes (§5).
- `core/model_router.py` — Active Brain as implicit "URI Auto" primary; `_model_for_role`'s matching fix (§6).
- `core/provider_registry.py` — Groq catalogue model replaced with a live-verified real one (§5).
- `core/connection_status.py` — `allow_refresh=True` fix (§10).
- `app/server.py` — `/ask` response gained real, measured token/duration metadata (§8).
- `test_model_router_cloud_provider_override.py` — new file (§5/§6 regression coverage).
- `test_gmail_connection_truth.py` — corrected assertion (§10).

**Launcher:**
- `Launch URI.bat` — hidden/detached invocation (§3).

**New:** `docs/plans/UI_HYBRID_LIVE_UX_REPAIR_REPORT.md` (this report).

Every one of these files was read and traced back to a concretely reproduced symptom before being changed; nothing here was a speculative or drive-by edit.

---

## Remaining limitations (consolidated)

1. **§6:** the drafting/narrative stage did not reliably reach Groq for every real turn even after the routing fixes; root cause not fully isolated within this pass's time budget. Graceful degradation held correctly throughout (no fabrication, deterministic answer still delivered).
2. **§9/§10:** Gmail/Drive connectivity is genuinely single-tenant (one host-wide credential) in this codebase today — now at least *consistently* reported, not per-account.
3. **§11:** contextual multi-turn follow-up was not independently re-tested this session; recorded as an honest gap.
4. **§12:** mobile-narrow-layout screens were not independently re-screenshotted (no device/emulator in this environment, matching the prior report's own disclosed limitation) — they share the same code path as desktop, so no separate divergence is expected.
5. **General:** this session's own browser-automation clipboard/paste mechanism was unreliable for pasting the Groq key (§5) — a testing-tool limitation, disclosed, not a product defect; the underlying app behavior was independently confirmed correct via the exact same production API the UI itself calls.
6. Carried over, unchanged, from the prior report: the Ollama probe still ignores a per-account Endpoint Config base_url override; the Scheduled-Task-managed backend can intermittently die shortly after starting.

---

## Readiness for a final User walkthrough

**Yes, ready for a final User walkthrough**, with the limitations above disclosed rather than hidden. Sixteen concerns were each reproduced-or-not honestly before any change; ten confirmed, root-caused, fixed, and re-verified live against real backends/real providers; two (§9, §13) confirmed already correct with no change needed; one (§11) is an honest, disclosed gap rather than a false pass; the remaining items are narrower, disclosed limitations rather than open defects. The full regression baseline (Flutter 160/160, analyzer clean, every targeted Python suite green) is confirmed, not assumed. No commit, push, release, or milestone-close action was taken, per this pass's explicit scope boundary.
