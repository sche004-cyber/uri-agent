import json
import os
import tempfile
import unittest

from uri_core.core.arn import (
    ARNEngine,
    ARNState,
    ARNStatus,
    Candidate,
    CostCeiling,
    EvidenceCategory,
    EvidenceItem,
    EvidencePromotionError,
    UserClue,
    attach_not_found_recovery,
)
from uri_core.core.turn_state import assemble_turn_state


class ARN1DeterministicNarrowingTests(unittest.TestCase):
    def test_initial_not_found_triggers_recovery_instead_of_terminal_failure(self):
        envelope = {
            "status": "unavailable",
            "execution": {"status": "not_found", "capability": "search"},
        }
        recovered = attach_not_found_recovery(
            envelope, goal="find policy", source="search", query="policy"
        )
        self.assertEqual(recovered["status"], "recovery_required")
        self.assertEqual(recovered["execution"]["status"], "not_found")
        self.assertEqual(recovered["arn_state"]["status"], "ACTIVE")

    def test_candidate_tracking_progressive_elimination(self):
        engine = ARNEngine()
        engine.trigger_recovery("find policy", "policy", [])
        engine.add_candidates(
            [Candidate("a"), Candidate("b"), Candidate("c")]
        )
        engine.eliminate_candidate("b", "wrong year")
        engine.eliminate_candidate("c", "wrong source")
        self.assertEqual([item.candidate_id for item in engine.state.candidates], ["a"])
        self.assertEqual([item.reason for item in engine.state.eliminated], ["wrong year", "wrong source"])

    def test_repeated_search_is_recorded_once(self):
        engine = ARNEngine()
        engine.trigger_recovery("find policy", "Policy  2024", [])
        self.assertTrue(engine.is_search_repeated("initial_lookup", "policy 2024"))
        self.assertFalse(engine.record_source_checked("initial_lookup", "POLICY 2024", []))
        self.assertEqual(len(engine.state.sources_checked), 1)

    def test_edge_deduction_cannot_be_promoted_to_verified_fact(self):
        deduction = EvidenceItem(EvidenceCategory.EDGE_DEDUCTION, "likely match")
        with self.assertRaises(EvidencePromotionError):
            deduction.reclassify(EvidenceCategory.VERIFIED_FACT)

    def test_user_clue_filters_only_task_scoped_candidates(self):
        durable_memory = {"category": "must remain untouched"}
        engine = ARNEngine()
        engine.trigger_recovery("find rule", "rule", [])
        engine.add_candidates(
            [
                Candidate("a", metadata={"category": "Faculty"}),
                Candidate("b", metadata={"category": "Project Staff"}),
            ]
        )
        remaining = engine.apply_user_clue(UserClue("category", "Faculty"))
        self.assertEqual([item.candidate_id for item in remaining], ["a"])
        self.assertEqual(durable_memory, {"category": "must remain untouched"})
        self.assertEqual(engine.state.user_clues[0].category, EvidenceCategory.USER_CLUE)

    def test_user_clue_that_rules_out_every_candidate_has_distinct_status(self):
        engine = ARNEngine()
        engine.trigger_recovery("find rule", "rule", [])
        engine.add_candidates([Candidate("a", metadata={"year": 2024})])
        engine.apply_user_clue(UserClue("year", 2025))
        self.assertEqual(engine.state.status, ARNStatus.USER_ELIMINATED_ALL)

    def test_cost_ceiling_boundary_transitions_to_genuine_exhausted(self):
        engine = ARNEngine(cost_ceiling=CostCeiling(max_searches=2))
        engine.trigger_recovery("find rule", "first", [])
        self.assertEqual(engine.state.status, ARNStatus.ACTIVE)
        self.assertTrue(engine.record_source_checked("files", "second", []))
        self.assertFalse(engine.check_budget())
        self.assertEqual(engine.state.status, ARNStatus.EXHAUSTED)
        self.assertEqual(engine.state.termination_reason, "cost_ceiling_reached")

    def test_operates_without_graphify_files(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                engine = ARNEngine()
                state = engine.trigger_recovery("find rule", "rule", [])
                self.assertEqual(state.status, ARNStatus.ACTIVE)
                self.assertNotIn("graphify", json.dumps(state.to_dict()).lower())
            finally:
                os.chdir(old_cwd)

    def test_structured_clarification_has_no_question_text(self):
        engine = ARNEngine()
        engine.trigger_recovery("find rule", "rule", [])
        engine.add_candidates(
            [
                Candidate("a", metadata={"category": "Faculty"}),
                Candidate("b", metadata={"category": "Project Staff"}),
            ]
        )
        recommendation = engine.get_clarification_recommendation()
        self.assertEqual(recommendation.suggested_axis, "category")
        self.assertEqual(set(recommendation.candidate_groups), {"Faculty", "Project Staff"})
        self.assertNotIn("question", recommendation.to_dict())

    def test_arn_state_attaches_to_turn_state_without_persistence(self):
        state = ARNState(task_goal="find policy")
        result = assemble_turn_state(
            user_text="find policy", session_id="s1", arn_state=state
        )
        self.assertEqual(result.data["arn_state"]["task_goal"], "find policy")


if __name__ == "__main__":
    unittest.main()
