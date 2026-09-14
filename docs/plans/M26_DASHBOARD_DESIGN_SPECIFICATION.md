# M26 — URI Desktop Dashboard & Companion Interface

**Artifact type:** Design specification only  
**State:** DRAFT — DESIGN COMPLETE, AWAITING USER APPROVAL  
**Scope:** Authenticated desktop companion surface; no onboarding redesign, backend implementation, Flutter implementation, test changes, or release commit.

## 0. Design mandate and boundaries

M26 defines the information architecture, visual language, component contracts,
state model, and implementation sequencing for a premium URI desktop dashboard.
It does not implement a screen or change an existing production contract.

The governing architecture remains unchanged:

* The Brain/model reasons and proposes.
* The deterministic runtime validates, authorizes, approves, executes, persists,
  audits, and reports.
* The Flutter client is a thin presentation/client layer. It may render runtime
  reports and initiate user actions, but it cannot grant a capability, approve
  an action, select an authorization role, or claim an execution result.
* `experience_tier` changes UX detail only. It is never an authorization input.
* Route classification and backend role enforcement remain authoritative. A
  visible button is not a permission.
* The hard-reference numbers and labels are visual placeholders, not runtime
  defaults, fixtures, or fallback values. The design-only preview displays the
  supplied reference board as its exact visual source; a future runtime must
  replace every such value with endpoint-backed data or an explicit unavailable
  state.

Onboarding and first-run Brain setup are outside this design. M26 begins after
the existing authenticated/root gate has completed. The existing preference
onboarding and Brain onboarding are not redesigned here.

## 1. Repository audit and existing baseline

### 1.1 Audit basis and delivery status

The audit covered `AGENTS.md`, `PROJECT_MEMORY.md`, `ARCHITECTURE.md`,
`URI_MILESTONE_TRACKER.md`, the governing model/runtime documents referenced by
those files, M22.3–M22.9 plans/states, M23, M24, M25, the reference image, the
current Flutter source, and the current FastAPI/runtime source.

The repository has an important split between documented delivery and observed
working-tree source:

| Evidence | Audited conclusion |
|---|---|
| M23 | Documented as the last independently verified committed feature baseline; graph is read-only/context-only and has no authority path. |
| M24 | `M24_STATE.md` is `NOT VERIFIED`; current working-tree source contains M24-era provider/Brain and memory-settings work, but it is not a verified release baseline. |
| M25 | `M25_STATE.md` is `ACCEPTED`; the plan describes clarification-pause and UI defect remediation, but current changes are uncommitted. |
| Working tree | Flutter, backend, tests, Windows scaffolding, and M24/M25 additions are modified or untracked. These changes are preserved and are not represented as a completed milestone by this document. |
| M26 | This artifact is design-only. No production file is changed by the design. |

For implementation planning, “existing” below means “observed in the current
source”; “verified” means only what the governing milestone state records.
The implementation owner must re-check the actual post-approval tree before
coding.

### 1.2 Existing Flutter architecture

The current client is already a useful thin-client foundation:

| Area | Existing source and reusable behavior |
|---|---|
| Root/app gate | `uri_ui/lib/app.dart`, `main.dart`: persisted preferences, server address, theme, session restore/revalidation, authentication gate, existing onboarding gates, then `UriHome`. |
| Shell | `uri_ui/lib/widgets/app_shell.dart`: `AppShell`, `UriSection`, `ShellIndex`, wide sidebar, compact AppBar/bottom navigation, persistent Brain status pill, safety footer. |
| Current destinations | Home, Tasks, Connections, Activity, History, Settings. There is no separate Chat destination; Home owns the canonical Ask URI conversation. |
| Home | `screens/home/home_screen.dart`: real counts for pending approvals, connected services, usable capabilities, memory entries, recent audit activity, plus the conversation pane. The current wide layout is a side-panel dashboard beside chat, not the M26 operational dashboard. |
| Chat | `screens/ask/ask_uri_screen.dart`: persistent conversation, attachments, processing/approval/execution/failure states, real file picker abstraction, Enter-to-send behavior in the current working tree. |
| Settings | `screens/settings/settings_shell.dart`: wide master-detail and compact list/detail presentation. Categories include Profile, Preferences, Memory, Memory & Context, Capabilities, Model Providers, Diagnostics, About, and admin-only Capability Grants. |
| Providers | `screens/settings/providers_screen.dart`: observed working-tree M24-era tabs for Accounts/API Keys, Local Models, and Custom Endpoints, persistent Active Brain indicator, key/config flows, explicit confirmation before changing Active Brain, usage-limit warning. This source is reusable but not yet a verified M24 release artifact. |
| Connections | `screens/connections/connections_screen.dart`: real Gmail/Drive status, credentials setup, authorize/disconnect actions, and honest server explanation. |
| State | `services/app_state.dart` extends `ChangeNotifier`; `AppStateScope` supplies it; screens use `ListenableBuilder`. This is the default M26 state pattern. |
| HTTP boundary | `services/uri_client.dart`, `http_uri_client.dart`: typed client contracts and response parsing. `MockUriClient` supports widget tests/offline UI but is not evidence for production data. |
| Existing state widgets | `widgets/loading_state.dart`, `empty_state.dart`, `status_pill.dart`, `screen_header.dart`, `turn_card.dart`, `uri_wordmark.dart`, `linkified_text.dart`. |
| Theme/tokens | `theme/uri_theme.dart`: `UriColors` ThemeExtension with light/dark palettes, `UriSpace`, `UriRadius`, and a 900px wide breakpoint. M26 should extend this token system rather than introduce hardcoded per-widget colors. |

The current sidebar branding is text/wordmark based. M26 retains that decision:
no pets, mascots, characters, or anthropomorphic illustrations.

### 1.3 Existing UI models

The requested model files `provider_info.dart` and `mode_info.dart` do not
exist as separate files in the audited tree. Their current typed models live in
`services/uri_client.dart` (`ProviderEntry`, `ActiveBrainInfo`, `ModelInfo`,
`ModeInfo`, `ModelStatus`, `UsageLimitStatus`, and related records).

Existing models relevant to M26 are:

* `UriTurn`, `TurnStage`, `ProposedAction`, `ActionResult`, `ResultSource`, and
  attachment references for the canonical interaction loop.
* `ServiceConnection` and `ConnectionStatus` (`connected`,
  `needsAuthorization`, `notConnected`).
* `TaskItem` for pending approval actions across sessions.
* `ActivityEvent` for structured audit events; it intentionally excludes raw
  prompts/model responses.
* `MemoryEntry`, `MemoryContextSettings`, `ConversationSummary`, `AccountInfo`,
  `DeviceSession`, `CapabilityInfo`, `ProviderEntry`, `ActiveBrainInfo`,
  `ModelStatus`, `ModeInfo`, and `UsageLimitStatus`.

M26 adds design-level view models around these contracts, not duplicate backend
domain models.

## 2. Reference analysis and visual design language

### 2.0 Prior hard-reference preview approach (superseded)

`docs/design_references/dashboard_preview.html` is a design-review artifact,
not a Flutter implementation or a runtime data surface. At its native
1024×682 board it renders `uri_dashboard_reference.jpg` without an added
toolbar, banner, margin, crop, color treatment, or substituted visual asset.
This makes the supplied board the pixel source of truth for the approval
review. Transparent semantic hit areas cover the left navigation, dashboard
tabs, composer controls, and right-rail links so the primary affordances can
be explored without altering the reference pixels.

The fixed composition is: 143px left rail, a 690px central workspace, and a
191px right operational rail. The central workspace begins with the 662px
wide mountain greeting board at x=158/y=29, followed by the seven-item tab
row, a five-card system row, four equal operational panels, and the persistent
command dock. The preview scales that entire 1024:682 board proportionally to
the available review viewport; it does not reflow or invent a responsive
variant during approval.

The reference is a 1024×682 dark desktop composition with a three-region
operational layout:

1. A fixed left navigation/brand rail.
2. A central header, tabbed operational canvas, and persistent composer.
3. A narrow right status rail with glance, model, sandbox, and tools cards.

The target aesthetic is premium, calm, technical, and legible:

* Deep obsidian slate-teal/black canvas (`#050d12`); slightly lifted translucent dark
  surfaces (`#071219`, `#0b1a23`); restrained borders (`rgba(45, 212, 191, 0.16)`);
  a radiant **turquoise green** primary accent (`#14b8a6`, `#2dd4bf`), complemented
  by mint (`#6ee7b7`) and emerald (`#10b981`), with semantic amber/red states.
* Atmospheric greeting banner may use a non-semantic decorative backdrop or
  gradient. It must not imply telemetry, location, weather, or model state.
* Brand & Logo: Faithfully adopts the reference image's visual identity — a bold,
  luminous, glowing gradient wordmark `URI` paired with the clean two-line small-caps
  subtitle `INTELLIGENCE FOR A BETTER TOMORROW`. Strictly typographic and geometric;
  no characters, animals, or mascots.
* Reference Layout Pattern: The central operational canvas follows the reference
  image structure — the System Usage dashboard (CPU, GPU, RAM, Disk, and System Health)
  covers the top section of the screen, while the bottom half accommodates the
  tri-column operational dashboards (Activity breakdown, Model Usage distribution, and
  Storage & Active Connections).
* Charts are explanatory, not decorative. Every chart has a legend, time range,
  empty state, and an accessible text summary.
* Use the existing `UriColors`, spacing, radius, typography, and Material 3
  semantics as the source of truth. M26 introduces dashboard-specific theme
  extension fields (turquoise green accent set) through `UriColors`.
* Light/system theme remains supported by the existing app architecture. The
  reference is the dark art direction, not permission to remove the existing
  light theme.

Recommended content density at desktop width:

```
┌──────────────┬───────────────────────────────────────┬───────────────┐
│ Brand + nav  │ Greeting / tabs / central dashboard   │ Status rail   │
│ 240–272 px   │ Flexible, scrollable, min 640 px      │ 280–336 px    │
│              │ Composer anchored at bottom           │               │
└──────────────┴───────────────────────────────────────┴───────────────┘
```

The widths are layout constraints, not data. At widths where they cannot fit,
the responsive strategy in §10 applies.

### 2.1 Fixed-size review preview (current)

The current `docs/design_references/dashboard_preview.html` is a design-review
artifact, not a Flutter implementation or runtime data surface. It restores
the prior 1024×682 dashboard as a fixed canvas, proportionally scaling the
whole board for smaller review viewports rather than reflowing its regions.
The hero, tabs, metrics, operational panels, command dock, and status rail are
bounded grid/flex bands, so no card expands into another band or is clipped at
the native board size.

The user-provided `misty_forest_sikkim.jpg` appears under readability overlays
in the hero and sidebar footer. The official `uri_app_logo.jpg` replaces the
former CSS-only wordmark and tagline in the left brand rail. Its black raster
field is removed at render time with `screen` blending and a tightly feathered
radial mask, so the silver-white URI lettering remains high-contrast and crisp
against the rail's obsidian background. A narrow cyan-blue halo keeps the
eclipse visible and intentional without diffusing the letterforms; `Desktop
Companion` remains a smaller, legible supporting line. There is no framed
square, badge, or added imagery. No other photograph or reference raster is
rendered. The artificial CSS polygon mountain is hidden. Typography, cards,
SVG sparklines, donut charts, bar histograms, and icons remain crisp native
vector DOM elements. The preview's numerical labels are visual placeholders
only, never runtime defaults or fixtures.

## 3. Backend-to-UI interface mapping matrix

Status vocabulary used in this matrix:

* **Operational:** an existing interface can support the display/action with no
  new semantic claim.
* **Partial:** a related interface exists, but the requested reference behavior
  is incomplete, bounded, or only available through another screen.
* **BACKEND INTERFACE REQUIRED:** the UI must render an unavailable state until
  a real, classified, authenticated contract exists. No client-side estimate or
  platform guess is permitted.

| UI component / field | Source service | Existing endpoint/method | Available fields | Missing or required interface |
|---|---|---|---|---|
| Greeting user name | Auth/session | `GET /auth/me`; `UriClient.getAccountInfo()` | `username`, role, experience tier, device IDs, authenticated flag | None for name. Greeting time is local UI time. |
| Backend reachability | Edge | `GET /health`; `checkConnection()` | `{status: "ok"}` or transport failure | None for reachability. It does not prove model, connector, or sandbox health. |
| Pending approval count | Approval/task read surface | `GET /tasks`; `listTasks()` | `action_id`, capability, description, risk, session, `created_at` | No due date, priority, calendar due date, or task completion contract. Label as approvals until a task domain exists. |
| Activity feed/histogram | Audit trail | `GET /activity`; `listActivity()` | timestamp, event type, status, capability, session ID | Audit is in-memory/current-process only; no durable historical telemetry or event aggregation endpoint. |
| Conversation history | Transcript store | `GET /history`, `GET /history/{session_id}`, `DELETE /history/{session_id}` | session ID, turn count, preview, last activity, turns | None for history. Keep read-only replay semantics. |
| Current Active Brain | Provider registry | `GET /providers/active-brain`, `PUT /providers/active-brain`; `GET /providers` | provider ID, model, display name, configured flag; provider adapter/base URL/configured/available/models/active flags | No provider latency/health history. Do not infer health from `configured`. |
| Provider usage | Usage metering | `GET /usage` | month, totals, by role, by provider, calls, known prompt/eval/duration values, unavailable record count, outcomes, limits | No reliable monetary total when cost is unavailable; show “Unavailable” rather than `$0`. |
| Usage limits | Usage ceiling | `GET /usage/limits`, `PUT /usage/limits`; current client consumes `GET /usage` limits | monthly ceiling, warning ratio, warning, ceiling reached | No separate daily requests contract; “requests today” requires a new aggregation/query field or client-side day fold over a durable, bounded record surface. |
| Model context | Capability/model status and provider catalogue | `GET /capabilities`, `GET /providers` | context window when available; provider/model availability; supports | Context percentage requires current-call/context-used data. If absent, show “Not reported”. |
| Provider credential status | Provider key store | `GET /providers`, `POST /providers/keys` | configured bool, last four only; raw key never returned | No plaintext leakage. No UI should log, cache, or echo the submitted key. |
| Capability catalogue | Capability registry/resolver | `GET /capabilities`; `listCapabilities()` | id, description, status, availability, permissions, approval requirement, risk, platform, limitations, gap reason; model status | None for catalogue read. Route remains a deferred PUBLIC diagnostic GET in M22.3 classification; future exposure review must not be silently assumed complete. |
| Installed skills | Skill installer | `GET /skills` | installed skill ID/name/version/source/digest/status/capabilities/dependencies/entrypoint/validation/timestamps | No direct skill-to-mode result, no client install endpoint, and enable/disable/remove are ADMIN-only. The UI cannot claim a skill is executable merely because it is installed/enabled in the ledger. |
| Capability grant admin | Capability grants | `GET /admin/users`, `GET/PUT /admin/users/{id}/grants` | users, role, grants, registry ceiling | ADMIN endpoint; account role is backend truth. `experience_tier` and `mode` must not be presented as role grants. |
| Connection status | Google credential evidence | `GET /connections`; authorize/disconnect/credentials methods | Gmail/Drive ID, description, connected/needs authorization/not connected, safe detail | No Email/Drive item list endpoint. OAuth is host-scoped and status query is non-interactive. |
| Gmail content/activity | Capability registry + tools | Via `/ask` and registered `gmail_search`/`gmail_find_draft` capability | Evidence arrives only in a turn execution/result selected by the Brain; capability metadata includes permission/gap state | No unread-message count, inbox feed, mailbox sync, or direct `/email` endpoint. `Unread emails` is BACKEND INTERFACE REQUIRED. |
| Drive content | Capability registry + tools | Via `/ask` and `drive_search`, `fetch_drive_spreadsheet`, `drive_upload` | Evidence/result or generated file references; connector state | No global Drive browser contract in Flutter client. A Drive screen is partial until a bounded list/detail interface exists. |
| Session files | FileStore | `POST /files`, `GET /files?session_id=`, `GET /files/{id}/content`, delete | file ID, filename, media type, size bytes; content only by explicit read/open request | No global file index/storage quota/volume usage endpoint. |
| Memory entries | MemoryStore | `GET/POST/PUT/DELETE /memory`, confirm/reject routes | memory ID, category, consent, content, confidence, notes, status, timestamps | None for existing CRUD, subject to authenticated/self-scoped semantics. |
| Memory/context settings | MemorySettingsStore (observed working tree) | `GET/PUT /memory/settings`; `MemoryContextSettings` | persistent/user profile toggles, budgets, provider, context engine, compression, protected recent messages | M24-era work is unverified. Reconfirm route classification, per-user store wiring, and implementation state before execution. |
| Graph | GraphStore/graph engine | Six read-only `GET /graph/*` routes | entities, relationships, provenance, confidence, status, bounded neighbors/path/explain/impact | No client graph screen exists today, but read contracts are present. No graph write route and no graph-based authorization. |
| Calendar | None found | None | None | **BACKEND INTERFACE REQUIRED:** provider identity, read-only event list/count, date range/timezone, authorization state, safe detail. |
| System CPU/GPU/RAM/disk/temperature/fan/power | None found in `uri_core` or Flutter dependencies | None | None | **BACKEND INTERFACE REQUIRED:** authenticated, platform-scoped, sampled telemetry with metric support/permission/freshness and no fabricated fallback. Flutter has file picker/open-file plugins but no telemetry provider. |
| Sandbox status | None found | None | None | **BACKEND INTERFACE REQUIRED:** actual execution isolation mode, enforcement status, host/runtime identity, and last verified time. A client toggle cannot create isolation. |
| Storage volume health | None found | FileStore only exposes per-session file references | Per-file size for files in a session | **BACKEND INTERFACE REQUIRED:** aggregate storage/quota/volume usage and supported scope. Do not sum one session and call it disk usage. |

### 3.1 Required binding rules

1. Every card with a numeric value displays its source and freshness in a
   tooltip or secondary label where practical.
2. A missing field is represented as an explicit state (`Unavailable`, `Not
   reported`, or `Backend interface required`), not `0`, `100%`, a blank chart,
   or a screenshot value.
3. A transport failure is not the same as an empty result. The view model keeps
   `loading`, `loaded-empty`, `unavailable`, and `error` distinct.
4. Provider `configured`, `available`, Active Brain selection, capability
   grants, and route role are different facts. Never merge them into one green
   “ready” badge.
5. Usage aggregations must retain the backend's known/unavailable semantics.
   Estimated or unavailable monetary cost is never displayed as zero.

## 4. Primary navigation architecture

### 4.1 Sidebar destinations

The M26 sidebar expands the existing `AppShell` section model into a stable
desktop navigation rail. It is grouped by purpose, with the current route
highlighted by a luminous accent edge and a restrained surface lift.

| Group | Destination | State | M26 behavior |
|---|---|---|---|
| Workspace | Home | Partial → target Operational | Operational dashboard plus persistent command bar. Current Home counts and conversation are reused. |
| Workspace | Chat | Partial | A named navigation entry may focus the canonical conversation surface, but must not create a second independent transcript/session. Home and Chat share the same `AppState` conversation/session. |
| Workspace | Email | Partial | Connector-aware landing page with Gmail status and “Ask URI” actions. No unread inbox count or mailbox grid until a backend item interface exists. |
| Workspace | Drive | Partial | Connector-aware Drive landing page and Ask URI shortcuts. No fake file list; session attachments and real Drive evidence may be linked where available. |
| Work | Files | Partial | Session attachment browser using `/files?session_id=` and real file references. Global storage/quota is unavailable. |
| Work | Tasks | Operational | Reuse `TaskItem`, `/tasks`, and approve/cancel. Present as “Awaiting approval” until a due-date/task domain exists. |
| Work | Calendar | Future Module | Reserved destination. Render an honest empty/future state with “Calendar interface required”; no local calendar scraping or invented events. |
| Knowledge | Graph | Operational (read-only) | New graph reader using existing bounded `/graph/*` routes; visually emphasize provenance and active/historical status. |
| Knowledge | Memory | Operational / M24 source unverified | Reuse memory CRUD and memory-context settings. Consent state must remain visible. |
| Knowledge | Insights | Partial | Combine existing usage, learning, growth, activity, and graph summaries only where each source is present; missing sections stay unavailable. |
| Runtime | Model | Operational / M24 source unverified | Provider catalogue, Active Brain, usage, limits, context status. Requires explicit confirmation on Brain change. |
| Runtime | Tools & Skills | Partial | Capability and installed-skill read surfaces; admin mutations only where backend route permits. |
| Runtime | Settings | Operational | Existing settings shell remains the configuration home; M26 cards deep-link into categories. |

“Future Module” is a product navigation status, not an authorization state.
The sidebar may show a reserved item if the user can understand why it is not
available; it must not imply a hidden implementation.

### 4.2 Sidebar structure

* Header: URI wordmark, tagline, and `Desktop Companion` subtitle.
* Optional compact environment chip: `Connected to <server>` with backend
  reachability only; never display a fake sandbox/telemetry status here.
* Group labels: Workspace, Work, Knowledge, Runtime.
* Destination rows: icon, label, optional status dot/count. Counts are only
  from real endpoints; no unread email count until available.
* Footer: current user, role display-only pill, theme control shortcut, and the
  existing safety sentence that URI never acts without approval unless the user
  has explicitly allowed it.

## 5. Home / System Telemetry Dashboard

### 5.1 Page composition

The authenticated Home page has four vertical bands:

1. **Greeting banner:** “Good evening, [User]. Let’s make progress today.”
   Time-of-day copy is local UI logic; user name comes from `/auth/me`. A
   decorative atmospheric backdrop can rotate without being read as data.
2. **Dashboard view switcher:** System, Activity, Tasks, Model, Connections,
   Storage, Insights. Tabs change the central operational view, not the sidebar
   destination or session identity.
3. **Central view:** responsive cards/charts for the selected tab.
4. **Persistent composer:** bottom chat/command bar, contextual tip, and
   shortcut cue. It stays available across dashboard tabs but is disabled only
   when the authenticated/session state says it must be.

The right rail remains visible at desktop width and becomes a stack/drawer at
smaller widths. It is a status rail, not a second navigation system.

### 5.2 System tab

The System tab is the reference's primary telemetry canvas, but the current
repository has no telemetry contract. The design therefore defines the target
contract and the honest pre-contract state.

#### Proposed telemetry contract for a future milestone

This is a design requirement, not an M26 implementation:

```text
GET /telemetry/system
  scope: authenticated caller's permitted runtime/device
  query: sample_window, resolution
  response:
    sampled_at, runtime_device_id, freshness_seconds,
    metrics: {
      cpu: { supported, value, unit, confidence, detail },
      gpu: { supported, value, unit, confidence, detail },
      ram: { supported, used, total, unit, confidence, detail },
      disk: { supported, used, total, unit, confidence, detail },
      temperatures: [{ sensor, supported, value, unit, detail }],
      fan: [{ sensor, supported, value, unit, detail }],
      power: { supported, value, unit, detail }
    }
```

The actual endpoint name/schema must be reviewed and classified before
implementation. It must say whether the value is measured, estimated, or
unavailable; expose platform support; be bounded and timeout-safe; and never
run arbitrary commands merely because the UI was opened.

#### Card specifications and reference layout structure

Per User direction (2026-09-12), the System Usage dashboard covers the full top
section of the central operational screen (CPU, GPU, RAM, Disk, and System Health
cards), with the other operational dashboards (Activity, Model Usage, and
Storage & Active Connections) arranged across the bottom half in a balanced
tri-column layout, following the exact composition of the approved reference image.

* **CPU card:** current utilization, load/temperature only when separately
  reported, host/runtime label, sample time, and a bounded recent series.
* **GPU card:** utilization and memory only when the selected runtime can
  report them. Otherwise “GPU telemetry unavailable on this runtime.”
* **RAM card:** used/total only when both are real. Do not derive total from a
  Flutter heap metric and label it system RAM.
* **Disk card:** used/total only from a volume-aware backend contract. Per-file
  sums do not qualify.
* **System Health:** a roll-up of metric support and backend health, not a
  hardcoded green check. “All systems normal” is allowed only when every
  displayed health assertion is backed by a current report.

Each card has a compact sparkline at desktop, a text summary for semantics, a
freshness timestamp, and a details action that explains missing sensors.

### 5.3 Activity tab

Use `/activity` as the source for the event list and histogram. The histogram
may group the returned timestamps by local day/hour only for the returned
current-process window. It must say “Current runtime activity” and show an
empty/restart limitation when no events are returned. It must not imply durable
analytics or count model prompts that the audit trail intentionally excludes.

### 5.4 Tasks tab

Render pending approval actions from `/tasks` with capability, description,
risk, session, creation time, and approve/cancel actions. The tab title can be
“Tasks” for navigation, but the dashboard subtitle should say “Awaiting your
approval” until due dates and completion state exist.

### 5.5 Model tab

Use the detailed Model design in §6. The central view includes provider health,
usage breakdown by role/provider, context-window reporting, budget state, and
fallback/unavailable explanations where the backend exposes them.

### 5.6 Connections tab

Use `/connections` for Gmail and Drive state. Show connection cards and safe
actions. Do not display inbox/message or Drive item counts as a substitute for
connector status.

### 5.7 Storage tab

Until a global storage interface exists, the Storage tab is a file/session
surface, not a disk-telemetry surface:

* Show current-session attachments from `GET /files?session_id=` with real
  filename, media type, and byte size.
* Provide open/download through `/files/{file_id}/content` and delete with
  backend confirmation.
* Show “Volume usage unavailable” for the reference's disk/volume meter.
* Do not sum only the current session and call it “used disk”.

### 5.8 Insights tab

Compose separate source panels:

* Usage: `/usage` totals/by-role/by-provider/limits.
* Learning: `/learning` counts and explicit error list.
* Growth: `/growth` only if the current client contract is extended to parse it.
* Activity: current-process audit summary.
* Graph: bounded entity/provenance counts if a graph query is active.

Every panel identifies the source and time horizon. A unified “insight score”
is not designed because no backend contract supports it.

## 6. Model experience and management

### 6.1 Current Model card

The right rail card displays:

* Active Brain: provider display name + selected model.
* State: configured, reachable/available, unreachable, or not configured. The
  state is assembled from `/providers/active-brain`, `/providers`, and/or
  `/capabilities`; `configured` alone is never treated as reachable.
* Usage: known monthly calls/tokens from `/usage`; daily request count remains
  “Not reported” until supported.
* Context: configured/context window when reported; current context percentage
  is “Not reported” unless the backend supplies both numerator and denominator.
* Cost: only known provider-reported/registry-backed amounts; otherwise
  “Unavailable”. A missing cost is not `$0.00`.
* Action: `Change Model` deep-links to Model Providers and starts the explicit
  confirmation flow.

The reference's “Active Brain” language is retained because it is URI's
constitutional single-brain concept, not a claim that the model has authority.

### 6.2 Detailed Model view

The Model view contains these sections:

1. Active Brain summary and last refresh.
2. Provider catalogue cards from `ProviderEntry`.
3. Local Models, Custom Endpoints, and Accounts/API Keys tabs already observed
   in the current Providers screen.
4. Usage chart from `by_provider` and `by_role`.
5. Budget/ceiling controls using the existing `GET/PUT /usage/limits` contract.
6. Safe configuration notes: base URL/model override may be shown; key values
   never appear, only configured state and last four where the backend returns
   it.

### 6.3 Change Model flow

The flow is a modal or side sheet with three deliberate phases:

1. **Select:** provider and model from the returned catalogue. A provider that
   is not configured or not available can still be inspected but is labelled;
   the primary action explains the consequence.
2. **Review:** show “This will make `<provider>/<model>` URI’s one Active Brain
   for reasoning and planning.” Show current and proposed selections. State
   that no other Brain remains active after confirmation.
3. **Confirm:** require an explicit user click. On success, re-fetch both
   Active Brain and provider catalogue and render the server response. On
   rejection/failure, keep the old selection and show the backend-safe reason.

No silent switching is allowed on provider failure. ModelRouter fallback may be
reported as a runtime outcome, but it must not be presented as a user-selected
Active Brain. The UI never writes role configuration, grants, or provider keys.

### 6.4 Provider credential safety

* API key entry is write-only, masked, and cleared after submission.
* Only `configured` and `last_four` can be rendered from the current contract.
* No raw key in widget state beyond the input lifetime, logs, analytics, crash
  reports, clipboard affordances, or URL query parameters.
* Provider base URLs are displayed as user configuration, with clear local vs
  external labeling derived from the backend/provider data; never expose an
  internal secret-bearing URL.
* Errors are status/detail messages, not request payloads.

## 7. Sandbox, runtime, and permissions design

### 7.1 Honest current state

The audit found no `sandbox`/execution-isolation status endpoint or Flutter
telemetry contract. M26 therefore defines the UI slot but not a claim:

* Card title: `Sandbox & Permissions`.
* Pre-contract status: `Execution isolation status unavailable`.
* Supporting copy: `URI can show permissions reported by the runtime; this
  dashboard cannot create or verify a sandbox by itself.`
* Action: `Manage Permissions` opens capability/grant presentation only; it
  does not toggle an imaginary sandbox.

### 7.2 Future runtime status contract

A future backend contract must report the actual execution environment,
including isolation mode, enforcement status, runtime/device ID, freshness, and
whether a requested capability requires ApprovalGate approval. It must be
classified in `route_classification.py`, authenticated/self-scoped as
appropriate, and tested as a read-only report. A client “toggle” may request a
runtime setting only after such a contract exists; the backend remains the
authority.

### 7.3 Permissions presentation

Use `CapabilityInfo` fields as the current permission display:

* Available now: `status`, `availability`, `gap_reason`.
* Required permission: `permissions`.
* Approval: `approval_requirement`.
* Risk: `risk`.
* Scope/limitations: `platform`, `limitations`, `interface` where safe.

For per-user grants, use the existing ADMIN-only `AdminGrantsScreen` flow and
the `/admin/users/{id}/grants` endpoints. The UI may hide a control as a
convenience after reading `AccountInfo.role`, but only the backend's 401/403
response is authoritative.

The design must visibly distinguish:

* account role (`USER`/`ADMIN`),
* experience tier (`BASIC`/`ADVANCED`, UX only),
* capability mode (`office`/`diagnostic`/`admin`, narrowing capability scope),
* per-user grants, and
* per-action approval.

The word “Admin” must not be used for a self-service mode in a way that implies
role escalation; M25 explicitly identified that confusion as security-sensitive.

## 8. Tools & Skills management

### 8.1 Overview card

The right rail card shows:

* `Enabled capabilities`: count of `CapabilityInfo.isUsable` results, with a
  link to the full list.
* `Installed skills`: count from `GET /skills` records.
* A compact status summary such as “Some capabilities unavailable” when any
  `gap_reason` or skill validation state requires attention.

No count is shown until its source request has completed. Empty is not loading.

### 8.2 Capability list

Each capability row has ID/display description, availability, approval
requirement, risk, permission labels, platform, limitation, and honest gap
reason. Use semantic state pills, not green styling for every registry item.

The primary actions are informational/deep links to Connections, Model, Files,
or Settings. There is no client-side “enable capability” action because the
runtime registry and `CapabilityResolver` own that decision.

### 8.3 Installed skill list

The skill list is a ledger view:

| Display | Source |
|---|---|
| Installed / quarantined / enabled / disabled | `GET /skills` `status` |
| Version/source/digest | Skill installer record |
| Declared capabilities/dependencies | Skill installer record |
| Validation result | Skill installer record `validation` |
| Runtime usable | Cross-reference current `/capabilities`; never infer from installed status |
| Approval required | Cross-reference each declared capability's `approval_requirement`; if no complete mapping, show “Not determined” |
| Disabled by mode | Only show when a future/returned mode-aware contract explicitly supports it; current skill records do not contain a mode result |

Enable, disable, and remove are ADMIN-only backend mutations. Since the current
Flutter client has no direct methods for them, M26 designs the view and status
presentation only; implementation must add a typed client action only with the
same route classification and negative authorization handling.

## 9. Connections experience

### 9.1 Connector cards

Gmail and Google Drive are represented as separate cards even though the current
backend shares Google credentials/token scope. The UI must explain the shared
host authorization safely:

* `Connected`: token evidence is usable for that service.
* `Auth required`: client secret exists but host sign-in has not completed.
* `Host setup required`: no Google client secret is configured on the URI server
  host.
* `Unavailable`: status could not be determined or a connector dependency is
  missing.

The existing `ServiceConnection` mapping is reusable. Authorize/disconnect
actions show the backend explanation verbatim or safely paraphrased without
claiming that a browser flow ran if the server only reported host setup.

### 9.2 Email and Drive destination behavior

Email and Drive navigation pages are connector-aware command surfaces, not
invented inbox/file browsers:

* Email: status, supported URI capabilities (`gmail_search`,
  `gmail_find_draft`, `gmail_create_draft`), and Ask URI shortcuts. Unread count
  stays unavailable.
* Drive: status, supported search/upload/read capabilities, and session file
  links. A Drive item grid waits for a dedicated bounded list/detail interface.
* Write capabilities show approval and scope: Gmail creates a draft; URI does
  not send email. Drive upload never implies overwrite/delete authority.

## 10. Chat bar, slash commands, and contextual tips

### 10.1 Persistent bottom composer

The composer is a shared `UriCommandBar` visual wrapper around the existing
Ask URI composer behavior:

* Attachment button using the existing `FilePickerFn` abstraction.
* Multiline natural-language input with placeholder `Ask URI anything…`.
* Microphone slot is visually reserved but marked unavailable until a real
  speech-input interface exists; do not render an inert action without an
  explanatory tooltip.
* Submit button reuses `AppState.ask`, the existing placeholder/turn lifecycle,
  and backend response parsing.
* Existing attachment chips, server rejection reasons, approval cards, result
  sources, generated file links, and connection prompts remain intact.

Natural language is the default. The composer never requires a command prefix.

### 10.2 Slash command trigger

Typing `/` at the beginning of the current composer token opens a dynamic
command palette. The palette is a view over registered runtime capability data,
not a hardcoded authority list:

1. Load the current `/capabilities` catalogue and filter to displayable entries.
2. On `/em`, match IDs/descriptions such as email-related capabilities; on
   `/dra`, match drafting capabilities.
3. Match case-insensitively and preserve capability ID as the stable selection
   key.
4. Show each command's availability, required permission, approval requirement,
   risk, and limitation before insertion.
5. Selecting a command inserts an optional natural-language accelerator or a
   structured hint into the composer; it does not directly call a tool or
   bypass the Brain/planner/ApprovalGate.
6. If catalogue loading fails, show “Commands unavailable — ask URI normally”
   and leave natural-language input fully functional.

The UI must not make a slash command appear executable when its backend
`gap_reason` says it is unavailable or not implemented. A command can be
visible as a discoverable gap, but its state and action must be clear.

### 10.3 Contextual tips

Tips are short, source-neutral suggestions below the bar. They may be selected
from a static UX copy set because they are not factual claims, for example:

* “You can ask URI in natural language.”
* “URI will ask before a sensitive action.”
* “Attach a file when you want URI to read that specific document.”

Tips must not claim a connector, model, telemetry sensor, or capability is
available unless the current state says so. Include `Press ? for help` as a
keyboard-help affordance, not as a promise that every shortcut is implemented.

## 11. Responsive strategy

The current code uses a 900px wide breakpoint. M26 adopts the requested product
bands while allowing the existing breakpoint to be migrated deliberately in a
later implementation change:

| Width | Layout | Behavior |
|---|---|---|
| 1200px and above | Full desktop | Persistent sidebar, central canvas, right rail, tab switcher, bottom composer. At larger widths the central grid expands; rail widths stay bounded. |
| 768–1199px | Tablet/compact desktop | Collapsible sidebar or icon rail, right rail stacks below/inside a drawer, dashboard cards wrap to two columns, composer remains bottom-persistent. |
| Below 768px | Single column | Drawer navigation, greeting and tabs horizontally scroll or become a segmented selector, cards stack, right rail becomes an ordered section below the central view, composer uses safe-area padding. |

Responsive invariants:

* No horizontal overflow from cards or tables.
* Chart legends can collapse to an accessible details panel.
* The composer must remain reachable when the keyboard opens.
* A drawer/destination change preserves the same `AppState` session and does
  not duplicate the chat transcript.
* Status messages and unavailable states remain visible, not hidden in a
  desktop-only rail.

## 12. Component hierarchy and Flutter architecture

### 12.1 Proposed widget tree

```text
UriApp
└── AppStateScope
    └── MaterialApp / existing theme gate
        └── AuthenticatedCompanionShell (existing AppShell evolution)
            ├── UriSidebar
            │   ├── UriWordmark
            │   ├── SidebarStatusSummary
            │   ├── NavigationGroup × 4
            │   │   └── NavigationDestinationRow
            │   └── SafetyFooter
            ├── CompanionWorkspace
            │   ├── AtmosphericGreetingBanner
            │   ├── DashboardViewSwitcher
            │   ├── DashboardViewHost
            │   │   ├── SystemDashboardView
            │   │   │   ├── TelemetryMetricGrid
            │   │   │   │   └── MetricCard × N
            │   │   │   └── SystemHealthCard
            │   │   ├── ActivityDashboardView
            │   │   ├── TasksDashboardView
            │   │   ├── ModelDashboardView
            │   │   ├── ConnectionsDashboardView
            │   │   ├── StorageDashboardView
            │   │   └── InsightsDashboardView
            │   └── UriCommandDock
            │       ├── AttachmentStrip
            │       ├── UriCommandBar
            │       ├── SlashCommandPalette
            │       └── ContextualTipBar
            └── OperationalStatusRail
                ├── TodayAtAGlanceCard
                ├── CurrentModelCard
                ├── SandboxPermissionsCard
                └── ToolsSkillsCard
```

`Email`, `Drive`, `Files`, `Graph`, `Memory`, `Model`, `Tools & Skills`, and
`Settings` destinations can be routed from the same shell host. The dashboard
tab switcher is a central-view concern and must not become a second shell index
system.

### 12.2 State ownership

Reuse the existing `AppStateScope`/`ChangeNotifier` architecture. Do not add a
parallel Riverpod/BLoC/store architecture for M26.

Recommended state slices are lightweight `ChangeNotifier`/Notifier extensions
owned by `AppState` or created once by the screen and disposed with it:

* `DashboardState`: selected dashboard tab, per-source loading/error/status,
  last refreshed time, refresh request coalescing.
* `SystemTelemetryState`: future telemetry contract, metric support and series;
  in M26 it remains an explicit unavailable state.
* `ModelDashboardState`: provider catalogue, Active Brain, usage, limits,
  confirmation/saving state.
* `ConnectorDashboardState`: connections and connector availability.
* `CapabilityDashboardState`: capabilities, skills, and cross-reference status.
* Existing `AppState` remains the owner of conversation, session, attachments,
  tasks, memory, auth, preferences, and navigation bridges.

Each slice should expose immutable snapshots or read-only collections to
widgets. A refresh of one endpoint must not blank unrelated successfully loaded
cards. Concurrent requests should settle independently and retain per-card
error state.

### 12.3 Model/view-model boundaries

The client models are presentation projections, not new authority objects.
Suggested projections include:

* `MetricSnapshot` with `support`, `value`, `unit`, `confidence`, `sampledAt`,
  `detail`.
* `UsageSnapshot` retaining backend `KNOWN`/unavailable semantics.
* `DashboardCardState<T>` with `idle`, `loading`, `data`, `empty`, `unavailable`,
  `error`.
* `NavigationDestinationSpec` with label, icon, group, product status, and
  route builder.
* `SlashCommandSuggestion` wrapping `CapabilityInfo`; it never holds an
  executable closure that bypasses `AppState.ask`.

No view model may synthesize authorization, approval, provider selection, or
execution outcomes.

## 13. State specifications

All surfaces use the existing `LoadingState`, `EmptyState`, `StatusPill`, and
screen-header conventions, extended with dashboard-specific copy.

| State | Visual treatment | Required copy/action |
|---|---|---|
| Loading | Skeleton/quiet spinner in the card footprint; keep sibling cards usable | “Loading <source>…”; no placeholder numbers. |
| Empty | Calm empty state with icon, explanation, and one useful action | Example: “No activity in this runtime yet.” Action: refresh or Ask URI. |
| Unauthenticated | Do not render authenticated dashboard data | Return to existing login/root gate. Never retain prior user's counts, conversation, files, or provider state. |
| Backend unreachable | Status rail amber/error treatment; preserve last known data only if freshness is explicit | “URI server is unreachable.” Action: check connection/open server settings. Do not relabel stale data as current. |
| Provider unhealthy/unavailable | Provider/model card warning with actual `available/detail/gap_reason` | “Provider unavailable” or backend detail; action: Model Providers. No silent model switch in the UI. |
| Metric unavailable | Metric card keeps its label/icon but uses a neutral unavailable state | CPU/GPU/etc.: “Hardware sensor unavailable.” Provider-derived: “Provider unavailable.” Backend absent: “Backend interface required.” |
| Empty usage | No donut/zero-fill illusion | “No measured model usage for this period.” Explain that unmeasured values are not treated as zero. |
| Partial data | Render available cards, mark missing siblings | “Some dashboard data is unavailable.” Per-card source/detail. |
| Error | Red/semantic error only for an actual failed request or rejected action | Safe error/detail, retry action. Never show exception text if it can leak credentials or internals. |
| Saving/confirming | Disable only the affected control and show progress | For Active Brain: keep current selection visible until server confirmation. |
| Permission denied | Neutral/locked state; no optimistic authority claim | “You do not have permission to manage this.” For admin surfaces, distinguish 401 signed-out from 403 non-admin in client handling where safe. |
| Stale | Timestamp and stale badge; preserve provenance | “Last checked <time>; refresh available.” Never use stale telemetry for a green health roll-up. |

## 14. Data freshness, accessibility, and interaction rules

* Prefer explicit `Refresh` actions and bounded polling only for a future
  telemetry endpoint; dashboard opening alone must not trigger model calls,
  OAuth, capability execution, or file reads.
* Every chart has a non-visual summary and a table/details affordance.
* State color is paired with text/icon; green alone never means “authorized”.
* Keyboard navigation order follows sidebar → header/tabs → central cards →
  right rail → composer. `?` opens help; `/` focuses command suggestions.
* Tooltips explain source, time, scope, and unavailable reason.
* Respect reduced-motion/platform accessibility settings for atmospheric and
  chart transitions.
* The UI must not surface raw prompts, model reasoning, API keys, access tokens,
  filesystem paths, or secret-bearing error strings.

## 15. Milestone implementation plan and boundaries

Execution begins only after this design is approved and independently audited.
The following batches are intentionally sequenced so the shell can be reviewed
without inventing missing backend facts.

### Batch 0 — Contract revalidation and design gate

* Re-read the approved M26 design against the actual clean/working tree.
* Decide whether M24/M25 uncommitted work is included, excluded, or separately
  released; do not silently treat it as verified baseline.
* Confirm all client response shapes and route classifications.
* Create/record the backend-interface-required list as explicit follow-on work.

Boundary: no visual implementation before this revalidation.

### Batch 1 — Shell and visual system

* Evolve `AppShell`/navigation specs into grouped sidebar + responsive host.
* Add dashboard dark-art-direction tokens through the existing ThemeExtension,
  preserving light/system mode.
* Add greeting banner, view switcher, rail/card primitives, empty/loading/error
  states, and shared spacing/semantics.

Boundary: cards may use only already-available data or explicit unavailable
states. No mock telemetry.

### Batch 2 — Central operational views backed by existing contracts

* Activity, Tasks, Model, Connections, Storage-session, and Insights panels.
* Provider/usage/Active Brain integration with explicit confirmation.
* Capability/skill read-only inventory and links to existing settings/admin
  screens.
* Graph read-only view using bounded existing graph routes, with provenance.

Boundary: no new authority path, no skill mutation shortcut, no graph writes.

### Batch 3 — Composer and command palette

* Extract/reuse the current Ask URI composer into the persistent command dock.
* Add slash suggestions backed by `/capabilities` and preserve natural-language
  default.
* Keep turn lifecycle, attachments, approvals, sources, and generated files on
  the existing `AppState`/`UriClient` path.

Boundary: slash selection never directly executes a registered capability.

### Batch 4 — Right rail and cross-surface deep links

* Today-at-a-glance with date and real tasks/connector fields only.
* Current Model and usage card.
* Sandbox card in explicit unavailable state until backend status exists.
* Tools & Skills card with source/freshness and settings links.

Boundary: unread email, upcoming events, hardware telemetry, global storage,
and sandbox isolation stay unavailable until a separately approved contract.

### Batch 5 — Responsive, accessibility, and state hardening

* Tablet/mobile drawer/stack behavior.
* Keyboard/focus semantics, screen-reader summaries, chart alternatives,
  reduced motion, stale/error/unauthenticated transitions.
* Verify user-switch/logout clears all user-scoped visual state.

### Batch 6 — Separate backend interface milestones, if approved

Candidate follow-on contracts are independently scoped and security-reviewed:

1. System telemetry read endpoint.
2. Calendar read-only connector/event summary.
3. Global storage/quota report.
4. Sandbox/runtime isolation report.
5. Durable activity aggregation, if product needs cross-restart analytics.
6. First-class Email/Drive list/detail APIs, if dedicated destination pages are
   desired.

These are not implied implementation work in M26's dashboard UI milestone.

## 16. Explicit non-goals and protected boundaries

M26 does not:

* redesign onboarding, first-run setup, account creation, or the existing Brain
  onboarding screen;
* modify `ApprovalGate`, `ApprovalStore`, `ToolDispatcher`, capability
  registry/resolver authority, route authorization, or model/runtime contract;
* grant capability access based on sidebar visibility, mode labels,
  experience tier, provider availability, or any client state;
* build a sandbox, hardware telemetry collector, calendar connector, global
  storage scanner, inbox sync, or Drive browser without a separate backend
  contract;
* expose raw credentials, model chain-of-thought, raw prompt content, or
  filesystem paths;
* copy mock numbers from the visual reference into code or fixtures;
* create a second chat/session architecture parallel to the existing canonical
  conversation;
* treat uncommitted M24/M25 source as a verified milestone release;
* commit or push code as part of this design phase.

## 17. Design acceptance checklist for the next audit

Before implementation is accepted, Claude's independent audit should confirm:

* the two design artifacts exist and no production code changed in this phase;
* every reference card has an endpoint mapping or an explicit
  `BACKEND INTERFACE REQUIRED` state;
* no reference screenshot number is used as a runtime default or fallback;
* sidebar/product status is distinct from backend authorization status;
* Active Brain change requires explicit user confirmation and post-write
  re-fetch;
* permissions are represented only, while runtime enforcement remains in the
  backend;
* system telemetry, calendar, sandbox, unread email, and global storage remain
  honest until contracts exist;
* the existing `AppShell`, `AppStateScope`, `UriClient`, models, theme tokens,
  turn lifecycle, and connection/memory/provider surfaces are reused rather
  than duplicated;
* responsive and accessibility requirements are testable without introducing
  a new state-management architecture;
* the implementation plan contains no unauthorized production changes.
