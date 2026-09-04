# Skill Router V1 — Architecture Audit

## Status
**Audit: MODIFY. Root-cause fix: APPLIED.** The required change identified in §7.1
(`SkillEvaluatorV1.evaluate_from_context_budget()` not annotating `_eval_score`) has been
implemented, targeted, and verified — see §7 and §11 for details. This document is kept
as the point-in-time audit record; the fix's application is recorded rather than the
original findings being rewritten.

## 1. Audit date
2026-09-04

## 2. Audit scope
Senior-level architecture review of the current Skill Router V1 implementation and its
immediate dependency, Skill Evaluator V1. Read-only inspection; no source files were
modified during the audit itself.

Reviewed:
- `skill_router_v1.py` (full read, 560 lines)
- `test_skill_router_v1.py` (structure, helper functions, coverage overview)
- `skill_evaluator_v1.py` (public API, scoring/annotation methods)
- `test_skill_evaluator_v1.py` (structure, coverage overview)
- `uri_core/core/context_budget.py` (output contract only, to verify the real
  `ContextBudget -> SkillEvaluator` interface)
- Confirmed via repository search: zero references to either module anywhere under
  `uri_core/`, i.e. no current orchestrator/runtime integration exists yet.

Not modified during the audit: any Skill Registry V1 data, ContextBudget V1
implementation, AuditTrail, or Evidence/Fact Integrity infrastructure.

## 3. Existing architecture reviewed
`SkillRouterV1` is a deterministic, side-effect-free decision layer consuming
`SkillEvaluatorV1` output and applying URI policy (eval-score floor, confidence floor,
URI-native vs. Hermes allow-list gating, deterministic tie-broken ordering) to produce one
of four routing states: `selected`, `ordered_candidates`, `clarification_required`,
`no_suitable_capability`. It never executes, authorizes, or contacts external systems.
`SkillEvaluatorV1` has two entry points: `evaluate()` (direct registry scoring) and
`evaluate_from_context_budget()` (consumes real `ContextBudget.build_context()` output).
Both files currently live at the repository root, standalone and unintegrated with
`uri_core/`.

## 4. Strengths
- The router's own decision logic is genuinely deterministic: no I/O, no randomness, a
  fixed sequential policy-check order, and a stable sort with explicit tie-breaking.
- Clean single-entrypoint public API (`route()`), explicit `ValueError`s on invalid
  construction, and a well-structured, auditable return schema (`policy_applied`,
  `decisions`, `rejected`, `context_used`).
- Correctly keeps `execution_risk` out of routing policy by design (risk belongs to a
  future authorization layer, not routing) — verified by a dedicated test
  (`test_high_risk_item_not_auto_rejected_by_router`).
- Genuinely side-effect-free, proven by its own test class
  (`TestSkillRouterV1SideEffectFreedom`).
- 62/62 pre-existing unit tests (38 router + 24 evaluator) passed on a fresh run,
  confirming solid coverage of each module's own internal logic in isolation.

## 5. Weaknesses
- **`SkillEvaluatorV1.evaluate_from_context_budget()` does not annotate `_eval_score`**
  onto its returned candidates (`skill_evaluator_v1.py:90-135`), unlike `evaluate()` /
  `_rank_candidates()`, which does this correctly. This is the documented *primary*
  pipeline (`ContextBudget -> SkillEvaluator -> SkillRouter`, per the router's own module
  docstring), and it silently breaks the router's policy gate for every candidate that
  travels through it.
- `SkillEvaluatorV1._build_routing_recommendation` independently produces its own
  `destination: "uri_runtime"|"hermes"|"none"` decision based on category alone, with no
  Hermes allow-list check and no confidence/score threshold — a second, weaker routing
  authority that overlaps with the Router's actual policy gate.
- A misspelled, entirely unused constant, `HERTES_FACING_CATEGORIES`
  (`skill_router_v1.py:52`), is defined but never referenced — dead code, cosmetic.
- Both files live at repository root rather than under `uri_core/core/`, inconsistent
  with every other piece of runtime-control infrastructure in this codebase.

## 6. Architectural risks
- **No end-to-end integration test exists** between the real `ContextBudget`, the real
  `SkillEvaluatorV1.evaluate_from_context_budget()`, and `SkillRouterV1.route()`. The
  existing `TestSkillRouterV1ContextBudgetPresence` tests use a synthetic
  `context_budget_output` dict and a fake evaluator-result helper — they check a presence
  *flag*, not the real pipeline. This is exactly why the `_eval_score` gap went
  undetected despite 62/62 tests passing — the two modules are well-tested in isolation
  but their actual designed integration was never exercised.
- The failure mode of the `_eval_score` gap is fail-safe-but-wrong (over-rejection: a
  missing score defaults to `0.0`, which is below the default floor), not an
  authorization bypass — worth being precise about rather than overstating it as a
  security hole. Still, it means the documented primary pipeline is currently
  non-functional in practice.
- The Evaluator's own `routing_recommendation` field is a latent trap for a future
  integrator who might reasonably assume it reflects real, allow-list-checked policy —
  it does not.

## 7. Required changes
1. **✅ APPLIED (Claude, on explicit instruction).** Fixed
   `SkillEvaluatorV1.evaluate_from_context_budget()` (`skill_evaluator_v1.py`) to
   annotate `_eval_score` on every returned candidate via
   `dict(item, _eval_score=score)`, matching `_rank_candidates()`'s existing pattern for
   `evaluate()` exactly. Scoring, thresholds, routing, URI-native classification,
   allow-list behavior, authorization, and execution were not touched — only the missing
   annotation was added. Originally identified as Hermes-owned; the fix was applied
   directly by Claude once explicitly authorized, rather than left pending.
2. **✅ Applied in the prior checkpoint.** Defensive check in `SkillRouterV1`
   distinguishing "no `_eval_score` annotation at all" from "explicitly scored `0.0`,"
   surfaced per-candidate (`eval_score_missing`) and as a routing-level summary
   (`eval_score_missing_count`), with a distinct explain reason naming the contract gap.
   Kept in place after the root-cause fix landed — it remains valid defense-in-depth for
   any future evaluator-side regression or a different, not-yet-written evaluator
   implementation.
3. **✅ Applied and updated.** The real end-to-end integration test
   (`test_skill_router_v1_eval_score_contract.py::RealEvaluatorToRouterIntegrationTests`)
   originally characterized the bug; it now proves the fix instead — `_eval_score`
   survives, the router receives the real (non-zero) score, a valid candidate is no
   longer treated as an implicit `0`, all other candidate fields are preserved
   unchanged, and the pipeline's routing decision is identical across repeated runs with
   identical inputs.

## 8. Deferred improvements
- Fixing the misspelled/dead `HERTES_FACING_CATEGORIES` constant — cosmetic, zero
  behavioral impact, not required for correctness.
- Reconciling `SkillEvaluatorV1.routing_recommendation` against the Router's authoritative
  decision (deprecate, rename, or clearly document as advisory-only) — a contract
  question for whoever does the eventual orchestrator integration; not urgent since
  nothing consumes it today.
- Relocating both modules under `uri_core/core/` — a packaging/consistency concern, not
  a correctness one.

## 9. Recommendation
**MODIFY.** The Router's own internal policy engine is sound and does not need
functional changes beyond the defensive addition above. The required fix lives in
`skill_evaluator_v1.py` (Hermes-owned) — the system as a whole cannot be trusted as
runtime-authoritative for the ContextBudget-integrated path until that lands.

## 10. Integration guidance
The `_eval_score` blocker for orchestrator integration is now resolved and verified (see
§11). Before wiring `SkillRouterV1`/`SkillEvaluatorV1` into the orchestrator, still treat
`SkillRouterV1.route()` as the sole routing authority; `SkillEvaluatorV1`'s own
`routing_recommendation` field should not be used to make routing or Hermes-approval
decisions (§8's deferred item — that overlap was not resolved by this fix and remains an
open question for whoever does the integration).

## 11. Test assessment
Before the audit: 62/62 passing (38 router + 24 evaluator), but with a real
integration-coverage gap (§6) that let the `_eval_score` bug go undetected.
After the audit note but before the fix: 71/71 passing (62 pre-existing, unmodified + 9
new, characterizing the gap end-to-end via the real pipeline).
**After the fix:** 73/73 passing (24 evaluator + 38 router, both still unmodified in
their own pre-existing test files + 11 in the new file, now proving — not just
characterizing — that `_eval_score` survives the real pipeline, that the router receives
it correctly, that no other candidate field was altered, and that routing is
deterministic across repeated runs).

## 12. Unresolved decisions
- Whether `SkillEvaluatorV1.routing_recommendation` should be removed, renamed, or
  simply documented as non-authoritative once integration work begins.
- Whether `skill_router_v1.py`/`skill_evaluator_v1.py` should eventually move under
  `uri_core/core/` alongside the rest of the runtime infrastructure.
- Whether the `eval_score_missing_count` signal added in this checkpoint should
  eventually become a hard error (reject the whole batch) rather than a per-candidate
  diagnostic, once there are real callers depending on it.

## 13. Ownership: Hermes vs. Claude
- **Originally identified as Hermes-owned, applied by Claude on explicit authorization:**
  the `_eval_score` annotation fix in
  `skill_evaluator_v1.py::evaluate_from_context_budget()`. The change was scoped
  narrowly (only the missing annotation) per explicit instruction, rather than left
  pending for Hermes.
- **Hermes-owned, still deferred:** the `HERTES_FACING_CATEGORIES` typo/dead-code
  cleanup (their file); the `routing_recommendation` overlap resolution.
- **Claude-owned, implemented:** the defensive missing-vs-zero distinction in
  `skill_router_v1.py`; the real-pipeline integration test (both the original
  bug-characterizing version and its update to a fix-proving version).
- **Unowned / future decision:** module relocation under `uri_core/core/`; orchestrator
  integration itself.
