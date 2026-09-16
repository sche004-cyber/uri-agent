# Home / System dashboard — reference patterns

## Current URI reality (verified 2026-09-15)

`HomeScreen` (`uri_ui/lib/screens/home/home_screen.dart`) is a fixed-size,
scaled "board" (`_FixedDashboardBoard`, `DashboardManifest.nativeHeight` /
`centerWidth` / `rightRailWidth`) with a greeting banner, dashboard tabs,
a center canvas, and the Chat dock (`UriCommandDock`) permanently docked at
the bottom — see `chat/README.md` for why that last part needs to change.
It loads, on mount: `loadHome`, `loadConnections`, `loadTasks`,
`loadCapabilities`, `loadMemory`, `loadActivity`, `loadAccountInfo`,
`loadSystemPerformance`, `loadUnreadEmailCount` — nine separate data loads
for one screen.

Real metrics available today, confirmed against `uri_ui/lib/services/uri_client.dart`
and `uri_core/app/server.py`:

- `HomeSummary.pendingApprovalCount` and `GET /tasks`
  (`uri_core/app/server.py:1586`) are **the same underlying data** — both
  read `context.orchestrator.approval_gate.approval_store.list_pending()`.
  "Pending approvals" and "pending tasks" are not two independent real
  metrics today; they are one queue of proposed actions awaiting a
  decision, shown two ways. A design that presents both as separate tiles
  should say so honestly (e.g. one tile, or two views of one count), not
  imply two distinct data sources that don't exist.
- `HomeSummary.connectedServiceCount` / `totalServiceCount` — real, backed
  by the Connections screen's Google/Gmail OAuth status.
- `unreadEmailCount` (`AppState.loadUnreadEmailCount`) — real, Gmail-backed
  (`uri_core/capabilities/gmail/`), the only capability module implemented
  today besides the base registry.
- `SystemPerformanceSnapshot` (`uri_ui/lib/models/system_performance.dart`)
  — real CPU/memory/disk/swap via `GET /system/performance`; this is
  *machine* health, not *Brain/provider* health.
- `ActiveBrainInfo` / `ModelInfo` (`uri_client.dart`) — real Brain/provider
  identity and verification state, sourced from `providers_screen.dart`'s
  data path; this is what "provider/Brain health" should actually bind to.
- **"Upcoming events" and "important deadlines" have no backing capability
  today.** `grep` across `uri_core/capabilities/` found only `gmail/` — no
  calendar module exists. Any dashboard tile for events/deadlines is
  either explicitly marked unavailable/coming-soon, or backed by a
  placeholder, until a calendar capability is built. Do not present a
  design that implies this data exists now.

## Reference patterns

Rendered screenshots captured 2026-09-15:
`../screenshots/kiranism_dashboard_overview.jpg`,
`../screenshots/tabler_dashboard.jpg`,
`../screenshots/shadcnstore_dashboard.jpg`. Kiranism's and shadcnstore's
overview pages render an identical 4-stat-tile row (Total Revenue, New
Customers, Active Accounts, Growth Rate) — both use the same underlying
shadcn dashboard block — confirming this is the base pattern to adapt,
with URI's own 4-6 real metrics substituted in. Tabler's dashboard is
noticeably denser (8+ tiles, a world map, storage/dev-activity widgets)
— more decoration than URI's real data supports; treat it as a "how not
to over-fill this" reference, not a template to match tile-for-tile.

- **shadcnstore/shadcn-dashboard-landing-template** —
  `nextjs-version/src/app/(dashboard)/dashboard-2/components/`
  (`metrics-overview.tsx`, `quick-actions.tsx`, `recent-transactions.tsx`,
  `customer-insights.tsx`, `dashboard-header.tsx`). A lighter metrics-tile
  + feed layout — closer to what six real metrics need than a dense
  admin/CRM grid.
- **Kiranism/next-shadcn-dashboard-starter** —
  `src/features/overview/components/` (`overview.tsx`, `area-graph.tsx`,
  `bar-graph.tsx`, `pie-graph.tsx`, `recent-sales.tsx`, and each
  component's own `-skeleton.tsx` loading state). Good reference for
  per-tile independent loading/error states, matching how URI's nine
  separate `load*` calls actually resolve at different times.
- **tabler/tabler** — `preview/pages/index.astro`,
  `preview/pages/dashboard-crm.astro`,
  `shared/components/cards/TasksDue.astro`. Plain stat-card patterns with
  low visual chrome — useful for keeping the dashboard information-dense
  without needing a dedicated visualization/graph library.
- **shadcnblockscom/shadcn-ui-blocks** — `docs/dashboard.md` (category
  reference only; no source in this repo — see `../DESIGN_INDEX.md`).
- **shadcnstore/shadcn-dashboard-landing-template**,
  `nextjs-version/src/app/(dashboard)/calendar/` — rendered live
  (screenshot: `../screenshots/shadcnstore_calendar.jpg`) as a full
  month-grid calendar with color-coded events. Kept here specifically as
  the reference to use **later**, if/when a real URI calendar capability
  is built — do not build this now against no backend.

## Guidance for the three-option prototype

Preserve real metrics as tiles: pending actions (approvals/tasks, as one
honestly-labeled data source), unread emails, connection/service health,
Brain/provider health. Mark events/deadlines explicitly as
not-yet-backed. Do not invent a metrics count that has no `GET` endpoint
behind it.

## Decisions

None yet.
