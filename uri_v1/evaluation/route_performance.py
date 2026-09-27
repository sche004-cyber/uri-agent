"""Per-user route-performance store and qualified-route preference (M33.3-R S8).

Plan B §11-12, M33.2 amendment G3:
- qualification sets eligibility; learning sets preference among already
  qualified, eligible routes only; it never qualifies a route, changes a
  calibration profile or threshold, or crosses the Edge/Capable boundary;
- a separate per-user store (not ExperienceStore), structured evidence only;
- durable learning defaults ON with OFF, inspect, delete and reset controls;
- evidence is invalidated when the route version changes; negative feedback
  weighs more; evidence decays; one item never permanently changes routing.
Offline use only: nothing here is consulted by a production request path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import threading
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from uri_v1.user_storage import locked_append as _locked_append, user_scoped_path


STORE_SCHEMA_VERSION = "m33.3-r.s8.route-performance.v1"
_IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/|\-@]{0,255}$")
_OUTCOMES = frozenset({"SUCCESS", "FALLBACK", "FAILURE", "CORRECTED"})
_FEEDBACK = frozenset({"positive", "negative", "none"})
_lock = threading.RLock()


@dataclass(frozen=True)
class RouteKey:
    task_class: str
    route_target: str        # DETERMINISTIC | EDGE | CAPABLE
    model_id: str            # "template" for the deterministic tier
    route_version: str       # policy/prompt/model/qualification version; a change invalidates evidence

    def __post_init__(self) -> None:
        for name in ("task_class", "route_target", "model_id", "route_version"):
            if not _IDENT.match(getattr(self, name) or ""):
                raise ValueError(f"{name} must be a bounded identifier")

    @property
    def route_id(self) -> str:
        return f"{self.task_class}|{self.route_target}|{self.model_id}"


@dataclass(frozen=True)
class RoutePerformanceRecord:
    route: RouteKey
    outcome: str
    feedback: str
    latency_ms: float
    timestamp: str
    trace_id: Optional[str] = None
    schema_version: str = STORE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.outcome not in _OUTCOMES or self.feedback not in _FEEDBACK:
            raise ValueError("closed-vocabulary field has an unknown value")
        if not isinstance(self.latency_ms, (int, float)) or self.latency_ms < 0 or math.isnan(self.latency_ms):
            raise ValueError("latency_ms must be a non-negative number")
        datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))

    def to_json(self) -> dict:
        data = asdict(self)
        return data

    @classmethod
    def from_json(cls, data: Mapping) -> "RoutePerformanceRecord":
        allowed = {"route", "outcome", "feedback", "latency_ms", "timestamp", "trace_id", "schema_version"}
        if set(data) - allowed or data.get("schema_version") != STORE_SCHEMA_VERSION:
            raise ValueError("unknown fields or schema")
        return cls(RouteKey(**data["route"]), data["outcome"], data["feedback"], data["latency_ms"],
                   data["timestamp"], data.get("trace_id"))


class RoutePerformanceStore:
    def __init__(self, user_id: str, *, root: str = "uri_workspace/users") -> None:
        self._path = user_scoped_path(user_id, os.path.join("route_performance", "records.jsonl"), root=root)
        self._settings = user_scoped_path(user_id, "route_performance_settings.json", root=root)

    def enabled(self) -> bool:
        try:
            raw = json.loads(Path(self._settings).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return True  # durable learning defaults ON
        except (OSError, json.JSONDecodeError):
            return False
        return raw.get("enabled") is True and raw.get("schema_version") == STORE_SCHEMA_VERSION

    def set_enabled(self, enabled: bool) -> None:
        if type(enabled) is not bool:
            raise ValueError("enabled must be boolean")
        os.makedirs(os.path.dirname(self._settings), exist_ok=True)
        tmp = self._settings + ".tmp"
        Path(tmp).write_text(json.dumps({"schema_version": STORE_SCHEMA_VERSION, "enabled": enabled}), encoding="utf-8")
        os.replace(tmp, self._settings)

    def record(self, record: RoutePerformanceRecord) -> bool:
        if not isinstance(record, RoutePerformanceRecord):
            raise ValueError("only validated records are stored")
        if not self.enabled():
            return False
        with _lock:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with _locked_append(self._path) as stream:
                stream.write((json.dumps(record.to_json(), sort_keys=True) + "\n").encode("utf-8"))
        return True

    def records(self) -> List[RoutePerformanceRecord]:
        out: List[RoutePerformanceRecord] = []
        try:
            lines = Path(self._path).read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return out
        for line in lines:
            try:
                out.append(RoutePerformanceRecord.from_json(json.loads(line)))
            except (ValueError, TypeError, KeyError):
                continue
        return out

    def reset(self) -> None:
        with _lock:
            try:
                os.remove(self._path)
            except FileNotFoundError:
                pass


@dataclass(frozen=True)
class PreferenceConfig:
    half_life_days: float = 14.0
    negative_weight: float = 3.0
    min_evidence: float = 5.0          # below this, keep the fixed (default) route
    margin: float = 0.10               # a learned route must beat the default by this reward margin
    latency_penalty_per_s: float = 0.0  # set from the frozen S5 gate; 0 = latency ignored


def record_reward(record: RoutePerformanceRecord, config: PreferenceConfig) -> Tuple[float, float]:
    """Return (reward in [0,1] before latency penalty, weight)."""
    base = {"SUCCESS": 1.0, "FALLBACK": 0.3, "FAILURE": 0.0, "CORRECTED": 0.0}[record.outcome]
    if record.feedback == "positive":
        base = min(1.0, base + 0.2)
    reward = max(0.0, base - config.latency_penalty_per_s * record.latency_ms / 1000.0)
    weight = config.negative_weight if (record.feedback == "negative" or record.outcome == "CORRECTED") else 1.0
    return reward, weight


def choose_route(task_class: str, default: RouteKey, eligible: Sequence[RouteKey],
                 records: Iterable[RoutePerformanceRecord], *, now: datetime,
                 config: PreferenceConfig = PreferenceConfig(), learning_enabled: bool = True) -> Tuple[RouteKey, dict]:
    """Pure preference among qualified, eligible routes. Never returns a route outside `eligible`.

    `eligible` must already be the intersection of qualification and router
    eligibility for this request; `default` is the fixed-routing choice.
    """
    eligible_ids = {r for r in eligible if r.task_class == task_class}
    if default not in eligible_ids:
        raise ValueError("the fixed default route must itself be qualified and eligible")
    explain = {"learning_enabled": learning_enabled, "scores": {}}
    if not learning_enabled:
        return default, {**explain, "reason": "learning_off"}
    stats: Dict[RouteKey, List[float]] = {r: [0.0, 0.0] for r in eligible_ids}
    for rec in records:
        if rec.route not in stats:
            continue  # unqualified, ineligible, other task class, or stale version: invalidated
        age_days = max(0.0, (now - datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))).total_seconds() / 86400)
        decay = 0.5 ** (age_days / config.half_life_days)
        reward, weight = record_reward(rec, config)
        stats[rec.route][0] += reward * weight * decay
        stats[rec.route][1] += weight * decay
    scores = {r: (s / w if w else None, w) for r, (s, w) in stats.items()}
    explain["scores"] = {r.route_id: {"mean_reward": None if m is None else round(m, 4), "evidence": round(w, 3)}
                         for r, (m, w) in scores.items()}
    default_mean, default_w = scores[default]
    best, best_mean = default, default_mean
    for route, (mean, weight) in sorted(scores.items(), key=lambda kv: kv[0].route_id):
        if route == default or mean is None or weight < config.min_evidence:
            continue
        baseline = default_mean if default_mean is not None and default_w >= config.min_evidence else None
        if baseline is not None and mean >= baseline + config.margin and (best_mean is None or mean > best_mean):
            best, best_mean = route, mean
    return best, {**explain, "reason": "learned_preference" if best != default else "fixed_default"}
