"""M33.3-R S8: route-performance store and qualified-route preference (offline only)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from uri_v1.evaluation.route_performance import (PreferenceConfig, RouteKey, RoutePerformanceRecord,
                                                 RoutePerformanceStore, choose_route)

USER = str(uuid.UUID(int=8))
NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)
TEMPLATE = RouteKey("EXPLAIN", "DETERMINISTIC", "template", "v1")
EDGE = RouteKey("EXPLAIN", "EDGE", "qwen3.5-2b", "v1")
UNQUALIFIED = RouteKey("EXPLAIN", "EDGE", "lfm2.5-350m", "v1")


def rec(route, outcome="SUCCESS", feedback="none", days=0.0, latency=100.0):
    return RoutePerformanceRecord(route, outcome, feedback, latency,
                                  (NOW - timedelta(days=days)).isoformat().replace("+00:00", "Z"))


def test_fixed_default_without_enough_evidence_and_when_off():
    records = [rec(EDGE)] * 3
    assert choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], records, now=NOW)[0] == TEMPLATE
    many = [rec(TEMPLATE, "FALLBACK")] * 10 + [rec(EDGE)] * 10
    assert choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], many, now=NOW)[0] == EDGE
    route, why = choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], many, now=NOW, learning_enabled=False)
    assert route == TEMPLATE and why["reason"] == "learning_off"


def test_never_selects_unqualified_route_regardless_of_evidence():
    records = [rec(UNQUALIFIED)] * 100 + [rec(TEMPLATE, "FAILURE")] * 10
    route, why = choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], records, now=NOW)
    assert route != UNQUALIFIED and UNQUALIFIED.route_id not in why["scores"]
    with pytest.raises(ValueError):
        choose_route("EXPLAIN", UNQUALIFIED, [TEMPLATE, EDGE], records, now=NOW)


def test_version_change_invalidates_evidence():
    records = [rec(TEMPLATE, "FALLBACK")] * 10 + [rec(EDGE)] * 10
    edge_v2 = RouteKey("EXPLAIN", "EDGE", "qwen3.5-2b", "v2")
    route, why = choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, edge_v2], records, now=NOW)
    assert route == TEMPLATE and why["scores"][edge_v2.route_id]["evidence"] == 0


def test_negative_feedback_weighs_more_and_decays():
    good = [rec(TEMPLATE, "FALLBACK")] * 10 + [rec(EDGE)] * 10
    corrected = good + [rec(EDGE, "CORRECTED", "negative")] * 6
    assert choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], corrected, now=NOW)[0] == TEMPLATE
    old_negatives = good + [rec(EDGE, "CORRECTED", "negative", days=120)] * 6
    assert choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], old_negatives, now=NOW)[0] == EDGE
    one_bad = good + [rec(EDGE, "FAILURE", "negative")]
    assert choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], one_bad, now=NOW)[0] == EDGE  # one item never flips permanently


def test_latency_penalty_from_config():
    records = [rec(TEMPLATE, "FALLBACK", latency=1)] * 10 + [rec(EDGE, latency=3000)] * 10
    cfg = PreferenceConfig(latency_penalty_per_s=0.3)
    assert choose_route("EXPLAIN", TEMPLATE, [TEMPLATE, EDGE], records, now=NOW, config=cfg)[0] == TEMPLATE


def test_store_on_off_reset_and_strict_records(tmp_path):
    store = RoutePerformanceStore(USER, root=str(tmp_path))
    assert store.enabled() and store.record(rec(EDGE))
    store.set_enabled(False)
    assert store.record(rec(EDGE)) is False and len(store.records()) == 1
    store.set_enabled(True)
    store.reset()
    assert store.records() == []
    with pytest.raises(ValueError):
        RoutePerformanceRecord(EDGE, "GREAT", "none", 1.0, NOW.isoformat())
    with pytest.raises(ValueError):
        RouteKey("EXPLAIN", "EDGE", "free text model", "v1")


def test_replay_method_validation_learner_and_ips_on_synthetic_arms():
    from scripts.m33_3_r_s8_replay import method_validation
    result = method_validation(808)
    assert result["label"].startswith("METHOD_VALIDATION_SYNTHETIC")
    assert result["passed"] and result["learner_chose"] == "B"
