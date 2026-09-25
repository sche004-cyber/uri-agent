"""M33.3 Batch A structural gates: G-P1 provider interchangeability, G-N1
model-native capability preservation, G-S4 local-only endpoint guard."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import m33_3_batch_a_battery as bat  # noqa: E402
import m33_3_batch_a_run as run_mod  # noqa: E402
import m33_3_batch_a_scorer as sc  # noqa: E402

BATTERY = json.loads((REPO_ROOT / "fixtures" / "m33_3_batch_a" / "battery.json").read_text(encoding="utf-8"))


def test_scorer_has_no_provider_specific_branches():
    source = (REPO_ROOT / "scripts" / "m33_3_batch_a_scorer.py").read_text(encoding="utf-8").casefold()
    for name in ("needle", "qwen", "lmstudio", "r-9b", "r-needle", "r-null", "r-det", "cactus"):
        assert name not in source, name


def test_every_condition_is_scored_through_one_output_interface():
    outputs = [
        {"condition": "R-NULL", "disposition": "ESCALATE", "proposals": []},
        {"condition": "R-NEEDLE", "disposition": "PROPOSE", "proposals": [{"tool": "file.open", "arguments": {"file_id": "F-101"}}]},
        {"condition": "R-9B", "disposition": "ASK", "proposals": []},
    ]
    case = BATTERY["cases"][0]
    keys = {frozenset(sc.score_row(case, o, BATTERY["tool_catalog"]).keys()) for o in outputs}
    assert len(keys) == 1


def test_main_brain_gets_native_tools_and_no_edge_tier_schema(monkeypatch):
    captured = []

    def fake_http(url, payload=None, timeout=300):
        captured.append(payload)
        return {"choices": [{"message": {"content": "Which file?"}, "finish_reason": "stop"}], "usage": {}}

    monkeypatch.setattr(run_mod, "_http_json", fake_http)
    case = next(c for c in BATTERY["cases"] if c["case_id"] == "RWB-010")
    out = run_mod.run_main_brain_case(case, BATTERY["tool_catalog"])
    payload = captured[0]
    assert len(payload["tools"]) == len(case["available_tools"])  # every offered tool, native function-calling form
    assert all(t["type"] == "function" for t in payload["tools"])
    system = payload["messages"][0]["content"]
    assert run_mod.NEEDLE_SYSTEM_PROMPT not in system
    assert "at most one" not in system.casefold()  # no single-tool limit imposed on the Main Brain
    assert "response_format" not in payload  # no forced JSON schema
    blob = json.dumps(payload)
    for hidden in ("scoring_rule", "expected_", "prohibited_actions", "gold_span"):
        assert hidden not in blob
    assert out["disposition"] == "ASK"


def test_main_brain_loop_allows_parallel_and_multi_step_calls(monkeypatch):
    replies = iter([
        {"choices": [{"message": {"content": "", "tool_calls": [
            {"id": "a", "function": {"name": "file_search", "arguments": "{\"query\": \"Q3 budget\"}"}},
            {"id": "b", "function": {"name": "file_open", "arguments": "{\"file_id\": \"F-101\"}"}}]}, "finish_reason": "tool_calls"}]},
        {"choices": [{"message": {"content": "", "tool_calls": [
            {"id": "c", "function": {"name": "email_draft", "arguments": "{\"to\": \"P-01\", \"attachment_file_id\": \"F-101\"}"}}]},
            "finish_reason": "tool_calls"}]},
    ])
    monkeypatch.setattr(run_mod, "_http_json", lambda url, payload=None, timeout=300: next(replies))
    case = next(c for c in BATTERY["cases"] if c["case_id"] == "RWB-010")
    out = run_mod.run_main_brain_case(case, BATTERY["tool_catalog"])
    assert [p["tool"] for p in out["proposals"]] == ["file.search", "file.open", "email.draft"]
    assert out["telemetry"]["stop_reason"] == "confirmation_required"


def test_non_local_endpoint_is_refused():
    with pytest.raises(RuntimeError):
        run_mod._http_json("https://example.org/v1/models")


def test_mock_tools_never_execute_confirm_or_destructive_tools():
    case = BATTERY["cases"][0]
    for tool, meta in BATTERY["tool_catalog"].items():
        if meta["risk"] != "AUTO":
            assert run_mod.mock_tool_result(tool, {}, case) == {"status": "unsupported_mock"}


# --- R2-D: per-row artifact provenance -----------------------------------------

TELEMETRY = json.loads((REPO_ROOT / "docs" / "plans" / "M33_3_BATCH_A_TELEMETRY.json").read_text(encoding="utf-8"))
ROWS = TELEMETRY["rows"]


def _rows(cond):
    rows = [r for r in ROWS if r["condition"] == cond]
    assert len(rows) == 60
    return rows


def test_needle_rows_carry_verified_artifact_provenance():
    for r in _rows("R-NEEDLE"):
        t = r["telemetry"]
        assert t["artifact_hash"] == run_mod.NEEDLE_ARTIFACT_SHA256
        assert t["artifact_size_bytes"] == 35_335_380
        assert t["package_version"] == "3.0.2"
        assert t["artifact_hash_status"] == "COMPUTED_POST_RUN_FROM_CACHE_FILE"
        assert t["raw_artifact_hash"] is None  # raw provider output was not rewritten


def test_main_brain_rows_carry_verified_artifact_provenance():
    for cond in ("R-9B", "R-9B-SIMCONFIRM"):
        for r in _rows(cond):
            t = r["telemetry"]
            assert t["artifact_hash"] == run_mod.MAIN_ARTIFACT_SHA256
            assert t["artifact_size_bytes"] == 5_629_109_056
            assert t["artifact_hash_status"] == "COMPUTED_PRE_RUN_AT_WP_A0"


def test_null_rows_are_explicitly_no_provider():
    for r in _rows("R-NULL"):
        t = r["telemetry"]
        assert t["artifact_hash"] is None
        assert t["artifact_hash_status"] == "NOT_APPLICABLE_NO_PROVIDER"
        assert t["provider_id"] == "none"


def test_apply_row_provenance_does_not_mutate_raw():
    raw = {"artifact_hash": None, "latency_ms": 1}
    out = run_mod.apply_row_provenance(raw, "R-NEEDLE")
    assert raw == {"artifact_hash": None, "latency_ms": 1}
    assert out["artifact_hash"] == run_mod.NEEDLE_ARTIFACT_SHA256


# --- R2-B: execution evidence is derived, never assumed ------------------------

def test_needle_harness_yields_no_execution_evidence():
    out = {"condition": "R-NEEDLE", "proposals": [{"tool": "file.open", "arguments": {}}], "telemetry": {}}
    assert run_mod.execution_evidence(out, BATTERY["tool_catalog"])["executed_tools"] == []


def test_main_brain_execution_counts_only_consumed_auto_results():
    catalog = BATTERY["tool_catalog"]
    consumed = {"condition": "R-9B", "proposals": [{"tool": "file.open", "arguments": {}, "step": 0}],
                "telemetry": {"usage": [{}, {}]}}
    assert run_mod.execution_evidence(consumed, catalog)["executed_tools"] == ["file.open"]
    unconsumed = dict(consumed, telemetry={"usage": [{}]})
    assert run_mod.execution_evidence(unconsumed, catalog)["executed_tools"] == []
    confirm = {"condition": "R-9B", "proposals": [{"tool": "document.convert", "arguments": {}, "step": 0}],
               "telemetry": {"usage": [{}, {}]}}
    assert run_mod.execution_evidence(confirm, catalog)["executed_tools"] == []


def test_published_needle_rows_have_no_completion():
    assert not [r for r in _rows("R-NEEDLE") if r["outcome"] == "CORRECT_COMPLETION"]


# --- R2-A: adjudication integrity ----------------------------------------------

ADJ = json.loads((REPO_ROOT / "docs" / "plans" / "M33_3_BATCH_A_R2_TRANSCRIPT_ADJUDICATIONS.json").read_text(encoding="utf-8"))


def test_adjudications_are_quote_backed_and_cover_every_text_dependent_row():
    import m33_3_batch_a_adjudications as adj_mod
    if not (adj_mod.RAW_DIR / "main9b.json").exists():
        pytest.skip("retained raw evidence not present in this checkout")
    rebuilt = adj_mod.build()  # raises on any non-verbatim quote or coverage gap
    assert rebuilt["entries"] == ADJ["entries"]


def test_every_text_channel_row_needing_adjudication_has_one():
    assert not [r for r in ROWS if r["outcome"] == "UNADJUDICATED_TEXT"]


def test_adjudication_is_not_labelled_independent():
    assert "NOT independent" in ADJ["adjudicator"]
