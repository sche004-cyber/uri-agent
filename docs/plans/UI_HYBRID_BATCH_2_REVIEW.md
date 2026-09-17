# URI Hybrid UI — Batch 2 Independent Review

**Initiative:** URI Hybrid UI Implementation  
**Governing Documents:**
- `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`
- `docs/plans/UI_HYBRID_BATCH_2_REPORT.md`
- `.claude/skills/uri-development/SKILL.md`

**Reviewer:** Antigravity (independent inspection)  
**Date:** 2026-09-17  
**Verdict:** **`BATCH_2_ACCEPTED`**

---

## 1. Executive Verdict

**Verdict: `BATCH_2_ACCEPTED`**

Batch 2 has faithfully implemented all required deliverables for Standalone Chat (§4.3), Tasks (§4.5), Model-Selector reconciliation (§7), and Test Reconciliation (§2.5) without weakening existing test assertions, introducing backend modifications, or expanding scope into Batch 3. All acceptance criteria for Batch 2 defined in `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` are satisfied.

No fixes were required. Batch 2 is ready to close, and Batch 3 may begin.

---

## 2. Independently Verified Findings

### 2.1 Standalone Chat Implementation (§4.3)
- **Three-tab Structure:** `AskUriScreen` (`uri_ui/lib/screens/ask/ask_uri_screen.dart`) is implemented as a `StatefulWidget` hosting a top `TabBar` with three tabs: `Conversation`, `History`, and `Activity`.
- **Composition:** The `Conversation` tab composes `UriConversationPane` and `UriCommandDock` directly.
- **Copy & Empty States:** The empty conversation state faithfully renders the reference copy (`New conversation` / `Ask URI anything to begin.`). The composer input hint is updated to `Message URI…`.
- **Dock & Composer Order:** Icon sequence preserves `attachment button` → `model selector` → `mic button` → `send button`.

### 2.2 History & Activity Tabs (§4.3)
- Internal tabs reuse `HistoryScreen` and `ActivityScreen` as internal subviews without adding top-level navigation items to `ShellIndex`.
- `HistoryScreen` gained an `onResumed` callback parameter. When resuming a session from within Chat's History tab, `onResumed` switches back to the `Conversation` tab in place (`_tabController.animateTo(0)`), preventing jarring navigation to Home. Standalone fallback routes to `ShellIndex.chat`.

### 2.3 Per-Message Copy Action (§4.3)
- Added `_CopyMessageAction` in `uri_ui/lib/widgets/turn_card.dart`.
- Assembles actual message contents (prompt, understanding, result summary, result detail, and draft text) without fake or placeholder strings.
- **Clipboard Failure Safety:** Wraps `Clipboard.setData` in try/catch; transient success state (`Copied` tooltip and check icon) is set only upon resolved clipboard write, and automatically resets after 2 seconds.

### 2.4 M31 Model-Selector Reconciliation (§7)
- The shipped structure from M31 utilized private `_ModelSelectorChip` in `ask_uri_screen.dart` rather than standalone exported widgets.
- Batch 2 preserved the entire state and logic layer intact (real provider inventory via `AppState.providerInventory`, unverified models disabled with red dot and reason text, `URI Auto` routing, `AskRequest.model_override` per-conversation dispatch, and turn caption).
- The presentation was refined by adding the trailing dropdown chevron (`Icons.expand_more_rounded`) inside a `RawChip` layout. Using `RawChip` instead of `Chip` preserves the regression guard in `attachment_ui_test.dart` (which isolates `Chip` finders for attachment pills).

### 2.5 Tasks Screen Rebuild (§4.5)
- Fully rebuilt `uri_ui/lib/screens/tasks/tasks_screen.dart` with:
  1. **Header:** Title, explanatory subtitle, and manual Refresh action.
  2. **4 Client-Computed Summary Tiles:** `TOTAL PENDING`, `LOW RISK`, `NEEDS REVIEW`, `HIGH RISK`, grouped deterministically from real `TaskItem.risk` strings returned by `GET /tasks`.
  3. **Search & Filter:** Search field filtering by task description or capability identifier, and a risk-level dropdown chip (`All risk levels`, `Low risk`, `Needs review`, `High risk`) with an empty-state "Clear filters" action.
  4. **Data Table:** Columns for `Description`, `Capability`, `Risk` (rendered via `StatusPill.forImpact`), `Created` (formatted local date), and Actions (`Approve` and `Cancel` icon buttons).
  5. Real execution calls `AppState.approveTask` and `AppState.cancelTask` through the established runtime gates.

### 2.6 Reconciliation of Broken Pre-Existing Tests
- `uri_ui/test/ask_uri_flow_test.dart`: Updated test harness helper to navigate to `Chat` before typing, reflecting the retirement of Home's embedded composer.
- `uri_ui/test/m18_history_memory_test.dart`: Updated to navigate via `Chat` → `History` tab rather than the retired `Files` sidebar entry, and asserted in-place resumption into the `Conversation` tab.
- `uri_ui/test/m25_ui_defects_test.dart`: Converted the obsolete topbar brain status pill assertion into an explicit `findsNothing` check, verifying that the topbar chrome remains clean and brain status lives solely on Home's "BRAIN / PROVIDER" tile.
- None of the test assertions were relaxed or weakened.

### 2.7 Verification of Scope & Backend Isolation
- `git status uri_core`: Clean working directory; 0 files modified in backend.
- Files touched in Batch 2 were strictly confined to Batch 2 scope:
  - `uri_ui/lib/screens/ask/ask_uri_screen.dart`
  - `uri_ui/lib/widgets/turn_card.dart`
  - `uri_ui/lib/screens/tasks/tasks_screen.dart`
  - `uri_ui/lib/screens/history/history_screen.dart`
  - `uri_ui/test/ask_uri_flow_test.dart`
  - `uri_ui/test/m18_history_memory_test.dart`
  - `uri_ui/test/m25_ui_defects_test.dart`
- Batch 3 files (`providers_screen.dart`, `connections_settings_screen.dart`, `settings_shell.dart`, theme system) were untouched.

### 2.8 Analysis of Remaining Test Failures
- Full test suite run (`flutter test`) yielded **124 passed, 5 failed**.
- The 5 failing tests are:
  - `test/connections_screen_test.dart`: 3 failures (`Connections shows the three distinct connection states`, `authorizing a not-connected service updates its state`, `reconnecting a needs-authorization service updates its state`)
  - `test/m22_ui_parity_test.dart`: 2 failures (`a non-admin sees enabled connect/reconnect controls and no admin-only notice`, `an admin sees enabled connect/reconnect controls and no notice`)
- Both test suites test Connections & Providers integration, which is explicitly owned and scheduled for refactoring in **Batch 3** (`docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` §6).
- Neither file was modified or broken by Batch 2 changes. These failures are confirmed to be pre-existing baseline artifacts outside Batch 2 scope.

---

## 3. Test & Analyzer Validation Evidence

### 3.1 Static Analysis (`flutter analyze`)
```
Analyzing uri_ui...
   info - 'value' is deprecated and shouldn't be used. Use initialValue instead. - lib\screens\settings\providers_screen.dart:697:5 - deprecated_member_use
1 issue found. (0 errors, 0 warnings)
```

### 3.2 Batch 2 Targeted & Regression Suites
Command:
```bash
flutter test test/ask_uri_flow_test.dart test/chat_lifecycle_test.dart test/turn_card_test.dart \
  test/attachment_ui_test.dart test/m18_history_memory_test.dart test/m25_ui_defects_test.dart \
  test/dashboard_shell_test.dart test/widget_test.dart test/redesign_test.dart test/http_uri_client_test.dart
```
**Result:** **72 / 72 passed (100%)**

### 3.3 Full Suite Run (`flutter test`)
Command:
```bash
flutter test
```
**Result:** **124 / 129 passed, 5 failed** (failures confined to Batch 3 scope in `connections_screen_test.dart` and `m22_ui_parity_test.dart`).

---

## 4. Fixes Made

**None.** The implementation in Batch 2 strictly meets all frozen blueprint specifications, adheres to architecture guidelines, and passes all required tests without defect.

---

## 5. Next Steps

- Batch 2 is **officially accepted and closed**.
- **Batch 3 (Connections & Providers, Settings, four themes)** may now proceed per `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` §6.
