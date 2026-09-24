"""M35 URIv1 -- A2.8L-A9-R2: bounded evidence/reporting correction after
independent re-audit of A9-R1.

R2 scope (per the R1 independent re-audit, verdict `REPAIR_REQUIRED` on
A9-R1): report/telemetry label and interpretation corrections ONLY. NO
mechanism, fixture, benchmark-semantic, or causal-factor change is made or
authorized here. `uri_v1/turn/rar_attachment_order_experimental.py` and
`uri_v1/turn/rar_attachment_order_factorial_fixtures.py` are byte-identical
to A9-R1 (verified by hash before and after this script runs). The A9-R1
independent re-audit's own verified numbers (1/64 qualifying, 0/896 delta,
88/196 transport mismatches, 112/54/0 natural-surface reconciliation, 119
tests/178 subtests) are reproduced here, not rederived from a different
protocol.

Corrections applied (R2-1 through R2-8 of the authorized task; R2-9 is a
separate governance-doc-only edit made directly to the overlay manifest,
not by this script; R2-10 is a disclosure, not a code change):

- R2-1 (transport taxonomy): the R1 `COMPILER_UNSAFE_BIND_NO_TIE_
  REPRESENTATION` bucket (38 rows) was NOT actually split by outcome
  direction despite its docstring claiming so -- `_attribute_mismatch`'s
  tie-vs-ambiguous branch never distinguished "sidecar correctly abstains,
  compiler unsafely binds" from "sidecar over-gates and abstains
  incorrectly, compiler is actually correct". This script's
  `_attribute_mismatch` now computes row-level correctness (against each
  case's frozen `expected_outcome`/`expected_candidate_id`/
  `expected_ambiguous_candidate_ids`) and branches on it, producing
  `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND` (sidecar correct, compiler
  wrong) and `SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT` (compiler correct,
  sidecar over-gated) as two distinct buckets. Ties remain representable in
  the existing `recency_rank` field (a densified rank or an all-equal tie
  both fit the existing int field); the bucket name intentionally avoids
  implying otherwise.
- R2-2 (G x P wording): report-only correction (see R2 correction report);
  this script adds no new mechanism behavior, only records per-case R-value
  context already present in the interaction tables so the report can state
  the conditional-on-R=1 interpretation without re-deriving it.
- R2-3 (surface labels): `_score_against_expected`'s mismatch-reason
  classification for the 12 NB-C-04/NB-C-05 rows is renamed from the R1
  generic "ABLATION_EXPECTED..." framing to a label naming the actual
  cells (qualifying cell + M-off/D-off ablations, including the all-off
  baseline cell) so the report does not call all 12 uniformly "ablation"
  mismatches when 4 of them are the baseline cell itself.
- R2-4 (IR-1 residual): the `"earlier"` token match in `_ordinal_literal_
  present` (module line ~143, unchanged from A9/A9-R1) is not frozen by
  A9-3's literal text (`recency_hint in {"latest","first","earlier"}` OR a
  literal `"latest"`/`"first"` token) for the *token* path -- A9-3 only
  froze `"earlier"` as a hint value, not as an additional ref-token
  literal. This script verifies (not fixes) that zero current factorial or
  natural rows are affected by this token path and records the finding as
  `NON_EFFECTING_SPEC_RESIDUAL` in the telemetry for the report to disclose.
- R2-5 (Q telemetry flag): `q_alone_resolves_all_case_b_ordinal_targets` is
  now computed against exactly the three ordinal Case-B ids
  (`B-LATEST-WRONG-CLOCK`, `B-FIRST-WRONG-CLOCK`, `B-LATEST-PROVENANCE-
  TWIN`), not the four-id `_B_CASE_IDS` tuple that also includes the
  non-ordinal `B-DISTRACTOR` (which Q alone does NOT resolve, correctly --
  Q has no effect on B-DISTRACTOR's A9-2 Level-5.5 path). The prior flag's
  name and population disagreed; this is a label/computation fix only.
- R2-6/R2-7 (performance): the compiler arm's wall-time benchmark
  (`compiler_results` in `run_performance_pass`) previously only shuffled
  the STORAGE index within one (cell, pool) block, identical to the sidecar
  defect R1 already fixed. This script gives the compiler arm the same
  genuine global (condition, iteration) interleaved CALL-ORDER schedule the
  sidecar already uses. The CPU-batch docstring's "spans >=100 ticks" claim
  is corrected to report the actual measured tick coverage per pool
  (verified empirically, not assumed).
- R2-8 (S16.5 telemetry gap): no per-row G/M-separability or R-overlay-vs-
  gate-attribution field was ever emitted by A9 or A9-R1's causal rows. This
  script adds no new fields (doing so would be a new telemetry surface, not
  a report correction); it records the gap explicitly in `telemetry_gaps`
  for the report to disclose, and confirms the same conclusion remains
  derivable post-hoc from the full 64-cell raw causal rows already on disk.
- R2-10 (environment metadata): `_environment_metadata()` was called once
  per performance pass, not once per fresh-process causal run as frozen
  §16.3 item 8 requires. This script now captures environment metadata
  inside `_causal_only_main` (the actual per-process entrypoint) so each of
  the two fresh subprocess runs records its own environment snapshot,
  and discloses that A9/A9-R1's historical fresh-process runs did NOT
  capture this (only source hashes) -- that gap is not retroactively
  fabricated.

Historical A9 evidence (`M35_URIV1_A2_8L_A9_*`) and A9-R1 evidence
(`M35_URIV1_A2_8L_A9_R1_*`) are NOT overwritten by this script. This script
writes to `M35_URIV1_A2_8L_A9_R2_*` paths only.

No mechanism or fixture modification is made here. No protected file
(plan §13.2) is touched. No commit or push occurs.
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
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended, clean_tokens  # noqa: E402
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

TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_R2_TELEMETRY.json"
AGGREGATES_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_R2_AGGREGATES.json"
RUN1_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_R2_RUN1_CAUSAL.json"
RUN2_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_R2_RUN2_CAUSAL.json"
R1_TELEMETRY_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_R1_TELEMETRY.json"
R1_REAUDIT_PATH = REPO_ROOT / "docs" / "plans" / "M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md"

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

MECHANISM_FILES = {
    "rar_attachment_order_experimental.py": REPO_ROOT / "uri_v1" / "turn" / "rar_attachment_order_experimental.py",
    "rar_attachment_order_factorial_fixtures.py": REPO_ROOT / "uri_v1" / "turn" / "rar_attachment_order_factorial_fixtures.py",
}

FACTORS = ["M", "G", "P", "D", "R", "Q"]
NATURAL_SURFACE_CASE_IDS = ("NB-C-04", "NB-C-05", "NB-D-01", "NB-D-02")
_B_CASE_IDS = ("B-LATEST-WRONG-CLOCK", "B-FIRST-WRONG-CLOCK", "B-LATEST-PROVENANCE-TWIN", "B-DISTRACTOR")


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
# Causal matrix (ER-8: UNTRUSTWORTHY_ORDER_BIND repaired to be reachable)
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
            # ER-8 repair: a confident bind to one MEMBER of the expected
            # ambiguous set, on a Case-B (untrustworthy-order) target, is the
            # untrustworthy-order failure mode by definition -- the resolver
            # picked one candidate out of a set that should have remained
            # tied/ambiguous because the ORDER used to break the tie was not
            # authoritative. A bind to an id OUTSIDE the expected set (e.g. a
            # non-member distractor) is a different, more severe failure
            # (INCORRECT_CONFIDENT_BINDING / NON_CURRENT_TURN_MEMBER_BIND-
            # shaped) regardless of case family. The prior classifier only
            # ever checked the "outside the set" branch, so
            # UNTRUSTWORTHY_ORDER_BIND was structurally unreachable.
            if case.id in _B_CASE_IDS and actual_cid in expected_amb:
                return "UNTRUSTWORTHY_ORDER_BIND"
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
        "schema": "m35.uriv1.a2_8l.a9r2.causal.v1",
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


def compute_per_case_minimal_sets(rows: List[dict]) -> dict:
    """ER-1/ER-2/ER-3 repair: per-case minimal PASSING factor sets over all 64
    cells, computed from raw rows. This is the evidence base for replacing the
    "5-way joint requirement" claim with a per-case structural account, and
    for correctly attributing D/M and G necessity (see aggregates
    `necessity_repaired_interpretation`)."""
    by_case: Dict[str, Dict[str, dict]] = {}
    for r in rows:
        if r["repeat"] != 1:
            continue
        by_case.setdefault(r["case_id"], {})[r["cell"]] = r

    result: Dict[str, dict] = {}
    for case_id, by_cell in by_case.items():
        passing_sets = []
        for cell_key, row in by_cell.items():
            if row["scoring_class"] == "PASS":
                flags = _flags_from_key(cell_key)
                passing_sets.append(frozenset(f for f in FACTORS if flags[f]))
        minimal = sorted(
            {s for s in passing_sets if not any(o < s for o in passing_sets)},
            key=lambda s: (len(s), sorted(s)),
        )
        result[case_id] = {
            "pass_count_of_64": len(passing_sets),
            "minimal_passing_sets": ["".join(sorted(s, key=FACTORS.index)) if s else "{}" for s in minimal],
        }
    return result


# ---------------------------------------------------------------------------
# Interaction tables (unchanged computation; interpretation corrected in the
# execution report / claims register, not by changing this data).
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
    if not background_key:
        return {"background_key": None, "note": "No qualifying cell exists; on-background tables not computable.", "tables": {}}
    background_flags = _flags_from_key(background_key)
    row_by_cell_case: Dict[Tuple[str, str], dict] = {
        (r["cell"], r["case_id"]): r for r in rows if r["repeat"] == 1
    }
    case_ids = sorted({r["case_id"] for r in rows})
    tables: Dict[str, dict] = {}
    interacting_pairs_on_background: List[dict] = []
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
                # ER-3 repair: explicitly detect and record genuine two-factor
                # interactions on the qualifying-cell background per §7's own
                # definition (neither single-factor cell passes, the pair
                # does, both_off/either single is not PASS) -- the pre-repair
                # report claimed no such interaction existed, which the raw
                # M x D / B-DISTRACTOR and G x P / A-LATEST-2 tables
                # contradict.
                keys4 = ["0,0", "1,0", "0,1", "1,1"]
                cls = {k: cell_decisions.get(f"{fa}={k.split(',')[0]},{fb}={k.split(',')[1]}", {}).get("scoring_class") for k in keys4}
                both_off_pass = cls["0,0"] == "PASS"
                a_only_pass = cls["1,0"] == "PASS"
                b_only_pass = cls["0,1"] == "PASS"
                both_on_pass = cls["1,1"] == "PASS"
                if both_on_pass and not a_only_pass and not b_only_pass and not both_off_pass:
                    interacting_pairs_on_background.append({"pair": f"{fa}x{fb}", "case_id": case_id})
            tables[f"{fa}x{fb}"] = per_case
    return {
        "background_key": background_key, "background_flags": background_flags, "tables": tables,
        "interacting_pairs_detected": interacting_pairs_on_background,
    }


# ---------------------------------------------------------------------------
# Transport comparison -- ER-5 repair: factor-state-parity overlay filtering
# for the compiler arm, and corrected mismatch attribution taxonomy.
# ---------------------------------------------------------------------------

_H3_ONLY_CASE_IDS = {"C-DOMAIN-RANK-SYNTH", "C-DOMAIN-RANK-NATURAL"}
_L55_EXTENSION_CASE_IDS = {"B-DISTRACTOR", "C-NATURAL-PHOTOS-C1", "C-NATURAL-PHOTOS-C2"}


def _parity_overlay_and_m(overlay: AttachmentOrderOverlay, flags: Dict[str, bool]) -> Tuple[AttachmentOrderOverlay, bool]:
    """Plan §16.3 item 4 repair: the compiler arm must receive the same
    G/P/D factor state as the sidecar arm for this row. The frozen §4.2.1
    algorithm itself (its 8 numbered steps) is NOT changed -- this filters
    only the OVERLAY INPUT and the effective `m` flag handed to the
    unmodified `compile_and_resolve_via_existing_contract`, at this script's
    (harness) level, so the compiler cannot see G/P/D evidence the sidecar
    was not also given for this cell:

    - D gates whether the sidecar applies M's membership restriction at all
      (per the mechanism's own D-consumes-M rule); without D, the compiler
      must not project either, so the effective `m` handed to the compiler
      is `flags['M'] and flags['D']`.
    - G gates the sidecar's order-derivation gate; without G, the compiler's
      overlay must not carry event-group evidence, so `event_group_by_id`/
      `group_ordinal_by_event` are cleared when G is off.
    - P gates the sidecar's authorization gate; without P, the compiler's
      overlay must not carry a provenance the sidecar was not authorized to
      trust, so `provenance` is cleared when P is off.
    """
    ov = overlay
    if not flags.get("G"):
        ov = AttachmentOrderOverlay(
            turn_membership_ids=ov.turn_membership_ids,
            event_group_by_id={}, group_ordinal_by_event={},
            provenance=ov.provenance, single_current_attachment_id=ov.single_current_attachment_id,
        )
    if not flags.get("P"):
        ov = AttachmentOrderOverlay(
            turn_membership_ids=ov.turn_membership_ids,
            event_group_by_id=ov.event_group_by_id, group_ordinal_by_event=ov.group_ordinal_by_event,
            provenance=None, single_current_attachment_id=ov.single_current_attachment_id,
        )
    effective_m = bool(flags.get("M")) and bool(flags.get("D"))
    return ov, effective_m


def _row_is_correct(case: FactorialCase, outcome: Optional[str], candidate_id: Optional[str],
                     ambiguous_ids: Optional[Sequence[str]]) -> bool:
    """R2-1: row-level correctness against the case's own frozen expectation
    (`expected_outcome`/`expected_candidate_id`/`expected_ambiguous_
    candidate_ids`), used to split the transport tie bucket by DIRECTION --
    this is the check the R1 taxonomy never performed, which is why its
    `COMPILER_UNSAFE_BIND_NO_TIE_REPRESENTATION` bucket silently mixed rows
    where the sidecar was wrong (over-gated) with rows where the sidecar
    was right and the compiler was unsafe."""
    if outcome is None:
        return False
    if case.id == "C-NO-RANK0":
        return outcome != "RESOLVED"
    if case.expected_outcome == RAROutcome.RESOLVED:
        return outcome == "RESOLVED" and candidate_id == case.expected_candidate_id
    if case.expected_outcome == RAROutcome.AMBIGUOUS:
        return outcome == "AMBIGUOUS" and set(ambiguous_ids or ()) == set(case.expected_ambiguous_candidate_ids)
    return False


def _attribute_mismatch(
    case: FactorialCase, cell_flags: Dict[str, bool], compiler_effective_m: bool, sidecar_row_for_attribution: dict,
    sidecar_outcome: str, sidecar_candidate_id: Optional[str], sidecar_ambiguous_ids: Sequence[str],
    compiler_outcome: Optional[str], compiler_candidate_id: Optional[str], compiler_ambiguous_ids: Optional[Sequence[str]],
) -> str:
    """Corrected taxonomy (R2-1, repairing A9-R1's ER-5 which claimed but did
    not actually perform this split -- see
    `docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md` §7).

    The former single `COMPILER_UNSAFE_BIND_NO_TIE_REPRESENTATION` bucket
    (A9-R1, 38 rows) checked only the SHAPE of the two arms' outcomes
    (sidecar AMBIGUOUS, compiler RESOLVED), never which arm was actually
    correct against the case's frozen expectation. It is now split by
    row-level correctness (`_row_is_correct`) into two disjoint, exhaustive
    buckets covering that same (AMBIGUOUS, RESOLVED) shape:

    - `COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND`: the sidecar is CORRECT
      (it should abstain) and the compiler is WRONG (it confidently binds).
      This is the genuine unsafe-transport direction -- the frozen §4.2.1
      step 4 has no branch that emits a tie/abstention the way the
      sidecar's R mechanism (A9-5 domain-wide tie, or the event-ordinal
      rank map) does.
    - `SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT`: the sidecar is WRONG (its
      own G/P gate makes it abstain when the frozen case expects a bind)
      and the compiler, now parity-filtered to the same G/P state, is
      CORRECT. The compiler is not unsafe here; the sidecar's own gate is
      conservative on this row. (§7's independent re-audit found exactly 8
      such rows, at the G0/P0 cells on `A-LATEST-2`/`A-FIRST-2`.)

    Neither bucket's name implies the RAR contract cannot represent ties:
    a densified rank or an all-equal `recency_rank` both fit the existing
    int field. The limitation attributed here is in the tested §4.2.1
    algorithm's step 4 branching (it never emits either), not in contract
    field expressiveness -- `NEW_CONTRACT_FIELD_REQUIRED` remains
    unestablished by this result.

    `COMPILER_M_GATED_NO_GPR_FALLBACK`'s description (A9-R1's fix,
    preserved here) is correct: the sidecar's ability to resolve without M
    is R's `_event_ordinal_rank_map` event-evidence fallback, not H3's
    lexical domain-relative-rank fallback (a different function).
    """
    if case.id in _H3_ONLY_CASE_IDS:
        return "H3_ABSENCE_CONFOUND"
    if case.id in _L55_EXTENSION_CASE_IDS and not sidecar_row_for_attribution.get("ordinal_trigger_matched"):
        return "D_M_LEVEL_5_5_EXTENSION_NOT_COMPILED"
    if sidecar_outcome == "AMBIGUOUS" and compiler_outcome == "RESOLVED":
        sidecar_ok = _row_is_correct(case, sidecar_outcome, sidecar_candidate_id, sidecar_ambiguous_ids)
        compiler_ok = _row_is_correct(case, compiler_outcome, compiler_candidate_id, compiler_ambiguous_ids)
        if sidecar_ok and not compiler_ok:
            return "COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND"
        if compiler_ok and not sidecar_ok:
            return "SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT"
        # Neither/both correct under this shape was not observed in the
        # tested cell set; kept as an explicit, reviewable fallback rather
        # than silently folded into either directional bucket.
        return "COMPILER_UNSAFE_BIND_AMBIGUOUS_CORRECTNESS_REQUIRES_REVIEW"
    if sidecar_outcome == "AMBIGUOUS" and compiler_outcome == "AMBIGUOUS" and sidecar_candidate_id != compiler_candidate_id:
        # Both abstain but over different sets -- distinct from a bind.
        return "COMPILER_DIFFERENT_AMBIGUITY_SET"
    if (not compiler_effective_m and sidecar_outcome == "RESOLVED" and compiler_outcome == "RESOLVED"
            and sidecar_candidate_id != compiler_candidate_id):
        # compiler_effective_m is parity_m (M AND D); the sidecar can still
        # resolve correctly without M or D active via R's own
        # `_event_ordinal_rank_map` event-evidence fallback over the
        # UNRESTRICTED domain (a no-event candidate is always ranked last),
        # while the compiler's step 2 (parity-gated on M AND D) skips
        # projection entirely and falls through to raw baseline.
        return "COMPILER_M_OR_D_GATED_NO_R_EVENT_FALLBACK"
    if not cell_flags.get("R") and sidecar_outcome == "RESOLVED" and compiler_outcome == "AMBIGUOUS":
        return "COMPILER_RANK_NOT_DENSIFIED_WITHOUT_R"
    if sidecar_outcome == "RESOLVED" and compiler_outcome == "RESOLVED" and sidecar_candidate_id == compiler_candidate_id:
        return "COMPILER_CORRECT_SIDECAR_OVER_GATED"  # matched decision tuple would not reach here; defensive
    return "UNEXPLAINED_REQUIRES_MANUAL_REVIEW"


def run_transport_comparison(qualifying_analysis: dict) -> dict:
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
                parity_overlay, parity_m = _parity_overlay_and_m(case.overlay, flags)
                try:
                    compiled_trace, diag = compile_and_resolve_via_existing_contract(
                        case.query, parity_overlay, m=parity_m, r=flags["R"],
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
                sidecar_amb_sorted = sorted(sidecar_tuple[2])
                compiler_amb_sorted = sorted(compiled_tuple[2]) if compiled_tuple else None
                row = {
                    "schema": "m35.uriv1.a2_8l.a9r2.transport.v1",
                    "cell": cell_key, "cell_flags": flags, "case_id": case.id, "repeat": repeat,
                    "sidecar_outcome": sidecar_tuple[0], "sidecar_candidate_id": sidecar_tuple[1],
                    "sidecar_ambiguous_ids": sidecar_amb_sorted,
                    "compiler_outcome": compiled_tuple[0] if compiled_tuple else None,
                    "compiler_candidate_id": compiled_tuple[1] if compiled_tuple else None,
                    "compiler_ambiguous_ids": compiler_amb_sorted,
                    "compiler_parity_m": parity_m,
                    "compiler_parity_overlay_g_stripped": not flags.get("G"),
                    "compiler_parity_overlay_p_stripped": not flags.get("P"),
                    "compiler_error": compiler_error,
                    "compiler_diagnostics": diag,
                    "arms_match": match,
                }
                if not match:
                    row["sidecar_correct"] = _row_is_correct(case, sidecar_tuple[0], sidecar_tuple[1], sidecar_amb_sorted)
                    row["compiler_correct"] = _row_is_correct(case, compiled_tuple[0] if compiled_tuple else None,
                                                                compiled_tuple[1] if compiled_tuple else None, compiler_amb_sorted)
                    row["mismatch_attribution"] = _attribute_mismatch(
                        case, flags, parity_m, sidecar_row_for_attribution,
                        sidecar_tuple[0], sidecar_tuple[1], sidecar_amb_sorted,
                        compiled_tuple[0] if compiled_tuple else None,
                        compiled_tuple[1] if compiled_tuple else None, compiler_amb_sorted,
                    )
                    attribution_counts[row["mismatch_attribution"]] = attribution_counts.get(row["mismatch_attribution"], 0) + 1
                    mismatches.append(row)
                rows.append(row)

    return {
        "t_value": t_count, "t_cap_hit": row_cap_hit, "cells_tested": cells_to_test,
        "row_count": len(rows), "rows": rows,
        "mismatches": mismatches, "mismatch_count": len(mismatches),
        "mismatch_attribution_counts": attribution_counts,
        "factor_state_parity_applied": True,
        "conclusion": (
            "TRANSPORT_RESULT_INCONCLUSIVE" if not qualifying_analysis["qualifying_cells"] else
            ("EXISTING_CONTRACT_COMPILATION_BEHAVIORALLY_SUFFICIENT" if not mismatches else
             "EXISTING_CONTRACT_COMPILATION_INSUFFICIENT")
        ),
        "conclusion_scope_note": (
            "Scoped exactly to the frozen §4.2.1 compiler algorithm as "
            "executed under factor-state parity (A9 §16.3 item 4, ER-5 "
            "repair); not a general claim about existing-contract "
            "compilation. Ties ARE representable in the existing "
            "recency_rank field; NEW_CONTRACT_FIELD_REQUIRED remains "
            "unestablished by this result."
        ),
    }


# ---------------------------------------------------------------------------
# D1RQ + natural-row confirmation surface -- ER-4 repair: score against
# expected outcome, not only changed/unchanged vs baseline.
# ---------------------------------------------------------------------------

def _natural_overlay_for(case_id: str, turn_attachments: FrozenSet[str]) -> AttachmentOrderOverlay:
    if case_id in ("NB-C-04", "NB-C-05") and turn_attachments:
        return AttachmentOrderOverlay(
            turn_membership_ids=turn_attachments,
            event_group_by_id={cid: "event-0" for cid in turn_attachments},
            group_ordinal_by_event={"event-0": 0},
            provenance=PROVENANCE_HISTORICAL_OBJECT_CREATED_AT,
        )
    return AttachmentOrderOverlay()


def _score_against_expected(outcome: str, cid: Optional[str], amb: FrozenSet[str],
                             expected_outcome: str, intended_ids: List[str]) -> str:
    intended = frozenset(intended_ids)
    if expected_outcome == "RESOLVED":
        if outcome == "RESOLVED" and len(intended) == 1 and cid in intended:
            return "MATCHES_EXPECTED"
        if outcome == "RESOLVED":
            return "WRONG_RESOLUTION"
        return "MISSED_EXPECTED_RESOLUTION"
    if expected_outcome == "AMBIGUOUS":
        if outcome == "AMBIGUOUS" and amb == intended:
            return "MATCHES_EXPECTED"
        if outcome == "AMBIGUOUS":
            return "WRONG_AMBIGUITY_DOMAIN"
        return "UNEXPECTED_CONFIDENT_OUTCOME"
    if expected_outcome == "UNKNOWN":
        return "MATCHES_EXPECTED" if outcome == "UNKNOWN" else "UNEXPECTED_NON_UNKNOWN_OUTCOME"
    return "NO_EXPECTED_OUTCOME_RECORDED"


def run_d1rq_natural_surface(qualifying_analysis: dict) -> dict:
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
    raw_baseline_diffs: List[dict] = []
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
            overlay = _natural_overlay_for(case_id, turn_attachments & frozenset(candidate_ids))

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
                    raw_trace = resolve_rar_deterministic_extended(q)
                    raw_decision = _decision_tuple(raw_trace.resolution)
                    if raw_decision != baseline_decision:
                        raw_baseline_diffs.append({
                            "case_id": case_id, "pool_condition": pool_cond, "ref_key": ref_key,
                            "oracle_recency": oracle_recency, "raw": list(raw_decision[:2]) + [sorted(raw_decision[2])],
                            "sidecar_all_off": list(baseline_decision[:2]) + [sorted(baseline_decision[2])],
                        })

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
                        expected_score = _score_against_expected(decision[0], decision[1], decision[2], expected_outcome, intended_ids)
                        # ER-4 repair, second pass: classify WHY an
                        # expected-outcome mismatch occurs so the report can
                        # separate already-disclosed, expected behavior from
                        # a genuinely new/unexplained defect:
                        #  - NB-D-02: plan §5.3 explicitly forbids any cell
                        #    from claiming to solve it; a non-PASS score here
                        #    is the disclosed capability gap, not a defect.
                        #  - NB-C-04/NB-C-05 with M or D not both active: the
                        #    A9-2 extension requires BOTH M and D; this cell
                        #    set is the qualifying cell's one-factor M/D
                        #    ablations PLUS the all-off baseline cell itself
                        #    (which is not an ablation of anything -- M and D
                        #    are simply never on there). R2-3 correction: the
                        #    label below is computed per-row so the report
                        #    does not call all such rows uniformly "ablation"
                        #    mismatches when some are the baseline cell.
                        #  - NB-D-01 with oracle_recency=False: the
                        #    factorial's own C-DOMAIN-RANK-NATURAL case is
                        #    scoped to oracle_recency=True only (plan
                        #    fixtures never test production-shaped
                        #    all-zero ranks for this case); an identical
                        #    outcome across every cell (including baseline)
                        #    is a pre-existing surface characteristic of
                        #    "latest"-wording without a created_at oracle,
                        #    unrelated to any A2.8L factor or this repair.
                        mismatch_reason = None
                        if expected_score not in (None, "MATCHES_EXPECTED", "NO_EXPECTED_OUTCOME_RECORDED"):
                            all_off_cell = cell_key == _cell_key({f: False for f in FACTORS})
                            if case_id == "NB-D-02":
                                mismatch_reason = "DISCLOSED_CAPABILITY_GAP_NB_D_02"
                            elif case_id in ("NB-C-04", "NB-C-05") and not (flags.get("M") and flags.get("D")):
                                mismatch_reason = (
                                    "M_AND_D_INACTIVE_ALL_OFF_BASELINE_CELL_A9_2_NOT_APPLICABLE"
                                    if all_off_cell else
                                    "M_OR_D_ABLATED_FROM_QUALIFYING_CELL_A9_2_REQUIRES_BOTH"
                                )
                            elif case_id == "NB-D-01" and not oracle_recency:
                                mismatch_reason = "PRE_EXISTING_NON_ORACLE_RANK_SCOPE_LIMITATION"
                            else:
                                mismatch_reason = "UNEXPLAINED"
                        rows.append({
                            "surface": "D1RQ_NATURAL", "case_id": case_id, "pool_condition": pool_cond,
                            "ref_key": ref_key, "oracle_recency": oracle_recency, "cell": cell_key,
                            "detected_span": f["span"], "detected_hint": f["recency_hint"],
                            "expected_outcome": expected_outcome, "intended_candidate_ids": intended_ids,
                            "baseline_decision": list(baseline_decision[:2]) + [sorted(baseline_decision[2])],
                            "cell_decision": list(decision[:2]) + [sorted(decision[2])],
                            "changed_from_baseline": changed_from_baseline,
                            "new_confident_bind_vs_baseline": is_new_confident_bind,
                            "expected_outcome_scoring": expected_score,
                            "expected_mismatch_reason": mismatch_reason,
                            "scoring_class": (
                                "NB_D_02_UNAUTHORIZED_NEW_BIND"
                                if case_id == "NB-D-02" and is_new_confident_bind
                                else ("CHANGED" if changed_from_baseline else "UNCHANGED")
                            ),
                        })
    nb_d02_violations = [r for r in rows if r.get("scoring_class") == "NB_D_02_UNAUTHORIZED_NEW_BIND"]
    changed_rows = [r for r in rows if r.get("changed_from_baseline")]
    changed_by_case_pool = {}
    for r in changed_rows:
        changed_by_case_pool.setdefault(f"{r['case_id']} {r['pool_condition']}", 0)
        changed_by_case_pool[f"{r['case_id']} {r['pool_condition']}"] += 1
    expected_mismatches = [r for r in rows if r.get("expected_outcome_scoring") not in (None, "MATCHES_EXPECTED", "NO_EXPECTED_OUTCOME_RECORDED")]
    unexplained_mismatches = [r for r in expected_mismatches if r.get("expected_mismatch_reason") == "UNEXPLAINED"]
    mismatch_reason_counts: Dict[str, int] = {}
    for r in expected_mismatches:
        reason = r.get("expected_mismatch_reason") or "UNKNOWN"
        mismatch_reason_counts[reason] = mismatch_reason_counts.get(reason, 0) + 1
    return {
        "cells_run": cells_to_run,
        "row_count": len(rows),
        "rows": rows,
        "nb_d02_unauthorized_new_bind_count": len(nb_d02_violations),
        "changed_rows_count": len(changed_rows),
        "changed_rows_by_case_and_pool_condition": changed_by_case_pool,
        "expected_outcome_mismatch_count": len(expected_mismatches),
        "expected_outcome_mismatch_reason_counts": mismatch_reason_counts,
        "unexplained_expected_outcome_mismatch_count": len(unexplained_mismatches),
        "unexplained_expected_outcome_mismatches": unexplained_mismatches,
        "expected_outcome_mismatches": expected_mismatches,
        "raw_baseline_vs_sidecar_all_off_diffs": raw_baseline_diffs,
        "note": (
            "Plan §5.3: NB-D-02 is a relative-anchor capability-gap "
            "control -- no cell may claim to solve it; only a safe "
            "abstention change from baseline is permitted. "
            "nb_d02_unauthorized_new_bind_count must be 0. ER-4 repair: "
            "expected_outcome_scoring is now computed per row against "
            "expected_by_reference (RESOLVED->intended id / "
            "AMBIGUOUS->intended set); expected_outcome_mismatch_count "
            "reports rows scoring class differs from PASS-equivalent, "
            "surfacing correctness defects the prior CHANGED/UNCHANGED-"
            "only scoring could not detect (e.g. the pre-repair NB-C-04 "
            "C2 wrong-domain row)."
        ),
    }


def run_sd_confirmation(qualifying_analysis: dict) -> dict:
    cells_to_run: List[str] = [_cell_key({f: False for f in FACTORS})] + list(qualifying_analysis["minimal_sufficient_sets"])
    per_cell: Dict[str, dict] = {}
    raw_baseline_diffs: List[dict] = []
    for fix in get_l5_diagnostic_fixtures():
        exp_off = resolve_rar_attachment_order_experimental(fix.query, AttachmentOrderOverlay())
        raw = resolve_rar_deterministic_extended(fix.query)
        if _decision_tuple(exp_off.resolution) != _decision_tuple(raw.resolution):
            raw_baseline_diffs.append({
                "fixture": fix.id,
                "raw": list(_decision_tuple(raw.resolution)[:2]) + [sorted(_decision_tuple(raw.resolution)[2])],
                "sidecar_all_off": list(_decision_tuple(exp_off.resolution)[:2]) + [sorted(_decision_tuple(exp_off.resolution)[2])],
            })
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
    return {
        "cells_run": cells_to_run, "per_cell": per_cell,
        "sd_battery_case_count": len(get_l5_diagnostic_fixtures()),
        "raw_baseline_vs_sidecar_all_off_diffs": raw_baseline_diffs,
        "raw_baseline_diff_count": len(raw_baseline_diffs),
        "note": (
            "ER-7 (A9-4) repair: raw_baseline_vs_sidecar_all_off_diffs "
            "reports every S-D fixture where sidecar all-off (which runs "
            "with H3 always-on per A9-4) differs from raw "
            "resolve_rar_deterministic_extended -- this is the explicit "
            "raw-baseline-equivalence measurement A9-4 requires be "
            "reported separately from the criterion-8 (H3-active) "
            "flag-off equivalence gate."
        ),
    }


def run_a2_5_reconciliation() -> dict:
    """ER-7: the plan's §5.3/§16.3-item-2 text names 'the unchanged A2.5 RAR
    test modules' as a confirmation surface. Those modules
    (`test_m35_uriv1_a2_5_*.py`) exercise `rar_deterministic.py` directly
    with no cell-flag parameter -- A2.8L never modifies that protected file,
    so there is no cell-conditioned behavior for those tests to exercise.
    'Under every candidate winning cell' does not apply to them the way it
    applies to the D1RQ/natural surface (which runs THROUGH the A2.8L
    resolver). This function records that reconciliation explicitly rather
    than silently treating a plain pytest pass as satisfying a per-cell
    requirement it structurally cannot satisfy."""
    return {
        "applicability": "NOT_CELL_PARAMETERIZABLE",
        "reason": (
            "A2.5 test modules call resolve_rar_deterministic_extended / "
            "rar_contracts validators directly; they carry no M/G/P/D/R/Q "
            "parameter and A2.8L does not modify rar_deterministic.py "
            "(a plan §13.2 protected file). Running them 'under a cell' "
            "is not a meaningful operation for this suite; their "
            "obligation under §5.3 is regression (still passing, byte-"
            "unchanged), which is satisfied and reported separately as "
            "the standard regression run (see execution report "
            "Regression section)."
        ),
    }


def run_ir1_earlier_token_residual_check() -> dict:
    """R2-4: verify (do NOT fix) the residual the R1 re-audit found in IR-1.

    `_ordinal_literal_present` (module line ~143, unchanged since A9) matches
    an `"earlier"` LITERAL REF TOKEN as well as the `"earlier"` HINT value.
    A9-3's frozen text (plan §16.1) only froze `"earlier"` as a hint value
    (`query.recency_hint in {"latest","first","earlier"}`) plus the existing
    baseline `"latest"`/`"first"` TOKEN convention -- it never froze
    `"earlier"` as an additional ref-token literal. This function checks,
    over every current factorial case and every current natural-surface
    D1RQ span, whether the ordinal trigger for that row is reached ONLY
    through the unfrozen token path (i.e. `recency_hint` is not itself
    "latest"/"first"/"earlier", but the literal word "earlier" appears in
    the reference expression's cleaned tokens). If this set is empty, the
    residual has zero effect on any decision currently in evidence and the
    finding is `NON_EFFECTING_SPEC_RESIDUAL`; it is neither fixed (no
    mechanism change is authorized in R2) nor silently dropped (the report
    must still disclose it, since the mechanism as written diverges from the
    frozen text even where zero current cases exercise the divergence)."""
    cases = get_factorial_cases()
    affected: List[str] = []
    for c in cases:
        ref_tokens = clean_tokens(c.query.reference_expression.strip())
        hint = c.query.local_evidence.recency_hint
        token_only_earlier = "earlier" in ref_tokens and hint not in ("latest", "first", "earlier")
        if token_only_earlier:
            affected.append(f"factorial:{c.id}")

    data = nbh.load_fixture()
    for case in data["cases"]:
        found = j8j.run_d1rq_case(case["raw_user_text"])
        for f in found:
            ref_tokens = clean_tokens(f["span"].strip())
            hint = f["recency_hint"]
            if "earlier" in ref_tokens and hint not in ("latest", "first", "earlier"):
                affected.append(f"natural:{case['case_id']}:{f['span'][:40]}")

    return {
        "location": "uri_v1/turn/rar_attachment_order_experimental.py:_ordinal_literal_present "
                     "(module line ~143, `\"earlier\" in ref_tokens` branch)",
        "divergence_from_frozen_text": (
            "A9-3 (plan §16.1) freezes `\"earlier\"` only as a `recency_hint` "
            "value, plus the pre-existing baseline `\"latest\"`/`\"first\"` "
            "literal-ref-token convention. The implementation additionally "
            "matches a literal `\"earlier\"` REF TOKEN even when "
            "`recency_hint` is not `\"latest\"`/`\"first\"`/`\"earlier\"`; "
            "that specific token-literal path was never frozen by A9-3."
        ),
        "affected_rows_current_evidence": affected,
        "affected_row_count": len(affected),
        "decision_effect_on_current_evidence": (
            "NONE" if not affected else "REQUIRES_MANUAL_REVIEW_ROWS_AFFECTED"
        ),
        "classification": "NON_EFFECTING_SPEC_RESIDUAL" if not affected else "EFFECTING_SPEC_RESIDUAL_REQUIRES_REPAIR",
        "disposition": (
            "Not fixed in R2 (no mechanism change authorized this round) and "
            "not formally frozen by any plan amendment. Remains open for a "
            "future bounded mechanism-conformance round (remove the extra "
            "token match, or freeze it via a plan amendment) if it is ever "
            "found to affect a row."
        ),
    }


# ---------------------------------------------------------------------------
# Performance -- ER-6 repair: genuine cross-cell/pool interleaving for wall
# time, interleaved batched sampling for CPU.
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
        "perf_counter_nominal_resolution_s": perf_info.resolution if perf_info else None,
        "process_time_nominal_resolution_s": proc_info.resolution if proc_info else None,
        "source_hashes": {**_protected_hashes(), **_mechanism_hashes()},
    }


def _measure_process_time_granularity(sample_seconds: float = 0.5) -> int:
    """Empirically measure the smallest observed nonzero process_time_ns
    step on this host, rather than trusting the nominal get_clock_info
    resolution (which reads 1e-7s on Windows even though the OS scheduler
    tick is much coarser)."""
    deltas = set()
    last = time.process_time_ns()
    end = time.perf_counter() + sample_seconds
    while time.perf_counter() < end:
        t = time.process_time_ns()
        if t != last:
            deltas.add(t - last)
            last = t
    return min(deltas) if deltas else 0


def run_performance_pass(qualifying_analysis: dict, warmups: int = 200, iterations: int = 2000,
                          cpu_batch_calls: int = 20000, cpu_batches_per_cell_pool: int = 30,
                          seed: int = 20260924) -> dict:
    pool_sizes = [2, 8, 32, 128]
    cell_names: List[Tuple[str, Dict[str, bool]]] = [("all_off", {f: False for f in FACTORS})]
    for f in FACTORS:
        flags = {ff: False for ff in FACTORS}
        flags[f] = True
        cell_names.append((f"single_{f}", flags))
    for key in qualifying_analysis["minimal_sufficient_sets"]:
        cell_names.append((key, _flags_from_key(key)))

    rng = random.Random(seed)
    measured_granularity_ns = _measure_process_time_granularity()

    # --- Wall time: GENUINE global interleaving across (cell, pool). -------
    # Build every (cell_idx, pool_idx) combination's warmup pass first (warm
    # caches deterministically per condition), then build ONE global schedule
    # of (cell_idx, pool_idx, iteration) triples across ALL conditions and
    # shuffle it, so consecutive measured calls are not grouped by condition.
    pool_cache: Dict[Tuple[str, int], Tuple[RARQuery, AttachmentOrderOverlay]] = {}
    for cell_name, _ in cell_names:
        for n in pool_sizes:
            pool_cache[(cell_name, n)] = _synthetic_pool(n)

    for cell_name, flags in cell_names:
        for n in pool_sizes:
            q, ov = pool_cache[(cell_name, n)]
            for _ in range(warmups):
                resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})

    conditions = [(cell_name, flags, n) for cell_name, flags in cell_names for n in pool_sizes]
    global_schedule: List[int] = []
    for cond_idx in range(len(conditions)):
        global_schedule.extend([cond_idx] * iterations)
    rng.shuffle(global_schedule)

    wall_ns_by_cond: Dict[int, List[int]] = {i: [] for i in range(len(conditions))}
    for cond_idx in global_schedule:
        cell_name, flags, n = conditions[cond_idx]
        q, ov = pool_cache[(cell_name, n)]
        t0 = time.perf_counter_ns()
        resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})
        wall_ns_by_cond[cond_idx].append(time.perf_counter_ns() - t0)

    results: Dict[str, Dict[str, dict]] = {name: {} for name, _ in cell_names}
    for cond_idx, (cell_name, flags, n) in enumerate(conditions):
        wall_ns = wall_ns_by_cond[cond_idx]
        wall_sorted = sorted(wall_ns)
        q, ov = pool_cache[(cell_name, n)]
        tracemalloc.start()
        resolve_rar_attachment_order_experimental(q, ov, **{k.lower(): v for k, v in flags.items()})
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results[cell_name][f"pool_{n}"] = {
            "mean_wall_ms": statistics.mean(wall_ns) / 1e6,
            "p95_wall_ms": wall_sorted[int(len(wall_sorted) * 0.95) - 1] / 1e6,
            "peak_alloc_bytes": peak, "iterations": len(wall_ns), "warmups": warmups,
        }

    # --- CPU: interleaved BATCHED sampling (ER-6 method). -------------------
    # A single call's process_time_ns delta reads 0 on this host (measured
    # granularity below). Each batch times a per-condition `cpu_batch_calls`
    # contiguous calls of ONE condition (contiguity is required so the
    # batch's total CPU time can be divided by the call count); batch ORDER
    # across the conditions actually used by the §10.2 threshold gate is
    # interleaved via a shuffled schedule with the same fixed seed, so no
    # condition's batches all run consecutively in wall-clock time
    # (thermal/scheduler drift is spread across conditions).
    #
    # Scope: the §10.2 CPU-overhead threshold check compares only the
    # all-off baseline against the winning cell, at pools 2/8/32 (not 128,
    # not the six single-factor cells -- those are not part of the
    # threshold gate). Restricting the expensive batched-CPU pass to
    # exactly those conditions (rather than all 32 wall-time conditions)
    # keeps this pass's total call count tractable while still measuring
    # every condition the threshold check actually needs.
    cpu_target_conditions = [
        idx for idx, (cell_name, _, n) in enumerate(conditions)
        if cell_name in ("all_off", *qualifying_analysis["minimal_sufficient_sets"][:1]) and n in (2, 8, 32)
    ]
    # Per-condition batch size: sized from this condition's already-measured
    # wall-time mean (a same-order-of-magnitude proxy for its CPU cost),
    # TARGETING >= 100x the measured process_time granularity per batch, but
    # capped at `cpu_batch_calls` (default 20000) to keep the pass tractable.
    # R2-6 correction: the prior docstring claimed every batch actually
    # REACHES that >=100-tick target; it does not -- the cap binds at pools
    # 2 and 8 (small per-call cost means 20000 calls does not add up to
    # 100 ticks), so actual measured coverage is reported per pool below
    # (`cpu_batch_actual_ticks`) rather than assumed from the target.
    cpu_batch_calls_by_cond: Dict[int, int] = {}
    for cond_idx in cpu_target_conditions:
        cell_name, flags, n = conditions[cond_idx]
        mean_wall_ns = max(results[cell_name][f"pool_{n}"]["mean_wall_ms"] * 1e6, 1000.0)
        target_ns = max(measured_granularity_ns, 1_000_000) * 100
        calls = int(target_ns / mean_wall_ns) + 1
        cpu_batch_calls_by_cond[cond_idx] = max(2000, min(calls, cpu_batch_calls))

    cpu_schedule: List[int] = []
    for cond_idx in cpu_target_conditions:
        cpu_schedule.extend([cond_idx] * cpu_batches_per_cell_pool)
    rng.shuffle(cpu_schedule)
    cpu_batches_ns: Dict[int, List[int]] = {i: [] for i in cpu_target_conditions}
    for cond_idx in cpu_schedule:
        cell_name, flags, n = conditions[cond_idx]
        q, ov = pool_cache[(cell_name, n)]
        kw = {k.lower(): v for k, v in flags.items()}
        calls = cpu_batch_calls_by_cond[cond_idx]
        t0 = time.process_time_ns()
        for _ in range(calls):
            resolve_rar_attachment_order_experimental(q, ov, **kw)
        cpu_batches_ns[cond_idx].append(time.process_time_ns() - t0)

    for cond_idx in cpu_target_conditions:
        cell_name, flags, n = conditions[cond_idx]
        calls = cpu_batch_calls_by_cond[cond_idx]
        per_call_estimates = [b / calls for b in cpu_batches_ns[cond_idx]]
        # R2-6: report actual measured tick coverage per pool, not the
        # >=100-tick target -- the cap binds at small pools (see comment
        # above `cpu_batch_calls_by_cond`).
        batch_ticks = [b / measured_granularity_ns for b in cpu_batches_ns[cond_idx]] if measured_granularity_ns else []
        results[cell_name][f"pool_{n}"]["cpu_batch_actual_ticks_min"] = min(batch_ticks) if batch_ticks else None
        results[cell_name][f"pool_{n}"]["cpu_batch_actual_ticks_median"] = statistics.median(batch_ticks) if batch_ticks else None
        results[cell_name][f"pool_{n}"]["cpu_batch_actual_ticks_max"] = max(batch_ticks) if batch_ticks else None
        results[cell_name][f"pool_{n}"]["cpu_batch_reached_100_tick_target"] = bool(batch_ticks) and min(batch_ticks) >= 100
        results[cell_name][f"pool_{n}"]["median_cpu_ns"] = statistics.median(per_call_estimates)
        results[cell_name][f"pool_{n}"]["median_cpu_ms"] = statistics.median(per_call_estimates) / 1e6
        results[cell_name][f"pool_{n}"]["cpu_batch_calls"] = calls
        results[cell_name][f"pool_{n}"]["cpu_batches"] = len(cpu_batches_ns[cond_idx])
        results[cell_name][f"pool_{n}"]["cpu_batch_raw_ns"] = cpu_batches_ns[cond_idx]
    cpu_measured_conditions = [f"{conditions[i][0]}/pool_{conditions[i][2]}" for i in cpu_target_conditions]

    # --- Compiler arm (R2-7 repair: genuine global interleaving, matching
    # the sidecar's method above). A9-R1 shuffled only the STORAGE index
    # within one (key, pool) block -- the CALL EXECUTION ORDER itself was
    # still fully sequential by (key, pool), identical to the sidecar defect
    # R1 already fixed. This block now builds one shuffled global
    # (key, pool, iteration) schedule across every compiler condition, using
    # the same fixed seed, and executes it in that order. --------------------
    compiler_keys = list(qualifying_analysis["minimal_sufficient_sets"] or ["all_off"])
    compiler_flags = {
        key: (_flags_from_key(key) if key != "all_off" else {f: False for f in FACTORS})
        for key in compiler_keys
    }
    compiler_pool_cache: Dict[Tuple[str, int], Tuple[RARQuery, AttachmentOrderOverlay]] = {}
    for key in compiler_keys:
        for n in pool_sizes:
            compiler_pool_cache[(key, n)] = _synthetic_pool(n)
    for key in compiler_keys:
        flags = compiler_flags[key]
        for n in pool_sizes:
            q, ov = compiler_pool_cache[(key, n)]
            for _ in range(warmups):
                compile_and_resolve_via_existing_contract(q, ov, m=flags["M"], r=flags["R"])

    compiler_conditions = [(key, n) for key in compiler_keys for n in pool_sizes]
    compiler_global_schedule: List[int] = []
    for cond_idx in range(len(compiler_conditions)):
        compiler_global_schedule.extend([cond_idx] * iterations)
    rng.shuffle(compiler_global_schedule)

    compiler_wall_ns_by_cond: Dict[int, List[int]] = {i: [] for i in range(len(compiler_conditions))}
    for cond_idx in compiler_global_schedule:
        key, n = compiler_conditions[cond_idx]
        flags = compiler_flags[key]
        q, ov = compiler_pool_cache[(key, n)]
        t0 = time.perf_counter_ns()
        compile_and_resolve_via_existing_contract(q, ov, m=flags["M"], r=flags["R"])
        compiler_wall_ns_by_cond[cond_idx].append(time.perf_counter_ns() - t0)

    compiler_results: Dict[str, dict] = {}
    for cond_idx, (key, n) in enumerate(compiler_conditions):
        wall_ns = compiler_wall_ns_by_cond[cond_idx]
        wall_sorted = sorted(wall_ns)
        compiler_results.setdefault(key, {})[f"pool_{n}"] = {
            "mean_wall_ms": statistics.mean(wall_ns) / 1e6,
            "p95_wall_ms": wall_sorted[int(len(wall_sorted) * 0.95) - 1] / 1e6,
            "iterations": len(wall_ns), "warmups": warmups,
        }

    threshold_checks = {}
    winning_keys = qualifying_analysis["minimal_sufficient_sets"]
    _cpu_probe_ok = []
    if winning_keys:
        for _n in (2, 8, 32):
            for _cn in ("all_off", winning_keys[0]):
                _cpu_probe_ok.append(results.get(_cn, {}).get(f"pool_{_n}", {}).get("median_cpu_ns", 0) > 0)
    cpu_evaluable = measured_granularity_ns > 0 and bool(_cpu_probe_ok) and all(_cpu_probe_ok)
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
                "within_threshold": (win_cpu <= 2 * base_cpu) if (base_cpu > 0 and cpu_evaluable) else None,
                "cpu_evaluable": cpu_evaluable,
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
        "protocol": "FULL_PRE_REGISTERED_200_WARMUP_2000_ITERATION_GLOBALLY_INTERLEAVED_WALL_PLUS_BATCHED_CPU",
        "seed": seed,
        "measured_process_time_granularity_ns": measured_granularity_ns,
        "cpu_measured_conditions": cpu_measured_conditions,
        "cpu_evaluable": cpu_evaluable,
        "environment": _environment_metadata(),
        "sidecar_results": results,
        "compiler_arm_results": compiler_results,
        "threshold_checks": threshold_checks,
        "threshold_checks_final_not_provisional": bool(threshold_checks),
        "interleaving_method": (
            "Sidecar wall time: one global (condition, iteration) index list "
            "across ALL cells and pools together, shuffled once with the "
            "fixed seed, executed in that shuffled order -- consecutive "
            "measured calls are not grouped by condition. R2-7: compiler-arm "
            "wall time now uses the SAME method (one global (key, pool, "
            "iteration) schedule across every compiler condition, shuffled "
            "with the same seed) -- A9-R1 only shuffled where each result "
            "was STORED, not the call execution order itself, which stayed "
            "sequential per (key, pool). CPU: interleaved BATCHED sampling; "
            "batch order across all conditions is shuffled with the same "
            "seed, each batch is `cpu_batch_calls` contiguous same-condition "
            "calls (contiguity required to divide batch CPU time by call "
            "count), `cpu_batches_per_cell_pool` batches per condition, "
            "median per-call estimate reported."
        ),
        "cpu_measurement_subset_of_frozen_16_3_item_7": {
            "frozen_requirement": (
                "§16.3 item 7: run all-off baseline, each single factor, the "
                "A9-amended candidate winning cell(s), and the compiler arm "
                "-- under the corrected protocol above, not a subset."
            ),
            "actual_cpu_conditions_measured": cpu_measured_conditions,
            "is_subset": True,
            "note": (
                "CPU batched sampling (unlike wall-time interleaving, which "
                "covers all 32 sidecar conditions plus the full compiler "
                "arm) is restricted to the 6 conditions the §10.2 CPU "
                "threshold gate actually compares (all-off x winning cell, "
                "pools 2/8/32). This is a disclosed, not silently applied, "
                "narrowing of §16.3 item 7's 'not a subset' instruction, "
                "carried forward unchanged from A9-R1 -- not newly "
                "introduced by R2."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Fresh-process causal matrix entrypoint
# ---------------------------------------------------------------------------

def _causal_only_main(out_path: Path) -> None:
    # R2-10: capture environment metadata INSIDE the actual per-process
    # entrypoint, not once in the parent process's performance pass (A9/
    # A9-R1's gap -- §16.3 item 8 asks for this per fresh-process run).
    env = _environment_metadata()
    rows = run_causal_matrix()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "rows": rows,
            "mechanism_hashes": _mechanism_hashes(),
            "protected_hashes": _protected_hashes(),
            "environment_metadata": env,
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
        # R2-10: per-run environment metadata, now captured inside each
        # subprocess (see `_causal_only_main`). A9's and A9-R1's historical
        # fresh-process runs did NOT capture this -- only source hashes were
        # recorded per run there; that historical gap is disclosed, not
        # retroactively fabricated (see `environment_metadata_disclosure`
        # in the telemetry written by `main()`).
        "run1_environment_metadata": run1_payload.get("environment_metadata"),
        "run2_environment_metadata": run2_payload.get("environment_metadata"),
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
    per_case_minimal_sets = compute_per_case_minimal_sets(run1)
    interactions_all_off = compute_pairwise_interactions_all_off(qualifying_analysis)
    best_cell = qualifying_analysis["minimal_sufficient_sets"][0] if qualifying_analysis["minimal_sufficient_sets"] else None
    interactions_on_background = compute_pairwise_interactions_on_background(run1, qualifying_analysis, best_cell)

    transport = run_transport_comparison(qualifying_analysis)
    sd_confirmation = run_sd_confirmation(qualifying_analysis)
    natural_confirmation = run_d1rq_natural_surface(qualifying_analysis)
    a2_5_reconciliation = run_a2_5_reconciliation()
    performance = run_performance_pass(qualifying_analysis)
    ir1_earlier_token_residual = run_ir1_earlier_token_residual_check()

    # Q characterization (task item): Q alone qualifies for the three
    # ordinal Case-B targets but breaks Case-A -- report explicitly rather
    # than only implying it through single_factor_sufficient (which will
    # NOT include Q, since Q breaks Case-A).
    q_alone_flags = {f: False for f in FACTORS}
    q_alone_flags["Q"] = True
    q_alone_key = _cell_key(q_alone_flags)
    q_alone_report = qualifying_analysis["cell_reports"].get(q_alone_key, {})
    b_case_ids = set(_B_CASE_IDS)
    # R2-5: the flag's NAME says "ordinal" -- its population must match. The
    # three ORDINAL Case-B targets are B-LATEST-WRONG-CLOCK,
    # B-FIRST-WRONG-CLOCK, B-LATEST-PROVENANCE-TWIN. B-DISTRACTOR is a
    # Case-B target but is NOT ordinal (no latest/first wording; it is
    # reached via the A9-2 Level-5.5 membership extension, which Q does not
    # touch). A9-R1's flag incorrectly checked disjointness against all
    # four `_B_CASE_IDS` including B-DISTRACTOR, so a B-DISTRACTOR failure
    # (from an unrelated cause -- Q alone has M/D off, so A9-2 never
    # restricts membership either) made the "ordinal" flag read False even
    # though Q alone correctly resolves all three ordinal targets.
    _b_ordinal_case_ids = {"B-LATEST-WRONG-CLOCK", "B-FIRST-WRONG-CLOCK", "B-LATEST-PROVENANCE-TWIN"}
    q_alone_failing = set(q_alone_report.get("failing_case_ids", []))
    q_characterization = {
        "q_alone_cell": q_alone_key,
        "q_alone_qualifies_globally": q_alone_report.get("qualifies", False),
        "q_alone_failing_case_ids": sorted(q_alone_failing),
        "q_alone_resolves_all_case_b_ordinal_targets": _b_ordinal_case_ids.isdisjoint(q_alone_failing),
        "q_alone_ordinal_case_ids_checked": sorted(_b_ordinal_case_ids),
        "q_alone_resolves_b_distractor": "B-DISTRACTOR" not in q_alone_failing,
        "interpretation": (
            "Q alone (M0G0P0D0R0Q1) is sufficient for the three ordinal "
            "Case-B targets (B-LATEST-WRONG-CLOCK, B-FIRST-WRONG-CLOCK, "
            "B-LATEST-PROVENANCE-TWIN) because unconditional Level-5.5 "
            "precedence abstains on any multi-attachment pool before the "
            "ordinal branch runs at all. It fails the qualification gate "
            "globally because the SAME unconditional precedence also "
            "preempts the three Case-A ordinal targets, which need the "
            "ordinal branch to run. Q is therefore INCOMPATIBLE WITH "
            "CASE-A under this tested construction, not globally useless: "
            "it is a correct, narrower mechanism for Case-B-only "
            "abstention, and the qualifying cell's Q=0 setting exists "
            "specifically to let the ordinal branch run for Case-A."
        ),
    }
    # verify B-DISTRACTOR too (non-ordinal, reachable_by_factors True via A9-2 -- unaffected by Q)
    q_characterization["q_alone_resolves_case_b_ordinal_only"] = _b_ordinal_case_ids.isdisjoint(q_alone_failing)

    # R2-8: §16.5 asks for per-row telemetry fields recording, per case,
    # whether G's effect is separable from M's (item 1) and whether R's
    # activation is attributable to overlay presence vs. the G+P gate
    # outcome specifically (item 2). Neither A9 nor A9-R1's causal rows
    # (`_run_one`) emit those fields directly -- this is a genuine
    # telemetry-format gap, not fixed here (adding new per-row fields would
    # be a new telemetry surface, not a report correction, and R2 is
    # report/label corrections only). The underlying conclusions remain
    # derivable post-hoc from the full 64-cell raw rows already on disk
    # (as both the A9 audit and the A9-R1 re-audit did by direct ablation
    # cross-referencing), so this is disclosed as a format gap, not an
    # evidence gap.
    telemetry_gaps = {
        "section_16_5_per_row_fields": {
            "required_fields": [
                "per-row: whether a G-ablated/M-present cell and an "
                "M-ablated/G-present cell produce different failure "
                "classes for the same case (§16.5 item 1, G/M "
                "separability)",
                "per-row: whether R's activation is attributable to "
                "overlay presence alone vs. the G+P gate outcome "
                "specifically (§16.5 item 2, R/overlay-vs-gate "
                "attribution)",
            ],
            "recorded_directly": False,
            "derivable_from_raw_rows": True,
            "derivation_method": (
                "Both conclusions were derived by direct cross-referencing "
                "of the full 64-cell raw causal rows (grouping by case_id "
                "across every (M,G,P,D,R,Q) combination and comparing "
                "scoring_class/no_op_reason across the relevant ablated "
                "cells) in the A9 independent audit (§3.2, §16.5 disclosure) "
                "and the A9-R1 independent re-audit (§4), not from a "
                "dedicated per-row field. This script does not add such a "
                "field; doing so is out of R2's report/label-correction "
                "scope."
            ),
            "classification": "TELEMETRY_FORMAT_LIMITATION_NOT_EVIDENCE_GAP",
        },
    }

    # R2-10: environment-metadata disclosure. §16.3 item 8 requires this per
    # fresh-process run; A9's and A9-R1's historical runs recorded only
    # source hashes per run (not full OS/Python/CPU metadata per run) --
    # this R2 run is the first to capture it per subprocess (see
    # `_causal_only_main`).
    environment_metadata_disclosure = {
        "frozen_requirement": (
            "§16.3 item 8: environment and source metadata -- OS, Python "
            "version, CPU identifier, process bitness, and source hashes -- "
            "reported per fresh-process run, not once for both."
        ),
        "a9_and_a9_r1_historical_runs": (
            "Recorded only mechanism_hashes/protected_hashes per fresh-"
            "process run (see M35_URIV1_A2_8L_A9_RUN1_CAUSAL.json / "
            "M35_URIV1_A2_8L_A9_R1_RUN1_CAUSAL.json payload keys); no full "
            "environment snapshot was captured inside either historical "
            "subprocess. That gap is disclosed here, not retroactively "
            "fabricated -- this R2 run does not backfill environment data "
            "into the historical A9/A9-R1 run files."
        ),
        "this_r2_run": (
            "Captures a full environment snapshot (OS, Python version, CPU "
            "identifier, process bitness, clock resolutions, current source "
            "hashes) inside each of the two fresh subprocess invocations "
            "(`_causal_only_main`), recorded per run in "
            "`fresh_process_report.run1_environment_metadata` / "
            "`run2_environment_metadata`."
        ),
        "classification": "HISTORICAL_GAP_DISCLOSED_NOT_BACKFILLED",
    }

    post_hashes = _protected_hashes()
    post_mechanism_hashes = _mechanism_hashes()
    hashes_unchanged = pre_hashes == post_hashes

    gxp_qualifying_background_interpretation = (
        "R2-2 correction (per the A9-R1 independent re-audit §5): on the "
        "qualifying-cell background where R=1, G^P meets §7's "
        "interacting-pair test for the three Case-A targets "
        "(A-LATEST-2, A-FIRST-2, A-LATEST-DISTRACTOR). This interaction is "
        "CONDITIONAL ON R=1 and is induced by the authorization/gating "
        "construction, not an independent two-factor causal contribution: "
        "A9-5's R ties the D-restricted domain unless both G and P pass; "
        "with R=0, all three Case-A targets pass regardless of G/P state "
        "(see pairwise_interactions_qualifying_cell_background 'GxR' and "
        "'PxR' tables, R=0 rows). No claim is made that G's ordinal content "
        "or P contributes independently of this gate. The M^D interaction "
        "(B-DISTRACTOR, C-NATURAL-PHOTOS-C2) is NOT gate-conditional in the "
        "same way and is reported separately."
    )
    natural_changed_rows_lineage = (
        "R2-3 correction: the verified 16 changed rows (8 NB-C-04 C2 + 8 "
        "NB-C-05 C2) are NOT a correction of an original A9 count from 8 to "
        "16. A9's original count of 8 (all NB-C-05 C2) was CORRECT for the "
        "pre-IR-1 implementation, under which NB-C-04 C2's D1RQ span never "
        "triggered the A9-2 extension at all (empty l5_pool_lexical) and so "
        "never changed from the H3-only baseline. The additional 8 "
        "NB-C-04 C2 rows exist BECAUSE IR-1 changed the Level-5.5 "
        "membership-restriction trigger pool from l5_pool_lexical to "
        "candidates_list, which is what makes NB-C-04 C2 responsive to the "
        "qualifying/ablation cells in the first place. Both counts (A9's 8, "
        "R2's 16) are correct for their respective, different mechanism "
        "states."
    )

    telemetry = {
        "schema": "m35.uriv1.a2_8l.a9r2.telemetry.v1",
        "corrects": "docs/plans/M35_URIV1_A2_8L_A9_R1_TELEMETRY.json (A9-R1; not overwritten)",
        "repair_of": "docs/plans/M35_URIV1_A2_8L_A9_TELEMETRY.json (A9, pre-repair; not overwritten)",
        "independent_audit": "docs/plans/M35_URIV1_A2_8L_A9_INDEPENDENT_AUDIT_REPORT.md",
        "independent_reaudit": "docs/plans/M35_URIV1_A2_8L_A9_R1_INDEPENDENT_REAUDIT_REPORT.md",
        "mechanism_repair_applied": "IR-1 (A9-2 Level-5.5 trigger pool corrected: l5_pool_lexical -> candidates_list; unchanged since A9-R1, verified byte-identical)",
        "frozen_checkpoint": "591f806",
        "pre_run_protected_hashes": pre_hashes, "post_run_protected_hashes": post_hashes,
        "protected_hashes_unchanged": hashes_unchanged,
        "pre_run_mechanism_hashes": pre_mechanism_hashes, "post_run_mechanism_hashes": post_mechanism_hashes,
        "fresh_process_report": fresh_process_report,
        "causal_rows": run1, "causal_row_count": len(run1),
        "repeat_reconciliation": reconciliation,
        "per_case_minimal_sets": per_case_minimal_sets,
        "gxp_qualifying_background_interpretation": gxp_qualifying_background_interpretation,
        "natural_changed_rows_lineage": natural_changed_rows_lineage,
        "transport_comparison": transport,
        "sd_confirmation": sd_confirmation,
        "natural_confirmation": natural_confirmation,
        "a2_5_reconciliation": a2_5_reconciliation,
        "performance": performance,
        "q_characterization": q_characterization,
        "ir1_earlier_token_residual": ir1_earlier_token_residual,
        "telemetry_gaps": telemetry_gaps,
        "environment_metadata_disclosure": environment_metadata_disclosure,
        "pre_a9_literal_plan_result": {
            "qualifying_cells": 0,
            "note": "Preserved per A9 §16.2 item 1 -- not reproduced by this rerun, stated as historical fact.",
        },
    }
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)

    aggregates = {
        "schema": "m35.uriv1.a2_8l.a9r2.aggregates.v1",
        "qualifying_analysis": qualifying_analysis,
        "per_case_minimal_sets": per_case_minimal_sets,
        "pairwise_interactions_all_off_background": interactions_all_off,
        "pairwise_interactions_qualifying_cell_background": interactions_on_background,
        "transport_conclusion": transport["conclusion"],
        "transport_conclusion_scope_note": transport["conclusion_scope_note"],
        "transport_mismatch_count": transport["mismatch_count"],
        "transport_mismatch_attribution_counts": transport["mismatch_attribution_counts"],
        "transport_factor_state_parity_applied": transport["factor_state_parity_applied"],
        "nb_d02_unauthorized_new_bind_count": natural_confirmation["nb_d02_unauthorized_new_bind_count"],
        "natural_expected_outcome_mismatch_count": natural_confirmation["expected_outcome_mismatch_count"],
        "natural_unexplained_expected_outcome_mismatch_count": natural_confirmation["unexplained_expected_outcome_mismatch_count"],
        "natural_expected_outcome_mismatch_reason_counts": natural_confirmation["expected_outcome_mismatch_reason_counts"],
        "natural_changed_rows_by_case_and_pool_condition": natural_confirmation["changed_rows_by_case_and_pool_condition"],
        "sd_raw_baseline_diff_count": sd_confirmation["raw_baseline_diff_count"],
        "natural_raw_baseline_diff_count": len(natural_confirmation["raw_baseline_vs_sidecar_all_off_diffs"]),
        "fresh_process_determinism_passed": fresh_process_report["fresh_process_determinism_passed"],
        "repeat_reconciliation_passed": reconciliation["reconciled"],
        "protected_hashes_unchanged": hashes_unchanged,
        "q_characterization": q_characterization,
        "cpu_evaluable": performance["cpu_evaluable"],
        "measured_process_time_granularity_ns": performance["measured_process_time_granularity_ns"],
        "gxp_qualifying_background_interpretation": gxp_qualifying_background_interpretation,
        "natural_changed_rows_lineage": natural_changed_rows_lineage,
        "ir1_earlier_token_residual_classification": ir1_earlier_token_residual["classification"],
        "ir1_earlier_token_residual_affected_row_count": ir1_earlier_token_residual["affected_row_count"],
        "telemetry_gaps": telemetry_gaps,
        "environment_metadata_disclosure_classification": environment_metadata_disclosure["classification"],
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
    print(f"Transport mismatch count: {transport['mismatch_count']}, attribution: {transport['mismatch_attribution_counts']}")
    print(f"NB-D-02 unauthorized new-bind count: {natural_confirmation['nb_d02_unauthorized_new_bind_count']}")
    print(f"Natural expected-outcome mismatch count: {natural_confirmation['expected_outcome_mismatch_count']} (unexplained: {natural_confirmation['unexplained_expected_outcome_mismatch_count']})")
    print(f"Protected hashes unchanged: {hashes_unchanged}")
    print(f"CPU evaluable: {performance['cpu_evaluable']} (measured granularity {performance['measured_process_time_granularity_ns']}ns)")
    print(f"IR-1 earlier-token residual: {ir1_earlier_token_residual['classification']} (affected rows: {ir1_earlier_token_residual['affected_row_count']})")
    print(f"Q-alone resolves all 3 ordinal Case-B targets: {q_characterization['q_alone_resolves_all_case_b_ordinal_targets']}")
    print(f"Transport bucket split: COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND={transport['mismatch_attribution_counts'].get('COMPILER_STEP4_NO_TIE_EMISSION_UNSAFE_BIND', 0)}, SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT={transport['mismatch_attribution_counts'].get('SIDECAR_GATE_ABSTAINS_COMPILER_CORRECT', 0)}")
    print(f"Wrote telemetry -> {TELEMETRY_PATH}")
    print(f"Wrote aggregates -> {AGGREGATES_PATH}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--causal-only":
        _causal_only_main(Path(sys.argv[2]))
    else:
        main()
