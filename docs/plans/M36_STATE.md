# M36 State — URI-Memory Minimum (pre-Office demonstrator)

STATE: PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT
Plan: `docs/plans/M36_URI_MEMORY_MINIMUM_PLAN.md`
Component: `URI-Memory` (status unchanged: `NOT_STARTED`)
Starting HEAD: `291c9daa48435200c4b56857d0e3bc630016e82a` (`m35-uri-v1-parallel-architecture`, local = origin)
Implementation authorized: NO
Independent plan pre-audit (PG-M1): NOT STARTED
User implementation authorization (PG-M2): NOT GIVEN
INT-* event: NONE. S13: not authorized. S9: remains deferred.

## Decisions

| ID | Date | Decision | Source |
|---|---|---|---|
| D4-R1 | 2026-09-28 | History yes, learning no. Durable task/outcome/correction history may feed cross-session reference resolution as grounded candidates and factual recency. Learned preference or tie-break weights, frequency preference, and repetition-based promotion stay deferred (S9). Memory never binds. | Direct User answer in the M36 planning session |

## Gates

| Gate | Requirement | Status |
|---|---|---|
| PG-M1 | Independent pre-audit of the plan by another model/session | OPEN |
| PG-M2 | Explicit User implementation authorization | OPEN |
| Freeze | Plan §12 item 4 | OPEN |

## History log

| Date | Actor | Transition | Note |
|---|---|---|---|
| 2026-09-28 | Claude Code (Opus 5.5), Architect / Pre-Auditor | (none) → PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT | Recovered Memory evidence across `_V1 uri_core/`, `_V1 uri_v1/`, plans, governance, and untracked harness-strategy research; bounded external research (Graphiti, MCP memory server, Letta, Mem0); User decision D4-R1 recorded; plan self-reviewed against its own acceptance criteria (plan §0, §15). Not auto-approved to implementation: the User limited this session to planning, and L4 is high-risk, so an independent pre-audit is required first. |
