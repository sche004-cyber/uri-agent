import json
import unittest
import sys
import os

# Add the project root to the path so we can import from uri_core
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    ),
)

from skill_evaluator_v1 import (
    SkillEvaluatorV1,
    ROUTABLE_CAPABILITY_CATEGORIES,
    NON_ROUTABLE_CATEGORIES,
)


# Helper functions copied from the original test file for consistency
def uri_core_item(name: str, purpose: str = "", **overrides) -> dict:
    base = {
        "name": name,
        "normalized_name": name,
        "source": "uri_tool",
        "category": "uri_core_capability",
        "purpose": purpose,
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": "none",
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": "controlled",
        "model_facing": True,
        "runtime_facing": True,
        "invocation_conditions": [],
        "integration_status": "integrated",
        "hermes_should_handle": False,
    }
    base.update(overrides)
    return base


def hermes_skill_item(
    name: str,
    purpose: str = "",
    execution_risk: str = "variable",
    **overrides,
) -> dict:
    base = {
        "name": name,
        "normalized_name": name,
        "source": "hermes_builtin_skill",
        "category": "on_demand_skill",
        "purpose": purpose,
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": "none",
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": execution_risk,
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": [],
        "integration_status": "not_applicable",
        "hermes_should_handle": False,
    }
    base.update(overrides)
    return base


def optimization_item(
    name: str = "defuddle_tool",
    purpose: str = "",
    token_saving_potential: str = "high",
    invocation_conditions=None,
    **overrides,
) -> dict:
    base = {
        "name": name,
        "normalized_name": name,
        "source": "uri_tool",
        "category": "skill_optimization",
        "purpose": purpose,
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": token_saving_potential,
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": "low",
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": invocation_conditions or ["pre_reasoning"],
        "integration_status": "integrated",
        "hermes_should_handle": False,
    }
    base.update(overrides)
    return base


def model_provider_item(name: str) -> dict:
    return {
        "name": name,
        "normalized_name": name,
        "source": "hermes_plugin",
        "category": "model_provider",
        "purpose": "",
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": "none",
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": "controlled",
        "model_facing": True,
        "runtime_facing": True,
        "invocation_conditions": [],
        "integration_status": "not_applicable",
        "hermes_should_handle": False,
    }


def hermes_specialist_item(name: str = "hermes-agent") -> dict:
    return {
        "name": name,
        "normalized_name": name,
        "source": "hermes_builtin_skill",
        "category": "hermes_specialist",
        "purpose": "",
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": "none",
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": "high",
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": [],
        "integration_status": "delegated",
        "hermes_should_handle": True,
    }


def specialized_item(name: str = "nit-sikkim-office-assistant") -> dict:
    return {
        "name": name,
        "normalized_name": name,
        "source": "hermes_builtin_skill",
        "category": "specialized",
        "purpose": "",
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": "none",
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": "controlled",
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": [],
        "integration_status": "preserved",
        "hermes_should_handle": False,
    }


def _candidate_score(candidates, name):
    for c in candidates:
        if c.get("name") == name:
            return c.get("_eval_score", 0.0)
    return 0.0


class TestSkillEvaluatorV1DirectRegistryEvaluation(unittest.TestCase):
    """Evaluate using the full registry items list directly."""

    def setUp(self):
        self.registry = [
            uri_core_item("draft_institutional_note", purpose="draft an administrative noting document"),
            uri_core_item("extract_student_records", purpose="retrieve student academic records"),
            hermes_skill_item(
                "pdf-reader",
                purpose="read and extract text from PDF files",
            ),
            hermes_skill_item(
                "gmail-search",
                purpose="search emails in gmail",
            ),
            optimization_item(
                "defuddle_tool",
                purpose="reduce context before model reasoning",
            ),
            model_provider_item("anthropic"),
            hermes_specialist_item(),
            specialized_item(),
        ]

    def test_directly_relevant_capability_ranks_highly(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate_with_score_annotation(
            "draft an office note for a new policy",
            intent={
                "task_type": "document drafting",
                "requested_output": "office note",
                "domain": "administrative",
            },
        )

        candidates = result["candidates"]
        self.assertGreater(len(candidates), 0)

        best = result["best_match"]
        self.assertIsNotNone(best)
        self.assertEqual(best["name"], "draft_institutional_note")
        self.assertGreater(
            _candidate_score(candidates, "draft_institutional_note"),
            _candidate_score(candidates, "pdf-reader"),
        )

    def test_irrelevant_capability_ranks_low_or_excluded(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate_with_score_annotation(
            "draft an office note for a new policy",
            intent={"task_type": "document drafting"},
        )

        low_score_names = [
            name
            for name, score in [
                (n, _candidate_score(result["candidates"], n))
                for n in ["gmail-search", "anthropic"]
            ]
            if score <= 5
        ]
        self.assertIn("anthropic", low_score_names)
        self.assertNotIn("draft_institutional_note", low_score_names)

    def test_uri_core_capability_classification_preserved(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate(
            "retrieve student academic records",
            intent={"task_type": "data retrieval"},
        )

        self.assertTrue(result["has_suitable_capability"])
        best = result["best_match"]
        self.assertEqual(best["category"], "uri_core_capability")
        self.assertEqual(best["name"], "extract_student_records")

        summary = result["classification_summary"]
        self.assertGreater(summary["uri_core_capability"], 0)

    def test_hermes_skill_classification_preserved(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate(
            "read text from a PDF file",
            intent={"task_type": "document extraction"},
        )

        self.assertTrue(result["has_suitable_capability"])
        best = result["best_match"]
        self.assertEqual(best["category"], "on_demand_skill")
        self.assertTrue(best["model_facing"])
        self.assertFalse(best["runtime_facing"])

    def test_hermes_specialist_remains_delegated(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate("whatever task")

        self.assertFalse(
            any(
                item.get("name") == "hermes-agent"
                for item in result["candidates"]
            ),
            "Hermes specialist should not appear in normal candidate list",
        )

        summary = result["classification_summary"]
        self.assertEqual(summary["excluded_non_routable"], 3)

    def test_defuddle_identified_as_optimization_not_task_capability(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate(
            "draft an office note for a complex policy change",
            intent={
                "task_type": "document drafting",
                "requested_output": "office note",
                "domain": "administrative",
            },
        )

        self.assertTrue(result["has_suitable_capability"])
        best = result["best_match"]
        self.assertEqual(best["name"], "draft_institutional_note")

        opt_candidates = [
            c
            for c in result["candidates"]
            if c.get("category") == "skill_optimization"
        ]
        self.assertTrue(
            any(c["name"] == "defuddle_tool" for c in opt_candidates),
            "Defuddle should be present as optimization candidate",
        )

        routing = result["routing_recommendation"]
        self.assertEqual(routing["destination"], "uri_runtime")
        self.assertEqual(routing["capability"], "draft_institutional_note")

    def test_unavailable_capability_not_invented(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate(
            "send an email through outlook",
            intent={"task_type": "email sending"},
        )

        candidate_names = {c["name"] for c in result["candidates"]}
        self.assertNotIn("outlook-email", candidate_names)
        self.assertNotIn("send-email", candidate_names)
        self.assertNotIn("email-send", candidate_names)

        self.assertFalse(result["has_suitable_capability"])
        self.assertTrue(result["capability_gap"])

        routing = result["routing_recommendation"]
        self.assertEqual(routing["destination"], "none")
        self.assertTrue(routing["requires_user_clarification"])

    def test_low_information_request_handled_safely(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate("", intent={})

        self.assertFalse(result["has_suitable_capability"])
        self.assertTrue(result["capability_gap"])
        self.assertEqual(result["routing_recommendation"]["destination"], "none")

        result2 = evaluator.evaluate("   ", intent=None)
        self.assertFalse(result2["has_suitable_capability"])

    def test_evaluator_never_executes_anything(self):
        evaluator = SkillEvaluatorV1(registry_items=self.registry)
        result = evaluator.evaluate(
            "draft an office note",
            intent={"task_type": "document drafting"},
        )

        for candidate in result.get("candidates", []):
            self.assertNotIn("execute", candidate)
            self.assertNotIn("run", candidate)
            self.assertNotIn("called", str(candidate).lower())

        self.assertNotIn("executed", result)
        self.assertNotIn("status", result)

    def test_evaluator_consumes_context_budget_output(self):
        from uri_core.core.context_budget import ContextBudget

        registry = [
            uri_core_item("draft_institutional_note"),
            uri_core_item("extract_student_records"),
            hermes_skill_item("pdf-reader", purpose="read PDF files"),
            optimization_item("defuddle_tool"),
            model_provider_item("anthropic"),
        ]

        budget = ContextBudget(
            registry_items=registry,
            max_capabilities=10,
            max_tokens=5000,
        )
        budget_output = budget.build_context(
            "draft an office note",
            intent={"task_type": "document drafting", "requested_output": "office note"},
        )

        evaluator = SkillEvaluatorV1()
        result = evaluator.evaluate_from_context_budget(
            "draft an office note",
            budget_output,
            intent={"task_type": "document drafting", "requested_output": "office note"},
        )

        self.assertTrue(result["has_suitable_capability"])
        self.assertIn(
            "draft_institutional_note",
            {c["name"] for c in result["candidates"]},
        )
        self.assertTrue(
            any(c["name"] == "defuddle_tool" for c in result["candidates"])
        )

        routing = result["routing_recommendation"]
        self.assertEqual(routing["destination"], "uri_runtime")
        self.assertEqual(routing["capability"], "draft_institutional_note")

    def test_routing_recommendation_for_optimize_destination(self):
        registry = [
            optimization_item("defuddle_tool", purpose="reduce context"),
            uri_core_item("extract_student_records"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate(
            "summarize long document before reasoning",
            intent={"task_type": "summarization"},
        )

        self.assertTrue(result["has_suitable_capability"])
        best = result["best_match"]
        routing = result["routing_recommendation"]
        self.assertEqual(routing["destination"], "optimization")
        self.assertEqual(routing["capability"], "defuddle_tool")

    def test_routing_recommendation_for_hermes_skill(self):
        registry = [
            hermes_skill_item("pdf-reader", purpose="read and extract PDF text"),
            uri_core_item("draft_institutional_note"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate(
            "extract text from PDF",
            intent={"task_type": "document extraction"},
        )

        self.assertTrue(result["has_suitable_capability"])
        routing = result["routing_recommendation"]
        self.assertEqual(routing["destination"], "hermes")
        self.assertEqual(routing["capability"], "pdf-reader")

    def test_routing_recommendation_for_uri_core_capability(self):
        registry = [
            uri_core_item("draft_institutional_note"),
            uri_core_item("extract_student_records"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate(
            "draft an office noting",
            intent={"task_type": "document drafting"},
        )

        routing = result["routing_recommendation"]
        self.assertEqual(routing["destination"], "uri_runtime")
        self.assertEqual(routing["capability"], "draft_institutional_note")

    def test_classification_summary_counts_all_categories(self):
        registry = [
            uri_core_item("a"),
            hermes_skill_item("b"),
            optimization_item("c"),
            model_provider_item("d"),
            hermes_specialist_item("e"),
            specialized_item("f"),
            uri_core_item("g", execution_risk="high"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate("task", intent={"task_type": "task"})

        summary = result["classification_summary"]
        self.assertEqual(summary["total_registry_items"], 7)
        self.assertGreater(summary["uri_core_capability"], 0)
        self.assertGreater(summary["on_demand_skill"], 0)
        self.assertGreater(summary["skill_optimization"], 0)
        self.assertGreater(summary["excluded_non_routable"], 0)

    def test_high_risk_capability_penalized_in_scoring(self):
        registry = [
            uri_core_item(
                "some_capability",
                purpose="does something risky",
                execution_risk="high",
            ),
            uri_core_item("safe_capability", purpose="safe helper"),
            uri_core_item("medium_capability", purpose="medium risk thing", execution_risk="variable"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate_with_score_annotation(
            "do something safe",
            intent={"task_type": "generic"},
        )

        safe_score = _candidate_score(result["candidates"], "safe_capability")
        risky_score = _candidate_score(result["candidates"], "some_capability")
        medium_score = _candidate_score(result["candidates"], "medium_capability")

        self.assertGreater(safe_score, risky_score)
        self.assertGreater(safe_score, medium_score)

    def test_intent_with_entities_boosts_relevant_skill(self):
        registry = [
            uri_core_item("extract_student_records", purpose="retrieve student records by roll number"),
            uri_core_item("draft_institutional_note"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate(
            "get the record for btech student",
            intent={
                "task_type": "data retrieval",
                "entities": ["btech", "roll number", "student id"],
            },
        )

        best = result["best_match"]
        self.assertEqual(best["name"], "extract_student_records")


class TestSkillEvaluatorV1ClassificationSemantics(unittest.TestCase):
    """Verify evaluator respects classification semantics from registry."""

    def test_routable_categories_are_whitelisted(self):
        self.assertIn("uri_core_capability", ROUTABLE_CAPABILITY_CATEGORIES)
        self.assertIn("on_demand_skill", ROUTABLE_CAPABILITY_CATEGORIES)
        self.assertIn("skill_optimization", ROUTABLE_CAPABILITY_CATEGORIES)
        self.assertIn("integration", ROUTABLE_CAPABILITY_CATEGORIES)
        self.assertIn("development", ROUTABLE_CAPABILITY_CATEGORIES)

    def test_non_routable_categories_are_excluded(self):
        self.assertIn("model_provider", NON_ROUTABLE_CATEGORIES)
        self.assertIn("model_infrastructure", NON_ROUTABLE_CATEGORIES)
        self.assertIn("hermes_specialist", NON_ROUTABLE_CATEGORIES)
        self.assertIn("specialized", NON_ROUTABLE_CATEGORIES)

    def test_specialized_skill_not_selected_for_general_task(self):
        registry = [
            specialized_item(),
            uri_core_item("draft_institutional_note"),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate("draft a note", intent={"task_type": "document drafting"})

        self.assertNotIn(
            "nit-sikkim-office-assistant",
            {c["name"] for c in result["candidates"]},
        )
        self.assertTrue(result["has_suitable_capability"])


class TestSkillEvaluatorV1EdgeCases(unittest.TestCase):
    """Edge case and defensive behavior tests."""

    def test_empty_registry(self):
        evaluator = SkillEvaluatorV1(registry_items=[])
        result = evaluator.evaluate("anything", intent={"task_type": "task"})

        self.assertFalse(result["has_suitable_capability"])
        self.assertTrue(result["capability_gap"])
        self.assertEqual(result["routing_recommendation"]["destination"], "none")

    def test_none_intent_handled(self):
        evaluator = SkillEvaluatorV1(registry_items=[uri_core_item("test")])
        result = evaluator.evaluate("task", intent=None)
        self.assertIsInstance(result, dict)
        self.assertIn("candidates", result)
        self.assertIn("routing_recommendation", result)

    def test_malformed_intent_keys_dont_crash(self):
        evaluator = SkillEvaluatorV1(registry_items=[uri_core_item("test")])
        result = evaluator.evaluate(
            "task",
            intent={"task_type": 123, "domain": None, "entities": "not a list"},
        )
        self.assertIsInstance(result, dict)

    def test_malformed_registry_items_skipped_safely(self):
        registry = [
            "not a dict",
            None,
            123,
            {"name": "valid", "category": "uri_core_capability"},
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate("task", intent={"task_type": "task"})
        self.assertIsInstance(result, dict)
        candidate_names = {c["name"] for c in result["candidates"]}
        self.assertIn("valid", candidate_names)

    def test_multiple_optimization_skills_distinguished(self):
        registry = [
            optimization_item("defuddle_tool", purpose="context reduction"),
            optimization_item(
                "some_other_opt",
                purpose="speed optimization",
                invocation_conditions=[],
            ),
        ]
        evaluator = SkillEvaluatorV1(registry_items=registry)
        result = evaluator.evaluate(
            "reduce context size before reasoning",
            intent={"task_type": "reasoning preparation"},
        )

        opt_names = [
            c["name"]
            for c in result["candidates"]
            if c.get("category") == "skill_optimization"
        ]
        self.assertIn("defuddle_tool", opt_names)
        self.assertTrue(
            result["has_suitable_capability"],
            "Should find defuddle as optimization when task matches",
        )


if __name__ == "__main__":
    print("=" * 72)
    print("SKILL EVALUATOR V1 TEST SUITE")
    print("=" * 72)

    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print()
    print("=" * 72)
    print(f"SKILL EVALUATOR V1 TESTS: {'PASS' if result.wasSuccessful() else 'FAIL'}")
    print("=" * 72)

    sys.exit(0 if result.wasSuccessful() else 1)