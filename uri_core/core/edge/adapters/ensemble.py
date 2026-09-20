"""Experimental micro-model configurations isolated from production routing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from .benchmark import BenchmarkCandidate


NEEDLE_3 = "needle-3"
SMOLLM2_135M = "smollm2-135m-instruct"
DEEPSEEK_TINY = "deepseek-r1-distill-qwen-1.5b"
QWEN_TINY = "qwen2.5-1.5b-instruct"
TINY_REASONER_IDS = (DEEPSEEK_TINY, QWEN_TINY)

_MODEL_PATH_ENV = {
    NEEDLE_3: "URI_EDGE_NEEDLE3_MODEL_PATH",
    SMOLLM2_135M: "URI_EDGE_SMOLLM2_135M_MODEL_PATH",
    DEEPSEEK_TINY: "URI_EDGE_DEEPSEEK_R1_1_5B_MODEL_PATH",
    QWEN_TINY: "URI_EDGE_QWEN2_5_1_5B_MODEL_PATH",
}

Component = Callable[[Dict[str, Any]], Dict[str, Any]]


def _deterministic_core(item: Dict[str, Any]) -> Dict[str, Any]:
    operation = item.get("operation")
    arguments = item.get("arguments") or {}
    if operation == "arithmetic":
        left = arguments.get("left")
        right = arguments.get("right")
        operator = arguments.get("operator")
        if operator == "+":
            answer = str(left + right)
        elif operator == "-":
            answer = str(left - right)
        elif operator == "*":
            answer = str(left * right)
        else:
            return {"status": "invalid_input", "model_invoked": False, "score": 0.0}
    elif operation == "reverse":
        answer = str(arguments.get("value", ""))[::-1]
    elif operation == "lookup":
        answer = str((arguments.get("table") or {}).get(str(arguments.get("key")), ""))
    elif operation == "length":
        answer = str(len(str(arguments.get("value", ""))))
    else:
        return {"status": "invalid_input", "model_invoked": False, "score": 0.0}
    return {
        "answer": answer,
        "score": 1.0,
        "status": "completed",
        "model_invoked": False,
        "ttft_ms": 0.0,
    }


class EnsembleAdapter:
    """Dict-in/dict-out tier dispatcher used only by the benchmark harness."""

    def __init__(self, components: Mapping[str, Optional[Component]]) -> None:
        self._components = dict(components)

    def __call__(self, item: Dict[str, Any]) -> Dict[str, Any]:
        tier = item.get("tier")
        if tier == "deterministic":
            return _deterministic_core(item)
        if tier == "escalate":
            return {
                "answer": "escalate",
                "score": 0.99,
                "status": "escalated",
                "escalated": True,
                "model_invoked": False,
                "ttft_ms": 0.0,
            }

        role = {
            "reflex": "reflex",
            "language-only": "language",
            "bounded-reasoning": "reasoner",
        }.get(str(tier))
        component = self._components.get(str(role))
        if component is None:
            return {
                "answer": "escalate",
                "score": 0.55,
                "status": "escalated",
                "escalated": True,
                "model_invoked": False,
                "ttft_ms": 0.0,
            }
        output = component(dict(item))
        if not isinstance(output, dict):
            return {"status": "invalid_output", "model_invoked": True}
        return {**output, "model_invoked": True}


def _fixture_component(item: Dict[str, Any]) -> Dict[str, Any]:
    output: Dict[str, Any] = {
        "answer": item.get("expected"),
        "score": 0.9,
        "status": "completed",
        "ttft_ms": 0.1,
    }
    expected = item.get("expected")
    if isinstance(expected, dict):
        output["capability_id"] = expected.get("capability_id")
    if item.get("tier") == "bounded-reasoning":
        output["steps_used"] = min(2, int((item.get("budget") or {}).get("max_steps", 2)))
        output["tokens_used"] = min(
            24, int((item.get("budget") or {}).get("max_tokens", 24))
        )
    return output


def _definitions(
    tiny_reasoner_id: str,
    needle: Optional[Component],
    language: Optional[Component],
    reasoner: Optional[Component],
) -> Dict[str, tuple[tuple[str, ...], Dict[str, Optional[Component]]]]:
    return {
        "A": ((NEEDLE_3,), {"reflex": needle}),
        "B": (
            (NEEDLE_3, SMOLLM2_135M),
            {"reflex": needle, "language": language},
        ),
        "C": (
            (NEEDLE_3, tiny_reasoner_id),
            {"reflex": needle, "reasoner": reasoner},
        ),
        "D": (
            (NEEDLE_3, SMOLLM2_135M, tiny_reasoner_id),
            {"reflex": needle, "language": language, "reasoner": reasoner},
        ),
    }


def _runtime_detail(required_models: tuple[str, ...]) -> str:
    details = []
    for model_id in required_models:
        env_name = _MODEL_PATH_ENV[model_id]
        value = os.environ.get(env_name)
        if not value:
            details.append(f"{model_id}: {env_name} is not set")
        elif not Path(value).is_file():
            details.append(f"{model_id}: configured weights are unavailable")
        else:
            details.append(f"{model_id}: weights present but no local callable supplied")
    return "; ".join(details)


def _roles(model_ids: tuple[str, ...]) -> tuple[str, ...]:
    roles = ["reflex"]
    if SMOLLM2_135M in model_ids:
        roles.append("language")
    if any(model_id in TINY_REASONER_IDS for model_id in model_ids):
        roles.append("reasoner")
    return tuple(roles)


def _candidate(
    configuration: str,
    model_ids: tuple[str, ...],
    components: Mapping[str, Optional[Component]],
    *,
    fixture: bool,
) -> BenchmarkCandidate:
    available = fixture or all(components.get(role) is not None for role in _roles(model_ids))
    prefix = "fixture-" if fixture else ""
    return BenchmarkCandidate(
        candidate_id=f"{prefix}configuration-{configuration.lower()}-{'-'.join(model_ids)}",
        provider="uri-owned-fixture" if fixture else "local-model-runtime",
        score_semantics="calibrated_confidence",
        licence="test-only" if fixture else "candidate-specific-permissive",
        invoke=EnsembleAdapter(components),
        runtime_status="available" if available else "unavailable",
        runtime_detail=None if available else _runtime_detail(model_ids),
    )


def build_candidate_configurations(
    *,
    tiny_reasoner_id: str = QWEN_TINY,
    needle: Optional[Component] = None,
    language: Optional[Component] = None,
    reasoner: Optional[Component] = None,
) -> Dict[str, BenchmarkCandidate]:
    """Build actual A-D candidates; absent injected local runtimes stay unavailable."""

    if tiny_reasoner_id not in TINY_REASONER_IDS:
        raise ValueError(f"unsupported tiny reasoner: {tiny_reasoner_id}")
    return {
        name: _candidate(name, model_ids, components, fixture=False)
        for name, (model_ids, components) in _definitions(
            tiny_reasoner_id, needle, language, reasoner
        ).items()
    }


def build_fixture_candidate_configurations(
    *, tiny_reasoner_id: str = QWEN_TINY
) -> Dict[str, BenchmarkCandidate]:
    """Build deterministic simulations that exercise A-D without model weights."""

    return {
        name: _candidate(name, model_ids, components, fixture=True)
        for name, (model_ids, components) in _definitions(
            tiny_reasoner_id,
            _fixture_component,
            _fixture_component,
            _fixture_component,
        ).items()
    }


def build_fixture_baseline_candidate() -> BenchmarkCandidate:
    """Single generalist control, clearly labelled as a deterministic fixture."""

    return BenchmarkCandidate(
        candidate_id="fixture-generalist-baseline",
        provider="uri-owned-fixture",
        score_semantics="calibrated_confidence",
        licence="test-only",
        invoke=EnsembleAdapter(
            {
                "reflex": _fixture_component,
                "language": _fixture_component,
                "reasoner": _fixture_component,
            }
        ),
    )
