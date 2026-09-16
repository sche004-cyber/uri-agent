# Model / Provider management — reference patterns

## Current URI reality (verified 2026-09-15)

Provider/Brain management lives inside Settings, not as a top-level
section: `uri_ui/lib/screens/settings/providers_screen.dart`, reached via
`Settings → Model Providers` (see the `'Model'` case in
`app_shell.dart:206`, which opens Settings with category `'Model
Providers'`). Backing data: `ActiveBrainInfo` and `ModelInfo`
(`uri_ui/lib/services/uri_client.dart:692` / `:711`), sourced from
`uri_core/core/model_router.py`, `uri_core/core/provider_registry.py`, and
`uri_core/config/model_roles.py`. `ModelInfo.verified` and
`ActiveBrainInfo.isConfigured` are the two real signals available for a
"provider/Brain health" indicator — there is no separate uptime/latency
health metric today beyond configured-and-verified vs. not.

`connections_screen.dart` is a distinct, separate concept: Google/Gmail
OAuth connection status (`StatusPill.forConnection`), not model/Brain
provider status. The two must not be conflated in a redesign — one is
"which AI models/providers can URI reason with," the other is "which
external services can URI act on."

## Reference patterns

- **Kiranism/next-shadcn-dashboard-starter** —
  `src/components/layout/app-sidebar.tsx` + `user-nav.tsx` for how a
  configuration-style entity (there: user/account) gets its own settings
  surface reachable from the shell without being a top-level nav item —
  same shape URI already uses for Providers-under-Settings.
- **tabler/tabler** — `preview/pages/settings.astro`,
  `preview/pages/settings-plan.astro` — tabbed settings pattern, one tab
  per configurable subsystem (a plan/tier tab is structurally similar to
  a provider/model tab: pick one from a list, show its configured state).
- **shadcnblockscom/shadcn-ui-blocks** — `docs/select.md`, `docs/badge.md`
  (category reference only) — relevant for rendering a provider list with
  a status badge per row (configured/verified/unreachable).

## Guidance for the three-option prototype

Whatever nav structure is chosen, keep Providers/Brain configuration and
Connections (external service OAuth) as clearly distinct areas even if
they are visually adjacent (e.g. both under one "Connections & Providers"
group) — do not merge them into one list where a model provider and a
Gmail connection status-pill sit indistinguishably side by side.

## Decisions

None yet.
