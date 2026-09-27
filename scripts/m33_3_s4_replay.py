"""Offline M33.3 S4 replay; frozen resolver and detectors are read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from m35_a2_8j_rar_safe_battery import (  # noqa: E402
    boundary_violation,
    build_query,
    find_matching_found_expr,
    run_d1rq_case,
)
from m35_a2_8f_detector_d1r import detect_references as d1r_detect  # noqa: E402
from m35_rar_natural_boundary_harness import build_candidate_pool  # noqa: E402
from m33_3_s4_source_to_candidate import build_snapshot, make_envelope, project  # noqa: E402
from uri_v1.reference_clarification.authority import classify_authority  # noqa: E402
from uri_v1.turn.contracts import AttachmentReference  # noqa: E402
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended  # noqa: E402
from uri_v1.turn.turn_frame_builder import build_turn_frame  # noqa: E402

CORPUS = ROOT / "uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json"
# R2 = upstream recovery replay. R1 files are kept as the pre-recovery evidence.
TELEMETRY = ROOT / "docs/plans/M33_3_S4_R2_TELEMETRY.json"
AGGREGATES = ROOT / "docs/plans/M33_3_S4_R2_AGGREGATES.json"
ANCHORS = {
    "uri_v1/turn/rar_natural_boundary_raw_turn_fixtures.json": "0ea5447354481041181538244ef70b6dc58a72267dd95263d61dbdb55ab07380",
    # Recovery targets (RC-5 contrast gate; NP preposition boundary). Pre-recovery anchors:
    # rar_deterministic e02af25b...8fb649, D1R 03479773...41be75, D1RQ 49f5faa9...fb6b82.
    "uri_v1/turn/rar_deterministic.py": "4db775666868e09a9f7232707d67ec3b4070970a30145ad3c5b41bb86b5e1b95",
    "uri_v1/turn/rar_contracts.py": "4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819",
    "fixtures/m33_3_batch_a/battery.json": "06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa",
    "uri_v1/turn/rar_attachment_order_experimental.py": "90d89c372e7618f3476719ed1acebcb81cdb0907b4723b695ec6d4a4f289f79c",
    "uri_v1/turn/rar_attachment_order_factorial_fixtures.py": "3657070635827bf9850d11aafe7cdd0c47bd7c7c7747025de6cb17227566315a",
    "scripts/m35_a2_8f_detector_d1r.py": "0986503dd46e87773f2303e612ed8b552500588f9a027b5c9aab6795615ec8b3",
    "scripts/m35_a2_8h_detector_d1rq.py": "42332d28eca4db3533a54174a3386e573b4e5495120ad3d537dd918d8aa80862",
}


def run_d0_case(raw_text: str, turn_attachments):
    frame = build_turn_frame(
        raw_text,
        attachments=tuple(AttachmentReference(identifier=a) for a in turn_attachments),
    )
    return [
        {"span": ref.expression,
         "recency_hint": "same" if ref.expression in ("same", "same thing") else None,
         "negation_spans": frame.negation_spans, "coarse_type": None}
        for ref in frame.candidate_references
    ]


def run_d1r_case(raw_text: str):
    return [
        {"span": ref.span, "recency_hint": ref.recency_hint,
         "negation_spans": ref.negation_spans, "coarse_type": ref.coarse_type,
         "mechanism": ref.mechanism}
        for ref in d1r_detect(raw_text)
    ]


def verify_anchors() -> dict[str, str]:
    actual = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ANCHORS}
    changed = [name for name, digest in actual.items() if digest != ANCHORS[name]]
    if changed:
        raise RuntimeError(f"FROZEN_ANCHOR_INTEGRITY_FAILURE: {changed}")
    return actual


def classify(expected: str, intended: list[str], outcome: str, candidate_id: str | None) -> str:
    if expected == "UNATTRIBUTED_DETECTOR_FIND":
        return "UNATTRIBUTED_DETECTOR_FIND"
    if expected == "NO_REFERENCE":
        if outcome == "NO_DETECTION":
            return "CORRECT_NO_REFERENCE"
        return "FALSE_POSITIVE_BINDING" if outcome == "RESOLVED" else "FALSE_POSITIVE_SAFE_ABSTENTION"
    if outcome == "NO_DETECTION":
        return "SILENT_DETECTION_MISS" if expected == "RESOLVED" else "NO_DETECTION_ABSTENTION"
    if outcome == "RESOLVED":
        return "CORRECT_RESOLUTION" if expected == "RESOLVED" and candidate_id in intended else "INCORRECT_CONFIDENT_BINDING"
    if expected == "RESOLVED":
        return "MISSED_RESOLVABLE_CASE"
    if expected in ("AMBIGUOUS", "UNKNOWN"):
        return "CORRECT_ABSTENTION" if outcome == expected else "ABSTENTION_FAMILY_MISMATCH"
    return "UNCLASSIFIED"


WRONG_BINDING = ("INCORRECT_CONFIDENT_BINDING", "FALSE_POSITIVE_BINDING")


def _producer_only(wrong: list[dict]) -> list[dict]:
    control = {(r["case_id"], r["arm"], r["condition"], r["ref_key"]) for r in wrong if r["path"] == "control"}
    return [r for r in wrong if r["path"] == "producer" and (r["case_id"], r["arm"], r["condition"], r["ref_key"]) not in control]


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (index - low), 3)


def _detected(arm: str, case: dict) -> tuple[list[dict], float]:
    start = time.perf_counter_ns()
    raw = case["raw_user_text"]
    if arm == "D0":
        found = run_d0_case(raw, case["conversation_context"].get("turn_attachments") or ())
    elif arm == "D1R":
        found = run_d1r_case(raw)
    else:
        found = run_d1rq_case(raw)
    return found, (time.perf_counter_ns() - start) / 1000


def _expected(variant: dict | None, ref_key: str | None, has_reference: bool,
              case_has_references: bool) -> tuple[str, list[str]]:
    if not has_reference:
        return ("UNATTRIBUTED_DETECTOR_FIND" if case_has_references else "NO_REFERENCE"), []
    if variant is None:
        return "UNKNOWN", []
    item = next((x for x in variant["expected_by_reference"] if x["ref_key"] == ref_key), None)
    if item is None:
        raise RuntimeError("missing scorer reference")
    return item["expected_outcome"], list(item.get("intended_candidate_ids") or ())


def replay() -> tuple[dict, dict]:
    pre_hashes = verify_anchors()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    library = corpus["candidate_library"]
    rows: list[dict] = []
    for case in corpus["cases"]:
        raw = case["raw_user_text"]
        context = case["conversation_context"]
        references = case["ground_truth_references"]  # scorer only, after producer inputs are built
        variants = {v["candidate_condition"]: v for v in case["variants"]}
        for arm in ("D0", "D1R", "D1RQ"):
            found, detector_us = _detected(arm, case)
            spans = [f["span"] for f in found]
            used: set[str] = set()
            attributed: list[tuple[str | None, dict | None, bool]] = []
            for gt in references:
                span = find_matching_found_expr(gt.get("human_marked_span"), spans, used)
                if span is not None:
                    used.add(span)
                attributed.append((gt["ref_key"], next((f for f in found if f["span"] == span), None), True))
            for f in found:
                if f["span"] not in used:
                    attributed.append((None, f, False))
            if not attributed:
                attributed.append((None, None, False))
            for condition in ("C1", "C2", "C3"):
                variant = variants.get(condition) if condition != "C3" else None
                ids = tuple(variant["available_candidates"]) if variant else ()
                # Positive input allowlist: no scorer field, case copy, or variant copy crosses this call.
                started = time.perf_counter_ns()
                snapshot = build_snapshot(raw, context, ids, library)
                envelope = make_envelope(snapshot)
                snapshot_us = (time.perf_counter_ns() - started) / 1000
                control_candidates = build_candidate_pool(ids, library, oracle_recency=False)
                if tuple(c.id for c in control_candidates) != envelope.authorized_ids:
                    raise RuntimeError("control/producer candidate set mismatch")
                provenance = [{"candidate_id": r.candidate_id, "source_kind": r.source_kind,
                               "locator": r.locator, "authorization_basis": envelope.authorization_basis,
                               "created_at_present": r.created_at is not None}
                              for r in envelope.records]
                for ref_key, detection, has_reference in attributed:
                    expected, intended = _expected(variant, ref_key, has_reference, bool(references))
                    common = {
                        "case_id": case["case_id"], "arm": arm, "condition": condition,
                        "ref_key": ref_key, "expected_outcome": expected,
                        "intended_candidate_ids": intended, "source_ids": list(envelope.authorized_ids),
                        "provenance": provenance, "record_bytes": snapshot.record_bytes,
                        "candidate_count": len(envelope.authorized_ids),
                        "detector_us": round(detector_us, 3), "snapshot_us": round(snapshot_us, 3),
                        "grounded_target_present": bool(intended) and set(intended).issubset(ids),
                    }
                    if detection is None:
                        for path in ("control", "producer"):
                            rows.append({**common, "path": path, "detected": False,
                                         "outcome": "NO_DETECTION", "candidate_id": None,
                                         "rule_used": None, "anchor_origin": "none", "authority_class": None,
                                         "project_us": 0,
                                         "resolver_us": 0, "full_boundary_us": round(detector_us + snapshot_us, 3),
                                         "classification": classify(expected, intended, "NO_DETECTION", None)})
                        continue
                    if boundary_violation(detection["span"], ids, raw):
                        raise RuntimeError("detector invented candidate ID")
                    for path in ("control", "producer"):
                        proj_start = time.perf_counter_ns()
                        if path == "control":
                            query = build_query(detection["span"], control_candidates,
                                                detection.get("recency_hint"), detection.get("negation_spans") or (),
                                                detection.get("coarse_type"))
                            anchor_origin = "none"
                        else:
                            query, anchor_origin = project(snapshot, envelope, detection["span"],
                                                           detection.get("recency_hint"), detection.get("negation_spans") or (),
                                                           detection.get("coarse_type"))
                        project_us = (time.perf_counter_ns() - proj_start) / 1000
                        if query.candidate_ids != envelope.authorized_ids:
                            raise RuntimeError("candidate invention or omission")
                        resolve_start = time.perf_counter_ns()
                        trace = resolve_rar_deterministic_extended(query)
                        resolver_us = (time.perf_counter_ns() - resolve_start) / 1000
                        result = trace.resolution
                        if result.candidate_id and result.candidate_id not in ids:
                            raise RuntimeError("resolver returned unauthorized ID")
                        outcome = result.outcome.value
                        rows.append({**common, "path": path, "detected": True,
                                     "outcome": outcome, "candidate_id": result.candidate_id,
                                     "ambiguous_candidate_ids": list(result.ambiguous_candidate_ids),
                                     "rule_used": trace.rule_used.value, "anchor_origin": anchor_origin,
                                     "authority_class": classify_authority(result, query).value,
                                     "project_us": round(project_us, 3), "resolver_us": round(resolver_us, 3),
                                     "full_boundary_us": round(detector_us + snapshot_us + project_us + resolver_us, 3),
                                     "classification": classify(expected, intended, outcome, result.candidate_id)})
    post_hashes = verify_anchors()
    if post_hashes != pre_hashes:
        raise RuntimeError("FROZEN_ANCHOR_INTEGRITY_FAILURE after replay")
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[f"{row['arm']}:{row['condition']}:{row['path']}"].append(row)
    aggregates = {}
    for key, subset in sorted(groups.items()):
        counts = Counter(r["classification"] for r in subset)
        times = [r["full_boundary_us"] for r in subset]
        prep = [r["detector_us"] + r["snapshot_us"] + r["project_us"] for r in subset]
        target_rows = [r for r in subset if r["intended_candidate_ids"]]
        aggregates[key] = {
            "rows": len(subset), "classification_counts": dict(sorted(counts.items())),
            "grounded_target_coverage": sum(r["grounded_target_present"] for r in target_rows),
            "grounded_target_denominator": len(target_rows),
            "incorrect_confident_bindings": counts["INCORRECT_CONFIDENT_BINDING"] + counts["FALSE_POSITIVE_BINDING"],
            "certainty_authority_rows": sum(r["authority_class"] == "CERTAINTY" for r in subset),
            "preparation_p50_us": _percentile(prep, .5), "preparation_p95_us": _percentile(prep, .95),
            "full_boundary_p50_us": _percentile(times, .5), "full_boundary_p95_us": _percentile(times, .95),
        }
    wrong = [r for r in rows if r["classification"] in WRONG_BINDING]
    attachment_certainty = [r for r in rows if r["authority_class"] == "CERTAINTY"
                            and "current_attachment" in r["anchor_origin"]]
    summary = {
        "schema": "m33.3.s4.offline_replay.v3",
        "gates": {
            "candidate_invention_or_unauthorized_source": 0,  # enforced by fail-closed runtime checks above
            "protected_hashes_unchanged": post_hashes == pre_hashes,
            "false_certainty_authority_on_scored_rows": sum(r["authority_class"] == "CERTAINTY" for r in wrong),
            "certainty_authority_on_unattributed_rows": sum(
                r["authority_class"] == "CERTAINTY" and r["classification"] == "UNATTRIBUTED_DETECTOR_FIND" for r in rows),
            "annotated_wrong_binding_rows": len(wrong),
            "annotated_wrong_binding_cases": sorted({f"{r['case_id']}:{r['ref_key'] or '-'}" for r in wrong}),
            "producer_only_wrong_binding_rows": len(_producer_only(wrong)),
            "safety_gate_passed": not wrong,
            # Turn-scoped attachment anchor (User decision A-F3): disclosed exposure, not production-approved.
            "attachment_anchor_certainty_rows": len(attachment_certainty),
            "attachment_anchor_certainty_unattributed_rows": sum(
                r["classification"] == "UNATTRIBUTED_DETECTOR_FIND" for r in attachment_certainty),
            "attachment_anchor_certainty_cases": sorted({r["case_id"] for r in attachment_certainty}),
        }, "case_count": len(corpus["cases"]),
        "row_count": len(rows), "frozen_hashes": pre_hashes, "groups": aggregates,
        "provider_coverage": "UNMEASURED", "cpu_ram_resource_cost": "UNMEASURED",
        "promotion_eligible": False,
        "limitation": "Synthetic fixed corpus predates producer, but D1R/D1RQ were previously run on it; no live-provider or independent detector-generalization claim.",
    }
    return {"schema": summary["schema"], "rows": rows}, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    telemetry, aggregates = replay()
    if args.write:
        TELEMETRY.write_text(json.dumps(telemetry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        AGGREGATES.write_text(json.dumps(aggregates, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": aggregates["row_count"], "cases": aggregates["case_count"],
                      "wrong_confident": sum(v["incorrect_confident_bindings"] for v in aggregates["groups"].values()),
                      "groups": len(aggregates["groups"])}, sort_keys=True))


if __name__ == "__main__":
    main()
