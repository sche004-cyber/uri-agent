# URI Hybrid UI — Batch 3 Independent Review

**Initiative:** URI Hybrid UI Implementation  
**Governing Documents:**
- `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`
- `docs/plans/UI_HYBRID_BATCH_3_REPORT.md`
- `.claude/skills/uri-development/SKILL.md`

**Reviewer:** Antigravity (independent inspection)  
**Date:** 2026-09-17  
**Verdict:** **`BATCH_3_ACCEPTED`**

---

## 1. Executive Verdict

**Verdict: `BATCH_3_ACCEPTED`**

Batch 3 has faithfully delivered all requirements for Connections & Providers (§4.6), Settings restructuring into two groups (§4.7), four real themes with persistence and legacy migration (§4.1/§5), and preservation of M31 model/provider contracts (§2/§7). All 5 previously failing tests from Batch 2 were genuinely reconciled without weakening assertions. The full Flutter test suite passes completely (143/143), Python backend regressions pass (33/33), static analysis is clean (0 errors, 0 warnings), and no backend or out-of-scope files were modified.

Batch 3 is **accepted without fixes**. Batch 4 may now begin.

---

## 2. Independently Verified Findings

### 2.1 Connections & Providers (§4.6)
- **Combined Screen Architecture:** `ConnectionsProvidersScreen` (`uri_ui/lib/screens/connections/connections_providers_screen.dart`) is mounted at `ShellIndex.connections`. On wide layouts (≥900px), it presents Connections and Providers side-by-side in a responsive row; on narrower layouts, it stacks them.
- **Connections Section:** `ConnectionsScreen` was restyled from a grid-of-cards into a single `Card` containing `.list-row` rows (avatar, service name, status pill, description, detail, and action button), satisfying §4.6. All underlying OAuth and connection-management calls (`authorizeConnection`, `disconnectConnection`, `saveGoogleCredentials`) remain intact. Only real Google/Gmail OAuth status is rendered; no fake rows (such as illustrative Slack) exist.
- **Providers Section (M31 Preservation):** `ProvidersScreen` is embedded as-is in the right-hand column. This preserves all M31 capabilities—provider API-key dialogs, custom endpoints, model overrides, fallback routing, and Active Brain selection—without loss of functionality.
- **Cleanup:** The orphaned `screens/settings/connections_settings_screen.dart` was deleted cleanly.

### 2.2 Settings Implementation (§4.7)
- **Two-Group Hierarchy:** `settings_shell.dart` categorizes settings into `Account` and `System`:
  - **Account:** Profile, Preferences, Memory, Memory & Context.
  - **System:** URI (Server), Capabilities, Diagnostics, About, Appearance, plus ADMIN-gated Capability Grants.
- **Category Pruning:** Connections and Model Providers were removed from Settings (now in the top-level destination). No illustrative "Tools & Skills" category was added (and test assertions verify its absence).
- **Appearance Settings:** New `AppearanceSettingsScreen` placed under System settings, hosting the 4-theme picker and system-following option.
- **Home Navigation Updates:** Navigation links from Home tiles ("BRAIN / PROVIDER" and Brain setup suggestion) that previously pointed to `Settings → Model Providers` were cleanly redirected to `ShellIndex.connections`.

### 2.3 Four-Theme Support (§4.1/§5)
- **Palettes:** Four real themes implemented in `uri_theme.dart` (`Graphite`, `Deep Navy`, `Slate + Teal`, `Light Professional`) matching the hex values in `Palettes.dc.html`, plus `System` mode that resolves dynamically according to platform brightness.
- **Theme Store & Migration:** `ThemeStore` migrates legacy `uri.themeMode` (`dark` → Graphite, `light` → Light Professional, `system` → System; unknown/corrupt keys fall back to Graphite default). Explicit selections are persisted to `uri.themeChoice`.
- **Shell & App Integration:**
  - `app_shell.dart` topbar renders 4 theme swatch buttons with the exact accent colors, active-selection ring indicators, and calls `state.setThemeChoice(choice)`.
  - `app.dart` binds the resolved palette to `MaterialApp` and observes platform brightness changes when in System mode.
  - `app_state.dart` manages `themeChoice` and `setThemeChoice`.

### 2.4 Reconciliation of the 5 Pre-Existing Test Failures
All 5 failing tests from Batch 2 were independently investigated and verified:
1. `test/connections_screen_test.dart` ("Connections shows the three distinct connection states")
2. `test/connections_screen_test.dart` ("authorizing a not-connected service updates its state")
3. `test/connections_screen_test.dart` ("reconnecting a needs-authorization service updates its state")
4. `test/m22_ui_parity_test.dart` ("a non-admin sees enabled connect/reconnect controls and no admin-only notice")
5. `test/m22_ui_parity_test.dart` ("an admin sees enabled connect/reconnect controls and no notice")

**Root Cause:** Each test failed on `find.text('Email')`, attempting to navigate using the retired 13-item navigation.  
**Resolution:** Updated test navigation to `find.text('Connections & Providers')`.  
**Integrity Verification:** None of the assertions were weakened. Tests assert real UI text (`Gmail`, `Connected`, `Needs authorization`, `Not connected`), button types (`ElevatedButton`, `OutlinedButton`), enabled states, and added verification that Providers (`Ollama (Local)`) renders alongside Connections on wide layouts.

In addition, `test/m24_providers_settings_shell_test.dart` was proactively updated to pump `ConnectionsProvidersScreen` directly instead of the retired Settings category.

---

## 3. Test & Analyzer Validation Evidence

### 3.1 Static Analysis (`flutter analyze`)
```
Analyzing uri_ui...
   info - 'value' is deprecated and shouldn't be used. Use initialValue instead. - lib\screens\settings\providers_screen.dart:697:5 - deprecated_member_use
1 issue found. (0 errors, 0 warnings)
```

### 3.2 Batch 3 Targeted Suites (9 suites)
```bash
flutter test test/m22_5_providers_test.dart test/m24_providers_settings_shell_test.dart \
  test/connections_screen_test.dart test/preferences_persistence_test.dart \
  test/settings_server_address_test.dart test/four_theme_persistence_test.dart \
  test/m22_ui_parity_test.dart test/redesign_test.dart test/chat_lifecycle_test.dart
```
**Result:** **49 / 49 passed (100%)**

### 3.3 Full Unscoped Flutter Suite
```bash
flutter test
```
**Result:** **143 / 143 passed, 0 failed (100%)**

### 3.4 Python M31 & Security Non-Regression
```bash
.venv/Scripts/python -m pytest tests/test_m31_model_brain_ux.py tests/dev_workflow/test_security_boundary.py
```
**Result:** **33 passed in 17.08s (100%)**

### 3.5 Chat Lifecycle Verification
```bash
flutter test test/chat_lifecycle_test.dart
```
**Result:** **11 / 11 passed (100%)**

---

## 4. Scope Compliance & Backend Isolation

- **Backend (`uri_core/`):** Clean working tree; zero modifications.
- **Batch 1 & Batch 2 Production Code:** Untouched with the exception of necessary navigation target updates in `home_screen.dart` (pointing to `ShellIndex.connections`) and topbar swatch wiring in `app_shell.dart`.
- **Dead Code:** `reference_dashboard.dart` remains untouched dead code, posing no build or runtime conflicts.

---

## 5. Fixes Made

**None.** The implementation satisfies all criteria and requirements cleanly.

---

## 6. Readiness for Batch 4

- Batch 3 is **formally accepted and closed**.
- **Batch 4 (Compact, mobile, consistency, full regression)** may proceed per `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` §6.
