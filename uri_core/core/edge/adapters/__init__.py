"""Experimental, proposal-only candidates; never imported by production routing."""

from .benchmark import (
    VALID_SCORE_SEMANTICS,
    BenchmarkCandidate,
    BenchmarkResult,
    run_benchmark,
)
from .ensemble import (
    TINY_REASONER_IDS,
    build_candidate_configurations,
    build_fixture_baseline_candidate,
    build_fixture_candidate_configurations,
)

__all__ = (
    "VALID_SCORE_SEMANTICS",
    "BenchmarkCandidate",
    "BenchmarkResult",
    "TINY_REASONER_IDS",
    "build_candidate_configurations",
    "build_fixture_baseline_candidate",
    "build_fixture_candidate_configurations",
    "run_benchmark",
)
