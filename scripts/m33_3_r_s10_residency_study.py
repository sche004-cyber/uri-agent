"""M33.3-R S10 residency study runner (protocol: docs/plans/M33_3_R_S10_RESIDENCY_STUDY_PROTOCOL.md).

Run only in a clean hardware window (no concurrent S5 or other local-model
measurement). URI-owned loads use `uri-lease-` identifiers and the
LeaseOwnershipLedger; URI never unloads an instance it does not own.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.m33_3_r_anchors import require_anchors
from scripts.m33_3_r_s5_qualify import build_contract, host_snapshot, load_battery
from uri_core.core.edge.lease_ownership import LeaseOwnershipLedger, new_uri_instance_id
from uri_core.core.edge.routing_policy import WordingNeedClass
from uri_v1.reference_clarification.render_contracts import make_render_request
from uri_v1.wording.need_class import classify_need
from uri_v1.wording.renderer_port import LMStudioRenderer
from uri_v1.wording.selector import validated_output

EDGE, CAPABLE = "qwen3.5-2b", "qwen3.5-9b"
RAM_FLOOR = int(1.5 * 2**30)
GPU_CEILING = int(15.0 * 2**30)
RUNTIME = "lmstudio"
OUT = ROOT / "docs" / "plans"


class LimitExceeded(RuntimeError):
    pass


def lms(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(["lms", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def instances() -> list[dict]:
    try:
        return json.loads(lms("ps", "--json").stdout or "[]")
    except json.JSONDecodeError:
        return []


def instance_ids() -> list[str]:
    return [m.get("identifier") for m in instances()]


def check_limits(tag: str, log: list) -> dict:
    snap = host_snapshot()
    snap["tag"] = tag
    log.append(snap)
    ram = snap.get("ram_available")
    gpu = snap.get("gpu_dedicated_bytes")
    if isinstance(ram, int) and ram < RAM_FLOOR:
        raise LimitExceeded(f"RAM available {ram} below floor at {tag}")
    if isinstance(gpu, int) and gpu > GPU_CEILING:
        raise LimitExceeded(f"GPU dedicated {gpu} above ceiling at {tag}")
    return snap


def uri_load(ledger: LeaseOwnershipLedger, model: str, ttl: int = 3600) -> tuple[str, float]:
    instance = new_uri_instance_id()
    start = time.perf_counter()
    out = lms("load", model, "--identifier", instance, "--ttl", str(ttl), "-y")
    elapsed = (time.perf_counter() - start) * 1000.0
    if out.returncode != 0:
        raise RuntimeError(f"load failed: {out.stderr[-300:]}")
    ledger.record_acquired(runtime_id=RUNTIME, model_id=model, provider_instance_id=instance)
    return instance, elapsed


def uri_unload(ledger: LeaseOwnershipLedger, instance: str) -> int:
    ledger.require_may_unload(instance)  # never unload a non-owned instance
    code = lms("unload", instance).returncode
    ledger.record_released(instance)
    return code


def explain_contracts() -> list:
    battery, _ = load_battery()
    out = []
    for case in battery["cases"]:
        _, contract = build_contract(case)
        if classify_need(contract) == WordingNeedClass.EXPLAIN:
            out.append((case["case_id"], contract))
    return out


def warm_requests(instance: str, contracts: list, n: int) -> list[dict]:
    renderer = LMStudioRenderer("study", instance, allow_cold_load=True)  # instance verified loaded via lms ps
    rows = []
    for i in range(n):
        case_id, contract = contracts[i % len(contracts)]
        if instance not in instance_ids():
            raise RuntimeError("instance no longer loaded")
        attempt = renderer.render(make_render_request(contract), contract)
        output, flags = validated_output(contract, attempt.raw_text)
        rows.append({"case_id": case_id, "latency_ms": round(attempt.latency_ms, 1), "error": attempt.error,
                     "completion_tokens": attempt.completion_tokens, "valid": output is not None})
    return rows


def summary(rows: list[dict]) -> dict:
    lat = sorted(r["latency_ms"] for r in rows if r["error"] is None)
    if not lat:
        return {"n": len(rows), "errors": len(rows)}
    q = lambda p: lat[min(len(lat) - 1, int(round(p * (len(lat) - 1))))]
    return {"n": len(rows), "errors": sum(r["error"] is not None for r in rows), "p50_ms": q(0.5),
            "p95_ms": q(0.95), "mean_ms": round(statistics.mean(lat), 1),
            "valid_rate": round(sum(r["valid"] for r in rows) / len(rows), 3)}


def main() -> None:
    result: dict[str, Any] = {"started_at": datetime.now(timezone.utc).isoformat(), "anchors_before": require_anchors(),
                              "configs": {}, "snapshots": [], "limits": {"ram_floor": RAM_FLOOR, "gpu_ceiling": GPU_CEILING}}
    snaps = result["snapshots"]
    pre = check_limits("preflight", snaps)
    if pre["loaded_models"]:
        raise SystemExit("preflight: models already loaded by another owner; refusing to run (no disruption)")
    ledger = LeaseOwnershipLedger(owner_id="m33.3-r-s10-study")
    contracts = explain_contracts()
    external = None
    try:
        # R1 / R2: single-model residency
        for tag, model in (("R1_edge_resident", EDGE), ("R2_capable_resident", CAPABLE)):
            inst, load_ms = uri_load(ledger, model)
            snap = check_limits(f"{tag}_loaded", snaps)
            rows = warm_requests(inst, contracts, 20)
            result["configs"][tag] = {"model": model, "instance": inst, "cold_load_ms": round(load_ms, 1),
                                      "warm": summary(rows), "rows": rows,
                                      "gpu_dedicated_bytes_loaded": snap.get("gpu_dedicated_bytes"),
                                      "ram_available_loaded": snap.get("ram_available")}
            uri_unload(ledger, inst)
            check_limits(f"{tag}_unloaded", snaps)
        # R3: co-residency
        e_inst, e_ms = uri_load(ledger, EDGE)
        c_inst, c_ms = uri_load(ledger, CAPABLE)
        snap = check_limits("R3_coresident_loaded", snaps)
        e_rows, c_rows = [], []
        for i in range(20):
            e_rows += warm_requests(e_inst, contracts[i:] + contracts[:i], 1)
            c_rows += warm_requests(c_inst, contracts[i:] + contracts[:i], 1)
        result["configs"]["R3_coresident"] = {"edge": summary(e_rows), "capable": summary(c_rows),
                                              "load_ms": {"edge": round(e_ms, 1), "capable": round(c_ms, 1)},
                                              "gpu_dedicated_bytes_loaded": snap.get("gpu_dedicated_bytes"),
                                              "ram_available_loaded": snap.get("ram_available"),
                                              "rows": {"edge": e_rows, "capable": c_rows}}
        uri_unload(ledger, e_inst)
        uri_unload(ledger, c_inst)
        check_limits("R3_unloaded", snaps)
        # R4: on-demand (load + first request)
        r4 = {}
        for model in (EDGE, CAPABLE):
            start = time.perf_counter()
            inst, load_ms = uri_load(ledger, model)
            first = warm_requests(inst, contracts, 1)[0]
            r4[model] = {"load_ms": round(load_ms, 1), "first_request_ms": first["latency_ms"],
                         "demand_total_ms": round((time.perf_counter() - start) * 1000.0, 1)}
            uri_unload(ledger, inst)
        result["configs"]["R4_on_demand"] = r4
        # R5: provider-native idle TTL
        inst, _ = uri_load(ledger, EDGE, ttl=20)
        loaded_at = time.perf_counter()
        warm_requests(inst, contracts, 1)
        idle_start = time.perf_counter()
        unloaded_after = None
        while time.perf_counter() - idle_start < 60:
            time.sleep(5)
            if inst not in instance_ids():
                unloaded_after = round(time.perf_counter() - idle_start, 1)
                break
        if unloaded_after is None:
            uri_unload(ledger, inst)
        else:
            ledger.record_released(inst)  # the provider released it by TTL
        result["configs"]["R5_idle_ttl"] = {"ttl_s": 20, "unloaded_after_idle_s": unloaded_after,
                                            "provider_released": unloaded_after is not None}
        # R6: external lease respect
        external = "external-sim-" + EDGE
        lms("load", EDGE, "--identifier", external, "-y")
        mine, _ = uri_load(ledger, CAPABLE)
        observed = [(m.get("identifier"), m.get("modelKey")) for m in instances()]
        classes = {l.provider_instance_id: l.owner_kind for l in ledger.classify(RUNTIME, observed)}
        refused = not ledger.may_unload(external)
        # URI cleanup: unload every instance URI owns, nothing else.
        for lease in list(ledger.active()):
            uri_unload(ledger, lease.provider_instance_id)
        still_loaded = external in instance_ids()
        result["configs"]["R6_external_respect"] = {"classification": classes, "uri_refused_external": refused,
                                                    "external_still_loaded_after_uri_cleanup": still_loaded,
                                                    "passed": refused and still_loaded and classes.get(external) == "EXTERNAL"
                                                    and classes.get(mine) == "URI"}
    except LimitExceeded as exc:
        result["stopped_by_limit"] = str(exc)
    finally:
        for lease in list(ledger.active()):
            try:
                uri_unload(ledger, lease.provider_instance_id)
            except Exception as exc:  # recorded, never masks the result
                result.setdefault("cleanup_errors", []).append(str(exc))
        if external and external in instance_ids():
            # The runner itself created this simulated external load; release it last and record it.
            result["simulated_external_release_returncode"] = lms("unload", external).returncode
        check_limits("postflight", snaps)
    result["anchors_after"] = require_anchors()
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    rows_free = json.loads(json.dumps(result))
    for cfg in rows_free["configs"].values():
        cfg.pop("rows", None)
    (OUT / "M33_3_R_S10_RESIDENCY_TELEMETRY.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    (OUT / "M33_3_R_S10_RESIDENCY_AGGREGATES.json").write_text(json.dumps(rows_free, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in rows_free["configs"].items()}, indent=1)[:4000])


if __name__ == "__main__":
    main()
