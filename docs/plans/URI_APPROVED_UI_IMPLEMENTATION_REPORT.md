# URI Approved UI Functional Prototype — Batch 1 Implementation Report

**Implementer:** Codex  
**Status:** IMPLEMENTATION_COMPLETE — awaiting Claude audit; no commit or push performed.

## Completed scope

- Fixed desktop board framing is manifest-driven in `uri_ui/lib/screens/home/home_screen.dart:67-137`: the desktop branch is explicit, and the centre/right board region is a `FittedBox` sized from the manifest's native dimensions. The application shell's left rail is `DashboardManifest.leftColumnFraction` of the board frame (`uri_ui/lib/widgets/app_shell.dart:163-166`). Hero and tab heights now use `DashboardManifest.heroHeight` and `DashboardManifest.tabsHeight` (`home_screen.dart:173`, `:265`). The existing narrow/mobile path remains a separate `center` branch.
- Navigation now iterates `DashboardManifest.navItems` (`app_shell.dart:173-197`), yielding the approved 13 labels. Before removal, reachability was read and confirmed: Email/Drive retain `ShellIndex.connections`, Insights retains `ShellIndex.activity`, and Files retains `ShellIndex.history` (`app_shell.dart:180-187`). No navigation dead end was created.
- The composer uses `Icons.arrow_forward_rounded` at `uri_ui/lib/screens/ask/ask_uri_screen.dart:378`. Current source contained one up-arrow call site, not two; that sole occurrence was changed.
- Added read-only `GET /gmail/unread-count` at `uri_core/app/server.py:1454-1466`; it directly returns `GmailSearchService().get_unread_count()` without fabricating a count. Its existing optional authenticated-user route pattern is classified as `USER` at `uri_core/app/route_classification.py:97`; route count is 68 (`:163`). No approval, permission, or dispatcher behavior changed.
- Added the client/state/UI path: `UriClient.loadUnreadEmailCount()` (`uri_ui/lib/services/uri_client.dart:157-159`), HTTP implementation (`http_uri_client.dart:946-965`), AppState load state (`app_state.dart:328-333`), and a fixed-shape `Today at a glance` value (`reference_dashboard.dart:684`, `:759`). A failed/unavailable request renders `Not reported`; initial loading renders `Loading…`; neither alters card bounds.
- Added real HTTP-boundary coverage in `test_gmail_unread_count_endpoint.py:14-40`; it issues a `TestClient` request, verifies both success and error response shapes, and asserts `get_unread_count()` was invoked exactly once in each case.

## Render

Native 1024×682 capture: `.tmp_m26_render/rebuilt_dashboard.png`.

`uri_ui/test/reference_render_test.dart` now captures at 1024×682. The resulting image was visually inspected against `docs/design_references/approved_ui_reference.png`; no overflow was present in the Batch 1 regions.

## Verification

- `flutter test test/reference_render_test.dart test/dashboard_shell_test.dart` — **6 passed**.
- `flutter analyze lib/screens/home/home_screen.dart lib/widgets/app_shell.dart lib/screens/ask/ask_uri_screen.dart lib/services/uri_client.dart lib/services/http_uri_client.dart lib/services/mock_uri_client.dart lib/services/app_state.dart lib/widgets/dashboard/reference_dashboard.dart test/reference_render_test.dart` — **No issues found**.
- `.venv\\Scripts\\python.exe -m unittest test_gmail_unread_count_endpoint.py` — **2 passed**.
- `.venv\\Scripts\\python.exe -m unittest test_gmail_unread_count_endpoint.py test_m22_3_route_authorization.py test_server_graph_endpoints.py` — **22 passed**.
- Full Flutter suite, `flutter test` — **130 passed, 1 failed**. The sole failure is `test/chat_lifecycle_test.dart`'s existing approval-flow test: the `Approve` control is rendered beneath the fixed composer at that test’s viewport, so the test tap cannot reach it and no `Result` is produced. This was not expanded into a Batch 1 composer/canvas interaction redesign.
- Full Python suite, `.venv\\Scripts\\python.exe -m unittest discover -v` — **1,627 tests run; 14 failures, 4 errors**. This terminal run predated route-classification registration for the new endpoint, so two failures were the expected unclassified/route-count drift; the focused 22-test run above proves those are repaired. The remaining failures/errors are existing model/environment and orchestration cases (including unavailable Ollama/model-dependent tests), not caused by the unread-count path. The run also emitted existing Gmail/network `ResourceWarning` messages.

## Scope boundary / stop record

No Batch 2 metrics, panels, right-rail geometry repair, GPU/model-usage unavailable visuals, donut/sparkline fidelity, approval logic, permission logic, or dispatcher logic was implemented. No navigation reachability stop condition occurred.

## Batch 2

**Implementer:** Codex  
**Status:** IMPLEMENTATION_COMPLETE — awaiting Claude audit; no commit or push performed.

### Completed scope

- Repaired the metrics and panels presentation states in
  `uri_ui/lib/widgets/dashboard/reference_dashboard.dart`. CPU, RAM, and
  Disk now distinguish loading/live/unavailable without changing their card
  shape; unavailable rendering retains a neutral sparkline baseline and an
  explicit label. GPU remains honestly unavailable and uses that same
  baseline geometry. System Health retains its four rows and shows an
  explicit loading/not-reported value per row.
- Activity retains a six-bar chart in every state; loading/unavailable bars
  are desaturated placeholders in the same chart bounds. Model Usage now
  draws a filled neutral ring at the manifest donut size with a centered
  `Provider breakdown unavailable` label. No GPU telemetry or model request
  accounting backend was added.
- Storage no longer presents system disk telemetry as a storage-category
  breakdown. It is explicitly unavailable, but keeps its full-width neutral
  meter and legend-row geometry. Existing connection data remains live.
- Replaced dash-only right-rail usage values with `Not reported`; Current
  Model's configured model/provider remain live. Sandbox remains honestly
  unavailable, and existing usable-tool data remains live while skills stay
  explicitly unreported.
- Added stable card keys and a widget regression test which pumps all touched
  metric, panel, and remaining right-rail cards in loading/live/unavailable
  presentation states and compares their complete `Rect` (offset and size).

### Verification

- `flutter test test/reference_render_test.dart test/dashboard_shell_test.dart` — **7 passed**.
- `flutter analyze lib/widgets/dashboard/reference_dashboard.dart test/dashboard_shell_test.dart test/reference_render_test.dart` — **No issues found**.
- `flutter test` — **131 passed, 1 failed**. The sole failure remains the
  previously disclosed `chat_lifecycle_test.dart` standalone approval-flow
  failure (the `Approve` hit target resolves through an overlay/absorb-pointer
  chain); it is outside this dashboard batch and was not re-diagnosed.

### Native render comparison

Rendered at 1024×682 to `.tmp_m26_render/rebuilt_dashboard.png` and visually
compared region-by-region with `docs/design_references/approved_ui_reference.png`.
The repaired regions retain their card/chart bounds, and the unavailable GPU,
Model Usage, and Storage treatments visibly preserve sparkline/ring/meter
shapes rather than collapsing to dashes or empty charts.

Remaining deltas, explicitly not hidden: the capture necessarily differs from
the populated reference wherever the runtime has no approved source (GPU,
provider accounting, storage categories, health sensors). The current right
rail is also vertically longer than the reference and its Tools & Skills card
falls below the 682px capture; resolving that is a visual-layout decision for
the next audit, not a backend fabrication or the Batch 1 left-rail/board
proportional-geometry limitation.

## Batch 4 — Typography Unification & Final UI Polish

**Implementer:** Codex  
**Status:** IMPLEMENTATION_COMPLETE — awaiting Claude audit; no commit or push performed.

### Completed scope

- Added `UriDashboardTextTheme` in `uri_ui/lib/theme/uri_theme.dart`, defining
  semantic roles derived from the active `TextTheme`: `metricValue`,
  `cardHeader`, `metricCaption`, `keyValue`, and `footerCaption`. The roles
  preserve the active theme family, brightness-aware palette, consistent line
  height, weight, and letter spacing.
- Removed every local `fontFamily: 'Segoe UI'` override from the approved
  dashboard, app shell, home, and Ask URI surfaces. All now inherit the
  application theme's single font family.
- Applied the semantic roles to metric captions/values, dashboard footer and
  key-value captions, and the home model-context caption. Existing explicit
  visual sizing remains where it is needed to preserve the frozen dashboard
  geometry and reference capture.

### Files modified

- `uri_ui/lib/theme/uri_theme.dart`
- `uri_ui/lib/widgets/dashboard/reference_dashboard.dart`
- `uri_ui/lib/widgets/app_shell.dart`
- `uri_ui/lib/screens/home/home_screen.dart`
- `uri_ui/lib/screens/ask/ask_uri_screen.dart`
- `docs/plans/URI_APPROVED_UI_IMPLEMENTATION_REPORT.md`

### Verification

- `flutter analyze lib/theme/uri_theme.dart lib/widgets/dashboard/reference_dashboard.dart lib/widgets/app_shell.dart lib/screens/home/home_screen.dart lib/screens/ask/ask_uri_screen.dart` — **No issues found**.
- `flutter test test/dashboard_shell_test.dart test/reference_render_test.dart test/redesign_test.dart test/m22_ui_parity_test.dart test/ask_uri_flow_test.dart` — **23 passed**.
- `test/reference_render_test.dart` completed without exception and regenerated `.tmp_m26_render/rebuilt_dashboard.png` (286,075 bytes; 2026-09-14 20:10:05 local time).
- Visual QA of the regenerated native 1024×682 capture found the unified text
  contained within the existing dashboard cards, rail, and command dock; no
  typography overflow or geometry change was observed.

### Protected Batch 3 scope

No responsive-scaling logic (`DashboardScale`, `_Sidebar`, or
`_FixedDashboardBoard`) was altered. No light/dark palette propagation was
changed. No local-model switching behavior in `providers_screen.dart` was
changed. No continuous chat-thread presentation or ordinary-success status
behavior in `turn_card.dart` was changed.
