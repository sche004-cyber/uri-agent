# URI UI overhaul preparation — handoff index

Date: 2026-09-15, prepared by Codex (documentation-only draft; superseded
2026-09-16). **Superseding update, 2026-09-16:** Claude independently
reviewed the 2026-09-15 Codex draft (verdict `READY_WITH_CHANGES`), the User
accepted that verdict, and Claude then produced the **Frozen UI
Implementation Blueprint** incorporating the review findings. Planning for
this initiative is now FROZEN; the draft plan/authority/mapping/checklist
files below are inputs the blueprint corrects and supersedes, not the
current instructions.

Canonical existing mailbox: [docs/governance/URI_AGENT_RELAY.md](docs/governance/URI_AGENT_RELAY.md). This root file is the requested discoverable UI handoff index, not a second authoritative milestone state. The existing M31 mailbox and active milestone remain unchanged.

## UI handoff checkpoint (current)

- **Status: FROZEN BLUEPRINT — implementation not started.** Authoritative
  document: [UI_HYBRID_FROZEN_BLUEPRINT.md](docs/plans/UI_HYBRID_FROZEN_BLUEPRINT.md).
  Do not start implementation from the superseded draft plan below.
- **Mandatory sequencing:** implementation may not begin until M31 — Model &
  Brain UX reaches Claude `VERIFIED` and is committed/pushed. See
  `docs/governance/URI_ACTIVE_MILESTONE.md` §1a and the blueprint's own
  sequencing section. M31's write scope covers nearly all of `uri_ui/lib`,
  the same surface every UI batch touches.
- **Roles for this initiative (2026-09-16, supersedes the 2026-09-15 line
  below):** Claude/Codex — planning and independent plan review only;
  Antigravity — primary implementer; Qwen 3 14B (local) — implementation
  review; Antigravity — repair of Qwen's findings. See `ORCHESTRATION.md` §0.
- Visual authority: the [published Hybrid Artifact](https://claude.ai/artifact/FtXLngXPXiRMCY9YQBefht)
  is **confirmed accessible** (Claude read it directly via the Artifact tool
  on 2026-09-16 — the 2026-09-15 "sign-in wall" applied only to unauthenticated
  browser/web-reader access, not to Claude's own Artifact tool). Its content
  (`Main.dc.html`, `MobileApp.dc.html`, `Palettes.dc.html`, `canvas.json`) is
  captured and reconciled in the blueprint and in the updated
  `docs/design_library/UI_DESIGN_AUTHORITY.md` / `COMPONENT_MAPPING.md`.
- Superseded inputs (pre-blueprint, kept for history):
  [UI_OVERHAUL_IMPLEMENTATION_PLAN.md](docs/plans/UI_OVERHAUL_IMPLEMENTATION_PLAN.md),
  [UI_DESIGN_AUTHORITY.md](docs/design_library/UI_DESIGN_AUTHORITY.md) (now
  updated in place, see its own revision note),
  [COMPONENT_MAPPING.md](docs/design_library/COMPONENT_MAPPING.md) (likewise
  updated in place),
  [UI_ACCEPTANCE_CHECKLIST.md](docs/design_library/UI_ACCEPTANCE_CHECKLIST.md).
- Explicit risks R1/R2 (failed task fetch appearing empty; composer draft
  disposal during navigation) remain required Batch 1 safeguards — carried
  into the blueprint unchanged, both independently source-verified by Claude.
- Next: Antigravity waits for M31 `VERIFIED`+committed, then begins Batch 1
  of the frozen blueprint. Do not start implementation from any
  pre-blueprint draft.
