# M26 STATE

STATE: DRAFT (DESIGN COMPLETE — AWAITING USER APPROVAL)

**Plan:** `docs/plans/M26_DASHBOARD_DESIGN_SPECIFICATION.md`

## Deliverable

The M26 design package is complete. It contains the repository audit, visual
language, backend-to-UI mapping matrix, navigation architecture, dashboard and
telemetry design, model/Active Brain flow, permissions and skills presentation,
connections, persistent composer and slash-command design, responsive strategy,
Flutter component hierarchy/state ownership, honest state specifications, and
implementation boundaries.

## Scope record

**Preview revision (2026-09-12):** The review board is restored to its prior
fixed 1024×682 composition and scales proportionally as one canvas. Its left,
central, and right regions retain their original proportions; bounded grid
bands prevent metric cards, operational panels, composer, and status cards
from overlapping or clipping at the native size. The user-supplied
`misty_forest_sikkim.jpg` remains dark-overlaid in the hero and sidebar footer.
The versioned `uri_app_logo_refined_v2.png` derivative is displayed as a
seamless left-rail brand mark: `screen` blending removes its black raster
field, crisp silver-white URI letterforms sit inside one continuous restrained
cyan eclipse, and the heavier `Desktop Companion` subtitle stays readable at
rail scale. No production Flutter or backend code is affected.

* Design only.
* No Flutter screens/widgets implemented.
* No production UI, backend, tests, or milestone tracker changes made.
* No commit or release claim made.
* Onboarding remains out of scope.
* Hardware telemetry, Calendar, sandbox status, unread email count, and global
  storage usage are explicitly marked `BACKEND INTERFACE REQUIRED`.
* Current uncommitted M24/M25/platform work is treated as observed working-tree
  context, not as a verified M26 or prior release baseline.
* The preview is a native 1024×682 design composition, proportionally scaled
  as a single board in smaller review viewports.
* The semantic controls let reviewers exercise navigation, dashboard tabs,
  command dock controls, and rail links without changing its design-only
  placeholder status.
* The preview is strictly design-only: it does not modify `uri_ui/` or
  `uri_core/`, call a runtime, create a product data fixture, or represent an
  implementation milestone.

## Approval gate

Awaiting User approval before a separately scoped implementation milestone is
initiated.
