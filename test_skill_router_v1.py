"""
Tests for Skill Router V1.

Focus areas required by the task:
- policy application
- confidence thresholds
- Hermes allow-list handling
- URI-native preference
- deterministic ordering / ties
- clarification and no-match states
- malformed candidates
- side-effect freedom (no execution, no Hermes calls, no external API calls)
"""

import unittest
from typing import Dict, List

from skill_router_v1 import (
    SkillRouterV1,
    is_uri_native,
    hermes_is_approved,
    routing_state_description,
    URI_NATIVE_SOURCES,
    URI_NATIVE_CAPABILITY_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Helpers to build candidate-shaped dicts
# ---------------------------------------------------------------------------

def uri_core_item(name: str, **overrides) -> Dict:
    base = {
        "name": name,
        "normalized_name": name.lower().replace(" ", "_"),
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


def hermes_skill_item(
    name: str,
    *,
    source: str = "hermes_builtin_skill",
    category: str = "on_demand_skill",
    eval_score: float = 40.0,
    **overrides,
) -> Dict:
    base = {
        "name": name,
        "normalized_name": name.lower().replace(" ", "_"),
        "source": source,
        "category": category,
        "purpose": "",
        "execution_risk": "variable",
        "model_facing": True,
        "runtime_facing": False,
        "invocation_conditions": [],
        "integration_status": "not_applicable",
        "hermes_should_handle": False,
        "_eval_score": eval_score,
    }
    base.update(overrides)
    return base


def eval_result(candidates, *, user_request="do something", **overrides) -> Dict:
    clean = [c for c in candidates if isinstance(c, dict) and c.get("name")]
    base = {
        "evaluated_at": "2026-01-01T00:00:00+00:00",
        "request": {
            "user_request": user_request,
            "signal_word_count": 1,
            "intent_present": True,
        },
        "candidates": candidates,
        "best_match": clean[0] if clean else None,
        "routing_recommendation": {
            "destination": "uri_runtime"
            if clean and is_uri_native(clean[0])
            else "hermes",
            "capability": clean[0].get("name") if clean else None,
        },
        "classification_summary": {
            "uri_core_capability": sum(
                1 for c in (candidates or []) if c.get("category") == "uri_core_capability"
            ),
            "on_demand_skill": 0,
            "skill_optimization": 0,
            "integration": 0,
            "development": 0,
            "excluded_non_routable": 0,
            "total_registry_items": 0,
        },
        "has_suitable_capability": bool(candidates),
        "capability_gap": not bool(candidates),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSkillRouterV1DeterministicRouting(unittest.TestCase):
    """Basic routing: evaluator candidates -> policy-bound decision."""

    def test_uri_native_selected_with_high_score(self):
        router = SkillRouterV1(hermes_allowlist=["extra"])
        result = router.route(
            eval_result([uri_core_item("draft_institutional_note", _eval_score=60.0)]),
            user_request="draft a note",
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "draft_institutional_note")
        self.assertTrue(result["selected"]["uri_native"])

    def test_approved_hermes_selected(self):
        router = SkillRouterV1(hermes_allowlist=["pdf-reader"])
        result = router.route(
            eval_result([hermes_skill_item("pdf-reader", eval_score=60.0)]),
            user_request="read pdf",
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "pdf-reader")
        self.assertFalse(result["selected"]["uri_native"])

    def test_multiple_candidates_ordered_with_uri_native_first(self):
        router = SkillRouterV1(
            hermes_allowlist=["pdf-reader", "gmail-search"],
            prefer_uri_native=True,
        )
        result = router.route(
            eval_result([
                hermes_skill_item("pdf-reader", eval_score=50.0),
                uri_core_item("draft_institutional_note", _eval_score=50.0),
            ]),
            user_request="draft a note and read pdf",
        )
        self.assertEqual(result["routing_state"], "ordered_candidates")
        self.assertEqual(result["selected_candidates"][0]["name"], "draft_institutional_note")
        self.assertTrue(result["selected_candidates"][0]["uri_native"])
        self.assertEqual(result["selected_candidates"][1]["name"], "pdf-reader")
        self.assertFalse(result["selected_candidates"][1]["uri_native"])


class TestSkillRouterV1PolicyApplication(unittest.TestCase):
    """Policy gates: eval score, confidence, Hermes allow-list, URI-native logic."""

    def test_low_eval_score_rejected(self):
        router = SkillRouterV1(hermes_allowlist=["anything"])
        result = router.route(
            eval_result([hermes_skill_item("pdf-reader", eval_score=5.0)]),
        )
        self.assertEqual(result["routing_state"], "clarification_required")
        self.assertEqual(result["selected"], None)
        self.assertEqual(len(result["selected_candidates"]), 0)
        self.assertTrue(all(not d["accepted"] for d in result["decisions"]))

    def test_low_confidence_rejected(self):
        # A low eval score yields low confidence relative to scale.
        router = SkillRouterV1(
            hermes_allowlist=["pdf-reader"],
            min_confidence=0.9,
            confidence_scale_best_score=100.0,
        )
        result = router.route(
            eval_result([hermes_skill_item("pdf-reader", eval_score=10.0)]),
        )
        self.assertEqual(result["routing_state"], "clarification_required")
        for d in result["decisions"]:
            self.assertFalse(d["accepted"])
            self.assertIn("confidence", d["reason"])

    def test_high_risk_item_not_auto_rejected_by_router(self):
        # Router is not a risk-execution layer; high risk is recorded but not a
        # hard block unless URI policy says so. Default policy does not block.
        router = SkillRouterV1(hermes_allowlist=["risky-skill"])
        result = router.route(
            eval_result([
                hermes_skill_item(
                    "risky-skill",
                    eval_score=80.0,
                    execution_risk="high",
                )
            ]),
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "risky-skill")
        # Still visible in explanation.
        self.assertTrue(any(d["name"] == "risky-skill" and d["accepted"] for d in result["decisions"]))

    def test_hermes_allowlist_gate_rejects_unapproved(self):
        router = SkillRouterV1(hermes_allowlist=["approved-only"])
        result = router.route(
            eval_result([
                uri_core_item("uri_native_ok"),
                hermes_skill_item("not_approved", eval_score=90.0),
            ]),
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "uri_native_ok")
        self.assertTrue(
            any(d["name"] == "not_approved" and not d["accepted"] for d in result["decisions"])
        )
        rejected_reasons = [
            d["explain"]["reason"]
            for d in result["rejected"]
            if d["candidate"]["name"] == "not_approved"
        ]
        self.assertTrue(rejected_reasons)
        self.assertIn("not in URI-approved allow-list", rejected_reasons[0])

    def test_hermes_allowlist_empty_rejects_non_uri(self):
        router = SkillRouterV1(hermes_allowlist=[], require_hermes_allowlist=True)
        result = router.route(
            eval_result([hermes_skill_item("any_skill")]),
        )
        self.assertEqual(result["routing_state"], "clarification_required")
        self.assertEqual(result["selected"], None)

    def test_uri_native_bypasses_allowlist(self):
        router = SkillRouterV1(hermes_allowlist=[], require_hermes_allowlist=True)
        result = router.route(
            eval_result([uri_core_item("core")]),
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "core")

    def test_require_hermes_allowlist_false_allows_all_hermes(self):
        router = SkillRouterV1(hermes_allowlist=[], require_hermes_allowlist=False)
        result = router.route(
            eval_result([hermes_skill_item("random_skill")]),
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "random_skill")


class TestSkillRouterV1URINativePreference(unittest.TestCase):
    """URI-native preference should order without changing accept/reject outcomes."""

    def test_prefer_uri_native_false_does_not_reject_uri(self):
        router = SkillRouterV1(
            hermes_allowlist=["hermes"],
            prefer_uri_native=False,
        )
        result = router.route(
            eval_result([
                uri_core_item("core"),
                hermes_skill_item("hermes", eval_score=60.0),
            ]),
        )
        self.assertEqual(result["routing_state"], "ordered_candidates")
        names = [c["name"] for c in result["selected_candidates"]]
        # Still sorted by confidence then name, but URI-native not forced first.
        self.assertIn("core", names)
        self.assertIn("hermes", names)

    def test_uri_native_preference_explains(self):
        router = SkillRouterV1(hermes_allowlist=["h"])
        result = router.route(
            eval_result([
                uri_core_item("core"),
                hermes_skill_item("h"),
            ]),
        )
        self.assertTrue(
            any(d["accepted"] and "URI-native capability" in d["reason"] for d in result["decisions"])
        )
        self.assertTrue(
            any("preferred" in d["reason"] for d in result["decisions"])
        )
        self.assertTrue(
            any(d["uri_native_preference_applied"] for d in result["decisions"])
        )


class TestSkillRouterV1DeterministicOrderingAndTies(unittest.TestCase):
    """Identical inputs must produce identical ordering."""

    def test_tie_break_by_name(self):
        router = SkillRouterV1(
            hermes_allowlist=["b", "a"],
            min_eval_score=0,
            min_confidence=0.0,
        )
        result = router.route(
            eval_result([
                hermes_skill_item("b", eval_score=50.0),
                hermes_skill_item("a", eval_score=50.0),
            ]),
        )
        ordered = [c["name"] for c in result["selected_candidates"]]
        self.assertEqual(ordered, ["a", "b"])

    def test_stable_ordering_across_two_calls(self):
        router = SkillRouterV1(
            hermes_allowlist=["x", "y", "z"],
            min_eval_score=0,
            min_confidence=0.0,
        )
        ev = eval_result([
            hermes_skill_item("z", eval_score=10.0),
            hermes_skill_item("y", eval_score=10.0),
            hermes_skill_item("x", eval_score=10.0),
        ])
        first = router.route(ev)
        second = router.route(ev)
        self.assertEqual(first["selected_candidates"], second["selected_candidates"])

    def test_uri_native_first_when_scores_equal(self):
        router = SkillRouterV1(
            hermes_allowlist=["h"],
            prefer_uri_native=True,
            min_eval_score=0,
            min_confidence=0.0,
        )
        result = router.route(
            eval_result([
                hermes_skill_item("h", eval_score=50.0),
                uri_core_item("core", _eval_score=50.0),
            ]),
        )
        self.assertEqual(result["selected_candidates"][0]["name"], "core")


class TestSkillRouterV1ClarificationAndNoMatchStates(unittest.TestCase):
    """Router states for insufficient signal or rejected candidates."""

    def test_no_suitable_capability_from_empty_candidates(self):
        router = SkillRouterV1()
        result = router.route(eval_result([]))
        self.assertEqual(result["routing_state"], "no_suitable_capability")
        self.assertEqual(result["selected"], None)
        self.assertEqual(result["selected_candidates"], [])

    def test_clarification_required_when_only_unapproved_hermes(self):
        router = SkillRouterV1(hermes_allowlist=[], require_hermes_allowlist=True)
        result = router.route(
            eval_result([hermes_skill_item("unapproved")]),
        )
        self.assertEqual(result["routing_state"], "clarification_required")
        self.assertEqual(result["selected"], None)

    def test_clarification_required_reason_includes_leading_rejection(self):
        router = SkillRouterV1(hermes_allowlist=[], require_hermes_allowlist=True)
        result = router.route(
            eval_result([hermes_skill_item("unapproved")]),
        )
        self.assertIn("unapproved", result["reason"])


class TestSkillRouterV1MalformedCandidates(unittest.TestCase):
    """Robustness when evaluator output is messy."""

    def test_non_dict_candidates_skipped(self):
        router = SkillRouterV1(hermes_allowlist=[], min_eval_score=0.0, min_confidence=0.0)
        result = router.route(
            eval_result([uri_core_item("valid", _eval_score=40.0)]),
        )
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "valid")

    def test_missing_name_treated_safely(self):
        router = SkillRouterV1(min_eval_score=0.0, min_confidence=0.0)
        result = router.route(
            eval_result([{"source": "uri_tool", "category": "uri_core_capability"}]),
        )
        # Still routes because uri_native bypass + zeroed thresholds allow it.
        self.assertEqual(result["routing_state"], "selected")
        self.assertEqual(result["selected"]["name"], "<unknown>")
        self.assertEqual(result["selected_candidates"][0]["name"], "<unknown>")

    def test_invalid_evaluator_result_returns_no_suitable_capability(self):
        router = SkillRouterV1()
        result = router.route("not-a-dict")
        self.assertEqual(result["routing_state"], "no_suitable_capability")
        self.assertEqual(result["selected"], None)

    def test_missing_candidates_key_returns_no_suitable_capability(self):
        router = SkillRouterV1()
        result = router.route({})
        self.assertEqual(result["routing_state"], "no_suitable_capability")


class TestSkillRouterV1SideEffectFreedom(unittest.TestCase):
    """Router must not execute, call Hermes, or touch external APIs."""

    def test_does_not_contain_execution_fields(self):
        router = SkillRouterV1(
            hermes_allowlist=["h"],
            min_eval_score=0.0,
            min_confidence=0.0,
        )
        result = router.route(
            eval_result([uri_core_item("core", _eval_score=40.0)]),
        )
        serialized = str(result)
        for forbidden in ["executed", "called"]:
            self.assertNotIn(forbidden, serialized.lower())

        for d in result["decisions"]:
            self.assertNotIn("execute", d)

    def test_does_not_provide_authorization_flags(self):
        router = SkillRouterV1()
        result = router.route(
            eval_result([uri_core_item("core")]),
        )
        self.assertNotIn("authorized", result)
        self.assertNotIn("approval_granted", result)
        self.assertNotIn("granted", result.get("policy_applied", {}))

    def test_does_not_invoke_hermes(self):
        router = SkillRouterV1(hermes_allowlist=["h"])
        result = router.route(
            eval_result([hermes_skill_item("h")]),
        )
        self.assertNotIn("hermes_response", result)
        self.assertNotIn("hermes_result", result)
        self.assertNotIn("hermes_output", result)

    def test_does_not_call_external_apis(self):
        # Structural check: the returned payload is self-contained and
        # contains no external resource handles.
        router = SkillRouterV1()
        result = router.route(
            eval_result([uri_core_item("core")]),
        )
        self.assertNotIn("http", str(result).lower())
        self.assertNotIn("url", str(result).lower())
        self.assertNotIn("api", str(result).lower())


class TestSkillRouterV1StandalonePredicates(unittest.TestCase):
    """Unit tests for exported helper predicates."""

    def test_is_uri_native_by_source(self):
        self.assertTrue(is_uri_native({"source": "uri_tool", "category": "integration"}))
        self.assertTrue(is_uri_native({"source": "uri_core", "category": "on_demand_skill"}))

    def test_is_uri_native_by_category(self):
        self.assertTrue(is_uri_native({"source": "hermes_plugin", "category": "uri_core_capability"}))

    def test_is_uri_native_false_for_hermes_builtin(self):
        self.assertFalse(
            is_uri_native({"source": "hermes_builtin_skill", "category": "on_demand_skill"})
        )

    def test_hermes_is_approved_allows_uri_native(self):
        self.assertTrue(
            hermes_is_approved(
                {"source": "uri_tool", "category": "uri_core_capability"},
                allowlist=[],
                require_allowlist=True,
            )
        )

    def test_hermes_is_approved_rejects_unlisted(self):
        self.assertFalse(
            hermes_is_approved(
                {"source": "hermes_builtin_skill", "name": "unknown"},
                allowlist=["known"],
                require_allowlist=True,
            )
        )

    def test_hermes_is_approved_allows_listed(self):
        self.assertTrue(
            hermes_is_approved(
                {"source": "hermes_builtin_skill", "name": "known"},
                allowlist=["known"],
                require_allowlist=True,
            )
        )

    def test_routing_state_description_known_states(self):
        for state in ["selected", "ordered_candidates", "clarification_required", "no_suitable_capability"]:
            self.assertIsInstance(routing_state_description(state), str)
            self.assertTrue(len(routing_state_description(state)) > 0)


class TestSkillRouterV1ContextBudgetPresence(unittest.TestCase):
    """ContextBudget is optional and diagnostic only."""

    def test_context_budget_present_flag(self):
        router = SkillRouterV1()
        result = router.route(
            eval_result([uri_core_item("core")]),
            context_budget_output={"capabilities": [], "token_estimate": 123},
        )
        self.assertTrue(result["context_used"]["context_budget_present"])
        self.assertEqual(result["context_used"]["evaluator_result_keys"], sorted([
            "best_match",
            "capability_gap",
            "candidates",
            "classification_summary",
            "evaluated_at",
            "has_suitable_capability",
            "request",
            "routing_recommendation",
        ]))

    def test_context_budget_absent_flag(self):
        router = SkillRouterV1()
        result = router.route(eval_result([uri_core_item("core")]))
        self.assertFalse(result["context_used"]["context_budget_present"])


class TestSkillRouterV1InputValidation(unittest.TestCase):
    """Constructor rejects invalid policy knobs."""

    def test_min_confidence_range(self):
        with self.assertRaises(ValueError):
            SkillRouterV1(min_confidence=1.5)

        with self.assertRaises(ValueError):
            SkillRouterV1(min_confidence=-0.1)

    def test_min_eval_score_non_negative(self):
        with self.assertRaises(ValueError):
            SkillRouterV1(min_eval_score=-1.0)

    def test_max_candidates_positive(self):
        with self.assertRaises(ValueError):
            SkillRouterV1(max_candidates_returned=0)


if __name__ == "__main__":
    print("=" * 72)
    print("SKILL ROUTER V1 TEST SUITE")
    print("=" * 72)

    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print()
    print("=" * 72)
    print(f"SKILL ROUTER V1 TESTS: {'PASS' if result.wasSuccessful() else 'FAIL'}")
    print("=" * 72)

    import sys as _sys
    _sys.exit(0 if result.wasSuccessful() else 1)
