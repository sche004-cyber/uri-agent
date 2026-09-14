# M26 Dashboard Preview — Visual QA

**Reviewed artifact:** `docs/design_references/dashboard_preview.html`

**Canvas:** fixed 1024×682 board, proportionally scaled as a single canvas.

**Asset verification:** the preview references only the supplied
`docs/design_references/misty_forest_sikkim.jpg` and
`docs/design_references/uri_app_logo.jpg` rasters. The forest image is used
beneath dark readability overlays in the greeting banner and sidebar footer;
the logo is screen-blended into the left rail without a visible image boundary.
No Himalaya or reference-board raster is rendered.

**Render verification (2026-09-12):** Chrome headless rendered the local file
at 1024×682. The capture shows distinct, non-overlapping vertical bands for:

- hero and dashboard tabs;
- metric cards and operational panels;
- persistent composer and contextual tip;
- every right-rail status card; and
- sidebar navigation and forest footer.

The health card is bounded within the metrics band, preventing its final status
row from crossing into the operational panels. The composer and the final
Tools & Skills card remain fully visible inside the native canvas. The left-rail
logo keeps the URI wordmark as the brightest, sharpest element, with a defined
but secondary cyan eclipse arc and a legible `Desktop Companion` line.

The logo's increased contrast and brightness are applied before the restrained
cyan drop shadow. This keeps its white/silver letter edges clear against the
obsidian rail while `screen` blending and the radial mask leave no rectangular
raster boundary.

**Result:** PASS for the requested fixed-size layout, overlap resolution, and
approved-asset constraint. This remains a design-only artifact; its displayed
values are visual placeholders rather than runtime data.
