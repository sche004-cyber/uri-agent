"""Author the M33.3-R S5 L3 wording battery (synthetic, no private data).

Part A copies, verbatim, every S3 L1 `build` case whose frozen expectation is a
PENDING clarification contract (inputs unchanged; `source_case_id` records the
S3 case). Part B adds office-realistic synthetic cases with grounded extra
display facts (modified, version, sender, thread_subject, locator) and
multi-round cases, so the EXPLAIN and REASONING need classes are exercised.
The battery is hash-anchored by `manifest.json` (SHA-256 over LF bytes).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "fixtures" / "m33_3_s5"
SCHEMA_VERSION = "m33.3-r.s5.l3.v1"


def c(cid, title, ctype="document", owner="", rank=0, attach=False):
    return {"id": cid, "title": title, "candidate_type": ctype, "owner": owner, "recency_rank": rank,
            "is_attachment": attach}


def f(key, value, source):
    return {"key": key, "value": value, "source": source}


def ambiguous(case_id, category, reference, candidates, extra=None, *, excluded=(), round_index=1, scope=None,
              impact="RECOVERABLE", note=""):
    ids = [x["id"] for x in candidates if x["id"] not in excluded] if scope is None else scope
    return {"case_id": case_id, "layer": "L3", "category": category, "part": "B",
            "input": {"reference": reference, "candidates": candidates, "resolution": "AMBIGUOUS", "scope": ids,
                      "impact": impact, "excluded": list(excluded), "extra_facts": extra or {},
                      "round_index": round_index},
            "semantic_notes": note}


def part_b() -> list[dict]:
    cases = []
    add = cases.append
    add(ambiguous("L3B-01", "document_versions", "the budget", [
        c("doc-b1", "Q3 Budget.xlsx", owner="Finance", rank=0),
        c("doc-b2", "Q3 Budget (draft).xlsx", owner="Finance", rank=1),
        c("doc-b3", "Q3 Budget - board copy.xlsx", owner="Finance", rank=2)], {
        "doc-b1": [f("modified", "Sep 24", "file_store:doc-b1"), f("version", "v3", "file_store:doc-b1")],
        "doc-b2": [f("modified", "Sep 12", "file_store:doc-b2"), f("version", "v2", "file_store:doc-b2")],
        "doc-b3": [f("modified", "Sep 20", "file_store:doc-b3"), f("version", "v3", "file_store:doc-b3")]},
        note="Three versions; discriminators are version and modified date."))
    add(ambiguous("L3B-02", "document_versions", "the policy", [
        c("doc-p1", "Leave Policy 2025.docx", owner="HR", rank=1),
        c("doc-p2", "Leave Policy 2026.docx", owner="HR", rank=0)], {
        "doc-p1": [f("modified", "Jan 8", "file_store:doc-p1")],
        "doc-p2": [f("modified", "Sep 2", "file_store:doc-p2")]}, note="Year in title plus modified date."))
    add(ambiguous("L3B-03", "emails_threads", "the email from finance", [
        c("em-1", "Budget approval", "email", rank=0), c("em-2", "Invoice INV-2231 overdue", "email", rank=1),
        c("em-3", "Travel claims deadline", "email", rank=2)], {
        "em-1": [f("sender", "Priya Nair", "gmail:em-1"), f("modified", "Sep 25", "gmail:em-1")],
        "em-2": [f("sender", "Accounts Payable", "gmail:em-2"), f("modified", "Sep 23", "gmail:em-2")],
        "em-3": [f("sender", "Priya Nair", "gmail:em-3"), f("modified", "Sep 19", "gmail:em-3")]},
        note="Sender repeats; subject and date discriminate."))
    add(ambiguous("L3B-04", "emails_threads", "that thread with Dana", [
        c("th-1", "Re: Venue booking", "email", rank=0), c("th-2", "Re: Venue booking", "email", rank=1)], {
        "th-1": [f("sender", "Dana Whitfield", "gmail:th-1"), f("modified", "Sep 26", "gmail:th-1"),
                 f("thread_subject", "Venue booking - October offsite", "gmail:th-1")],
        "th-2": [f("sender", "Dana Whitfield", "gmail:th-2"), f("modified", "Aug 30", "gmail:th-2"),
                 f("thread_subject", "Venue booking - September workshop", "gmail:th-2")]},
        note="Identical subject lines; thread subject and date discriminate."))
    add(ambiguous("L3B-05", "attachments", "the attachment", [
        c("att-1", "signed_contract.pdf", owner="", rank=0, attach=True),
        c("att-2", "contract_redline.docx", owner="", rank=0, attach=True)], {
        "att-1": [f("locator", "attached to Contract renewal email", "gmail:em-9")],
        "att-2": [f("locator", "attached to Contract renewal email", "gmail:em-9")]},
        note="Two attachments on one email."))
    add(ambiguous("L3B-06", "attachments", "the spreadsheet you sent", [
        c("att-3", "headcount.xlsx", rank=0, attach=True), c("att-4", "headcount_old.xlsx", rank=1, attach=True)], {
        "att-3": [f("modified", "Sep 21", "gmail:em-4")], "att-4": [f("modified", "Jun 3", "gmail:em-5")]}))
    add(ambiguous("L3B-07", "same_name_people", "Sam", [
        c("per-1", "Sam Patel", "person", owner="Finance"), c("per-2", "Sam Okoro", "person", owner="Legal")],
        note="Distinct surnames, different teams."))
    add(ambiguous("L3B-08", "same_name_people", "Jordan Lee", [
        c("per-3", "Jordan Lee", "person", owner="Procurement"), c("per-4", "Jordan Lee", "person", owner="IT Support")],
        note="Identical names; team discriminates."))
    add(ambiguous("L3B-09", "temporal", "the latest report", [
        c("rep-1", "Monthly Sales Report - August.pdf", rank=0), c("rep-2", "Monthly Sales Report - July.pdf", rank=1)], {
        "rep-1": [f("modified", "Sep 3", "file_store:rep-1")], "rep-2": [f("modified", "Aug 4", "file_store:rep-2")]}))
    add(ambiguous("L3B-10", "temporal", "yesterday's minutes", [
        c("min-1", "Board minutes.docx", owner="Secretariat"), c("min-2", "Project steering minutes.docx", owner="PMO")], {
        "min-1": [f("modified", "Sep 26", "file_store:min-1")], "min-2": [f("modified", "Sep 26", "file_store:min-2")]}))
    add(ambiguous("L3B-11", "similar_files", "the onboarding checklist", [
        c("chk-1", "Onboarding checklist.docx", owner="HR"), c("chk-2", "Onboarding checklist - contractors.docx", owner="HR"),
        c("chk-3", "IT onboarding checklist.xlsx", owner="IT Support")]))
    add(ambiguous("L3B-12", "similar_files", "the logo", [
        c("img-1", "uri_logo.png", "image", owner="Design"), c("img-2", "uri_logo_dark.png", "image", owner="Design")]))
    add(ambiguous("L3B-13", "negation_contrast", "the other invoice", [
        c("inv-1", "Invoice INV-2231.pdf", owner="Vendor A"), c("inv-2", "Invoice INV-2240.pdf", owner="Vendor B"),
        c("inv-3", "Invoice INV-2252.pdf", owner="Vendor C")], excluded=("inv-1",),
        note="The first invoice is excluded by contrast and must not appear."))
    add(ambiguous("L3B-14", "negation_contrast", "not the draft, the other budget", [
        c("doc-b1", "Q3 Budget.xlsx", owner="Finance"), c("doc-b2", "Q3 Budget (draft).xlsx", owner="Finance"),
        c("doc-b3", "Q3 Budget - board copy.xlsx", owner="Finance")], excluded=("doc-b2",)))
    add(ambiguous("L3B-15", "display_overflow", "the proposal", [
        c(f"prop-{i}", t, owner=o, rank=i) for i, (t, o) in enumerate([
            ("Vendor proposal - Acme.pdf", "Procurement"), ("Vendor proposal - Birch.pdf", "Procurement"),
            ("Research proposal.docx", "R&D"), ("Grant proposal draft.docx", "R&D"),
            ("Office move proposal.pptx", "Facilities"), ("Training proposal.docx", "HR"),
            ("Budget proposal FY27.xlsx", "Finance")])],
        note="Seven candidates; five shown plus overflow."))
    add(ambiguous("L3B-16", "exactly_two", "the agenda", [
        c("ag-1", "Team meeting agenda.docx", owner="PMO", rank=0), c("ag-2", "AGM agenda.pdf", owner="Secretariat", rank=1)]))
    add(ambiguous("L3B-17", "conflicting_metadata", "Maria's report", [
        c("rp-1", "Quarterly report.docx", owner="Maria Chen", rank=0), c("rp-2", "Quarterly report.docx", owner="Maria Santos", rank=1)], {
        "rp-1": [f("modified", "Sep 22", "file_store:rp-1")], "rp-2": [f("modified", "Sep 22", "file_store:rp-2")]},
        note="Same title and date; owner discriminates."))
    add(ambiguous("L3B-18", "five_candidates", "the form", [
        c(f"form-{i}", t, owner=o, rank=i) for i, (t, o) in enumerate([
            ("Leave request form.docx", "HR"), ("Expense claim form.xlsx", "Finance"),
            ("Access request form.pdf", "IT Support"), ("Purchase request form.docx", "Procurement"),
            ("Feedback form.docx", "PMO")])]))
    reasoning = [
        ("L3B-19", "reasoning_escalation", "the contract", [
            c("ct-1", "Supplier contract - Acme.pdf", owner="Legal", rank=0),
            c("ct-2", "Supplier contract - Birch.pdf", owner="Legal", rank=1)], {}),
        ("L3B-20", "reasoning_escalation", "that document Alex mentioned", [
            c("dx-1", "Risk register.xlsx", owner="PMO", rank=0), c("dx-2", "Audit findings.docx", owner="Audit", rank=1),
            c("dx-3", "Risk appetite statement.pdf", owner="Board", rank=2)], {}),
        ("L3B-21", "reasoning_escalation", "the budget", [
            c("doc-b1", "Q3 Budget.xlsx", owner="Finance", rank=0), c("doc-b3", "Q3 Budget - board copy.xlsx", owner="Finance", rank=1)], {
            "doc-b1": [f("version", "v3", "file_store:doc-b1")], "doc-b3": [f("version", "v3", "file_store:doc-b3")]}),
    ]
    for cid, cat, ref, cands, extra in reasoning:
        add(ambiguous(cid, cat, ref, cands, extra, round_index=3,
                      note="Third round without resolution; R1.8 hand-off class."))
    add({"case_id": "L3B-22", "layer": "L3", "category": "zero_candidates", "part": "B",
         "input": {"reference": "the Henderson file", "candidates": [c("unrelated-1", "Weekly roster.xlsx")],
                   "resolution": "UNKNOWN", "scope": [], "impact": "RECOVERABLE", "excluded": [],
                   "extra_facts": {}, "round_index": 1}, "semantic_notes": "Nothing matches."})
    add({"case_id": "L3B-23", "layer": "L3", "category": "one_insufficient", "part": "B",
         "input": {"reference": "send it to the board", "candidates": [c("doc-b3", "Q3 Budget - board copy.xlsx", owner="Finance")],
                   "resolution": "RESOLVED", "scope": ["doc-b3"], "impact": "CONSEQUENTIAL", "excluded": [],
                   "extra_facts": {}, "round_index": 1},
         "semantic_notes": "Single candidate but consequential action; confirm."})
    add({"case_id": "L3B-24", "layer": "L3", "category": "one_insufficient", "part": "B",
         "input": {"reference": "delete the old roster", "candidates": [c("ros-1", "Weekly roster - 2025.xlsx", owner="Operations")],
                   "resolution": "RESOLVED", "scope": ["ros-1"], "impact": "CONSEQUENTIAL", "excluded": [],
                   "extra_facts": {"ros-1": [f("modified", "Dec 19", "file_store:ros-1")]}, "round_index": 1}})
    return cases


def part_a() -> list[dict]:
    battery = json.loads((ROOT / "fixtures" / "m33_3_arn" / "battery.json").read_text(encoding="utf-8"))
    cases = []
    for case in battery["cases"]:
        exp = case["expected"]
        if case["layer"] != "L1" or case["operation"] != "build" or exp.get("state") != "PENDING" or exp.get("error"):
            continue
        data = dict(case["input"])
        data.setdefault("excluded", [])
        data["extra_facts"] = {}
        data["round_index"] = 1
        cases.append({"case_id": f"L3A-{len(cases) + 1:02d}", "layer": "L3", "category": case["category"],
                      "part": "A", "source_case_id": case["case_id"], "input": data})
    return cases


def main() -> None:
    cases = part_a() + part_b()
    battery = {"schema_version": SCHEMA_VERSION, "cases": cases}
    text = json.dumps(battery, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "battery.json").write_bytes(text.encode("utf-8"))
    manifest = {"battery_file": "battery.json", "schema_version": SCHEMA_VERSION, "case_count": len(cases),
                "part_a_count": sum(x["part"] == "A" for x in cases), "part_b_count": sum(x["part"] == "B" for x in cases),
                "battery_bytes": len(text.encode("utf-8")),
                "battery_lf_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "hash_rule": "SHA-256 over UTF-8 bytes with CRLF normalized to LF",
                "privacy": "synthetic-only",
                "provenance": "Part A verbatim from fixtures/m33_3_arn/battery.json (S3 v2) L1 build cases with a PENDING contract; Part B authored for M33.3-R S5 (office-realistic synthetic facts)."}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest)


if __name__ == "__main__":
    main()
