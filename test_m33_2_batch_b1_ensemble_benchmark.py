import ast
import json
import math
from pathlib import Path

import pytest

from uri_core.core.edge.adapters import benchmark
from uri_core.core.edge.adapters.benchmark import (
    CANONICAL_TIERS,
    VALID_SCORE_SEMANTICS,
    BenchmarkCandidate,
    _metrics,
    run_benchmark,
)
from uri_core.core.edge.adapters.ensemble import (
    build_candidate_configurations,
    build_fixture_baseline_candidate,
    build_fixture_candidate_configurations,
)


CORPUS_PATH = Path("fixtures/m33_2_edge_benchmark/corpus.json")


def _corpus():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_binned_ece_mce_and_nll_use_per_bin_accuracy():
    rows = [
        {"score": 0.1, "correct": False},
        {"score": 0.2, "correct": True},
        {"score": 0.8, "correct": True},
        {"score": 0.9, "correct": True},
    ]

    ece, mce, nll = _metrics(rows, bin_count=2)

    assert ece == pytest.approx(0.25)
    assert mce == pytest.approx(0.35)
    expected_nll = -sum(
        math.log(1 - score) if not correct else math.log(score)
        for score, correct in ((0.1, False), (0.2, True), (0.8, True), (0.9, True))
    ) / 4
    assert nll == pytest.approx(expected_nll)


@pytest.mark.parametrize("semantics", sorted(VALID_SCORE_SEMANTICS))
def test_canonical_score_semantics_are_enumerated(semantics):
    candidate = BenchmarkCandidate(
        "canonical", "fixture", semantics, "test", invoke=lambda item: {"answer": "4"}
    )
    result = run_benchmark(
        candidate,
        [{"tier": "deterministic", "expected": "4", "offered_capabilities": []}],
    )
    assert result.runtime_status == "available"


@pytest.mark.parametrize("score", [-0.01, 1.01, float("nan"), True, None])
def test_probability_scores_outside_canonical_range_are_rejected(score):
    candidate = BenchmarkCandidate(
        "bad-range",
        "fixture",
        "probability",
        "test",
        invoke=lambda item: {"answer": item["expected"], "score": score},
    )
    result = run_benchmark(candidate, _corpus())
    assert result.safety == "REJECTED"
    assert result.qualification == "REJECTED"


def test_invalid_semantics_precedes_missing_tier_and_unknown_tier_fails_closed():
    invalid = BenchmarkCandidate("invalid", "fixture", None, "test", invoke=lambda _: {})
    invalid_result = run_benchmark(invalid, [{"expected": "4"}])
    assert invalid_result.qualification == "REJECTED"
    assert invalid_result.runtime_detail == "invalid score_semantics"

    canonical = BenchmarkCandidate(
        "canonical", "fixture", "none", "test", invoke=lambda _: {}
    )
    tier_result = run_benchmark(canonical, [{"expected": "4"}])
    assert tier_result.safety == "REJECTED"
    assert tier_result.qualification == "REJECTED"
    assert "non-canonical corpus tier" in tier_result.runtime_detail


def test_all_five_tiers_and_tier_metrics_are_calculated():
    corpus = _corpus()
    assert {item["tier"] for item in corpus} == CANONICAL_TIERS
    assert all(sum(item["tier"] == tier for item in corpus) >= 4 for tier in CANONICAL_TIERS)

    result = run_benchmark(build_fixture_baseline_candidate(), corpus)
    assert result.correctness == 1.0
    assert result.reflex_accuracy == 1.0
    assert result.bounded_reasoning_accuracy == 1.0
    assert result.language_rubric_score == 1.0
    assert result.escalation_rate == 1.0
    assert result.false_escalation_rate == 0.0
    assert result.qualification == "QUALIFIED_FOR_COMPARISON"


def test_resource_instrumentation_tracks_rss_load_latency_and_unavailable_gpu_ttft(
    monkeypatch,
):
    rss_values = iter((100.0, 125.0, 130.0))
    clock_values = iter((1.0, 1.025, 2.0, 2.010))
    monkeypatch.setattr(benchmark, "_rss_mb", lambda process: next(rss_values))
    monkeypatch.setattr(benchmark.time, "perf_counter", lambda: next(clock_values))
    monkeypatch.setattr(
        benchmark, "_gpu_resource", lambda: {"gpu": "unavailable", "vram_mb": "unavailable"}
    )
    candidate = BenchmarkCandidate(
        "instrumented",
        "fixture",
        "probability",
        "test",
        load=lambda: None,
        invoke=lambda item: {"answer": item["expected"], "score": 0.9},
    )

    result = run_benchmark(
        candidate,
        [{"tier": "reflex", "expected": "ok", "offered_capabilities": []}],
    )

    assert result.resource["rss_before_load_mb"] == 100.0
    assert result.resource["rss_after_load_mb"] == 125.0
    assert result.resource["rss_load_delta_mb"] == 25.0
    assert result.resource["rss_benchmark_delta_mb"] == 5.0
    assert result.resource["load_time_ms"] == pytest.approx(25.0)
    assert result.p50_ms == pytest.approx(10.0)
    assert result.resource["gpu"] == "unavailable"
    assert result.resource["vram_mb"] == "unavailable"
    assert result.resource["ttft_ms"] == "unavailable"


def test_configurations_truthfully_report_missing_models_and_fixtures_compare():
    actual = build_candidate_configurations()
    fixtures = build_fixture_candidate_configurations()
    assert set(actual) == {"A", "B", "C", "D"}
    assert set(fixtures) == {"A", "B", "C", "D"}

    for candidate in actual.values():
        result = run_benchmark(candidate, _corpus())
        assert result.runtime_status == "unavailable"
        assert result.qualification == "UNAVAILABLE"
        assert result.runtime_detail

    for candidate in fixtures.values():
        result = run_benchmark(candidate, _corpus())
        assert result.runtime_status == "available"
        assert result.qualification == "QUALIFIED_FOR_COMPARISON"


def test_edge_adapters_have_zero_egress_and_recursive_static_authority_boundary():
    root = Path("uri_core/core/edge")
    forbidden_import_roots = {
        "approval",
        "canonical_execution",
        "capability_registry",
        "dispatcher",
        "multi_action_dispatch",
        "orchestrator",
        "permission_binding",
    }
    forbidden_egress = {"http", "httpx", "requests", "socket", "urllib"}

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports = {node.module.split(".")[0], node.module.split(".")[-1]}
            else:
                continue
            assert imports.isdisjoint(forbidden_import_roots), path
            assert imports.isdisjoint(forbidden_egress), path
