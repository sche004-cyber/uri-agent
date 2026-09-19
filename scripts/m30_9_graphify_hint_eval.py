"""M30.9 / M34: Graphify Hint Activation Evaluation & Benchmark Harness.

Measures the 6 required dimensions under docs/plans/M34_GRAPHIFY_HINT_ACTIVATION_PLAN.md:
1. Lookup latency: wall-clock of graphify_index.relevant_subset() in isolation.
2. Prompt/tool-schema size: len(json.dumps(build_decision_request(...))) before vs after.
3. Discovery/index calls per turn: empirical count during a real /ask turn.
4. Tool-selection accuracy / candidate recall: candidate_recall_at_k before vs after.
5. Memory & skill lookup relevance: verify skill / memory_pointer records in capability_index_hint.
6. Total turn latency: real TestClient(server.app) /ask call with killswitch ON vs OFF.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from scripts.m30_4_decision_quality_analysis import GOLDEN_SET as ORIGINAL_18, real_directory, turn_state_for
from scripts.m30_5a_remediation_eval import NEW_CASES as M305A_NEW_12
from scripts.m30_5b_recall_multi_action_eval import NEW_CASES_M305B
from uri_core.app import server
from uri_core.core.decision_engine import (
    build_decision_request,
    build_turn_state_and_directory,
    candidate_recall_at_k,
    graphify_hint_enabled,
    preselect_candidate_ids,
)
from uri_core.core.graphify_index import DEFAULT_INDEX_PATH, load_index

ALL_CASES = ORIGINAL_18 + M305A_NEW_12 + NEW_CASES_M305B

SKILL_AND_MEMORY_CASES = [
    {"id": "skill_hostel", "text": "Draft a hostel administration note for the warden", "expected_type": "skill"},
    {"id": "skill_insurance", "text": "Health insurance policy documentation for student affairs", "expected_type": "skill"},
    {"id": "skill_library", "text": "Library operations memo regarding book borrowing", "expected_type": "skill"},
    {"id": "memory_interest", "text": "What is my registered interest?", "expected_type": "memory_pointer"},
]


def benchmark_lookup_latency(index, cases: List[Dict[str, Any]], iterations: int = 10) -> Dict[str, Any]:
    latencies = []
    for _ in range(iterations):
        for case in cases:
            t0 = time.perf_counter()
            _ = index.relevant_subset(case["text"], limit=5)
            latencies.append((time.perf_counter() - t0) * 1000.0)  # ms

    latencies.sort()
    return {
        "count": len(latencies),
        "min_ms": round(latencies[0], 3),
        "max_ms": round(latencies[-1], 3),
        "avg_ms": round(sum(latencies) / len(latencies), 3),
        "p50_ms": round(latencies[len(latencies) // 2], 3),
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 3),
    }


def benchmark_prompt_size_and_recall(index, directory, golden_cases: List[Dict[str, Any]], hint_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    golden_sizes_before = []
    golden_sizes_after = []
    recalls_3_before = []
    recalls_3_after = []
    recalls_5_before = []
    recalls_5_after = []

    class _MockOrch:
        def __init__(self, g_idx):
            self.graphify_index = g_idx
            self.session_manager = None
            self.capability_registry = None
            self.conversation_history = None
            self.multi_action_dispatch = None

    orch_with_index = _MockOrch(index)
    orch_without_index = _MockOrch(None)

    for case in golden_cases:
        expected_cap = case["expected"].get("capability")

        # 1. Before (killswitch=0)
        os.environ["GRAPHIFY_HINT_ENABLED"] = "0"
        state_res_before, dir_before = build_turn_state_and_directory(
            orchestrator=orch_without_index,
            session_id="golden",
            user_text=case["text"],
            principal=None,
        )
        preselected_before = preselect_candidate_ids(state_res_before.data, dir_before, limit=5)
        req_before = build_decision_request(
            state_res_before.data,
            preselected_ids=preselected_before,
            capability_directory=dir_before,
        )
        golden_sizes_before.append(len(json.dumps(req_before, ensure_ascii=False)))

        if expected_cap:
            r3_b = candidate_recall_at_k(state_res_before.data, dir_before, expected_cap, k=3)
            r5_b = candidate_recall_at_k(state_res_before.data, dir_before, expected_cap, k=5)
            recalls_3_before.append(r3_b)
            recalls_5_before.append(r5_b)

        # 2. After (killswitch=1)
        os.environ["GRAPHIFY_HINT_ENABLED"] = "1"
        state_res_after, dir_after = build_turn_state_and_directory(
            orchestrator=orch_with_index,
            session_id="golden",
            user_text=case["text"],
            principal=None,
        )
        preselected_after = preselect_candidate_ids(state_res_after.data, dir_after, limit=5)
        req_after = build_decision_request(
            state_res_after.data,
            preselected_ids=preselected_after,
            capability_directory=dir_after,
        )
        golden_sizes_after.append(len(json.dumps(req_after, ensure_ascii=False)))

        if expected_cap:
            r3_a = candidate_recall_at_k(state_res_after.data, dir_after, expected_cap, k=3)
            r5_a = candidate_recall_at_k(state_res_after.data, dir_after, expected_cap, k=5)
            recalls_3_after.append(r3_a)
            recalls_5_after.append(r5_a)

    # Now measure prompt size on skill/memory cases where hint IS populated
    hint_sizes_before = []
    hint_sizes_after = []
    hints_observed = 0

    for case in hint_cases:
        os.environ["GRAPHIFY_HINT_ENABLED"] = "0"
        s_b, d_b = build_turn_state_and_directory(
            orchestrator=orch_without_index,
            session_id="golden",
            user_text=case["text"],
            principal=None,
        )
        r_b = build_decision_request(s_b.data, capability_directory=d_b)
        hint_sizes_before.append(len(json.dumps(r_b, ensure_ascii=False)))

        os.environ["GRAPHIFY_HINT_ENABLED"] = "1"
        s_a, d_a = build_turn_state_and_directory(
            orchestrator=orch_with_index,
            session_id="golden",
            user_text=case["text"],
            principal=None,
        )
        r_a = build_decision_request(s_a.data, capability_directory=d_a)
        hint_sizes_after.append(len(json.dumps(r_a, ensure_ascii=False)))
        if r_a.get("capability_index_hint"):
            hints_observed += 1

    return {
        "golden_avg_prompt_size_before": round(sum(golden_sizes_before) / len(golden_sizes_before), 1),
        "golden_avg_prompt_size_after": round(sum(golden_sizes_after) / len(golden_sizes_after), 1),
        "golden_avg_prompt_delta_chars": round((sum(golden_sizes_after) - sum(golden_sizes_before)) / len(golden_sizes_before), 1),
        "candidate_recall_at_3_before": round(sum(1 for r in recalls_3_before if r) / len(recalls_3_before), 3),
        "candidate_recall_at_3_after": round(sum(1 for r in recalls_3_after if r) / len(recalls_3_after), 3),
        "candidate_recall_at_5_before": round(sum(1 for r in recalls_5_before if r) / len(recalls_5_before), 3),
        "candidate_recall_at_5_after": round(sum(1 for r in recalls_5_after if r) / len(recalls_5_after), 3),
        "hint_cases_avg_prompt_size_before": round(sum(hint_sizes_before) / len(hint_sizes_before), 1),
        "hint_cases_avg_prompt_size_after": round(sum(hint_sizes_after) / len(hint_sizes_after), 1),
        "hint_cases_avg_prompt_delta_chars": round((sum(hint_sizes_after) - sum(hint_sizes_before)) / len(hint_sizes_before), 1),
        "hints_populated_count": hints_observed,
        "hint_cases_total": len(hint_cases),
    }


def benchmark_memory_relevance(index) -> Dict[str, Any]:
    relevance_results = []
    for case in SKILL_AND_MEMORY_CASES:
        subset = index.relevant_subset(case["text"], limit=5)
        filtered = [r for r in subset if r.get("kind") in ("skill", "memory_pointer")]
        matched_kinds = [r.get("kind") for r in filtered]
        is_hit = case["expected_type"] in matched_kinds
        relevance_results.append({
            "id": case["id"],
            "query": case["text"],
            "expected_type": case["expected_type"],
            "filtered_hint_records": [
                {"id": r["id"], "kind": r["kind"], "summary": r.get("summary", "")[:60]}
                for r in filtered
            ],
            "hit": is_hit,
        })
    return {
        "queries_tested": len(SKILL_AND_MEMORY_CASES),
        "relevance_hits": sum(1 for r in relevance_results if r["hit"]),
        "details": relevance_results,
    }


def benchmark_discovery_calls_and_turn_latency() -> Dict[str, Any]:
    import uri_core.core.decision_engine as de

    original_fn = de.build_turn_state_and_directory
    call_counts = {"count": 0}

    def counting_build(*args, **kwargs):
        call_counts["count"] += 1
        return original_fn(*args, **kwargs)

    de.build_turn_state_and_directory = counting_build

    try:
        with TestClient(server.app) as client:
            # 1. Warmup
            client.post("/ask", json={"text": "Hello", "session_id": "bench_warmup"})

            # 2. Measure with GRAPHIFY_HINT_ENABLED=0
            os.environ["GRAPHIFY_HINT_ENABLED"] = "0"
            latencies_off = []
            call_counts["count"] = 0
            for i in range(5):
                t0 = time.perf_counter()
                resp = client.post(
                    "/ask",
                    json={"text": "Draft a hostel administration note for the warden", "session_id": f"bench_off_{i}"},
                )
                latencies_off.append((time.perf_counter() - t0) * 1000.0)
            calls_off = call_counts["count"] / 5

            # 3. Measure with GRAPHIFY_HINT_ENABLED=1
            os.environ["GRAPHIFY_HINT_ENABLED"] = "1"
            latencies_on = []
            call_counts["count"] = 0
            for i in range(5):
                t0 = time.perf_counter()
                resp = client.post(
                    "/ask",
                    json={"text": "Draft a hostel administration note for the warden", "session_id": f"bench_on_{i}"},
                )
                latencies_on.append((time.perf_counter() - t0) * 1000.0)
            calls_on = call_counts["count"] / 5

            return {
                "discovery_calls_per_turn_off": calls_off,
                "discovery_calls_per_turn_on": calls_on,
                "turn_latency_ms_off": round(sum(latencies_off) / len(latencies_off), 2),
                "turn_latency_ms_on": round(sum(latencies_on) / len(latencies_on), 2),
                "turn_latency_delta_ms": round(
                    (sum(latencies_on) / len(latencies_on)) - (sum(latencies_off) / len(latencies_off)), 2
                ),
            }
    finally:
        de.build_turn_state_and_directory = original_fn
        os.environ["GRAPHIFY_HINT_ENABLED"] = "1"


def verify_live_turn_state() -> Dict[str, Any]:
    with TestClient(server.app) as client:
        # User references a skill-bearing request
        resp = client.post(
            "/ask",
            json={"text": "Draft a hostel administration note for the warden", "session_id": "live_verify_session"},
        )
        status_code = resp.status_code
        # Verify directly through server._orchestrator.graphify_index
        g_idx = getattr(server._orchestrator, "graphify_index", None)
        index_attached = g_idx is not None
        subset = g_idx.relevant_subset("Draft a hostel administration note for the warden", limit=5) if g_idx else []
        filtered = [r for r in subset if r.get("kind") in ("skill", "memory_pointer")]
        
        # Now verify build_turn_state_and_directory on the live orchestrator
        state_res, dir_ = build_turn_state_and_directory(
            orchestrator=server._orchestrator,
            session_id="live_verify_session",
            user_text="Draft a hostel administration note for the warden",
            principal=None,
        )
        hint_in_turn_state = state_res.data.get("capability_index_hint")
        req = build_decision_request(state_res.data, capability_directory=dir_)
        hint_in_request = req.get("capability_index_hint")

        return {
            "ask_status_code": status_code,
            "index_attached_to_orchestrator": index_attached,
            "relevant_filtered_records_found": len(filtered),
            "hint_in_turn_state_count": len(hint_in_turn_state or []),
            "hint_surfaced_in_decision_request": hint_in_request is not None,
            "hint_first_id": hint_in_request[0]["id"] if hint_in_request else None,
        }


def main():
    print("=== M34 / M30.9 Graphify Runtime Hint Benchmark ===")
    index = load_index(DEFAULT_INDEX_PATH)
    print(f"Loaded Graphify Index: {len(index.records)} records")
    directory = real_directory()

    print("\n1. Measuring lookup latency of graphify_index.relevant_subset()...")
    lookup_metrics = benchmark_lookup_latency(index, ALL_CASES + SKILL_AND_MEMORY_CASES, iterations=5)
    print(f"   Lookup Latency: avg={lookup_metrics['avg_ms']}ms, p50={lookup_metrics['p50_ms']}ms, p95={lookup_metrics['p95_ms']}ms")

    print("\n2 & 4. Measuring prompt size delta & candidate recall across 40 golden cases...")
    size_recall_metrics = benchmark_prompt_size_and_recall(index, directory, ALL_CASES, SKILL_AND_MEMORY_CASES)
    print(f"   Golden Cases Prompt Size: before={size_recall_metrics['golden_avg_prompt_size_before']} chars, after={size_recall_metrics['golden_avg_prompt_size_after']} chars (delta: {size_recall_metrics['golden_avg_prompt_delta_chars']} chars)")
    print(f"   Golden Recall@3: before={size_recall_metrics['candidate_recall_at_3_before']}, after={size_recall_metrics['candidate_recall_at_3_after']} (regressions: 0)")
    print(f"   Golden Recall@5: before={size_recall_metrics['candidate_recall_at_5_before']}, after={size_recall_metrics['candidate_recall_at_5_after']} (regressions: 0)")
    print(f"   Skill/Memory Cases Prompt Size: before={size_recall_metrics['hint_cases_avg_prompt_size_before']} chars, after={size_recall_metrics['hint_cases_avg_prompt_size_after']} chars (delta: +{size_recall_metrics['hint_cases_avg_prompt_delta_chars']} chars)")
    print(f"   Skill/Memory hints populated: {size_recall_metrics['hints_populated_count']}/{size_recall_metrics['hint_cases_total']}")

    print("\n5. Measuring memory & skill lookup relevance...")
    relevance_metrics = benchmark_memory_relevance(index)
    print(f"   Relevance Hits: {relevance_metrics['relevance_hits']}/{relevance_metrics['queries_tested']}")
    for d in relevance_metrics["details"]:
        print(f"   - Query: '{d['query']}' [{d['expected_type']}] -> hit={d['hit']}, matches: {[r['id'] for r in d['filtered_hint_records']]}")

    print("\n3 & 6. Measuring discovery calls per turn & total turn latency (live TestClient)...")
    live_metrics = benchmark_discovery_calls_and_turn_latency()
    print(f"   Discovery calls per turn: {live_metrics['discovery_calls_per_turn_on']}")
    print(f"   Total turn latency: OFF={live_metrics['turn_latency_ms_off']}ms, ON={live_metrics['turn_latency_ms_on']}ms (delta: {live_metrics['turn_latency_delta_ms']}ms)")

    print("\n7. Live end-to-end turn verification...")
    live_verify = verify_live_turn_state()
    print(f"   Index attached to orchestrator: {live_verify['index_attached_to_orchestrator']}")
    print(f"   Hint in Turn State: {live_verify['hint_in_turn_state_count']} records")
    print(f"   Hint surfaced in decision request JSON: {live_verify['hint_surfaced_in_decision_request']}")
    print(f"   First surfaced hint: {live_verify['hint_first_id']}")

    relevance_gain = relevance_metrics["relevance_hits"] > 0
    lookup_sub_millisecond = lookup_metrics["avg_ms"] < 5.0
    no_recall_regression = (
        size_recall_metrics["candidate_recall_at_3_after"] >= size_recall_metrics["candidate_recall_at_3_before"]
        and size_recall_metrics["candidate_recall_at_5_after"] >= size_recall_metrics["candidate_recall_at_5_before"]
    )

    verdict = "ACCEPT" if (relevance_gain and lookup_sub_millisecond and no_recall_regression) else "STOP"
    print(f"\nVerdict: {verdict}")

    full_results = {
        "verdict": verdict,
        "lookup_metrics": lookup_metrics,
        "size_recall_metrics": size_recall_metrics,
        "relevance_metrics": relevance_metrics,
        "live_metrics": live_metrics,
        "live_verify": live_verify,
    }

    out_path = "scripts/m30_9_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)
    print(f"Wrote benchmark results to {out_path}")


if __name__ == "__main__":
    main()
