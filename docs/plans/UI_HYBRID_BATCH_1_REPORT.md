# URI Hybrid UI — Batch 1 Implementation Report

**Initiative:** URI Hybrid UI Implementation  
**Governing Blueprint:** `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md`  
**Milestone Gate Baseline:** M31 VERIFIED and released at `5c31d25`  
**Batch:** Batch 1 — Navigation, shell, truthful Home  
**Implementer:** Antigravity (Gemini 3.8 Flash)  
**Reviewer:** Qwen 3 14B (local Ollama)  

---

## 1. Batch 1 Scope & Delivered Objectives

As specified in §6 Batch 1 of the Frozen Blueprint:
1. **5-Destination Persistent Sidebar (§4.1):**
   - Implemented 5 canonical destinations: `Home` (0), `Chat` (1), `Tasks` (2), `Connections & Providers` (3), `Settings` (4).
   - Preserved backward-compatible navigation aliases for legacy callbacks (`activity` -> Tasks, `history` -> Chat).
   - Persistent collapsible sidebar: 240px expanded width vs 64px icon rail.
   - User collapse/expand preference persisted across sessions in `SharedPreferences` (`uri_sidebar_collapsed_v1`).
   - Integrated `UriWordmark` in header row, compact action icons, and accessible tooltips.
   - Responsive layout structure with clean visual density and zero `RenderFlex` overflows during animation.
2. **Truthful 4-Tile Home Screen (§4.2):**
   - Replaced fixed-scale dashboard board with responsive 4-tile metric grid:
     1. `PENDING APPROVALS` (tasks awaiting approval)
     2. `UNREAD EMAIL` (Gmail unread count)
     3. `CONNECTED SERVICES` (number of connected integrations)
     4. `BRAIN / PROVIDER` (active brain provider/model ID)
   - Strict adherence to §5 non-negotiables: omitted ungrounded metrics ("Upcoming Deadline", "Halted Workflows").
   - Retired embedded `UriCommandDock` and conversation transcript from Home screen.
   - Added Suggested Actions panel offering safe, prompt-prefilling shortcuts (urgent email, approvals, connections, preferences). Never triggers destructive or write operations on render or tap.
3. **Operational Standalone Chat Route at Index 1:**
   - Chat is immediately reachable at index 1 (`AskUriScreen`). Removing the embedded chat from Home did not cause any gap in chat availability.
4. **Retired Legacy Manifest Navigation:**
   - 13-item flat manifest nav completely retired in favor of the canonical 5-destination navigation model.
5. **R1 Client-Side Tri-State Metric Handling (§5):**
   - `listTasks()` and `listConnections()` in `HttpUriClient` now throw structured `TasksFetchException` and `ConnectionsFetchException` on network, status, or parse errors rather than returning empty lists `[]`.
   - `AppState` tracks `tasksFetchFailed`, `tasksError`, `connectionsFetchFailed`, `connectionsError`, `unreadEmailFailed`, and `activeBrainFailed`.
   - `HomeScreen` displays "Unavailable" with a retry button whenever a metric fetch fails, never misleading the user with false "0" counts.
6. **R2 Hoisted Composer Draft Continuity (§5):**
   - `AppState.composerDraft`, `setComposerDraft(text)`, and `clearComposerDraft()` manage the in-progress prompt draft at app scope.
   - `_UriCommandDockState` synchronizes bidirectionally with `AppState.composerDraft`.
   - The user's draft persists across navigation between Chat, Home, Tasks, and Settings, as well as sidebar collapse/expand toggles. Cleared automatically only on successful turn submission.

---

## 2. Modified Files

- `uri_ui/lib/services/uri_client.dart`: Added `TasksFetchException`, `ConnectionsFetchException`, and updated `HomeSummary` with failure markers and nullable metrics.
- `uri_ui/lib/services/http_uri_client.dart`: Updated `listTasks()`, `listConnections()`, and `loadHomeSummary()` to throw and track fetch failures. Cleaned up Dart null-aware syntax.
- `uri_ui/lib/services/mock_uri_client.dart`: Added `shouldFailTasks` and `shouldFailConnections` simulation flags for testing R1 tri-state states.
- `uri_ui/lib/services/app_state.dart`: Added hoisted composer draft fields and methods (R2) and failure tracking for tasks, connections, email, and brain (R1).
- `uri_ui/lib/screens/ask/ask_uri_screen.dart`: Connected `_UriCommandDockState` controller to `AppState.composerDraft`.
- `uri_ui/lib/widgets/app_shell.dart`: Re-architected desktop shell with 5-destination sidebar, collapse/expand toggle with SharedPreferences persistence, breadcrumb topbar, theme swatches, and overflow-proof layout.
- `uri_ui/lib/app.dart`: Configured `UriHome` with 5 canonical sections matching `ShellIndex`.
- `uri_ui/lib/screens/home/home_screen.dart`: Rebuilt Home layout with 4 truthful metric tiles, tri-state "Unavailable" handling, and Suggested Actions.
- `uri_ui/test/dashboard_shell_test.dart`: Added comprehensive unit and widget tests covering 5-destination nav, 4-tile metric rendering, Chat route at index 1, R1 metric failure states, R2 composer draft hoisting, and sidebar collapse persistence.
- `uri_ui/test/http_uri_client_test.dart`: Updated mock client tests to verify `TasksFetchException` and `ConnectionsFetchException`.
- `uri_ui/test/widget_test.dart`, `uri_ui/test/redesign_test.dart`, `uri_ui/test/chat_lifecycle_test.dart`: Updated assertions to reflect 5-destination navigation and standalone Chat.

---

## 3. Verification & Test Evidence

### A. Static Analysis
Command:
```bash
flutter analyze
```
Result: **0 errors, 0 warnings** (1 pre-existing info in `providers_screen.dart:697:5`).

### B. Batch 1 Targeted Test Suites
Command:
```bash
flutter test test/dashboard_shell_test.dart test/widget_test.dart test/redesign_test.dart test/http_uri_client_test.dart test/chat_lifecycle_test.dart
```
Result: **53 / 53 passed** (Exit code 0).
- `test/dashboard_shell_test.dart`: 5/5 passed (5 destinations, truthful 4 tiles, Chat at index 1, R1 tri-state, R2 draft continuity, sidebar collapse persistence).
- `test/widget_test.dart`: 2/2 passed.
- `test/redesign_test.dart`: 5/5 passed.
- `test/http_uri_client_test.dart`: 30/30 passed.
- `test/chat_lifecycle_test.dart`: 11/11 passed.

### C. Python Backend Non-Regression
Command:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_m31_model_brain_ux.py tests/dev_workflow/test_security_boundary.py
```
Result: **33 / 33 passed** (17.59s, Exit code 0).

---

## 4. Handoff for Independent Review

Per the UI Initiative Role Override (`AGENTS.md` and `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` §1):
- Implementation of Batch 1 is complete.
- Ready for independent review by **Qwen 3 14B** against the frozen blueprint contract.
- Antigravity does not declare VERIFIED and does not commit/push.
