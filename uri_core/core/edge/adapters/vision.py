"""Benchmark-only local vision candidates and perception scoring."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from .benchmark import BenchmarkCandidate

try:  # Optional runtime; qualification remains available without it.
    import pytesseract  # type: ignore[import-not-found]
    from PIL import Image  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - environment-specific.
    pytesseract = None
    Image = None


VisionCallable = Callable[[Dict[str, Any]], Dict[str, Any]]


def _normalize(value: Any) -> str:
    return " ".join(
        re.findall(r"[\w]+", str(value).casefold().replace("_", " "), flags=re.UNICODE)
    )


def field_f1_score(
    expected_fields: Dict[str, Any], predicted_fields: Dict[str, Any]
) -> Tuple[float, float, float]:
    """Score exact normalized key/value pairs with field precision/recall/F1."""

    expected = {(_normalize(key), _normalize(value)) for key, value in expected_fields.items()}
    predicted = {
        (_normalize(key), _normalize(value)) for key, value in predicted_fields.items()
    }
    if not expected and not predicted:
        return 1.0, 1.0, 1.0
    matched = len(expected & predicted)
    precision = matched / len(predicted) if predicted else 0.0
    recall = matched / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def vqa_exact_match(expected: str, predicted: str) -> float:
    """Return one only when normalized answer strings match exactly."""

    return float(_normalize(expected) == _normalize(predicted))


def _fixture_output(item: Dict[str, Any], pathway: str) -> Dict[str, Any]:
    category = str(item.get("category"))
    expected = item.get("expected")
    correct_categories = {
        "v1": {"screenshot_error", "field_extraction", "ambiguous_low_quality", "escalate"},
        "v2": {"ui_state", "vqa", "ambiguous_low_quality", "escalate"},
        "v3": {
            "screenshot_error",
            "field_extraction",
            "ui_state",
            "vqa",
            "ambiguous_low_quality",
            "escalate",
        },
    }[pathway]
    correct = category in correct_categories
    if category == "field_extraction":
        fields = dict(expected) if correct and isinstance(expected, dict) else {"name": "unknown"}
        answer: Any = fields
    else:
        fields = None
        answer = expected if correct else "unknown"
    output: Dict[str, Any] = {
        "answer": answer,
        "score": {"v1": 0.86, "v2": 0.88, "v3": 0.94}[pathway] if correct else 0.42,
        "status": "escalated" if answer == "escalate" else "completed",
        "escalated": answer == "escalate",
        "ttft_ms": {"v1": 2.0, "v2": 14.0, "v3": 18.0}[pathway],
        "fusion": "ocr+vlm" if pathway == "v3" else pathway,
    }
    if fields is not None:
        output["fields"] = fields
    return output


def _fixture_candidate(pathway: str) -> BenchmarkCandidate:
    candidate_ids = {
        "v1": "fixture-v1-ocr",
        "v2": "fixture-v2-vlm",
        "v3": "fixture-v3-hybrid",
    }
    return BenchmarkCandidate(
        candidate_id=candidate_ids[pathway],
        provider="uri-owned-fixture",
        score_semantics="calibrated_confidence",
        licence="test-only",
        invoke=lambda item: _fixture_output(item, pathway),
    )


def build_fixture_vision_candidates() -> Dict[str, BenchmarkCandidate]:
    """Return deterministic OCR, VLM, and hybrid harness simulations."""

    return {name: _fixture_candidate(name) for name in ("v1", "v2", "v3")}


def _tesseract_probe() -> tuple[Optional[str], Optional[str]]:
    configured = os.environ.get("URI_EDGE_TESSERACT_PATH")
    if configured:
        path = Path(configured)
        if not path.is_file():
            return None, "URI_EDGE_TESSERACT_PATH does not name an available file"
        return str(path), None
    discovered = shutil.which("tesseract")
    if not discovered:
        return None, "tesseract system binary is not on PATH and URI_EDGE_TESSERACT_PATH is unset"
    return discovered, None


def _extract_fields(text: str) -> Dict[str, str]:
    patterns = {
        "name": r"(?im)^\s*name\s*[:#-]\s*(.+?)\s*$",
        "date": r"(?im)^\s*date\s*[:#-]\s*(.+?)\s*$",
        "reference_number": r"(?im)^\s*(?:reference(?:\s+number)?|ref)\s*[:#-]\s*(.+?)\s*$",
    }
    fields: Dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            fields[key] = match.group(1).strip()
    return fields


def _ocr_invoke(tesseract_path: str) -> VisionCallable:
    def invoke(item: Dict[str, Any]) -> Dict[str, Any]:
        if pytesseract is None or Image is None:
            return {"status": "unavailable", "score": 0.0}
        image_ref = Path(str(item.get("image_ref", "")))
        if not image_ref.is_file():
            return {
                "status": "unavailable",
                "score": 0.0,
                "detail": f"image fixture is not materialized: {image_ref}",
            }
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        text = pytesseract.image_to_string(Image.open(image_ref))
        fields = _extract_fields(text)
        answer: Any = fields if item.get("category") == "field_extraction" else text.strip()
        return {
            "answer": answer,
            "fields": fields,
            "score": 0.75 if text.strip() else 0.0,
            "status": "completed" if text.strip() else "unavailable",
        }

    return invoke


def _vlm_detail(model_path: Optional[str], vlm: Optional[VisionCallable]) -> Optional[str]:
    if not model_path:
        return "URI_EDGE_VLM_MODEL_PATH is unset"
    if not Path(model_path).exists():
        return "URI_EDGE_VLM_MODEL_PATH does not exist"
    if vlm is None:
        return "local VLM weights are present but no offline inference callable was supplied"
    return None


def _hybrid_invoke(ocr: VisionCallable, vlm: VisionCallable) -> VisionCallable:
    def invoke(item: Dict[str, Any]) -> Dict[str, Any]:
        ocr_output = ocr(dict(item))
        vlm_output = vlm(dict(item))
        if ocr_output.get("status") == "unavailable" or vlm_output.get("status") == "unavailable":
            return {"status": "unavailable", "score": 0.0}
        category = item.get("category")
        selected = ocr_output if category in {"field_extraction", "screenshot_error"} else vlm_output
        scores = [value for value in (ocr_output.get("score"), vlm_output.get("score")) if isinstance(value, (int, float))]
        return {**selected, "score": sum(scores) / len(scores) if scores else 0.0, "fusion": "ocr+vlm"}

    return invoke


def build_actual_vision_candidates(
    *, vlm: Optional[VisionCallable] = None
) -> Dict[str, BenchmarkCandidate]:
    """Build environment-backed pathways; absent binaries/weights fail closed."""

    tesseract_path, ocr_detail = _tesseract_probe()
    if pytesseract is None or Image is None:
        ocr_detail = "pytesseract/Pillow runtime is unavailable"
        tesseract_path = None
    model_path = os.environ.get("URI_EDGE_VLM_MODEL_PATH")
    vlm_detail = _vlm_detail(model_path, vlm)
    ocr_callable = _ocr_invoke(tesseract_path) if tesseract_path else None
    v1 = BenchmarkCandidate(
        "actual-v1-ocr", "pytesseract", "calibrated_confidence", "Apache-2.0",
        invoke=ocr_callable, runtime_status="available" if ocr_callable else "unavailable",
        runtime_detail=ocr_detail,
    )
    v2 = BenchmarkCandidate(
        "actual-v2-vlm", "local-vlm", "calibrated_confidence", "candidate-specific",
        invoke=vlm, runtime_status="available" if vlm_detail is None else "unavailable",
        runtime_detail=vlm_detail,
    )
    hybrid_detail = "; ".join(detail for detail in (ocr_detail, vlm_detail) if detail)
    hybrid = _hybrid_invoke(ocr_callable, vlm) if ocr_callable and vlm_detail is None and vlm else None
    v3 = BenchmarkCandidate(
        "actual-v3-hybrid", "ocr-vlm-hybrid", "calibrated_confidence", "candidate-specific",
        invoke=hybrid, runtime_status="available" if hybrid else "unavailable",
        runtime_detail=hybrid_detail or None,
    )
    return {"v1": v1, "v2": v2, "v3": v3}
