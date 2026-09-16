# URI UI — Prototype Directions (A/B/C + Hybrid)

Status: **DRAFT — presented for User selection. Nothing here has been
implemented.** No Flutter code was modified to produce this document.

**Editable visual canvas (2026-09-15):** all four directions were also
built as an editable, click-to-select visual mockup canvas — the closest
available equivalent to Figma in this environment (there is no Figma
integration here) — covering Home, Chat, Providers, Connections, Tasks,
and Settings for each direction:
https://claude.ai/artifact/9P4K3mKwBoDawp178Rhce9
This text document remains the authoritative written spec (references,
mapping, advantages/disadvantages, difficulty); the canvas is the visual
comparison built from it.

Produced under `.claude/skills/uri-ux-design/SKILL.md`, using
`docs/design_library/` as the reference source and the real URI backend
and current Flutter code as the capability/history source.

## Acceptance criteria for this document

Defined before drafting, per the repository's Verification-First
standard:

1. Each option cites a design-library reference with a path verified
   against the actual repository tree (see `DESIGN_INDEX.md`), not an
   assumed one.
2. Each option maps only to real, verified URI backend capability, and
   explicitly flags anything not yet backed (e.g. calendar/events).
3. Each option is simpler than the current UI — measured against the
   verified current surface: 6 real `AppShell` sections, a 13-label nav
   rail that disguises deep-links into ~10 Settings categories, and Chat
   embedded as a permanent dock inside Home (see "Current baseline"
   below).
4. Chat is a standalone workspace in all three options, never embedded
   in Home/System.
5. Real dashboard metrics (unread emails, pending actions,
   connection/service health, provider/Brain health) are preserved and
   honestly labeled; no invented metric with no backing endpoint.
6. No Flutter code is modified by this document; options are presented,
   not implemented, pending User selection.

This document was drafted, then self-reviewed against these six criteria,
then corrected once (see "Self-review correction" note at the end) before
being presented.

## Current baseline (verified 2026-09-15, for comparison only)

- Real top-level `AppShell` sections (`uri_ui/lib/app.dart:186-228`):
  Home, Tasks, Connections, Activity, History, Settings — 6 screens.
- The visible left-rail nav is a *separate*, 13-label list
  (`DashboardManifest.navItems`) that remaps several labels into the same
  6 sections or into specific Settings categories via
  `openSettingsCategory` (`app_shell.dart:183-218`) — e.g. "Email"/"Drive"
  both open Connections, "Graph" opens Settings → "Memory & Context",
  "Model" opens Settings → "Model Providers". The apparent 13 destinations
  resolve to 6 real screens plus ~10 Settings categories.
- Chat is not a section at all — it is `UriCommandDock`, permanently
  docked at the bottom of `HomeScreen` (`home_screen.dart:84`). A
  standalone `AskUriScreen` class exists in the same file but is never
  instantiated anywhere — dead code.
- `HomeScreen` fires nine separate data loads on mount (home, connections,
  tasks, capabilities, memory, activity, account info, system
  performance, unread email count) into one fixed-size scaled board.
- `UriSection.group` (Workspace/Work/Knowledge/Runtime) exists in code
  but is never rendered — the sidebar shows a flat list, not grouped
  sections, despite the grouping data being present.
- A `_BrainStatusPill` already exists in the top app bar
  (`app_shell.dart:129`), tapping through to Settings → Model Providers —
  a real, if minimal, existing Brain-health affordance worth reusing
  rather than reinventing.

All three options below are simpler than this baseline by design.

## Reference sources — evidence note

**Correction (2026-09-15, later same day):** the paragraph originally
here said no screenshots had been captured and file-tree structure alone
had been verified. After the User asked to compare actual rendered
references, real screenshots of each project's live demo were captured
(browser automation) and saved to `docs/design_library/screenshots/` —
see the table in `DESIGN_INDEX.md`. Two of the structural inferences
below, made from file/folder names alone, turned out to be wrong once
rendered: tabler's `chat.astro` renders as a two-pane contact-list chat,
not single-thread as its name suggested, and tabler's `settings.astro`
renders as a nested sub-nav inside one page, not literal tabs. Both are
corrected in `chat/README.md` and `settings/README.md` respectively, and
Option D (below) is built only from the corrected, screenshot-verified
versions. The A/B/C sections above are left as originally drafted rather
than silently rewritten, per this repository's auditable-correction-
history rule — read them alongside this correction, not as if the file
names described the true rendered shape.

---

## Option A — Minimal AI Companion

A ChatGPT/Claude-like single-purpose companion: chat is the main act, the
dashboard is a thin status strip, everything else is one click away in
Settings.

### Design references used

- **tabler/tabler**, `preview/pages/chat.astro` — single-thread,
  low-chrome chat page (no conversation-list rail), matching URI's real
  one-active-session model rather than a multi-thread inbox.
  Source: https://github.com/tabler/tabler/blob/dev/preview/pages/chat.astro
- **shadcnstore/shadcn-dashboard-landing-template**,
  `nextjs-version/src/app/(dashboard)/dashboard-2/components/metrics-overview.tsx`
  — a light metrics strip (not a full grid) for the minimal Home.
  Source: https://github.com/shadcnstore/shadcn-dashboard-landing-template/tree/main/nextjs-version/src/app/(dashboard)/dashboard-2/components

### Proposed screen hierarchy

```
App
├─ Home            (thin status strip: greeting + 4 chips, no tabs, no board)
├─ Chat            (standalone, default landing screen after Home's strip)
├─ Tasks           (flat pending-decision list)
└─ Settings
   ├─ Providers & Brain
   ├─ Connections
   └─ (everything else — Memory, Diagnostics, Preferences, About, Admin — as one flat list of rows, no sub-grouping)
```
4 top-level destinations (down from 6 real sections + 13 nav labels).
Activity and History fold into Chat itself (scroll-back is the history —
see "Disadvantages").

### URI functionality mapping

| Area | Real URI source |
|---|---|
| Home status chips | `HomeSummary.pendingApprovalCount` (also = Tasks count), `unreadEmailCount`, `connectedServiceCount`/`totalServiceCount`, `ActiveBrainInfo.isConfigured` |
| Chat | Existing turn/session loop (`ConversationHistoryStore`, `orchestrator.py`), inline approval cards for proposed actions |
| Tasks | `GET /tasks` — unchanged data, flat list UI instead of `tasks_screen.dart`'s current layout |
| Settings → Providers & Brain | `providers_screen.dart` data (`ActiveBrainInfo`, `ModelInfo`) |
| Settings → Connections | `connections_screen.dart` (Gmail OAuth) |
| Settings (rest) | Existing `memory_settings_screen.dart`, `diagnostics_settings_screen.dart`, `preferences_settings_screen.dart`, `about_settings_screen.dart`, `admin_grants_screen.dart`, `profile_settings_screen.dart`, `capabilities_settings_screen.dart` — kept, just flattened into one settings list instead of categories opened via disguised nav labels |
| Not backed — omitted | Events/deadlines (no calendar capability) |

### Advantages

- Fewest destinations of all three options — lowest cognitive load,
  closest to a familiar chat-app mental model.
- Removes the dead `AskUriScreen` class and the disguised-label nav
  pattern entirely rather than working around them.
- Smallest implementation surface: mostly deletion and flattening, one
  new minimal status-strip widget, one new standalone Chat screen scaffold.

### Disadvantages

- Folding Activity/History into Chat scroll-back loses the dedicated
  cross-session audit view `activity_screen.dart`/`history_screen.dart`
  provide today — acceptable only if the User doesn't need a separate
  audit trail view; otherwise this needs a 5th destination.
- A single flat Settings list of ~10 screens is simple to build but can
  get long; it trades navigation depth for scroll length.
- Least "system awareness" of the three — a user who wants to glance at
  system health without opening chat gets less than in Options B/C.

### Implementation difficulty

**Low.** Net removal of code (dead screen, disguised-label remap logic)
plus one new thin status-strip widget and promoting `UriCommandDock`'s
content into its own routed screen. No new backend calls needed.

### Desktop / mobile suitability

Desktop now: straightforward, no fixed-board scaling needed (unlike
today's `_FixedDashboardBoard`) since the status strip is a normal
responsive row, not a frozen canvas. Mobile later: best of the three —
this shape already matches a phone-first chat-app layout with a bottom
tab bar (Home/Chat/Tasks/Settings), minimal rework expected.

---

## Option B — Productivity Workspace

Chat alongside a fuller work surface: tasks, connections, and provider
management presented as peer workspace areas, closer to a lightweight
admin/productivity app than a companion app.

### Design references used

- **Kiranism/next-shadcn-dashboard-starter**,
  `src/components/layout/app-sidebar.tsx` (grouped sidebar shell) +
  `src/features/chat/components/` (`chat-area.tsx`, `chat-header.tsx`,
  `conversation-list.tsx`, `message-bubble.tsx`, `message-composer.tsx`)
  + `src/features/notifications/components/notification-center.tsx`.
  Source: https://github.com/Kiranism/next-shadcn-dashboard-starter/tree/main/src/features
- **shadcnstore/shadcn-dashboard-landing-template**,
  `nextjs-version/src/app/(dashboard)/chat/` for the chat route-as-sibling
  pattern, and `dashboard-2/components/quick-actions.tsx` for a
  work-surface home.
  Source: https://github.com/shadcnstore/shadcn-dashboard-landing-template/tree/main/nextjs-version/src/app/(dashboard)

### Proposed screen hierarchy

```
App (grouped sidebar — finally rendering the existing but unused
     UriSection.group data: Workspace / Work / Runtime)
├─ Workspace
│  ├─ Home       (metrics-overview + quick-actions style dashboard)
│  └─ Chat       (standalone, conversation-list-ready layout even though
│                 URI has one session today — see mapping note)
├─ Work
│  ├─ Tasks           (notification-center-style pending-decision list)
│  ├─ Connections     (Gmail/OAuth status)
│  └─ Providers       (promoted OUT of Settings to a peer of Connections)
└─ Runtime
   └─ Settings         (Memory, Diagnostics, Preferences, About, Admin, Capabilities)
```
6 top-level destinations, but organized into 3 rendered groups instead of
today's flat, disguised-label list — same section count as today's real 6,
minus the 13-label decoy rail, plus Providers promoted to a real peer
destination instead of a Settings category.

### URI functionality mapping

| Area | Real URI source |
|---|---|
| Home | Same real metrics as Option A, laid out as a proper tile grid (`Overview`-style) instead of a thin strip |
| Chat | Same conversation/turn backend as Option A. The reference's conversation-list rail has **no real backing today** (URI has one session per login, not saved multi-thread history) — if adopted, the list rail should show session/date groupings of existing turn history, not implying multiple independent named conversations that don't exist as a backend concept |
| Tasks | `GET /tasks`, same data as Option A, presented as a notification-center list (icon + description + risk pill + accept/dismiss) |
| Connections | `connections_screen.dart` unchanged in data, promoted to a top-level "Work" destination |
| Providers | `providers_screen.dart` data (`ActiveBrainInfo`, `ModelInfo`), promoted OUT of Settings to its own "Work" destination |
| Settings | Remaining categories only: Memory, Diagnostics, Preferences, About, Admin Grants, Capabilities |
| Not backed — omitted | Events/deadlines |

### Advantages

- Finally uses the `UriSection.group` data that already exists in code
  but is currently thrown away — smallest conceptual gap between "what
  the code already models" and "what the UI shows."
- Promoting Providers out of Settings gives Brain/provider health real
  top-level visibility, which the existing `_BrainStatusPill` in the app
  bar already gestures at wanting.
- Most balanced of the three for a user who treats URI as a daily driver
  across several concerns (mail, tasks, model config), not just chat.

### Disadvantages

- More destinations than Option A — more surface to keep simple.
- The conversation-list rail from the references has no real backend
  concept behind it yet (see mapping note above); building it as
  decoration without real multi-conversation switching would repeat the
  exact mistake being corrected in Option A (a UI element implying data
  that doesn't exist) — it must be scoped down or left out until/unless
  URI actually gains multi-session history switching.
- Grouped sidebar rendering is new UI work; the current sidebar has never
  rendered groups, so this isn't free even though the data model exists.

### Implementation difficulty

**Medium.** Requires: rendering `UriSection.group` in the sidebar (new,
but the data already exists), promoting Providers to top-level (moving an
existing screen, updating its entry point), a proper dashboard tile grid
(more layout work than Option A's strip), and a standalone Chat screen.
No new backend endpoints required if the conversation-list rail is scoped
down to date-grouped turn history rather than a fabricated multi-thread
model.

### Desktop / mobile suitability

Desktop now: good fit — grouped sidebar with 6 destinations reads well at
desktop width. Mobile later: workable but needs the groups collapsed into
a single flat tab bar or a drawer (bottom nav can't show 3 groups
cleanly) — more mobile adaptation work than Option A, less than Option C.

---

## Option C — Operational Dashboard Companion

Keeps a genuine system-awareness dashboard (closest to today's intent)
but corrects the one thing the User specifically flagged: Chat becomes
its own clean workspace instead of a dock riding along under it.

### Design references used

- **shadcnstore/shadcn-dashboard-landing-template**,
  `nextjs-version/src/app/(dashboard)/dashboard-2/components/`
  (`metrics-overview.tsx`, `quick-actions.tsx`, `recent-transactions.tsx`,
  `customer-insights.tsx`) for a full but light metrics-tile-plus-feed
  Home, and `chat/` for Chat as a fully separate sibling route.
  Source: https://github.com/shadcnstore/shadcn-dashboard-landing-template/tree/main/nextjs-version/src/app/(dashboard)
- **tabler/tabler**, `preview/pages/index.astro` and
  `shared/components/cards/TasksDue.astro` for plain, low-chrome stat/task
  cards (keeping "operational" from becoming "decorative").
  Source: https://github.com/tabler/tabler/blob/dev/preview/pages/index.astro
- **Kiranism/next-shadcn-dashboard-starter**,
  `src/features/overview/components/` (`overview.tsx`, and each tile's own
  `-skeleton.tsx`) for independent per-tile loading/error states, matching
  how URI's `HomeScreen` already fires nine independent `load*` calls that
  resolve at different times.
  Source: https://github.com/Kiranism/next-shadcn-dashboard-starter/tree/main/src/features/overview/components

### Proposed screen hierarchy

```
App
├─ Home           (tile grid: pending actions, unread email, connection
│                  health, Brain/provider health — each tile independently
│                  loading/erroring; events/deadlines tile explicitly
│                  marked "not yet available")
├─ Chat           (standalone; NOT reachable through Home, has its own
│                  destination and its own icon)
├─ Tasks          (unchanged data, current tasks_screen.dart layout kept —
│                  it already works and matches the notification-list shape)
├─ Connections    (unchanged, kept as-is)
├─ Providers      (promoted out of Settings, same reasoning as Option B)
└─ Settings       (remaining categories: Memory, Diagnostics, Preferences,
                   About, Admin Grants, Capabilities)
```
6 top-level destinations — same count as today's real 6, but Chat
replaces "Activity" and "History" as a destination (folded into a
"History" tab inside Chat itself, since both are conversational-turn
records) while Providers is promoted out of Settings. Net: one more
genuinely distinct destination (Chat) for one fewer disguised one.

### URI functionality mapping

| Area | Real URI source |
|---|---|
| Home tiles | Same six real metrics as Options A/B: `pendingApprovalCount`/Tasks, `unreadEmailCount`, `connectedServiceCount`/`totalServiceCount`, `ActiveBrainInfo`/`ModelInfo`, `SystemPerformanceSnapshot` (machine health, kept distinct from Brain health per `providers/README.md`); events/deadlines tile shown as explicitly unavailable, not fabricated |
| Chat | Standalone screen; a "History" sub-tab inside Chat reuses `activity_screen.dart`/`history_screen.dart`'s existing data rather than duplicating a second Home-adjacent Activity destination |
| Tasks | `GET /tasks`, current `tasks_screen.dart` UI kept (already fit for purpose per `tasks/README.md`) |
| Connections | `connections_screen.dart`, unchanged |
| Providers | `providers_screen.dart` data, promoted to top-level |
| Settings | Remaining categories |

### Advantages

- Closest to preserving the User's explicitly stated goal ("keeps URI's
  useful live metrics and system awareness") while fixing the one
  explicitly flagged problem (Chat embedded in Home).
- Reuses the most existing, already-working screen code of the three
  options (`tasks_screen.dart`, `connections_screen.dart` kept verbatim)
  — least risk of regressing something that already works.
- Per-tile independent loading/error states (from the Kiranism reference)
  directly match how URI's nine `load*` calls already behave — no new
  synchronization behavior needs inventing.

### Disadvantages

- Highest tile count of the three on Home — most surface area to keep
  from creeping back toward the current dense board if not actively
  guarded during implementation.
- Folding Activity/History into a Chat sub-tab is a real structural
  change to two existing top-level screens, not just an add — needs
  explicit User confirmation that a "History" tab inside Chat is an
  acceptable replacement for two dedicated destinations.
- Of the three, the one most likely to be asked to "add just one more
  tile" over time, since it already frames itself as the dashboard-y
  option — needs the tightest scope discipline against the "don't invent
  unbacked metrics" rule.

### Implementation difficulty

**Medium-high** — the highest of the three, though still simpler than
today's baseline. Requires: a new standalone Chat screen (shared with
A/B), promoting Providers (shared with B), folding two existing
screens' data into a Chat sub-tab (new, not shared with A/B), and
rebuilding Home as an unscaled tile grid with per-tile async states
instead of the current fixed-scale board.

### Desktop / mobile suitability

Desktop now: strong fit — a tile-grid dashboard is exactly what desktop
width is for. Mobile later: hardest of the three to adapt — a
multi-tile dashboard plus a Chat screen with an internal History sub-tab
needs real mobile-specific layout work (stacked tiles, collapsed
sub-tabs), more than either A or B.

---

## Option D — Hybrid (hardest edges of A/B/C reconciled)

Requested by the User after reviewing A/B/C: combine the strongest,
best-evidenced element of each rather than picking one option whole.
This direction resolves Option B's one open gap (Activity/History
placement) and replaces every reference citation that later rendered
differently than its file name suggested with the corrected, screenshot-
verified pattern (see `docs/design_library/screenshots/`).

### Design references used (all screenshot-verified 2026-09-15)

- **shadcnstore/shadcn-dashboard-landing-template**, `tasks` route
  (screenshot: `screenshots/shadcnstore_tasks_table.jpg`) — the
  filterable task **table** with summary tiles, not a kanban board; the
  closest match to `TaskItem`'s real shape (see `tasks/README.md`).
- **tabler/tabler**, `settings.html` (screenshot:
  `screenshots/tabler_settings.jpg`) — nested sub-nav inside one
  Settings page, for URI's ~10 real settings categories.
- **Kiranism/next-shadcn-dashboard-starter** and
  **shadcnstore/shadcn-dashboard-landing-template** chat routes
  (screenshots: `screenshots/kiranism_chat.jpg`,
  `screenshots/shadcnstore_chat.jpg`) — two-pane chat, scoped down (per
  `chat/README.md`) to a date-grouped history list instead of a
  fabricated multi-conversation inbox.
- **shadcnstore/shadcn-dashboard-landing-template**,
  `dashboard-2/components/` (`metrics-overview.tsx`, `quick-actions.tsx`)
  — a moderate tile count, not Tabler's dense 8+-tile dashboard
  (screenshot comparison: `screenshots/shadcnstore_dashboard.jpg` vs.
  `screenshots/tabler_dashboard.jpg`).
- Providers promoted out of Settings, per Option B/C's shared reasoning
  (the existing `_BrainStatusPill` in `app_shell.dart:129` already
  gestures at wanting this) — but grouped together with Connections
  under one "Connections & Providers" destination instead of two
  separate top-level items, to avoid Option B's 6-destination count
  while keeping both visible and distinct within that one screen.

### Proposed screen hierarchy

```
App
├─ Home                    (moderate tile grid: pending actions, unread
│                           email, connection health, Brain/provider
│                           health — 4 tiles, not 6+; events/deadlines
│                           omitted entirely rather than shown as
│                           "unavailable," since it has no backing capability)
├─ Chat                    (standalone; internal "History" tab reuses
│                           activity_screen.dart/history_screen.dart data
│                           — resolves Option B's unresolved gap the same
│                           way Option C did)
├─ Tasks                   (shadcnstore-style filterable table, not the
│                           current tasks_screen.dart card list nor a kanban board)
├─ Connections & Providers (one destination, two clearly labeled
│                           sections: Connections (Gmail/OAuth) and
│                           Providers (Brain/model) — distinct, not merged
│                           into one list)
└─ Settings                (tabler-style nested sub-nav: remaining ~8
                            categories — Memory, Diagnostics,
                            Preferences, About, Admin Grants, Capabilities,
                            Profile, Server)
```
5 top-level destinations — fewer than B/C's 6, more capable than A's 4.

### URI functionality mapping

| Area | Real URI source |
|---|---|
| Home tiles (4) | `HomeSummary.pendingApprovalCount`/Tasks, `unreadEmailCount`, `connectedServiceCount`/`totalServiceCount`, `ActiveBrainInfo`/`ModelInfo` |
| Chat + History tab | Conversation/turn backend, plus `activity_screen.dart`/`history_screen.dart` data reused inside a tab |
| Tasks table | `GET /tasks`, same data, table presentation instead of cards or a board |
| Connections & Providers | `connections_screen.dart` + `providers_screen.dart`, one destination, two sections |
| Settings | Remaining ~8 categories, nested sub-nav |

### Advantages

- Resolves the one concrete open question Option B left unresolved
  (Activity/History), using the same answer Option C already committed
  to, rather than inventing a third approach.
- Every reference citation behind this option was screenshot-verified,
  not inferred from file/folder names alone — two citations in the
  original A/B/C draft (tabler's "single-thread" chat, tabler's "tabbed"
  settings) turned out to render differently once actually opened; this
  option is built only from the corrected versions.
- Fewer top-level destinations than B or C (5 vs. 6) while keeping both
  Providers and Connections visibly promoted, by pairing them on one
  screen instead of splitting them into two nav items.

### Disadvantages

- "Connections & Providers" as one screen with two sections is itself a
  new structural choice not literally present in any single reference —
  it is a synthesis, not a copy, and should be treated as such rather
  than as independently reference-verified.
- Home's 4-tile cap is a deliberate simplicity choice, not the richest
  possible system-awareness view — if the User wants more visible system
  state than Option A's strip but Option C's full grid felt like too
  much, this is the compromise; it will feel thinner than Option C to
  someone who wanted Option C's richness specifically.

### Implementation difficulty

**Low-medium** — between Option A and Option B. No conversation-list
fabrication (like Option B's open risk), no new grouped-sidebar
rendering (also Option B), and only one genuinely new composite screen
(Connections & Providers) beyond what A/B/C already require individually.

### Desktop / mobile suitability

Desktop now: strong — 5 clear destinations, moderate tile count. Mobile
later: better than Option C (fewer destinations, no internal
dashboard-tile-grid-plus-sub-tab combination), not quite as simple as
Option A (a two-section Connections & Providers screen and a Chat
History tab both need real mobile layout decisions Option A doesn't
have to make).

## Comparison at a glance

| | A — Minimal Companion | B — Productivity Workspace | C — Operational Dashboard Companion | D — Hybrid |
|---|---|---|---|---|
| Top-level destinations | 4 | 6 (grouped) | 6 | 5 |
| Chat standalone | Yes | Yes | Yes | Yes |
| Providers promoted from Settings | No | Yes (own destination) | Yes (own destination) | Yes (paired with Connections on one destination) |
| Activity/History | Folded into Chat scroll-back | Kept as-is (unlisted above; would need a 7th slot or similar folding decision) | Folded into a Chat "History" sub-tab | Folded into a Chat "History" sub-tab (same answer as C) |
| Tasks presentation | Current card list | Notification-center list | Current card list (kept as-is) | Filterable table (shadcnstore reference) |
| Dashboard richness | Thin status strip | Full tile grid | Full tile grid + most metrics surfaced | Moderate 4-tile grid |
| Implementation difficulty | Low | Medium | Medium-high | Low-medium |
| Best desktop fit today | All viable | All viable | Strongest (tile grid) | Strong |
| Best mobile fit later | Strongest | Moderate | Weakest | Better than C, not quite A |

Note: Option B's hierarchy above does not list Activity/History at all —
if selected, the User should confirm whether Activity/History folds into
Chat (as in A/C) or is kept as a 7th destination, since Option B's draft
did not resolve this the way A and C explicitly did. This gap is called
out here rather than silently defaulted.

## Self-review correction

While checking this draft against acceptance criterion 3 (simpler than
baseline), the first draft of Option B listed Providers, Connections,
Tasks, Home, Chat, and Settings as 6 destinations but did not account for
Activity/History at all, silently dropping two real existing screens
without saying so. That gap is disclosed above rather than fixed by
silently inventing a resolution on the User's behalf — it is a genuine
open question for whichever direction (or hybrid) the User picks.

## What happens next

None of these are implemented. Per the standing process, the User selects
one direction (or asks for a hybrid/adjustment) before any
`docs/design_library/approved/` record is written or any Flutter code
changes.
