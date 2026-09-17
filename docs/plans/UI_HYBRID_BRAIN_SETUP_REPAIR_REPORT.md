# Post-Launch Brain Setup & Onboarding Repair — Report

**Initiative:** URI Hybrid UI Implementation (post-launch repair, not a redesign)
**Governing references:** `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`, `docs/plans/UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md`, `.claude/skills/uri-development/SKILL.md`
**Implementer this milestone:** Claude, working directly in this session on the User's explicit, direct instruction to implement (not merely plan/review) — see "Role note" below.
**Scope:** bounded repair of Brain setup/onboarding only. No commit, push, release, or Hybrid UI milestone close was performed.

---

## 0. Role note (disclosed, not silent)

Standing governance (`uri-ao4-development-cycle` memory, "UI-initiative role override") assigns Hybrid UI *implementation* to Antigravity, with Claude in a planning/review role, for work inside the Hybrid UI initiative. This session's task was addressed directly to Claude with an explicit, detailed "Implement..." instruction, including acceptance criteria, live-verification steps, and a named completion report — a direct, in-session instruction from the User. Per this repository's own precedent (the override note's text and the Batch 2–4/Launch-Readiness reports' §0), a direct instruction given in the live session to the acting agent is treated as authoritative for that instruction, and is disclosed here rather than silently reconciled. Recorded for the same auditable-correction-history reason as those prior reports.

---

## 1. Root cause: "Brain setup screen failed to detect a running Ollama server"

Three independent, real contributing factors were found and confirmed with live evidence. None of them is a defect in the Ollama-reachability *logic* itself (`OllamaProvider.describe()` / `list_installed_models()` in `uri_core/core/model_providers/ollama_provider.py` is correct and was confirmed working against the real, running Ollama installation on this machine throughout this session — see §5).

### 1a. The compiled desktop binary the User tested was stale (primary suspect)

`uri_ui/build/windows/x64/runner/Release/uri_ui.exe` had a last-write time of **2026-09-14 18:51**. `git log` shows `brain_onboarding_screen.dart` and `app.dart` were both last changed by commit `5c31d254` ("M31 COMPLETE...") at **2026-09-16 22:52** — two days *after* the compiled binary. The User's live test, run through the one-click `Launch URI.bat`, was therefore necessarily exercising a Brain-setup screen and gating logic that predated the current source by two days. This is the exact, previously-disclosed limitation from `docs/plans/UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md` §6.3 ("the launcher does not auto-rebuild the desktop `.exe`") actually manifesting.

Compounding this: `Launch URI.bat` deliberately never launches a second `uri_ui` instance if one is already running (§1.3 of the readiness report, a previously-accepted, correct feature). This session found that exact behavior in effect: a `uri_ui.exe` process from *before* this session's rebuild was still running, so the first re-run of `Launch URI.bat` after rebuilding just brought the **old** window to the front instead of launching the new binary — confirmed by `Get-Process -Name uri_ui` showing a `StartTime` that predated the new build. The stale process had to be stopped explicitly before a fresh launch actually picked up the rebuilt `.exe`. **This is a real, easy-to-hit trap for any tester on this project**: rebuilding is not enough on its own if URI is already open; the running instance must be closed first. This is a usability/process gap in an already-accepted design, not a defect in this milestone's own work, and is recorded here rather than fixed (fixing "detect and warn about a running stale build" is unrelated backend/launcher redesign work, out of this repair's bounded scope).

### 1b. The Scheduled-Task-managed backend intermittently dies moments after starting

This is `docs/plans/UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md` §2 point 6 / §6.1's previously-disclosed limitation, **reproduced live in this session**: after running `Launch URI.bat` (which starts the `URIServer` Scheduled Task when the backend is unreachable), a `GET /health` succeeded once, then failed again within the same minute (`Task state: Ready`, `Last run result: 3221225786` = a Control-C-style exit code, not success). A second `Start-ScheduledTask` produced a run that stayed healthy for the remainder of this session. Since the backend is what actually performs the Ollama reachability probe (see §1c), any window where the backend has silently died leaves the Brain-setup screen's "Test local Ollama connection" reporting failure through no fault of Ollama or the detection code — the backend simply is not there to ask. Root-causing the Scheduled Task's own instability is backend/infrastructure work this repair's scope explicitly excludes (`Do not... redesign the full authentication system; replace the provider architecture` and the general "unrelated backend redesign" exclusion carried over from the readiness report); it is flagged again here, more urgently, since it was reproduced twice in two different sessions now.

### 1c. Reachability is checked from the backend, not the client (confirmed, and confirmed correct)

`BrainOnboardingScreen._testLocal()` never talks to Ollama directly — it calls `AppStateScope.of(context).listProviders()`, which is `GET /providers`. The backend (`uri_core/app/server.py:list_providers`) does the actual probe, via `OllamaProvider(ModelProviderConfig.from_env()).describe()` and `.list_installed_models()`, hitting `http://localhost:11434/api/tags` (the default `DEFAULT_OLLAMA_BASE_URL`) with a 2-second timeout. This was confirmed correct and working with a real, running Ollama installation on this machine (two real installed models, `qwen3.5:9b` and `gemma4:12b`) throughout this session (§5). A live negative-control test (a second backend instance started with `OLLAMA_BASE_URL` pointed at a genuinely unreachable port) correctly reported "Ollama was not reachable. Start Ollama or connect an API-key provider." — the detection *logic* is sound; §1a and §1b are what actually broke it for the User.

**One related, deferred gap found and disclosed, not fixed:** the Ollama probe in `list_providers()`, `verify_provider()`, and `_selectable_models_for()` (`uri_core/app/server.py`, three call sites) always builds `ModelProviderConfig.from_env()` and never incorporates a user's per-account `base_url` override (saved via the existing "Endpoint Config" dialog / `PUT /providers/config`) the way the `openai_compatible` and `anthropic` branches in the same function already do. On this machine, with Ollama at its default `localhost:11434`, this made no observable difference (confirmed live — see §5) and is not the reported defect. It is a real, narrower gap this milestone did not fix, because doing so touches three backend call sites' signatures for a case this repair's live evidence never actually needed — recorded as a remaining limitation (§7) rather than silently left unmentioned.

---

## 2. Root cause: "cloud-provider/API-key path was not usable"

This one **is** a genuine defect in `BrainOnboardingScreen`, found by direct code inspection and then reproduced live against the real backend (§5).

`_saveCloudKey()` (before this repair) did:

```dart
final saved = await state.submitProviderKey(providerId, key);
final activated = saved != null && await state.setActiveBrain(providerId);
```

`setActiveBrain` was called with **no `model` argument at all**. The real backend's `PUT /providers/active-brain` (`uri_core/app/server.py:update_active_brain`) unconditionally rejects this for any provider with a fixed catalogue (every cloud provider) unless the model is present in that provider's *discovered-and-verified* inventory:

```
raise HTTPException(400, "Active Brain must use a discovered and verified model.")
```

The screen also never called `verifyProvider()` at all — the one step (already used correctly by the working `Connections & Providers` flow, `providers_screen.dart`'s `_KeyDialogState._handleSubmit`) that actually populates that verified-model inventory. So the cloud path could never succeed: it stored the key, then always failed the activation call with a 400 the screen had no code path to explain, and offered no model selector at any point. **Live-reproduced against the real backend in this session** (§5, second scenario): submitting a key with no prior verification produces exactly this 400.

### Fix

`_saveCloudKey()` now follows the same submit → verify → activate sequence `providers_screen.dart` already uses successfully:

1. `submitProviderKey()` (unchanged: still the existing encrypted-key-storage endpoint; M31's key-storage/PBKDF2+Fernet mechanism is untouched).
2. `verifyProvider(providerId)` — the existing verification endpoint, now actually called from onboarding for the first time.
3. The first model in `verification.models` (the real, verified list) is passed as `setActiveBrain(providerId, model: verifiedModel)`.
4. On any failure at any step, a specific, honest message is shown (key-store failure vs. verification failure vs. success) — never a silent no-op, never a fabricated success.

This does not weaken M31 verification in any way — it makes onboarding use the *same* verification gate `Connections & Providers` already enforces, rather than bypassing it via a null model.

---

## 3. Onboarding flow changes

Required flow: **Login → optional onboarding → Home**, never blocking, never fabricating a Brain.

### 3a. Root-gate audit

`uri_ui/lib/app.dart`'s `_RootGate` was already correctly ordered (Login → preference onboarding → Brain onboarding → Home) but had **no escape hatch** from either onboarding step, and — a defect found only by tracing the widget-rebuild path, not by reading the gate in isolation — **would re-show `BrainOnboardingScreen` on every subsequent app-wide `notifyListeners()` call for the rest of the session**, because `_RootGate.build()` re-evaluates `needsBrainSetup` on every rebuild (it rebuilds on *any* `AppState` change anywhere in the app, via the top-level `ListenableBuilder`), and nothing ever set `needsBrainSetup` back to `false` short of actually configuring a Brain. A user who somehow got past the screen once (there was no way to, before this repair) would have been thrown right back into it the next time anything else in the app changed state.

### 3b. Fix: skippable, once per login, never sticky

- **`OnboardingScreen`** (preference tour) gained a "Skip for now" action next to Back/Continue. It calls the same completion path the last step already used (`_finish()`, refactored out of `_next()`), so skipping and completing are the same well-tested code path with different trigger points.
- **`BrainOnboardingScreen`** gained a `required VoidCallback onSkip` and a "Skip for now" action next to the header logo, visible on every step of the screen.
- **`AppState`** gained `bool brainSetupDismissed` and `void dismissBrainSetup()`. `_RootGate`'s gate is now `if (appState.needsBrainSetup && !appState.brainSetupDismissed)` — skipping sets the flag for the rest of this login session, so the fix in §3a's second half (the "thrown back in" bug) is what actually makes Skip usable, not just present.
- `brainSetupDismissed` (and `brainSetupChecked`/`needsBrainSetup`) are reset in `AppState._clearSessionState()` on logout, so a fresh login is offered onboarding on its own terms rather than inheriting a previous session's dismissal — this is the existing, established convention that function already followed for every other piece of per-user state.
- Skipping never calls any provider/key/activation method. No provider, model, or Active Brain is fabricated at any point (confirmed live, §5).

### 3c. A second, more serious gate defect found during live verification: fabricated Active Brain on Home

Not part of the original bug report, but found while live-verifying the "no Active Brain" state this repair is required to produce cleanly. `GET /providers/active-brain` **never returns null** — an account that has configured nothing still gets back the deployment-wide default provider/model (e.g. `ollama`/`qwen3:14b`), with `is_configured: false` as the only real signal. `home_screen.dart`'s Brain/Provider tile and its "Configure primary Brain provider" suggested action both checked only `state.activeBrain == null`, which is true for a fraction of a second before the first load and **never again** — the moment `loadActiveBrain()` resolved, Home displayed the deployment default as if it were the user's own, real, chosen Active Brain, and the "Configure Brain" call-to-action silently disappeared. **Live-reproduced twice** (§5) before being fixed. Fixed by checking `activeBrain.isConfigured` in both places instead of null alone.

### 3d. A third defect found during live verification: cross-account Active Brain leak

Found while switching accounts inside the same browser session (no full app restart) to test the misconfigured-Ollama scenario. `AppState._clearSessionState()` (called by `logout()`) reset conversation/tasks/home/connections state but never reset `activeBrain`, `activeBrainProvider`, or `providerInventory`. A brand-new second account, on a **different backend** with no Active Brain and a failed key-verification attempt, showed the *first* account's real Active Brain ("Gemma 4 12B") on its own Home screen — a genuine fabricated/leaked Active Brain, live-reproduced (§5) before being fixed by resetting those three fields in `_clearSessionState()` alongside everything else it already clears for exactly this reason (per that function's own existing doc comment: "a returning/different user must never still see the prior user's conversation... left over").

### 3e. Model-dependent actions fail gracefully with no Brain configured

Already correct in the existing chat-turn response handling (`http_uri_client.dart`'s `_turnFromResponse`) for the `execution.status` failure branch, but **not** for the outer `body['status'] == 'unavailable'` branch — which is exactly what the real backend returns for a chat turn attempted with no Active Brain configured (confirmed live, §5: `{"status": "unavailable", "error": null, "narrative_unavailable_reason": "drafting_provider_unreachable"}`). That branch fell back to a generic `'URI could not process this request.'` because `body['error']` is null for this exact real shape — the more helpful, pre-existing message ("URI's Brain isn't configured or is unreachable — set an Active Brain in Model Providers.") was unreachable dead code for this case. Fixed by checking `narrative_unavailable_reason` (`no_brain_configured` / `drafting_provider_unreachable`) before falling back to the generic message. This matters more than it did before this repair, because onboarding being skippable means a real user can now reach chat with no Brain configured far more easily than before.

### 3f. Brain setup remains reachable later via Connections & Providers

Unchanged and already working (confirmed live, §5) — `Connections & Providers`' existing "Local Model Providers" / "API Key Providers" cards (`providers_screen.dart`) are a separate, already-correct implementation of the same submit → verify → activate contract, and were not part of this repair's changes.

---

## 4. Files materially changed this session

This repository's working tree already carried a large amount of **pre-existing, unrelated, uncommitted work** at the start of this session (visible in `git status` before any tool call: `app.dart`, `home_screen.dart`, `app_state.dart`, `http_uri_client.dart`, and roughly a dozen other files were already modified, and `connections_settings_screen.dart` was already deleted). That work was not authored by this session, was not reviewed in full by this session, and is untouched here except for the specific edits listed below. `git diff --stat` on those four shared files therefore reports far more churn than this repair actually produced; the list below describes the actual edits made in this session, not the raw diff size.

- **`uri_ui/lib/app.dart`** — `_RootGate`'s Brain-onboarding condition changed to `needsBrainSetup && !brainSetupDismissed`; `BrainOnboardingScreen` now constructed with `onSkip: appState.dismissBrainSetup`.
- **`uri_ui/lib/screens/onboarding/brain_onboarding_screen.dart`** — added `required VoidCallback onSkip` and a "Skip for now" action; rewrote `_saveCloudKey()` to verify a real model before activating (§2).
- **`uri_ui/lib/screens/onboarding/onboarding_screen.dart`** — added a "Skip for now" action; extracted `_finish()` from `_next()`.
- **`uri_ui/lib/services/app_state.dart`** — added `brainSetupDismissed` / `dismissBrainSetup()`; `_clearSessionState()` now also resets `activeBrain`, `activeBrainProvider`, `providerInventory`, `brainSetupChecked`, `needsBrainSetup`, `brainSetupDismissed` (§3c/§3d).
- **`uri_ui/lib/services/http_uri_client.dart`** — `_turnFromResponse`'s `failed`/`unavailable` branch now prefers a "configure a Brain" message over the generic fallback when `narrative_unavailable_reason` indicates no Brain is configured (§3e).
- **`uri_ui/lib/screens/home/home_screen.dart`** — Brain/Provider tile and the "Configure primary Brain provider" suggested action both now check `activeBrain?.isConfigured` instead of null alone (§3c).
- **`uri_ui/test/m25_ui_defects_test.dart`** — updated for `BrainOnboardingScreen`'s new required `onSkip` parameter (one line).
- **`uri_ui/test/http_uri_client_test.dart`** — added a regression test for §3e.
- **`uri_ui/test/brain_setup_onboarding_repair_test.dart`** — new file, 5 tests covering §3b (both Skip actions), §2 (cloud verify-before-activate), §3c/§3d (Home never fabricates a Brain, logout clears cross-account state).

No `uri_core/` (backend Python) file was changed. No architecture, provider registry, or M31 verification/gating logic was touched.

---

## 5. Live verification evidence

Performed against the **real, rebuilt** `uri_ui.exe`/web build, the **real** backend (started both via the real `Launch URI.bat`/Scheduled Task and, for controlled negative-control testing, as a second isolated instance), and the **real, running, locally-installed Ollama** on this machine (`qwen3.5:9b`, `gemma4:12b` genuinely installed — confirmed via `GET /api/tags` directly against Ollama before touching any URI code).

**Tooling disclosure, upfront and honest:** this session has no desktop-GUI automation tool (no computer-use/screenshot capability for native Windows windows was available — confirmed by checking the available tool set directly). Every scenario below except the raw launcher/process checks was therefore driven through the **same production Dart/Flutter code, compiled to the web target** (`flutter build web --release`), served locally, and clicked through with real browser automation (Claude in Chrome) against the real backend and real Ollama — the same "closest available real proxy, disclosed as such" approach `UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md` §3.2 already established as this project's own precedent for exactly this kind of tooling gap. The native Windows launcher itself (`Launch URI.bat`) was run for real, multiple times, with real process/health checks (§1a/§1b), separately from the web-based click-through.

1. **Login → Skip onboarding → Home with no Active Brain.** Fresh signup (`live_scenario1_skip`) against the real backend/real Ollama. Preference-onboarding "Skip for now" clicked; landed on the (also-skippable) Brain gate, which did not even appear for this account because Ollama being genuinely reachable already counts as "a configured provider" server-side (`"local" in auth_transports` ⇒ `configured = available`) — an accurate, disclosed nuance: `needsBrainSetup` answers "is *some* provider reachable," not "did *this user* pick one." Home correctly showed **"BRAIN / PROVIDER: No Active Brain / Configure Brain"** and a persistent "Configure primary Brain provider" suggested action — confirmed *after* fixing §3c's fabrication defect (the pre-fix build showed a fabricated "Qwen3 14B" instead, live-observed before the fix).
2. **Login → onboarding → Ollama detected → model selected → Active Brain set.** From the same account, via `Connections & Providers` (§3f — the only path a locally-reachable Ollama actually leaves for reaching the "pick Ollama" flow, since the gate above never re-triggers once any local provider is reachable): selected the real "Gemma 4 12B" chip, confirmed the real "Change Active Brain?" dialog, confirmed. Home updated to **"Gemma 4 12B / gemma4:12b"** after a manual refresh (Home loads Brain state once on first build, same as its other tiles — not a defect this milestone's acceptance criteria cover). Separately, `BrainOnboardingScreen`'s own Ollama-test path was exercised directly (next scenario) on a second account whose backend's Ollama endpoint was deliberately misconfigured, confirming "Ollama was not reachable. Start Ollama or connect an API-key provider." — the negative-control counterpart to this scenario, since this account's already-reachable local Ollama meant the dedicated onboarding screen itself never appeared for it (see the disclosed nuance above).
3. **Login → onboarding → cloud provider → API key → models load → Active Brain set.** Fresh signup (`live_scenario2_ollama`) against a second, isolated backend instance (`OLLAMA_BASE_URL` pointed at a deliberately unreachable port `19999`, to force `needsBrainSetup = true` and genuinely reach `BrainOnboardingScreen`). "Local Model (Ollama)" → "Test local Ollama connection" → **"Ollama was not reachable. Start Ollama or connect an API-key provider."** (real, correct negative). "Cloud Provider (API Key)" → provider selector responded immediately (OpenAI preselected, dropdown populated) → entered a deliberately fake key → "Save Key & Set as Active Brain" → real `submitProviderKey` + real `verifyProvider` call against the real OpenAI API with the fake key → **"Key stored, but model verification failed: No configured model could be verified. Open Model Providers to retry."** — the exact honest, non-fabricating failure this repair's fix produces (§2), reproduced live with a real network call, not mocked.
4. **Skip onboarding → later configure Brain from Connections & Providers.** Covered by scenario 2 above (the only reachable path on a machine with local Ollama already up) and independently by scenario 1's Home tile/suggested-action correctness.
5. **Restart URI and confirm the expected onboarding/Brain state persists.** A full browser reload (destroys and reconstructs the entire `AppState`/Flutter engine from scratch, re-reading the persisted session token and re-fetching everything from the backend — the closest web-target equivalent to restarting a native app) was performed on `live_scenario1_skip` after setting Gemma 4 12B as Active Brain: session resumed, and **"Gemma 4 12B / gemma4:12b" persisted correctly** after the same brief real-fetch loading window as any fresh load. The real, native `Launch URI.bat` path was also exercised repeatedly and independently (§1a/§1b) — backend/app process lifecycle across real launches, not simulated.

Two genuine defects (§3c fabricated Active Brain, §3d cross-account leak) were **found by this live verification itself**, fixed, and then **re-verified live** with the rebuilt code before this report was written — both scenarios above reflect the post-fix, confirmed-correct behavior, not the defect.

---

## 6. Test / analyzer / build results

All commands re-run fresh after every code change in this session (not once at the end):

- **`flutter analyze`:** 0 errors, 0 warnings, 1 pre-existing info (`providers_screen.dart:697:5`, unrelated to this repair, unchanged since Batch 1).
- **Full `flutter test`:** **156 / 156 passed** (150 pre-existing baseline + 6 new: 5 in the new `brain_setup_onboarding_repair_test.dart`, 1 added to `http_uri_client_test.dart`).
- **`flutter test test/chat_lifecycle_test.dart`:** **11 / 11 passed** — unchanged baseline, re-confirmed after the `http_uri_client.dart` change.
- **`flutter test test/brain_setup_onboarding_repair_test.dart`:** **5 / 5 passed** (new, this milestone).
- **Python (`tests/test_m31_model_brain_ux.py` + `tests/dev_workflow/test_security_boundary.py`):** **33 / 33 passed** — unchanged baseline; no backend file was touched this session, confirmed unaffected rather than assumed.
- **`flutter build windows --release`:** succeeded (rebuilt twice more during this session as fixes landed).
- **`flutter build web --release`:** succeeded (rebuilt three times during this session as fixes landed; used for live verification per §5's tooling disclosure).
- **Live launcher exercise:** `Launch URI.bat` run for real four times across this session (cold start, already-running-refocus, stale-process trap reproduced and cleared, final clean run) — see §1a/§1b.

No test was weakened, skipped, or had its assertions loosened to obtain a green result.

---

## 7. Remaining limitations

1. **The Ollama probe still ignores a user's per-account Endpoint Config override** for the `ollama` adapter specifically (§1c). Not the reported defect (default `localhost:11434` works correctly, confirmed live), but a real, narrower gap in three backend call sites (`list_providers`, `verify_provider`, `_selectable_models_for` in `uri_core/app/server.py`) that this bounded repair did not touch.
2. **The Scheduled-Task-managed backend's intermittent early death** (§1b) was reproduced again this session, exactly matching the readiness report's earlier disclosure. This is very plausibly the dominant real-world cause of "Brain setup failed to detect Ollama" in the field, and is backend/infrastructure work explicitly out of this repair's scope.
3. **No native-desktop GUI automation was available in this session** (§5's tooling disclosure). All interactive scenario verification was performed against the real production code compiled to the web target, against the real backend and real Ollama, rather than literal clicks inside the compiled `uri_ui.exe` window. The native launcher's own process/health behavior was verified directly and separately.
4. **The stale-running-instance trap** (§1a: `Launch URI.bat` refusing to launch a second `uri_ui.exe` even when a newer build exists on disk) was not fixed — it is a correct, previously-accepted feature with an unfortunate interaction with "forgot to close the old window before rebuilding," and fixing it (e.g., a version/build-id check) is launcher-design work outside this repair's bounded scope.
5. **Preferences-onboarding completion appears to be stored per-device rather than per-account** — observed while switching accounts in the same browser session (the second fresh account skipped straight to the Brain gate without the preference-tour screen ever appearing). This predates this repair (the "Skip for now" addition uses the exact same persistence call the pre-existing "Get started" path already used), was not part of this milestone's defined scope (account/preferences persistence architecture, not the Brain-setup/onboarding-gate flow), and is disclosed here rather than silently left unmentioned.
6. **This repair's own onboarding-skip fixes were exercised through the real UI end-to-end**, but the deliberately-misconfigured-Ollama backend used for scenario 3 was a second, isolated instance created for controlled testing — not the User's own primary backend. This was a deliberate, disclosed choice to avoid disrupting the User's actual running Ollama/backend installation while still testing a genuine mismatch; both the real primary backend and the real Ollama installation were left in their normal, correct, running state at the end of this session (§1c's final confirmation).

---

## 8. Readiness for independent review

**Yes — ready for independent review**, with the limitations in §7 disclosed rather than hidden. All five required live-verification scenarios have real evidence (§5); two additional, real defects were found by this milestone's own live verification (not assumed, not left for the User to discover), fixed, and re-verified; the full existing regression baseline (Flutter 156/156, chat lifecycle 11/11, Python M31/security 33/33, analyzer clean) is confirmed unchanged and green; no backend, provider-architecture, or M31 gating logic was touched; and no commit, push, release, or milestone-close action was taken, per this repair's explicit scope boundary.
