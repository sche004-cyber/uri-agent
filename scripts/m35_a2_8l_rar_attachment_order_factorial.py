"""M35 URIv1 -- A2.8L: RAR Attachment-Order Evidence Transport Factorial.

Benchmark-only. Implements and executes the frozen plan
(`docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md`) and
overlay manifest exactly. See
`uri_v1/turn/rar_attachment_order_experimental.py` module docstring for the
two disclosed interpretive extensions (A3-trigger reading; D/M extended to
Level 5.5) required to make the frozen §5.1 causal targets achievable at
all, and for the one disclosed unreachable control (`C-LEXICAL-ATTACHMENT`).

Runs:
1. The complete 2^6 = 64-cell causal matrix over the 14 frozen decision rows,
   twice (determinism check), via the SIDE-CAR arm
   (`resolve_rar_attachment_order_experimental`).
2. Necessary/sufficient/minimal-sufficient-set/interaction derivation from
   the raw rows (plan §7).
3. The bounded transport comparison (SIDE-CAR vs EXISTING-CONTRACT COMPILER)
   for the discovered minimal sufficient sets and their one-factor
   ablations, capped at 896 rows / T <= 16 (plan §4.3).
4. Confirmation/regression surfaces: full S-D battery, selected natural
   rows, flag-off equivalence.
5. A performance pass at pool sizes 2/8/32/128 (documented as a REDUCED
   iteration count relative to the plan's 200-warmup/2000-iteration
   pre-registration -- see PERFORMANCE_ITERATIONS_NOTE -- because this
   session's wall-clock budget could not accommodate the full protocol;
   this is disclosed, not silently substituted).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from uri_v1.turn.rar_contracts import RARCandidate, RAREvidence, RAROutcome, RARQuery  # noqa: E402
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended  # noqa: E402
from uri_v1.turn.rar_l5_diagnostic_fixtures import get_l5_diagnostic_fixtures, L5_DIAGNOSTIC_METADATA  # noqa: E402
from uri_v1.turn.rar_attachment_order_experimental import (  # noqa: E402
    AttachmentOrderOverlay,
    compile_and_resolve_via_existing_contract,
    resolve_rar_attachment_order_experimental,
)
from uri_v1.turn.rar_attachment_order_factorial_fixtures import (  # noqa: E402
    FactorialCase,
    get_factorial_cases,
)
import m35_rar_natural_boundary_harness as nbh  # noqa: E402

TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_TELEMETRY.json"
AGGREGATES_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_AGGREGATES.json"

PROTECTED_FILES = {
    "rar_contracts.py": REPO_ROOT / "uri_v1" / "turn" / "rar_contracts.py",
    "rar_deterministic.py": REPO_ROOT / "uri_v1" / "turn" / "rar_deterministic.py",
    "rar_safe_experimental.py": REPO_ROOT / "uri_v1" / "turn" / "rar_safe_experimental.py",
    "rar_l5_experimental.py": REPO_ROOT / "uri_v1" / "turn" / "rar_l5_experimental.py",
    "rar_l5_diagnostic_fixtures.py": REPO_ROOT / "uri_v1" / "turn" / "rar_l5_diagnostic_fixtures.py",
    "d1rq_detector.py": REPO_ROOT / "scripts" / "m35_a2_8h_detector_d1rq.py",
    "a2_8k_l5_battery.py": REPO_ROOT / "scripts" / "m35_a2_8k_l5_battery.py",
    "corpus.json": nbh.FIXTURE_PATH,
}

FACTORS = ["M", "G", "P", "D", "R", "Q"]

PERFORMANCE_ITERATIONS_NOTE = (
    "Plan §10.2 pre-registers 200 warmups + 2000 measured iterations per "
    "cell. This run uses 20 warmups + 200 measured iterations per cell "
    "(disclosed reduction, not a silent substitution) to fit this session's "
    "wall-clock budget. Relative comparisons (overhead ratios) are the "
    "intended use of this data; absolute thresholds in plan §10.2 should be "
    "treated as provisional pending a full-iteration rerun."
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _protected_hashes() -> Dict[str, str]:
    return {name: sha256_of(p) for name, p in PROTECTED_FILES.items()}


def _decision_tuple(res) -> tuple:
    return (res.outcome.value, res.candidate_id, frozenset(res.ambiguous_candidate_ids))


def _all_cells() -> List[Dict[str, bool]]:
    cells = []
    for bits in itertools.product([False, True], repeat=6):
        cells.append(dict(zip(FACTORS, bits)))
    return cells


def _cell_key(cell: Dict[str, bool]) -> str:
    return "".join(f + ("1" if cell[f] else "0") for f in FACTORS)


def _classify_row(case: FactorialCase, actual_outcome: str, actual_cid: Optional[str], actual_amb: FrozenSet[str]) -> str:
    """Row-level failure classification per plan §8, applied against this
    case's own frozen expected decision."""
    expected_amb = frozenset(case.expected_ambiguous_candidate_ids)
    if case.id == "C-NO-RANK0":
        return "PASS" if actual_outcome != "RESOLVED" else "UNCHANGED_DOMAIN_RERANK"

    if case.expected_outcome == RAROutcome.RESOLVED:
        if actual_outcome == "RESOLVED" and actual_cid == case.expected_candidate_id:
            return "PASS"
        if actual_outcome == "RESOLVED" and actual_cid != case.expected_candidate_id:
            return "INCORRECT_CONFIDENT_BINDING" if case.is_causal_target else "INCORRECT_CONFIDENT_BINDING"
        if actual_outcome == "AMBIGUOUS":
            return "MISSED_TRUSTWORTHY_BINDING"
        return "MISSED_TRUSTWORTHY_BINDING"

    if case.expected_outcome == RAROutcome.AMBIGUOUS:
        if actual_outcome == "RESOLVED":
            all_ids = {c.id for c in case.query.candidates}
            if actual_cid not in expected_amb and actual_cid in all_ids:
                if case.id in ("B-DISTRACTOR", "B-LATEST-WRONG-CLOCK", "B-FIRST-WRONG-CLOCK", "B-LATEST-PROVENANCE-TWIN"):
                    return "UNTRUSTWORTHY_ORDER_BIND"
                return "INCORRECT_CONFIDENT_BINDING"
            return "INCORRECT_CONFIDENT_BINDING"
        if actual_outcome == "AMBIGUOUS":
            if actual_amb == expected_amb:
                return "PASS"
            return "WRONG_AMBIGUITY_DOMAIN"
        return "WRONG_AMBIGUITY_DOMAIN"

    return "HARNESS_OR_FIXTURE_INVALID"


def _run_one(case: FactorialCase, cell: Dict[str, bool], repeat: int) -> dict:
    trace = resolve_rar_attachment_order_experimental(
        case.query, case.overlay,
        m=cell["M"], g=cell["G"], p=cell["P"], d=cell["D"], r=cell["R"], q=cell["Q"],
    )
    actual_outcome = trace.resolution.outcome.value
    actual_cid = trace.resolution.candidate_id
    actual_amb = frozenset(trace.resolution.ambiguous_candidate_ids)
    scoring = _classify_row(case, actual_outcome, actual_cid, actual_amb)
    return {
        "schema": "m35.uriv1.a2_8l.causal.v1",
        "cell": _cell_key(cell), "cell_flags": dict(cell), "repeat": repeat,
        "case_id": case.id, "case_source": case.source, "is_causal_target": case.is_causal_target,
        "pool_condition": case.pool_condition, "reachable_by_factors": case.reachable_by_factors,
        "candidate_ids_supplied": [c.id for c in case.query.candidates],
        "original_ranks": trace.original_ranks,
        "expected_outcome": case.expected_outcome.value,
        "expected_candidate_id": case.expected_candidate_id,
        "expected_ambiguous_candidate_ids": list(case.expected_ambiguous_candidate_ids),
        "actual_outcome": actual_outcome, "actual_candidate_id": actual_cid,
        "actual_ambiguous_candidate_ids": sorted(actual_amb),
        "rule_used": trace.rule_used.value if trace.rule_used else None,
        "failure_class": trace.failure_class.value if trace.failure_class else None,
        "which_level_returned": trace.which_level_returned,
        "level_5_5_ran_first": trace.level_5_5_ran_first,
        "ordinal_trigger_matched": trace.ordinal_trigger_matched,
        "effective_domain_ids": list(trace.effective_domain_ids),
        "effective_ranks": trace.effective_ranks,
        "factor_requested": trace.factor_requested, "factor_consumed": trace.factor_consumed,
        "no_op_reason": trace.no_op_reason,
        "scoring_class": scoring,
        "latency_ms": trace.latency_ms,
    }


def run_causal_matrix() -> List[dict]:
    cases = get_factorial_cases()
    cells = _all_cells()
    assert len(cells) == 64
    assert len(cases) == 14
    rows: List[dict] = []
    for cell in cells:
        for case in cases:
            for repeat in (1, 2):
                rows.append(_run_one(case, cell, repeat))
    assert len(rows) == 64 * 14 * 2 == 1792, f"Expected 1792 causal rows, got {len(rows)}"
    return rows


def reconcile_repeats(rows: List[dict]) -> dict:
    by_key: Dict[tuple, List[dict]] = {}
    for r in rows:
        key = (r["cell"], r["case_id"])
        by_key.setdefault(key, []).append(r)
    mismatches = []
    for key, pair in by_key.items():
        if len(pair) != 2:
            mismatches.append({"key": key, "reason": "MISSING_OR_DUPLICATE_REPEAT", "count": len(pair)})
            continue
        t0 = (pair[0]["actual_outcome"], pair[0]["actual_candidate_id"], frozenset(pair[0]["actual_ambiguous_candidate_ids"]))
        t1 = (pair[1]["actual_outcome"], pair[1]["actual_candidate_id"], frozenset(pair[1]["actual_ambiguous_candidate_ids"]))
        if t0 != t1:
            mismatches.append({"key": key, "reason": "NON_DETERMINISTIC", "repeat1": t0, "repeat2": t1})
    return {
        "total_keys": len(by_key),
        "expected_keys": 64 * 14,
        "mismatches": mismatches,
        "reconciled": len(mismatches) == 0 and len(by_key) == 64 * 14,
    }


def compute_qualifying_cells(rows: List[dict]) -> dict:
    """Plan §7: a cell QUALIFIES iff every row (repeat 1; repeats are
    identical per determinism) scores PASS, EXCLUDING C-LEXICAL-ATTACHMENT
    (disclosed unreachable-by-design control, per explicit User direction)."""
    by_cell: Dict[str, List[dict]] = {}
    for r in rows:
        if r["repeat"] != 1:
            continue
        by_cell.setdefault(r["cell"], []).append(r)

    qualifying: List[str] = []
    cell_reports: Dict[str, dict] = {}
    for cell_key, case_rows in by_cell.items():
        scored = [r for r in case_rows if r["reachable_by_factors"]]
        failing = [r for r in scored if r["scoring_class"] != "PASS"]
        cell_reports[cell_key] = {
            "failing_case_ids": [r["case_id"] for r in failing],
            "excluded_unreachable_case_ids": [r["case_id"] for r in case_rows if not r["reachable_by_factors"]],
            "qualifies": len(failing) == 0,
        }
        if not failing:
            qualifying.append(cell_key)

    minimal_sufficient: List[str] = []
    for cell_key in qualifying:
        cell_flags = {f: cell_key[FACTORS.index(f) * 2 + 1] == "1" for f in FACTORS}
        on_factors = {f for f, v in cell_flags.items() if v}
        is_minimal = True
        for f in on_factors:
            subset_flags = dict(cell_flags)
            subset_flags[f] = False
            subset_key = _cell_key(subset_flags)
            if subset_key in qualifying:
                is_minimal = False
                break
        if is_minimal:
            minimal_sufficient.append(cell_key)

    all_off_key = _cell_key({f: False for f in FACTORS})
    single_factor_sufficient = []
    for f in FACTORS:
        flags = {ff: False for ff in FACTORS}
        flags[f] = True
        key = _cell_key(flags)
        if key in qualifying:
            single_factor_sufficient.append(f)

    # Necessity: ON in every qualifying cell.
    necessary_factors = []
    if qualifying:
        for f in FACTORS:
            idx = FACTORS.index(f) * 2 + 1
            if all(key[idx] == "1" for key in qualifying):
                necessary_factors.append(f)

    return {
        "cell_reports": cell_reports,
        "qualifying_cells": qualifying,
        "qualifying_cell_count": len(qualifying),
        "minimal_sufficient_sets": minimal_sufficient,
        "single_factor_sufficient": single_factor_sufficient,
        "necessary_factors_if_any_qualifying": necessary_factors,
        "all_off_qualifies": all_off_key in qualifying,
    }


def compute_pairwise_interactions(rows: List[dict], qualifying_analysis: dict) -> dict:
    """§7 interacting-pair check: for every factor pair, compare the 2x2 of
    (both off / A only / B only / both on) qualification under the SAME
    remaining-factor background (all remaining factors off), reported as a
    raw 2x2 decision table, not inferred."""
    interactions = {}
    for i in range(len(FACTORS)):
        for j in range(i + 1, len(FACTORS)):
            fa, fb = FACTORS[i], FACTORS[j]
            table = {}
            for a_on in (False, True):
                for b_on in (False, True):
                    flags = {f: False for f in FACTORS}
                    flags[fa] = a_on
                    flags[fb] = b_on
                    key = _cell_key(flags)
                    table[f"{fa}={int(a_on)},{fb}={int(b_on)}"] = key in qualifying_analysis["qualifying_cells"]
            both_off = table[f"{fa}=0,{fb}=0"]
            a_only = table[f"{fa}=1,{fb}=0"]
            b_only = table[f"{fa}=0,{fb}=1"]
            both_on = table[f"{fa}=1,{fb}=1"]
            interacting = both_on and not a_only and not b_only and not both_off
            interactions[f"{fa}x{fb}"] = {"table": table, "interacting_pair": interacting}
    return interactions


# ---------------------------------------------------------------------------
# Transport comparison (bounded, plan §4.2/§4.3)
# ---------------------------------------------------------------------------

def run_transport_comparison(qualifying_analysis: dict) -> dict:
    cases = get_factorial_cases()
    minimal_sets = qualifying_analysis["minimal_sufficient_sets"]

    cells_to_test: List[str] = []
    if minimal_sets:
        cells_to_test.append(_cell_key({f: False for f in FACTORS}))  # T=1 baseline
        for key in minimal_sets:
            if key not in cells_to_test:
                cells_to_test.append(key)
            flags = {f: key[FACTORS.index(f) * 2 + 1] == "1" for f in FACTORS}
            for f in FACTORS:
                if flags[f]:
                    ablated = dict(flags)
                    ablated[f] = False
                    ablated_key = _cell_key(ablated)
                    if ablated_key not in cells_to_test:
                        cells_to_test.append(ablated_key)
    else:
        cells_to_test.append(_cell_key({f: False for f in FACTORS}))

    t_count = len(cells_to_test)
    row_cap_hit = t_count > 16
    if row_cap_hit:
        cells_to_test = cells_to_test[:16]
        t_count = 16

    rows: List[dict] = []
    mismatches: List[dict] = []
    for cell_key in cells_to_test:
        flags = {f: cell_key[FACTORS.index(f) * 2 + 1] == "1" for f in FACTORS}
        for case in cases:
            for repeat in (1, 2):
                sidecar_trace = resolve_rar_attachment_order_experimental(
                    case.query, case.overlay, **{k.lower(): v for k, v in flags.items()}
                )
                try:
                    compiled_trace, diag = compile_and_resolve_via_existing_contract(
                        case.query, case.overlay, m=flags["M"], r=flags["R"],
                    )
                    compiler_error = None
                except ValueError as exc:
                    compiled_trace, diag = None, {"error": str(exc)}
                    compiler_error = str(exc)

                sidecar_tuple = _decision_tuple(sidecar_trace.resolution)
                compiled_tuple = _decision_tuple(compiled_trace.resolution) if compiled_trace else None
                match = (sidecar_tuple == compiled_tuple) if compiled_trace else False
                row = {
                    "schema": "m35.uriv1.a2_8l.transport.v1",
                    "cell": cell_key, "case_id": case.id, "repeat": repeat,
                    "sidecar_outcome": sidecar_tuple[0], "sidecar_candidate_id": sidecar_tuple[1],
                    "sidecar_ambiguous_ids": sorted(sidecar_tuple[2]),
                    "compiler_outcome": compiled_tuple[0] if compiled_tuple else None,
                    "compiler_candidate_id": compiled_tuple[1] if compiled_tuple else None,
                    "compiler_ambiguous_ids": sorted(compiled_tuple[2]) if compiled_tuple else None,
                    "compiler_error": compiler_error,
                    "compiler_diagnostics": diag,
                    "arms_match": match,
                }
                rows.append(row)
                if not match:
                    mismatches.append(row)

    expected_rows = 56 * t_count if not row_cap_hit else None
    return {
        "t_value": t_count,
        "t_cap_hit": row_cap_hit,
        "cells_tested": cells_to_test,
        "rows": rows,
        "row_count": len(rows),
        "mismatches": mismatches,
        "mismatch_count": len(mismatches),
        "conclusion": (
            "TRANSPORT_RESULT_INCONCLUSIVE" if not qualifying_analysis["qualifying_cells"] else
            ("EXISTING_CONTRACT_COMPILATION_BEHAVIORALLY_SUFFICIENT" if not mismatches else
             "EXISTING_CONTRACT_COMPILATION_INSUFFICIENT")
        ),
    }


# ---------------------------------------------------------------------------
# Confirmation / regression surfaces (plan §5.3)
# ---------------------------------------------------------------------------

def run_confirmation_surfaces(best_cell: Optional[str]) -> dict:
    flags = {f: False for f in FACTORS}
    if best_cell:
        flags = {f: best_cell[FACTORS.index(f) * 2 + 1] == "1" for f in FACTORS}

    sd_mismatches = []
    for fix in get_l5_diagnostic_fixtures():
        base = resolve_rar_deterministic_extended(fix.query)
        exp_off = resolve_rar_attachment_order_experimental(fix.query, AttachmentOrderOverlay())
        exp_flag = resolve_rar_attachment_order_experimental(
            fix.query, AttachmentOrderOverlay(), **{k.lower(): v for k, v in flags.items()}
        )
        if _decision_tuple(exp_flag.resolution) != _decision_tuple(exp_off.resolution) and fix.id not in (
            "SD-A-04", "SD-A-05", "SD-A-06", "SD-A-07",
        ):
            sd_mismatches.append({
                "fixture": fix.id,
                "flag_off": _decision_tuple(exp_off.resolution),
                "with_best_cell": _decision_tuple(exp_flag.resolution),
            })

    return {
        "sd_battery_case_count": len(get_l5_diagnostic_fixtures()),
        "sd_unexpected_flagged_changes": sd_mismatches,
        "flag_used_for_confirmation": flags,
        "note": (
            "SD-A-04/05/06/07 are expected to change under the winning cell "
            "(they are this experiment's own reused causal targets); all "
            "other S-D rows must be unchanged."
        ),
    }


# ---------------------------------------------------------------------------
# Performance pass (plan §10.2, reduced iteration count -- disclosed)
# ---------------------------------------------------------------------------

def _synthetic_pool(n: int) -> Tuple[RARQuery, AttachmentOrderOverlay]:
    from uri_v1.turn.rar_attachment_order_experimental import PROVENANCE_CURRENT_TURN_SEQUENCE
    cands = []
    membership = set()
    event_group = {}
    ordinal = {}
    for i in range(n):
        cid = f"perf-{i}"
        cands.append(RARCandidate(id=cid, title=f"Distractor_{i}.pdf", candidate_type="document",
                                   recency_rank=n - i, is_attachment=True))
        if i < 2:
            membership.add(cid)
            event_group[cid] = f"event-{i}"
            ordinal[f"event-{i}"] = i
    cands[0] = RARCandidate(id="perf-0", title="Draft_New.pdf", candidate_type="document",
                             recency_rank=n - 1, is_attachment=True)
    cands[1] = RARCandidate(id="perf-1", title="Draft_Old.pdf", candidate_type="document",
                             recency_rank=n - 2, is_attachment=True)
    q = RARQuery("the latest attachment", tuple(cands), RAREvidence(recency_hint="latest"))
    ov = AttachmentOrderOverlay(
        turn_membership_ids=frozenset(membership), event_group_by_id=event_group,
        group_ordinal_by_event=ordinal, provenance=PROVENANCE_CURRENT_TURN_SEQUENCE,
    )
    return q, ov


def run_performance_pass(qualifying_analysis: dict, warmups: int = 20, iterations: int = 200) -> dict:
    pool_sizes = [2, 8, 32, 128]
    cells: List[Tuple[str, Dict[str, bool]]] = [("all_off", {f: False for f in FACTORS})]
    for key in qualifying_analysis["minimal_sufficient_sets"][:3]:
        flags = {f: key[FACTORS.index(f) * 2 + 1] == "1" for f in FACTORS}
        cells.append((key, flags))

    results = {}
    for cell_name, flags in cells:
        results[cell_name] = {}
        for n in pool_sizes:
            q, ov = _synthetic_pool(n)
            for _ in range(warmups):
                resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})

            wall_ns: List[int] = []
            cpu_ns: List[int] = []
            for _ in range(iterations):
                t0_wall, t0_cpu = time.perf_counter_ns(), time.process_time_ns()
                resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})
                wall_ns.append(time.perf_counter_ns() - t0_wall)
                cpu_ns.append(time.process_time_ns() - t0_cpu)

            tracemalloc.start()
            resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            wall_sorted = sorted(wall_ns)
            results[cell_name][f"pool_{n}"] = {
                "mean_wall_ms": statistics.mean(wall_ns) / 1e6,
                "p95_wall_ms": wall_sorted[int(len(wall_sorted) * 0.95) - 1] / 1e6,
                "median_cpu_ms": statistics.median(cpu_ns) / 1e6,
                "peak_alloc_bytes": peak,
                "iterations": iterations,
                "warmups": warmups,
            }
    return {"note": PERFORMANCE_ITERATIONS_NOTE, "results": results}


def main() -> None:
    pre_hashes = _protected_hashes()

    run1 = run_causal_matrix()
    run2 = run_causal_matrix()
    determinism_ok = [
        (r["cell"], r["case_id"], r["repeat"], r["actual_outcome"], r["actual_candidate_id"], tuple(r["actual_ambiguous_candidate_ids"]))
        for r in run1
    ] == [
        (r["cell"], r["case_id"], r["repeat"], r["actual_outcome"], r["actual_candidate_id"], tuple(r["actual_ambiguous_candidate_ids"]))
        for r in run2
    ]

    reconciliation = reconcile_repeats(run1)
    qualifying_analysis = compute_qualifying_cells(run1)
    interactions = compute_pairwise_interactions(run1, qualifying_analysis)
    best_cell = qualifying_analysis["minimal_sufficient_sets"][0] if qualifying_analysis["minimal_sufficient_sets"] else None
    transport = run_transport_comparison(qualifying_analysis)
    confirmation = run_confirmation_surfaces(best_cell)
    performance = run_performance_pass(qualifying_analysis)

    post_hashes = _protected_hashes()
    hashes_unchanged = pre_hashes == post_hashes

    telemetry = {
        "schema": "m35.uriv1.a2_8l.telemetry.v1",
        "pre_run_protected_hashes": pre_hashes,
        "post_run_protected_hashes": post_hashes,
        "protected_hashes_unchanged": hashes_unchanged,
        "causal_rows": run1,
        "causal_row_count": len(run1),
        "determinism_check_passed": determinism_ok,
        "repeat_reconciliation": reconciliation,
        "transport_comparison": transport,
        "confirmation_surfaces": confirmation,
        "performance": performance,
    }
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)

    aggregates = {
        "schema": "m35.uriv1.a2_8l.aggregates.v1",
        "qualifying_analysis": qualifying_analysis,
        "pairwise_interactions": interactions,
        "transport_conclusion": transport["conclusion"],
        "transport_mismatch_count": transport["mismatch_count"],
        "determinism_check_passed": determinism_ok,
        "repeat_reconciliation_passed": reconciliation["reconciled"],
        "protected_hashes_unchanged": hashes_unchanged,
    }
    with open(AGGREGATES_PATH, "w", encoding="utf-8") as f:
        json.dump(aggregates, f, indent=2)

    print(f"Causal rows: {len(run1)} (expect 1792)")
    print(f"Determinism check passed: {determinism_ok}")
    print(f"Repeat reconciliation: {reconciliation['reconciled']}")
    print(f"Qualifying cells: {qualifying_analysis['qualifying_cell_count']} / 64")
    print(f"Minimal sufficient sets: {qualifying_analysis['minimal_sufficient_sets']}")
    print(f"Transport T value: {transport['t_value']}, conclusion: {transport['conclusion']}")
    print(f"Protected hashes unchanged: {hashes_unchanged}")
    print(f"Wrote telemetry -> {TELEMETRY_PATH}")
    print(f"Wrote aggregates -> {AGGREGATES_PATH}")


if __name__ == "__main__":
    main()
