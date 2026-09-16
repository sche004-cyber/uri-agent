# Settings / navigation structure — reference patterns

## Current URI reality (verified 2026-09-15)

`SettingsShell` (`uri_ui/lib/screens/settings/settings_shell.dart`) hosts
at least ten sub-screens as categories, not separate top-level nav items:
`about_settings_screen.dart`, `admin_grants_screen.dart`,
`capabilities_settings_screen.dart`, `connections_settings_screen.dart`,
`diagnostics_settings_screen.dart`, `memory_context_settings_screen.dart`,
`memory_settings_screen.dart`, `preferences_settings_screen.dart`,
`profile_settings_screen.dart`, `providers_screen.dart`,
`uri_server_settings_screen.dart`. The visual left-rail nav
(`DashboardManifest.navItems`, 13 labels) further routes several
non-Settings-sounding labels into specific Settings categories via
`AppStateScope.of(context).openSettingsCategory(category)` —
e.g. `'Graph'` → category `'Memory & Context'`, `'Model'` → category
`'Model Providers'`, `'Tools & Skills'` → category `'Capabilities'`
(`app_shell.dart:199-215`). This means today's real navigable surface is
6 top-level `AppShell` sections plus ~10 Settings categories reached
through category deep-links disguised as top-level nav items — a
significantly more complex real structure than the 6-section list alone
suggests, and worth simplifying rather than preserving as-is.

## Reference patterns

- **tabler/tabler** — `preview/pages/settings.astro`,
  `preview/pages/settings-plan.astro`. Renders (screenshot:
  `../screenshots/tabler_settings.jpg`) as a nested left sub-nav
  (Business Settings: My Account / My Notifications / Connected Apps /
  Plans / Billing & Invoices; Experience: Give Feedback) inside one
  Settings page — not literal top tabs as the source filenames implied.
  Corrected from this document's earlier "tabbed" description. This
  nested-sidebar-within-Settings shape is the closer match for URI's ~10
  existing settings categories than a flat tab strip would be.
- **Kiranism/next-shadcn-dashboard-starter** —
  `src/app/dashboard/profile/`, `src/app/dashboard/billing/` — each
  settings-adjacent concern as its own routed page under one `dashboard/`
  parent, reachable from a single settings/account entry point rather
  than scattered across the primary nav.
- **shadcnblockscom/shadcn-ui-blocks** — `docs/sidebar.md`,
  `docs/tabs.md` (category reference only) — vocabulary for choosing
  between a nested-sidebar-within-settings vs. a flat-tabs settings page.

## Guidance for the three-option prototype

Each of the three options must propose one settings/navigation approach
and be explicit about which of the ~10 existing settings categories it
keeps, merges, or drops — not just gesture at "Settings" as one opaque
item the way the current nav rail's disguised deep-links do today.

## Decisions

None yet.
