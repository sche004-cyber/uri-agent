import json
import unittest
import sys
import os

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    ),
)

from uri_core.core.context_budget import (
    ContextBudget,
    estimate_characters,
    estimate_json_size,
    _capability_snapshot,
)


# ---------------------------------------------------------------------------
# Lightweight registry fixtures used across tests
# ---------------------------------------------------------------------------

def core_item(name, **overrides):
    base = {
        "name": name,
        "normalized_name": name,
        "source": "uri_tool",
        "category": "uri_core_capability",
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
        "integration_status": "integrated",
        "hermes_should_handle": False,
    }
    base.update(overrides)
    return base


def hermes_skill_item(name, purpose=""):
    return {
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
        "execution_risk": "variable",
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": [],
        "integration_status": "not_applicable",
        "hermes_should_handle": False,
    }


def defuddle_item(**overrides):
    base = {
        "name": "defuddle_tool",
        "normalized_name": "defuddle_tool",
        "source": "uri_tool",
        "category": "skill_optimization",
        "purpose": "",
        "input_requirements": [],
        "output_type": "",
        "token_saving_potential": "high",
        "latency": "unknown",
        "reliability": "unknown",
        "privacy_implications": "unknown",
        "external_dependencies": [],
        "execution_risk": "low",
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": ["pre_reasoning"],
        "integration_status": "integrated",
        "hermes_should_handle": False,
    }
    base.update(overrides)
    return base


def model_provider_item(name):
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


class TestContextBudget(unittest.TestCase):

    def test_irrelevant_skills_are_excluded(self):
        registry = [
            core_item("extract_student_records"),
            hermes_skill_item(
                "apple-notes",
                purpose="note taking on apple devices",
            ),
            hermes_skill_item(
                "ascii-art",
                purpose="generate ascii art",
            ),
            hermes_skill_item(
                "ascii-video",
                purpose="render ascii video",
            ),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(
            request_text="print hello world to the terminal",
            intent={"task_type": "execution"},
        )

        names = {item["name"] for item in context["capabilities"]}
        self.assertNotIn("apple-notes", names)
        self.assertNotIn("ascii-art", names)
        self.assertNotIn("ascii-video", names)
        self.assertIn("extract_student_records", names)

    def test_directly_relevant_skills_are_selected(self):
        registry = [
            core_item("draft_institutional_note"),
            core_item("extract_student_records"),
            hermes_skill_item(
                "ascii-art",
                purpose="generate ascii art",
            ),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(
            request_text="draft an office note for a student request",
        )

        names = {item["name"] for item in context["capabilities"]}
        self.assertIn("draft_institutional_note", names)
        self.assertIn("extract_student_records", names)
        self.assertNotIn("ascii-art", names)

    def test_uri_core_capabilities_receive_appropriate_priority(self):
        registry = [
            core_item("extract_student_records"),
            hermes_skill_item(
                "apple-notes",
                purpose="note taking on apple devices",
            ),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(
            request_text="note tasks on my mac",
        )

        selected = context["capabilities"]
        self.assertGreater(len(selected), 0)

        names = [item["name"] for item in selected]
        if "extract_student_records" in names:
            self.assertLess(
                names.index("extract_student_records"),
                names.index("apple-notes"),
                "URI core capability should rank above non-URI skill",
            )

    def test_context_budget_is_respected(self):
        registry = [
            core_item(
                f"cap_{i}",
                purpose=("x" * 500) + f" {i}",
            )
            for i in range(100)
        ]
        budget = ContextBudget(
            registry_items=registry,
            token_estimator=estimate_json_size,
            max_tokens=3000,
        )
        context = budget.build_context(request_text="do something")

        snapshot_size = estimate_json_size(
            _capability_snapshot(selected := context["capabilities"][0])
        )
        total_size = estimate_json_size(
            [_capability_snapshot(item) for item in context["capabilities"]]
        )
        self.assertLessEqual(
            total_size,
            budget.max_tokens,
            "Selected capabilities must fit within the token budget",
        )
        min_token_size = estimate_json_size(
            _capability_snapshot(context["capabilities"][0]...[truncated]

    def test_max_capability_count_is_respected(self):
        registry = [
            core_item(f"cap_{i}") for i in range(100)
        ]
        budget = ContextBudget(
            registry_items=registry,
            max_capabilities=7,
        )
        context = budget.build_context(request_text="do something")

        self.assertLessEqual(
            len(context["capabilities"]),
            budget.max_capabilities,
        )
        self.assertGreaterEqual(
            len(context["capabilities"]),
            1,
        )

    def test_defuddle_is_selected_as_pre_reasoning_optimization(self):
        registry = [
            core_item("draft_institutional_note"),
            defuddle_item(),
            hermes_skill_item(
                "ascii-art",
                purpose="generate ascii art",
            ),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(
            request_text="draft an office note",
        )

        opt_names = {item["name"] for item in context["optimization_candidates"]}
        self.assertIn("defuddle_tool", opt_names)

    def test_defuddle_not_selected_for_non_reasoning_context(self):
        registry = [
            defuddle_item(),
            core_item("extract_student_records"),
        ]
        budget = ContextBudget(
            registry_items=registry,
            context_purpose="drafting",
        )
        context = budget.build_context(
            request_text="extract student records",
        )

        self.assertEqual(context["optimization_candidates"], [])

    def test_no_capability_execution_occurs(self):
        registry = [
            core_item("extract_student_records"),
            hermes_skill_item("claude-code", purpose="coding agent"),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(request_text="extract student records")

        for item in context["capabilities"]:
            self.assertNotIn("execute", item)
            self.assertNotIn("run", item)
            self.assertNotIn("_executed", item)

        for item in context["optimization_candidates"]:
            self.assertNotIn("execute", item)

    def test_registry_metadata_remains_intact(self):
        registry = [
            core_item("extract_student_records"),
            defuddle_item(),
            hermes_skill_item("ascii-art", purpose="ascii art"),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(request_text="ascii art")

        self.assertEqual(context["total_available"], len(registry))
        self.assertEqual(
            context["budget_max_capabilities"],
            budget.max_capabilities,
        )
        self.assertEqual(
            context["budget_max_tokens"],
            budget.max_tokens,
        )

        for item in context["capabilities"]:
            self.assertIn("normalized_name", item)
            self.assertIn("category", item)
            if item.get("normalized_name") == "defuddle_tool":
                self.assertEqual(item["category"], "skill_optimization")

    def test_empty_and_low_information_requests_are_safe(self):
        registry = [
            core_item("extract_student_records"),
            core_item("draft_institutional_note"),
        ]
        budget = ContextBudget(registry_items=registry)

        context = budget.build_context(request_text="")
        self.assertEqual(context["signal_summary"]["signal_word_count"], 0)
        self.assertGreaterEqual(len(context["capabilities"]), 0)

        context = budget.build_context(request_text="   ")
        self.assertEqual(context["signal_summary"]["signal_word_count"], 0)

        context = budget.build_context(request_text="xyz789")
        self.assertGreaterEqual(len(context["capabilities"]), 0)
        self.assertEqual(context["total_available"], 2)

    def test_token_estimator_is_swappable(self):
        registry = [
            core_item(
                "draft_institutional_note",
                purpose=("abc " * 20),
            ),
        ]

        calls = []

        def fake_estimator(value):
            calls.append(str(value))
            return 123

        budget = ContextBudget(
            registry_items=registry,
            token_estimator=fake_estimator,
        )
        context = budget.build_context(request_text="draft a note")
        self.assertEqual(context["token_estimate"], 123)
        self.assertGreater(len(calls), 0)

    def test_max_capabilities_must_be_positive(self):
        registry = [core_item("cap_1")]
        with self.assertRaises(ValueError):
            ContextBudget(registry_items=registry, max_capabilities=0)

        with self.assertRaises(ValueError):
            ContextBudget(registry_items=registry, max_capabilities=-1)

    def test_max_tokens_must_be_positive(self):
        registry = [core_item("cap_1")]
        with self.assertRaises(ValueError):
            ContextBudget(registry_items=registry, max_tokens=0)

        with self.assertRaises(ValueError):
            ContextBudget(registry_items=registry, max_tokens=-5)

    def test_optimization_candidate_only_when_condition_met(self):
        registry = [
            defuddle_item(invocation_conditions=["post_reasoning"]),
            core_item("extract_student_records"),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(request_text="extract records")

        self.assertNotIn(
            "defuddle_tool",
            {item["name"] for item in context["optimization_candidates"]},
        )

    def test_model_providers_are_not_present_in_selected_capabilities(self):
        registry = [
            model_provider_item("anthropic"),
            model_provider_item("openai-codex"),
            core_item("extract_student_records"),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(request_text="extract records")

        names = {item["name"] for item in context["capabilities"]}
        self.assertNotIn("anthropic", names)
        self.assertNotIn("openai-codex", names)

    def test_skill_optimization_is_selectable_when_relevant(self):
        registry = [
            defuddle_item(),
            core_item("draft_institutional_note"),
        ]
        budget = ContextBudget(registry_items=registry)
        context = budget.build_context(
            request_text="draft an office note",
        )

        selected_names = [item["name"] for item in context["capabilities"]]
        self.assertIn("defuddle_tool", selected_names)
        self.assertIn("draft_institutional_note", selected_names)


class TestEstimationFunctions(unittest.TestCase):

    def test_char_estimate_is_deterministic(self):
        self.assertEqual(estimate_characters("hello"), 5)
        self.assertEqual(estimate_characters(""), 0)

    def test_json_size_estimate_is_bytes_of_serialized_json(self):
        payload = {"a": "ab"}
        size = estimate_json_size(payload)
        self.assertEqual(size, len(json.dumps(payload, ensure_ascii=False)))

    def test_capability_snapshot_preserves_metadata_fields(self):
        item = {
            "name": "draft_institutional_note",
            "normalized_name": "draft_institutional_note",
            "category": "uri_core_capability",
            "purpose": "",
            "input_requirements": [],
            "output_type": "",
            "token_saving_potential": "none",
            "execution_risk": "controlled",
            "model_facing": True,
            "runtime_facing": True,
            "invocation_conditions": [],
            "integration_status": "integrated",
            "hermes_should_handle": False,
        }
        snapshot = _capability_snapshot(item)
        self.assertEqual(snapshot["name"], "draft_institutional_note")
        self.assertEqual(snapshot["category"], "uri_core_capability")
        self.assertEqual(snapshot["runtime_facing"], True)


if __name__ == "__main__":
    print("=" * 72)
    print("URI CONTEXT BUDGET V1 TEST SUITE")
    print("=" * 72)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestContextBudget
    )
    suite.addTests(
        unittest.defaultTestLoader.loadTestsFromTestCase(
            TestEstimationFunctions
        )
    )

    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print()
    print("=" * 72)
    print("CONTEXT BUDGET TESTS:", "PASS" if result.wasSuccessful() else "FAIL")
    print("=" * 72)

    raise SystemExit(0 if result.wasSuccessful() else 1)
