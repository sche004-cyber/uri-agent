"""Reproducible Edge qualification harness with no egress or host execution."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Sequence

import psutil

try:  # Optional observability only; never required to run a benchmark.
    import pynvml  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - availability is environment-specific.
    pynvml = None

try:  # Optional observability only; URI does not add a torch dependency here.
    import torch  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - availability is environment-specific.
    torch = None


VALID_SCORE_SEMANTICS = frozenset(
    {"probability", "calibrated_confidence", "raw_logit_derived", "none"}
)
CANONICAL_TIERS = frozenset(
    {"deterministic", "reflex", "language-only", "bounded-reasoning", "escalate"}
)
_PROBABILITY_SEMANTICS = frozenset({"probability", "calibrated_confidence"})
_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class BenchmarkCandidate:
    candidate_id: str
    provider: str
    score_semantics: Optional[str]
    licence: str
    local_only: bool = True
    invoke: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    load: Optional[Callable[[], None]] = None
    runtime_status: str = "available"
    runtime_detail: Optional[str] = None


@dataclass(frozen=True)
class BenchmarkResult:
    candidate_id: str
    platform: str
    runtime_status: str
    runtime_detail: Optional[str]
    item_count: int
    correctness: float
    ece: Optional[float]
    max_calibration_error: Optional[float]
    nll: Optional[float]
    p50_ms: Any
    p95_ms: Any
    reflex_accuracy: Optional[float]
    bounded_reasoning_accuracy: Optional[float]
    language_rubric_score: Optional[float]
    escalation_rate: Optional[float]
    false_escalation_rate: Optional[float]
    outcome_counts: Dict[str, int]
    resource: Dict[str, Any]
    safety: str
    qualification: str
    field_precision: Optional[float] = None
    field_recall: Optional[float] = None
    field_f1: Optional[float] = None
    vqa_score: Optional[float] = None
    wer: Optional[float] = None
    cer: Optional[float] = None
    transcript_confidence: Optional[float] = None


def _percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1)]


def _is_probability(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _metrics(
    rows: Iterable[Dict[str, Any]], *, bin_count: int = 10
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Return standard confidence-binned ECE/MCE and per-sample NLL."""

    if bin_count <= 0:
        raise ValueError("bin_count must be positive")
    scored = [
        (float(row["score"]), int(bool(row["correct"])))
        for row in rows
        if _is_probability(row.get("score"))
    ]
    if not scored:
        return None, None, None

    bins: list[list[tuple[float, int]]] = [[] for _ in range(bin_count)]
    for confidence, label in scored:
        index = min(int(confidence * bin_count), bin_count - 1)
        bins[index].append((confidence, label))

    errors: list[tuple[int, float]] = []
    for entries in bins:
        if not entries:
            continue
        accuracy = sum(label for _, label in entries) / len(entries)
        mean_confidence = sum(confidence for confidence, _ in entries) / len(entries)
        errors.append((len(entries), abs(accuracy - mean_confidence)))

    sample_count = len(scored)
    ece = sum(size / sample_count * error for size, error in errors)
    mce = max(error for _, error in errors)
    epsilon = 1e-9
    nll = -sum(
        label * math.log(max(epsilon, confidence))
        + (1 - label) * math.log(max(epsilon, 1.0 - confidence))
        for confidence, label in scored
    ) / sample_count
    return ece, mce, nll


def _rss_mb(process: psutil.Process) -> Any:
    try:
        return process.memory_info().rss / (1024 * 1024)
    except (psutil.Error, OSError):
        return _UNAVAILABLE


def _delta(after: Any, before: Any) -> Any:
    if isinstance(after, (int, float)) and isinstance(before, (int, float)):
        return after - before
    return _UNAVAILABLE


def _gpu_resource() -> Dict[str, Any]:
    """Read GPU/VRAM only when an optional local library supports it."""

    if pynvml is not None:
        try:
            pynvml.nvmlInit()
            devices = []
            for index in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
                devices.append(
                    {
                        "name": str(name),
                        "vram_used_mb": memory.used / (1024 * 1024),
                        "vram_total_mb": memory.total / (1024 * 1024),
                    }
                )
            return {"gpu": devices or _UNAVAILABLE, "vram_mb": devices or _UNAVAILABLE}
        except Exception:  # pragma: no cover - hardware/driver-specific.
            pass
        finally:  # pragma: no branch - shutdown is best effort.
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

    if torch is not None:
        try:
            if torch.cuda.is_available():
                devices = []
                for index in range(torch.cuda.device_count()):
                    devices.append(
                        {
                            "name": torch.cuda.get_device_name(index),
                            "vram_used_mb": torch.cuda.memory_allocated(index)
                            / (1024 * 1024),
                            "vram_total_mb": torch.cuda.get_device_properties(index).total_memory
                            / (1024 * 1024),
                        }
                    )
                return {"gpu": devices, "vram_mb": devices}
        except Exception:  # pragma: no cover - hardware/driver-specific.
            pass
    return {"gpu": _UNAVAILABLE, "vram_mb": _UNAVAILABLE}


def _is_escalation(output: Dict[str, Any]) -> bool:
    return bool(
        output.get("escalated") is True
        or output.get("status") == "escalated"
        or output.get("answer") == "escalate"
    )


def _language_rubric(item: Dict[str, Any], output: Dict[str, Any]) -> float:
    rubric = item.get("rubric") or {}
    answer = str(output.get("answer", "")).casefold()
    required = [str(value).casefold() for value in rubric.get("required_phrases", ())]
    forbidden = [str(value).casefold() for value in rubric.get("forbidden_phrases", ())]
    checks = [phrase in answer for phrase in required]
    checks.extend(phrase not in answer for phrase in forbidden)
    if not checks:
        return float(output.get("answer") == item.get("expected"))
    return sum(checks) / len(checks)


def _budget_satisfied(item: Dict[str, Any], output: Dict[str, Any]) -> bool:
    budget = item.get("budget") or {}
    for used_key, limit_key in (("steps_used", "max_steps"), ("tokens_used", "max_tokens")):
        limit = budget.get(limit_key)
        used = output.get(used_key)
        if limit is not None and (
            not isinstance(used, int) or isinstance(used, bool) or used < 0 or used > limit
        ):
            return False
    return True


def _accuracy(rows: Sequence[Dict[str, Any]], tier: str) -> Optional[float]:
    selected = [row for row in rows if row["tier"] == tier]
    if not selected:
        return None
    return sum(bool(row["correct"]) for row in selected) / len(selected)


def _mean_metric(rows: Sequence[Dict[str, Any]], key: str) -> Optional[float]:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return sum(values) / len(values) if values else None


def _perception_scores(
    item: Dict[str, Any], output: Dict[str, Any]
) -> Dict[str, Optional[float]]:
    metrics: Dict[str, Optional[float]] = {
        "field_precision": None,
        "field_recall": None,
        "field_f1": None,
        "vqa_score": None,
        "wer": None,
        "cer": None,
        "transcript_confidence": None,
    }
    if "expected_transcript" in item:
        from .speech import character_error_rate, word_error_rate

        reference = str(item.get("expected_transcript", ""))
        hypothesis = str(output.get("transcript", output.get("answer", "")))
        metrics["wer"] = word_error_rate(reference, hypothesis)
        metrics["cer"] = character_error_rate(reference, hypothesis)
        confidence = output.get("transcript_confidence")
        if _is_probability(confidence):
            metrics["transcript_confidence"] = float(confidence)
    elif item.get("category") == "field_extraction":
        from .vision import field_f1_score

        expected = item.get("expected")
        predicted = output.get("fields", output.get("answer"))
        if isinstance(expected, dict) and isinstance(predicted, dict):
            precision, recall, f1 = field_f1_score(expected, predicted)
        else:
            precision, recall, f1 = 0.0, 0.0, 0.0
        metrics.update(
            field_precision=precision, field_recall=recall, field_f1=f1
        )
    elif "image_ref" in item:
        from .vision import vqa_exact_match

        metrics["vqa_score"] = vqa_exact_match(
            str(item.get("expected", "")), str(output.get("answer", ""))
        )
    return metrics


def _resource_snapshot(
    process: psutil.Process,
    rss_before_load: Any,
    rss_after_load: Any,
    load_time_ms: float,
    ttfts: Sequence[float],
) -> Dict[str, Any]:
    rss_after_benchmark = _rss_mb(process)
    resource = {
        "cpu": platform.processor() or _UNAVAILABLE,
        "rss_before_load_mb": rss_before_load,
        "rss_after_load_mb": rss_after_load,
        "rss_after_benchmark_mb": rss_after_benchmark,
        "rss_load_delta_mb": _delta(rss_after_load, rss_before_load),
        "rss_benchmark_delta_mb": _delta(rss_after_benchmark, rss_after_load),
        "load_time_ms": load_time_ms,
        "ttft_ms": _percentile(ttfts, 0.5) if ttfts else _UNAVAILABLE,
        "ttft_p95_ms": _percentile(ttfts, 0.95) if ttfts else _UNAVAILABLE,
    }
    resource.update(_gpu_resource())
    return resource


def _terminal_result(
    candidate: BenchmarkCandidate,
    corpus: Sequence[Dict[str, Any]],
    process: psutil.Process,
    rss_before_load: Any,
    rss_after_load: Any,
    load_time_ms: float,
    *,
    runtime_status: str,
    runtime_detail: Optional[str],
    safety: str,
    qualification: str,
) -> BenchmarkResult:
    return BenchmarkResult(
        candidate_id=candidate.candidate_id,
        platform=platform.platform(),
        runtime_status=runtime_status,
        runtime_detail=runtime_detail,
        item_count=len(corpus),
        correctness=0.0,
        ece=None,
        max_calibration_error=None,
        nll=None,
        p50_ms=_UNAVAILABLE,
        p95_ms=_UNAVAILABLE,
        reflex_accuracy=None,
        bounded_reasoning_accuracy=None,
        language_rubric_score=None,
        escalation_rate=None,
        false_escalation_rate=None,
        outcome_counts={runtime_status: len(corpus)},
        resource=_resource_snapshot(
            process, rss_before_load, rss_after_load, load_time_ms, ()
        ),
        safety=safety,
        qualification=qualification,
    )


def run_benchmark(
    candidate: BenchmarkCandidate,
    corpus: Iterable[Dict[str, Any]],
    *,
    outbound_deny: bool = True,
) -> BenchmarkResult:
    """Measure one local proposal-only candidate against a frozen corpus."""

    items = [dict(item) for item in corpus]
    if not outbound_deny or not candidate.local_only:
        raise ValueError("local outbound-deny candidate required")

    process = psutil.Process()
    rss_before_load = _rss_mb(process)

    # Candidate score meaning is part of the trust boundary. Reject it before
    # inspecting corpus constraints or loading any candidate runtime.
    if candidate.score_semantics not in VALID_SCORE_SEMANTICS:
        return _terminal_result(
            candidate,
            items,
            process,
            rss_before_load,
            rss_before_load,
            0.0,
            runtime_status=candidate.runtime_status,
            runtime_detail="invalid score_semantics",
            safety="REJECTED",
            qualification="REJECTED",
        )

    unknown_tiers = {
        item.get("tier") for item in items if item.get("tier") not in CANONICAL_TIERS
    }
    if unknown_tiers:
        rendered = sorted(repr(tier) for tier in unknown_tiers)
        return _terminal_result(
            candidate,
            items,
            process,
            rss_before_load,
            rss_before_load,
            0.0,
            runtime_status=candidate.runtime_status,
            runtime_detail=f"non-canonical corpus tier(s): {rendered}",
            safety="REJECTED",
            qualification="REJECTED",
        )

    load_started = time.perf_counter()
    load_error: Optional[str] = None
    if candidate.runtime_status == "available" and candidate.load is not None:
        try:
            candidate.load()
        except Exception as exc:  # Candidate failure is evidence, not a harness crash.
            load_error = f"{type(exc).__name__}: {exc}"
    load_time_ms = (time.perf_counter() - load_started) * 1000
    rss_after_load = _rss_mb(process)

    if candidate.runtime_status != "available" or load_error is not None:
        return _terminal_result(
            candidate,
            items,
            process,
            rss_before_load,
            rss_after_load,
            load_time_ms,
            runtime_status=_UNAVAILABLE,
            runtime_detail=load_error or candidate.runtime_detail,
            safety=_UNAVAILABLE,
            qualification="UNAVAILABLE",
        )
    if candidate.invoke is None:
        raise ValueError("available candidate requires an invoke callable")

    rows: list[Dict[str, Any]] = []
    latencies: list[float] = []
    ttfts: list[float] = []
    safety = "pass"
    outcome_counts: Dict[str, int] = {}
    for item in items:
        started = time.perf_counter()
        try:
            output = candidate.invoke(dict(item))
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies.append(elapsed_ms)
        except Exception as exc:  # Candidate failures stay explicit in evidence.
            elapsed_ms = (time.perf_counter() - started) * 1000
            latencies.append(elapsed_ms)
            output = {"status": "crash", "error": f"{type(exc).__name__}: {exc}"}

        if not isinstance(output, dict):
            output = {"status": "invalid_output"}
            safety = "REJECTED"
        status = str(output.get("status", "completed"))
        if status in {"unavailable", "timeout", "crash", "invalid_output"}:
            outcome = status
        else:
            outcome = "completed"
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        offered = tuple(item.get("offered_capabilities", ()))
        if (
            output.get("host_function")
            or output.get("capability_id") not in (None, *offered)
            or (item["tier"] == "deterministic" and output.get("model_invoked") is True)
        ):
            safety = "REJECTED"

        score = output.get("score")
        if candidate.score_semantics in _PROBABILITY_SEMANTICS and not _is_probability(score):
            safety = "REJECTED"
        ttft = output.get("ttft_ms")
        if isinstance(ttft, (int, float)) and not isinstance(ttft, bool) and ttft >= 0:
            ttfts.append(float(ttft))

        correct = output.get("answer") == item.get("expected")
        perception = _perception_scores(item, output)
        if perception["field_f1"] is not None:
            correct = perception["field_f1"] == 1.0
        elif perception["vqa_score"] is not None:
            correct = perception["vqa_score"] == 1.0
        elif perception["wer"] is not None:
            correct = perception["wer"] == 0.0
        if item["tier"] == "bounded-reasoning":
            correct = correct and _budget_satisfied(item, output)
        rows.append(
            {
                "tier": item["tier"],
                "correct": bool(correct),
                "score": score,
                "escalated": _is_escalation(output),
                "language_rubric": _language_rubric(item, output)
                if item["tier"] == "language-only"
                else None,
                **perception,
            }
        )

    ece, mce, nll = _metrics(rows)
    correctness = sum(row["correct"] for row in rows) / len(rows) if rows else 0.0
    language_rows = [row for row in rows if row["tier"] == "language-only"]
    escalation_rows = [row for row in rows if row["tier"] == "escalate"]
    false_escalation_rows = [
        row for row in rows if row["tier"] in {"deterministic", "reflex"}
    ]

    if any(key in outcome_counts for key in ("unavailable", "timeout", "crash")):
        runtime_status = "degraded"
    else:
        runtime_status = "available"
    if safety != "pass":
        qualification = "REJECTED"
    elif runtime_status != "available":
        qualification = "UNAVAILABLE"
    elif correctness <= 0.5:
        qualification = "REJECTED"
    else:
        qualification = "QUALIFIED_FOR_COMPARISON"

    return BenchmarkResult(
        candidate_id=candidate.candidate_id,
        platform=platform.platform(),
        runtime_status=runtime_status,
        runtime_detail=candidate.runtime_detail,
        item_count=len(rows),
        correctness=correctness,
        ece=ece,
        max_calibration_error=mce,
        nll=nll,
        p50_ms=_percentile(latencies, 0.5) if latencies else _UNAVAILABLE,
        p95_ms=_percentile(latencies, 0.95) if latencies else _UNAVAILABLE,
        reflex_accuracy=_accuracy(rows, "reflex"),
        bounded_reasoning_accuracy=_accuracy(rows, "bounded-reasoning"),
        language_rubric_score=(
            sum(row["language_rubric"] for row in language_rows) / len(language_rows)
            if language_rows
            else None
        ),
        escalation_rate=(
            sum(row["correct"] and row["escalated"] for row in escalation_rows)
            / len(escalation_rows)
            if escalation_rows
            else None
        ),
        false_escalation_rate=(
            sum(row["escalated"] for row in false_escalation_rows)
            / len(false_escalation_rows)
            if false_escalation_rows
            else None
        ),
        outcome_counts=outcome_counts,
        resource=_resource_snapshot(
            process, rss_before_load, rss_after_load, load_time_ms, ttfts
        ),
        safety=safety,
        qualification=qualification,
        field_precision=_mean_metric(rows, "field_precision"),
        field_recall=_mean_metric(rows, "field_recall"),
        field_f1=_mean_metric(rows, "field_f1"),
        vqa_score=_mean_metric(rows, "vqa_score"),
        wer=_mean_metric(rows, "wer"),
        cer=_mean_metric(rows, "cer"),
        transcript_confidence=_mean_metric(rows, "transcript_confidence"),
    )


def write_artifacts(
    out: Path, manifest: Dict[str, Any], result: BenchmarkResult
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    corpus = Path(manifest["corpus"])
    materialized_manifest = {
        **manifest,
        "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
    }
    (out / "manifest.json").write_text(
        json.dumps(materialized_manifest, sort_keys=True, indent=2), encoding="utf-8"
    )
    (out / "result.json").write_text(
        json.dumps(asdict(result), sort_keys=True, indent=2), encoding="utf-8"
    )
