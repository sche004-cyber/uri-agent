# Hybrid Artifact/Canvas design authority

Date: 2026-09-15, **updated 2026-09-16 (Claude, against directly-verified Artifact content)**. Status: user-approved product requirements recorded; visual reference **VERIFIED 2026-09-16**. This is now the frozen design-authority record feeding `docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md` — implementation still requires that blueprint and the mandatory M31 sequencing recorded in `docs/governance/URI_ACTIVE_MILESTONE.md` §1a.

## Authority and provenance

**User-confirmed visual authority:** [Published Claude Hybrid Artifact](https://claude.ai/artifact/FtXLngXPXiRMCY9YQBefht) — title "URI Hybrid Design". **2026-09-16 correction:** the 2026-09-15 "sign-in wall" applied only to an unauthenticated browser/web-reader fetch. Claude read the Artifact directly via the Artifact tool (`action: read`) on 2026-09-16 and confirmed full content access: it is a Claude Design canvas with three source files — `Main.dc.html` (desktop "Workspace Desktop" page, 1280×900, interactive), `MobileApp.dc.html` (390×844, "Mobile" page, interactive), and `Palettes.dc.html` (theme reference, non-interactive) — plus `canvas.json` describing the two pages and their annotations. There is no separate Compact artboard; Compact is a runtime presentation mode toggled inside `Main.dc.html` itself (`presentationToggle` / `this.state.presentation === 'compact'`), rendered as a fixed 420×580 floating window over the same conversation state, not a distinct file. The older dashboard preview is never a substitute.

**Known gap in the reference itself (2026-09-16, do not treat as pending — it is a real, permanent gap in the source, not a verification-access problem):** `MobileApp.dc.html` only builds real layouts for Home and Chat. Its own in-artifact annotation states plainly for Tasks, Connections & Providers, and Settings: *"Full \<X\> screen — see the Workspace Desktop page for the complete \<X\>."* Each of those three renders as a generic centered placeholder card, not a mobile layout. Batch 4 of the blueprint must treat these three as **net-new responsive design work** with no visual reference to match pixel-for-pixel — only the desktop `Main.dc.html` structure, component styling (`--om-*` tokens shared across both artboards), and the general "adapt the desktop section, don't scale it" principle transfer.

The user's attached “Resume URI UI development…” instruction supersedes conflicting historical presentation and coordination instructions for this phase. Claude owns architecture/design mapping/planning and independent read-only audit; Codex owns implementation/tests/runtime repair; User owns live acceptance. Antigravity is excluded. This document was prepared by Codex as a documentation draft, not a Claude approval.

Order: explicit user requirements → latest approved Hybrid interactive prototype → its Compact/mobile/palette references → supporting design-library patterns. Existing Flutter, M26 dashboard and older option proposals are history, never visual authority.

| Required reference | Inspection status |
|---|---|
| Latest Hybrid / Main | **VERIFIED 2026-09-16.** `Main.dc.html`, read in full via the Artifact tool. Structure: collapsible sidebar (icon rail collapsed / icon+label expanded), topbar with theme swatches + Compact-mode toggle, 5 nav destinations (Home, Chat, Tasks, Connections & Providers, Settings), content region switched by page state. |
| Compact Mode prototype | **VERIFIED 2026-09-16.** Not a separate file — a `presentation: 'compact'` state inside `Main.dc.html`, rendered as a 420×580 floating window (`.compact-window`) over the same conversation feed/composer, triggered by the topbar's Compact-mode icon button. |
| Mobile prototype | **VERIFIED 2026-09-16, partial by design.** `MobileApp.dc.html` (390×844) has real layouts only for Home and Chat, with a 5-item bottom nav (Home/Chat/Tasks/Connect/Settings). Tasks, Connections & Providers, and Settings are explicit placeholder cards pointing back to desktop — see the gap note above. This is not an access problem; it is the actual content of the approved reference. |
| Palette/theme references | **VERIFIED 2026-09-16.** `Palettes.dc.html` contains real hex swatches for all four approved themes (Graphite, Deep Navy, Slate + Teal, Light Professional). `Main.dc.html`'s topbar swatch buttons use these exact hex values: Graphite `#c8a25a`, Deep Navy `#5b8fc7`, Slate + Teal `#4a9c92`, Light Professional `#3b5a78` (accent/swatch colors; full per-token palettes are in `Palettes.dc.html` and must be read from it directly during implementation, not re-derived). |
| Design library | DESIGN_INDEX.md, UI_DIRECTION_OPTIONS.md Hybrid section, dashboard/chat/providers/tasks/settings README files inspected. |
| docs/design_references/dashboard_preview.html | Located; older fixed dashboard/dock design, explicitly not substituted for Hybrid. |

Implementation must read the published Artifact directly (via the Artifact tool, `action: read`, or the Antigravity/implementer's own equivalent access) before building each screen, and must reproduce the exact structure and hex tokens found there — not values transcribed secondhand from this document, which paraphrases them for planning purposes only. Do not invent token values or label the older preview approved Hybrid.

## Approved product structure

- Five primary destinations, in order: Home, Chat, Tasks, Connections & Providers, Settings.
- One collapsible desktop sidebar: icon rail collapsed; icons and labels expanded; identical destination identity, selected state and permissions; explicit toggle/pin and persisted local state. No duplicate global navigation tree.
- Home is an operational dashboard. **Exactly 4 metric tiles** (not the reference's 6 — see correction below) plus actionable Suggested Actions / Needs Attention. No chat container or composer on Home.
  - **2026-09-16 correction:** `Main.dc.html`'s Home page actually renders 6 tiles: Pending Approvals, Unread Email, Upcoming Deadline, Connected Services, Brain/Provider, Halted Workflows. Only 4 of these have real URI backend support — Pending Approvals (`GET /tasks`), Unread Email (`GET /gmail/unread-count`), Connected Services (`GET /connections`), Brain/Provider (`GET /providers/active-brain`, `GET /providers`). **Upcoming Deadline and Halted Workflows are fabricated in the reference itself** (no calendar capability exists; no global halted-workflow/project API exists — see `COMPONENT_MAPPING.md`'s "Events/deadlines" and "Halted workflow/project" rows). Implementation must build the 4-tile grid using the reference's tile component styling (`.tile`/`.tile-label`/`.tile-value`/`.tile-hint` classes, `--om-*` tokens) and **must not build the other 2 tiles at all** — not even as a disabled/unavailable placeholder, since the uri-ux-design skill's standing constraint is to omit an unbacked metric entirely, not to invent one and then explain it away.
- Chat is standalone: New Chat, real session/history, user and URI messages, approvals, workflow/tool status, artifacts/results/files, attachments, one model selector, composer. Composer order: attachment, Ask URI anything…, URI Auto/selected model, mic, send. Copy both message types; Copy prompt/draft where relevant; lightweight success feedback only after clipboard success.
- Tasks is a real pending-action table on desktop, readable rows/cards on mobile; preserve approve/cancel. No fabricated completed-task totals or due dates.
- Connections & Providers is one destination with two distinct sections: service OAuth connections and Brain/model providers. Preserve existing configuration, verification and fallback contracts.
- Settings contains remaining functioning categories, including Appearance. Four themes: Graphite, Deep Navy, Slate + Teal, Light Professional. No theme switches on Home or normal topbars.
- Compact is the same application/session: small output/conversation, attachments, one selector, text/send, limited useful status/actions, Expand to Workspace. No second client or independent conversation.
- Mobile uses bottom navigation and/or drawer, full-screen Chat, responsive metrics/actions, dedicated Connections & Providers, Settings → Appearance, safe-area/keyboard handling. Never scale down the desktop board.

## Data and state boundaries

Use one existing AppState/UriClient and canonical runtime loop. Presentation never authorizes an action. Read-only launches may proceed directly; send/write/change proposals retain runtime validation and approval. Experience tier remains UX-only.

Pending tasks and approvals share one queue. Unread Gmail, connected services and configured/verified Brain have real sources. Upcoming events/deadlines lack a verified client contract; omit until backed. Halted-workflow/project suggestions require a real current identifier/status and supported continuation contract; no inferred global count from historical activity. Mic currently has no voice implementation: visible unavailable state, no fake recording.

One semantic theme system covers background, surface, elevated surface, primary/secondary/muted text, border, accent, focus, success/warning/error, selection, typography, spacing and radius across all surfaces. Palette values must come from missing approved references. Device-local persistence is supported; account-level sync is deferred. Theme changes cannot change navigation or runtime state.

## Rejected legacy patterns

Retire the 13-label manifest navigation, Chat→Home alias, fixed scaled dashboard board, embedded Home conversation/dock, duplicated primary History/Activity destinations, competing provider entry trees, hard-coded component colors and prototype topbar theme controls. History/activity stay reachable within Chat. Reuse their data and functional rendering, not their old primary-navigation placement. Do not add widgets around the old shell and call it a redesign.

Supporting patterns: library Hybrid option; shadcnstore tasks table and moderate dashboard; Kiranism/shadcnstore standalone chat; Tabler Settings master/detail. These support structure only and cannot replace missing approved prototype visuals.
