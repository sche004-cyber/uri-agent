"""M33.3-R S8 offline route-performance replay (fixed routing vs learned preference).

Inputs (all frozen before this runs):
- S5 FINAL telemetry and aggregates (per case x route outcomes, qualified routes);
- the frozen S5 threshold gate (qualified routes, latency penalty).

Method:
- Ground truth is full-information: S5 measured every route on every case, so
  each policy's true value is computed exactly.
- A logged stream is simulated with a uniform-random logging policy over the
  qualified routes of each task class (known propensity 1/k), time-ordered.
- The learned policy (`choose_route`) is evaluated with the replay method
  (Li et al. 2011: accept an event only when the learner's choice equals the
  logged action), and its final policy is also estimated by IPS and SNIPS and
  compared with the exact ground truth to validate the estimators.
- Guard checks: learning OFF and reset fall back to fixed routing; a route
  version bump invalidates evidence; an unqualified route with perfect logged
  records is never chosen. Offline only: nothing is written to any user store
  outside a temporary directory, and no production path is touched.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.m33_3_r_anchors import require_anchors
from uri_v1.evaluation.route_performance import (PreferenceConfig, RouteKey, RoutePerformanceRecord,
                                                 RoutePerformanceStore, choose_route, record_reward)

GATE = ROOT / "fixtures" / "m33_3_s5" / "threshold_gate.json"
# Current closing-audit qualification; prior candidate evidence stays immutable.
AUDIT_EVIDENCE = ROOT / "docs" / "plans" / "M33_3_R_CLOSING_AUDIT_EVIDENCE"
FINAL_TELEMETRY = AUDIT_EVIDENCE / "S5_FINAL_TELEMETRY.json"
FINAL_AGGREGATES = AUDIT_EVIDENCE / "S5_FINAL_AGGREGATES.json"
OUT = AUDIT_EVIDENCE / "S8_REPLAY_RESULTS.json"
T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
ARM_TARGET = {"template": ("DETERMINISTIC", "template"), "edge": ("EDGE", None), "capable": ("CAPABLE", None)}


def route_key(task_class: str, arm: str, model: str | None, version: str) -> RouteKey:
    target, fixed_model = ARM_TARGET[arm]
    return RouteKey(task_class, target, fixed_model or model, version)


def load_inputs():
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    rows = json.loads(FINAL_TELEMETRY.read_text(encoding="utf-8"))
    aggregates = json.loads(FINAL_AGGREGATES.read_text(encoding="utf-8"))
    gate_sha = hashlib.sha256(GATE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if aggregates.get("gate_evaluation", {}).get("gate_sha256") != gate_sha:
        raise ValueError("S5 evidence does not match the current frozen gate; requalify before replay")
    if aggregates.get("prompt_version") != gate["production_config"]["prompt_version"]:
        raise ValueError("S5 evidence prompt version mismatch")
    return gate, rows, aggregates


def outcome_table(rows, gate):
    """(case_id, arm) -> list of (outcome, latency) under the frozen production configuration."""
    cfg = gate["production_config"]
    table = defaultdict(list)
    classes = {}
    models = {}
    for r in rows:
        if r["arm"] != "template" and (r["decoding"] != cfg["decoding"] or r["prompt_variant"] != cfg["prompt_variant"]):
            continue
        outcome = "SUCCESS" if r["valid"] else ("FAILURE" if r["error"] else "FALLBACK")
        table[(r["case_id"], r["arm"])].append((outcome, r["latency_ms"]))
        classes[r["case_id"]] = r["need_class"]
        if r["model"]:
            models[r["arm"]] = r["model"]
    return table, classes, models


def value(policy, cases, table, config):
    rewards = []
    for cid in cases:
        arm = policy(cid)
        samples = table[(cid, arm)]
        rewards.append(statistics.mean(record_reward(RoutePerformanceRecord(
            RouteKey("x", "EDGE", "m", "v"), o, "none", lat, T0.isoformat()), config)[0] for o, lat in samples))
    return statistics.mean(rewards)


def method_validation(seed: int, events: int = 4000) -> dict:
    """METHOD VALIDATION ONLY (synthetic arms with known success rates, not URI routes).

    Proves the replay learner and the IPS/SNIPS estimators behave correctly when
    more than one qualified route exists; it is not route evidence.
    """
    rng = random.Random(seed)
    arms = {"A": (RouteKey("SYNTH", "DETERMINISTIC", "synthetic-a", "mv1"), 0.6),
            "B": (RouteKey("SYNTH", "EDGE", "synthetic-b", "mv1"), 0.9)}
    eligible = [k for k, _ in arms.values()]
    default = arms["A"][0]
    config = PreferenceConfig()
    records, logged = [], []
    # Independent training prefix: validate preference separately from held-out
    # IPS/SNIPS and replay. This is not evidence that a fixed, unseeded policy
    # explores other routes (the actual one-route study cannot test that).
    training_events = 1000
    for i in range(training_events):
        name = rng.choice(sorted(arms))
        key, p = arms[name]
        outcome = "SUCCESS" if rng.random() < p else "FAILURE"
        records.append(RoutePerformanceRecord(key, outcome, "none", 10.0,
                                              (T0 + timedelta(minutes=i)).isoformat()))
    chosen, _ = choose_route("SYNTH", default, eligible, records, now=T0 + timedelta(minutes=training_events), config=config)
    target = "B" if chosen == arms["B"][0] else "A"
    for _ in range(events):
        name = rng.choice(sorted(arms))
        logged.append((name, "SUCCESS" if rng.random() < arms[name][1] else "FAILURE"))
    matched = [o == "SUCCESS" for n, o in logged if n == target]
    ips = sum(2.0 * (o == "SUCCESS") for n, o in logged if n == target) / len(logged)
    snips = sum(matched) / len(matched) if matched else None
    return {"label": "METHOD_VALIDATION_SYNTHETIC_NOT_ROUTE_EVIDENCE", "true_value_B": 0.9,
            "ips_estimate_B": round(ips, 4), "abs_error": round(abs(ips - 0.9), 4),
            "training_events": training_events, "held_out_events": events,
            "snips_estimate": None if snips is None else round(snips, 4),
            "replay_accepted": len(matched), "replay_mean_reward": snips,
            "limitation": "Seeded preference plus held-out fixed-policy evaluation; no unseeded exploration claim.",
            "learner_chose": "B" if chosen == arms["B"][0] else "A",
            "passed": chosen == arms["B"][0] and abs(ips - 0.9) < 0.05
            and snips is not None and abs(snips - 0.9) < 0.05}


def main() -> None:
    global FINAL_TELEMETRY, FINAL_AGGREGATES, OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=808)
    parser.add_argument("--s5-prefix", help="Prefix of the current qualified S5 evidence (without _FINAL suffix)")
    parser.add_argument("--out", help="Write a new evidence file without replacing historical results")
    args = parser.parse_args()
    if args.s5_prefix:
        FINAL_TELEMETRY = ROOT / (args.s5_prefix + "_FINAL_TELEMETRY.json")
        FINAL_AGGREGATES = ROOT / (args.s5_prefix + "_FINAL_AGGREGATES.json")
    if args.out:
        OUT = ROOT / args.out
    anchors_before = require_anchors()
    gate, rows, aggregates = load_inputs()
    evaluation = aggregates["gate_evaluation"]
    if evaluation["verdict"] != "S5_FINAL_REQUALIFIED":
        raise SystemExit("S8 requires a requalified S5 final run")
    qualified = evaluation["qualified_routes"]      # {task_class: [arm, ...]} from the frozen gate verdict
    fixed = {"SIMPLE": "template",
             "EXPLAIN": "edge" if "edge" in qualified["EXPLAIN"] else "template",
             "REASONING": "capable" if "capable" in qualified["REASONING"] else "template"}
    s8 = gate["s8_parameters"]
    version = s8["route_version"]
    config = PreferenceConfig(latency_penalty_per_s=s8["latency_penalty_per_s"])
    table, classes, models = outcome_table(rows, gate)
    cases = sorted(classes)
    rng = random.Random(args.seed)

    def key(cid_class, arm, ver=version):
        return route_key(cid_class, arm, models.get(arm), ver)

    eligible = {tc: [key(tc, a) for a in arms] for tc, arms in qualified.items()}
    arm_of = {key(tc, a): a for tc, arms in qualified.items() for a in arms}

    # Exact (full-information) values.
    fixed_value = value(lambda c: fixed[classes[c]], cases, table, config)
    oracle_arm = {c: max(qualified[classes[c]], key=lambda a: value(lambda _c: a, [c], table, config)) for c in cases}
    oracle_value = value(lambda c: oracle_arm[c], cases, table, config)

    # Logged stream: uniform logging over qualified routes.
    logged = []
    for i in range(args.events):
        cid = rng.choice(cases)
        tc = classes[cid]
        arm = rng.choice(qualified[tc])
        outcome, latency = rng.choice(table[(cid, arm)])
        logged.append({"t": T0 + timedelta(minutes=i), "case_id": cid, "task_class": tc, "arm": arm,
                       "propensity": 1 / len(qualified[tc]), "outcome": outcome, "latency": latency})

    # Replay evaluation of the learner.
    with tempfile.TemporaryDirectory() as tmp:
        store = RoutePerformanceStore(str(uuid.UUID(int=880)), root=tmp)
        accepted, rewards, choices = 0, [], defaultdict(int)
        for ev in logged:
            tc = ev["task_class"]
            chosen, _ = choose_route(tc, key(tc, fixed[tc]), eligible[tc], store.records(), now=ev["t"], config=config)
            choices[(tc, arm_of[chosen])] += 1
            if arm_of[chosen] != ev["arm"]:
                continue
            accepted += 1
            rec = RoutePerformanceRecord(chosen, ev["outcome"], "none", ev["latency"], ev["t"].isoformat())
            rewards.append(record_reward(rec, config)[0])
            store.record(rec)
        final_policy = {tc: arm_of[choose_route(tc, key(tc, fixed[tc]), eligible[tc], store.records(),
                                                now=logged[-1]["t"], config=config)[0]] for tc in qualified}
        learned_exact = value(lambda c: final_policy[classes[c]], cases, table, config)
        # IPS / SNIPS estimates of the final learned policy from the logged stream.
        w = [(1.0 / ev["propensity"]) if final_policy[ev["task_class"]] == ev["arm"] else 0.0 for ev in logged]
        r = [record_reward(RoutePerformanceRecord(key(ev["task_class"], ev["arm"]), ev["outcome"], "none",
                                                  ev["latency"], ev["t"].isoformat()), config)[0] for ev in logged]
        ips = sum(wi * ri for wi, ri in zip(w, r)) / len(logged)
        snips = sum(wi * ri for wi, ri in zip(w, r)) / sum(w) if sum(w) else None

        # Guard checks.
        guards = {}
        guards["off_uses_fixed"] = all(choose_route(tc, key(tc, fixed[tc]), eligible[tc], store.records(),
                                                    now=logged[-1]["t"], learning_enabled=False)[0] == key(tc, fixed[tc])
                                       for tc in qualified)
        store.set_enabled(False)
        before = len(store.records())
        store.record(RoutePerformanceRecord(key(cases and classes[cases[0]], fixed[classes[cases[0]]]), "SUCCESS",
                                            "none", 1.0, T0.isoformat()))
        guards["off_writes_nothing"] = len(store.records()) == before
        store.set_enabled(True)
        bumped = {tc: [key(tc, a, version + ".bump") for a in arms] for tc, arms in qualified.items()}
        guards["version_bump_invalidates"] = all(
            choose_route(tc, key(tc, fixed[tc], version + ".bump"), bumped[tc], store.records(),
                         now=logged[-1]["t"], config=config)[0] == key(tc, fixed[tc], version + ".bump")
            for tc in qualified)
        fake = RouteKey(next(iter(qualified)), "EDGE", "unqualified-model", version)
        perfect = [RoutePerformanceRecord(fake, "SUCCESS", "positive", 1.0, T0.isoformat())] * 500
        tc0 = next(iter(qualified))
        guards["unqualified_never_chosen"] = choose_route(tc0, key(tc0, fixed[tc0]), eligible[tc0],
                                                          list(store.records()) + perfect, now=logged[-1]["t"],
                                                          config=config)[0] != fake
        store.reset()
        guards["reset_returns_fixed"] = all(choose_route(tc, key(tc, fixed[tc]), eligible[tc], store.records(),
                                                         now=logged[-1]["t"], config=config)[0] == key(tc, fixed[tc])
                                            for tc in qualified)

    result = {
        "anchors_before": anchors_before, "events": args.events, "seed": args.seed, "route_version": version,
        "qualified_routes": qualified, "fixed_routing": fixed, "config": config.__dict__,
        "exact_values": {"fixed": round(fixed_value, 4), "learned_final": round(learned_exact, 4),
                         "per_case_oracle": round(oracle_value, 4)},
        "learned_final_policy": final_policy,
        "replay": {"accepted_events": accepted, "mean_reward": round(statistics.mean(rewards), 4) if rewards else None},
        "estimators": {"ips": round(ips, 4), "snips": None if snips is None else round(snips, 4),
                       "abs_error_ips": round(abs(ips - learned_exact), 4),
                       "abs_error_snips": None if snips is None else round(abs(snips - learned_exact), 4)},
        "choice_counts": {f"{k[0]}|{k[1]}": v for k, v in sorted(choices.items())},
        "guards": guards, "guards_passed": all(guards.values()),
        "method_validation": method_validation(args.seed),
        "anchors_after": require_anchors(),
    }
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("exact_values", "learned_final_policy", "replay", "estimators",
                                            "guards", "guards_passed", "method_validation")}, indent=1))


if __name__ == "__main__":
    main()
