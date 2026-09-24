"""M35 URIv1 -- A2.8K-R1: repair-specific unit tests.

Narrowly scoped to the two bounded defects the independent final audit
(`docs/plans/M35_URIV1_A2_8K_INDEPENDENT_FINAL_AUDIT.md`, verdict
`REPAIR_REQUIRED`) found and this repair fixes:

- R1-B: `scripts/m35_a2_8k_l5_battery.py`'s `compute_aggregates` changed-row
  comparator must derive from the full decision (outcome, candidate id,
  ambiguous-id set), not a narrowed `(scoring_class, candidate_id)` pair
  that can silently miss an `AMBIGUOUS -> UNKNOWN` transition (audit §6,
  §18, §22.3).

R1-A (H3 filtered-domain ordinal ranking, in `rar_l5_experimental.py`) is
covered by `tests/test_m35_uriv1_a2_8k_l5_experimental.py::H3MechanismTests`
(dedicated mechanism tests added by this same repair); this module does not
duplicate those.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from m35_a2_8k_l5_battery import _decision_tuple, compute_aggregates  # noqa: E402


def _telemetry_row(surface, case_id, ref_key, c_axis, variant, outcome, candidate_id,
                    ambiguous_ids=(), scoring_class="CORRECT_ABSTENTION"):
    return {
        "surface": surface, "case_id": case_id, "ref_key": ref_key, "c_axis": c_axis,
        "variant": variant, "actual_outcome": outcome, "actual_candidate_id": candidate_id,
        "actual_ambiguous_ids": list(ambiguous_ids), "scoring_class": scoring_class,
        "level": None,
    }


class DecisionTupleTests(unittest.TestCase):
    def test_ambiguous_ids_compared_as_a_set_not_a_sequence(self):
        a = _telemetry_row("S-D", "X", "r1", "SD", "H0", "AMBIGUOUS", None, ("b", "a"))
        b = _telemetry_row("S-D", "X", "r1", "SD", "H3", "AMBIGUOUS", None, ("a", "b"))
        self.assertEqual(_decision_tuple(a), _decision_tuple(b))

    def test_outcome_change_with_same_none_candidate_is_a_different_decision(self):
        """The exact class of defect the independent audit found: outcome
        changes from AMBIGUOUS to UNKNOWN, candidate_id stays None in both
        -- this MUST register as a changed decision."""
        h0 = _telemetry_row("S-A", "NB-X", "r1", "C1", "H0", "AMBIGUOUS", None, ("a", "b"),
                             scoring_class="MISSED_RESOLVABLE_CASE")
        h3 = _telemetry_row("S-A", "NB-X", "r1", "C1", "H3", "UNKNOWN", None, (),
                             scoring_class="MISSED_RESOLVABLE_CASE")
        self.assertEqual(h0["scoring_class"], h3["scoring_class"])  # same coarse class
        self.assertEqual(h0["actual_candidate_id"], h3["actual_candidate_id"])  # both None
        self.assertNotEqual(_decision_tuple(h0), _decision_tuple(h3))  # but a real decision change


class ComputeAggregatesFullAccountingTests(unittest.TestCase):
    """Builds a small synthetic telemetry set that reproduces the exact
    defect shape the audit found (same scoring_class + candidate_id, but a
    different outcome/ambiguous-set), and asserts the repaired comparator
    counts it."""

    def _telemetry(self, h0_row, h3_row):
        return {
            "records": [h0_row, h3_row],
            "se_records": [],
        }

    def test_ambiguous_to_unknown_transition_is_counted(self):
        h0 = _telemetry_row("S-A", "NB-X", "r1", "C1", "H0", "AMBIGUOUS", None, ("a", "b"),
                             scoring_class="MISSED_RESOLVABLE_CASE")
        h3 = _telemetry_row("S-A", "NB-X", "r1", "C1", "H3", "UNKNOWN", None, (),
                             scoring_class="MISSED_RESOLVABLE_CASE")
        agg = compute_aggregates(self._telemetry(h0, h3))
        self.assertEqual(len(agg["changed_rows_vs_h0"]["H3"]), 1)
        self.assertFalse(agg["s_a_regression_check_passed"]["H3"])

    def test_true_no_op_row_is_not_counted(self):
        h0 = _telemetry_row("S-A", "NB-Y", "r1", "C1", "H0", "RESOLVED", "cand1",
                             scoring_class="CORRECT_RESOLUTION")
        h3 = _telemetry_row("S-A", "NB-Y", "r1", "C1", "H3", "RESOLVED", "cand1",
                             scoring_class="CORRECT_RESOLUTION")
        agg = compute_aggregates(self._telemetry(h0, h3))
        self.assertEqual(len(agg["changed_rows_vs_h0"]["H3"]), 0)
        self.assertTrue(agg["s_a_regression_check_passed"]["H3"])

    def test_reconciliation_check_matches_raw_scan(self):
        h0 = _telemetry_row("S-A", "NB-X", "r1", "C1", "H0", "AMBIGUOUS", None, ("a", "b"),
                             scoring_class="MISSED_RESOLVABLE_CASE")
        h3 = _telemetry_row("S-A", "NB-X", "r1", "C1", "H3", "UNKNOWN", None, (),
                             scoring_class="MISSED_RESOLVABLE_CASE")
        agg = compute_aggregates(self._telemetry(h0, h3))
        rc = agg["reconciliation_check"]["H3"]
        self.assertEqual(rc["aggregate_changed_row_count"], rc["raw_decision_diff_count"])
        self.assertTrue(rc["reconciled"])

    def test_reconciliation_invariant_holds_across_all_variants_with_mixed_rows(self):
        """aggregate changed-row count == count(raw H0 decision != variant
        decision), for every variant, over a small mixed synthetic set."""
        rows = [
            _telemetry_row("S-D", "R1", "r1", "SD", "H0", "RESOLVED", "x", scoring_class="CORRECT_RESOLUTION"),
            _telemetry_row("S-D", "R1", "r1", "SD", "H1", "RESOLVED", "x", scoring_class="CORRECT_RESOLUTION"),
            _telemetry_row("S-D", "R1", "r1", "SD", "H2", "AMBIGUOUS", None, ("x", "y"), scoring_class="MISSED_RESOLVABLE_CASE"),
            _telemetry_row("S-D", "R2", "r1", "SD", "H0", "AMBIGUOUS", None, ("a", "b"), scoring_class="CORRECT_ABSTENTION"),
            _telemetry_row("S-D", "R2", "r1", "SD", "H1", "UNKNOWN", None, scoring_class="CORRECT_ABSTENTION"),
            _telemetry_row("S-D", "R2", "r1", "SD", "H2", "AMBIGUOUS", None, ("b", "a"), scoring_class="CORRECT_ABSTENTION"),
        ]
        agg = compute_aggregates({"records": rows, "se_records": []})
        for v, rc in agg["reconciliation_check"].items():
            self.assertEqual(rc["aggregate_changed_row_count"], rc["raw_decision_diff_count"], v)
        # R2: H1 differs from H0 (UNKNOWN vs AMBIGUOUS) -> counted.
        self.assertEqual(len(agg["changed_rows_vs_h0"]["H1"]), 1)
        # R2: H2 vs H0 -- same set {a,b} just reordered -> NOT counted.
        self.assertEqual(len(agg["changed_rows_vs_h0"]["H2"]), 1)  # only R1's genuine change


if __name__ == "__main__":
    unittest.main()
