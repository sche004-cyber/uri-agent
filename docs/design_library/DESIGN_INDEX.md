# URI Design Library — Index

Status: established 2026-09-15. This library is the entry point for a
**reference-first** design process: before any URI screen is designed or
redesigned, the relevant category folder here is consulted for an existing
structural pattern, which is then adapted to URI's real backend
capabilities. See `.claude/skills/uri-ux-design/SKILL.md` for the mandatory
process this library supports.

## What this library is, and is not

- This library stores **descriptions, verified structural notes, and links**
  to external reference repositories — not copies of their code.
- None of the repositories listed below are runtime dependencies of URI.
  Nothing here is imported, vendored, or built into `uri_ui/`.
- `approved/` and `rejected/` hold decision records for specific screen
  designs (see below), not source code either.
- Every path cited in this library was confirmed against the referenced
  repository's actual file tree on 2026-09-15 (via `gh api repos/<org>/<repo>/git/trees`).
  If a repository's structure changes later, re-verify before trusting a
  cited path — do not assume these citations stay accurate indefinitely.
- `docs/design_library/screenshots/` holds real rendered screenshots
  captured from each project's live hosted demo on 2026-09-15 (browser
  automation, not AI-generated mockups) — see "Rendered screenshots"
  below for what was captured and from which URL.

## Rendered screenshots (captured 2026-09-15)

Static file-tree structure alone doesn't show what a pattern actually
looks like rendered, so the following pages were opened in a real browser
and screenshotted directly from each project's own public live demo:

| File | Captured from | Notes |
|---|---|---|
| `screenshots/kiranism_dashboard_overview.jpg` | `shadcn-dashboard.kiranism.dev/dashboard/overview` | Loaded state — 4 stat tiles + dotted area chart + recent-sales feed. |
| `screenshots/kiranism_sidebar_nav.jpg` | same, sidebar open | Real nav: Dashboard, Workspaces, Product, Users, Kanban, **Chat**, **AI Chat**, then Elements/Account groups. |
| `screenshots/kiranism_chat.jpg` | `.../dashboard/chat` | Conversation-list rail + thread + composer with quick-reply chips. |
| `screenshots/kiranism_kanban.jpg` | `.../dashboard/kanban` | Drag-and-drop board with "+ Add New Task" — an authoring tool, not a decision queue (see `tasks/README.md`). |
| `screenshots/tabler_dashboard.jpg` | `preview.tabler.io/` | Dense stat-tile/chart dashboard — more tiles than URI has real metrics for. |
| `screenshots/tabler_chat.jpg` | `preview.tabler.io/chat.html` | Single low-chrome chat page with a contact list, closer to a team-chat than an AI conversation. |
| `screenshots/tabler_tasks.jpg` | `preview.tabler.io/tasks.html` | Trello-style multi-board task view — same authoring-tool caveat as Kiranism's kanban. |
| `screenshots/tabler_settings.jpg` | `preview.tabler.io/settings.html` | Nested-sidebar-within-page settings pattern (My Account / My Notifications / Connected Apps / Plans / Billing). |
| `screenshots/shadcnstore_dashboard.jpg` | `shadcnstore.com/templates/.../dashboard` | Same 4-stat-tile pattern as Kiranism (both use the same shadcn dashboard block), plus a data table below. |
| `screenshots/shadcnstore_chat.jpg` | `shadcnstore.com/templates/.../chat` | Conversation-list rail + thread, lighter-weight than Kiranism's. |
| `screenshots/shadcnstore_calendar.jpg` | `shadcnstore.com/templates/.../calendar` | Full month-grid calendar with color-coded events — the clearest reference for a *future* URI events/deadlines capability, once one exists. |
| `screenshots/shadcnstore_tasks_table.jpg` | `shadcnstore.com/templates/.../tasks` | **A filterable task table with status/priority columns and summary tiles (Total/Completed/In Progress/Pending) — structurally the closest match of any captured reference to URI's real `TaskItem` shape** (a flat list of items with a status/risk attribute, not a kanban board a user authors into). Added to `tasks/README.md` as the primary Tasks reference. |

Evidence note: reaching Kiranism's dashboard/chat/kanban pages required
signing in; the demo (Clerk-based auth) silently accepted an existing
Google browser session already signed in as the operating User
(sche004@gmail.com) rather than requiring a fresh credential entry. No
credentials were typed and no account data was viewed or changed beyond
loading these public demo pages — flagged here for transparency, not
because anything sensitive was exposed.

## Primary reference repositories

### 1. Kiranism/next-shadcn-dashboard-starter
- URL: https://github.com/Kiranism/next-shadcn-dashboard-starter
- License: MIT (confirmed via `gh repo view`).
- Stack: Next.js 16, shadcn/ui, Tailwind CSS, TypeScript.
- Why it's here: the most complete reference for an admin-style app shell
  (sidebar + header + routed sections) that also already contains a chat
  surface and a kanban/task surface living as peers of a metrics dashboard,
  which is close to URI's own shape (Home / Chat / Tasks / Settings as
  siblings, not one screen).
- Verified structure of interest:
  - `src/components/layout/app-sidebar.tsx`, `header.tsx`, `page-container.tsx`
    — the shell/nav pattern.
  - `src/app/dashboard/overview/` (+ parallel routes `@area_stats`,
    `@bar_stats`, `@pie_stats`, `@sales`) and
    `src/features/overview/components/overview.tsx`, `recent-sales.tsx`
    — a metrics-tile dashboard, each tile independently loading/erroring.
  - `src/app/dashboard/chat/`, `src/app/dashboard/ai-chat/`, and
    `src/features/chat/components/` (`chat-area.tsx`, `chat-header.tsx`,
    `conversation-list.tsx`, `message-bubble.tsx`, `message-composer.tsx`,
    `messenger.tsx`) — a chat workspace treated as its own routed section,
    not embedded in the dashboard overview.
  - `src/app/dashboard/kanban/` + `src/features/kanban/components/`
    (`kanban-board.tsx`, `task-card.tsx`, `new-task-dialog.tsx`) — a task
    board pattern.
  - `src/app/dashboard/notifications/` +
    `src/features/notifications/components/notification-center.tsx` —
    a pending-items/notification surface, structurally close to URI's
    approval/task queue.
  - `src/app/dashboard/profile/`, `src/app/dashboard/billing/` — settings-
    adjacent single-purpose pages rather than one giant settings screen.

### 2. tabler/tabler
- URL: https://github.com/tabler/tabler
- License: MIT (confirmed via `gh repo view`).
- Stack: server-rendered HTML/Bootstrap 5 + Astro-based preview site (not a
  React/Flutter stack — used here purely for layout and information-density
  patterns, never for code reuse).
- Why it's here: the deepest catalogue of plain, low-chrome dashboard cards
  (stat tiles, "tasks due", invoices, settings tabs) — useful for keeping a
  dashboard functional and readable rather than decorative.
- Verified structure of interest:
  - `preview/pages/index.astro` — the default dashboard homepage.
  - `preview/pages/dashboard-crm.astro`, `dashboard-crypto.astro` —
    alternate stat-tile dashboard layouts.
  - `preview/pages/chat.astro`, `core/scss/ui/_chat.scss`,
    `docs/content/ui/components/chat.mdx` — a dedicated chat page,
    separate from the dashboard pages above.
  - `preview/pages/tasks.astro`, `preview/pages/tasks-list.astro`,
    `shared/components/cards/Tasks.astro`,
    `shared/components/cards/TasksDue.astro` — task list/queue card
    patterns, including a "due" variant relevant to deadline-style framing.
  - `preview/pages/settings.astro`, `preview/pages/settings-plan.astro` —
    settings-as-tabs pattern.
  - `preview/pages/email-inbox.astro`, `preview/pages/emails.astro` —
    inbox-style list pattern, relevant to an "unread emails" tile linking
    out to a fuller view.

### 3. shadcnblockscom/shadcn-ui-blocks
- URL: https://github.com/shadcnblockscom/shadcn-ui-blocks
- License: **none declared at the repository root** (`gh repo view` returned
  no license). Treat as reference-only in the strictest sense — do not port
  any code from the hosted block library without checking that specific
  block's own licensing on shadcnblocks.com first.
- Important structural fact, verified: **this GitHub repository contains
  documentation only** (`docs/*.md` — e.g. `docs/dashboard.md`,
  `docs/sidebar.md`, `docs/calendar.md`, `docs/table.md`, `docs/hero.md`,
  `docs/blocks.md`). The actual block markup/components live on the hosted
  site (serp.ly/shadcnblocks.com), not in this repo. Citations against this
  source should name the doc topic (e.g. "shadcn-ui-blocks: sidebar
  pattern"), not a source file path, since no component source exists here
  to point at.
- Why it's here anyway: it is the broadest named catalogue of small,
  composable block categories (sidebar variants, dashboard variants,
  calendar, table, hero) that URI's screens can be decomposed into, useful
  for vocabulary and category coverage even without vendored code.

### 4. shadcnstore/shadcn-dashboard-landing-template
- URL: https://github.com/shadcnstore/shadcn-dashboard-landing-template
- License: MIT (confirmed via `gh repo view`).
- Stack: two parallel implementations, `nextjs-version/` and
  `vite-version/`, both shadcn/ui + Tailwind.
- Why it's here: it separates chat, calendar, and a second alternate
  dashboard layout as distinct routed areas, and its `dashboard-2` variant
  is a clean minimal-metrics layout rather than a data-heavy admin panel —
  useful specifically for Option A/B-style minimal directions.
- Verified structure of interest (paths under `nextjs-version/src/app/(dashboard)/`):
  - `chat/` + `chat/components/` (`chat-header.tsx`, `chat.tsx`,
    `conversation-list.tsx`, `message-input.tsx`, `message-list.tsx`) —
    chat as its own route group.
  - `calendar/` + `calendar/components/` (`calendar-main.tsx`,
    `calendar-sidebar.tsx`, `event-form.tsx`, `quick-actions.tsx`) —
    a real events/deadlines surface pattern (URI has no backend capability
    for this yet — see `dashboard/README.md`).
  - `dashboard-2/components/` (`metrics-overview.tsx`,
    `quick-actions.tsx`, `recent-transactions.tsx`,
    `customer-insights.tsx`) — a lighter-weight metrics-tile-plus-feed
    layout, closer in spirit to what URI's dashboard actually needs than a
    full admin/CRM dashboard.

## Category folders

| Folder | Scope |
|---|---|
| `chat/` | Chat workspace patterns — always evaluated as a first-class, standalone area, never as a widget embedded in a dashboard. |
| `dashboard/` | Home/System overview patterns — stat tiles, health/status cards, activity feeds. |
| `providers/` | Model/Brain and provider management patterns — connection/health status, configuration forms. |
| `tasks/` | Pending-action / approval-queue / task-list patterns. |
| `settings/` | Settings navigation and forms patterns (tabs vs. nested list vs. sectioned page). |
| `approved/` | Decision records for a screen design that has been selected — what was chosen, from which reference, and why. |
| `rejected/` | Decision records for a screen design that was considered and turned down — kept so the same idea isn't re-proposed without knowing it was already rejected, and why. |

Each category folder has its own `README.md` with the specific reference
paths above filtered to that category, evidence for that category's real
URI backend support, and open questions/gaps still unresolved.
