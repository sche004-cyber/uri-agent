# URI Hybrid UI — Frozen Implementation Blueprint

**Status: FROZEN. Implementation has not started. This document is the sole authoritative implementation spec for the URI Hybrid UI initiative, superseding `docs/plans/UI_OVERHAUL_IMPLEMENTATION_PLAN.md` wherever the two differ.**

**Date frozen:** 2026-09-16
**Authors:** Codex (2026-09-15 planning draft) → Claude (2026-09-16 independent review, verdict `READY_WITH_CHANGES`) → User (accepted verdict, directed blueprint production) → Claude (this document, incorporating all review findings).
**Do not start another planning/review cycle on this document.** Per explicit User instruction, exploration ended at freeze. Implementation follows this document precisely; deviations that are discovered during implementation go through the repair loop in §9, not a new planning pass.

---

## 1. Roles for this initiative (2026-09-16, supersedes AO-4 defaults for this work only)

- **Claude (CLI) and Codex (CLI): planning and independent plan review only.** Neither writes UI or reconciled-backend production code for this initiative. Neither performs a bounded-fix, audit-for-release, or release role here — this is a deliberate, explicit departure from the general AO-4 roles recorded in `ORCHESTRATION.md` §1 / `AGENTS.md`, scoped to this initiative.
- **Antigravity (Gemini 3.8 Flash): primary implementer.** Builds every batch below directly against this document, in addition to its existing Loop Manager/Orchestrator duties.
- **Qwen 3 14B (local Ollama): implementation review.** Reviews Antigravity's implementation of each batch against this document and produces concrete, itemized findings. This supersedes Qwen's normal "reserve/fallback, User-invoked only" status for this initiative specifically.
- **Antigravity (Gemini 3.8 Flash): repair.** Fixes the concrete findings Qwen's review produces, per batch, then hands back to Qwen for re-review.
- **User: live acceptance and final go-ahead**, per the standing live-verification gate — unchanged by this role override.
- Full governance reconciliation: `ORCHESTRATION.md` §0, `AGENTS.md` item 7, `PROJECT_MEMORY.md` "UI-Initiative Role Override", `docs/governance/URI_ACTIVE_MILESTONE.md` §1a.

Loop per batch: **Antigravity implements → Qwen reviews → Antigravity repairs findings → Qwen re-reviews → User live-accepts → next batch.** No step in this loop is performed by Claude or Codex.

---

## 2. Mandatory sequencing — hard dependency on M31

**Do not start Batch 1 (or any later batch) until `docs/governance/URI_ACTIVE_MILESTONE.md` records M31 — Model & Brain UX as Claude `VERIFIED` and committed/pushed to `origin/master`.**

Reason: M31's own "CURRENT WRITE SCOPE" already covers `uri_ui/` broadly (providers screen, ask_uri screen, composer, models, state, widgets, tests) and `uri_core/core/model_router.py`, `provider_registry.py`, `app/server.py`. This is not a partial overlap confined to one batch — it spans the same files every batch below touches (Batch 1: `app_shell.dart`, `app_state.dart`, `http_uri_client.dart`; Batch 2: `ask_uri_screen.dart`, `turn_card.dart`; Batch 3: `providers_screen.dart`, `connections_settings_screen.dart`, `model_router.py`-adjacent client code). Starting any batch while M31 is still `REPAIRING`/`AUDITING`/`IMPLEMENTING` risks the two initiatives silently clobbering each other's changes to the same files — exactly the kind of collision the Verification-First standard exists to catch before it happens, not after.

At blueprint-freeze time (2026-09-16), M31's own state file (`docs/plans/M31_STATE.md`) records: Codex implementation complete, awaiting User live acceptance, then Claude final audit under the standing live-verification gate. This is a concrete, near-term unblocking condition — not an indefinite wait.

**Check before starting Batch 1:** re-read `docs/governance/URI_ACTIVE_MILESTONE.md` §1 fresh (do not trust a cached view) and confirm `CURRENT STATE` for M31 reads `VERIFIED`/`COMPLETE` with a recorded commit. If it does not, stop and wait — this is a hard gate, not a preference.

---

## 3. Governing references (read these before implementing any screen)

- **This document** — authoritative sequencing, batch scope, and corrections.
- `docs/design_library/UI_DESIGN_AUTHORITY.md` — structure, verified reference inspection (2026-09-16), the 4-real-tile correction, the mobile-placeholder gap, palette hex values.
- `docs/design_library/COMPONENT_MAPPING.md` — per-region real backend citation (endpoint/model/file:line), reconciled 2026-09-16.
- `docs/design_library/UI_ACCEPTANCE_CHECKLIST.md` — the evidence checklist every batch must satisfy (updated 2026-09-16).
- `docs/design_library/approved/hybrid_ui_2026-09-16.md` — the formal approval record (what was chosen, what was explicitly excluded, why).
- **The published Hybrid Artifact itself:** `https://claude.ai/artifact/FtXLngXPXiRMCY9YQBefht` ("URI Hybrid Design"). Read it directly (Artifact tool `action: read`, or Antigravity's equivalent access) before building each screen — this blueprint transcribes the structural facts needed to implement without re-deriving them, but exact CSS values/spacing beyond what's quoted below should come from the source, not be reinvented.

---

## 4. Verified reference structure (transcribed 2026-09-16 from the Artifact's actual source files, so implementation does not need to re-derive it)

The Artifact is a Claude Design canvas with three files: `Main.dc.html` (desktop "Workspace Desktop" page, 1280×900, interactive), `MobileApp.dc.html` (390×844, "Mobile" page, interactive), `Palettes.dc.html` (theme swatch reference, static). There is **no separate Compact file** — Compact is a `presentation: 'compact'` state toggled inside `Main.dc.html` itself.

### 4.1 Shell / navigation (desktop)

- Sidebar: brand row (mark + name + collapse button) at top, then 5 nav items with icon + label (expanded) or icon-only rail (collapsed, `.nav-rail-item`, 44×44 logical px, `title=` tooltip). Active item gets `.active` (soft accent bg/fg).
- Nav items, in order: **Home, Chat, Tasks, Connections & Providers, Settings.** (Collapsed-rail tooltip text for the 4th is the full "Connections & Providers".)
- Topbar: breadcrumb-style page name on the left; on the right, 4 theme swatch buttons (circular, 16×16, `title=` theme name) then a Compact-mode icon button.
- Theme swatch accent colors (from `Main.dc.html`'s topbar, confirmed against `Palettes.dc.html`): Graphite `#c8a25a`, Deep Navy `#5b8fc7`, Slate + Teal `#4a9c92`, Light Professional `#3b5a78`. Read `Palettes.dc.html` directly for the full per-token palette (bg/surface/border/text/accent/success/warning/error) for each of the four — do not guess intermediate tokens from the accent alone.

### 4.2 Home

**Tile grid — build exactly 4 tiles, in this order, using the reference's `.tile`/`.tile-label`/`.tile-value`/`.tile-hint` component pattern:**

| Tile (reference label) | Real source (see COMPONENT_MAPPING.md for full detail) |
|---|---|
| Pending Approvals | `HomeSummary.pendingApprovalCount` via `GET /tasks` |
| Unread Email | `AppState.loadUnreadEmailCount` via `GET /gmail/unread-count` |
| Connected Services | `listConnections` via `GET /connections` |
| Brain / Provider | `loadActiveBrain`/`listProviders` via `GET /providers/active-brain`, `GET /providers` |

**Do not build these two reference tiles at all** (not even as a disabled/"coming soon" placeholder — omit entirely per the uri-ux-design skill's standing constraint):
- "Upcoming Deadline" — no calendar capability exists.
- "Halted Workflows" — no global halted-workflow/project listing API exists (`UriTurn` status can expose per-conversation evidence only; see COMPONENT_MAPPING.md's "Halted workflow/project" row).

Below the tile grid: a Suggested Actions / Needs Attention panel (`.suggest-actions` pattern) — build from real current tasks/connections/providers/navigation state per COMPONENT_MAPPING.md's "Suggested Actions" row. Each suggestion is read-only navigation or an explicit prompt-fill; **no suggestion ever executes a write directly from a tap.**

No composer or transcript on Home (unchanged from the existing authority).

### 4.3 Chat

- Standalone screen, own route, reachable immediately (never re-embedded in Home).
- History: a "New chat" affordance (`+`) above the feed; existing turns render as message bubbles with a per-message Copy action (`.msg-actions`/`.msg-action`, copy icon, `{{item.copyLabel}}` — shows transient "Copied" feedback after clipboard success only, never before).
- Empty state: "New conversation — ask URI anything to begin."
- **Composer, top to bottom:** a text row (`Message URI…` placeholder) above an icon row containing, left to right: **attachment button (paperclip) → model selector (label + chevron, opens a dropdown menu) → mic button → send button.** This matches `UI_DESIGN_AUTHORITY.md`'s stated composer order (attachment, message field, model selector, mic, send) — the reference simply puts the text field on its own row above the icon row rather than inline; either arrangement satisfies the authority's ordering requirement, but the icon *sequence* (attachment, model, mic, send) must be preserved exactly.
- **Model selector — reconciliation with M31 (mandatory, see §7 below):** the reference's dropdown (`URI Auto` / `Claude Sonnet 5` / `GPT-4o` / `Llama 3.1 8B (local)`, all always-enabled) is **visual reference only**. The actual implementation must be M31's real `ModelSelectorChip` + `ChooseModelPopover` behavior: real discovered/verified provider inventory, unverified models disabled with a red dot and explicit reason text, `URI Auto` retained as a real entry, selection sent as `AskRequest.model_override` without mutating global Active Brain, and a "Conversation model: <model>" caption reflecting the persisted turn history. Do not ship the reference's flat always-enabled list.
- Approval/proposal cards, tool/workflow status, attachments, and result rendering: re-theme the existing `TurnCard` rendering paths (per COMPONENT_MAPPING.md's "Approval/workflow/result" and "Attachments/files" rows) into the new visual language — do not rebuild their logic.

### 4.4 Compact

- Not a separate screen/session. Toggled via the topbar's Compact-mode icon button (`presentationToggle`), which sets `presentation: 'compact'` on the **same** app/session state.
- Renders as a fixed 420×580 floating window (`.compact-overlay` / `.compact-window`) centered over the app background, with its own scaled-down header, feed (`.compact-feed`, denser bubble padding/font-size), and composer (identical field order to §4.3, denser sizing).
- Expand returns to Workspace with the exact same session ID, transcript, draft, attachments, model override, and any pending/in-flight response — this is a presentation-mode switch, never a new session, never a duplicate request.

### 4.5 Tasks

- Page header + 4 summary tiles (`Total Pending`, `Low Risk`, `Needs Review`, `High Risk` — computed client-side from the real `GET /tasks` rows' `risk` field, not separate endpoints) + a search/filter row (`Search tasks…`, an "All risk levels" filter chip) + a data table (`Description`, `Capability`, `Risk`, `Created`, action column with an approve icon button).
- Table rows are real `TaskItem`s only — no fabricated completed/due-date columns, no kanban board. Clearing the filter restores the full list. Approve/cancel refresh the queue with real success/failure feedback (see COMPONENT_MAPPING.md's "Tasks" row and R1 below).

### 4.6 Connections & Providers

- One screen, two columns/sections: **Connections** (left) and **Providers** (right), each `.card` containing `.list-row` entries (avatar icon, name, status line, trailing pill: `Connected`/`Reconnect`/`Verified`/`Verify`/`Not configured` etc.).
- Connections section: real Google/Gmail OAuth status only (per `connections_screen.dart`/`connections_settings_screen.dart`) — the reference's illustrative second "Slack" row has no real URI backend and must not be built.
- Providers section: real discovered/verified provider inventory (`providers_screen.dart` data — `ActiveBrainInfo`, `ModelInfo`), preserving existing configuration/verification/fallback-routing contracts. This absorbs M31's Connect Provider work (Figma 1:71) restyled into this layout — see §7.

### 4.7 Settings

- Nested sub-nav pattern (two labeled groups) + a detail card on the right, matching the reference's visual structure exactly, but populated with URI's **real** settings screens, not the reference's illustrative labels:

| Group | Real screens to include |
|---|---|
| Account | Profile (`profile_settings_screen.dart`), Preferences (`preferences_settings_screen.dart`), Memory (`memory_settings_screen.dart`), Memory & Context (`memory_context_settings_screen.dart`) |
| System | Server (`uri_server_settings_screen.dart`), Capabilities (`capabilities_settings_screen.dart`), Diagnostics (`diagnostics_settings_screen.dart`), Admin Grants (`admin_grants_screen.dart`, USER/ADMIN-gated), About (`about_settings_screen.dart`), **Appearance (new, see below)** |

**Do not build a "Tools & Skills" nav item** — the reference shows this label but no such real URI screen/capability exists; it is illustrative only and must be dropped, per the uri-ux-design skill's "map only real, verified backend capability" rule.

Appearance (new, moved into Settings per the authority): the 4-theme picker (Graphite/Deep Navy/Slate + Teal/Light Professional) lives here, backed by `theme/uri_theme.dart` + `services/theme_store.dart`. No theme control anywhere else (remove the existing prototype topbar/Home theme controls other than the Hybrid topbar's own theme swatches, which are the one approved exception — see §4.1).

### 4.8 Mobile (390×844 reference width)

- 5-item **bottom navigation** (this resolves the plan's open bottom-nav-vs-drawer question — the reference itself uses bottom nav, confirmed directly in `MobileApp.dc.html`): Home, Chat, Tasks, **Connect** (abbreviated label for Connections & Providers), Settings. Same destination set and order as desktop.
- **Home and Chat have real mobile layouts in the reference** — build these to match: Home shows a condensed suggestion card + the same 4-tile logic stacked; Chat is full-screen with the same composer field order as desktop, denser sizing, and a `modelMenuOpen` popover variant of the model selector.
- **Tasks, Connections & Providers, and Settings have no real mobile layout in the reference** (they render as placeholder cards there). This is genuine, unreferenced responsive-design work for Batch 4 — see §8.4. Base these three on the *desktop* Hybrid structure (§4.5–§4.7) adapted with standard responsive patterns (stacked tiles, full-width table rows becoming cards, single-column settings list with a back-button drill-in instead of a two-pane nested nav) — not on any mobile mockup, because none exists for them.

---

## 5. Global architecture rules (apply to every batch)

- **Reuse, never rebuild, the runtime loop.** One `AppState`/`UriClient` instance; presentation never authorizes an action; read-only navigation may proceed directly; every send/write/approval keeps existing runtime validation and approval-gate behavior unchanged.
- **No parallel/fake functionality.** Every screen/tile/action maps to a real endpoint or model field cited in `COMPONENT_MAPPING.md`. If a genuinely missing backend contract blocks a Hybrid element, stop and record it for disposition (per §9) — never invent an endpoint or a client-side approximation.
- **R1 (mandatory, all batches touching data fetches):** a failed fetch is never rendered as a successful empty/zero result. `HttpUriClient.listTasks` (and equivalent methods for connections/unread-count/providers) currently collapse network, HTTP-error, and parse failures to `[]`/defaults (verified at `http_uri_client.dart:765-785` for `listTasks`) — this must be replaced with an explicit tri-state result (loading / confirmed-value / failed) surfaced to the UI, tested against actual network/HTTP/parse failure injection, not only mocked `AppState`.
- **R2 (mandatory, all batches touching navigation/state):** composer draft, staged attachment, model override, and session ID must survive navigation (Chat → Home → Tasks → Chat, sidebar toggle, Compact ↔ Workspace) without loss or duplication. `AppShell`'s `KeyedSubtree(ValueKey(_index))` and `UriCommandDock`'s local `TextEditingController` (verified structure) must have their state hoisted above the disposable route subtree — implement this in Batch 1 and prove it again for Compact in Batch 4.
- **No fabricated metrics anywhere**, not just Home — apply the same standard to any tile/summary/count introduced in any batch.
- **One semantic token system** (`--om-*`-equivalent: bg/surface/elevated/border/text tiers/accent/success/warning/error/selection) driving all 4 themes across every surface, including Compact and mobile — no hard-coded hex in component code.
- **Theme changes never touch navigation, session, or runtime state** — verify this explicitly per batch.

---

## 6. Batch plan

Batches below are Codex's 2026-09-15 draft batches, corrected per this review. File lists, reuse/retire lists, and runtime-check lists from `docs/plans/UI_OVERHAUL_IMPLEMENTATION_PLAN.md` §"Batch 1–4" remain valid **except** where this section overrides them. Read that document's batch sections alongside this one; where they conflict, this document wins (per the header note).

### Batch 1 — Navigation, shell, truthful Home

- Files: `app.dart`, `widgets/app_shell.dart`, `screens/home/home_screen.dart`; new sidebar/tile/SuggestedActions components under `widgets/`; state additions in `services/app_state.dart`; R1 client-side fix in `uri_client.dart`/`http_uri_client.dart`/mock client.
- Build: 5-destination sidebar (§4.1), Home with **exactly 4 tiles** (§4.2) + Suggested Actions. Expose a reachable Chat route immediately (never let removing Home's embedded chat make Chat unreachable even transiently).
- Retire: 13-item manifest nav, Chat→Home alias, fixed-scale Home board, embedded Home composer/conversation.
- R1 and R2 (§5) are Batch 1 deliverables, not deferred — implement and test both here.
- Targeted tests: `dashboard_shell_test.dart`, `widget_test.dart`, `redesign_test.dart`, `http_uri_client_test.dart`, `chat_lifecycle_test.dart`, plus new sidebar-preference and metric-failure-state tests (R1/R2 coverage).
- Runtime checks: all 5 routes reachable expanded/collapsed; sidebar pin persists across relaunch; Home and Chat visually and functionally distinct; disconnect backend and confirm Home shows "unavailable," never "0"; type a draft, navigate away and back, confirm it's intact.
- Completion gate: one shell, 5 working routes, Home with no chat, 4 real tiles only (no "Upcoming Deadline"/"Halted Workflows"), R1/R2 proven, no new test failures.

### Batch 2 — Standalone Chat, actions, Tasks

- Files: `screens/ask/ask_uri_screen.dart`, `widgets/turn_card.dart`, `screens/tasks/tasks_screen.dart`, shared conversation state, new chat/action components.
- Build: Chat per §4.3 including the **model-selector reconciliation in §7** (this is the batch where that reconciliation must land — do not ship the reference's flat dropdown even temporarily). New Chat, Copy (message + relevant draft/prompt, clipboard-failure-safe), History tab reusing `activity_screen.dart`/`history_screen.dart` data. Tasks per §4.5 (filterable table, 4 summary tiles computed client-side).
- Reuse: `ask`/`model_override` plumbing, `startNewChat`/`resumeSession`, `approve`/`cancel`, attachments/files/history/activity data paths — never re-execute a historical turn to render it.
- Suggested-actions wiring (from Home, §4.2): urgent-email fills a read-only prompt (may launch via canonical `ask` only on explicit user action), approvals opens Tasks, draft opens the actual turn, Connect/Verify open Connections & Providers, personalization opens Settings → Preferences. No suggestion executes a write on tap/render alone.
- Targeted tests: `ask_uri_flow_test.dart`, `chat_lifecycle_test.dart`, `turn_card_test.dart`, `attachment_ui_test.dart`, `m18_history_memory_test.dart`, `m25_ui_defects_test.dart`, plus new clipboard success/failure and no-write-from-suggestion tests.
- Runtime checks: New Chat creates a new session ID; resuming history preserves identity without re-execution; send text + attachment and confirm a grounded response; approve/cancel through the real runtime; a stale approval fails honestly; Tasks updates are consistent across sessions.
- Completion gate: standalone Chat with real model-selector behavior (§7) and real Tasks pass all functional/regression checks; no model/session/Brain leakage between conversations.

### Batch 3 — Connections & Providers, Settings, four themes

- Files: new combined `Connections & Providers` screen (composing `connections_settings_screen.dart` + `providers_screen.dart`), `settings_shell.dart` + the settings screens listed in §4.7, `theme/uri_theme.dart`, `theme_store.dart`, `app.dart` theme binding.
- **Preconditions specific to this batch:** confirm M31 is `VERIFIED`+committed (§2) before touching `providers_screen.dart` — this is M31's own primary file. Absorb M31's Design 02 (Connect Provider) content into the Hybrid Providers section rather than building a second, competing provider UI.
- Build: Connections & Providers per §4.6 (two sections, real data only, no illustrative "Slack" row). Settings per §4.7 (real screen set, two groups, no "Tools & Skills"). Appearance moved into Settings, 4 real palettes from `Palettes.dc.html` driving one semantic token system (§5).
- Preference migration: preserve any existing stored theme choice; map old "dark" → Graphite and old "light" → Light Professional only after this blueprint's palette values are the ones implemented (they are, as of freeze); unknown/old keys fall back to a recorded default; "system" retains OS-following behavior until an explicit 4-theme choice is made.
- Targeted tests: `m22_5_providers_test.dart`, `m24_providers_settings_shell_test.dart`, `connections_screen_test.dart`, `preferences_persistence_test.dart`, `settings_server_address_test.dart`, plus new four-theme-persistence, unknown-key-migration, and settings-access tests. **Also re-run `tests/test_m31_model_brain_ux.py` (Python) and `flutter test test/chat_lifecycle_test.dart` as an M31 non-regression check** — this batch is the highest-risk one for silently undoing M31's just-verified provider/model-selector work.
- Runtime checks: real discovered models (not fixed names) in Providers; unverified disabled with reason; explicit verify success/failure preserved; global Active Brain unaffected by any conversation override; all 4 themes rendered correctly across Home/Chat/Tasks/forms/dialogs, surviving restart.
- Completion gate: all service/provider/settings functions reachable; 4 consistent themes from the verified `Palettes.dc.html` values; M31 non-regression tests pass; no fake inventory or auth relaxation.

### Batch 4 — Compact, mobile, consistency, full regression

- Files: shared shell/chat presentation state, new Compact overlay component (§4.4), new mobile bottom-nav shell + responsive screen components, shared theme tokens.
- Build: Compact per §4.4 (same session, 420×580 floating window, same composer field order, Expand returns to Workspace with exact state). Mobile per §4.8: **Home and Chat follow the reference layout; Tasks, Connections & Providers, and Settings are new responsive designs** (stacked tiles → cards, table rows → cards, nested settings nav → single-column drill-in) built from the desktop Hybrid structure, not from any mobile mockup, since none exists for these three. Bottom nav: 5 items, "Connect" abbreviated label, same order as desktop (§4.8 — already resolved, do not reopen as an open question).
- Reuse: same `AppState`/`UriClient`/session/transcript/draft/attachments/pending-response/model-override/approvals across mode switches. Mode changes never create a session or duplicate a request.
- Targeted tests: new Compact/mobile continuity and responsive-matrix tests; `chat_lifecycle_test.dart`, `attachment_ui_test.dart`, `dashboard_shell_test.dart`, `reference_render_test.dart`, `multi_client_test.dart`, `bootstrap_screen_test.dart`. Run `flutter analyze` and full `flutter test` in `uri_ui`. Run the project's full Python regression command (record the exact command/count from the current baseline) plus targeted M31/authorization/approval/isolation suites, including `tests/test_m31_model_brain_ux.py` and `tests/dev_workflow/test_security_boundary.py`.
- Runtime checks: switch Compact↔Workspace during an in-flight draft/upload/ask/pending-approval and confirm no duplicate submission; rotate/resize and open the keyboard on mobile; compare session/turn IDs before/after every transition; a gated write is cancelled with no side effect and an authorized write executes once in a User-approved live test.
- Completion gate: checklist evidence (per `UI_ACCEPTANCE_CHECKLIST.md`) for all surfaces/themes/modes; no new regression failures; User live acceptance; release stays with Claude under existing release authority and requires a separate explicit User release instruction — **this initiative's role override in §1 does not touch release authority, which this blueprint does not delegate to Antigravity.**

---

## 7. Model-selector reconciliation (M31 ↔ Hybrid composer) — mandatory detail for Batch 2

The Hybrid Artifact's composer model selector is a **position and trigger pattern only** (a labeled chip that opens a dropdown, placed between the attachment and mic icons). Its actual list content (`URI Auto`/`Claude Sonnet 5`/`GPT-4o`/`Llama 3.1 8B (local)`, all rendered as equally clickable) is illustrative and must not ship as-is, because it has no verified/unverified distinction and no real provider-discovery backing.

M31 (once `VERIFIED`) will already have built the real behavior: `ModelSelectorChip` (the composer trigger) and `ChooseModelPopover` (the menu), wired to real discovered/verified provider inventory, unverified entries disabled with a red-dot indicator and explicit reason text, `URI Auto` as a real routed entry, per-conversation override via `AskRequest.model_override` without mutating the global Active Brain, and a persisted "Conversation model: <model>" caption.

**Batch 2 must re-skin M31's existing `ModelSelectorChip`/`ChooseModelPopover` components into the Hybrid visual language (position, sizing, menu styling matching `.model-select`/`.model-menu` in the reference) rather than building a new selector from the reference's mockup markup.** Concretely: keep M31's state/logic layer (discovery, verification-gating, override plumbing, caption persistence) untouched; restyle only its presentation to match the Hybrid composer's visual spec in §4.3. If M31's actual shipped component structure differs from what's assumed here, re-read `docs/plans/M31_MODEL_BRAIN_UX_PLAN.md` and the real `ModelSelectorChip`/`ChooseModelPopover` source at Batch 2 start time — this is exactly the kind of "genuinely missing/changed contract" case §5 says to record rather than improvise around.

---

## 8. Reference gaps requiring genuine new design work (not reference adaptation)

Recorded explicitly so implementation does not mistake "no reference exists" for "look harder for one":

1. **Mobile Tasks screen** (§4.8) — no mobile mockup exists. Design from desktop Tasks (§4.5) using standard table→card responsive conversion.
2. **Mobile Connections & Providers screen** (§4.8) — no mobile mockup exists. Design from desktop (§4.6): likely two full-width sections or a segmented toggle between them, given mobile width can't show two columns side by side.
3. **Mobile Settings screen** (§4.8) — no mobile mockup exists. Design from desktop nested nav (§4.7): a single-column category list that drill-in navigates to each screen, with a back button, rather than the desktop's persistent two-pane layout.
4. **"Connections & Providers" as one screen with two sections** — per the approved record (`docs/design_library/approved/hybrid_ui_2026-09-16.md`), this pairing is itself a synthesis not literally present in any single upstream reference; treat the two-column desktop layout (§4.6) as the settled answer, not an open question.

For all four, Qwen's implementation review (§1) should specifically check that the built screen preserves every real data field/action from the corresponding desktop section and doesn't silently drop functionality while adapting layout.

---

## 9. What happens if implementation finds a genuine blocker

If Antigravity discovers during implementation that a real backend contract is missing, that M31's shipped component structure doesn't match §7's assumption, or that a Hybrid structural element genuinely cannot map onto real URI capability: **stop that specific piece, record the blocker in the batch's report (`docs/plans/UI_HYBRID_BATCH_<N>_REPORT.md`), and continue other unblocked work in the same batch.** Per §1, resolving a genuine blocker that requires a plan change is Claude's/Codex's job (planning/review), not Antigravity's to improvise around — it does not require restarting this whole review cycle, only a scoped addendum to this blueprint if the fix is non-trivial.

---

## 10. Freeze statement

This blueprint incorporates every required change, missing/under-specified item, and recommendation from Claude's 2026-09-16 independent review (verdict `READY_WITH_CHANGES`, accepted by the User) of Codex's 2026-09-15 planning draft. Per explicit User instruction, planning stops here: no further review cycle, no implementation by Claude or Codex. Antigravity begins Batch 1 only once §2's M31 gate is satisfied.
