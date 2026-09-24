"""M35 URIv1 -- A2.8L: unit/mechanism tests for the RAR attachment-order
evidence transport factorial. Run before the full battery (plan §14 step 5).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from uri_v1.turn.rar_contracts import RARCandidate, RAREvidence, RAROutcome, RARQuery
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended
from uri_v1.turn.rar_l5_experimental import resolve_rar_l5_experimental
from uri_v1.turn.rar_l5_diagnostic_fixtures import get_l5_diagnostic_fixtures
from uri_v1.turn.rar_attachment_order_experimental import (
    AttachmentOrderOverlay,
    PROVENANCE_CURRENT_TURN_SEQUENCE,
    PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
    PROVENANCE_UNKNOWN,
    compile_and_resolve_via_existing_contract,
    resolve_rar_attachment_order_experimental,
)
from uri_v1.turn.rar_attachment_order_factorial_fixtures import get_factorial_cases


def _c(cid, title, rank=0, is_att=True):
    return RARCandidate(id=cid, title=title, candidate_type="document", recency_rank=rank, is_attachment=is_att)


class TestFlagOffEquivalence(unittest.TestCase):
    """Plan §3/§9.8: with every A2.8L flag off, the experimental resolver
    must be decision-identical to the accepted A2.8K H3-only mechanism
    (verified equivalence baseline; NOT raw baseline -- see module docstring
    disclosure for why H3 is the correct flag-off reference)."""

    def test_sd_battery_flag_off_matches_h3_only(self):
        for fix in get_l5_diagnostic_fixtures():
            with self.subTest(fixture=fix.id):
                h3_only = resolve_rar_l5_experimental(fix.query, h3=True)
                exp = resolve_rar_attachment_order_experimental(fix.query, AttachmentOrderOverlay())
                self.assertEqual(
                    (h3_only.resolution.outcome, h3_only.resolution.candidate_id,
                     frozenset(h3_only.resolution.ambiguous_candidate_ids)),
                    (exp.resolution.outcome, exp.resolution.candidate_id,
                     frozenset(exp.resolution.ambiguous_candidate_ids)),
                )


class TestCausalTargets(unittest.TestCase):
    """Plan §5.1: the seven causal targets must resolve exactly as frozen
    under the discovered minimal sufficient set (M=G=P=D=R=True, Q=False)."""

    WINNING_FLAGS = dict(m=True, g=True, p=True, d=True, r=True, q=False)

    def test_all_causal_targets_resolve_correctly_under_winning_cell(self):
        for case in get_factorial_cases():
            if not case.is_causal_target:
                continue
            with self.subTest(case=case.id):
                trace = resolve_rar_attachment_order_experimental(case.query, case.overlay, **self.WINNING_FLAGS)
                if case.expected_outcome == RAROutcome.RESOLVED:
                    self.assertEqual(trace.resolution.outcome, RAROutcome.RESOLVED)
                    self.assertEqual(trace.resolution.candidate_id, case.expected_candidate_id)
                else:
                    self.assertEqual(trace.resolution.outcome, RAROutcome.AMBIGUOUS)
                    self.assertEqual(
                        frozenset(trace.resolution.ambiguous_candidate_ids),
                        frozenset(case.expected_ambiguous_candidate_ids),
                    )

    def test_reachable_controls_pass_under_winning_cell(self):
        for case in get_factorial_cases():
            if case.is_causal_target or not case.reachable_by_factors:
                continue
            with self.subTest(case=case.id):
                trace = resolve_rar_attachment_order_experimental(case.query, case.overlay, **self.WINNING_FLAGS)
                if case.expected_outcome == RAROutcome.RESOLVED:
                    self.assertEqual(trace.resolution.candidate_id, case.expected_candidate_id)
                elif case.expected_outcome == RAROutcome.AMBIGUOUS:
                    self.assertEqual(
                        frozenset(trace.resolution.ambiguous_candidate_ids),
                        frozenset(case.expected_ambiguous_candidate_ids),
                    )
                else:
                    self.assertNotEqual(trace.resolution.outcome, RAROutcome.RESOLVED)

    def test_c_lexical_attachment_is_disclosed_unreachable(self):
        """Documents the disclosed structural exception rather than hiding
        it: this control fails under EVERY configuration, including
        all-on, because none of the six factors touch Level 5.5's
        `is_attachment` counting."""
        case = next(c for c in get_factorial_cases() if c.id == "C-LEXICAL-ATTACHMENT")
        self.assertFalse(case.reachable_by_factors)
        for flags in (
            dict(m=False, g=False, p=False, d=False, r=False, q=False),
            dict(m=True, g=True, p=True, d=True, r=True, q=True),
        ):
            trace = resolve_rar_attachment_order_experimental(case.query, case.overlay, **flags)
            self.assertEqual(trace.resolution.outcome, RAROutcome.AMBIGUOUS)


class TestFactorNecessity(unittest.TestCase):
    """Plan §7: ablating any one of M/G/P/D/R from the minimal sufficient
    cell must cause at least one frozen target to fail; toggling Q on must
    also cause a failure (HQ's destructive interaction)."""

    BASE = dict(m=True, g=True, p=True, d=True, r=True, q=False)

    def _cell_fails_some_causal_target(self, flags) -> bool:
        for case in get_factorial_cases():
            if not case.is_causal_target:
                continue
            trace = resolve_rar_attachment_order_experimental(case.query, case.overlay, **flags)
            if case.expected_outcome == RAROutcome.RESOLVED:
                if not (trace.resolution.outcome == RAROutcome.RESOLVED and
                        trace.resolution.candidate_id == case.expected_candidate_id):
                    return True
            else:
                if not (trace.resolution.outcome == RAROutcome.AMBIGUOUS and
                        frozenset(trace.resolution.ambiguous_candidate_ids) == frozenset(case.expected_ambiguous_candidate_ids)):
                    return True
        return False

    def test_ablating_each_necessary_factor_breaks_a_causal_target(self):
        for factor in ("m", "g", "p", "d", "r"):
            with self.subTest(factor=factor):
                flags = dict(self.BASE)
                flags[factor] = False
                self.assertTrue(self._cell_fails_some_causal_target(flags))

    def test_enabling_q_breaks_case_a_ordering(self):
        flags = dict(self.BASE)
        flags["q"] = True
        self.assertTrue(self._cell_fails_some_causal_target(flags))


class TestExistingContractCompiler(unittest.TestCase):
    """Plan §4.2.1: the compiler must never invent a candidate outside the
    original supplied universe, and must be a pure passthrough when the A3
    ordinal trigger does not match."""

    def test_compiler_never_invents_a_candidate(self):
        for case in get_factorial_cases():
            with self.subTest(case=case.id):
                trace, diag = compile_and_resolve_via_existing_contract(
                    case.query, case.overlay, m=True, r=True,
                )
                universe = {c.id for c in case.query.candidates}
                bound = set()
                if trace.resolution.candidate_id:
                    bound.add(trace.resolution.candidate_id)
                bound.update(trace.resolution.ambiguous_candidate_ids)
                self.assertTrue(bound.issubset(universe))

    def test_compiler_passthrough_for_non_ordinal_query(self):
        a = _c("a", "Photo_1.jpg")
        b = _c("b", "Photo_2.jpg")
        q = RARQuery("the attachment", (a, b), RAREvidence())
        trace, diag = compile_and_resolve_via_existing_contract(q, AttachmentOrderOverlay(), m=True, r=True)
        baseline = resolve_rar_deterministic_extended(q)
        self.assertEqual(trace.resolution.outcome, baseline.resolution.outcome)
        self.assertEqual(diag["steps"][1]["action"], "PASSTHROUGH_UNMODIFIED")


class TestProvenanceMinimalPair(unittest.TestCase):
    """Plan §5.1: A-LATEST-2 and B-LATEST-PROVENANCE-TWIN must be
    byte-identical except for provenance, and must produce OPPOSITE
    outcomes under the winning cell."""

    def test_minimal_pair_differs_only_by_outcome(self):
        cases = {c.id: c for c in get_factorial_cases()}
        a = cases["A-LATEST-2"]
        b = cases["B-LATEST-PROVENANCE-TWIN"]
        self.assertEqual(
            [(c.id, c.title, c.recency_rank, c.is_attachment) for c in a.query.candidates],
            [(c.id, c.title, c.recency_rank, c.is_attachment) for c in b.query.candidates],
        )
        self.assertEqual(a.overlay.turn_membership_ids, b.overlay.turn_membership_ids)
        self.assertEqual(a.overlay.event_group_by_id, b.overlay.event_group_by_id)
        self.assertNotEqual(a.overlay.provenance, b.overlay.provenance)

        flags = dict(m=True, g=True, p=True, d=True, r=True, q=False)
        trace_a = resolve_rar_attachment_order_experimental(a.query, a.overlay, **flags)
        trace_b = resolve_rar_attachment_order_experimental(b.query, b.overlay, **flags)
        self.assertEqual(trace_a.resolution.outcome, RAROutcome.RESOLVED)
        self.assertEqual(trace_b.resolution.outcome, RAROutcome.AMBIGUOUS)


class TestDeterminism(unittest.TestCase):
    def test_repeated_calls_are_decision_identical(self):
        flags = dict(m=True, g=True, p=True, d=True, r=True, q=False)
        for case in get_factorial_cases():
            with self.subTest(case=case.id):
                results = [
                    resolve_rar_attachment_order_experimental(case.query, case.overlay, **flags).resolution
                    for _ in range(5)
                ]
                tuples = {(r.outcome, r.candidate_id, frozenset(r.ambiguous_candidate_ids)) for r in results}
                self.assertEqual(len(tuples), 1)


if __name__ == "__main__":
    unittest.main()
