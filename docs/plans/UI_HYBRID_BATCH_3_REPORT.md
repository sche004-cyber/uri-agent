# URI Hybrid UI — Batch 3 Implementation Report

**Initiative:** URI Hybrid UI Implementation
**Governing Blueprint:** `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`
**Batch:** Batch 3 — Connections & Providers, Settings, four themes
**Implementer this batch:** Claude (see §0 — explicit, scoped role divergence, User-directed)
**Reviewer:** not yet run (see §8)

---

## 0. Role divergence from the Frozen Blueprint (disclosed, not silent)

The Frozen Blueprint's §1 assigns this initiative to Antigravity (primary implementer), Qwen (review), and states that "Claude and Codex... neither writes UI or reconciled-backend production code for this initiative." Batch 2's report (§0) recorded an explicit, scoped exception for Batch 2 only, stating Batch 3 should resume the normal Antigravity/Qwen loop unless told otherwise.

This batch was again implemented by Claude directly, under an explicit, current-session User instruction ("Implement Hybrid UI Batch 3 exactly according to... You are authorized to: edit Batch 3-owned files; make bounded repairs...; update tests...; run targeted... tests"). Because this instruction directly conflicts with the blueprint's own role table, Claude raised the conflict to the User before proceeding (via a clarifying question) rather than silently either overriding the blueprint or refusing the User's direct instruction. The User confirmed: override for this batch. This is recorded here per the repository's auditable-correction-history convention, scoped to this batch only — it does not revise the general role table for Batch 4, which should resume Antigravity/Qwen unless the User says otherwise again.

---

## 1. Implementation summary

Scope per Blueprint §6 Batch 3: Connections & Providers (§4.6), Settings restructured into two groups (§4.7), four real themes (§4.1/§5), and the M31 gate check (§2) before touching `providers_screen.dart`.

**M31 gate:** confirmed satisfied before starting — `git log` shows `5c31d25 M31 COMPLETE: Model & Brain UX, Claude VERIFIED and released` as an ancestor commit, matching Batch 1/2's own recorded baseline.

### 1.1 Connections & Providers (§4.6)

- New top-level screen `ConnectionsProvidersScreen` (`screens/connections/connections_providers_screen.dart`), wired into `app.dart` at `ShellIndex.connections` (replacing the old bare `ConnectionsScreen`).
- Two sections, side by side on a wide layout (`UriBreakpoints.wide`, ≥900px), stacked on a narrow one: Connections (left) and Providers (right).
- **Connections** (`connections_screen.dart`, restyled): the old 2-column grid-of-cards became one `Card` containing `.list-row`-style entries — avatar icon, name + status pill, description, detail, and the same real action button (Connect/Reconnect/Disconnect) per row — per §4.6's literal "`.card` containing `.list-row` entries" requirement. State/logic (`_authorize`, `_configureCredentials`, real `AppState.authorizeConnection`/`disconnectConnection`/`saveGoogleCredentials` calls) is untouched. No illustrative "Slack" row exists or was added.
- **Providers** (`providers_screen.dart`): embedded **verbatim, unrestyled** — see the disclosed reconciliation in §1.1.1 below.
- Deleted `screens/settings/connections_settings_screen.dart` (the old Settings-embedded wrapper around `ConnectionsScreen`) — orphaned once Connections moved to the top-level screen; verified no remaining importers before deletion.

#### 1.1.1 Disclosed reconciliation: Providers embedded verbatim, not restyled into list-rows

Blueprint §4.6 describes both sections using the same `.card`/`.list-row` visual pattern, and §7 says Batch 3 "absorbs M31's Connect Provider work... restyled into this layout." The real `ProvidersScreen` (M31's shipped work) is materially richer than a status-pill list: per-provider API-key dialogs, endpoint/model-override config dialogs, fallback-routing configuration, Active-Brain selection with confirmation, and usage-limit warnings — all backed by real, tested backend contracts (`m22_5_providers_test.dart`, `m22_8_basic_provider_tier_test.dart` pump this exact screen directly and were not touched).

Flattening this into flat `.list-row` entries (avatar/name/status/trailing pill) would either drop real functionality (key configuration, fallback routing, active-brain switching) or require rebuilding it from scratch inside a constrained row — both of which the blueprint's own governing rule (§5: "no parallel/fake functionality"; §6 Batch 3's completion gate: "no fake inventory or auth relaxation") argues against, and rebuilding a working, tested M31 surface is exactly the kind of "substantial remediation" this batch is not authorized to invent architecture for.

**Decision:** `ProvidersScreen` is embedded as-is (no internal changes) as the right-hand section. The "restyle into this layout" §7 asks for is read as this screen's two-section structural layout (position, sizing, side-by-side placement), not a rebuild of Providers' internals — the same precedent already established in this codebase by `ConnectionsSettingsScreen` (now removed) reusing `ConnectionsScreen` verbatim rather than duplicating its logic. Flagged here per §9 for the reviewer's attention as a reconciliation, not a silent substitution.

### 1.2 Settings restructured into two groups (§4.7)

- `settings_shell.dart`: categories now carry a `_SettingsGroup` (`account`/`system`) and both the wide master-detail sidebar and the narrow list render a group header ("ACCOUNT" / "SYSTEM") above each group's entries.
- **Account:** Profile, Preferences, Memory, Memory & Context.
- **System:** URI (Server), Capabilities, Diagnostics, About, Appearance (new), plus Capability Grants when ADMIN-gated (unchanged gating).
- **Removed:** the "Connections" and "Model Providers" Settings categories (moved to §1.1's new top-level screen). No "Tools & Skills" category exists or was added (it never did).
- Two Home-tile/suggestion navigation targets that pointed at `Settings → Model Providers` (`home_screen.dart`'s "BRAIN / PROVIDER" tile and the "Configure primary Brain provider" suggestion) were retargeted to `ShellIndex.connections`, since that category no longer exists.

### 1.3 Four real themes (§4.1/§5)

- `theme/uri_theme.dart`: added `UriThemeChoice` (`system`, `graphite`, `deepNavy`, `slateTeal`, `lightProfessional`) and four real `UriColors` palettes, replacing the old binary `light`/`dark` palettes entirely.
- `resolveUriColors(choice, platformBrightness)`: `system` resolves to Graphite (dark) or Light Professional (light) depending on the OS signal; the other four choices are pinned regardless of platform brightness.
- `buildUriTheme(UriColors palette)` now takes a resolved palette directly (brightness is derived via `ThemeData.estimateBrightnessForColor`), rather than a bare `Brightness`.
- `theme_store.dart`: migrates the old `uri.themeMode` key (`dark`/`light`/`system`) to the new `uri.themeChoice` key — old `dark` → Graphite, old `light` → Light Professional, old `system` stays `system`; an unrecognized/garbage legacy value falls back to the recorded default, Graphite. A new-key value always takes priority over a stale legacy key.
- `app_state.dart`: `themeMode`/`setThemeMode(ThemeMode)` replaced with `themeChoice`/`setThemeChoice(UriThemeChoice)`.
- `app.dart`: `MaterialApp` now resolves the active palette once per rebuild (`resolveUriColors(appState.themeChoice, platformBrightness)`) and forces it via `theme` alone (`themeMode: ThemeMode.light` is a deliberate no-op selector, not a real "light mode" claim — see the doc comment at the call site); `didChangePlatformBrightness` triggers a rebuild when the OS signal changes while `system` is selected.
- `app_shell.dart`'s topbar: the 4 swatch buttons now call `state.setThemeChoice(...)` with the real enum values (previously 3 of the 4 silently called `setThemeMode(ThemeMode.dark)` regardless of which swatch was tapped — a Batch 1 placeholder). Added a selected-state ring so the active theme is visibly indicated, which the placeholder never did.
- New `screens/settings/appearance_settings_screen.dart`: the 4-theme picker + implicit `system` follow-OS option, added to Settings → System. The old Light/Dark/System `SegmentedButton` was removed from `preferences_settings_screen.dart` (moved here per §4.7).
- Preference migration behavior matches §6 Batch 3 exactly: existing stored choice preserved; old `dark`→Graphite, old `light`→Light Professional (using this blueprint's palette values, which are the ones implemented, as of freeze); unknown/old keys fall back to the recorded default (Graphite); `system` keeps OS-following until an explicit 4-theme choice is made.

#### 1.3.1 Disclosed judgment call: derived color tokens

`Palettes.dc.html` (read directly from the published Hybrid Artifact) gives canvas/surface/elevated/border/ink/accent per theme plus each theme's success/warning pill tones — but not `inkSoft`/`inkFaint`/`accentSoft`/`accentInk`/`danger`/`dangerSoft`, which `UriColors` also requires. These were derived, not taken verbatim from the reference:
- `inkSoft`/`inkFaint`: ink blended toward canvas at 30%/55%.
- `accentSoft`: surface blended toward accent at 12–18%.
- `accentInk`: accent lightened toward white (dark themes, ~35%) or darkened toward black (Light Professional, ~15%), for contrast against `accentSoft`.
- `danger`/`dangerSoft`: reused verbatim from this app's previously-accepted dark (`#FF8080`/`#3B1E1E`) and light (`#C23B3B`/`#FBE9E9`) error colors, since no per-theme error tone exists in the reference at all — reusing known-working, already-used-elsewhere values rather than inventing four new untested reds.

This is a reviewable judgment call, not literal artifact data — flagged here per §9, same footing as Batch 2's risk-bucket-mapping and empty-state-string disclosures.

---

## 2. Files materially changed

Production:
- `uri_ui/lib/theme/uri_theme.dart` — 4 real palettes, `UriThemeChoice`, `resolveUriColors`, `buildUriTheme` signature change.
- `uri_ui/lib/services/theme_store.dart` — rewritten for `UriThemeChoice` + legacy migration.
- `uri_ui/lib/services/app_state.dart` — `themeMode`→`themeChoice`.
- `uri_ui/lib/app.dart` — `MaterialApp` theme binding, platform-brightness observer, `_buildConnections` now returns `ConnectionsProvidersScreen`.
- `uri_ui/lib/widgets/app_shell.dart` — topbar swatches wired to real choices + selected-state indicator.
- `uri_ui/lib/screens/connections/connections_providers_screen.dart` — **new**, combined screen.
- `uri_ui/lib/screens/connections/connections_screen.dart` — grid-of-cards → `.card` of `.list-row`s; no longer owns its own scroll/padding (embedded only).
- `uri_ui/lib/screens/settings/connections_settings_screen.dart` — **deleted** (orphaned).
- `uri_ui/lib/screens/settings/settings_shell.dart` — two-group structure, Connections/Model Providers categories removed.
- `uri_ui/lib/screens/settings/appearance_settings_screen.dart` — **new**.
- `uri_ui/lib/screens/settings/preferences_settings_screen.dart` — Appearance section removed (moved).
- `uri_ui/lib/screens/home/home_screen.dart` — 2 navigation targets retargeted from `Settings→Model Providers` to `ShellIndex.connections`.

Tests:
- `uri_ui/test/connections_screen_test.dart` — navigation retargeted from the retired 'Email' label to 'Connections & Providers'; `ensureVisible` added before tapping Connect (the combined screen is taller than the viewport at this content volume); added a same-screen Providers-section assertion.
- `uri_ui/test/m22_ui_parity_test.dart` — same navigation retarget, 2 cases.
- `uri_ui/test/m24_providers_settings_shell_test.dart` — retargeted from `SettingsShell`+tap to `ConnectionsProvidersScreen` directly (no tap needed; both sections render at once on a wide layout).
- `uri_ui/test/redesign_test.dart` — Settings category list updated (Connections/Model Providers removed, Appearance added, explicit absence assertions added for both plus "Tools & Skills"); appearance test rewritten for the 4-theme picker.
- `uri_ui/test/four_theme_persistence_test.dart` — **new**: default, round-trip, legacy migration (dark/light/system/garbage), new-key-priority, and `resolveUriColors` coverage.

No `uri_core/` (backend) files were touched. No Batch 1/2-owned files (`app_shell.dart`'s navigation logic itself, `home_screen.dart`'s tile set, `ask_uri_screen.dart`, `tasks_screen.dart`, the client files) were modified beyond the two navigation-target line changes in `home_screen.dart` and the topbar theme-swatch wiring in `app_shell.dart`, both required directly by this batch's own scope (Settings restructuring removed the navigation target the tiles pointed at; the topbar swatches are this batch's four-theme deliverable per §4.1/§5).

---

## 3. The 5 known failures: before → after

| Test | Before | Root cause | After |
|---|---|---|---|
| `connections_screen_test.dart`: "Connections shows the three distinct connection states" | FAIL — `find.text('Email')` found 0 widgets | Batch 1 retired the old 13-item manifest nav (which had an "Email" item); no replacement navigation was ever applied to this Batch-3-owned test | PASS |
| `connections_screen_test.dart`: "authorizing a not-connected service updates its state" | FAIL — same | same | PASS |
| `connections_screen_test.dart`: "reconnecting a needs-authorization service updates its state" | FAIL — same | same | PASS |
| `m22_ui_parity_test.dart`: "a non-admin sees enabled connect/reconnect controls..." | FAIL — same | same | PASS |
| `m22_ui_parity_test.dart`: "an admin sees enabled connect/reconnect controls..." | FAIL — same | same | PASS |

All 5 were reconciled by retargeting navigation to the real, current 5-item shell nav's "Connections & Providers" destination — the actual UI behavior these tests check (three distinct connection states, honest Connect/Reconnect controls, no ADMIN-only gating) was never wrong; only the test's route to reach it was stale. No assertion was weakened: every original expectation (`Gmail`/`Connected`/`Needs authorization`/`Not connected` text, `OutlinedButton`/`ElevatedButton` types and labels, `onPressed` non-null) is preserved verbatim.

One additional, not-originally-listed but directly related failure was found and fixed during Batch 3 work: `m24_providers_settings_shell_test.dart` (`tap(find.text('Model Providers'))`) would have broken the moment Model Providers was removed from Settings, per §1.2 — retargeted to the new host before it could regress, since it is squarely inside this batch's Connections & Providers ownership.

---

## 4. Acceptance criteria satisfied (Blueprint §6 Batch 3 completion gate)

| Criterion | Status |
|---|---|
| All service/provider/settings functions reachable | Met — Connections & Providers reachable from the sidebar; all remaining Settings categories reachable, regrouped |
| 4 consistent themes from the verified `Palettes.dc.html` values | Met (§1.3), with the derived-token judgment call disclosed (§1.3.1) |
| M31 non-regression tests pass | Met — `tests/test_m31_model_brain_ux.py` + `tests/dev_workflow/test_security_boundary.py`: 33/33; `chat_lifecycle_test.dart`: passing |
| No fake inventory or auth relaxation | Met — Providers embedded verbatim (real discovered/verified inventory, unchanged verification gating); Connections shows only real Google OAuth status, no illustrative rows |
| Real discovered models (not fixed names) in Providers; unverified disabled with reason | Met — unchanged, `ProvidersScreen` internals untouched |
| Global Active Brain unaffected by any conversation override | Met — unchanged, untouched code path (M31's own contract, not this batch's file) |
| All 4 themes rendered correctly across Home/Chat/Tasks/forms/dialogs, surviving restart | Partially independently verified — `flutter analyze`/`flutter test` confirm the theme extension resolves and persists correctly (§1.3, §5); full visual verification across every screen/dialog was not done via a running app this session (no `flutter run` was launched) — disclosed as untested-by-runtime-observation in §6 |

---

## 5. Test / analyzer / regression evidence

All commands re-run fresh this session.

**Static analysis** (`flutter analyze`, `uri_ui/`): **0 errors, 0 warnings**, 1 pre-existing info (`providers_screen.dart:697:5`, a deprecated `DropdownButtonFormField.value` API — identical to the Batch 1/2 baseline, not touched this batch).

**Batch 3 targeted suites** (per Blueprint §6 Batch 3's list, plus the newly-added four-theme test and the M31/chat regression guard):
```
flutter test test/m22_5_providers_test.dart test/m24_providers_settings_shell_test.dart \
  test/connections_screen_test.dart test/preferences_persistence_test.dart \
  test/settings_server_address_test.dart test/four_theme_persistence_test.dart \
  test/m22_ui_parity_test.dart test/redesign_test.dart test/chat_lifecycle_test.dart
```
Result: **49 / 49 passed.**

**Full `flutter test` (entire `uri_ui/test/` suite, unscoped): 143 / 143 passed, 0 failed.** (Batch 2's baseline was 124/129 with the 5 known failures; this batch's net change is +9 new tests, the 5 known failures fixed, and no new failures introduced.)

**M31/chat non-regression (Python + Flutter):**
- `tests/test_m31_model_brain_ux.py` + `tests/dev_workflow/test_security_boundary.py`: **33 / 33 passed** in 17.28s — identical count to Batch 1/2's independently re-verified baseline.
- `flutter test test/chat_lifecycle_test.dart`: **passing** (included in both runs above).

---

## 6. Remaining defects, blockers, deviations

1. **Role divergence (§0).** Recorded, scoped to this batch, not standing — Batch 4 should resume Antigravity/Qwen per the blueprint unless the User says otherwise.
2. **Providers embedded verbatim, not restyled into `.list-row`s (§1.1.1).** A disclosed, deliberate reconciliation to avoid regressing real M31 functionality. Flagged for reviewer judgment on whether a lighter visual pass (matching card chrome/spacing to the Connections column without touching internal widgets) is wanted in a follow-up, or whether this reconciliation should be written back into the blueprint as the settled answer.
3. **Derived color tokens (§1.3.1).** `inkSoft`/`inkFaint`/`accentSoft`/`accentInk`/`danger`/`dangerSoft` are computed/reused judgment calls, not literal `Palettes.dc.html` data (which doesn't define them per-theme). Reviewable; not verified against the live Artifact pixel-for-pixel.
4. **Mobile/narrow responsive design for Connections & Providers is minimal, not the Batch 4 polish.** `ConnectionsProvidersScreen` stacks the two sections vertically below `UriBreakpoints.wide` so the screen doesn't break at phone width, but the "two full-width sections or a segmented toggle" design explicitly called out as genuine new design work belongs to Batch 4 per Blueprint §8.2 — this batch's stacked fallback is a minimum-viable placeholder, not that deliverable.
5. **Full 4-theme visual verification was not done by launching the running app.** Verified programmatically (palette values resolve and persist correctly, `MaterialApp`'s active theme extension matches the selected choice in a widget test) but not by visually inspecting every screen/dialog under all 4 themes in a live `flutter run` session this batch. Disclosed per the Verification-First standard's "explicit unverified disclosure" requirement — this is missing evidence, and it affects only the "surviving restart" and full visual-consistency portions of the runtime-checks list in §6 Batch 3, not the functional/data-correctness claims above, which are covered by the automated tests.
6. **`reference_dashboard.dart`** (an orphaned, unimported file from before Batch 1's navigation retirement, containing stale `ShellIndex.connections`/`settingsCategory: 'Model Providers'` calls) was left untouched — it is dead code, out of Batch 3's file ownership, and compiles fine as-is (untyped string literal, no reference to the actual removed category) since nothing imports it. Not a regression; noted for whoever eventually cleans up dead files.

No destructive Git operations were performed. Nothing was committed, pushed, or released. Batch 4 was not started.

---

## 7. Deviations from literal blueprint text (summary)

- §4.6's ".list-row" pattern was applied to Connections but not to Providers (§1.1.1) — a scoped, disclosed reconciliation, not a silent substitution.
- §7's "restyled into this layout" for Providers was read as structural (position/sizing within the new two-section screen), not internal-widget restyling — same reconciliation as above.

Both are the "genuinely missing/changed contract" case Blueprint §5/§7/§9 direct implementation to record rather than improvise around; neither required inventing a new architecture or expanding scope beyond Batch 3's file ownership.

---

## 8. Ready for independent review

**Yes**, with the six items in §6 flagged for the reviewer's attention (particularly #2 and #5), and the role divergence in §0 flagged for the User specifically — Batch 4 should resume the blueprint's normal Antigravity/Qwen loop unless the User directs otherwise again.
