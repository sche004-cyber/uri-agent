"""Author the frozen, synthetic M33.3 S3 L1/L2 qualification fixture.

Run only when intentionally creating a new battery version. The qualification
runner never writes this fixture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "m33_3_arn"
CASES: list[dict] = []


def add(layer: str, category: str, operation: str, data: dict, expected: dict, source: str) -> None:
    CASES.append({"case_id": f"ARB-{len(CASES) + 1:03d}", "layer": layer,
                  "category": category, "operation": operation, "input": data,
                  "expected": expected, "source": source})


def candidate(cid: str, title: str, kind: str = "document", *, owner: str | None = None,
              recency: int = 0, attachment: bool = False) -> dict:
    return {"id": cid, "title": title, "candidate_type": kind, "owner": owner,
            "recency_rank": recency, "is_attachment": attachment}


def build(category: str, candidates: list[dict], kind: str, *, reference: str = "which one",
          outcome: str = "AMBIGUOUS", impact: str = "RECOVERABLE", subset: list[str] | None = None,
          shown: list[str] | None = None, overflow: int = 0, axis: str | None = None,
          state: str = "PENDING", error: bool = False, excluded: list[str] | None = None) -> None:
    scope = subset if subset is not None else [c["id"] for c in candidates]
    add("L1", category, "build", {"reference": reference, "candidates": candidates,
        "resolution": outcome, "scope": scope, "impact": impact, "excluded": excluded or []},
        {"state": state, "kind": kind, "scope": scope if kind != "ERROR" else [],
         "shown": shown if shown is not None else (scope[:5] if kind in ("CHOOSE_ONE", "CONFIRM_ONE") else []),
         "overflow": overflow, "axis": axis, "error": error},
        "Plan A R4.3/R4.12; S1 state §§4,6")


# 18 grounded domain variants. The expected kind is independently specified.
for i, n in enumerate((2, 3, 4), 1):
    build("same_name_people", [candidate(f"person-{i}-{j}", "Alex Morgan", "person",
                                  owner=f"Unit {j}") for j in range(n)],
          "CHOOSE_ATTRIBUTE", axis="owner", shown=[], reference="Alex Morgan")
for i in range(3):
    build("similar_files", [candidate(f"file-{i}-{j}", f"Budget {2024+j}{'-rev' if i == 2 else ''}.pdf",
                                    owner="Finance") for j in range(2+i)], "CHOOSE_ONE",
          reference="the budget file")
for i in range(3):
    build("temporal", [candidate(f"time-{i}-{j}", f"Minute {j+1}.pdf", recency=j)
                       for j in range(2+i)], "CHOOSE_ONE", reference=("latest", "earlier", "first")[i])
for i in range(3):
    build("attachments", [candidate(f"attachment-{i}-{j}", f"Attachment {j+1}.pdf",
                                      attachment=True) for j in range(2+i)], "CHOOSE_ONE",
          reference="the attachment")
for i in range(3):
    build("emails_threads", [candidate(f"email-{i}-{j}", f"Email thread {j+1}", "email",
                                       owner=f"Sender {j+1}") for j in range(2+i)],
          "CHOOSE_ONE", reference="the email thread")
for i, n in enumerate((2, 3, 4)):
    build("document_versions", [candidate(f"version-{i}-{j}", "Policy.pdf", owner="Office",
                                         recency=j) for j in range(n)],
          "CHOOSE_ATTRIBUTE", axis="recency", shown=[], reference="the policy version")

# 10 scope/cardinality and fail-closed boundaries.
for reference in ("missing report", "unknown attachment"):
    build("zero_candidates", [], "FREE_INPUT_ONLY", reference=reference, outcome="UNKNOWN")
for impact in ("CONSEQUENTIAL", "RECOVERABLE"):
    candidates = [candidate(f"one-{impact}", "Proposal.pdf")]
    build("one_insufficient", candidates, "CONFIRM_ONE" if impact == "CONSEQUENTIAL" else "DIRECT",
          outcome="RESOLVED", impact=impact, state="PENDING" if impact == "CONSEQUENTIAL" else "TENTATIVE")
for i in range(2):
    build("five_candidates", [candidate(f"five-{i}-{j}", f"File {j}.pdf") for j in range(5)],
          "CHOOSE_ONE", reference="one of five")
for i in range(2):
    rows = [candidate(f"overflow-{i}-{j}", f"File {j}.pdf") for j in range(7+i)]
    build("display_overflow", rows, "CHOOSE_ONE", shown=[c["id"] for c in rows[:5]],
          overflow=len(rows)-5, reference="one of many")
for i in range(2):
    build("indistinguishable", [candidate(f"duplicate-{i}-{j}", "Same.pdf", owner="Same")
                                  for j in range(2)], "ERROR", error=True, state="ERROR")

# 12 typed-response scenarios. Each supplies real candidate identity data; the
# runner uses S1 BindingService, and expected states are fixture-owned.
responses = [
    ("click_replay", "CONFIRMED", "y"),
    ("wrong_session", "REJECTED", None),
    ("wrong_round", "REJECTED", None),
    ("stale_candidate", "REJECTED", None),
    ("hidden_free_input", "CONFIRMED", "hidden"),
    ("out_of_scope_free_input", "PENDING", None),
    ("free_exact_id", "CONFIRMED", "y"),
    ("free_title_heuristic", "TENTATIVE", "y"),
    ("free_unknown", "PENDING", None),
    ("attribute_narrow", "PENDING", None),
    ("change_rebind", "CONFIRMED", "y"),
    ("budget_stop", "REJECTED", None),
    ("change_post_execution", "CONFIRMED", "y"),
    ("stale_title", "REJECTED", None),
    ("candidate_removed", "REJECTED", None),
    ("other_candidate_changed", "CONFIRMED", "y"),
    ("budget_cost_stop", "REJECTED", None),
]
for scenario, state, cid in responses:
    rows = [candidate("x", "Report.pdf", owner="Alice"),
            candidate("y", "Report.pdf", owner="Bob"),
            candidate("hidden", "Hidden.pdf", owner="Carol")]
    if scenario == "hidden_free_input":
        rows = [candidate("x", "First.pdf", owner="Alice"),
                candidate("y", "Second.pdf", owner="Bob")]
        rows += [candidate(f"extra-{i}", f"Extra {i}.pdf", owner="Unit") for i in range(4)]
        rows.append(candidate("hidden", "Hidden.pdf", owner="Carol"))
    elif scenario not in ("attribute_narrow", "budget_stop", "budget_cost_stop"):
        rows[0]["title"] = "First.pdf"
        rows[1]["title"] = "Second.pdf"
    if scenario == "free_title_heuristic":
        rows[1]["title"] = "Report.pdf"
    phrase = {"hidden_free_input": "hidden", "out_of_scope_free_input": "hidden",
              "free_exact_id": "y", "free_title_heuristic": "Report",
              "free_unknown": "unmatched text", "budget_stop": "unmatched text",
              "budget_cost_stop": "unmatched text"}.get(scenario)
    add("L1", scenario, "respond", {"scenario": scenario, "candidates": rows,
        "scope": [r["id"] for r in rows] if scenario == "hidden_free_input" else ["x", "y"],
        "reference": "Second.pdf" if scenario in ("change_rebind", "change_post_execution") else "which report",
        "response_text": phrase},
        {"state": state, "candidate_id": cid},
        "S1 state §§4.1,6; Plan A R3.1/R3.2/R4.4/R4.5/R4.12")

# 4 S2 action-level gate cases over supplied binding states.
for impact, binding, outcome in (("RECOVERABLE", "TENTATIVE", "ALLOWED_TENTATIVE_RECOVERABLE"),
                                 ("CONSEQUENTIAL", "TENTATIVE", "CONFIRMATION_REQUIRED"),
                                 (None, "TENTATIVE", "CONFIRMATION_REQUIRED"),
                                 (None, "CONFIRMED", "ALLOWED_CONFIRMED")):
    add("L1", "impact_gate", "gate", {"impact": impact, "binding": binding},
        {"outcome": outcome, "allowed": outcome != "CONFIRMATION_REQUIRED"},
        "S2 state §5 G5-G7; D1 and U-1")

# Complete the Plan A §10 L1 category minimums. Model/routing-only portions
# remain outside S3; Edge/generator fields mean deterministic template path.
for i in range(2):
    build("conflicting_metadata", [candidate(f"conflict-{i}-a", "Record.pdf", owner="North"),
          candidate(f"conflict-{i}-b", "Record.pdf", owner="South")], "CHOOSE_ATTRIBUTE",
          axis="owner", shown=[], reference="record")
for i in range(2):
    build("exactly_two", [candidate(f"two-{i}-a", "First.pdf"),
          candidate(f"two-{i}-b", "Second.pdf")], "CHOOSE_ONE", reference="which file")
for i in range(3):
    rows = [candidate(f"contrast-{i}-excluded", f"Avoid {i}.pdf"),
            candidate(f"contrast-{i}-a", "One.pdf"), candidate(f"contrast-{i}-b", "Two.pdf")]
    build("negation_contrast", rows, "CHOOSE_ONE", reference="the other file",
          subset=[rows[1]["id"], rows[2]["id"]], excluded=[rows[0]["id"]])
for i in range(2):
    build("edge_disabled", [candidate(f"edge-{i}-a", "One.pdf"),
          candidate(f"edge-{i}-b", "Two.pdf")], "CHOOSE_ONE", reference="which file")
    CASES[-1]["input"]["edge_state"] = "OFF"
for i in range(2):
    build("generator_unavailable", [candidate(f"generator-{i}-a", "One.pdf"),
          candidate(f"generator-{i}-b", "Two.pdf")], "CHOOSE_ONE", reference="which file")
    CASES[-1]["input"]["renderer_availability"] = "UNAVAILABLE" if i == 0 else "TIMEOUT"

assert len(CASES) == 60

# 20 L2 probes. V-ORDER is diagnostic and allowed only because URI owns the
# final displayed ordering; all other injections are acceptance-critical.
mutations = [
    ("malformed_output", "not_json", "V-SCHEMA", False),
    ("malformed_output", "extra_field", "V-SCHEMA", False),
    ("malformed_output", "duplicate_json_key", "V-SCHEMA", False),
    ("invented_option", "unknown_slot", "V-SLOT-UNKNOWN", False),
    ("invented_option", "extra_slot", "V-SLOT-UNKNOWN", False),
    ("rank_mutation", "reverse_order", "V-ORDER", True),
    ("omission", "omit_first", "V-SLOT-MISSING", False),
    ("omission", "omit_second", "V-SLOT-MISSING", False),
    ("unsupported_fact", "invented_label", "V-UNSUPPORTED-FACT", False),
    ("unsupported_fact", "invented_question", "V-UNSUPPORTED-FACT", False),
    ("unsupported_fact", "invented_location", "V-UNSUPPORTED-FACT", False),
    ("cross_slot", "swap_labels", "V-CROSS-SLOT", False),
    ("cross_slot", "borrow_owner", "V-CROSS-SLOT", False),
    ("presumption", "selected_question", "V-SELECTION", False),
    ("presumption", "assume_question", "V-SELECTION", False),
    ("contrast", "excluded_question", "V-EXCLUSION", False),
    ("contrast", "excluded_label", "V-EXCLUSION", False),
    ("contrast", "excluded_second", "V-EXCLUSION", False),
    ("duplicate_label", "duplicate_labels", "V-LABEL-DUP", False),
    ("duplicate_label", "duplicate_labels_case", "V-LABEL-DUP", False),
]
for category, mutation, flag, valid in mutations:
    add("L2", category, "render", {"mutation": mutation,
        "candidates": [candidate("a", "Budget.pdf", owner="Alice"),
                       candidate("b", "Forecast.pdf", owner="Bob")]},
        {"flag": flag, "valid": valid},
        "Plan A §§6,10-11; S1 RenderValidator contract")

assert len(CASES) == 80
OUT.mkdir(parents=True, exist_ok=True)
payload = {"schema_version": "m33.3.s3.l1l2.v1", "cases": CASES}
raw = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
(OUT / "battery.json").write_bytes(raw)
manifest = {"schema_version": "m33.3.s3.l1l2.v1", "battery_file": "battery.json",
            "case_count": len(CASES), "l1_count": 60, "l2_count": 20,
            "battery_bytes": len(raw), "battery_lf_sha256": hashlib.sha256(raw).hexdigest(),
            "hash_rule": "SHA-256 over UTF-8 bytes with CRLF normalized to LF",
            "provenance": "Synthetic S3 cases authored from Plan A R4, S1/S2 frozen contracts; no private data",
            "privacy": "synthetic-only"}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Authored {len(CASES)} cases: {manifest['battery_lf_sha256']}")
