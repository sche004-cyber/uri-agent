# URI Development Control Layer Normalization — Phase 1 Inventory

**Status:** Evidence-backed inventory supporting `URI_STATE.yaml`. Bounded governance-engineering task. No implementation, no rewrite of accepted historical artifacts.
**Date:** 2026-09-25
**Repository state inspected:** worktree `C:\Users\cheta\Development\Uri\_V1`, branch `m35-uri-v1-parallel-architecture`, HEAD `47af60a65946e83b5fa10132b8363adfd18aca31`, remote `origin` = `https://github.com/sche004-cyber/uri-agent.git`.

Every row below was checked directly against a primary artifact (commit, file, `git worktree list`) — none is inferred from naming alone.

---

## 1. Current branch / HEAD / remote

- Branch: `m35-uri-v1-parallel-architecture`.
- HEAD == accepted architecture-plan commit `47af60a` ("docs(plans): freeze M35 URIv1 A3 architecture synthesis - M33.3 identity accepted"). Verified via `git rev-parse HEAD`.
- `git worktree list`:
  - `C:/Users/cheta/Development/uri-agent` @ `e8e3b65` (`master`) — this is `PROTECTED_LEGACY_URI_AGENT`, per `URI_DEVELOPMENT_EVIDENCE_REGISTRY.md` §0, and is the same repository/remote as this worktree, not a separate project.
  - `C:/Users/cheta/Development/Uri/_V1` @ `47af60a` (`m35-uri-v1-parallel-architecture`) — this worktree, `CURRENT_V1_URI_CORE`.
  - `C:/Users/cheta/Development/uri-agent/.tmp_m33_1_batch4_baseline_5973f6d` @ `5973f6d` (detached) — a preserved baseline snapshot, not an active line of work.

## 2. Current milestones (governed `Mxx`)

| ID | Title | Status | Evidence |
|---|---|---|---|
| M33.2 | Edge / Second Brain Foundation | **CLOSED / VERIFIED** (final closure 2026-09-20) | `URI_ACTIVE_MILESTONE.md` §1 "M33.2 — Edge / Second Brain Foundation — FINAL CLOSURE" |
| M33.3 | **Edge Intelligence Qualification & Integration** (current accepted identity) | Planning basis frozen; implementation NOT STARTED | Commit `47af60a`: "Freezes `docs/plans/M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md` as the planning basis for M33.3 - Edge Intelligence Qualification & Integration." Terminal audit state `ARCHITECTURE_PLAN_ACCEPTED_WITH_LIMITATIONS`. |
| M33.1 | Real Integrations / Acquire & Manage Abilities | **CLOSED / ACCEPTED** (2026-09-20) | `URI_ACTIVE_MILESTONE.md` §1 "M33.1 Batch 4 final independent closure review" |
| M31 | Model & Brain UX | **CLOSED / CLAUDE VERIFIED — COMPLETE**, released | `URI_ACTIVE_MILESTONE.md` §1, §6d |
| M32 | Brain Latency / Core Execution Architecture | **CLOSED / CLAUDE VERIFIED — COMPLETE** (2026-09-18) | `URI_ACTIVE_MILESTONE.md` §1, §6f |
| M32.1 | Execution Continuation Residual Hardening | Reservation only — **NOT STARTED** | `URI_ACTIVE_MILESTONE.md` §1c |
| M34 | Model-Native Capability Preservation & Adaptive Scaffolding | **CLOSED / CLAUDE VERIFIED — COMPLETE** (2026-09-19) | `URI_ACTIVE_MILESTONE.md` §1, §6g |
| M35 | URI Companion Experience (governed product milestone, presentation-only) | Reservation only — **NOT STARTED** | `URI_ACTIVE_MILESTONE.md` §1c. Distinct namespace collision risk with the *research line* also labeled "M35 URIv1" below — see §7. |
| ARN.1 | Deterministic Narrowing Core | **CLOSED / VERIFIED** (2026-09-20); ARN milestone **PAUSED** after ARN.1, ARN.2 NOT authorized | `URI_AGENT_RELAY.md` "PREVIOUS HANDOFF (CLOSED: ARN.1 ...)" |
| Hybrid UI ("Compact Chat Mode") | Queued initiative, not milestone-numbered | **FROZEN BLUEPRINT**, still paused, not accepted, not closed | `URI_ACTIVE_MILESTONE.md` §1a |

## 3. Closed milestones (superseded numbering / historical)

M30, M30-PFC, M30.7B/C, M30.8, M30.4/5/5A-D — all CLOSED, see `URI_ACTIVE_MILESTONE.md` §1 and §5a/§6a/§6b for approval/closure records. Not re-litigated here; preserved as-is.

## 4. Active continuation

**None currently authorized to implement.** M33.3's planning basis is frozen (`47af60a`) but implementation has not been authorized to begin in this repository state. `LOOP_STATE` in `URI_ACTIVE_MILESTONE.md` §1 (last recorded, 2026-09-19) reads `IDLE`; this has not been contradicted by any later entry inspected.

## 5. Research lines (`M35 URIv1 A0–A9`)

- **Status: CLOSED experimental research line.** `URI_AGENT_RELAY.md` "CURRENT HANDOFF" records A2.8L-A9 as `CLOSED / ACCEPT_WITH_DOCUMENTED_LIMITATIONS`, and states explicitly: "A9 is frozen: no further A9 mechanism repair, factorial expansion, or causal experimentation is authorized by this closure."
- A2.9 (native problem-solving trace pilot) — `CLOSED / ACCEPTED AS PILOT`, commit `9e5d5e2`.
- A2.8K (Level-5 evidence sufficiency qualification) — `CLOSED / ACCEPTED`, commit `2351048`.
- A2.8J (RAR-SAFE evidence-safety hardening) — `COMPLETE`, bounded re-audit `ACCEPTED`, commit `247265f`.
- This entire `M35 URIv1 A*` research line lives in `uri_v1/` (git-tracked but zero-imported by `uri_core/`, per `URI_DEVELOPMENT_EVIDENCE_REGISTRY.md` §0). It produced evidence — RAR/ARN mechanism qualification, Needle/Qwen/LFM classifications — that the frozen M33.3 architecture synthesis (`47af60a`) explicitly draws on, but the research line does not itself own or grant production architecture authority. This is the exact ambiguity Phase 2's namespace separation (`EXP-*` vs `Mxx`) is designed to remove going forward.

## 6. Architecture ownership

- **M33.2** is the accepted owner of URI's sole Edge / Second-Brain architectural foundation, confirmed by `URI_ACTIVE_MILESTONE.md` §1c M35 entry: "M33.2 owns URI's sole Edge / Second-Brain intelligence architecture... M35 must not create, rename, or retain a competing Mini-AI architecture."
- **M33.3**'s frozen planning basis (`M35_URIV1_A3_ARCHITECTURE_SYNTHESIS_AND_NEXT_BATCH_PLAN.md`) is the next authorized continuation of that same lineage ("Edge Intelligence Qualification & Integration"), not a competing architecture.
- **M35 (product milestone, Companion Experience)** is explicitly presentation-only and consumes M33.2's contracts; it does not own a model or intelligence architecture (`URI_ACTIVE_MILESTONE.md` §1c).
- **`uri_v1/`** (the new parallel architecture housing the research line above) is zero-imported by `uri_core/` in either direction (independently re-verified by grep per the Evidence Registry audit) — it has produced evidence, not yet production architecture.

## 7. Reusable components

**No formal reusable-component identity (`URI-RAR`, `URI-Memory`, `URI-Edge`, `URI-Eval`, `URI-Agent-Adapters`, or any other) exists anywhere in the repository today** — confirmed by a repository-wide grep for these exact strings and for the `EXP-*`/`INT-*` prefixes, zero matches. This normalization introduces these identities net-new; it does not rename or reconcile any existing component naming, because none currently exists at this granularity. Candidate mappings for a future batch to formally adopt (not binding by this normalization alone):
- **URI-RAR**: the RAR (Retrieval-Augmented Resolution?) mechanism under `uri_v1/turn/rar_deterministic.py`, `rar_contracts.py`, subject of the A2.8x research line.
- **URI-Edge**: `uri_core/core/edge/` (zero-egress, provider-agnostic Edge/Second-Brain core) plus the sibling `uri_core/core/edge_lifecycle/` (user-space model/runtime lifecycle, M33.2 Batch B.3).
- **URI-Memory**: explicitly named in the task brief as a **future separate reusable-subsystem track** — not yet started, no existing code claims this identity.
- **URI-Eval / URI-Agent-Adapters**: no existing single-module candidate identified in this inventory pass; left unassigned.

## 8. Integration status (`INT-*`)

**No `INT-*` authorized integration event exists.** Nothing in the repository has transitioned research/qualification evidence into a formally authorized production-integration event under this namespace, because the namespace did not exist before this normalization. M33.1's real integrations (Gmail OAuth, pinned `yt-dlp`, `strip-json-comments-cli`, `remember_fact`) are production capabilities already live under the existing Connected Service / Capability lifecycle — they are not examples of research-to-production integration in the RAR/Edge sense this task's `INT-*` namespace targets, and are not renamed by this normalization.

## 9. Aliases / naming collisions found

1. **M33.3 identity change, not yet reconciled in `URI_ACTIVE_MILESTONE.md`.** §1c (recorded 2026-09-18) still reads "M33.3 is reserved for **Unified URI Interaction & Capability UI**." Commit `47af60a` (2026-09-25) superseded this: M33.3's accepted identity is now **Edge Intelligence Qualification & Integration**. This is exactly the "stale current-state wording" the task brief flagged. **Not rewritten by this normalization** (per the task's own instruction not to rewrite accepted historical artifacts to make naming cleaner) — instead, `URI_ACTIVE_MILESTONE.md` receives one additive correction note (preserving the original text, per this file's own auditable-correction-history convention) pointing to `URI_STATE.yaml` as the canonical current-identity source, and `URI_STATE.yaml` itself records the corrected identity.
2. **"M35" is overloaded across two unrelated namespaces**: (a) the *research line* `M35 URIv1 A0-A9` / `A2.8x` / `A2.9` (an `EXP-*`-shaped body of work that happens to have been labeled with the `M35` prefix historically), and (b) the *governed product milestone* `M35 — URI Companion Experience` (a real `Mxx` reservation, NOT STARTED). These are already distinguished in prose in `URI_ACTIVE_MILESTONE.md` §1c ("M35 URIv1... Companion Experience remains separate/NOT STARTED") and in commit `47af60a`'s message, but nothing machine-readable previously separated them. `URI_STATE.yaml` records them as two distinct entries to remove this ambiguity going forward; existing `M35_URIV1_*` document filenames are **not renamed** by this normalization (history preserved).
3. **M32 was renumbered to M33 for "External Capability Bridge"** (`URI_ACTIVE_MILESTONE.md` §1b, "renumbered from M32, 2026-09-18") while a *different* M32 ("Brain Latency / Core Execution Architecture") was simultaneously in flight and later closed under the original M32 number. This is already disclosed and reconciled in `URI_ACTIVE_MILESTONE.md` itself (roadmap-reconciliation bullets under the M31/M32 Critical Invariants) — recorded here for completeness, no further action needed.
4. **"Compact Chat Mode" vs "Companion Mode"** — already disambiguated at the governance level in `URI_ACTIVE_MILESTONE.md` §1a (2026-09-18 naming-disambiguation note). No outstanding collision.

## 10. Stale current-state references

- `URI_ACTIVE_MILESTONE.md` §1c, M33.3 entry — stale, see §9 item 1 above.
- No other stale current-state contradiction was found in `URI_ACTIVE_MILESTONE.md`, `URI_AGENT_RELAY.md`, or `URI_DEVELOPMENT_EVIDENCE_REGISTRY.md` during this inventory pass; all other entries checked are internally consistent with commit `47af60a` and with each other.

## 11. Legacy URI location

`C:\Users\cheta\Development\uri-agent` — same repository/remote as this worktree (confirmed via `git worktree list` and `git remote -v` in both), branch `master`, currently at `e8e3b65`. Formally recorded as `PROTECTED_LEGACY_URI_AGENT`, read-only by governance, in `URI_DEVELOPMENT_EVIDENCE_REGISTRY.md` §0. Not a separate historical URI generation with different code — it is the same tracked `uri_core/` at a different (older) commit, plus uncommitted local edits specific to that worktree.

---

**Not rewritten, not renamed, not reopened by this inventory:** any accepted historical plan, state, completion-report, or relay entry. This document and `URI_STATE.yaml` are additive governance artifacts only.
