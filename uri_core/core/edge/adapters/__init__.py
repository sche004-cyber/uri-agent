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
from .speech import (
    NeedleAudioClassification,
    build_actual_speech_candidates,
    build_fixture_speech_candidates,
    character_error_rate,
    probe_needle_audio,
    word_error_rate,
)
from .vision import (
    build_actual_vision_candidates,
    build_fixture_vision_candidates,
    field_f1_score,
    vqa_exact_match,
)

__all__ = (
    "VALID_SCORE_SEMANTICS",
    "BenchmarkCandidate",
    "BenchmarkResult",
    "TINY_REASONER_IDS",
    "NeedleAudioClassification",
    "build_actual_speech_candidates",
    "build_actual_vision_candidates",
    "build_candidate_configurations",
    "build_fixture_baseline_candidate",
    "build_fixture_candidate_configurations",
    "build_fixture_speech_candidates",
    "build_fixture_vision_candidates",
    "character_error_rate",
    "field_f1_score",
    "probe_needle_audio",
    "run_benchmark",
    "vqa_exact_match",
    "word_error_rate",
)
