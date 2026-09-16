# Hybrid UI overhaul — implementation preparation

Date: 2026-09-15. Status: REQUIREMENTS-BASED PLANNING DRAFT COMPLETE / VISUAL FIDELITY PENDING ARTIFACT ACCESS. No batch started. Prepared by Codex; Claude plan review and independent audit remain outstanding. User explicitly requested documentation only and will hand Batch 1 to Codex after reviewing the checkpoint.

## Governing scope

Recreate the approved Hybrid presentation structure → reuse working URI services/state/backend underneath it. Follow [design authority](../design_library/UI_DESIGN_AUTHORITY.md), [mapping](../design_library/COMPONENT_MAPPING.md) and [acceptance checklist](../design_library/UI_ACCEPTANCE_CHECKLIST.md). ADR-018, operating policy and Model↔Runtime Contract retain runtime authority and user isolation.

The user's current phase excludes Antigravity and assigns Claude read-only architecture/audit while Codex owns implementation and repairs. This overrides conflicting historical role instructions for this phase. Existing active milestone file still records M31 REPAIRING; this preparation does not close M31, advance a milestone or certify dirty work. Resolve overlapping M31 ownership before a UI batch edits its provider/state files.

## Readiness gates

1. Inspect the [approved published Artifact](https://claude.ai/artifact/FtXLngXPXiRMCY9YQBefht), including Workspace/Compact/mobile/palettes; record version or capture date and reference captures in authority. Direct browser access reached “Sign in to view this page.” User explicitly permits requirements/design-library planning now; visual fidelity remains gated before implementation. Separate local HTML exports are optional, not missing required deliverables. Never substitute the legacy dashboard.
2. Claude reviews/finalizes this draft against those references. This Codex-authored record is not an independent Claude plan or audit.
3. Satisfy four-stage lifecycle using frozen `docs/research/UI_OVERHAUL_ROOT_CAUSE_AUDIT.md`, `docs/architecture/UI_OVERHAUL_CANONICAL_ARCHITECTURE.md`, and `docs/plans/UI_OVERHAUL_MIGRATION_PLAN.md`. This source mapping supplies evidence input, but live Stage 1 inspection has not occurred and these stages are not asserted complete.
4. User reviews checkpoint and hands off Batch 1. No automatic launch; no Antigravity.

## Common execution contract

**Explicit regression risks:** R1 — failed task reads currently return an empty list, causing false “0 pending” in Home/Tasks. Preserve request-specific failure status and test network/HTTP/parse errors versus a successful empty queue. R2 — composer draft is widget-local and can be disposed when AppShell changes its keyed route. Hoist shared presentation state above disposable surfaces and test exact draft/attachment/model/session continuity through navigation and Compact transitions. Both are mandatory Batch 1 safeguards, with Batch 2/4 race and mode-transition coverage; see checklist R1/R2.

Allowed implementation scope after handoff: `uri_ui/lib` presentation, necessary shared presentation state/client error reporting, matching `uri_ui/test`, scoped integration tests, evidence documents. No URI Core redesign, new provider/calendar/project/voice capability, auth policy changes, execution bypass, dependency overhaul, private agent logs or global credential changes. Backend regression tests may run read-only. If a genuinely missing backend contract blocks UI, record it for Claude architecture disposition; never invent an endpoint.

Before each batch record HEAD, scoped dirty diff and file hashes in its report; preserve existing uncommitted work. Run and record current targeted baseline before edits. Failures must be separated into pre-existing, environment-related and new with actual logs. Reports belong in `docs/plans/UI_OVERHAUL_BATCH_<N>_REPORT.md`; Claude audit in corresponding `_AUDIT.md`. No completion by assertion, mock screenshot alone or stale test counts.

Rollback: keep a batch-only patch against that captured working baseline. Revert only that patch if necessary, never reset the worktree or discard M31 changes. Each batch replaces its active route/component rather than leaving two competing shells. Remove obsolete components only once caller inspection proves they are unused.

## Batch 1 — navigation, shell, truthful Home

- Files: `app.dart`, `widgets/app_shell.dart`, `screens/home/home_screen.dart`; introduce sidebar/metric/SuggestedActions shell components under `widgets/`; bounded state/store additions in `services/`; client load-status correction in `uri_client.dart`, `http_uri_client.dart`, mock client and tests if needed.
- Reuse: root auth/bootstrap/AppStateScope, real task/connection/Gmail/Brain sources. Expose an operational Chat route using AskUriScreen immediately so removing Home chat never makes chat unreachable. Connections & Providers can compose existing functional sections pending Batch 3 polish.
- Retire: 13-item manifest navigation, Chat→Home alias, fixed scaled Home board and Home composer. Redirect old Activity/History links to reachable internal Chat views; provider settings links to combined destination.
- Preserve composer draft above disposed routes now. Persist sidebar expanded/pinned choice with a versioned local preference; toggle does not change destination, session or Brain. Do not persist sensitive content in navigation preferences.
- Home: independently loading/erroring real metrics; tasks/approvals clearly one queue; source-grounded action shell. No manufactured calendar/project numbers. Explicit resource-failure states are mandatory before claiming truthful zero counts.
- Targeted tests: `dashboard_shell_test.dart`, `widget_test.dart`, `redesign_test.dart`, `http_uri_client_test.dart`, `chat_lifecycle_test.dart`; new sidebar preference and metric-failure tests.
- Runtime checks: select all five routes expanded/collapsed; pin/relaunch; verify Home and Chat distinct; compare displayed counts to actual successful responses; disconnect backend and distinguish unknown from zero; navigate away/back with draft intact.
- Completion: one shell, five functioning routes, Home without chat, reachable legacy functions, truthful success/empty/failure states, no new targeted failures; evidence ready for Claude read-only audit. No batch 2 until audit/repair resolves batch 1.

## Batch 2 — standalone Chat, actions, Tasks

- Files: `screens/ask/ask_uri_screen.dart`, `widgets/turn_card.dart`, `screens/tasks/tasks_screen.dart`, history/activity screens, shared conversation state and new chat/action components.
- Reuse: ask/model_override, startNewChat/resumeSession, approve/cancel, attachments/files/history/activity. Never re-execute a historical turn to render it.
- Implement New Chat and accessible Copy for user/URI text and relevant prompt/draft; feedback after success, error after clipboard failure. Preserve proposals, approval decisions, memory confirmation, tool/workflow status, generated files and attachments.
- Suggested actions: urgent email fills a read-only prompt and may explicitly launch via canonical ask; approvals opens Tasks; draft opens actual turn; Connect Gmail opens connection setup; Verify provider opens explicit verification surface; Configure Brain opens routing; personalisation opens Preferences/Profile. Never execute a write from a suggestion itself. Halted resume appears only with proven current state and supported canonical continuation, otherwise open conversation for review. Deduplicate stale targets and refresh after decisions.
- Tasks table uses real risk/capability/description/time fields and existing approve/cancel; mobile rows adapt, no authoring board or fabricated completion stats.
- Retire old standalone global Activity/History placement and passive right rail, not underlying functionality.
- Targeted tests: `ask_uri_flow_test.dart`, `chat_lifecycle_test.dart`, `turn_card_test.dart`, `attachment_ui_test.dart`, `m18_history_memory_test.dart`, `m25_ui_defects_test.dart`; add clipboard success/failure, action dispatch/no-write, cross-session race tests.
- Runtime checks: New Chat creates new ID; resume old history retains identity; send text + attachment, inspect grounded response/file, copy exact content; approve/cancel through actual runtime; stale approval fails honestly; Tasks updates across sessions.
- Completion: standalone full chat and real Tasks/actions pass functional and regression checks; no model/global Brain/session leakage; Claude audit resolves findings before next batch.

## Batch 3 — Connections & Providers, Settings, four themes

- Files: combined destination wrapper, existing connections/providers forms, settings_shell/preferences screens, theme/uri_theme.dart, theme_store.dart, app.dart and shared appearance state. Preserve M31 production contracts and coordinate its dirty-file ownership.
- Reuse: provider key/config/verification, discovered verified inventory, active Brain and fallback routing; Google credentials/OAuth status; remaining Settings categories and admin checks. No subscription transport implementation.
- Implement one combined destination with clear service/provider separation; one composer model selector with URI Auto; conversation override never mutates global Brain. Move Appearance into Settings on desktop/mobile; four palettes use one semantic token structure derived from approved references.
- Preference migration: preserve old stored choice; map explicit dark to Graphite and light to Light Professional only after Claude confirms palette authority. For system retain OS-following compatibility until an explicit four-theme selection; unknown keys use recorded default. Keep old key readable; no account sync claim.
- Retire duplicate navigation and component hard-coded colors in touched shared surfaces; remove Home/topbar theme controls. Theme changes must not rebuild/reset conversation/client.
- Targeted tests: `m22_5_providers_test.dart`, `m24_providers_settings_shell_test.dart`, `connections_screen_test.dart`, `preferences_persistence_test.dart`, `settings_server_address_test.dart`, relevant HTTP tests; add four-theme persistence, unknown-key migration, settings-only access and state-invariance tests.
- Runtime checks: real discovered models (not fixed model names), unverified disabled, explicit verify failure/success, selected serving-model caption, global Brain unchanged by override; provider configuration errors preserved; all themes across Home/Chat/Tasks/forms/dialogs with restart persistence.
- Completion: all service/provider/settings functions reachable; four consistent themes from verified references; no fake inventory or auth relaxation; Claude audit resolves findings.

## Batch 4 — Compact, mobile, consistency and full regression

- Files: shared shell/chat presentation state, new Compact surface, responsive screen components/theme tokens, existing platform surfaces only where necessary for same-window mode switching. No second app or backend session.
- Reuse: same AppState, UriClient, sessionId, transcript, draft, attachments, pending response, model override, approvals and file results. Expand always returns to Chat with exact state. Mode changes never create a session or duplicate requests.
- Mobile: five-destination bottom nav or drawer, full-screen Chat, stacked metrics/actions, readable tasks, two-section Connections & Providers, category Settings/Appearance; keyboard and safe areas. No global desktop-scale transform.
- Retire desktop-only assumptions, leftover alternate shells and palette literals. Existing compact composer flag is a reuse seam, not evidence of a complete Compact application mode.
- Targeted tests: new compact/workspace continuity and responsive matrix tests; `chat_lifecycle_test.dart`, `attachment_ui_test.dart`, `dashboard_shell_test.dart`, `reference_render_test.dart`, bootstrap/multi-client/session tests. Run `flutter analyze` and full `flutter test` in `uri_ui`; run project's established full Python regression command recorded from current baseline and targeted M31/authorization/approval/isolation suites. Record exact commands, runtime versions, counts and failures; no invented pass totals.
- Runtime checks: switch during draft/upload/ask/pending approval; rotate/resize and open keyboard; compare session and turn IDs before/after; real attachment capability discovery → runtime validation → result → grounded Brain response; gated write cancelled without side effect and authorized write executed once in a User-approved live test.
- Completion: checklist evidence for all surfaces/themes; no new regression failures; Claude pre-final audit → User live acceptance → Codex repairs if needed → Claude final audit. Commit/push stays with Claude under existing release authority and requires applicable explicit release instruction. Never release automatically from this preparation.

## Audit loop

Claude plan → User handoff → Codex batch/tests/runtime evidence → Claude read-only audit → Codex repair/retest → Claude re-audit → next batch. Repeat through four, full regression, Claude pre-final, User live acceptance, repairs, Claude final, authorized release. Quota unavailability preserves repository checkpoint as WAITING_FOR_MODEL; no silent replacement or Antigravity routing.
