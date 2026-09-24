"""M35 URIv1 -- A2.8K: Level-5 Evidence Sufficiency & Attachment Ordering
Diagnostic Qualification Battery.

Benchmark-only. Runs H0 (baseline `resolve_rar_deterministic_extended`),
H1-H4 and DX-1 (all via `resolve_rar_l5_experimental`) across the five
measurement surfaces the accepted plan defines (§4):

  S-A  Production-shaped: D1RQ spans + D1RQ hints, all ranks 0, natural
       corpus, C1/C2/C3.
  S-B  Realistic hints, real ranks: D1RQ spans + D1RQ hints, created_at
       ranks, natural corpus, C1/C2.
  S-C  Oracle (Probe A generalised): ground-truth span + oracle hint
       mapping, created_at ranks, all 168 C1/C2 reference rows.
  S-D  Frozen minimal pairs (`uri_v1/turn/rar_l5_diagnostic_fixtures.py`).
  S-E  Existing RAR tests: the four A2.5 RAR test modules, resolver swapped
       in per variant via namespace monkeypatch (no test file is edited on
       disk -- the patch is undone after each variant).

Reuses existing, unmodified scripts/modules by import rather than
duplicating their logic: `m35_a2_8j_rar_safe_battery` (D1RQ pipeline,
scoring-class classification, boundary-violation check, RULE_TO_LEVEL) and
`m35_rar_natural_boundary_harness` (fixture loading, candidate-pool
construction, oracle temporal-meaning mapping). Neither is modified.

Integrity checks: SHA-256 of every protected file (plan §9.1, directive §18)
before and after; the battery is run twice and decision outputs (outcome,
candidate_id, ambiguous_candidate_ids) must be identical between runs
(latency excluded) -- see `main()`.

**A2.8K-R1 repair (bounded, post-independent-audit):** the independent final
audit (`docs/plans/M35_URIV1_A2_8K_INDEPENDENT_FINAL_AUDIT.md`, verdict
`REPAIR_REQUIRED`) found two defects in this script and in
`uri_v1/turn/rar_l5_experimental.py`, both now repaired here:

- **R1-A** (in `rar_l5_experimental.py`, not this file): H3 filtered the
  candidate domain but evaluated ordinal position using candidates' original
  global `recency_rank`, not their position within the filtered domain.
- **R1-B** (this file, `compute_aggregates`): the changed-row comparator
  used `(scoring_class, actual_candidate_id)` and missed
  `AMBIGUOUS`->`UNKNOWN` transitions that kept the same coarse scoring
  class. It now compares the full decision tuple (outcome, candidate id,
  ambiguous-id set) via `_decision_tuple`, with an independent
  `reconciliation_check` recomputing the same counts by a direct re-scan.

This script's own output paths were changed to `_R1_TELEMETRY.json` /
`_R1_AGGREGATES.json` so the pre-repair `M35_URIV1_A2_8K_TELEMETRY.json` /
`_AGGREGATES.json` the audit measured remain on disk, untouched, as the
historical record.

**A2.8K-R2 repair (bounded, post-R1-independent-re-audit):** the R1
independent re-audit found R1-A's domain-relative re-ranking activated even
when H3's lexical filter did not genuinely narrow the candidate pool,
fabricating a rank-0 winner in domains baseline deliberately left without
one (`test_rc1_current_conflicting_no_rank0_abstains`). The fix (an
activation-boundary check, `_h3_narrowed`, comparing candidate ID membership
before/after H3's filter) is entirely in `rar_l5_experimental.py`; this
script's R1-B accounting logic is unchanged (no defect was found in it).
Output paths bumped again to `_R2_TELEMETRY.json` / `_R2_AGGREGATES.json` so
both the original and R1 evidence remain on disk, untouched.
"""

from __future__ import annotations

import functools
import hashlib
import importlib
import json
import sys
import unittest
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import m35_a2_8j_rar_safe_battery as j8j  # noqa: E402
import m35_rar_natural_boundary_harness as nbh  # noqa: E402
from m35_a2_8h_detector_d1rq import detect_references as d1rq_detect  # noqa: E402

from uri_v1.turn.rar_contracts import RARQuery  # noqa: E402
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended  # noqa: E402
from uri_v1.turn.rar_l5_experimental import resolve_rar_l5_experimental  # noqa: E402
from uri_v1.turn.rar_l5_diagnostic_fixtures import (  # noqa: E402
    L5_DIAGNOSTIC_METADATA,
    get_l5_diagnostic_fixtures,
)

# A2.8K-R1 repair: R1-A (H3 filtered-domain ordinal ranking) and R1-B (full
# decision-transition accounting) both change this script's own logic, so
# its output is no longer the same evidence the independent audit measured.
# Per the repair directive ("New R1 outputs must be clearly distinguishable
# ... Do not silently overwrite files whose contents were used by the
# independent audit"), this rerun writes to `_R1_` paths. The original
# `M35_URIV1_A2_8K_TELEMETRY.json` / `_AGGREGATES.json` produced before this
# repair are left on disk, untouched, as the historical pre-repair record.
# A2.8K-R2 repair: the R1 independent re-audit found one further defect
# (H3's domain-relative re-ranking activated even when the lexical filter
# did not genuinely narrow the pool). That is fixed in
# `rar_l5_experimental.py` (the activation-boundary check, `_h3_narrowed`);
# this script's own R1-B accounting logic is unchanged (the R1 audit found
# no defect in it). Output paths bumped to `_R2_` so the R1 evidence this
# repair responds to, and the original pre-R1 evidence, both remain on disk
# untouched.
TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8K_R2_TELEMETRY.json"
AGGREGATES_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8K_R2_AGGREGATES.json"

PROTECTED_FILES = {
    "rar_deterministic.py": REPO_ROOT / "uri_v1" / "turn" / "rar_deterministic.py",
    "rar_contracts.py": REPO_ROOT / "uri_v1" / "turn" / "rar_contracts.py",
    "rar_safe_experimental.py": REPO_ROOT / "uri_v1" / "turn" / "rar_safe_experimental.py",
    "d1rq_detector.py": REPO_ROOT / "scripts" / "m35_a2_8h_detector_d1rq.py",
    "corpus.json": nbh.FIXTURE_PATH,
    "sd_fixtures.py": REPO_ROOT / "uri_v1" / "turn" / "rar_l5_diagnostic_fixtures.py",
}

VARIANT_NAMES = ["H0", "H1", "H2", "H3", "H4", "DX1"]


def _resolver_for(variant: str, dx1_tie_ids: FrozenSet[str] = frozenset()):
    if variant == "H0":
        return resolve_rar_deterministic_extended
    flags = {
        "H1": dict(h1=True),
        "H2": dict(h2=True),
        "H3": dict(h3=True),
        "H4": dict(h1=True, h2=True, h3=True),
        "DX1": dict(dx1_tie_ids=dx1_tie_ids),
    }[variant]
    return functools.partial(resolve_rar_l5_experimental, **flags)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _protected_hashes() -> Dict[str, str]:
    return {name: sha256_of(p) for name, p in PROTECTED_FILES.items()}


def _decision(trace) -> dict:
    return {
        "outcome": trace.resolution.outcome.value,
        "candidate_id": trace.resolution.candidate_id,
        "ambiguous_candidate_ids": list(trace.resolution.ambiguous_candidate_ids),
        "rule_used": trace.rule_used.value if trace.rule_used else None,
        "failure_class": trace.failure_class.value if trace.failure_class else None,
    }


# ---------------------------------------------------------------------------
# S-A / S-B: D1RQ-detected span + D1RQ hint, natural corpus
# ---------------------------------------------------------------------------

def _run_d1rq_surface(surface: str, oracle_recency: bool, c_axes: Sequence[str]) -> List[dict]:
    data = nbh.load_fixture()
    library = data["candidate_library"]
    cases = data["cases"]
    rows: List[dict] = []

    for case in cases:
        case_id = case["case_id"]
        category = case["category"]
        raw_text = case["raw_user_text"]
        gt_refs = case["ground_truth_references"]
        gt_by_key = {r["ref_key"]: r for r in gt_refs}
        variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}
        turn_attachments = set(case.get("conversation_context", {}).get("turn_attachments") or ())

        d1rq_found = j8j.run_d1rq_case(raw_text)
        found_spans = [f["span"] for f in d1rq_found]

        for variant_name in VARIANT_NAMES:
            used_spans: set = set()
            match_for_ref: Dict[str, Optional[dict]] = {}
            for ref_key, gt in gt_by_key.items():
                m_expr = j8j.find_matching_found_expr(gt.get("human_marked_span"), found_spans, used_spans)
                if m_expr is not None:
                    used_spans.add(m_expr)
                    match_for_ref[ref_key] = next(f for f in d1rq_found if f["span"] == m_expr)
                else:
                    match_for_ref[ref_key] = None

            for c_axis in c_axes:
                if c_axis == "C3":
                    candidate_ids: Sequence[str] = ()
                    variant = None
                else:
                    variant = variants_by_cond[c_axis]
                    candidate_ids = variant["available_candidates"]
                candidates = nbh.build_candidate_pool(candidate_ids, library, oracle_recency=oracle_recency)
                dx1_tie_ids = frozenset(turn_attachments & set(candidate_ids))
                resolver_fn = _resolver_for(variant_name, dx1_tie_ids)

                expected_by_ref = {}
                if variant is not None:
                    for eb in variant["expected_by_reference"]:
                        expected_by_ref[eb["ref_key"]] = eb

                if not gt_refs:
                    continue  # no-reference rows are not the target of this qualification; skip (S-A/S-B focus on scored references)

                for ref_key, gt in gt_by_key.items():
                    eb = expected_by_ref.get(ref_key, {})
                    expected_outcome = eb.get("expected_outcome", "UNKNOWN")
                    intended_ids = eb.get("intended_candidate_ids", [])
                    f = match_for_ref.get(ref_key)
                    if f is None:
                        rows.append(_row(
                            surface, case_id, category, variant_name, c_axis, ref_key, None,
                            expected_outcome, intended_ids, candidate_ids, None, None,
                            scoring_class_override="SILENT_DETECTION_MISS",
                        ))
                        continue
                    bv = j8j.boundary_violation(f["span"], candidate_ids, raw_text)
                    if bv:
                        rows.append(_row(
                            surface, case_id, category, variant_name, c_axis, ref_key, f["span"],
                            expected_outcome, intended_ids, candidate_ids, f, None, boundary_violation=True,
                        ))
                        continue
                    q = j8j.build_query(f["span"], candidates, f["recency_hint"], f["negation_spans"], f.get("coarse_type"))
                    trace = resolver_fn(q)
                    rows.append(_row(
                        surface, case_id, category, variant_name, c_axis, ref_key, f["span"],
                        expected_outcome, intended_ids, candidate_ids, f, trace,
                    ))
    return rows


# ---------------------------------------------------------------------------
# S-C: oracle span + oracle hint mapping, real ranks, all C1/C2 rows
# ---------------------------------------------------------------------------

def _run_oracle_surface() -> List[dict]:
    data = nbh.load_fixture()
    library = data["candidate_library"]
    cases = data["cases"]
    rows: List[dict] = []

    for case in cases:
        case_id = case["case_id"]
        category = case["category"]
        gt_refs = case["ground_truth_references"]
        variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}
        turn_attachments = set(case.get("conversation_context", {}).get("turn_attachments") or ())

        for variant_name in VARIANT_NAMES:
            for c_axis in ("C1", "C2"):
                variant = variants_by_cond.get(c_axis)
                if variant is None:
                    continue
                candidate_ids = variant["available_candidates"]
                candidates = nbh.build_candidate_pool(candidate_ids, library, oracle_recency=True)
                dx1_tie_ids = frozenset(turn_attachments & set(candidate_ids))
                resolver_fn = _resolver_for(variant_name, dx1_tie_ids)
                expected_by_ref = {eb["ref_key"]: eb for eb in variant["expected_by_reference"]}

                for gt in gt_refs:
                    ref_key = gt["ref_key"]
                    eb = expected_by_ref.get(ref_key, {})
                    expected_outcome = eb.get("expected_outcome", "UNKNOWN")
                    intended_ids = eb.get("intended_candidate_ids", [])
                    q = nbh.s2_query_for_reference(gt, candidates)
                    trace = resolver_fn(q)
                    rows.append(_row(
                        "S-C", case_id, category, variant_name, c_axis, ref_key,
                        gt.get("human_marked_span") or gt.get("implicit_antecedent"),
                        expected_outcome, intended_ids, candidate_ids, None, trace,
                    ))
    return rows


# ---------------------------------------------------------------------------
# S-D: frozen minimal pairs
# ---------------------------------------------------------------------------

def _run_sd_surface() -> List[dict]:
    rows: List[dict] = []
    for fix in get_l5_diagnostic_fixtures():
        meta = L5_DIAGNOSTIC_METADATA[fix.id]
        intended_ids = [fix.expected_candidate_id] if fix.expected_candidate_id else list(fix.expected_ambiguous_candidate_ids)
        for variant_name in VARIANT_NAMES:
            resolver_fn = _resolver_for(variant_name, meta.dx1_tie_ids)
            trace = resolver_fn(fix.query)
            rows.append(_row(
                "S-D", fix.id, fix.category, variant_name, "SD", fix.id, fix.turn_text,
                fix.expected_outcome.value, intended_ids,
                [c.id for c in fix.query.candidates], None, trace,
                scoring_class_override=("MEASURE_ONLY" if meta.measure_only else None),
            ))
    return rows


# ---------------------------------------------------------------------------
# S-E: existing A2.5 RAR test modules, resolver monkeypatched per variant
# ---------------------------------------------------------------------------

SE_TEST_MODULES = [
    "test_m35_uriv1_a2_5_deterministic_rar",
    "test_m35_uriv1_a2_5_rar_adversarial_safety",
    "test_m35_uriv1_a2_5_rar_contracts",
    "test_m35_uriv1_a2_5_rar_stage4_refinements",
]


def _run_se_surface() -> List[dict]:
    """Runs each existing A2.5 test module once per variant, with
    `resolve_rar_deterministic_extended` monkeypatched IN THAT MODULE'S OWN
    IMPORTED-NAME BINDING to the variant resolver, then restored. No test
    file on disk is edited (plan §9.8 / directive §18)."""
    rows: List[dict] = []
    sys.path.insert(0, str(REPO_ROOT))
    for module_name in SE_TEST_MODULES:
        module = importlib.import_module(module_name)
        if not hasattr(module, "resolve_rar_deterministic_extended"):
            # This module (rar_contracts) tests resolve_rar_deterministically
            # and the RARFixture/contract invariants directly -- it never
            # calls the Level 0-7 cascade this batch experiments on, so
            # there is nothing to swap. Recorded as N/A, not skipped
            # silently: still counted in the report's S-E coverage table.
            rows.append({
                "surface": "S-E", "case_id": module_name, "variant": "N/A",
                "tests_run": 0, "failures": 0, "errors": 0, "conflicting_tests": [],
                "scoring_class": "S_E_NOT_APPLICABLE",
            })
            continue
        original = module.resolve_rar_deterministic_extended
        try:
            for variant_name in VARIANT_NAMES:
                resolver_fn = _resolver_for(variant_name)
                module.resolve_rar_deterministic_extended = resolver_fn
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromModule(module)
                result = unittest.TestResult()
                suite.run(result)
                conflicts = []
                for test, err in result.failures + result.errors:
                    conflicts.append(str(test))
                rows.append({
                    "surface": "S-E", "case_id": module_name, "variant": variant_name,
                    "tests_run": result.testsRun, "failures": len(result.failures),
                    "errors": len(result.errors), "conflicting_tests": conflicts,
                    "scoring_class": "S_E_PASS" if not conflicts else "S_E_CONFLICT",
                })
        finally:
            module.resolve_rar_deterministic_extended = original
    return rows


# ---------------------------------------------------------------------------
# Row builder / classification (D1RQ + oracle + S-D surfaces; S-E uses its
# own row shape above)
# ---------------------------------------------------------------------------

def _row(surface, case_id, category, variant, c_axis, ref_key, span, expected_outcome,
         intended_ids, candidate_ids, found, trace, boundary_violation=False,
         scoring_class_override=None):
    row = {
        "surface": surface, "case_id": case_id, "category": category,
        "variant": variant, "cell": f"{surface}:{variant}x{c_axis}", "c_axis": c_axis,
        "ref_key": ref_key, "detected_span": span, "expected_outcome": expected_outcome,
        "intended_candidate_ids": intended_ids, "candidate_ids_supplied": list(candidate_ids),
        "signals_supplied": {
            "recency_hint": found.get("recency_hint") if found else None,
            "negation_spans": list(found.get("negation_spans") or ()) if found else [],
        } if found else {},
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
            "level": j8j.RULE_TO_LEVEL.get(rule_val, "UNKNOWN") if rule_val else None,
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
        row["scoring_class"] = j8j._classify(row)
    return row


# ---------------------------------------------------------------------------
# Battery driver
# ---------------------------------------------------------------------------

def run_battery() -> dict:
    pre_hashes = _protected_hashes()

    records: List[dict] = []
    records += _run_d1rq_surface("S-A", oracle_recency=False, c_axes=("C1", "C2", "C3"))
    records += _run_d1rq_surface("S-B", oracle_recency=True, c_axes=("C1", "C2"))
    records += _run_oracle_surface()
    records += _run_sd_surface()
    se_records = _run_se_surface()

    post_hashes = _protected_hashes()

    return {
        "schema": "m35.uriv1.a2_8k.r2.telemetry.v1",
        "pre_run_protected_hashes": pre_hashes,
        "post_run_protected_hashes": post_hashes,
        "variants": VARIANT_NAMES,
        "records": records,
        "se_records": se_records,
    }


def _decision_tuple(row: dict) -> tuple:
    """A2.8K-R1 repair R1-B: the full decision a row represents, for
    reconciliation. Two rows are the same decision iff outcome, candidate
    id, AND the ambiguous-candidate SET (frozenset -- order carries no
    semantic meaning) are all equal. Used instead of `(scoring_class,
    candidate_id)` for changed-row detection (see call site)."""
    return (
        row.get("actual_outcome"),
        row.get("actual_candidate_id"),
        frozenset(row.get("actual_ambiguous_ids") or ()),
    )


def compute_aggregates(telemetry_output: dict) -> dict:
    records = telemetry_output["records"]
    se_records = telemetry_output["se_records"]

    scoring_class_totals: Dict[str, Dict[str, int]] = {}
    per_surface_variant: Dict[str, Dict[str, Dict[str, int]]] = {}
    per_level: Dict[str, Dict[str, Dict[str, int]]] = {}

    for r in records:
        v, sc, surface = r["variant"], r["scoring_class"], r["surface"]
        scoring_class_totals.setdefault(v, {})
        scoring_class_totals[v][sc] = scoring_class_totals[v].get(sc, 0) + 1
        per_surface_variant.setdefault(surface, {}).setdefault(v, {})
        per_surface_variant[surface][v][sc] = per_surface_variant[surface][v].get(sc, 0) + 1
        level = r.get("level")
        if level and r["surface"] in ("S-A", "S-B", "S-C") and r.get("c_axis") in ("C1", "C2"):
            per_level.setdefault(v, {}).setdefault(level, {})
            per_level[v][level][sc] = per_level[v][level].get(sc, 0) + 1

    # Changed rows vs H0, per surface, individually listed (plan §9.5/§15).
    by_key: Dict[tuple, dict] = {}
    for r in records:
        key = (r["surface"], r["case_id"], r["ref_key"], r["c_axis"])
        by_key.setdefault(key, {})[r["variant"]] = r

    changed_vs_h0: Dict[str, List[dict]] = {v: [] for v in VARIANT_NAMES if v != "H0"}
    new_icb_vs_h0: Dict[str, List[dict]] = {v: [] for v in VARIANT_NAMES if v != "H0"}
    closed_icb_vs_h0: Dict[str, List[dict]] = {v: [] for v in VARIANT_NAMES if v != "H0"}
    lost_correct_vs_h0: Dict[str, List[dict]] = {v: [] for v in VARIANT_NAMES if v != "H0"}

    for key, pair in by_key.items():
        h0 = pair.get("H0")
        if h0 is None:
            continue
        for v in VARIANT_NAMES:
            if v == "H0":
                continue
            other = pair.get(v)
            if other is None:
                continue
            # A2.8K-R1 repair R1-B (independent audit §22.3): a row counts
            # as "changed" iff its full decision differs -- outcome,
            # candidate_id, AND the ambiguous-candidate set (order-
            # insensitive; ambiguity is a set, not a sequence) -- not merely
            # scoring_class + candidate_id. The prior comparator missed
            # AMBIGUOUS -> UNKNOWN transitions that kept the same coarse
            # scoring_class (both MISSED_RESOLVABLE_CASE) and the same (None)
            # candidate_id, which is exactly the audit's 12 omitted H3/H4
            # rows (audit §6, §18). This is derived from the raw rows on
            # every call, not a hard-coded count.
            if _decision_tuple(h0) == _decision_tuple(other):
                continue
            entry = {
                "surface": key[0], "case_id": key[1], "ref_key": key[2], "c_axis": key[3],
                "h0_scoring_class": h0["scoring_class"], "h0_outcome": h0["actual_outcome"],
                "h0_candidate_id": h0["actual_candidate_id"],
                "h0_ambiguous_ids": h0.get("actual_ambiguous_ids") or [],
                "variant_scoring_class": other["scoring_class"], "variant_outcome": other["actual_outcome"],
                "variant_candidate_id": other["actual_candidate_id"],
                "variant_ambiguous_ids": other.get("actual_ambiguous_ids") or [],
            }
            changed_vs_h0[v].append(entry)
            if h0["scoring_class"] != "INCORRECT_CONFIDENT_BINDING" and other["scoring_class"] == "INCORRECT_CONFIDENT_BINDING":
                new_icb_vs_h0[v].append(entry)
            if h0["scoring_class"] == "INCORRECT_CONFIDENT_BINDING" and other["scoring_class"] != "INCORRECT_CONFIDENT_BINDING":
                closed_icb_vs_h0[v].append(entry)
            if h0["scoring_class"] == "CORRECT_RESOLUTION" and other["scoring_class"] != "CORRECT_RESOLUTION":
                lost_correct_vs_h0[v].append(entry)

    # S-A must be decision-identical for every variant vs H0 (regression guard, plan §4).
    s_a_diffs = {v: [e for e in changed_vs_h0[v] if e["surface"] == "S-A"] for v in changed_vs_h0}

    # R1-B reconciliation invariant (directive: "aggregate changed-row count
    # == count(raw baseline decision != variant decision)"), computed
    # independently of the loop above by a direct full re-scan of `by_key`,
    # so a future regression to the old narrowed comparator would show up
    # here as a mismatch rather than passing silently.
    reconciliation_check: Dict[str, dict] = {}
    for v in changed_vs_h0:
        raw_diff_count = 0
        for pair in by_key.values():
            h0 = pair.get("H0")
            other = pair.get(v)
            if h0 is None or other is None:
                continue
            if _decision_tuple(h0) != _decision_tuple(other):
                raw_diff_count += 1
        reconciliation_check[v] = {
            "aggregate_changed_row_count": len(changed_vs_h0[v]),
            "raw_decision_diff_count": raw_diff_count,
            "reconciled": len(changed_vs_h0[v]) == raw_diff_count,
        }

    se_conflicts = {}
    for r in se_records:
        se_conflicts.setdefault(r["variant"], {})[r["case_id"]] = {
            "tests_run": r["tests_run"], "failures": r["failures"], "errors": r["errors"],
            "conflicting_tests": r["conflicting_tests"],
        }

    return {
        "schema": "m35.uriv1.a2_8k.r2.aggregates.v1",
        "scoring_class_totals_by_variant": scoring_class_totals,
        "per_surface_variant_scoring_class_counts": per_surface_variant,
        "per_level_breakdown_s_a_b_c": per_level,
        "changed_rows_vs_h0": changed_vs_h0,
        "new_icb_vs_h0": new_icb_vs_h0,
        "closed_icb_vs_h0": closed_icb_vs_h0,
        "lost_correct_resolutions_vs_h0": lost_correct_vs_h0,
        "s_a_regression_check_diffs": s_a_diffs,
        "s_a_regression_check_passed": {v: len(diffs) == 0 for v, diffs in s_a_diffs.items()},
        "se_conflicts_by_variant": se_conflicts,
        "reconciliation_check": reconciliation_check,
    }


def main() -> None:
    run1 = run_battery()
    run2 = run_battery()

    def _decisions(output):
        return [
            (r["surface"], r["case_id"], r["ref_key"], r["c_axis"], r["variant"],
             r.get("actual_outcome"), r.get("actual_candidate_id"), tuple(r.get("actual_ambiguous_ids") or ()))
            for r in output["records"]
        ]

    determinism_ok = _decisions(run1) == _decisions(run2)

    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    telemetry_output = run1
    telemetry_output["determinism_check_passed"] = determinism_ok
    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(telemetry_output, f, indent=2)

    aggregates = compute_aggregates(telemetry_output)
    aggregates["determinism_check_passed"] = determinism_ok
    with open(AGGREGATES_PATH, "w", encoding="utf-8") as f:
        json.dump(aggregates, f, indent=2)

    print(f"Determinism check (2 runs identical): {determinism_ok}")
    print(f"Wrote {len(telemetry_output['records'])} S-A/S-B/S-C/S-D records + {len(telemetry_output['se_records'])} S-E module runs to {TELEMETRY_PATH}")
    print(f"Wrote aggregates to {AGGREGATES_PATH}")
    for v in VARIANT_NAMES:
        if v == "H0":
            continue
        print(f"  S-A regression check passed for {v}: {aggregates['s_a_regression_check_passed'].get(v)}")


if __name__ == "__main__":
    main()
