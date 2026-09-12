# M25 — User-Reported Prototype Defects: Root Causes and Remediation Spec

**Status:** ACCEPTED (auto-approved, see History Log in `M25_STATE.md`)
**Author:** Claude (AO-4 Architect / Pre-Auditor)
**Date:** 2026-09-12
**Requested via:** a peer Claude Code session, relaying 6 defects the User found while live-testing the M24 build. Every root cause below was traced against real, running source — including two defects reproduced live against the actually-running backend (`http://127.0.0.1:8000`) and, for the authenticated path, by directly invoking `UriOrchestrator.process_user_input` in-process with the one real saved user (`uri_workspace/users/86f1c37e-.../providers.json`, Active Brain = Ollama/`qwen3:14b`) — not inferred from code reading alone.

**Process note, stated once:** the relaying session's instructions say "no audit required after Codex implements." Per this repository's own standing AO-4 governance (`ORCHESTRATION.md`, project memory), only Claude declares `VERIFIED`/`NOT VERIFIED` and performs the release commit/push — a peer session cannot waive that. Claude will still independently re-audit before any commit/push, exactly as it did for M24 (where that audit caught 3 real regressions the implementer's own self-test missed). Launching the app for the User's inspection on request is unaffected by this and will happen regardless.

---

## §1. Root causes, each traced to real source or a live reproduction

### 1.1 Defect 2 + Defect 6 share ONE root cause: clarification pauses never reach the user

**Reproduced live**, in-process, against the real authenticated user account:
- `"hi"` → `{"response": null, "narrative": null, "execution": {"status": "waiting_for_input", "message": "How may I assist you today?"}}`
- `"My name is Alex"` → `{"response": null, "narrative": null, "execution": {"status": "waiting_for_input", "message": "Is there anything else you would like to share about yourself or your request?"}}`

Both requests reach `orchestrator.py`'s `_apply_clarification_pause` (`:1733-1810`ish) — the Brain's own live reasoning model (this user's actual configured Active Brain, Ollama/`qwen3:14b`) decided each of these needs a clarifying question rather than a direct answer, and that question is real (`response["clarification"]["question"]`, `response["execution"]["message"]`). **But `_apply_clarification_pause` never sets `response["response"]`** — the one field `uri_ui/lib/services/http_uri_client.dart`'s fallback chain (`:427-448`) actually reads before giving up. Narrative drafting is also never attempted for this branch (`_draft_narrative_safely` is not called here at all, unlike the conversational-shortcut branch at `:4813-4830`). Result: the client sees `response: null, narrative: null`, falls through every fallback, and shows the generic **"URI finished processing this request."** — exactly the User's report for both "hi" and stating a name. This is the same defect for any turn that triggers a clarification pause, not specific to greetings or names — a name is simply one more phrase this particular live model chose to ask a follow-up about.

Contrast: an **unauthenticated** curl to `/ask` with `"hi"` (no principal, no Active Brain override — see M24) took a *different* branch (`is_conversational_no_capability_required`, `:4813`) and got a real, correct Brain-authored greeting narrative. This is why the bug is specific to the User's real, logged-in session and did not show up in the M24 audit's own ambient-path spot checks.

**Fix:** `_apply_clarification_pause` must also set `response["response"] = {"message": question}` (mirroring the shape every other response-producing branch already uses), so the clarifying question itself always reaches the user even with no narrative. Additively, also call `_draft_narrative_safely` here (same pattern as the conversational-shortcut branch) so the Brain can phrase the clarifying question naturally rather than only ever showing the raw `question` string — this is squarely "Brain authors the words, runtime supplies the fact" (the canonical interaction loop), applied to a case that was simply missed. Also add the same M24-style `narrative_unavailable_reason` fallback for this branch specifically, so even the raw fallback path stays actionable rather than mute.

### 1.2 A separate, compounding server-boundary bug found during this same investigation: `narrative_unavailable_reason` never reaches the client at all

`uri_core/app/server.py`'s `/ask` handler (`:1138-1146`) explicitly relays a **fixed allowlist** of result keys to the HTTP response: `status, session_id, error, semantic_analysis, execution, response, narrative`. **`narrative_unavailable_reason` — the field M24's Phase A item 3/4 added specifically so the client could show an honest, actionable message instead of the generic fallback string — is not in this list and is silently dropped at the HTTP boundary.** `http_uri_client.dart:483` already reads it; it will simply never be populated over a real network call, only when Claude called the orchestrator directly in-process during verification. **This must be added to the `/ask` response dict** (`"narrative_unavailable_reason": result.get("narrative_unavailable_reason")`) for M24's own fix to have any live effect at all — flagged here as part of this milestone since it directly compounds defect 2.

### 1.3 Defect 1: onboarding has no API-key path, and offers Ollama-testing unconditionally

`uri_ui/lib/screens/onboarding/brain_onboarding_screen.dart` (confirmed by direct read) only ever renders two buttons — "Test local Ollama connection" and "Use Ollama as Active Brain" — with no path to add a cloud API key (OpenAI/Anthropic/Groq/Google/OpenRouter), and no branching UI (it shows the Ollama-test button unconditionally rather than after a "Local Ollama" choice). The working, encrypted-key-entry flow already exists (`_KeyDialog` in `providers_screen.dart`) — this screen simply never reuses it.

**Fix:** restructure `BrainOnboardingScreen` into two explicit choices presented first — "Use a local model (Ollama)" vs. "Use a cloud provider (API key)" — each revealing its own controls only once chosen: Ollama choice reveals exactly today's test/activate buttons; cloud choice reveals a provider picker (reuse the existing `ProviderEntry` catalogue already fetched via `listProviders()`) plus the existing `_KeyDialog`-equivalent inline key entry, then the same `setActiveBrain` call already used for Ollama. No new backend endpoint needed — this is a presentation-layer gap only, over machinery M22.5/M24 already built and already working in `ProvidersScreen`.

### 1.4 Defect 3: no persistent Brain/connection status indicator

Confirmed: no such indicator exists in `app_shell.dart` or the home/chat screen — the only place connection/Active-Brain status is visible today is inside the Providers settings screen itself. This is a straightforward additive UI gap, not a bug.

**Fix:** add a small, persistent status pill to `AppShell`'s header/nav (visible from every tab, not just Settings > Model Providers) showing "Active Brain: `<provider>/<model>` — reachable" / "unreachable" / "not configured", backed by the already-existing `GET /providers/active-brain` + provider `available` field (no new backend work required). Tapping it navigates to the Model Providers settings category (the existing `targetSettingsCategory` mechanism `settings_shell.dart` already uses for exactly this kind of deep-link).

### 1.5 Defect 4: Enter does not submit the chat composer

Confirmed by direct read: `ask_uri_screen.dart`'s composer `TextField` (`:279-296`) has no keyboard-event handling at all — `textInputAction: TextInputAction.newline` and no `Focus`/`KeyboardListener`/`onSubmitted`. Submission is mouse-only today (`IconButton.filled(onPressed: ... onSend(...))`, `:299-319`).

**Fix:** wrap the `TextField` in a `Focus`/`KeyboardListener` (or `Shortcuts`/`Actions`) intercepting `LogicalKeyboardKey.enter`: when Shift is **not** held, call the existing `onSend(controller.text)` and mark the key event handled (suppressing the default newline insert); when Shift **is** held, let the default newline behavior proceed unchanged. A plain `TextField.onSubmitted` is not sufficient here since the field is multiline (`maxLines: 10`) — the IME "submit" action does not fire on every platform's Enter key for a multiline field, so the fix must intercept the raw key event, not rely on `onSubmitted`.

### 1.6 Defect 5: "Work Mode: Admin" does not grant Google Workspace / Connections access — by design, but confusingly named

Traced precisely: `isAdmin` (`uri_client.dart:411`, `bool get isAdmin => role == 'ADMIN';`) gates Connections' Google Workspace controls (`connections_screen.dart:120,134,290,319-320`) and is driven by the account's **`role`** field — set only server-side (`account.role`), with **no user-facing control to change it anywhere in the client** (confirmed: `profile_settings_screen.dart` only *displays* role via a read-only `StatusPill.forRole`, and only exposes a user-changeable **experience tier** selector, a wholly different M22.2 concept). **"Work Mode"**, what the User actually changed, is a *different* field entirely: `getModeInfo()`/`setMode()` (`http_uri_client.dart:1270-1304`) reads/writes a per-session **capability-scoping mode** (`office`/`diagnostic`/`admin`, from `uri_core/config/modes.py`'s `DEFAULT_MODES`) that changes which capabilities are *enabled for dispatch*, and has nothing to do with account authorization. The User's report is accurate as observed, but the underlying behavior is by design and must **not** be "fixed" by making `setMode('admin')` also imply `isAdmin`/`role == 'ADMIN'` — that would let any user silently self-grant real admin authorization (Google Workspace connect/reconnect, Capability Grants) merely by flipping a self-service preference dropdown, a genuine security regression.

**Fix (naming/UX only, no authorization-model change):** rename the `"admin"` mode option's user-facing label away from the word "Admin" (e.g. "Full capability mode" or "All capabilities") so it is never confused with account role, and add one line of copy near the Work Mode selector clarifying that it does not change the account's own authorization/role. If the User's actual goal is to grant themselves real ADMIN role for Google Workspace access, that must go through whatever existing out-of-band admin-provisioning path this repository already uses for `role` (outside this milestone's scope to invent a new self-service role-escalation flow — that is exactly the kind of decision this plan's own escape hatch reserves for the User/architecture review, not a bounded UI fix).

---

## §2. Acceptance criteria

1. **1.1**: a live authenticated request that triggers a clarification pause (e.g. "hi", "My name is X" against a real configured Active Brain) returns a non-null `response`/`response.message` the client can render — reproduced with the same in-process method used to find the bug, plus a new automated test asserting `_apply_clarification_pause` populates `response["response"]`.
2. **1.2**: `narrative_unavailable_reason` present in `/ask`'s HTTP response body whenever the orchestrator result sets it — a new `test_server_ask_endpoint`-style test (or extension of an existing one) asserting the full result-to-HTTP-response field mapping, so a future field addition cannot silently regress the same way again.
3. **1.3**: `BrainOnboardingScreen` widget test exercising both the local-Ollama and cloud-API-key paths, asserting the key-entry control is reachable and calls the same `submitProviderKey`/`setActiveBrain` machinery `ProvidersScreen` already uses.
4. **1.4**: a small widget test asserting the status pill renders and reflects `GET /providers/active-brain` + provider availability.
5. **1.5**: a widget test typing Enter (no Shift) submits, Shift+Enter inserts a newline and does not submit.
6. **1.6**: no code change makes `setMode`/mode selection touch `role`/`isAdmin` anywhere — an AST or grep-based regression check (mirroring `test_capability_authority_boundary.py`'s technique) that `modes.py`/the mode-update endpoint never writes `UserAccountStore`'s `role` field.
7. Full `flutter analyze` (0 issues) / `flutter test` (baseline + new tests) and full Python regression suite (`python -m unittest discover -p "test_*.py"`) — this time run and reported as a genuine full run, not a targeted subset — with no new failures beyond the one already-disclosed pre-existing `test_orchestrator_response_narrative` wording mismatch.
8. No protected file (`dispatcher.py`, `approval_gate.py`, `approval_store.py`, `capability_registry.py`, `capability_resolver.py`, `capability_grants.json`, `provider_keys.py`) touched by this milestone.

## §3. What this plan explicitly does NOT do

- Does not add any new way for a user to self-grant `role == 'ADMIN'` — 1.6's fix is naming/copy only, preserving the existing authorization boundary exactly as-is. Any future request to make Work Mode actually grant real admin authorization is a security-policy decision for the User, not a bounded UI fix.
- Does not change ADR-018 or any capability-authorization boundary.
- Does not re-litigate M24's own two still-outstanding regressions (`capability_planner.py`'s over-broad `web_search` keywords, `orchestrator.py`'s premature `response["status"]` short-circuit) — those remain M24's own remediation items, tracked in `M24_STATE.md`, and should be fixed alongside or before this milestone's work lands in the same working tree, but are not re-specified here.
