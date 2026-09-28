# M36 State — URI-Memory Minimum (pre-Office demonstrator)

STATE: PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT
READINESS: M36_READY_FOR_INDEPENDENT_PG_M1_PREAUDIT (plan amendment A1, 2026-09-28)
Plan: `docs/plans/M36_URI_MEMORY_MINIMUM_PLAN.md` (sections 0–15 as drafted; section 16 = amendment A1)
Component: `URI-Memory` (status unchanged: `NOT_STARTED`)
Starting HEAD: `291c9daa48435200c4b56857d0e3bc630016e82a` (`m35-uri-v1-parallel-architecture`, local = origin)
Plan commit: `1f3ec48`
Implementation authorized: NO
Independent plan pre-audit (PG-M1): NOT STARTED (ready; brief in plan §16.5)
User implementation authorization (PG-M2): NOT GIVEN
INT-* event: NONE. S13: not authorized. S9: remains deferred.

## Decisions

| ID | Date | Decision | Source |
|---|---|---|---|
| D4-R1 | 2026-09-28 | History yes, learning no. Durable task/outcome/correction history may feed cross-session reference resolution as grounded candidates and factual recency. Learned preference or tie-break weights, frequency preference, and repetition-based promotion stay deferred (S9). Memory never binds. | Direct User answer in the M36 planning session |
| D-A (OD-1), OD-2, OD-3, OD-4, OD-5, VG-1, LF-1 | 2026-09-28 | External execution harness rulings, Brain provider/transport neutrality, workspace and permission defaults, harness contract placement, viability gate, local-first principle. Full text in `docs/governance/URI_STATE.yaml` → `architecture_decisions` and `docs/plans/PAPERCLIP_URI_ARCHITECTURE_RECONNAISSANCE.md` §24. No structural change to M36 (plan §16.1). | Direct User instruction, 2026-09-28 |
| M36-A1-H1 | 2026-09-28 | `harness_run_ref` DEFERRED with name and constraints reserved (plan §16.2): lineage-only, non-authoritative, loss-tolerant, never retrievable content; to be added only in a later schema version with a v1 reader. PG-M1 may instead accept the stated in-M36 fallback. | Claude Code (Architect), within the User's instruction to avoid unnecessary M36 expansion; subject to PG-M1 |

## Gates

| Gate | Requirement | Status |
|---|---|---|
| PG-M1 | Independent pre-audit of the plan by another model/session (12 determinations, plan §16.5) | OPEN — ready |
| PG-M2 | Explicit User implementation authorization | OPEN |
| Freeze | Plan §12 item 4 | OPEN |

## History log

| Date | Actor | Transition | Note |
|---|---|---|---|
| 2026-09-28 | Claude Code (Opus 5.5), Architect / Pre-Auditor | (none) → PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT | Recovered Memory evidence across `_V1 uri_core/`, `_V1 uri_v1/`, plans, governance, and untracked harness-strategy research; bounded external research (Graphiti, MCP memory server, Letta, Mem0); User decision D4-R1 recorded; plan self-reviewed against its own acceptance criteria (plan §0, §15). Not auto-approved to implementation: the User limited this session to planning, and L4 is high-risk, so an independent pre-audit is required first. |
| 2026-09-28 | Claude Code (Opus 5.5), Architect | PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT (unchanged); readiness marker added | Amendment A1 (plan §16): recorded the effect on M36 of the User's harness rulings (D-A/OD-1…OD-5, VG-1, LF-1) after the Paperclip reconnaissance. No structural change. `harness_run_ref` deferred and reserved. Exit criterion E-6 added (already met by the §7.8 design). Edge-planning implications recorded. PG-M1 audit brief written. PG-M1 itself not performed (author is not independent). |
