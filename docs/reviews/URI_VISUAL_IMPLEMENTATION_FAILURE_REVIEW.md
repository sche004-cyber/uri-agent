# URI Visual Implementation Failure Review

**Scope:** forensic audit only. No Flutter/Python application source was modified, and this report authorises no implementation, commit, or push.

## Executive Summary

The rebuild is not a faithful reproduction of the approved dashboard. It is an operationally honest, responsive Flutter dashboard that borrows some reference cues, while preserving the previous URI shell, theme extension, data-driven unavailable states, and generic composer. The result has materially different proportions, density, typography, visual hierarchy, chart treatment, and brand composition.

The decisive failure was not just colour choice. The fixed 1024 x 682 board specification in `docs/design_references/dashboard_preview.html:4-24` was not treated as the implementation contract. Flutter instead uses a flexible `Row` with a 300 px rail (`uri_ui/lib/screens/home/home_screen.dart:84-103`) and a scrollable tab host (`home_screen.dart:320-337`). The rendered `.tmp_m26_render/rebuilt_dashboard.png` is therefore a new interpretation, not a matched rendering of `docs/design_references/approved_ui_reference.png`.

M26 remains `DRAFT` and design-only (`docs/plans/M26_STATE.md:1-4`). The active UI work is uncommitted and unverified.

## What Was Expected

The approved screenshot is a 1024 x 677 deep-obsidian board with a 14% / 66% / 20% three-column grid (`dashboard_preview.html:4`), a fixed-bound central composition, subtle cyan atmospheric glow, fine grid texture, glass panels, and cool-white typography. It specifies `#020910`, panel and line tokens, exact `cqw` layout measurements, shadows, radii, gradients, and responsive fallback at `dashboard_preview.html:4,17-24`.

It also specifies the image-led raster eclipse lockup and forest asset: logo at 108% background scale with `screen` blend and no duplicate subtitle; forest used in rail and hero (`dashboard_preview.html:6-16`). Its rail has the complete Home/Chat/Email/Drive/Files/Tasks/Calendar/Graph/Memory/Insights/Model/Tools & Skills/Settings set (`dashboard_preview.html:27`); its centre has five colourful metric cards, four secondary panels, and a docked composer; its right rail is a tight profile-plus-operational-card stack.

## What Was Actually Implemented

The assets are declared at `uri_ui/pubspec.yaml:67-68` and used in the shell (`app_shell.dart:201-204,430-443`) and greeting (`home_screen.dart:147-161`). Reference-blue, pink, mint and gold constants, glass-like panels, painters, a selected blue nav pill, and a blue composer exist (`reference_dashboard.dart:9-31,560-670`; `app_shell.dart:288-299`; `ask_uri_screen.dart:283-365`).

However, the architecture retained is materially different:

* Start-up loads home, connections, tasks, capabilities, memory, activity, account information, and system performance (`home_screen.dart:35-45`), so unknown live-data states dominate the visual result.
* Seven dashboard tabs replace the tightly bounded central bands (`home_screen.dart:113-132,320-337`).
* The raster logo is placed in a 125/180px responsive header and a second companion tagline is rendered in text (`app_shell.dart:195-222`), contrary to the HTML instruction that the raster itself carries the companion line (`dashboard_preview.html:6-12`).
* An independent legacy vector `UriWordmark` eclipse painter remains (`uri_ui/lib/widgets/uri_wordmark.dart:7-138`).
* The screenshot test writes a PNG but only asserts that no exception occurred; it never compares it to the approved image (`uri_ui/test/reference_render_test.dart:49-58`).

## Visual Delta Analysis

| Area | Approved | Current/result | Evidence |
| --- | --- | --- | --- |
| Palette | Obsidian/cyan, root `--blue:#27c9ff` | Global dark theme remains teal: accent `#2DD4BF`, soft `#0F2B29`, ink `#6EE7B7` | `dashboard_preview.html:4`; `uri_theme.dart:83-100` |
| Layout | Fixed board, 14/66/20 columns | Responsive `Row`, flexible centre, 300px rail, scrollable content | CSS line 4; `home_screen.dart:84-103,320-337` |
| Surfaces | Translucent panels with inset top highlight and restrained shadow | Opaque `#081928` to `#030F1A` panels plus outer blue shadow; mixed theme surfaces | CSS `.card,.panel,.sidecard` line 4; `reference_dashboard.dart:23-32` |
| Brand | Integrated small raster halo/eclipse | Enlarged raster, added live subtitle, competing vector wordmark path | HTML lines 6-12; `app_shell.dart:195-222`; `uri_wordmark.dart:7-138` |
| Navigation | 13 reference items, no duplicates | Legacy Connections, Activity and History appended after Settings | HTML line 27; `app_shell.dart:163-180` |
| Hero | Fixed short 8.2cqw band with specified forest crop | Responsive-height asset banner whose typography and whitespace differ | CSS lines 15,18-20; `home_screen.dart:135-222` |
| Metrics | Five equal cards with filled cyan/magenta/mint/amber waves | GPU unavailable and line/dot states; proportions/type differ | HTML lines 29-34; `reference_dashboard.dart:95-230`; rebuilt render |
| Secondary cards | Filled 312-token donut, storage split, compact activity/connections | Tall sparse cards, hollow unknown donut, generic bar and unavailable copy | CSS line 4; `reference_dashboard.dart:300-557`; rebuilt render |
| Right rail | Dense profile and four compact operational cards | Equivalent cards exist but are taller, sparse and warning-led | `ReferenceRail` at `reference_dashboard.dart:670-...`; rebuilt render |
| Composer | Paperclip/mic, circular blue **right arrow**, short tip bar | Retained generic Ask URI dock; output uses upward send arrow and different proportions | CSS `.composer,.send,.tip` line 4; `ask_uri_screen.dart:254-399` |

## Root Cause Analysis

### A. Prompt interpretation failure

**Substantiated.** “Honest live data” was prioritised over the approved visual composition. The M26 design prohibits presenting screenshot values as production defaults (`docs/plans/M26_DASHBOARD_DESIGN_SPECIFICATION.md:884-903`), but that was allowed to turn the replica into an unavailable-state dashboard. The required distinction—visual fixture/presentation contract versus claimed runtime telemetry—was not made.

### B. Insufficient visual reasoning

**Substantiated.** Some hex values were copied, but not their relationships: fixed scale, grid overlay, `cqw` bands, inner sheen, exact image crop/overlay, halo treatment, and optical density. The approved and rebuilt screenshots directly show the flattened result.

### C. Existing-component inertia

**Substantiated.** `HomeScreen` retains its `StatefulWidget`, loading lifecycle, tab switcher, `SingleChildScrollView`, and extracted `UriCommandDock` (`home_screen.dart:28-45,63-79,320-337`). The reference was fitted into old boundaries instead of those boundaries being replaced or isolated for the board.

### D. Theme/style inheritance

**Substantiated.** Old global `UriColors.dark` preserves a teal family (`uri_theme.dart:83-100`). New local blue constants (`reference_dashboard.dart:9-13`) coexist with widgets reading `UriColors.of` (`app_shell.dart:275-277`). This split token authority explains the surviving flat teal/black character.

### E. Inappropriate legacy-widget reuse

**Substantiated.** The general-purpose `UriCommandDock` is retained (`home_screen.dart:77-80`; `ask_uri_screen.dart:189-399`); `UriWordmark` is retained next to the raster reference mark (`uri_wordmark.dart:7-138`); generic `AppShell` owns the rail (`app_shell.dart:46-140`). These are runtime-reasonable reuses, but not screenshot-parity components.

### F. Architecture constraints

**Substantiated.** HTML specifies a fixed aspect-ratio board and only then a mobile media query (`dashboard_preview.html:4,17-24`). Flutter instead shares breakpoint-responsive shell rules (`app_shell.dart:79-139`) and permits scrolling. A one-to-one translation of the supplied vertical bands could not result from that structure.

### G. Test-preservation bias

**Likely contributing pressure; intent unproven.** Existing tests require live `AppState` paths, widget presence and no overflow (`dashboard_shell_test.dart:30-70`). They do not prove the implementer was reluctant to refactor, but they made functional preservation visible while visual parity was unmeasured.

### H. Insufficient asset inspection

**Substantiated.** HTML records 108% logo scale, `screen` blend, contrast/brightness/saturation filter, and no second subtitle (`dashboard_preview.html:6-16`). Flutter only uses `BoxFit.contain` and colour blending (`app_shell.dart:201-204`); no source crop/filter recipe or asset-dimension-derived layout is evident.

### I. HTML/CSS was not used as specification

**Substantiated.** The CSS supplies tokens, grid, band heights, radii, borders, gradients and SVG chart paths (`dashboard_preview.html:4,17-24,30-34`). Flutter contains independently chosen values: radius 9/blur 8 (`reference_dashboard.dart:23-32`), rail width 300 (`home_screen.dart:100-102`) and tab height 42 (`home_screen.dart:231-269`). No 1:1 token mapping exists.

### J. Screenshot/comparison verification absent

**Substantiated.** `reference_render_test.dart:49-58` outputs a 1440 x 920 PNG and asserts `takeException()==null`; it has no reference read, golden comparator, threshold, crop normalisation or difference image. The native reference is 1024 x 677. This gate would have caught the failure immediately.

### K. Model capability limitation

**Contributing, not sufficient.** Coding models can reliably implement a quantified Flutter layout. They are weaker at global visual weight and aesthetic cohesion across shell, theme, charts, assets, rail and composer without measured feedback. The broad multi-file change surface compounds that weakness, but does not excuse ignoring available CSS and image QA.

### L. Task decomposition problem

**Substantiated.** The work bundles shell/navigation, live-data contracts, dashboard tabs, painters, branding, composer, responsiveness and tests. The recent `HEAD~1` diff changes more than 40 UI files. No evidence shows staged visual acceptance of rail, centre, right rail and dock before integration.

### M. Dirty, unverified baseline

**Substantiated.** The worktree is dirty across UI, backend, tests and untracked design artifacts. `AGENTS.md` says the UI work is active and unverified. This prevents reliable render-to-revision attribution and makes approval claims unsafe.

## Model Capability Analysis

| Work | Coding model can reliably do | Requires stronger visual/design control |
| --- | --- | --- |
| Deterministic Flutter | Widget tree, painters, assets, constraints, semantics | Exact token/layout manifest |
| Architecture | Preserve `AppState.ask`, attachment lifecycle and authority boundaries | Architecture owner defines protected paths/state contracts |
| Visual interpretation | Apply a specified design | Optical alignment, glow, crop, hierarchy and composition judgement |
| Design-system extraction | Translate supplied table | Extract/reconcile CSS and screenshot tokens first |
| Screenshot matching | Automate render/diff | Define target, tolerance and review difference image |
| Visual QA | Repair measured deltas | Independent human/design sign-off |

The prior workflow made one implementation model responsible for all six jobs. It should only be final authority for deterministic code after design ambiguity is removed.

## Repository/Architecture Factors

The runtime safeguards are valid: `AppState` owns connection/activity state (`uri_ui/lib/services/app_state.dart:93-94,301-310`) and should not claim unmeasured telemetry. That does not require a different visual design. Clearly labelled reference/demo fixtures, neutral card shells, or explicit presentation contracts could preserve card geometry without representing screenshot data as real.

## Why the Old Theme Survived

1. `UriColors.dark` stayed global authority with teal accents (`uri_theme.dart:83-100`).
2. Reference colours were added locally, not made coherent dashboard tokens (`reference_dashboard.dart:9-13`).
3. Old `AppShell`, `UriCommandDock`, `UriWordmark`, responsive layout and live-state paths remained on the production path.
4. Unknown-data values introduced dashes, “Unavailable,” generic buttons and hollow charts, replacing the reference's visual mass.
5. Tests assert finders/no exception/no overflow, not image equivalence (`dashboard_shell_test.dart:30-70`; `reference_render_test.dart:49-58`).

## Recommended Model Responsibilities

* A strong visual/design model: interpret the approved image, extract assets/tokens/crops, and issue an unambiguous signed specification.
* Architecture authority: map each presentation field to authorised live data, explicit empty state or labelled fixture; preserve URI authority boundaries.
* Coding model: implement that specification literally and record any ambiguity rather than guessing or retaining legacy components.
* Independent visual QA: own side-by-side/difference acceptance.

## Recommended Revised Workflow

1. Extract a machine-readable manifest from `dashboard_preview.html`: every hex/alpha, cqw pixel value at 1024 x 682, font, radius, shadow, SVG coordinate, crop, blend and breakpoint.
2. Have a multimodal/design reviewer reconcile it with `approved_ui_reference.png` and annotate optical corrections; resolve ambiguity before coding.
3. Implement a fixed desktop board first, isolated from legacy shell/theme inertia and live unavailable-state layout changes.
4. Integrate authorised runtime values only after visual parity, preserving footprint and provenance without inventing facts.
5. Render at the approved viewport, enforce a golden/image-diff threshold, and inspect the difference image.
6. Iterate by region: rail/brand, hero/tabs, metrics, secondary panels, right rail, composer. Treat responsive variants as separate accepted designs.

## Acceptance Criteria for the Next Implementation

* Accepted spec maps every approved element/CSS token to Flutter before coding.
* At the agreed native reference viewport, a golden/diff test fails on material delta and writes a reviewable difference image.
* Three-column proportions, complete non-duplicated nav set, five metrics, four secondary cards, asset-led brand, right rail and dock match the reference composition.
* Raster crop/blend/filter and typography/chart/shadow/radius details are visually reviewed.
* Data is authorised live with provenance or explicitly labelled visual state; screenshot numbers are never implied real telemetry.
* A clean isolated diff and independent visual review precede any completion claim.

## Risks

* Literal replication can misrepresent mock telemetry unless fixtures/states are labelled.
* Global palette replacement can regress light mode/unrelated screens; migration must be deliberate.
* Fixed-board parity can create accessibility/responsive issues; variants need their own approval.
* Pixel diffs require pinned fonts, viewport and DPR and still need human review.
* Continuing in a dirty tree makes revision attribution and acceptance unreliable.

## Final Recommendation

Do not incrementally polish the current dashboard as though it were a near-match. Treat it as an unverified operational-dashboard interpretation. Before more code, create and approve an exact visual implementation manifest from the approved HTML/screenshot, isolate the desktop board from legacy shell/theme inertia, and require screenshot comparison before acceptance. Preserve URI runtime truth and authority boundaries, but do not let them substitute a different UI for the approved design.

IMPLEMENTATION STATUS: NOT AUTHORISED
