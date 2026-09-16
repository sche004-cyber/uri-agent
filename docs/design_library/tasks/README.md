# Tasks / pending-approval queue — reference patterns

## Current URI reality (verified 2026-09-15)

`TasksScreen` (`uri_ui/lib/screens/tasks/tasks_screen.dart`) is a real,
already top-level `AppShell` section. Its data model, `TaskItem`
(`uri_ui/lib/models/task_item.dart`), is explicitly documented in its own
source comment as "one proposed action still awaiting a user decision" —
**not** a general-purpose to-do/deadline task manager. Fields: `id`,
`capabilityId`, `description`, `risk`, `sessionId`, `createdAt`. There is
no due-date/deadline field. The backing endpoint, `GET /tasks`
(`uri_core/app/server.py:1586`), reads the same `ApprovalStore.list_pending()`
queue that also produces `HomeSummary.pendingApprovalCount` — see
`dashboard/README.md` for why "pending approvals" and "pending tasks" are
one data source, not two.

Approving or rejecting stays exclusively `POST /approve` / `POST /cancel`
per the endpoint's own docstring — Tasks is a read + decide surface, not a
freeform task-creation tool a user fills in themselves.

## Reference patterns

- **shadcnstore/shadcn-dashboard-landing-template** — the `tasks` route of
  the live demo (screenshot: `../screenshots/shadcnstore_tasks_table.jpg`,
  captured 2026-09-15 from `shadcnstore.com/templates/dashboard/shadcn-dashboard-landing-template/tasks`).
  A filterable table (status, category, priority columns) with four
  summary tiles (Total/Completed/In Progress/Pending) above it — this is
  the **closest structural match of any captured reference** to URI's
  real `TaskItem` shape: a flat list of discrete items, each with a
  status/risk attribute, filterable, with no per-row authoring beyond
  filtering and an accept/decide action. Prefer this over a kanban board
  as the primary Tasks reference.
- **Kiranism/next-shadcn-dashboard-starter** —
  `src/features/kanban/components/` (`kanban-board.tsx`, `task-card.tsx`,
  `new-task-dialog.tsx`) and
  `src/features/notifications/components/notification-center.tsx`. The
  notification-center pattern is the closer structural match — a list of
  discrete pending items each with an accept/dismiss action — since URI
  tasks are proposed-and-decided, not user-authored and freely editable
  like a kanban card. A kanban board's "create new task" affordance does
  not apply to URI's Tasks screen and should not be copied — confirmed
  visually in `../screenshots/kiranism_kanban.jpg` (drag-and-drop board
  with a "+ Add New Task" button).
- **tabler/tabler** — `shared/components/cards/Tasks.astro`,
  `shared/components/cards/TasksDue.astro`,
  `preview/pages/tasks.astro`, `preview/pages/tasks-list.astro`. Plain
  list-with-status-pill patterns, close to what `TaskItem.risk` already
  needs (a risk/status pill per row, reusing `ActionImpact` per the
  existing `tasks_screen.dart` comment). The live demo's `tasks.html`
  (screenshot: `../screenshots/tabler_tasks.jpg`) turned out to render as
  a multi-board Trello-style view, not the plain list its Astro source
  name suggested — same authoring-tool caveat as Kiranism's kanban.

## Guidance for the three-option prototype

Treat Tasks as a decision queue (accept/reject a proposed action), not a
task-authoring tool. Any "add task" affordance from a reference repo's
kanban/todo pattern is out of scope unless a future milestone actually
adds user-authored tasks as a new backend capability.

## Decisions

None yet.
