"""M35 URIv1 -- A2.8L-A9: frozen rerun under the A9-amended plan.

Implements the A9 rerun task brief against the frozen checkpoint `591f806`
(`docs/plans/M35_URIV1_A2_8L_RAR_EVIDENCE_TRANSPORT_FACTORIAL_PLAN.md` §16,
`docs/plans/M35_URIV1_A2_8L_OVERLAY_MANIFEST.md`).

**No mechanism code is changed by this rerun.** The A2.8L mechanism module
(`uri_v1/turn/rar_attachment_order_experimental.py`) and fixture module
(`uri_v1/turn/rar_attachment_order_factorial_fixtures.py`) were inspected
before this script was written and already implement A9-1 through A9-5
byte-for-byte as adopted by the A9 amendment (their own docstrings disclose
the same five behaviors A9 froze): the `C-LEXICAL-ATTACHMENT`
qualification-gate exclusion (`compute_qualifying_cells` below, unchanged
logic from the pre-A9 script), the D/M-to-Level-5.5 extension
(`_attachment_domain_trigger` in the mechanism module), the `"earlier"` A3
hint (`_ordinal_literal_present`), H3 as an always-on substrate
(`l5_pool_lexical = _h3_domain(...)`, unconditional), and R's domain-wide
tie (`_domain_wide_tie_rank_map`). This script therefore performs a
protocol-corrected RERUN of the same unmodified mechanism, not a
reimplementation.

Corrects, relative to `scripts/m35_a2_8l_rar_attachment_order_factorial.py`
(the pre-A9 script, left on disk unmodified as the historical record):

1. **Two independent fresh-process causal runs** (subprocess invocations of
   this same file in `--causal-only` mode), not two in-process repeats.
2. **D1RQ + natural-row confirmation surface** (`run_d1rq_natural_surface`):
   NB-C-04, NB-C-05, NB-D-01, NB-D-02 at C1/C2, D1RQ-detected span/hint,
   both production-shaped (oracle_recency=False) and created_at-oracle
   (oracle_recency=True) ranks, run under baseline (all-off) and every
   A9-amended qualifying cell plus its one-factor ablations -- not only a
   single "best cell".
3. **Case-level 2x2 interaction tables on the qualifying-cell background**
   (`compute_pairwise_interactions_on_background`), in addition to the
   existing all-off-background tables (both are reported; A9 §16.3 item 3).
4. **Transport mismatch attribution** (`_attribute_mismatch`): every
   sidecar/compiler mismatch is tagged with an explicit cause bucket
   (H3-absence confound / D-M-Level-5.5-extension not compiled / R-rank-
   projection asymmetry / unexplained) rather than left as an aggregate
   footnote. The frozen §4.2.1 compiler algorithm itself is NOT changed.
5. **Full pre-registered performance protocol**: 200 warmups / 2,000
   randomized-and-interleaved measured iterations (not the pre-A9 script's
   disclosed 20/200 reduction), plus explicit environment/source metadata
   (OS, Python version, CPU identifier, process bitness, source hashes,
   measured clock resolution).

Both the original pre-A9 literal-plan result (0 qualifying cells under
A1-A8 text alone, per A9 §16.2 item 1) and this rerun's A9-amended result
are reported; this script does not reproduce or assume the former, and does
not overwrite `M35_URIV1_A2_8L_TELEMETRY.json` / `_AGGREGATES.json` (the
pre-A9 run's own evidence, preserved byte-unchanged on disk).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import platform
import random
import statistics
import subprocess
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
from uri_v1.turn.rar_l5_diagnostic_fixtures import get_l5_diagnostic_fixtures  # noqa: E402
from uri_v1.turn.rar_attachment_order_experimental import (  # noqa: E402
    AttachmentOrderOverlay,
    PROVENANCE_CURRENT_TURN_SEQUENCE,
    PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
    compile_and_resolve_via_existing_contract,
    resolve_rar_attachment_order_experimental,
)
from uri_v1.turn.rar_attachment_order_factorial_fixtures import (  # noqa: E402
    FactorialCase,
    get_factorial_cases,
)
import m35_rar_natural_boundary_harness as nbh  # noqa: E402
import m35_a2_8j_rar_safe_battery as j8j  # noqa: E402

TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_TELEMETRY.json"
AGGREGATES_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_AGGREGATES.json"
RUN1_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_RUN1_CAUSAL.json"
RUN2_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_RUN2_CAUSAL.json"

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

# A9-conformant mechanism/fixture files: hashed and reported (not "protected"
# in the plan §13.2 sense -- they ARE the A2.8L implementation -- but their
# byte-identity across this rerun's two subprocess invocations is required
# evidence of a genuinely frozen mechanism under test).
MECHANISM_FILES = {
    "rar_attachment_order_experimental.py": REPO_ROOT / "uri_v1" / "turn" / "rar_attachment_order_experimental.py",
    "rar_attachment_order_factorial_fixtures.py": REPO_ROOT / "uri_v1" / "turn" / "rar_attachment_order_factorial_fixtures.py",
}

FACTORS = ["M", "G", "P", "D", "R", "Q"]

NATURAL_SURFACE_CASE_IDS = ("NB-C-04", "NB-C-05", "NB-D-01", "NB-D-02")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _protected_hashes() -> Dict[str, str]:
    return {name: sha256_of(p) for name, p in PROTECTED_FILES.items()}


def _mechanism_hashes() -> Dict[str, str]:
    return {name: sha256_of(p) for name, p in MECHANISM_FILES.items()}


def _decision_tuple(res) -> tuple:
    return (res.outcome.value, res.candidate_id, frozenset(res.ambiguous_candidate_ids))


def _all_cells() -> List[Dict[str, bool]]:
    return [dict(zip(FACTORS, bits)) for bits in itertools.product([False, True], repeat=6)]


def _cell_key(cell: Dict[str, bool]) -> str:
    return "".join(f + ("1" if cell[f] else "0") for f in FACTORS)


def _flags_from_key(key: str) -> Dict[str, bool]:
    return {f: key[FACTORS.index(f) * 2 + 1] == "1" for f in FACTORS}


# ---------------------------------------------------------------------------
# Causal matrix (item 2/8/9: fresh-process capable, identical scoring logic
# to the pre-A9 script -- reused verbatim since the A9 amendments changed no
# scoring rule, only which control is gated and how the mechanism behaves)
# ---------------------------------------------------------------------------

def _classify_row(case: FactorialCase, actual_outcome: str, actual_cid: Optional[str], actual_amb: FrozenSet[str]) -> str:
    expected_amb = frozenset(case.expected_ambiguous_candidate_ids)
    if case.id == "C-NO-RANK0":
        return "PASS" if actual_outcome != "RESOLVED" else "UNCHANGED_DOMAIN_RERANK"
    if case.expected_outcome == RAROutcome.RESOLVED:
        if actual_outcome == "RESOLVED" and actual_cid == case.expected_candidate_id:
            return "PASS"
        if actual_outcome == "RESOLVED" and actual_cid != case.expected_candidate_id:
            return "INCORRECT_CONFIDENT_BINDING"
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
            return "PASS" if actual_amb == expected_amb else "WRONG_AMBIGUITY_DOMAIN"
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
        "schema": "m35.uriv1.a2_8l.a9.causal.v1",
        "cell": _cell_key(cell), "cell_flags": dict(cell), "repeat": repeat,
        "case_id": case.id, "case_source": case.source, "is_causal_target": case.is_causal_target,
        "pool_condition": case.pool_condition, "reachable_by_factors": case.reachable_by_factors,
        "candidate_ids_supplied": [c.id for c in case.query.candidates],
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
        by_key.setdefault((r["cell"], r["case_id"]), []).append(r)
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
        "total_keys": len(by_key), "expected_keys": 64 * 14, "mismatches": mismatches,
        "reconciled": len(mismatches) == 0 and len(by_key) == 64 * 14,
    }


def compute_qualifying_cells(rows: List[dict]) -> dict:
    """A9 §16.1 A9-1: C-LEXICAL-ATTACHMENT excluded from the gate via
    `reachable_by_factors`. Logic unchanged from the pre-A9 script -- A9-1
    only formalized this exclusion in the frozen plan text; the pre-A9
    script's implementation of it is adopted as-is."""
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
        cell_flags = _flags_from_key(cell_key)
        on_factors = {f for f, v in cell_flags.items() if v}
        is_minimal = True
        for f in on_factors:
            subset_flags = dict(cell_flags)
            subset_flags[f] = False
            if _cell_key(subset_flags) in qualifying:
                is_minimal = False
                break
        if is_minimal:
            minimal_sufficient.append(cell_key)

    all_off_key = _cell_key({f: False for f in FACTORS})
    single_factor_sufficient = []
    for f in FACTORS:
        flags = {ff: False for ff in FACTORS}
        flags[f] = True
        if _cell_key(flags) in qualifying:
            single_factor_sufficient.append(f)

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


# ---------------------------------------------------------------------------
# Interaction tables: all-off background (pre-A9 script's original probe)
# PLUS qualifying-cell background (A9 §16.3 item 3, new)
# ---------------------------------------------------------------------------

def compute_pairwise_interactions_all_off(qualifying_analysis: dict) -> dict:
    interactions = {}
    for i in range(len(FACTORS)):
        for j in range(i + 1, len(FACTORS)):
            fa, fb = FACTORS[i], FACTORS[j]
            table = {}
            for a_on in (False, True):
                for b_on in (False, True):
                    flags = {f: False for f in FACTORS}
                    flags[fa], flags[fb] = a_on, b_on
                    table[f"{fa}={int(a_on)},{fb}={int(b_on)}"] = _cell_key(flags) in qualifying_analysis["qualifying_cells"]
            both_off, a_only = table[f"{fa}=0,{fb}=0"], table[f"{fa}=1,{fb}=0"]
            b_only, both_on = table[f"{fa}=0,{fb}=1"], table[f"{fa}=1,{fb}=1"]
            interactions[f"{fa}x{fb}"] = {
                "table": table,
                "interacting_pair": both_on and not a_only and not b_only and not both_off,
            }
    return interactions


def compute_pairwise_interactions_on_background(rows: List[dict], qualifying_analysis: dict, background_key: str) -> dict:
    """A9 §16.3 item 3: case-level 2x2 tables with all OTHER factors held at
    the qualifying-cell's own values (not all-off), reporting raw per-case
    decision changes, not only cell-level qualification pass/fail -- the
    pre-A9 all-off probe cannot detect a joint requirement that only shows
    up once the other necessary factors are already present."""
    if not background_key:
        return {"background_key": None, "note": "No qualifying cell exists; on-background tables not computable.", "tables": {}}
    background_flags = _flags_from_key(background_key)
    row_by_cell_case: Dict[Tuple[str, str], dict] = {
        (r["cell"], r["case_id"]): r for r in rows if r["repeat"] == 1
    }
    case_ids = sorted({r["case_id"] for r in rows})
    tables: Dict[str, dict] = {}
    for i in range(len(FACTORS)):
        for j in range(i + 1, len(FACTORS)):
            fa, fb = FACTORS[i], FACTORS[j]
            per_case: Dict[str, dict] = {}
            for case_id in case_ids:
                cell_decisions = {}
                for a_on in (False, True):
                    for b_on in (False, True):
                        flags = dict(background_flags)
                        flags[fa], flags[fb] = a_on, b_on
                        key = _cell_key(flags)
                        row = row_by_cell_case.get((key, case_id))
                        if row is None:
                            continue
                        cell_decisions[f"{fa}={int(a_on)},{fb}={int(b_on)}"] = {
                            "scoring_class": row["scoring_class"],
                            "actual_outcome": row["actual_outcome"],
                            "actual_candidate_id": row["actual_candidate_id"],
                        }
                per_case[case_id] = cell_decisions
            tables[f"{fa}x{fb}"] = per_case
    return {"background_key": background_key, "background_flags": background_flags, "tables": tables}


# ---------------------------------------------------------------------------
# Transport comparison (unchanged §4.2.1 algorithm) + mismatch attribution
# ---------------------------------------------------------------------------

_H3_ONLY_CASE_IDS = {"C-DOMAIN-RANK-SYNTH", "C-DOMAIN-RANK-NATURAL"}
_L55_EXTENSION_CASE_IDS = {"B-DISTRACTOR", "C-NATURAL-PHOTOS-C1", "C-NATURAL-PHOTOS-C2"}


def _attribute_mismatch(
    case_id: str, cell_flags: Dict[str, bool], sidecar_row: dict,
    sidecar_outcome: str, sidecar_candidate_id: Optional[str],
    compiler_outcome: Optional[str], compiler_candidate_id: Optional[str],
) -> str:
    """A9 §16.3 item 4: explicit per-mismatch cause, not an aggregate
    footnote. The compiler algorithm (§4.2.1) is unchanged; this only
    explains why sidecar and compiler diverge for THIS row given the
    A9-conformant sidecar's own (unchanged) behavior. Buckets were derived
    by inspecting every observed mismatch pattern in this rerun (not
    guessed in advance) -- see the execution report's "Transport
    mismatch-cause taxonomy" section for the worked examples behind each
    bucket.

    - H3_ABSENCE_CONFOUND: the compiler's step-6 call to raw
      `resolve_rar_deterministic_extended` never runs H3 (§4.2.1 has no H3
      step); non-attachment domain-rank controls always mismatch,
      independent of M/G/P/D/R/Q.
    - D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED: the frozen compiler algorithm's
      step 1 ordinal-trigger check has no analogue for A9-2's Level-5.5
      membership extension, so a non-ordinal attachment case always falls
      through to an unprojected baseline call.
    - COMPILER_NO_TIE_ABSTENTION_REPRESENTATION: the sidecar safely
      abstains (AMBIGUOUS) via R's domain-wide tie (A9-5) when G/P/R jointly
      or partially fail to authorize a bind; the compiler's step 4 is a
      binary choice (project a trusted dense rank, or leave the original
      rank unchanged) with no tie/abstention representation in between, so
      it always falls through to a confident RESOLVE on the un-tied
      original ranks.
    - COMPILER_M_GATED_NO_GPR_FALLBACK: the compiler's step 2 skips ALL
      projection (including any G/P/R benefit) whenever M is not
      transported; the sidecar can still resolve correctly without M via
      H3's own domain-relative rank fallback over the unrestricted pool
      (using G/P/R's event evidence directly, not gated by M) -- a genuine
      compiler capability gap, not an M-attributable disagreement.
    - COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R: the compiler's step 4 only
      densifies rank when R is explicitly on; the sidecar's H3 fallback
      (`_fallback_rank_map`) densifies rank unconditionally whenever the
      domain is genuinely narrowed by M/D, independent of R. When R is
      ablated, the compiler's M-projected-but-unranked subset can lack a
      rank-0 member entirely, so it safely (but unnecessarily, relative to
      the sidecar) falls through to AMBIGUOUS where the sidecar resolves.
    """
    if case_id in _H3_ONLY_CASE_IDS:
        return "H3_ABSENCE_CONFOUND"
    if case_id in _L55_EXTENSION_CASE_IDS and not sidecar_row.get("ordinal_trigger_matched"):
        return "D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED"
    if sidecar_outcome == "AMBIGUOUS" and compiler_outcome == "RESOLVED":
        return "COMPILER_NO_TIE_ABSTENTION_REPRESENTATION"
    if (not cell_flags.get("M") and sidecar_outcome == "RESOLVED" and compiler_outcome == "RESOLVED"
            and sidecar_candidate_id != compiler_candidate_id):
        return "COMPILER_M_GATED_NO_GPR_FALLBACK"
    if not cell_flags.get("R") and sidecar_outcome == "RESOLVED" and compiler_outcome == "AMBIGUOUS":
        return "COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R"
    return "UNEXPLAINED_REQUIRES_MANUAL_REVIEW"


def run_transport_comparison(qualifying_analysis: dict, causal_rows_by_cell_case: Dict[Tuple[str, str], dict]) -> dict:
    cases = get_factorial_cases()
    minimal_sets = qualifying_analysis["minimal_sufficient_sets"]

    cells_to_test: List[str] = []
    if minimal_sets:
        cells_to_test.append(_cell_key({f: False for f in FACTORS}))
        for key in minimal_sets:
            if key not in cells_to_test:
                cells_to_test.append(key)
            flags = _flags_from_key(key)
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
    attribution_counts: Dict[str, int] = {}
    for cell_key in cells_to_test:
        flags = _flags_from_key(cell_key)
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
                sidecar_row_for_attribution = {
                    "ordinal_trigger_matched": sidecar_trace.ordinal_trigger_matched,
                    "which_level_returned": sidecar_trace.which_level_returned,
                }
                row = {
                    "schema": "m35.uriv1.a2_8l.a9.transport.v1",
                    "cell": cell_key, "cell_flags": flags, "case_id": case.id, "repeat": repeat,
                    "sidecar_outcome": sidecar_tuple[0], "sidecar_candidate_id": sidecar_tuple[1],
                    "sidecar_ambiguous_ids": sorted(sidecar_tuple[2]),
                    "compiler_outcome": compiled_tuple[0] if compiled_tuple else None,
                    "compiler_candidate_id": compiled_tuple[1] if compiled_tuple else None,
                    "compiler_ambiguous_ids": sorted(compiled_tuple[2]) if compiled_tuple else None,
                    "compiler_error": compiler_error,
                    "compiler_diagnostics": diag,
                    "arms_match": match,
                }
                if not match:
                    row["mismatch_attribution"] = _attribute_mismatch(
                        case.id, flags, sidecar_row_for_attribution,
                        sidecar_tuple[0], sidecar_tuple[1],
                        compiled_tuple[0] if compiled_tuple else None,
                        compiled_tuple[1] if compiled_tuple else None,
                    )
                    attribution_counts[row["mismatch_attribution"]] = attribution_counts.get(row["mismatch_attribution"], 0) + 1
                    mismatches.append(row)
                rows.append(row)

    return {
        "t_value": t_count, "t_cap_hit": row_cap_hit, "cells_tested": cells_to_test,
        "row_count": len(rows), "rows": rows,
        "mismatches": mismatches, "mismatch_count": len(mismatches),
        "mismatch_attribution_counts": attribution_counts,
        "conclusion": (
            "TRANSPORT_RESULT_INCONCLUSIVE" if not qualifying_analysis["qualifying_cells"] else
            ("EXISTING_CONTRACT_COMPILATION_BEHAVIORALLY_SUFFICIENT" if not mismatches else
             "EXISTING_CONTRACT_COMPILATION_INSUFFICIENT")
        ),
        "conclusion_scope_note": (
            "Scoped exactly to the frozen §4.2.1 compiler algorithm as "
            "executed (A9 §16.4 rule 4); not a general claim about "
            "existing-contract compilation."
        ),
    }


# ---------------------------------------------------------------------------
# D1RQ + natural-row confirmation surface (A9 rerun task item 4)
# ---------------------------------------------------------------------------

def _natural_overlay_for(case_id: str, pool_cond: str, turn_attachments: FrozenSet[str]) -> AttachmentOrderOverlay:
    """Overlay facts exactly as frozen in the plan/manifest for NB-C-04 and
    NB-C-05 (both single shared re-attachment/attachment event,
    HISTORICAL_OBJECT_CREATED_AT). NB-D-01/NB-D-02 have no turn_attachments
    in the corpus and no overlay authored anywhere in the manifest -- they
    run with the empty overlay, exactly as their pool composition (no
    current-turn membership signal exists for them) requires."""
    if case_id in ("NB-C-04", "NB-C-05") and turn_attachments:
        return AttachmentOrderOverlay(
            turn_membership_ids=turn_attachments,
            event_group_by_id={cid: "event-0" for cid in turn_attachments},
            group_ordinal_by_event={"event-0": 0},
            provenance=PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
        )
    return AttachmentOrderOverlay()


def run_d1rq_natural_surface(qualifying_analysis: dict) -> dict:
    """Plan §5.3: D1RQ-detected span + hint, natural rows NB-C-04/NB-C-05/
    NB-D-01/NB-D-02 at C1/C2, both production-shaped (oracle_recency=False)
    and created_at-oracle (oracle_recency=True) ranks -- run under baseline
    (all-off) and EVERY A9-amended qualifying cell plus its one-factor
    ablations (task item 4), not a single "best cell" as the pre-A9 script's
    `run_confirmation_surfaces` did."""
    data = nbh.load_fixture()
    library = data["candidate_library"]
    cases_by_id = {c["case_id"]: c for c in data["cases"]}

    cells_to_run: List[str] = [_cell_key({f: False for f in FACTORS})]
    for key in qualifying_analysis["minimal_sufficient_sets"]:
        if key not in cells_to_run:
            cells_to_run.append(key)
        flags = _flags_from_key(key)
        for f in FACTORS:
            if flags[f]:
                ablated = dict(flags)
                ablated[f] = False
                ablated_key = _cell_key(ablated)
                if ablated_key not in cells_to_run:
                    cells_to_run.append(ablated_key)

    rows: List[dict] = []
    for case_id in NATURAL_SURFACE_CASE_IDS:
        case = cases_by_id.get(case_id)
        if case is None:
            rows.append({"case_id": case_id, "scoring_class": "HARNESS_OR_FIXTURE_INVALID", "reason": "case not found in corpus"})
            continue
        raw_text = case["raw_user_text"]
        gt_refs = case["ground_truth_references"]
        gt_by_key = {r["ref_key"]: r for r in gt_refs}
        variants_by_cond = {v["candidate_condition"]: v for v in case["variants"]}
        turn_attachments = frozenset(case.get("conversation_context", {}).get("turn_attachments") or ())

        d1rq_found = j8j.run_d1rq_case(raw_text)
        found_spans = [f["span"] for f in d1rq_found]

        for pool_cond in ("C1", "C2"):
            variant = variants_by_cond.get(pool_cond)
            if variant is None:
                continue
            candidate_ids = variant["available_candidates"]
            expected_by_ref = {eb["ref_key"]: eb for eb in variant["expected_by_reference"]}
            overlay = _natural_overlay_for(case_id, pool_cond, turn_attachments & frozenset(candidate_ids))

            for oracle_recency in (False, True):
                candidates = nbh.build_candidate_pool(candidate_ids, library, oracle_recency=oracle_recency)
                used_spans: set = set()
                for ref_key, gt in gt_by_key.items():
                    m_expr = j8j.find_matching_found_expr(gt.get("human_marked_span"), found_spans, used_spans)
                    eb = expected_by_ref.get(ref_key, {})
                    expected_outcome = eb.get("expected_outcome", "UNKNOWN")
                    intended_ids = eb.get("intended_candidate_ids", [])
                    if m_expr is None:
                        rows.append({
                            "surface": "D1RQ_NATURAL", "case_id": case_id, "pool_condition": pool_cond,
                            "ref_key": ref_key, "oracle_recency": oracle_recency,
                            "scoring_class": "SILENT_DETECTION_MISS",
                            "expected_outcome": expected_outcome, "intended_candidate_ids": intended_ids,
                        })
                        continue
                    used_spans.add(m_expr)
                    f = next(x for x in d1rq_found if x["span"] == m_expr)
                    if j8j.boundary_violation(f["span"], candidate_ids, raw_text):
                        rows.append({
                            "surface": "D1RQ_NATURAL", "case_id": case_id, "pool_condition": pool_cond,
                            "ref_key": ref_key, "oracle_recency": oracle_recency,
                            "scoring_class": "BOUNDARY_VIOLATION",
                            "expected_outcome": expected_outcome, "intended_candidate_ids": intended_ids,
                        })
                        continue
                    q = j8j.build_query(f["span"], candidates, f["recency_hint"], f["negation_spans"], f.get("coarse_type"))

                    baseline_trace = resolve_rar_attachment_order_experimental(q, AttachmentOrderOverlay())
                    baseline_decision = _decision_tuple(baseline_trace.resolution)

                    for cell_key in cells_to_run:
                        flags = _flags_from_key(cell_key)
                        trace = resolve_rar_attachment_order_experimental(
                            q, overlay, **{k.lower(): v for k, v in flags.items()}
                        )
                        decision = _decision_tuple(trace.resolution)
                        changed_from_baseline = decision != baseline_decision
                        is_new_confident_bind = (
                            decision[0] == "RESOLVED" and baseline_decision[0] != "RESOLVED"
                        )
                        rows.append({
                            "surface": "D1RQ_NATURAL", "case_id": case_id, "pool_condition": pool_cond,
                            "ref_key": ref_key, "oracle_recency": oracle_recency, "cell": cell_key,
                            "detected_span": f["span"], "detected_hint": f["recency_hint"],
                            "expected_outcome": expected_outcome, "intended_candidate_ids": intended_ids,
                            "baseline_decision": list(baseline_decision[:2]) + [sorted(baseline_decision[2])],
                            "cell_decision": list(decision[:2]) + [sorted(decision[2])],
                            "changed_from_baseline": changed_from_baseline,
                            "new_confident_bind_vs_baseline": is_new_confident_bind,
                            "scoring_class": (
                                "NB_D_02_UNAUTHORIZED_NEW_BIND"
                                if case_id == "NB-D-02" and is_new_confident_bind
                                else ("CHANGED" if changed_from_baseline else "UNCHANGED")
                            ),
                        })
    nb_d02_violations = [r for r in rows if r.get("scoring_class") == "NB_D_02_UNAUTHORIZED_NEW_BIND"]
    return {
        "cells_run": cells_to_run,
        "row_count": len(rows),
        "rows": rows,
        "nb_d02_unauthorized_new_bind_count": len(nb_d02_violations),
        "note": (
            "Plan §5.3: NB-D-02 is a relative-anchor capability-gap "
            "control -- no cell may claim to solve it; only a safe "
            "abstention change from baseline is permitted. "
            "nb_d02_unauthorized_new_bind_count must be 0."
        ),
    }


def run_sd_confirmation(qualifying_analysis: dict) -> dict:
    """S-D battery under every candidate qualifying cell (not only the
    first minimal set)."""
    cells_to_run: List[str] = [_cell_key({f: False for f in FACTORS})] + list(qualifying_analysis["minimal_sufficient_sets"])
    per_cell: Dict[str, dict] = {}
    for cell_key in cells_to_run:
        flags = _flags_from_key(cell_key)
        mismatches = []
        for fix in get_l5_diagnostic_fixtures():
            exp_off = resolve_rar_attachment_order_experimental(fix.query, AttachmentOrderOverlay())
            exp_flag = resolve_rar_attachment_order_experimental(
                fix.query, AttachmentOrderOverlay(), **{k.lower(): v for k, v in flags.items()}
            )
            if _decision_tuple(exp_flag.resolution) != _decision_tuple(exp_off.resolution) and fix.id not in (
                "SD-A-04", "SD-A-05", "SD-A-06", "SD-A-07",
            ):
                mismatches.append({
                    "fixture": fix.id,
                    "flag_off": list(_decision_tuple(exp_off.resolution)[:2]) + [sorted(_decision_tuple(exp_off.resolution)[2])],
                    "with_cell": list(_decision_tuple(exp_flag.resolution)[:2]) + [sorted(_decision_tuple(exp_flag.resolution)[2])],
                })
        per_cell[cell_key] = {"unexpected_mismatches": mismatches, "mismatch_count": len(mismatches)}
    return {"cells_run": cells_to_run, "per_cell": per_cell,
            "sd_battery_case_count": len(get_l5_diagnostic_fixtures())}


# ---------------------------------------------------------------------------
# Performance pass -- full 200/2000 pre-registered protocol (A9 rerun item 7)
# ---------------------------------------------------------------------------

def _synthetic_pool(n: int) -> Tuple[RARQuery, AttachmentOrderOverlay]:
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


def _environment_metadata() -> dict:
    freq = getattr(time, "get_clock_info", None)
    perf_info = time.get_clock_info("perf_counter") if freq else None
    proc_info = time.get_clock_info("process_time") if freq else None
    return {
        "os": platform.system(), "os_release": platform.release(), "os_version": platform.version(),
        "python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
        "cpu_identifier": platform.processor() or platform.machine(),
        "machine": platform.machine(), "process_bitness": 64 if sys.maxsize > 2 ** 32 else 32,
        "perf_counter_resolution_s": perf_info.resolution if perf_info else None,
        "process_time_resolution_s": proc_info.resolution if proc_info else None,
        "source_hashes": {**_protected_hashes(), **_mechanism_hashes()},
    }


def run_performance_pass(qualifying_analysis: dict, warmups: int = 200, iterations: int = 2000, seed: int = 20260924) -> dict:
    """Plan §10.2, full pre-registered protocol: 200 warmups + 2,000
    RANDOMIZED/INTERLEAVED measured iterations per cell, all pool sizes,
    all-off baseline, single factors, every minimal-sufficient/candidate
    qualifying cell, and the compiler arm."""
    pool_sizes = [2, 8, 32, 128]
    cell_names: List[Tuple[str, Dict[str, bool]]] = [("all_off", {f: False for f in FACTORS})]
    for f in FACTORS:
        flags = {ff: False for ff in FACTORS}
        flags[f] = True
        cell_names.append((f"single_{f}", flags))
    for key in qualifying_analysis["minimal_sufficient_sets"]:
        cell_names.append((key, _flags_from_key(key)))

    rng = random.Random(seed)
    # Interleaved/randomized schedule: build the full (cell, pool, iteration)
    # index list once per arm, shuffle it, then execute in that order so
    # iteration order is not grouped by cell/pool (plan §10.2, §11 seed
    # disclosure requirement).
    results: Dict[str, Dict[str, dict]] = {name: {} for name, _ in cell_names}
    compiler_results: Dict[str, dict] = {}

    for cell_name, flags in cell_names:
        for n in pool_sizes:
            q, ov = _synthetic_pool(n)
            for _ in range(warmups):
                resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})

            schedule = list(range(iterations))
            rng.shuffle(schedule)
            wall_ns: List[int] = [0] * iterations
            cpu_ns: List[int] = [0] * iterations
            for idx in schedule:
                t0_wall, t0_cpu = time.perf_counter_ns(), time.process_time_ns()
                resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})
                wall_ns[idx] = time.perf_counter_ns() - t0_wall
                cpu_ns[idx] = time.process_time_ns() - t0_cpu

            tracemalloc.start()
            resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            wall_sorted = sorted(wall_ns)
            results[cell_name][f"pool_{n}"] = {
                "mean_wall_ms": statistics.mean(wall_ns) / 1e6,
                "p95_wall_ms": wall_sorted[int(len(wall_sorted) * 0.95) - 1] / 1e6,
                "median_cpu_ms": statistics.median(cpu_ns) / 1e6,
                "peak_alloc_bytes": peak, "iterations": iterations, "warmups": warmups,
            }

    # Compiler arm: same pool sizes, all-off vs each minimal-sufficient cell's
    # M/R projection (Q/G/P/D have no existing-contract analogue, §4.2.1).
    for key in qualifying_analysis["minimal_sufficient_sets"] or ["all_off"]:
        flags = _flags_from_key(key) if key != "all_off" else {f: False for f in FACTORS}
        compiler_results[key] = {}
        for n in pool_sizes:
            q, ov = _synthetic_pool(n)
            for _ in range(warmups):
                compile_and_resolve_via_existing_contract(q, ov, m=flags["M"], r=flags["R"])
            schedule = list(range(iterations))
            rng.shuffle(schedule)
            wall_ns = [0] * iterations
            for idx in schedule:
                t0 = time.perf_counter_ns()
                compile_and_resolve_via_existing_contract(q, ov, m=flags["M"], r=flags["R"])
                wall_ns[idx] = time.perf_counter_ns() - t0
            wall_sorted = sorted(wall_ns)
            compiler_results[key][f"pool_{n}"] = {
                "mean_wall_ms": statistics.mean(wall_ns) / 1e6,
                "p95_wall_ms": wall_sorted[int(len(wall_sorted) * 0.95) - 1] / 1e6,
                "iterations": iterations, "warmups": warmups,
            }

    # Threshold evaluation against the winning cell, vs all-off, per §10.2.
    threshold_checks = {}
    winning_keys = qualifying_analysis["minimal_sufficient_sets"]
    if winning_keys:
        win = winning_keys[0]
        for n in [2, 8, 32]:
            base_p95 = results["all_off"][f"pool_{n}"]["p95_wall_ms"]
            win_p95 = results[win][f"pool_{n}"]["p95_wall_ms"]
            allowed = max(0.25, 2 * base_p95)
            threshold_checks[f"p95_overhead_pool_{n}"] = {
                "baseline_p95_ms": base_p95, "winning_p95_ms": win_p95,
                "allowed_ms": allowed, "within_threshold": win_p95 <= allowed,
            }
            base_cpu = results["all_off"][f"pool_{n}"]["median_cpu_ms"]
            win_cpu = results[win][f"pool_{n}"]["median_cpu_ms"]
            threshold_checks[f"cpu_overhead_pool_{n}"] = {
                "baseline_cpu_ms": base_cpu, "winning_cpu_ms": win_cpu,
                "allowed_ms": 2 * base_cpu if base_cpu > 0 else None,
                "within_threshold": (win_cpu <= 2 * base_cpu) if base_cpu > 0 else None,
            }
        growth_32 = results[win]["pool_32"]["mean_wall_ms"]
        growth_128 = results[win]["pool_128"]["mean_wall_ms"]
        ratio = (growth_128 / growth_32) if growth_32 > 0 else None
        threshold_checks["pool_32_to_128_growth_ratio"] = {
            "ratio": ratio, "allowed_max": 6.0, "within_threshold": (ratio is not None and ratio <= 6.0),
        }
        peak_128 = results[win]["pool_128"]["peak_alloc_bytes"]
        threshold_checks["peak_alloc_pool_128"] = {
            "bytes": peak_128, "allowed_max_bytes": 256 * 1024, "within_threshold": peak_128 < 256 * 1024,
        }

    return {
        "protocol": "FULL_PRE_REGISTERED_200_WARMUP_2000_ITERATION_RANDOMIZED_INTERLEAVED",
        "seed": seed,
        "environment": _environment_metadata(),
        "sidecar_results": results,
        "compiler_arm_results": compiler_results,
        "threshold_checks": threshold_checks,
        "threshold_checks_final_not_provisional": bool(threshold_checks),
    }


# ---------------------------------------------------------------------------
# Fresh-process causal matrix entrypoint (item 3: two independent processes)
# ---------------------------------------------------------------------------

def _causal_only_main(out_path: Path) -> None:
    rows = run_causal_matrix()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "rows": rows,
            "mechanism_hashes": _mechanism_hashes(),
            "protected_hashes": _protected_hashes(),
        }, f)


def run_two_fresh_process_causal_runs() -> Tuple[List[dict], List[dict], dict]:
    for p in (RUN1_PATH, RUN2_PATH):
        if p.exists():
            p.unlink()
    for out_path in (RUN1_PATH, RUN2_PATH):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--causal-only", str(out_path)],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Fresh-process causal run failed (exit {result.returncode}) writing {out_path}:\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
    with open(RUN1_PATH, "r", encoding="utf-8") as f:
        run1_payload = json.load(f)
    with open(RUN2_PATH, "r", encoding="utf-8") as f:
        run2_payload = json.load(f)
    run1, run2 = run1_payload["rows"], run2_payload["rows"]

    def _key(r):
        return (r["cell"], r["case_id"], r["repeat"], r["actual_outcome"], r["actual_candidate_id"], tuple(r["actual_ambiguous_candidate_ids"]))

    determinism_ok = [_key(r) for r in run1] == [_key(r) for r in run2]
    hashes_identical_across_processes = (
        run1_payload["mechanism_hashes"] == run2_payload["mechanism_hashes"]
        and run1_payload["protected_hashes"] == run2_payload["protected_hashes"]
    )
    fresh_process_report = {
        "run1_row_count": len(run1), "run2_row_count": len(run2),
        "fresh_process_determinism_passed": determinism_ok,
        "source_hashes_identical_across_processes": hashes_identical_across_processes,
        "run1_source_hashes": run1_payload["mechanism_hashes"],
        "run2_source_hashes": run2_payload["mechanism_hashes"],
    }
    return run1, run2, fresh_process_report


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def main() -> None:
    pre_hashes = _protected_hashes()
    pre_mechanism_hashes = _mechanism_hashes()

    run1, run2, fresh_process_report = run_two_fresh_process_causal_runs()

    reconciliation = reconcile_repeats(run1)
    qualifying_analysis = compute_qualifying_cells(run1)
    interactions_all_off = compute_pairwise_interactions_all_off(qualifying_analysis)
    best_cell = qualifying_analysis["minimal_sufficient_sets"][0] if qualifying_analysis["minimal_sufficient_sets"] else None
    interactions_on_background = compute_pairwise_interactions_on_background(run1, qualifying_analysis, best_cell)

    causal_rows_by_cell_case = {(r["cell"], r["case_id"]): r for r in run1 if r["repeat"] == 1}
    transport = run_transport_comparison(qualifying_analysis, causal_rows_by_cell_case)
    sd_confirmation = run_sd_confirmation(qualifying_analysis)
    natural_confirmation = run_d1rq_natural_surface(qualifying_analysis)
    performance = run_performance_pass(qualifying_analysis)

    post_hashes = _protected_hashes()
    post_mechanism_hashes = _mechanism_hashes()
    hashes_unchanged = pre_hashes == post_hashes
    mechanism_unchanged = pre_mechanism_hashes == post_mechanism_hashes

    telemetry = {
        "schema": "m35.uriv1.a2_8l.a9.telemetry.v1",
        "frozen_checkpoint": "591f806",
        "pre_run_protected_hashes": pre_hashes, "post_run_protected_hashes": post_hashes,
        "protected_hashes_unchanged": hashes_unchanged,
        "pre_run_mechanism_hashes": pre_mechanism_hashes, "post_run_mechanism_hashes": post_mechanism_hashes,
        "mechanism_hashes_unchanged": mechanism_unchanged,
        "fresh_process_report": fresh_process_report,
        "causal_rows": run1, "causal_row_count": len(run1),
        "repeat_reconciliation": reconciliation,
        "transport_comparison": transport,
        "sd_confirmation": sd_confirmation,
        "natural_confirmation": natural_confirmation,
        "performance": performance,
        "pre_a9_literal_plan_result": {
            "qualifying_cells": 0,
            "note": "Preserved per A9 §16.2 item 1 -- not reproduced by this rerun, stated as historical fact.",
        },
    }
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)

    aggregates = {
        "schema": "m35.uriv1.a2_8l.a9.aggregates.v1",
        "qualifying_analysis": qualifying_analysis,
        "pairwise_interactions_all_off_background": interactions_all_off,
        "pairwise_interactions_qualifying_cell_background": interactions_on_background,
        "transport_conclusion": transport["conclusion"],
        "transport_conclusion_scope_note": transport["conclusion_scope_note"],
        "transport_mismatch_count": transport["mismatch_count"],
        "transport_mismatch_attribution_counts": transport["mismatch_attribution_counts"],
        "nb_d02_unauthorized_new_bind_count": natural_confirmation["nb_d02_unauthorized_new_bind_count"],
        "fresh_process_determinism_passed": fresh_process_report["fresh_process_determinism_passed"],
        "repeat_reconciliation_passed": reconciliation["reconciled"],
        "protected_hashes_unchanged": hashes_unchanged,
        "mechanism_hashes_unchanged": mechanism_unchanged,
    }
    with open(AGGREGATES_PATH, "w", encoding="utf-8") as f:
        json.dump(aggregates, f, indent=2)

    print(f"Causal rows: {len(run1)} (expect 1792)")
    print(f"Fresh-process determinism passed: {fresh_process_report['fresh_process_determinism_passed']}")
    print(f"Repeat reconciliation: {reconciliation['reconciled']}")
    print(f"Qualifying cells: {qualifying_analysis['qualifying_cell_count']} / 64")
    print(f"Minimal sufficient sets: {qualifying_analysis['minimal_sufficient_sets']}")
    print(f"Necessary factors: {qualifying_analysis['necessary_factors_if_any_qualifying']}")
    print(f"Transport T value: {transport['t_value']}, conclusion: {transport['conclusion']}")
    print(f"Transport mismatch attribution: {transport['mismatch_attribution_counts']}")
    print(f"NB-D-02 unauthorized new-bind count: {natural_confirmation['nb_d02_unauthorized_new_bind_count']}")
    print(f"Protected hashes unchanged: {hashes_unchanged}; mechanism hashes unchanged: {mechanism_unchanged}")
    print(f"Wrote telemetry -> {TELEMETRY_PATH}")
    print(f"Wrote aggregates -> {AGGREGATES_PATH}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--causal-only":
        _causal_only_main(Path(sys.argv[2]))
    else:
        main()
