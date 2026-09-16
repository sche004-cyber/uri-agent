# URI Approved UI Functional Prototype — Step 1: Claude Review & Acceptance Criteria

**Milestone:** URI Approved UI Functional Prototype (User-authorized 2026-09-14).
**Role:** Claude — visual/architecture authority, acceptance-criteria setter, bounded fixer.
**Status:** Step 1 complete. Handing off to Codex for the first implementation batch.

This document is the concrete, actionable Step 1 of the approved loop
(`Claude review/criteria → Codex implementation → build/render → Claude
audit → bounded repair → repeat → UI PROTOTYPE READY FOR USER REVIEW`).
It distills `docs/plans/URI_APPROVED_UI_IMPLEMENTATION_PLAN.md` (the
accepted plan) into the specific, checkable criteria this milestone's
first Codex batch is judged against — it does not re-derive that plan.

---

## 1. Frozen Visual Contract & Manifest — CONFIRMED, generated this step

Neither `docs/design_references/dashboard_manifest.json` nor
`uri_ui/lib/theme/dashboard_manifest.dart` existed before this review.
**Both are generated now**, directly from `dashboard_preview.html`'s real
CSS at its native 1024×682 board size:

- `1cqw` in that stylesheet is 1% of the `#board` container's own inline
  size (`container-type:inline-size`), so at native size `1cqw ==
  10.24px` exactly — every pixel value in the manifest is that exact
  arithmetic conversion (computed by a small script, not hand-typed),
  not an estimate.
- The JSON file is the canonical, tooling-generated source; the Dart file
  is its Flutter-consumable mirror. **Both must always be regenerated
  together** if the reference HTML ever changes — never hand-edit one
  without the other.
- Covers: board/column geometry, all 8 named region bands (left rail,
  hero, tabs, metrics, panels, composer, tip, right rail), and the 8 root
  color tokens.
- Does **not** yet cover every micro-detail (per-shadow blur radii, every
  gradient stop, SVG sparkline path coordinates) — those remain sourced
  directly from `dashboard_preview.html` by whoever implements each
  specific widget, using the manifest's band/dimension/token values as
  the frozen outer contract those widgets must fit inside, not a
  substitute for reading the actual reference for a widget's own fine
  detail.

**Acceptance criterion for this item:** any widget change in this
milestone that touches a value present in the manifest must read it from
`DashboardManifest`, never re-type a literal. A PR/diff that hardcodes a
number the manifest already defines fails review.

---

## 2. Region-by-Region Acceptance Criteria

Each region is accepted independently (per the plan's own region-loop,
§7 of the implementation plan) against these checks. A region is not
"done" until all of its own checks pass **and** the User has visually
signed off (plan §6 layer 5) — Codex's own build/render evidence in this
loop satisfies the automated checks only.

### 2.1 Left rail / branding
- Rail occupies exactly `leftColumnFraction` (14%) of the board width at
  native size; width is manifest-driven, not a hardcoded breakpoint.
- Raster logo (`uri_app_logo_refined_v2.png`) at `logoSize`×`logoSize`,
  `screen` blend mode, no separate text caption competing with it (the
  raster already carries "Desktop Companion").
- Nav list contains exactly the 13 items in `DashboardManifest.navItems`,
  in that order — no `Connections`/`Activity`/`History` duplicates (the
  confirmed regression from the second-pass audit).
- Footer: forest photo, fading overlay, quote, org/version line.

### 2.2 Hero / tabs
- Hero band height fixed at `heroHeight` (84px at native scale, scaling
  proportionally at other sizes — never an independently-chosen height).
- Greeting text block + right-aligned quote block, forest photo with dark
  gradient overlay.
- 7-pill tab row, one active state, height fixed at `tabsHeight`.

### 2.3 Metrics row
- Exactly 5 equal-width cards (CPU/GPU/RAM/Disk + System Health), row
  height fixed at `metricsHeight`.
- Each of CPU/RAM/Disk/System-Health backed by real
  `/system/performance` data (already wired) in its `live` state.
- GPU card: always `unavailable` state (no real backend telemetry exists
  — confirmed DEFER, §4 below) — never a fabricated value.
- **Three-state geometry rule (binding, see §3):** `loading`/`live`/
  `unavailable` must render at identical card bounds and identical
  internal layout for every card in this row.

### 2.4 Secondary panels
- 4 panels (Activity, Model Usage, Storage, Active Connections), row
  height fixed at `panelsHeight`, column fractions per
  `panelColumnFractions`.
- Activity: backed by real `/activity` data (already wired).
- Active Connections: backed by real connection state
  (`connection_status.py`, already wired).
- Model Usage: always `unavailable` (no backend request-accounting exists
  — DEFER, §4).
- Storage: no backend source currently confirmed — treat as
  `unavailable` unless Codex confirms a real source exists; do not
  fabricate a value to fill the meter/legend.
- Same three-state geometry rule as §2.3.

### 2.5 Composer + tip line
- Height fixed at `composerHeight`, border radius `composerBorderRadius`.
- Send button uses a **right-pointing arrow** (`arrow-right`), not the
  current up-arrow (confirmed regression, second-pass audit §4.1).
- Tip line height fixed at `tipHeight`, present below the composer.
- Existing attachment/mic/input wiring (`UriCommandDock`) is reused, not
  rebuilt.

### 2.6 Right rail
- Width exactly `rightColumnFraction` (20%) of board width at native
  size.
- Profile row (avatar, name, org), date line, then exactly 4 stacked
  cards in this order: Today at a glance, Current Model, Sandbox &
  Permissions, Tools & Skills.
- "Today at a glance" unread-email count backed by real
  `gmail_search_service.get_unread_count()` (BUILD NOW, §4 — not yet
  wired to `AppState`, this milestone's job to wire it).
- Current Model / Sandbox & Permissions / Tools & Skills: no backend
  request-accounting source confirmed for the Current Model card's
  usage stats specifically — treat those specific fields as
  `unavailable`; the capability/tool-count fields already have real
  sources (`AppState`'s existing capabilities load) and must stay real.

---

## 3. Presentation-State Contract (binding for every card touched this milestone)

Per the implementation plan §4: every card has exactly three states, and
**all three must share identical outer bounds and identical internal
child layout** — only content/color changes between them.

| State | Rule |
|---|---|
| `loading` | Same shape as `live`, a low-opacity skeleton of the same chart/list shape. No layout shift on resolve. |
| `live` | Real data, filled chart exactly as the reference renders it. |
| `unavailable` | Same shape as `live`; chart element still drawn (e.g. the donut ring, the sparkline baseline) in a neutral/desaturated token color, one explicit label where the reference places its caption text. Never a dash-only card, never a hollow/absent chart shape. |

This is a **repair to existing behavior**, not new design: the current
build's confirmed regression (second-pass audit §4.1) is that
`unavailable` currently collapses a card's shape (hollow donut, dash
rows, missing sparkline) instead of preserving it. Fixing this is
in-scope for every card this milestone touches; it does not require
touching a card the milestone doesn't otherwise change.

---

## 4. Backend Classification — CONFIRMED (unchanged from the second-pass audit)

| Item | Decision | Why |
|---|---|---|
| CPU/RAM/Disk/System Health | **BUILD NOW** | `/system/performance` already real, already wired to `AppState` |
| Activity | **BUILD NOW** | `/activity` already real, already wired |
| Active Connections | **BUILD NOW** | `connection_status.py` already real, already wired |
| Unread Gmail count | **BUILD NOW** | `gmail_search_service.get_unread_count()` is a real, implemented method — **not yet wired to `AppState`/the UI**. This milestone's bounded backend task. |
| GPU telemetry | **DEFER** | No backend GPU telemetry exists anywhere in `uri_core` |
| Model usage (donut/request accounting) | **DEFER** | No backend per-model request accounting exists |
| Reminders / scheduled tasks | **DEFER** | No backend concept distinct from existing Tasks/Calendar; needs a User decision on scope, not this milestone |

No item above changes from the second-pass audit
(`docs/research/URI_APPROVED_UI_SECOND_PASS_AUDIT.md` §6) — re-confirmed
here as still accurate before handing work to Codex.

---

## 5. Bounded Fix Applied Directly (Claude, this step)

Per standing bounded-fix authority and this milestone's own explicit
Task Instructions §3:

**`uri_ui/lib/screens/ask/ask_uri_screen.dart:391`** — `UriColors.
textMuted` does not exist (`UriColors` has no such static field, and per
its own documented architecture is never referenced as a bare static —
every color is resolved via `UriColors.of(context)`, matching the
surrounding `Theme.of(context).textTheme` call in the same expression).
Fixed to `UriColors.of(context).inkFaint` — the class's existing,
semantically equivalent "muted text" field — restoring the codebase's
own single-source-of-truth theming invariant rather than adding a new
field that would violate it.

**Verified:** `flutter test test/reference_render_test.dart test/
dashboard_shell_test.dart` — compiles and **6/6 tests pass** (previously
failing to compile at all). `flutter analyze` on the new manifest file:
no issues.

No other compile errors or `UriColors.` misuse found repo-wide (checked
by grep across `uri_ui/lib`).

---

## 6. Handoff

Concrete Codex implementation package for the first batch:
`uri_workspace/dev_workflow/tasks/ui_prototype_codex_task.txt`.

Relay mailbox updated to `HANDOFF_TO_CODEX`.

**Not yet done, and explicitly Codex's first-batch job, not Claude's:**
the fixed-board container (§2 implies it, doesn't build it), the nav-item
dedup, the composer send-icon fix, the three-state geometry repair for
every metrics/panels/right-rail card, and wiring `get_unread_count()`
into `AppState`. This review defines acceptance criteria and fixes the
one blocking compile error — it does not implement the prototype.
