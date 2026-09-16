---
name: uri-ux-design
description: "Use before designing, redesigning, or proposing any URI Flutter screen or navigation structure. Reference-first UX process for this repository: inspect real URI backend capability first, then search docs/design_library/ for a matching structural pattern, then map URI functionality into that structure. Existing uri_ui/ layout is implementation history, not design authority. Trigger: any request to design, redesign, mock up, or restructure a URI screen, dashboard, chat workspace, provider/connections screen, tasks screen, or settings/navigation."
---

# URI UX / Product Design Process

This is the repository-specific process for designing any URI screen. It
is the standing companion to the general `ui-ux-pro-max` skill: use
`ui-ux-pro-max` for general UI craft (typography, color, component
choice, accessibility), and use this skill first, every time, to decide
*what structure* a URI screen should even have before applying that
craft. Established 2026-09-15 at the User's direction, when URI UI
development moved to a reference-first design process.

## Mandatory sequence, before designing any URI screen

1. **Inspect the relevant URI backend capability/state.** Read the actual
   endpoint, model, or capability module the screen will represent —
   `uri_core/app/server.py`, the relevant `uri_core/capabilities/*`
   module, and the Flutter-side model/client method in
   `uri_ui/lib/services/uri_client.dart` and `uri_ui/lib/models/`. Use
   `graphify query "<question>"` first per this repo's standing graphify
   rule (see root `AGENTS.md`) to locate these quickly. Never assume a
   metric, capability, or data field exists — confirm it against the real
   endpoint/model. If it doesn't exist yet, say so explicitly in the
   design rather than designing around an imagined capability.

2. **Search `docs/design_library/` for a matching structural pattern**
   before sketching anything from scratch. Start at
   `docs/design_library/DESIGN_INDEX.md`, then the category folder that
   matches the screen (`chat/`, `dashboard/`, `providers/`, `tasks/`,
   `settings/`). Check `approved/` and `rejected/` first for that
   screen — do not re-propose a structure already rejected, and do not
   redesign a screen whose structure was already approved without a new
   reason.

3. **Prioritize functionality and clarity over visual complexity.** A
   reference pattern is adopted for its structure (what regions exist,
   how they relate, what a user can do in each), not for decorative
   density. When a reference repo's version of a pattern is more ornate
   than URI's real data supports, simplify it — do not pad a screen with
   sections that have no real backend behind them just because the
   reference has them.

4. **Treat existing URI Flutter layout as implementation history, not
   design authority.** The current `uri_ui/lib/screens/` and
   `uri_ui/lib/widgets/app_shell.dart` structure records what was built
   and why (often with a comment explaining a past User-reported defect
   it fixed) — valuable evidence for what NOT to repeat, not a template
   to extend by default. A screen redesign is free to discard the
   existing layout entirely if the reference-first structure serves the
   real capability better.

5. **Select a reference structure first**, from the design library,
   before writing any Flutter-specific layout detail. Name which
   reference and which specific path(s) within it are being adapted (per
   the citation style already used in `docs/design_library/*/README.md`).

6. **Map URI backend functionality into that structure afterward.** Only
   once a reference structure is chosen does the real capability/data
   from step 1 get placed into its regions. If the mapping doesn't fit
   cleanly, prefer adjusting which reference elements are used over
   forcing URI's data into a shape it doesn't have.

## Recording the outcome

- If a structure is selected for actual implementation, write a record to
  `docs/design_library/approved/<screen>_<date>.md`.
- If a candidate structure is considered and turned down, write a record
  to `docs/design_library/rejected/<screen>_<date>.md` so it is not
  silently re-proposed later.
- Update the relevant category `README.md`'s "Decisions" section to point
  at the new record.

## Standing product constraints (do not violate silently)

- Chat is a first-class, standalone workspace — never re-embed it as a
  dock or widget inside a Home/System dashboard screen. See
  `docs/design_library/chat/README.md` for why this was explicitly
  called out.
- Preserve the real dashboard metrics that have actual backend support:
  unread emails, pending approvals/tasks (currently one data source, not
  two — see `docs/design_library/dashboard/README.md`), connection/service
  health, and provider/Brain health. Do not invent an events/deadlines
  metric as if it were backed today — no calendar capability exists yet.
- Any new screen or navigation proposal must be evaluated against the
  Verification-First Audit and Planning Standard in the root `AGENTS.md`:
  cite real evidence (endpoint, model field, existing screen file/line),
  not assumption, and disclose explicitly whatever could not be verified.
- Multiple alternative directions are User decisions, not something
  Codex picks unilaterally — present options with references,
  advantages/disadvantages, and difficulty, and wait for the User's
  selection before implementing.
