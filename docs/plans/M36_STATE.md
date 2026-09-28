# M36 State — URI-Memory Minimum (pre-Office demonstrator)

STATE: PLAN_A2_REPAIRED_AWAITING_PG_M1_FOCUSED_RECHECK
READINESS: M36_A2_READY_FOR_PG_M1_FOCUSED_RECHECK (plan amendment A2, 2026-09-28)
Plan: docs/plans/M36_URI_MEMORY_MINIMUM_PLAN.md (§17 = controlling A2 repairs; §0–§16 preserved with explicit supersession notices)
Component: `URI-Memory` (status unchanged: `NOT_STARTED`)
Starting HEAD: `291c9daa48435200c4b56857d0e3bc630016e82a` (`m35-uri-v1-parallel-architecture`, local = origin)
Plan commit: `1f3ec48`
Implementation authorized: NO
Independent plan pre-audit (PG-M1): PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS — not fully accepted; focused re-check pending
Audit report: docs/plans/M36_PG_M1_INDEPENDENT_PREAUDIT_REPORT.md (unchanged)
Required findings: F-1 through F-11; plan §17.1–§17.11, qualification mapping §17.12
Amendment A2: REPAIRED_AWAITING_FOCUSED_RECHECK (Codex bounded documentation repair; no independent acceptance claim)
Planning/governance repair baseline: e26d98c5b6827946c3e546663758a94bf1be7033
User implementation authorization (PG-M2): NOT GIVEN — BLOCKED_PENDING_PG_M1_FOCUSED_RECHECK; do not request/start
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
| PG-M1 | Independent pre-audit, then focused A2 re-check of F-1…F-11 (plan §17.14 prompt) | PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS; A2 ready, focused re-check pending; not fully accepted |
| PG-M2 | Explicit User implementation authorization after PG-M1 repairs independently pass | BLOCKED_PENDING_PG_M1_FOCUSED_RECHECK; authorization not given |
| Freeze | Plan §12 item 4 | OPEN |

## History log

| Date | Actor | Transition | Note |
|---|---|---|---|
| 2026-09-28 | Claude Code (Opus 5.5), Architect / Pre-Auditor | (none) → PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT | Recovered Memory evidence across `_V1 uri_core/`, `_V1 uri_v1/`, plans, governance, and untracked harness-strategy research; bounded external research (Graphiti, MCP memory server, Letta, Mem0); User decision D4-R1 recorded; plan self-reviewed against its own acceptance criteria (plan §0, §15). Not auto-approved to implementation: the User limited this session to planning, and L4 is high-risk, so an independent pre-audit is required first. |
| 2026-09-28 | Claude Code (Opus 5.5), Architect | PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT (unchanged); readiness marker added | Amendment A1 (plan §16): recorded the effect on M36 of the User's harness rulings (D-A/OD-1…OD-5, VG-1, LF-1) after the Paperclip reconnaissance. No structural change. `harness_run_ref` deferred and reserved. Exit criterion E-6 added (already met by the §7.8 design). Edge-planning implications recorded. PG-M1 audit brief written. PG-M1 itself not performed (author is not independent). |
| 2026-09-28 | Claude Code (Opus 5.5), fresh independent session | PG_M1_ACCEPTED_WITH_BOUNDED_REPAIRS | Report above finds eleven required planning defects F-1…F-11 / R-1…R-11. No implementation authority. harness_run_ref deferral accepted. |
| 2026-09-28 | Codex, User-authorized bounded planning-repair implementer | PLAN_DRAFTED_AWAITING_INDEPENDENT_PREAUDIT → PLAN_A2_REPAIRED_AWAITING_PG_M1_FOCUSED_RECHECK | Additive A2 (§17) repairs F-1…F-11, marks conflicting draft text historical/superseded, adds Q-A2-1…Q-A2-11 and performs focused self-review only. Memory boundary unchanged; PG-M2 remains blocked. Prior A1 claim “E-6 already met” is historical: conditional on future OD-3 representation, not independently demonstrated. Edge sufficiency unverified until an Edge plan exists. |

## A2 handoff

- Exact repair interpretation, normative specification and qualification mapping: plan §17.
- harness_run_ref: DEFERRED under unchanged §16.2 reserved constraints; no fake harness fixtures.
- Open: independent focused PG-M1 re-check; future implementation/qualification/live evidence; advisory F-12…F-18 and disclosed Edge/Harness sufficiency limitations. F-19 overstatements are marked historical, not independently re-audited.
- Recommended focused re-check prompt: plan §17.14. Stop at M36_A2_READY_FOR_PG_M1_FOCUSED_RECHECK; no PG-M2 request.

## A2 planning validation — 2026-09-28

| Check | Observed result |
|---|---|
| Governance validator | VALID; no DCL violations |
| Existing governance and selected frozen regression suites | 83 passed (37 governance plus 46 S1 governance/parity, S7 events, S11 versions and closing-audit tests) |
| Frozen hash checker | ok=True; changed=[]; 8 S4 and 24 LF anchors |
| Frozen scope diff | No tracked uri_v1/uri_core code, tests, scripts or fixtures differ from 291c9daa48435200c4b56857d0e3bc630016e82a |
| A2 structure/state consistency | 11 repair sections and 11 qualification rows present; state/status/gates consistent; non-M36 governance unchanged |
| A2-scoped git diff --check | Clean for the five modified planning/governance/handoff files |
| Repository-wide git diff --check | Existing SKILL.md trailing whitespace at lines 581/582 only; file preserved untouched |
| Dirty-worktree preservation | All 220 pre-existing dirty/untracked individual files retain their baseline hashes, including the independent audit report; only the five authorized documentation files modified |

No Memory implementation tests, new test files, full architecture audit or live Memory acceptance are claimed. The independent report is retained unchanged as M36 audit evidence alongside the bounded documentation commit; unrelated research is excluded. Commit identity is reported by the repairer after creation.
