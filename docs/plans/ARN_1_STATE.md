# ARN.1 — State: Deterministic Narrowing Core

**Status:** CLOSED / VERIFIED (Gemini independent final audit per direct User instruction)  
**Plan:** `docs/plans/ARN_ADAPTIVE_RETRIEVAL_NARROWING_PLAN.md` (Batch ARN.1)  
**Depends on:** M33.2 CLOSED/VERIFIED (`eb8116b`). Reuses M33.2 qualification verdicts and canonical interaction loop.

## History log

- **2026-09-20 — PLAN ACCEPTED (Claude):** ARN parent plan accepted at `eb8116b`.
- **2026-09-20 — IMPLEMENTING (Antigravity → Codex):** User authorized starting implementation of ARN.1 (Deterministic Narrowing Core) only. Antigravity prepared task package and routed execution to Codex.
- **2026-09-20 — VERIFICATION_READY (Codex):** Deterministic contracts, narrowing engine, task-local Turn State attachment, and canonical `NOT_FOUND` recovery seam implemented. Focused ARN.1 suite passed 10/10; predecessor M33.2 regression passed 60/60; relevant dispatch/decision/Turn State/orchestrator recovery sweep passed 130/130 plus 13 subtests. Completion evidence: `docs/plans/ARN_1_COMPLETION_REPORT.md`. No commit or push performed.
- **2026-09-20 — CLOSED / VERIFIED (Gemini):** Gemini performed independent final audit per direct User instruction. Verified NOT_FOUND recovery seam, evidence taxonomy, EDGE_DEDUCTION promotion guard, search-state tracking, no-loop behavior, clarification boundary (no question text), cost ceilings, Graphify independence, integration safety, and architectural purity (0 model calls). Reproductions: 10/10 focused ARN.1 passed; 60/60 M33.2 passed; 130 passed + 13 subtests passed on core suite. Full regression suite run: 2,259 passed, 16 failed (10 historical baseline, 6 Ollama environment-specific), zero ARN.1 regressions. Verdict: ACCEPT. ARN milestone paused after ARN.1. Next authorized direction: Resume M31 Hybrid UI after ARN.1 closure.

## Authorized Scope (Batch ARN.1 Only)

1. `ARNState` (§4) tracking:
   - task_goal
   - sources_checked: [SourceRecord]
   - candidates: [Candidate]
   - eliminated: [(Candidate, reason)]
   - user_clues: [Clue]
   - clarification_asked: bool
   - successful_route: Optional[Route]
   - cost_spent: CostAccumulator
2. Explicit temporary candidate/search state distinction:
   - VERIFIED FACT
   - USER CLUE
   - EDGE DEDUCTION (never promoted to fact)
   - ELIMINATED CANDIDATE
   - SOURCE POINTER
   - UNRESOLVED QUESTION
3. `NOT_FOUND` as recovery trigger seam (hook only, not terminal failure; no new execution authority).
4. Repeated-search avoidance (never re-query an eliminated or already searched path in the same task).
5. Progressive narrowing and cost ceiling (§2.8) with genuine `EXHAUSTED` termination semantics.
6. Operates 100% without Graphify (`graphify-out/`).
7. No model calls in ARN.1; no Edge or small reasoner wired in ARN.1; no user-facing question authoring (URI only recommends when/what axis, never literal question text); no M31 UI; no cascading browser/human-interaction layers.
8. Focused tests: `test_arn_1_deterministic_narrowing.py`.
9. Stop condition: `VERIFICATION_READY`.

## Implementer Return Report

- **Milestone ID:** ARN.1
- **Implementer:** Codex
- **Summary of Actions:** Implemented pure task-scoped ARN contracts and evidence taxonomy, deterministic candidate/source/clue/cost handling, repeated-search prevention, genuine terminal states, structured clarification-axis recommendations without question wording, Turn State projection, and canonical execution recovery from a first `NOT_FOUND` result.
- **Files Modified/Created:** See `docs/plans/ARN_1_COMPLETION_REPORT.md`.
- **Tests Performed:** 10 focused ARN.1 tests; 60 predecessor M33.2 regression tests; 130 relevant dispatch/decision/Turn State/orchestrator recovery tests plus 13 subtests. All passed.
- **Assumptions & Decisions:** Reaching a configured maximum is treated as hitting the ceiling. Raw execution evidence remains `not_found`; only the containing envelope becomes `recovery_required`. ARN state remains caller-owned and is never durably persisted.
- **Known Issues / Gaps:** None within ARN.1 scope. Claude independent audit remains pending. ARN.2–ARN.5 remain explicitly deferred.
