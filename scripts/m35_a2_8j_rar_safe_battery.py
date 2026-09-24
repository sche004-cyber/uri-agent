"""M35 URIv1 -- A2.8J: RAR-SAFE Natural-Boundary Corpus Battery.

Benchmark-only. Runs the frozen 79-case corpus through the ONE existing
D1RQ detector column (`scripts/m35_a2_8h_detector_d1rq.py`, unmodified,
imported not copied) crossed with the existing C1/C2/C3 candidate-pool
conditions, calling BOTH the real, unmodified
`resolve_rar_deterministic_extended` (uri_v1.turn.rar_deterministic) and
the new experimental `resolve_rar_safe_experimental`
(uri_v1.turn.rar_safe_experimental) exactly once per detected reference,
per variant. Neither resolver module is modified by this script.

This is a narrower fork of `scripts/m35_a2_8h_run.py`: same corpus, same
D1RQ detector, same C1/C2/C3 conditions, same scoring taxonomy and boundary-
violation check -- the only difference is the RESOLVER axis (RAR vs
RAR-SAFE) replacing A2.8H's DETECTOR axis (D0/D1/D2/D1R/D1RQ).

Frozen boundary check (same as A2.8H): every detector-produced span/field is
scanned for accidental leakage of a live candidate_id before use; any hit is
recorded as boundary_violation=True and excluded from scoring.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from m35_rar_natural_boundary_harness import (  # noqa: E402
    FIXTURE_PATH,
    build_candidate_pool,
    load_fixture,
    sha256_of,
)
from m35_a2_8h_detector_d1rq import detect_references as d1rq_detect  # noqa: E402

from uri_v1.turn.rar_contracts import RAREvidence, RARQuery  # noqa: E402
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended  # noqa: E402
from uri_v1.turn.rar_safe_experimental import resolve_rar_safe_experimental  # noqa: E402

TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8J_TELEMETRY.json"
AGGREGATES_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8J_AGGREGATES.json"
CELLS_C = ("C1", "C2", "C3")

RESOLVERS = {
    "RAR": resolve_rar_deterministic_extended,
    "RAR-SAFE": resolve_rar_safe_experimental,
}

# Mirrors rar_deterministic.py's own cascade-level attribution via rule_used.
# Grouped for the per-level rollup the mission brief (§9) requires. "NONE"
# covers Level 7's residual/failure classification (never a positive rule).
RULE_TO_LEVEL = {
    "EXACT_ID": "L0",
    "EXACT_ALIAS": "L0",
    "ACTIVE_UI": "L1",
    "CURRENT_ATTACHMENT": "L1_or_L5_5",  # ambiguous by rule alone; disambiguated below
    "EXACT_TITLE": "L1_or_L2",
    "ACTIVE_POINTER": "L3",
    "CONTRAST_FILTER": "L4a_or_L4b",
    "TYPE_FILTER": "L4b",
    "TEMPORAL_RELATION": "L5",
    "REVISION_RELATION": "L5",
    "TERM_DISCRIMINATION": "L6",
    "NONE": "L7",
}


def find_matching_found_expr(gt_span: Optional[str], found_exprs: Sequence[str], used: set) -> Optional[str]:
    """Bidirectional substring match (unchanged from A2.8H)."""
    if not gt_span:
        return None
    gt_lower = gt_span.lower()
    for expr in found_exprs:
        if expr in used:
            continue
        expr_lower = expr.lower()
        if expr_lower in gt_lower or gt_lower in expr_lower:
            return expr
    return None


def boundary_violation(span: Optional[str], candidate_ids: Sequence[str], raw_text: str = "") -> bool:
    """Unchanged from A2.8H: a genuine boundary violation is the DETECTOR
    fabricating a live candidate_id the user never actually typed."""
    if not span:
        return False
    span_low = span.lower()
    raw_low = raw_text.lower()
    for cid in candidate_ids:
        cid_low = cid.lower()
        if cid_low in span_low or span_low == cid_low:
            if cid_low not in raw_low:
                return True
    return False


def build_query(reference_expression: str, candidates, recency_hint, negation_spans, target_type_hint=None) -> RARQuery:
    evidence = RAREvidence(
        recency_hint=recency_hint,
        negation_spans=tuple(negation_spans or ()),
        target_type_hint=target_type_hint,
    )
    return RARQuery(
        reference_expression=reference_expression,
        candidates=candidates,
        local_evidence=evidence,
        deterministic_anchor=None,
    )


def run_d1rq_case(raw_text: str):
    out = []
    for r in d1rq_detect(raw_text):
        out.append({
            "span": r.span, "recency_hint": r.recency_hint, "negation_spans": r.negation_spans,
            "coarse_type": r.coarse_type, "mechanism": r.mechanism,
        })
    return out


def _classify(row: dict) -> str:
    expected = row["expected_outcome"]
    actual = row["actual_outcome"]
    intended = row["intended_candidate_ids"]
    cid = row["actual_candidate_id"]

    if expected == "NO_REFERENCE":
        return "DETECTOR_FALSE_POSITIVE_BINDING" if actual == "RESOLVED" else "DETECTOR_FALSE_POSITIVE_SAFE_ABSTENTION"
    if expected == "UNATTRIBUTED_DETECTOR_FIND":
        return "UNATTRIBUTED_DETECTOR_FIND"

    if actual == "RESOLVED":
        if expected == "RESOLVED" and cid in intended:
            return "CORRECT_RESOLUTION"
        return "INCORRECT_CONFIDENT_BINDING"
    if expected == "RESOLVED":
        return "MISSED_RESOLVABLE_CASE"
    if expected in ("AMBIGUOUS", "UNKNOWN"):
        return "CORRECT_ABSTENTION" if actual == expected else "CORRECT_ABSTENTION_FAMILY_MISMATCH"
    return "UNCLASSIFIED_OBSERVED_OUTCOME"


def _row(case_id, category, variant, c_axis, ref_key, span, expected_outcome,
         intended_ids, candidate_ids, found, trace, boundary_violation=False,
         scoring_class_override=None):
    row = {
        "case_id": case_id, "category": category, "detector": "D1RQ",
        "variant": variant, "cell": f"{variant}x{c_axis}", "c_axis": c_axis, "ref_key": ref_key,
        "detected_span": span, "expected_outcome": expected_outcome,
        "intended_candidate_ids": intended_ids, "candidate_ids_supplied": list(candidate_ids),
        "signals_supplied": {
            "recency_hint": found.get("recency_hint") if found else None,
            "negation_spans": list(found.get("negation_spans") or ()) if found else [],
            "coarse_type": found.get("coarse_type") if found else None,
        } if found else {},
        "mechanism": found.get("mechanism") if found else None,
        "boundary_violation": boundary_violation,
    }
    if trace is not None:
        rule_val = trace.rule_used.value if trace.rule_used else None
        row.update({
            "rar_invoked": True,
            "actual_outcome": trace.resolution.outcome.value,
            "actual_candidate_id": trace.resolution.candidate_id,
            "actual_ambiguous_ids": list(trace.resolution.ambiguous_candidate_ids),
            "rar_failure_class": trace.failure_class.value if trace.failure_class else None,
            "rule_used": rule_val,
            "level": RULE_TO_LEVEL.get(rule_val, "UNKNOWN") if rule_val else None,
            "latency_ms": trace.latency_ms,
        })
    else:
        row.update({
            "rar_invoked": False, "actual_outcome": None, "actual_candidate_id": None,
            "actual_ambiguous_ids": [], "rar_failure_class": None, "rule_used": None,
            "level": None, "latency_ms": None,
        })

    if scoring_class_override:
        row["scoring_class"] = scoring_class_override
    elif boundary_violation:
        row["scoring_class"] = "BOUNDARY_VIOLATION"
    elif not row["rar_invoked"]:
        row["scoring_class"] = "SILENT_DETECTION_MISS"
    else:
        row["scoring_class"] = _classify(row)
    return row


def run_battery() -> dict:
    pre_hash = sha256_of(FIXTURE_PATH)
    data = load_fixture()
    library = data["candidate_library"]
    cases = data["cases"]

    telemetry: List[dict] = []

    for case in cases:
        case_id = case["case_id"]
        category = case["category"]
        raw_text = case["raw_user_text"]
        gt_refs = case["ground_truth_references"]
        gt_by_key = {r["ref_key"]: r for r in gt_refs}
        variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}

        d1rq_found = run_d1rq_case(raw_text)
        found_spans = [f["span"] for f in d1rq_found]

        for variant_name, resolver_fn in RESOLVERS.items():
            used_spans: set = set()
            match_for_ref: Dict[str, Optional[dict]] = {}
            for ref_key, gt in gt_by_key.items():
                m_expr = find_matching_found_expr(gt.get("human_marked_span"), found_spans, used_spans)
                if m_expr is not None:
                    used_spans.add(m_expr)
                    match_for_ref[ref_key] = next(f for f in d1rq_found if f["span"] == m_expr)
                else:
                    match_for_ref[ref_key] = None
            unattributed = [f for f in d1rq_found if f["span"] not in used_spans]

            for c_axis in CELLS_C:
                if c_axis == "C3":
                    candidate_ids: Sequence[str] = ()
                    variant = None
                else:
                    variant = variants_by_cond[c_axis]
                    candidate_ids = variant["available_candidates"]
                candidates = build_candidate_pool(candidate_ids, library, oracle_recency=False)
                expected_by_ref = {}
                if variant is not None:
                    for eb in variant["expected_by_reference"]:
                        expected_by_ref[eb["ref_key"]] = eb

                if not gt_refs:
                    if d1rq_found:
                        for f in d1rq_found:
                            bv = boundary_violation(f["span"], candidate_ids, raw_text)
                            if bv:
                                telemetry.append(_row(
                                    case_id, category, variant_name, c_axis, None, f["span"],
                                    "NO_REFERENCE", [], candidate_ids, f, None, boundary_violation=True,
                                ))
                                continue
                            q = build_query(f["span"], candidates, f["recency_hint"], f["negation_spans"], f.get("coarse_type"))
                            trace = resolver_fn(q)
                            telemetry.append(_row(
                                case_id, category, variant_name, c_axis, None, f["span"],
                                "NO_REFERENCE", [], candidate_ids, f, trace,
                            ))
                    else:
                        telemetry.append(_row(
                            case_id, category, variant_name, c_axis, None, None,
                            "NO_REFERENCE", [], candidate_ids, None, None,
                        ))
                    continue

                for ref_key, gt in gt_by_key.items():
                    eb = expected_by_ref.get(ref_key, {})
                    expected_outcome = eb.get("expected_outcome", "UNKNOWN")
                    intended_ids = eb.get("intended_candidate_ids", [])
                    f = match_for_ref.get(ref_key)

                    if f is None:
                        telemetry.append(_row(
                            case_id, category, variant_name, c_axis, ref_key, None,
                            expected_outcome, intended_ids, candidate_ids, None, None,
                            scoring_class_override="SILENT_DETECTION_MISS",
                        ))
                        continue

                    bv = boundary_violation(f["span"], candidate_ids, raw_text)
                    if bv:
                        telemetry.append(_row(
                            case_id, category, variant_name, c_axis, ref_key, f["span"],
                            expected_outcome, intended_ids, candidate_ids, f, None, boundary_violation=True,
                        ))
                        continue

                    q = build_query(f["span"], candidates, f["recency_hint"], f["negation_spans"], f.get("coarse_type"))
                    trace = resolver_fn(q)
                    telemetry.append(_row(
                        case_id, category, variant_name, c_axis, ref_key, f["span"],
                        expected_outcome, intended_ids, candidate_ids, f, trace,
                    ))

                for f in unattributed:
                    bv = boundary_violation(f["span"], candidate_ids, raw_text)
                    telemetry.append(_row(
                        case_id, category, variant_name, c_axis, None, f["span"],
                        "UNATTRIBUTED_DETECTOR_FIND", [], candidate_ids, f, None,
                        boundary_violation=bv, scoring_class_override="UNATTRIBUTED_DETECTOR_FIND",
                    ))

    post_hash = sha256_of(FIXTURE_PATH)

    output = {
        "schema": "m35.uriv1.a2_8j.telemetry.v1",
        "fixture_path": str(FIXTURE_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "pre_run_sha256": pre_hash,
        "post_run_sha256": post_hash,
        "detector": "D1RQ",
        "variants": list(RESOLVERS.keys()),
        "records": telemetry,
    }
    return output


def compute_aggregates(telemetry_output: dict) -> dict:
    records = telemetry_output["records"]
    gt_records = [r for r in records if r["expected_outcome"] not in ("NO_REFERENCE", "UNATTRIBUTED_DETECTOR_FIND")]

    per_variant_cell: Dict[str, Dict[str, int]] = {}
    per_level: Dict[str, Dict[str, Dict[str, int]]] = {}
    scoring_class_totals: Dict[str, Dict[str, int]] = {}
    invented_candidate_count = 0
    boundary_violation_count = 0

    valid_ids_by_rowkey: Dict[str, set] = {}

    for r in records:
        cell = r["cell"]
        per_variant_cell.setdefault(cell, {})
        sc = r["scoring_class"]
        per_variant_cell[cell][sc] = per_variant_cell[cell].get(sc, 0) + 1

        scoring_class_totals.setdefault(r["variant"], {})
        scoring_class_totals[r["variant"]][sc] = scoring_class_totals[r["variant"]].get(sc, 0) + 1

        if r.get("boundary_violation"):
            boundary_violation_count += 1

        candidate_ids_supplied = set(r.get("candidate_ids_supplied") or [])
        cid = r.get("actual_candidate_id")
        if cid and candidate_ids_supplied and cid not in candidate_ids_supplied:
            invented_candidate_count += 1
        for aid in r.get("actual_ambiguous_ids") or []:
            if candidate_ids_supplied and aid not in candidate_ids_supplied:
                invented_candidate_count += 1

        level = r.get("level")
        if level and r["c_axis"] in ("C1", "C2"):
            per_level.setdefault(r["variant"], {})
            per_level[r["variant"]].setdefault(level, {})
            per_level[r["variant"]][level][sc] = per_level[r["variant"]][level].get(sc, 0) + 1

    # Per-level before(RAR)->after(RAR-SAFE) delta table, restricted to
    # ground-truth-bearing rows at C1/C2 (mission §9's per-level breakdown).
    level_names = sorted({lvl for v in per_level.values() for lvl in v.keys()})
    level_delta = {}
    for lvl in level_names:
        rar = per_level.get("RAR", {}).get(lvl, {})
        safe = per_level.get("RAR-SAFE", {}).get(lvl, {})
        level_delta[lvl] = {
            "RAR": rar,
            "RAR-SAFE": safe,
            "correct_before": rar.get("CORRECT_RESOLUTION", 0),
            "correct_after": safe.get("CORRECT_RESOLUTION", 0),
            "unsafe_before": rar.get("INCORRECT_CONFIDENT_BINDING", 0),
            "unsafe_after": safe.get("INCORRECT_CONFIDENT_BINDING", 0),
        }

    # Per-case:ref paired comparison (RAR vs RAR-SAFE) at C1/C2 to find every
    # coverage loss (correct -> abstention) individually (mission §6/§15).
    by_key: Dict[tuple, dict] = {}
    for r in records:
        if r["c_axis"] not in ("C1", "C2"):
            continue
        key = (r["case_id"], r["ref_key"], r["c_axis"])
        by_key.setdefault(key, {})[r["variant"]] = r

    coverage_losses = []
    new_safety_gains = []
    regressions = []
    for key, pair in by_key.items():
        rar = pair.get("RAR")
        safe = pair.get("RAR-SAFE")
        if rar is None or safe is None:
            continue
        rar_sc = rar["scoring_class"]
        safe_sc = safe["scoring_class"]
        if rar_sc == "CORRECT_RESOLUTION" and safe_sc != "CORRECT_RESOLUTION":
            coverage_losses.append({
                "case_id": key[0], "ref_key": key[1], "c_axis": key[2],
                "rar_outcome": rar["actual_outcome"], "rar_candidate_id": rar["actual_candidate_id"],
                "safe_outcome": safe["actual_outcome"], "safe_scoring_class": safe_sc,
            })
        if rar_sc == "INCORRECT_CONFIDENT_BINDING" and safe_sc != "INCORRECT_CONFIDENT_BINDING":
            new_safety_gains.append({
                "case_id": key[0], "ref_key": key[1], "c_axis": key[2],
                "rar_outcome": rar["actual_outcome"], "rar_candidate_id": rar["actual_candidate_id"],
                "safe_outcome": safe["actual_outcome"], "safe_scoring_class": safe_sc,
            })
        if rar_sc != "INCORRECT_CONFIDENT_BINDING" and safe_sc == "INCORRECT_CONFIDENT_BINDING":
            regressions.append({
                "case_id": key[0], "ref_key": key[1], "c_axis": key[2],
                "rar_scoring_class": rar_sc, "safe_scoring_class": safe_sc,
                "safe_candidate_id": safe["actual_candidate_id"],
            })

    aggregates = {
        "schema": "m35.uriv1.a2_8j.aggregates.v1",
        "pre_run_sha256": telemetry_output["pre_run_sha256"],
        "post_run_sha256": telemetry_output["post_run_sha256"],
        "n_ground_truth_rows_per_variant_per_c": len([r for r in gt_records if r["variant"] == "RAR" and r["c_axis"] == "C1"]),
        "scoring_class_totals_by_variant": scoring_class_totals,
        "per_cell_scoring_class_counts": per_variant_cell,
        "per_level_breakdown": per_level,
        "per_level_before_after": level_delta,
        "coverage_losses_correct_to_abstention": coverage_losses,
        "new_safety_gains_icb_to_safe": new_safety_gains,
        "regressions_new_icb_under_safe": regressions,
        "invented_candidate_count": invented_candidate_count,
        "boundary_violation_count": boundary_violation_count,
    }
    return aggregates


def main() -> None:
    telemetry_output = run_battery()
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(telemetry_output, f, indent=2)

    aggregates = compute_aggregates(telemetry_output)
    with open(AGGREGATES_PATH, "w", encoding="utf-8") as f:
        json.dump(aggregates, f, indent=2)

    print(f"Wrote {len(telemetry_output['records'])} telemetry records to {TELEMETRY_PATH}")
    print(f"Wrote aggregates to {AGGREGATES_PATH}")
    print(f"Pre-run SHA-256:  {telemetry_output['pre_run_sha256']}")
    print(f"Post-run SHA-256: {telemetry_output['post_run_sha256']}")
    print(f"Coverage losses (correct->abstention): {len(aggregates['coverage_losses_correct_to_abstention'])}")
    print(f"New safety gains (ICB->safe): {len(aggregates['new_safety_gains_icb_to_safe'])}")
    print(f"Regressions (new ICB under RAR-SAFE): {len(aggregates['regressions_new_icb_under_safe'])}")
    print(f"Invented candidates: {aggregates['invented_candidate_count']}")
    print(f"Boundary violations: {aggregates['boundary_violation_count']}")


if __name__ == "__main__":
    main()
