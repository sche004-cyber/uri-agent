"""
Focused tests added by the Skill Router V1 architecture audit
(SKILL_ROUTER_V1_ARCHITECTURE_AUDIT.md).

Covers two things, deliberately kept in one file since they're the
same underlying contract issue:

1. SkillRouterV1's own defensive distinction between "the Skill
   Evaluator explicitly scored this candidate 0.0" and "the Skill
   Evaluator never annotated an _eval_score at all" - a Claude-side,
   Router-only change (skill_router_v1.py).

2. A real, end-to-end integration test:
   ContextBudget -> SkillEvaluatorV1.evaluate_from_context_budget()
   -> SkillRouterV1.route()
   using the real evaluator, not a synthetic fake result - the
   coverage gap the audit identified as the reason the underlying
   bug (SkillEvaluatorV1.evaluate_from_context_budget() not
   annotating _eval_score) went undetected despite 62/62 existing
   unit tests passing.

Does not modify skill_evaluator_v1.py or test_skill_router_v1.py.
"""

import unittest

from skill_router_v1 import SkillRouterV1


def _eval_result(candidates, user_request="do something"):
    """Minimal synthetic evaluator-result shape, isolated from
    SkillEvaluatorV1, for testing SkillRouterV1's own defensive
    behavior in isolation."""
    return {
        "evaluated_at": "2026-01-01T00:00:00+00:00",
        "request": {
            "user_request": user_request,
            "signal_word_count": 1,
            "intent_present": True,
        },
        "candidates": candidates,
        "best_match": candidates[0] if candidates else None,
        "routing_recommendation": {},
        "classification_summary": {},
        "has_suitable_capability": bool(candidates),
        "capability_gap": not bool(candidates),
    }


class DefensiveMissingEvalScoreTests(unittest.TestCase):
    """
    SkillRouterV1-only behavior: distinguishing a missing
    _eval_score annotation from an explicit 0.0.
    """

    def _candidate(self, name, **overrides):
        base = {
            "name": name,
            "normalized_name": name.lower(),
            "source": "uri_tool",
            "category": "uri_core_capability",
            "purpose": "",
            "execution_risk": "controlled",
            "model_facing": True,
            "runtime_facing": True,
            "invocation_conditions": [],
            "integration_status": "integrated",
            "hermes_should_handle": False,
            "_eval_score": 40.0,
        }
        base.update(overrides)
        return base

    def test_candidate_without_eval_score_key_is_flagged_missing(self):

        candidate = self._candidate("draft_note")
        del candidate["_eval_score"]

        router = SkillRouterV1()

        result = router.route(_eval_result([candidate]))

        self.assertEqual(result["eval_score_missing_count"], 1)
        self.assertTrue(result["decisions"][0]["eval_score_missing"])

    def test_candidate_with_explicit_zero_is_not_flagged_missing(self):

        candidate = self._candidate("draft_note", _eval_score=0.0)

        router = SkillRouterV1()

        result = router.route(_eval_result([candidate]))

        self.assertEqual(result["eval_score_missing_count"], 0)
        self.assertFalse(result["decisions"][0]["eval_score_missing"])

    def test_missing_and_explicit_zero_both_still_rejected(self):
        """
        The defensive flag changes what's reported, not the
        accept/reject policy outcome itself - both are below the
        default eval-score floor either way.
        """

        missing = self._candidate("missing_one")
        del missing["_eval_score"]

        explicit_zero = self._candidate(
            "explicit_zero_one", _eval_score=0.0
        )

        router = SkillRouterV1()

        result = router.route(
            _eval_result([missing, explicit_zero])
        )

        self.assertEqual(result["routing_state"], "clarification_required")
        self.assertTrue(all(not d["accepted"] for d in result["decisions"]))

    def test_missing_eval_score_reason_names_the_contract_gap(self):

        candidate = self._candidate("draft_note")
        del candidate["_eval_score"]

        router = SkillRouterV1()

        result = router.route(_eval_result([candidate]))

        reason = result["decisions"][0]["reason"]

        self.assertIn("no _eval_score annotation", reason)
        self.assertIn("upstream evaluator contract gap", reason)

    def test_explicit_zero_reason_uses_original_wording(self):
        """
        Backward compatibility: the pre-existing reason text for a
        genuinely low/zero explicit score is unchanged.
        """

        candidate = self._candidate("draft_note", _eval_score=0.0)

        router = SkillRouterV1()

        result = router.route(_eval_result([candidate]))

        reason = result["decisions"][0]["reason"]

        self.assertIn("eval score 0.0 below min_eval_score", reason)

    def test_no_candidates_reports_zero_missing_count(self):

        router = SkillRouterV1()

        result = router.route(_eval_result([]))

        self.assertEqual(result["eval_score_missing_count"], 0)

    def test_invalid_evaluator_result_reports_zero_missing_count(self):

        router = SkillRouterV1()

        result = router.route("not-a-dict")

        self.assertEqual(result["eval_score_missing_count"], 0)


class RealEvaluatorToRouterIntegrationTests(unittest.TestCase):
    """
    End-to-end regression test using the REAL SkillEvaluatorV1 and
    real ContextBudget output - not a synthetic fake evaluator
    result. This is the coverage the audit found missing.
    """

    def _registry(self):
        return [
            {
                "name": "draft_institutional_note",
                "normalized_name": "draft_institutional_note",
                "source": "uri_tool",
                "category": "uri_core_capability",
                "purpose": "draft an administrative noting document",
                "execution_risk": "controlled",
                "model_facing": True,
                "runtime_facing": True,
                "invocation_conditions": [],
                "integration_status": "integrated",
                "hermes_should_handle": False,
            },
            {
                "name": "pdf-reader",
                "normalized_name": "pdf-reader",
                "source": "hermes_builtin_skill",
                "category": "on_demand_skill",
                "purpose": "read and extract text from PDF files",
                "execution_risk": "variable",
                "model_facing": True,
                "runtime_facing": False,
                "invocation_conditions": [],
                "integration_status": "not_applicable",
                "hermes_should_handle": False,
            },
        ]

    def _run_real_pipeline(self):
        """Runs the real ContextBudget -> evaluate_from_context_budget
        -> SkillRouterV1.route() pipeline once, with no synthetic
        evaluator_result anywhere in the path."""

        from uri_core.core.context_budget import ContextBudget
        from skill_evaluator_v1 import SkillEvaluatorV1

        budget = ContextBudget(
            registry_items=self._registry(),
            max_capabilities=10,
            max_tokens=5000,
        )

        budget_output = budget.build_context(
            "draft an office note",
            intent={
                "task_type": "document drafting",
                "requested_output": "office note",
            },
        )

        evaluator = SkillEvaluatorV1()

        evaluator_result = evaluator.evaluate_from_context_budget(
            "draft an office note",
            budget_output,
            intent={
                "task_type": "document drafting",
                "requested_output": "office note",
            },
        )

        router = SkillRouterV1(hermes_allowlist=["pdf-reader"])

        routing_decision = router.route(
            evaluator_result, user_request="draft an office note"
        )

        return evaluator_result, routing_decision

    def test_real_pipeline_preserves_eval_score_annotation(self):
        """
        Proves the root-cause fix: SkillEvaluatorV1.evaluate_from_
        context_budget() now annotates _eval_score on every returned
        candidate (matching evaluate()'s existing behavior), so the
        real ContextBudget -> evaluate_from_context_budget ->
        SkillRouterV1.route() pipeline no longer loses it.
        """

        evaluator_result, routing_decision = self._run_real_pipeline()

        self.assertGreater(len(evaluator_result["candidates"]), 0)

        # _eval_score survives on every candidate returned by the
        # evaluator, and is a real (non-placeholder-zero) number for
        # the relevant capability.
        for candidate in evaluator_result["candidates"]:
            self.assertIn("_eval_score", candidate)
            self.assertIsInstance(
                candidate["_eval_score"], (int, float)
            )

        top_candidate = evaluator_result["candidates"][0]
        self.assertEqual(top_candidate["name"], "draft_institutional_note")
        self.assertGreater(top_candidate["_eval_score"], 0.0)

        # The router receives the real score: nothing is flagged as
        # missing, and no valid candidate is treated as an implicit 0.
        self.assertEqual(routing_decision["eval_score_missing_count"], 0)

        self.assertTrue(
            all(
                not d["eval_score_missing"]
                for d in routing_decision["decisions"]
            )
        )

        matching_decision = next(
            d
            for d in routing_decision["decisions"]
            if d["name"] == "draft_institutional_note"
        )

        self.assertEqual(
            matching_decision["eval_score"], top_candidate["_eval_score"]
        )
        self.assertGreater(matching_decision["eval_score"], 0.0)

        # With a real, non-zero score, the relevant URI-native
        # candidate is actually routable now - not stuck in
        # clarification_required because of a lost annotation.
        self.assertIn(
            routing_decision["routing_state"],
            ("selected", "ordered_candidates"),
        )
        self.assertEqual(
            routing_decision["selected"]["name"],
            "draft_institutional_note",
        )

    def test_real_pipeline_preserves_all_other_candidate_fields(self):
        """
        The fix must not drop or alter any other candidate field -
        only add/overwrite _eval_score.
        """

        evaluator_result, _ = self._run_real_pipeline()

        by_name = {
            c["name"]: c for c in evaluator_result["candidates"]
        }

        # draft_institutional_note is relevant to this request and is
        # guaranteed present (see test_real_pipeline_preserves_eval_
        # score_annotation); pdf-reader is filtered out upstream by
        # ContextBudget's own relevance selection for this request
        # and is not expected to appear here.
        note_candidate = by_name["draft_institutional_note"]

        self.assertEqual(note_candidate["source"], "uri_tool")
        self.assertEqual(note_candidate["category"], "uri_core_capability")
        self.assertEqual(
            note_candidate["purpose"],
            "draft an administrative noting document",
        )

    def test_real_pipeline_routing_is_deterministic_across_runs(self):
        """
        Running the real pipeline twice with identical inputs must
        produce identical scores and routing decisions.
        """

        first_result, first_decision = self._run_real_pipeline()
        second_result, second_decision = self._run_real_pipeline()

        first_scores = [
            c["_eval_score"] for c in first_result["candidates"]
        ]
        second_scores = [
            c["_eval_score"] for c in second_result["candidates"]
        ]

        self.assertEqual(first_scores, second_scores)

        self.assertEqual(
            first_decision["routing_state"],
            second_decision["routing_state"],
        )
        self.assertEqual(
            first_decision["selected"], second_decision["selected"]
        )

    def test_real_direct_evaluate_path_does_not_lose_eval_score(self):
        """
        Contrast case: SkillEvaluatorV1.evaluate() (not the
        ContextBudget-integrated path) correctly annotates
        _eval_score today, so the router sees no missing-score
        candidates through this path.
        """

        from skill_evaluator_v1 import SkillEvaluatorV1

        evaluator = SkillEvaluatorV1(registry_items=self._registry())

        evaluator_result = evaluator.evaluate(
            "draft an office note",
            intent={
                "task_type": "document drafting",
                "requested_output": "office note",
            },
        )

        self.assertGreater(len(evaluator_result["candidates"]), 0)

        router = SkillRouterV1(hermes_allowlist=["pdf-reader"])

        routing_decision = router.route(
            evaluator_result, user_request="draft an office note"
        )

        self.assertEqual(routing_decision["eval_score_missing_count"], 0)


if __name__ == "__main__":
    unittest.main()
