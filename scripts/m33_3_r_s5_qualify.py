"""M33.3-R S5 clarification-wording qualification harness.

Modes:
  --mode deterministic   no model: template validity, need classes, policy-mode
                         frozen gates with recording renderers (Edge OFF never
                         invokes Edge; SIMPLE/EXPLAIN never cold-load).
  --mode exploratory     deterministic + live no-cold-load probe + real arm runs
                         (template / Edge / Capable x decoding x prompt variant)
                         + blind comparison sheet. No thresholds are applied.
  --mode final           like exploratory but evaluates the frozen threshold
                         gate file; refuses to run without it.

Evidence integrity: raw model text is stored untruncated; every row records
validator flags, latency, tokens and the model load state before/after.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.m33_3_r_anchors import require_anchors
from scripts.m33_3_s3_qualify import make_query, make_resolution
from uri_core.core.edge.routing_policy import RouteTarget, WordingNeedClass, route_clarification_wording
from uri_core.core.edge.runtime_inventory import EdgeRuntimeInventory, RuntimeProfile
from uri_core.core.edge.settings import EdgeSettings
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.reference_clarification.render_contracts import make_render_request
from uri_v1.reference_clarification.render_validator import validate_render
from uri_v1.reference_clarification.template_renderer import render_template
from uri_v1.turn.rar_clarification_contract import CandidateFact, ESCAPE_LABEL
from uri_v1.wording.need_class import NEED_CLASS_POLICY_VERSION, classify_need
from uri_v1.wording.renderer_port import PROMPT_VERSION, LMStudioRenderer, RenderAttempt, TemplateRenderer
from uri_v1.wording.selector import select_wording, validated_output

FIXTURES = ROOT / "fixtures" / "m33_3_s5"
GATE_FILE = FIXTURES / "threshold_gate.json"
NOW = datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc)
EDGE_MODEL = "qwen3.5-2b"
CAPABLE_MODEL = "qwen3.5-9b"
INVENTORY = EdgeRuntimeInventory(runtimes={"lmstudio": RuntimeProfile("lmstudio", frozenset({EDGE_MODEL}))})
MODES = ("EDGE_ONLY", "HYBRID", "MAIN_BRAIN_PREFERRED")


def load_battery() -> tuple[dict, dict]:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    raw = (FIXTURES / manifest["battery_file"]).read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != manifest["battery_lf_sha256"] or len(raw) != manifest["battery_bytes"]:
        raise ValueError("S5 L3 battery hash/size mismatch")
    battery = json.loads(raw)
    if battery["schema_version"] != manifest["schema_version"] or len(battery["cases"]) != manifest["case_count"]:
        raise ValueError("S5 L3 battery schema/count mismatch")
    return battery, manifest


def build_contract(case: dict):
    data = case["input"]
    query = make_query(data)
    extra = {cid: tuple(CandidateFact(**f) for f in facts) for cid, facts in data.get("extra_facts", {}).items()}
    built = build_clarification(query, make_resolution(query, data["resolution"], data["scope"]),
                                session_id="s5-session", turn_id=f"s5-{case['case_id']}",
                                wrong_binding_impact=data["impact"], now=NOW,
                                excluded_ids=tuple(data.get("excluded", ())), extra_facts=extra,
                                round_index=data.get("round_index", 1))
    if built.contract is None:
        raise ValueError(f"{case['case_id']} produced no clarification contract")
    return query, built.contract


def id_leak(contract, query, text: str | None) -> list[str]:
    if not text:
        return []
    ids = set(query.candidate_ids) | set(contract.scope_candidate_ids)
    return sorted(i for i in ids if i in text)


def select_wording_policy(contract, *, settings: EdgeSettings, inventory: EdgeRuntimeInventory, edge_renderer,
                          capable_renderer, edge_wording_qualified: bool, capable_available: bool,
                          resource_admitted: bool, explicit_model_id=None, auto_capable_model_id=None, trace_id=None):
    """Bind the single uri_core router into the uri_v1 selector (uri_v1 never imports uri_core)."""
    def route(need_class: str, edge_warm: bool):
        return route_clarification_wording(
            settings, inventory, need_class, edge_wording_qualified=edge_wording_qualified and edge_renderer is not None,
            edge_warm=edge_warm, resource_admitted=resource_admitted,
            capable_available=capable_available and capable_renderer is not None,
            explicit_model_id=explicit_model_id, auto_capable_model_id=auto_capable_model_id)
    return select_wording(contract, route_wording=route, edge_renderer=edge_renderer,
                          capable_renderer=capable_renderer, trace_id=trace_id)


def settings(mode: str, enabled: bool) -> EdgeSettings:
    return EdgeSettings(intelligence_mode=mode, enabled=enabled, edge={"runtime_id": "lmstudio", "model_id": EDGE_MODEL})


class RecordingRenderer:
    """Deterministic stand-in used only to prove routing gates; returns template JSON."""

    def __init__(self, arm: str, warm: bool) -> None:
        self.arm, self.warm, self.calls = arm, warm, 0

    def model_state(self) -> str:
        return "loaded" if self.warm else "not-loaded"

    def render(self, request, contract) -> RenderAttempt:
        self.calls += 1
        attempt = TemplateRenderer().render(request, contract)
        return RenderAttempt(self.arm, attempt.raw_text, 0.0, invoked_model=self.arm,
                             model_state_before=self.model_state(), model_state_after=self.model_state())


def deterministic_checks(cases: list[dict]) -> dict:
    rows, violations = [], []
    for case in cases:
        query, contract = build_contract(case)
        template = render_template(contract)
        valid = validate_render(contract, template)
        need = classify_need(contract)
        rows.append({"case_id": case["case_id"], "kind": contract.kind.value, "need_class": need,
                     "template_valid": valid.valid, "template_flags": list(valid.flags)})
        if not valid.valid:
            violations.append(("template_invalid", case["case_id"]))
        for mode in MODES:
            for enabled in (True, False):
                for warm in (True, False):
                    for explicit in (None, "explicit-capable"):
                        edge = RecordingRenderer("edge", warm)
                        capable = RecordingRenderer("capable", True)
                        result = select_wording_policy(contract, settings=settings(mode, enabled), inventory=INVENTORY,
                                                edge_renderer=edge, capable_renderer=capable,
                                                edge_wording_qualified=True, capable_available=True,
                                                resource_admitted=True, explicit_model_id=explicit,
                                                auto_capable_model_id=CAPABLE_MODEL)
                        key = (case["case_id"], mode, enabled, warm, explicit)
                        if not enabled and edge.calls:
                            violations.append(("edge_off_invoked_edge", key))
                        if need in (WordingNeedClass.SIMPLE, WordingNeedClass.EXPLAIN) and not warm and edge.calls:
                            violations.append(("cold_load_for_simple_or_explain", key))
                        if need == WordingNeedClass.SIMPLE and (edge.calls or capable.calls):
                            violations.append(("model_called_for_simple", key))
                        if need != WordingNeedClass.REASONING and capable.calls:
                            violations.append(("capable_called_for_cosmetic_wording", key))
                        if mode == "EDGE_ONLY" and capable.calls:
                            violations.append(("edge_only_called_capable", key))
                        shown = result.options
                        if shown[-1] != ("escape", ESCAPE_LABEL):
                            violations.append(("escape_missing", key))
                        expected_keys = [k for k, _ in make_render_request(contract).slots]
                        if [k for k, _ in shown[:-1]] != expected_keys:
                            violations.append(("presented_slots_mismatch", key))
                        if id_leak(contract, query, result.question + " ".join(l for _, l in shown)):
                            violations.append(("presented_id_leak", key))
    return {"rows": rows, "violations": [list(map(str, v)) for v in violations],
            "need_class_counts": dict(Counter(r["need_class"] for r in rows)),
            "kind_counts": dict(Counter(r["kind"] for r in rows)),
            "template_valid_all": all(r["template_valid"] for r in rows)}


# ---------------------------------------------------------------------------
# Live measurement helpers
# ---------------------------------------------------------------------------

def lms(*args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(["lms", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def loaded_models() -> list[dict]:
    out = lms("ps", "--json")
    try:
        return json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return []


def host_snapshot() -> dict:
    snap: dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        import psutil
        vm = psutil.virtual_memory()
        snap.update(ram_total=vm.total, ram_available=vm.available, cpu_percent=psutil.cpu_percent(interval=0.5))
    except Exception:
        snap["ram"] = "UNAVAILABLE"
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage').CounterSamples | "
                              "Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        snap["gpu_dedicated_bytes"] = int(float(out.stdout.strip())) if out.stdout.strip() else "UNAVAILABLE"
    except Exception:
        snap["gpu_dedicated_bytes"] = "UNAVAILABLE"
    snap["loaded_models"] = [{"identifier": m.get("identifier"), "modelKey": m.get("modelKey"),
                              "sizeBytes": m.get("sizeBytes")} for m in loaded_models()]
    return snap


def load_model(model: str) -> dict:
    before = host_snapshot()
    start = time.perf_counter()
    out = lms("load", model, "--identifier", model, "--ttl", "3600", "-y")
    return {"model": model, "cold_load_ms": (time.perf_counter() - start) * 1000.0, "returncode": out.returncode,
            "stderr_tail": out.stderr[-400:], "before": before, "after": host_snapshot()}


def unload_model(model: str) -> int:
    return lms("unload", model).returncode


def live_no_cold_load_probe(cases: list[dict]) -> dict:
    """With the Edge model NOT loaded, policy-mode EXPLAIN wording must not load it."""
    edge = LMStudioRenderer("edge", EDGE_MODEL)
    state_before = edge.model_state()
    rows = []
    for case in cases:
        _, contract = build_contract(case)
        if classify_need(contract) != WordingNeedClass.EXPLAIN:
            continue
        result = select_wording_policy(contract, settings=settings("HYBRID", True), inventory=INVENTORY,
                                edge_renderer=edge, capable_renderer=None, edge_wording_qualified=True,
                                capable_available=False, resource_admitted=True)
        rows.append({"case_id": case["case_id"], "route": result.route.target.value, "tier": result.tier_used,
                     "edge_invoked": result.edge_invoked})
    state_after = edge.model_state()
    return {"edge_model": EDGE_MODEL, "state_before": state_before, "state_after": state_after,
            "explain_cases": len(rows), "edge_invocations": sum(r["edge_invoked"] for r in rows),
            "passed": state_before != "loaded" and state_after == state_before and not any(r["edge_invoked"] for r in rows),
            "rows": rows}


def run_arm(cases: list[dict], renderer, repeat: int) -> list[dict]:
    rows = []
    for rep in range(repeat):
        for case in cases:
            query, contract = build_contract(case)
            attempt = renderer.render(make_render_request(contract), contract)
            output, flags = validated_output(contract, attempt.raw_text)
            schema_ok = True
            try:
                parsed = json.loads(attempt.raw_text or "")
                schema_ok = isinstance(parsed, dict) and set(parsed) == {"question", "labels"}
            except json.JSONDecodeError:
                schema_ok = False
            rows.append({
                "case_id": case["case_id"], "category": case["category"], "repeat": rep,
                "kind": contract.kind.value, "need_class": classify_need(contract), "arm": renderer.arm,
                "model": getattr(renderer, "model_id", None), "decoding": attempt.decoding,
                "prompt_variant": attempt.prompt_variant, "raw_text": attempt.raw_text, "error": attempt.error,
                "schema_ok": schema_ok, "valid": output is not None, "flags": list(flags),
                "invented_slot": "V-SLOT-UNKNOWN" in flags or "V-EXTRA-OPTION" in flags,
                "omission": "V-SLOT-MISSING" in flags, "unsupported_fact": "V-UNSUPPORTED-FACT" in flags,
                "candidate_id_leak": id_leak(contract, query, attempt.raw_text),
                "presented_question": (output or render_template(contract)).question,
                "presented_labels": dict((output or render_template(contract)).labels),
                "fallback": output is None, "latency_ms": round(attempt.latency_ms, 3),
                "offending_tokens": offending_tokens(contract, attempt.raw_text),
                "function_word_only_reject": bool(output is None and set(flags) == {"V-UNSUPPORTED-FACT"}
                                                  and set(offending_tokens(contract, attempt.raw_text) or ["?"]) <= FUNCTION_WORDS),
                "prompt_tokens": attempt.prompt_tokens, "completion_tokens": attempt.completion_tokens,
                "model_state_before": attempt.model_state_before, "model_state_after": attempt.model_state_after,
            })
    return rows


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))], 1)


def aggregate(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[f"{row['arm']}|{row['decoding']}|{row['prompt_variant']}"].append(row)
        groups[f"{row['arm']}|{row['decoding']}|{row['prompt_variant']}|{row['need_class']}"].append(row)
    out = {}
    for key, items in sorted(groups.items()):
        n = len(items)
        lat = [r["latency_ms"] for r in items if r["error"] is None]
        out[key] = {
            "n": n, "schema_valid_rate": round(sum(r["schema_ok"] for r in items) / n, 4),
            "validator_accept_rate": round(sum(r["valid"] for r in items) / n, 4),
            "fallback_rate": round(sum(r["fallback"] for r in items) / n, 4),
            "invented_slot_rate": round(sum(r["invented_slot"] for r in items) / n, 4),
            "omission_rate": round(sum(r["omission"] for r in items) / n, 4),
            "unsupported_fact_rate": round(sum(r["unsupported_fact"] for r in items) / n, 4),
            "candidate_id_leak_rows": sum(bool(r["candidate_id_leak"]) for r in items),
            "errors": sum(r["error"] is not None for r in items),
            "latency_ms_p50": pct(lat, 0.5), "latency_ms_p95": pct(lat, 0.95),
            "completion_tokens_mean": round(statistics.mean([r["completion_tokens"] for r in items if r["completion_tokens"]]), 1)
            if any(r["completion_tokens"] for r in items) else None,
            "flag_counts": dict(Counter(f for r in items for f in r["flags"])),
            "shadow_function_word_only_reject_rate": round(sum(r.get("function_word_only_reject", False) for r in items) / n, 4),
        }
    return out


# Shadow analysis only (never a gate): common English function words the frozen
# S1 validator's closed allowlist does not contain. A reject whose only
# unsupported tokens are in this list is a likely validator false rejection.
FUNCTION_WORDS = frozenset("""a an the or of is are be it its this that these those with for in on at to from
and your you please option options mean meant refer referring want would like any other between here
listed choose select pick confirm correct right as by was were has have do does""".split())


def offending_tokens(contract, raw_text: str | None) -> list[str] | None:
    from uri_v1.reference_clarification.render_validator import _ALLOW, _tokens
    try:
        data = json.loads(raw_text or "")
        labels = data["labels"] if isinstance(data.get("labels"), dict) else {}
        question = str(data.get("question", ""))
    except (json.JSONDecodeError, AttributeError, KeyError, TypeError):
        return None
    request = make_render_request(contract)
    common = _tokens(request.reference) | _ALLOW | ({str(request.overflow)} if request.overflow else set())
    facts = set().union(*[_tokens(" ".join(v for _, v in f)) for _, f in request.slots]) if request.slots else set()
    words = _tokens(question).union(*[_tokens(str(v)) for v in labels.values()]) if labels else _tokens(question)
    return sorted(words - common - facts)


def blind_sheet(rows: list[dict], cases: list[dict], seed: int, per_class: int) -> tuple[list[dict], dict]:
    """Arena-style blind pairwise comparison (repeat 0): template vs each model arm.

    Set "valid": the model output passed the validator (what a user could see).
    Set "shadow": the model output was rejected only for common function words
    (what a user could see if the validator allowlist were widened).
    """
    rng = random.Random(seed)
    template = {r["case_id"]: r for r in rows if r["arm"] == "template"}
    sheet, key = [], {}
    for arm in ("edge", "capable"):
        for subset in ("valid", "shadow"):
            pool = defaultdict(list)
            for r in rows:
                if r["repeat"] != 0 or r["arm"] != arm or r["decoding"] != "constrained":
                    continue
                if subset == "valid" and not r["valid"]:
                    continue
                if subset == "shadow" and (r["valid"] or not r["function_word_only_reject"]):
                    continue
                pool[r["need_class"]].append(r)
            for need in ("SIMPLE", "EXPLAIN", "REASONING"):
                picks = sorted(pool[need], key=lambda r: (r["case_id"], r["prompt_variant"]))
                seen, unique = set(), []
                for r in picks:
                    if r["case_id"] not in seen:
                        seen.add(r["case_id"])
                        unique.append(r)
                rng.shuffle(unique)
                for r in sorted(unique[:per_class], key=lambda r: r["case_id"]):
                    n = len(sheet) + 1
                    shown_model = ({"question": json.loads(r["raw_text"])["question"],
                                    "options": list(json.loads(r["raw_text"])["labels"].values())}
                                   if subset == "shadow" else
                                   {"question": r["presented_question"], "options": list(r["presented_labels"].values())})
                    shown_template = {"question": template[r["case_id"]]["presented_question"],
                                      "options": list(template[r["case_id"]]["presented_labels"].values())}
                    pair = [("template", shown_template), (arm, shown_model)]
                    rng.shuffle(pair)
                    item = {"item": n, "set": subset, "need_class": need,
                            "reference": next(c for c in cases if c["case_id"] == r["case_id"])["input"]["reference"],
                            "variants": {}}
                    key[str(n)] = {"case_id": r["case_id"], "set": subset, "prompt_variant": r["prompt_variant"]}
                    for letter, (name, shown) in zip("AB", pair):
                        item["variants"][letter] = {**shown, "options": shown["options"] + [ESCAPE_LABEL]}
                        key[str(n)][letter] = name
                    sheet.append(item)
    return sheet, key


def evaluate_gate(gate: dict, gate_sha: str, manifest: dict, det: dict, probe: dict, rows: list[dict]) -> dict:
    cfg = gate["production_config"]
    validator = hashlib.sha256((ROOT / "uri_v1/reference_clarification/render_validator.py").read_bytes()
                               .replace(b"\r\n", b"\n")).hexdigest()
    inputs_ok = {
        "battery": gate["inputs"]["battery_lf_sha256"] == manifest["battery_lf_sha256"],
        "validator": gate["inputs"]["validator_lf_sha256"] == validator,
        "prompt_version": cfg["prompt_version"] == PROMPT_VERSION,
        "need_class_policy": gate["inputs"]["need_class_policy_version"] == NEED_CLASS_POLICY_VERSION,
    }
    battery_cases = {c["case_id"]: c for c in load_battery()[0]["cases"]}
    model_rows = [r for r in rows if r["arm"] != "template"]
    presented_valid = all(validate_render(build_contract(battery_cases[r["case_id"]])[1],
                                          {"question": r["presented_question"], "labels": r["presented_labels"]}).valid
                          for r in rows)
    frozen = {
        "template_valid_on_every_contract": det["template_valid_all"],
        "zero_policy_violations_in_deterministic_grid": not det["violations"],
        "live_no_cold_load_probe_passed": bool(probe.get("passed")),
        "zero_candidate_id_leaks_in_raw_model_output": not any(r["candidate_id_leak"] for r in model_rows),
        "zero_invented_slots_after_validation": not any(r["valid"] and r["invented_slot"] for r in model_rows),
        "presented_output_always_valid": presented_valid,
    }
    tiers = {}
    for need, spec in gate["tier_gates"].items():
        sel = [r for r in rows if r["arm"] == spec["arm"] and r["need_class"] == need
               and r["decoding"] == cfg["decoding"] and r["prompt_variant"] == cfg["prompt_variant"]]
        rule = gate["qualification_rule"]
        lat = [r["latency_ms"] for r in sel if r["error"] is None]
        fb = sum(r["fallback"] for r in sel) / len(sel) if sel else 1.0
        p95 = pct(lat, 0.95)
        errors = sum(r["error"] is not None for r in sel)
        tiers[need] = {"arm": spec["arm"], "rows": len(sel), "fallback_rate": round(fb, 4), "latency_ms_p95": p95,
                       "provider_errors": errors,
                       "qualified": bool(sel) and fb <= rule["max_fallback_rate"] and p95 is not None
                       and p95 <= rule["max_latency_ms_p95"] and errors <= rule["max_provider_errors"]}
    frozen_ok = all(frozen.values()) and all(inputs_ok.values())
    return {"gate_sha256": gate_sha, "inputs_match": inputs_ok, "frozen_required": frozen,
            "frozen_required_passed": frozen_ok, "tiers": tiers,
            "qualified_routes": {"SIMPLE": ["template"],
                                 "EXPLAIN": ["template"] + (["edge"] if tiers.get("EXPLAIN", {}).get("qualified") else []),
                                 "REASONING": ["template"] + (["capable"] if tiers.get("REASONING", {}).get("qualified") else [])},
            "verdict": ("S5_FINAL_FROZEN_REQUIRED_FAILED" if not frozen_ok else "S5_FINAL_REQUALIFIED")}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("deterministic", "exploratory", "final"), required=True)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--out-prefix", default="docs/plans/M33_3_R_S5")
    parser.add_argument("--blind-seed", type=int, default=3303)
    parser.add_argument("--keep-loaded", action="store_true")
    args = parser.parse_args()

    anchors_before = require_anchors()
    battery, manifest = load_battery()
    cases = battery["cases"]
    gate = None
    if args.mode == "final":
        if not GATE_FILE.exists():
            raise SystemExit("final mode requires the frozen threshold gate file")
        gate_bytes = GATE_FILE.read_bytes().replace(b"\r\n", b"\n")
        gate = json.loads(gate_bytes)
        gate_sha = hashlib.sha256(gate_bytes).hexdigest()
    det = deterministic_checks(cases)
    result: dict[str, Any] = {
        "mode": args.mode, "started_at": datetime.now(timezone.utc).isoformat(), "host": platform.platform(),
        "battery": {k: manifest[k] for k in ("schema_version", "case_count", "battery_lf_sha256")},
        "prompt_version": PROMPT_VERSION, "need_class_policy_version": NEED_CLASS_POLICY_VERSION,
        "anchors_before": anchors_before, "deterministic": det,
    }
    rows: list[dict] = []
    if args.mode != "deterministic":
        result["preflight_host"] = host_snapshot()
        if result["preflight_host"]["loaded_models"]:
            raise SystemExit("models already loaded by another owner; refusing to measure (S5/S10 serialization)")
        result["live_no_cold_load_probe"] = live_no_cold_load_probe(cases)
        rows += run_arm(cases, TemplateRenderer(), 1)
        loads = []
        for model, arm in ((EDGE_MODEL, "edge"), (CAPABLE_MODEL, "capable")):
            loads.append(load_model(model))
            for constrained in (True, False):
                for allowlist in (False, True):
                    rows += run_arm(cases, LMStudioRenderer(arm, model, constrained=constrained,
                                                            allowlist_prompt=allowlist), args.repeat)
            if not args.keep_loaded:
                loads[-1]["unload_returncode"] = unload_model(model)
        result["loads"] = loads
        result["postflight_host"] = host_snapshot()
    result["aggregates"] = aggregate(rows) if rows else {}
    if gate is not None:
        result["gate_evaluation"] = evaluate_gate(gate, gate_sha, manifest, det, result["live_no_cold_load_probe"], rows)
    result["anchors_after"] = require_anchors()
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    prefix = ROOT / args.out_prefix
    label = {"deterministic": "DETERMINISTIC", "exploratory": "EXPLORATORY", "final": "FINAL"}[args.mode]
    write_json(Path(f"{prefix}_{label}_AGGREGATES.json"), {k: v for k, v in result.items()})
    if rows:
        write_json(Path(f"{prefix}_{label}_TELEMETRY.json"), rows)
        sheet, key = blind_sheet(rows, cases, args.blind_seed, per_class=4)
        write_json(Path(f"{prefix}_{label}_BLIND_SHEET.json"), sheet)
        write_json(Path(f"{prefix}_{label}_BLIND_KEY.json"), key)
    print(json.dumps({"violations": len(det["violations"]), "need_classes": det["need_class_counts"],
                      "rows": len(rows), "probe": result.get("live_no_cold_load_probe", {}).get("passed"),
                      "gate": result.get("gate_evaluation")}, indent=1))


if __name__ == "__main__":
    main()
