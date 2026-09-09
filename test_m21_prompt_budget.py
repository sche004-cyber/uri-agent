"""M21: coverage for the shared, deterministic budget/bounding utilities
(context_budget.estimate_tokens/bound_json_value/fit_within_budget) and
their application to the two largest unbounded prompt-bloat sources the
M21 audit measured on real state:

- orchestrator.py's session_context.active_workflow.execution_history,
  measured at 65,634 characters (~16,400 tokens) in one real persisted
  session (uri_workspace/sessions/noting_generation_test.json) - larger
  than URI's entire reasoning prompt.
- system_policy being resent in full (~9,778 chars, 58.8% of one real
  reasoning payload) inside the variable user JSON on every one of the
  several Brain calls one turn can make.

No live model calls here - test_m21_context_window_live.py covers the
real-model regression separately.
"""

import unittest

from uri_core.core.context_budget import (
    bound_json_value,
    estimate_tokens,
    fit_within_budget,
)
from uri_core.core.orchestrator import (
    MAX_EXECUTION_HISTORY_ENTRIES,
    UriOrchestrator,
)
from uri_core.core.state import SessionState


class EstimateTokensTests(unittest.TestCase):

    def test_empty_and_none_are_zero(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens(None), 0)

    def test_scales_with_length(self):
        short = estimate_tokens("a" * 40)
        long = estimate_tokens("a" * 400)
        self.assertLess(short, long)
        self.assertEqual(long, 100)


class BoundJsonValueTests(unittest.TestCase):

    def test_value_within_budget_is_returned_unchanged(self):
        value = {"a": 1, "b": "small"}
        self.assertEqual(bound_json_value(value, max_chars=800), value)

    def test_oversized_value_is_replaced_with_truncated_preview(self):
        value = {"data": "x" * 5000}
        result = bound_json_value(value, max_chars=800)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("_truncated"))
        self.assertLessEqual(len(result["preview"]), 800 + len("...(truncated)"))

    def test_never_raises_on_unserializable_value(self):
        class Unserializable:
            def __repr__(self):
                return "Unserializable()"

        result = bound_json_value(Unserializable(), max_chars=10)
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("_truncated"))


class FitWithinBudgetTests(unittest.TestCase):

    def test_all_items_kept_when_under_budget(self):
        items = [{"i": i} for i in range(3)]
        result = fit_within_budget(items, max_tokens=1000)
        self.assertEqual(result, items)

    def test_drops_lowest_priority_items_over_budget(self):
        # Each item is a fixed size; caller-provided order is priority
        # (most-important-first) - fit_within_budget never reorders.
        items = [{"pad": "x" * 40} for _ in range(20)]
        one_item_tokens = estimate_tokens(
            __import__("json").dumps(items[0], ensure_ascii=False)
        )
        budget = one_item_tokens * 3
        result = fit_within_budget(items, max_tokens=budget)

        self.assertLess(len(result), len(items))
        self.assertEqual(result, items[: len(result)])

    def test_never_empties_the_list_for_one_oversized_leading_item(self):
        items = [{"pad": "x" * 5000}, {"pad": "y"}]
        result = fit_within_budget(items, max_tokens=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], items[0])

    def test_empty_input_returns_empty_output(self):
        self.assertEqual(fit_within_budget([], max_tokens=100), [])

    def test_custom_estimator_is_used(self):
        items = ["a", "bb", "ccc"]
        result = fit_within_budget(items, max_tokens=3, item_estimator=len)
        self.assertEqual(result, ["a", "bb"])


class ExecutionHistoryBoundingTests(unittest.TestCase):
    """orchestrator.py's _bounded_active_workflow / _build_model_session_
    context must never let an unbounded execution_history reach a Brain
    call - the single largest real defect measured during the M21
    audit."""

    def _orchestrator(self):
        return UriOrchestrator(enable_model_reasoning_shadow=False)

    def test_short_execution_history_passes_through_unchanged(self):
        orchestrator = self._orchestrator()
        workflow = {
            "workflow_id": "wf1",
            "status": "in_progress",
            "steps": [],
            "execution_history": [{"step": "one"}, {"step": "two"}],
        }
        result = orchestrator._bounded_active_workflow(workflow)
        self.assertEqual(result["execution_history"], workflow["execution_history"])
        self.assertNotIn("execution_history_omitted_count", result)

    def test_long_execution_history_is_capped_to_most_recent_entries(self):
        orchestrator = self._orchestrator()
        history = [{"step": f"step_{i}", "data": "x" * 50} for i in range(50)]
        workflow = {"workflow_id": "wf1", "execution_history": history}

        result = orchestrator._bounded_active_workflow(workflow)

        self.assertEqual(
            len(result["execution_history"]), MAX_EXECUTION_HISTORY_ENTRIES
        )
        self.assertEqual(
            result["execution_history_omitted_count"],
            len(history) - MAX_EXECUTION_HISTORY_ENTRIES,
        )
        # Kept entries are the most RECENT ones, not the oldest.
        kept_steps = [entry.get("step") for entry in result["execution_history"]]
        self.assertEqual(
            kept_steps,
            [f"step_{i}" for i in range(50 - MAX_EXECUTION_HISTORY_ENTRIES, 50)],
        )

    def test_realistic_65k_character_history_shrinks_to_a_small_bounded_size(self):
        # Mirrors the real shape measured in
        # uri_workspace/sessions/noting_generation_test.json during the
        # M21 audit: a long-running workflow whose execution_history
        # alone reached 65,634 characters.
        import json

        orchestrator = self._orchestrator()
        history = [
            {
                "step_id": f"step_{i}",
                "capability": "retrieve_evidence",
                "status": "completed",
                "result": {"data": "y" * 1600},
            }
            for i in range(40)
        ]
        workflow = {"workflow_id": "wf1", "steps": [], "execution_history": history}
        self.assertGreater(len(json.dumps(history)), 65000)

        result = orchestrator._bounded_active_workflow(workflow)
        bounded_size = len(json.dumps(result["execution_history"]))

        self.assertLess(bounded_size, 5000)

    def test_non_dict_active_workflow_degrades_safely(self):
        orchestrator = self._orchestrator()
        self.assertIsNone(orchestrator._bounded_active_workflow(None))
        self.assertEqual(orchestrator._bounded_active_workflow("not a workflow"), "not a workflow")

    def test_build_model_session_context_bounds_execution_history_end_to_end(self):
        orchestrator = self._orchestrator()
        history = [{"step": i, "data": "z" * 200} for i in range(30)]
        session = SessionState(
            session_id="s1",
            active_workflow={"workflow_id": "wf1", "execution_history": history},
        )

        context = orchestrator._build_model_session_context(session)

        self.assertLessEqual(
            len(context["active_workflow"]["execution_history"]),
            MAX_EXECUTION_HISTORY_ENTRIES,
        )

    def test_build_model_session_context_bounds_oversized_fact_fields(self):
        orchestrator = self._orchestrator()
        session = SessionState(
            session_id="s1",
            current_facts={"blob": "q" * 5000},
        )

        context = orchestrator._build_model_session_context(session)

        self.assertIsInstance(context["current_facts"], dict)
        self.assertTrue(context["current_facts"].get("_truncated"))

    def test_build_model_session_context_leaves_small_facts_unchanged(self):
        orchestrator = self._orchestrator()
        session = SessionState(
            session_id="s1",
            current_facts={"subject": "Extension request"},
        )

        context = orchestrator._build_model_session_context(session)

        self.assertEqual(context["current_facts"], {"subject": "Extension request"})


if __name__ == "__main__":
    unittest.main()
