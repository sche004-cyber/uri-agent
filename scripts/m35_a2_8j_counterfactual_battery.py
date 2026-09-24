"""M35 URIv1 -- A2.8J: RAR-SAFE Counterfactual Probe Battery.

Benchmark-only, diagnostic. Runs the three named counterfactual probes from
the A2.8J plan/task against BOTH the real, unmodified
`resolve_rar_deterministic_extended` and the new experimental
`resolve_rar_safe_experimental`, without wiring recency, T2 detection, or
any D1RQ change into production. Does not modify D1RQ, RAR, RAR-SAFE, the
harness, or the corpus -- reads/imports all of them unmodified.

Appends its results as a new top-level "counterfactual_probes" key onto the
EXISTING `docs/plans/M35_URIV1_A2_8J_AGGREGATES.json` file (must be run
after `scripts/m35_a2_8j_rar_safe_battery.py`); does not create a third
telemetry file, per the accepted plan's deliverable list (§4).

Probe A -- Recency truthful-rank (Known A / New: masks removed).
    Mirrors A2.8I's P3: the harness's own oracle query construction
    (`s2_query_for_reference`) combined with REAL `created_at`-derived
    ranks (`build_candidate_pool(oracle_recency=True)`), for every
    ground-truth reference whose `temporal_meaning != "none"`. Reports
    correct/ICB before (RAR) vs after (RAR-SAFE) at C1 and C2.

Probe B -- T2 perfect-span diagnostic (New F, latent unsafe-if-detected).
    The 7 known T2 bare-proper-name silent detection misses
    (`NB-B-05:r2`, `NB-G-04:r1`, `NB-I-02:r2`, `NB-I-06:r2`, `NB-L-01:r2`,
    `NB-L-02:r2`, `NB-L-04:r2`). Mirrors A2.8I's P1: the ground-truth span
    is substituted directly as `reference_expression`, and D1RQ's OWN
    (unmodified) signal-extraction helpers (`_recency_hint_for_text`,
    `_type_hint_for_phrase`, `_clause_negation_spans`) are applied to the
    span's home clause -- exactly what D1RQ would have produced had it
    detected this span. `recency_rank=0` (S1/oracle_recency=False), C1/C2.
    Reports correct/ICB before (RAR) vs after (RAR-SAFE).

Probe C -- Exclusion/contrast (Known B, active/unsafe -- `NB-H-06`).
    The real D1RQ-detected span/signals for `NB-H-06:r1` (no reconstruction
    -- pulled from the live detector output), run through both resolvers at
    C1 and C2. Reports outcome/ICB before (RAR) vs after (RAR-SAFE).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from m35_rar_natural_boundary_harness import (  # noqa: E402
    build_candidate_pool,
    load_fixture,
    s2_query_for_reference,
)
from m35_a2_8h_detector_d1rq import (  # noqa: E402
    detect_references as d1rq_detect,
    _recency_hint_for_text,
    _type_hint_for_phrase,
    _clause_negation_spans,
)

from uri_v1.turn.rar_contracts import RAREvidence, RARQuery, RAROutcome  # noqa: E402
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended  # noqa: E402
from uri_v1.turn.rar_safe_experimental import resolve_rar_safe_experimental  # noqa: E402

AGGREGATES_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8J_AGGREGATES.json"

RESOLVERS = {"RAR": resolve_rar_deterministic_extended, "RAR-SAFE": resolve_rar_safe_experimental}

T2_TARGETS = [
    ("NB-B-05", "r2"), ("NB-G-04", "r1"), ("NB-I-02", "r2"), ("NB-I-06", "r2"),
    ("NB-L-01", "r2"), ("NB-L-02", "r2"), ("NB-L-04", "r2"),
]

EXCLUSION_TARGET = ("NB-H-06", "r1")


def _classify(expected_outcome, intended_ids, actual_outcome, actual_candidate_id) -> str:
    if actual_outcome == "RESOLVED":
        if expected_outcome == "RESOLVED" and actual_candidate_id in intended_ids:
            return "CORRECT_RESOLUTION"
        return "INCORRECT_CONFIDENT_BINDING"
    if expected_outcome == "RESOLVED":
        return "MISSED_RESOLVABLE_CASE"
    if expected_outcome in ("AMBIGUOUS", "UNKNOWN"):
        return "CORRECT_ABSTENTION" if actual_outcome == expected_outcome else "CORRECT_ABSTENTION_FAMILY_MISMATCH"
    return "UNCLASSIFIED_OBSERVED_OUTCOME"


def _run_both(query: RARQuery, expected_outcome: str, intended_ids: Sequence[str]) -> dict:
    out = {}
    for name, fn in RESOLVERS.items():
        trace = fn(query)
        res = trace.resolution
        sc = _classify(expected_outcome, intended_ids, res.outcome.value, res.candidate_id)
        out[name] = {
            "outcome": res.outcome.value,
            "candidate_id": res.candidate_id,
            "ambiguous_ids": list(res.ambiguous_candidate_ids),
            "rule_used": trace.rule_used.value if trace.rule_used else None,
            "scoring_class": sc,
        }
    return out


def probe_a_recency_truthful_rank(cases: List[dict], library: dict) -> dict:
    results = []
    for case in cases:
        case_id = case["case_id"]
        gt_refs = case["ground_truth_references"]
        variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}
        for gt in gt_refs:
            if (gt.get("temporal_meaning") or "none") == "none":
                continue
            for c_axis in ("C1", "C2"):
                variant = variants_by_cond.get(c_axis)
                if variant is None:
                    continue
                eb_by_key = {eb["ref_key"]: eb for eb in variant["expected_by_reference"]}
                eb = eb_by_key.get(gt["ref_key"])
                if eb is None:
                    continue
                candidates = build_candidate_pool(variant["available_candidates"], library, oracle_recency=True)
                if not candidates:
                    continue
                q = s2_query_for_reference(gt, candidates)
                pair = _run_both(q, eb.get("expected_outcome", "UNKNOWN"), eb.get("intended_candidate_ids", []))
                results.append({
                    "case_id": case_id, "ref_key": gt["ref_key"], "c_axis": c_axis,
                    "temporal_meaning": gt.get("temporal_meaning"),
                    "expected_outcome": eb.get("expected_outcome", "UNKNOWN"),
                    "RAR": pair["RAR"], "RAR-SAFE": pair["RAR-SAFE"],
                })

    icb_before = sum(1 for r in results if r["RAR"]["scoring_class"] == "INCORRECT_CONFIDENT_BINDING")
    icb_after = sum(1 for r in results if r["RAR-SAFE"]["scoring_class"] == "INCORRECT_CONFIDENT_BINDING")
    correct_before = sum(1 for r in results if r["RAR"]["scoring_class"] == "CORRECT_RESOLUTION")
    correct_after = sum(1 for r in results if r["RAR-SAFE"]["scoring_class"] == "CORRECT_RESOLUTION")
    return {
        "description": "Oracle temporal query (s2_query_for_reference) + real created_at-derived recency_rank "
                        "(build_candidate_pool(oracle_recency=True)), all references with temporal_meaning != none, C1+C2.",
        "n_probed": len(results),
        "icb_before_RAR": icb_before,
        "icb_after_RAR_SAFE": icb_after,
        "correct_before_RAR": correct_before,
        "correct_after_RAR_SAFE": correct_after,
        "records": results,
    }


def probe_b_t2_perfect_span(cases_by_id: dict, library: dict) -> dict:
    results = []
    for case_id, ref_key in T2_TARGETS:
        case = cases_by_id[case_id]
        raw_text = case["raw_user_text"]
        gt_by_key = {r["ref_key"]: r for r in case["ground_truth_references"]}
        gt = gt_by_key[ref_key]
        span = gt.get("human_marked_span") or gt.get("implicit_antecedent") or ""

        home_clause = raw_text
        for c in [s.strip() for s in raw_text.replace("?", ".").replace("!", ".").split(".") if s.strip()]:
            if span.lower() in c.lower():
                home_clause = c
                break

        recency_hint = _recency_hint_for_text(home_clause)
        coarse_type = _type_hint_for_phrase(span)
        negation_spans = _clause_negation_spans(home_clause)

        variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}
        for c_axis in ("C1", "C2"):
            variant = variants_by_cond.get(c_axis)
            if variant is None:
                continue
            eb_by_key = {eb["ref_key"]: eb for eb in variant["expected_by_reference"]}
            eb = eb_by_key.get(ref_key)
            if eb is None:
                continue
            candidates = build_candidate_pool(variant["available_candidates"], library, oracle_recency=False)
            evidence = RAREvidence(
                recency_hint=recency_hint,
                negation_spans=negation_spans,
                target_type_hint=coarse_type,
            )
            q = RARQuery(reference_expression=span, candidates=candidates, local_evidence=evidence, deterministic_anchor=None)
            pair = _run_both(q, eb.get("expected_outcome", "UNKNOWN"), eb.get("intended_candidate_ids", []))
            results.append({
                "case_id": case_id, "ref_key": ref_key, "c_axis": c_axis, "span": span,
                "signals": {"recency_hint": recency_hint, "coarse_type": coarse_type, "negation_spans": negation_spans},
                "expected_outcome": eb.get("expected_outcome", "UNKNOWN"),
                "RAR": pair["RAR"], "RAR-SAFE": pair["RAR-SAFE"],
            })

    icb_before = sum(1 for r in results if r["RAR"]["scoring_class"] == "INCORRECT_CONFIDENT_BINDING")
    icb_after = sum(1 for r in results if r["RAR-SAFE"]["scoring_class"] == "INCORRECT_CONFIDENT_BINDING")
    correct_before = sum(1 for r in results if r["RAR"]["scoring_class"] == "CORRECT_RESOLUTION")
    correct_after = sum(1 for r in results if r["RAR-SAFE"]["scoring_class"] == "CORRECT_RESOLUTION")
    return {
        "description": "Ground-truth span substituted directly as reference_expression; D1RQ's own unmodified "
                        "signal-extraction helpers applied to the span's home clause (as if D1RQ had detected it); "
                        "recency_rank=0 (oracle_recency=False), C1+C2. 7 known T2 bare-proper-name silent misses.",
        "n_probed": len(results),
        "icb_before_RAR": icb_before,
        "icb_after_RAR_SAFE": icb_after,
        "correct_before_RAR": correct_before,
        "correct_after_RAR_SAFE": correct_after,
        "records": results,
    }


def probe_c_exclusion_contrast(cases_by_id: dict, library: dict) -> dict:
    case_id, ref_key = EXCLUSION_TARGET
    case = cases_by_id[case_id]
    raw_text = case["raw_user_text"]
    gt_by_key = {r["ref_key"]: r for r in case["ground_truth_references"]}
    gt = gt_by_key[ref_key]

    d1rq_found = list(d1rq_detect(raw_text))
    match = None
    for r in d1rq_found:
        gt_span = gt.get("human_marked_span") or ""
        if r.span.lower() in gt_span.lower() or gt_span.lower() in r.span.lower():
            match = r
            break

    results = []
    variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}
    for c_axis in ("C1", "C2"):
        variant = variants_by_cond.get(c_axis)
        if variant is None or match is None:
            continue
        eb_by_key = {eb["ref_key"]: eb for eb in variant["expected_by_reference"]}
        eb = eb_by_key.get(ref_key)
        if eb is None:
            continue
        candidates = build_candidate_pool(variant["available_candidates"], library, oracle_recency=False)
        evidence = RAREvidence(
            recency_hint=match.recency_hint,
            negation_spans=match.negation_spans,
            target_type_hint=match.coarse_type,
        )
        q = RARQuery(reference_expression=match.span, candidates=candidates, local_evidence=evidence, deterministic_anchor=None)
        pair = _run_both(q, eb.get("expected_outcome", "UNKNOWN"), eb.get("intended_candidate_ids", []))
        results.append({
            "case_id": case_id, "ref_key": ref_key, "c_axis": c_axis,
            "detected_span": match.span,
            "signals": {"recency_hint": match.recency_hint, "coarse_type": match.coarse_type, "negation_spans": match.negation_spans},
            "expected_outcome": eb.get("expected_outcome", "UNKNOWN"),
            "RAR": pair["RAR"], "RAR-SAFE": pair["RAR-SAFE"],
        })

    icb_before = sum(1 for r in results if r["RAR"]["scoring_class"] == "INCORRECT_CONFIDENT_BINDING")
    icb_after = sum(1 for r in results if r["RAR-SAFE"]["scoring_class"] == "INCORRECT_CONFIDENT_BINDING")
    return {
        "description": "Real D1RQ-detected span/signals for NB-H-06:r1 (live detector output, no reconstruction), C1+C2.",
        "n_probed": len(results),
        "icb_before_RAR": icb_before,
        "icb_after_RAR_SAFE": icb_after,
        "records": results,
    }


def main() -> None:
    data = load_fixture()
    library = data["candidate_library"]
    cases = data["cases"]
    cases_by_id = {c["case_id"]: c for c in cases}

    probes = {
        "recency_truthful_rank": probe_a_recency_truthful_rank(cases, library),
        "t2_perfect_span": probe_b_t2_perfect_span(cases_by_id, library),
        "exclusion_contrast_nb_h_06": probe_c_exclusion_contrast(cases_by_id, library),
    }

    if AGGREGATES_PATH.exists():
        with open(AGGREGATES_PATH, "r", encoding="utf-8") as f:
            aggregates = json.load(f)
    else:
        aggregates = {"schema": "m35.uriv1.a2_8j.aggregates.v1"}

    aggregates["counterfactual_probes"] = probes

    with open(AGGREGATES_PATH, "w", encoding="utf-8") as f:
        json.dump(aggregates, f, indent=2)

    print(f"Wrote counterfactual_probes into {AGGREGATES_PATH}")
    for name, p in probes.items():
        print(f"  {name}: n={p['n_probed']} icb_before={p.get('icb_before_RAR')} icb_after={p.get('icb_after_RAR_SAFE')}")


if __name__ == "__main__":
    main()
