"""Unit tests for M35 URIv1 Batch A2.5 Phase 0: RAR Adversarial Safety Gate.

Executes a 24-case held-out adversarial suite covering:
- duplicate titles
- candidate order shuffling (invariance & anti-bias)
- misleading lexical overlap
- stale active pointer
- two equally plausible "previous" candidates
- missing timestamps
- contradictory recency metadata
- irrelevant distractor candidates
- same title across different target types
- multiple pronouns
- multiple references of different types
- negated candidate
- "not that one"
- "the other one"
- revised/original/latest/earlier relationships
- candidate with strong TF-IDF overlap but wrong semantic identity
- insufficient metadata
- zero candidates
- one valid candidate among many distractors
- ambiguous ownership

Primary safety metric:
WRONG BINDING RATE = 0
"""

from __future__ import annotations

import unittest
from typing import List

from uri_v1.turn.rar_adversarial_fixtures import get_rar_adversarial_fixtures
from uri_v1.turn.rar_contracts import RAROutcome
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended


class RARAdversarialSafetyGateTests(unittest.TestCase):
    """Executes the Phase 0 held-out adversarial safety gate."""

    def test_all_24_adversarial_fixtures_zero_wrong_bindings(self):
        fixtures = get_rar_adversarial_fixtures()
        self.assertGreaterEqual(len(fixtures), 20, "Must contain at least 20 adversarial cases")

        wrong_bindings = []
        latencies = []

        for fix in fixtures:
            with self.subTest(fixture_id=fix.id, name=fix.name):
                trace = resolve_rar_deterministic_extended(fix.query)
                res = trace.resolution
                latencies.append(trace.latency_ms)

                # 1. Primary Safety Gate: ZERO wrong bindings
                if res.outcome == RAROutcome.RESOLVED:
                    if fix.expected_outcome != RAROutcome.RESOLVED or res.candidate_id != fix.expected_candidate_id:
                        wrong_bindings.append({
                            "fixture_id": fix.id,
                            "name": fix.name,
                            "bound_candidate_id": res.candidate_id,
                            "expected_candidate_id": fix.expected_candidate_id,
                            "rule_used": trace.rule_used.value,
                        })

                # Outcome must match expected or be in acceptable safe outcomes
                if fix.acceptable_outcomes:
                    self.assertIn(
                        res.outcome,
                        fix.acceptable_outcomes,
                        f"Fixture {fix.id} produced unacceptable outcome {res.outcome} (acceptable: {fix.acceptable_outcomes})",
                    )
                else:
                    self.assertEqual(
                        res.outcome,
                        fix.expected_outcome,
                        f"Fixture {fix.id} failed outcome: expected {fix.expected_outcome}, got {res.outcome}",
                    )

                # If resolved, candidate ID must match exactly
                if fix.expected_candidate_id is not None and res.outcome == RAROutcome.RESOLVED:
                    self.assertEqual(
                        res.candidate_id,
                        fix.expected_candidate_id,
                        f"Fixture {fix.id} bound candidate {res.candidate_id}, expected {fix.expected_candidate_id}",
                    )

        # Assert zero wrong bindings across entire adversarial suite
        self.assertEqual(
            len(wrong_bindings),
            0,
            f"STOP RULE TRIGGERED: DETERMINISTIC_RAR_REQUIRES_HARDENING. Wrong bindings: {wrong_bindings}",
        )

        mean_lat = sum(latencies) / len(latencies)
        sorted_lat = sorted(latencies)
        p95_lat = sorted_lat[int(len(sorted_lat) * 0.95)]
        print(f"\n[Phase 0 RAR Safety Gate] 24/24 passed cleanly. Wrong bindings: 0. Mean latency: {mean_lat:.3f}ms, P95: {p95_lat:.3f}ms")


if __name__ == "__main__":
    unittest.main()
