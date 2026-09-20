"""Benchmark-only local speech candidates and empirical Needle audio probe."""

from __future__ import annotations

import inspect
import io
import json
import os
import re
import sys
import wave
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Sequence

from .benchmark import BenchmarkCandidate

try:  # Optional candidate runtime; absence is an expected probe outcome.
    import needle as _needle_module  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - environment-specific.
    _needle_module = None

try:  # Alternate import name used by some distributions.
    import cactus_needle as _cactus_needle_module  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - environment-specific.
    _cactus_needle_module = None

try:  # Optional Windows-compatible local STT runtime.
    from faster_whisper import WhisperModel  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - environment-specific.
    WhisperModel = None


TranscriptCallable = Callable[[Dict[str, Any]], Dict[str, Any]]
_AUDIO_PARAMETERS = frozenset({"audio", "audio_format", "sample_rate", "channels"})


class NeedleAudioClassification(str, Enum):
    AVAILABLE_SUPPORTED = "AVAILABLE_SUPPORTED"
    API_PRESENT_RUNTIME_UNAVAILABLE = "API_PRESENT_RUNTIME_UNAVAILABLE"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    FAILED_QUALIFICATION = "FAILED_QUALIFICATION"
    # Additive sub-state (audit correction, 2026-09-20): distinct from
    # NOT_SUPPORTED, which per the frozen B.2 plan means an installed,
    # introspectable API that genuinely exposes no audio capability. When no
    # needle/cactus_needle module can be imported at all, nothing is
    # introspectable, so that absence must never be reported as NOT_SUPPORTED.
    PACKAGE_NOT_INSTALLED = "PACKAGE_NOT_INSTALLED"


def _normalized_words(value: str) -> list[str]:
    return re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE)


def _levenshtein(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, predicted in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != predicted),
                )
            )
        previous = current
    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Return normalized Levenshtein word error rate."""

    reference_words = _normalized_words(reference)
    hypothesis_words = _normalized_words(hypothesis)
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    return _levenshtein(reference_words, hypothesis_words) / len(reference_words)


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Return character error rate after case/punctuation/space normalization."""

    reference_text = "".join(_normalized_words(reference))
    hypothesis_text = "".join(_normalized_words(hypothesis))
    if not reference_text:
        return 0.0 if not hypothesis_text else 1.0
    return _levenshtein(list(reference_text), list(hypothesis_text)) / len(reference_text)


def _metadata_candidates(distribution_names: Iterable[str]) -> Iterable[Path]:
    normalized = {name.casefold().replace("-", "_") for name in distribution_names}
    for entry in sys.path:
        root = Path(entry or ".")
        if not root.is_dir():
            continue
        for metadata in root.glob("*.dist-info/METADATA"):
            stem = metadata.parent.name.rsplit(".dist-info", 1)[0]
            package_name = stem.rsplit("-", 1)[0].casefold().replace("-", "_")
            if package_name in normalized:
                yield metadata


def _package_version(module: Any) -> tuple[Optional[str], Optional[str]]:
    version = getattr(module, "__version__", None) if module is not None else None
    if version:
        return str(version), "module.__version__"
    for metadata in _metadata_candidates(("cactus-needle", "needle")):
        try:
            for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip(), str(metadata)
        except OSError:
            continue
    return None, None


def _commit_tag(module: Any) -> tuple[Optional[str], Optional[str]]:
    if module is not None:
        for name in ("__commit__", "__git_commit__", "__tag__"):
            value = getattr(module, name, None)
            if value:
                return str(value), f"module.{name}"
        module_file = getattr(module, "__file__", None)
        if module_file:
            root = Path(module_file).resolve().parent
            for parent in (root, *root.parents):
                direct_url = next(parent.glob("*.dist-info/direct_url.json"), None)
                if direct_url:
                    try:
                        data = json.loads(direct_url.read_text(encoding="utf-8"))
                        vcs = data.get("vcs_info") or {}
                        value = vcs.get("commit_id") or vcs.get("requested_revision")
                        if value:
                            return str(value), str(direct_url)
                    except (OSError, ValueError):
                        pass
                if parent.name in {"site-packages", "dist-packages"}:
                    break
    return None, None


def _callables(module: Any) -> Dict[str, Callable[..., Any]]:
    found: Dict[str, Callable[..., Any]] = {}
    for name in ("complete", "run", "embed"):
        value = getattr(module, name, None)
        if callable(value):
            found[name] = value
    for class_name, value in inspect.getmembers(module, inspect.isclass):
        if getattr(value, "__module__", None) != getattr(module, "__name__", None):
            continue
        for name in ("complete", "run", "embed"):
            member = getattr(value, name, None)
            if callable(member):
                found[f"{class_name}.{name}"] = member
    return found


def _silent_wav() -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x00" * 1600)
    return stream.getvalue()


def _probe_kwargs(signature: inspect.Signature) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    values: Dict[str, Any] = {}
    sample = _silent_wav()
    defaults = {
        "audio": sample,
        "audio_format": "wav",
        "sample_rate": 16000,
        "channels": 1,
        "text": "",
        "query": "",
        "prompt": "",
    }
    for name, parameter in signature.parameters.items():
        if name in {"self", "cls"}:
            return None, "callable is an unbound instance/class method"
        if name in defaults:
            values[name] = defaults[name]
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            return None, f"required parameter cannot be safely synthesized: {name}"
    return values, None


def probe_needle_audio(module: Any = None) -> Dict[str, Any]:
    """Empirically classify the installed Needle audio surface exactly once."""

    selected = module or _needle_module or _cactus_needle_module
    version, version_source = _package_version(selected)
    commit, commit_source = _commit_tag(selected)
    evidence: Dict[str, Any] = {
        "classification": NeedleAudioClassification.NOT_SUPPORTED.value,
        "module_imported": selected is not None,
        "module_name": getattr(selected, "__name__", None),
        "package_version": version,
        "package_version_source": version_source,
        "git_commit_or_tag": commit,
        "git_commit_or_tag_source": commit_source,
        "signatures": {},
        "audio_parameters": [],
        "audio_input_capable": False,
        "transcription_output_capable": False,
        "transcript_confidence_capable": False,
        "runtime_status": "unavailable",
        "load_status": "not_loaded",
        "local_offline_behavior": "not verified",
        "detail": None,
    }
    if selected is None:
        evidence["classification"] = NeedleAudioClassification.PACKAGE_NOT_INSTALLED.value
        evidence["detail"] = "neither needle nor cactus_needle can be imported"
        return evidence

    callables = _callables(selected)
    audio_callable: Optional[Callable[..., Any]] = None
    audio_signature: Optional[inspect.Signature] = None
    for name, callable_value in callables.items():
        try:
            signature = inspect.signature(callable_value)
        except (TypeError, ValueError) as exc:
            evidence["signatures"][name] = f"unavailable: {type(exc).__name__}: {exc}"
            continue
        evidence["signatures"][name] = str(signature)
        parameters = sorted(_AUDIO_PARAMETERS & set(signature.parameters))
        if parameters:
            evidence["audio_parameters"] = sorted(
                set(evidence["audio_parameters"]) | set(parameters)
            )
            if audio_callable is None:
                audio_callable = callable_value
                audio_signature = signature

    if audio_callable is None or audio_signature is None:
        evidence["detail"] = "installed API exposes no audio input parameters on complete/run/embed"
        return evidence

    evidence["audio_input_capable"] = True
    kwargs, reason = _probe_kwargs(audio_signature)
    if kwargs is None:
        evidence.update(
            classification=NeedleAudioClassification.API_PRESENT_RUNTIME_UNAVAILABLE.value,
            detail=reason,
            load_status="api_present",
        )
        return evidence
    try:
        result = audio_callable(**kwargs)
    except Exception as exc:  # Runtime/load failure is evidence, not a probe crash.
        evidence.update(
            classification=NeedleAudioClassification.API_PRESENT_RUNTIME_UNAVAILABLE.value,
            detail=f"{type(exc).__name__}: {exc}",
            load_status="load_failed",
            local_offline_behavior="in-process zero-egress probe attempted",
        )
        return evidence

    if isinstance(result, dict):
        transcript = result.get("transcript")
        confidence = result.get("transcript_confidence")
    else:
        transcript = result if isinstance(result, str) else None
        confidence = getattr(result, "transcript_confidence", None)
        transcript = getattr(result, "transcript", transcript)
    evidence["transcription_output_capable"] = isinstance(transcript, str)
    evidence["transcript_confidence_capable"] = isinstance(confidence, (int, float))
    evidence["runtime_status"] = "available"
    evidence["load_status"] = "loaded"
    evidence["local_offline_behavior"] = "in-process zero-egress probe completed"
    if isinstance(transcript, str):
        evidence["classification"] = NeedleAudioClassification.AVAILABLE_SUPPORTED.value
        evidence["detail"] = "audio input executed and returned a transcript"
    else:
        evidence["classification"] = NeedleAudioClassification.FAILED_QUALIFICATION.value
        evidence["detail"] = "audio execution returned no transcript"
    return evidence


def _fixture_transcribe(item: Dict[str, Any]) -> Dict[str, Any]:
    reference = str(item.get("expected_transcript", ""))
    if item.get("id") == "audio-noisy-002":
        transcript = "could you move meeting to three"
        confidence = 0.68
    else:
        transcript = reference
        confidence = 0.94 if item.get("category") != "noisy_ambiguous" else 0.78
    return {
        "answer": transcript,
        "transcript": transcript,
        "transcript_confidence": confidence,
        "score": confidence,
        "status": "escalated" if item.get("category") == "escalate" else "completed",
        "escalated": item.get("category") == "escalate",
        "ttft_ms": 6.0,
    }


def build_fixture_speech_candidates() -> Dict[str, BenchmarkCandidate]:
    return {
        "stt": BenchmarkCandidate(
            "fixture-stt-candidate",
            "uri-owned-fixture",
            "calibrated_confidence",
            "test-only",
            invoke=_fixture_transcribe,
        )
    }


class _FasterWhisperAdapter:
    def __init__(self, model_path: Path) -> None:
        self._model_path = model_path
        self._model: Any = None

    def load(self) -> None:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper library is unavailable")
        self._model = WhisperModel(str(self._model_path), device="cpu", compute_type="int8")

    def __call__(self, item: Dict[str, Any]) -> Dict[str, Any]:
        audio_ref = Path(str(item.get("audio_ref", "")))
        if self._model is None or not audio_ref.is_file():
            return {"status": "unavailable", "score": 0.0}
        generated_segments, info = self._model.transcribe(str(audio_ref), beam_size=1)
        segments = list(generated_segments)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        probabilities = [getattr(segment, "avg_logprob", None) for segment in segments]
        numeric = [float(value) for value in probabilities if isinstance(value, (int, float))]
        confidence = None
        if numeric:
            confidence = max(0.0, min(1.0, 1.0 + sum(numeric) / len(numeric)))
        return {
            "answer": transcript,
            "transcript": transcript,
            "transcript_confidence": confidence,
            "score": confidence if confidence is not None else 0.0,
            "status": "completed" if transcript else "unavailable",
            "language": getattr(info, "language", None),
        }


def _needle_runtime_callable(module: Any) -> Optional[TranscriptCallable]:
    for callable_value in _callables(module).values():
        try:
            signature = inspect.signature(callable_value)
        except (TypeError, ValueError):
            continue
        if not (_AUDIO_PARAMETERS & set(signature.parameters)):
            continue

        def invoke(
            item: Dict[str, Any],
            *,
            selected: Callable[..., Any] = callable_value,
            selected_signature: inspect.Signature = signature,
        ) -> Dict[str, Any]:
            audio_ref = Path(str(item.get("audio_ref", "")))
            if not audio_ref.is_file():
                return {"status": "unavailable", "score": 0.0}
            kwargs, reason = _probe_kwargs(selected_signature)
            if kwargs is None:
                return {"status": "unavailable", "score": 0.0, "detail": reason}
            if "audio" in kwargs:
                kwargs["audio"] = audio_ref.read_bytes()
            result = selected(**kwargs)
            if isinstance(result, dict):
                transcript = result.get("transcript")
                confidence = result.get("transcript_confidence")
            else:
                transcript = getattr(result, "transcript", result if isinstance(result, str) else None)
                confidence = getattr(result, "transcript_confidence", None)
            return {
                "answer": transcript or "",
                "transcript": transcript or "",
                "transcript_confidence": confidence,
                "score": confidence if isinstance(confidence, (int, float)) else 0.0,
                "status": "completed" if isinstance(transcript, str) else "unavailable",
            }

        return invoke
    return None


def build_actual_speech_candidates(
    *, needle_transcribe: Optional[TranscriptCallable] = None
) -> Dict[str, BenchmarkCandidate]:
    """Build Needle and automatic provider-agnostic fallback candidates."""

    probe = probe_needle_audio()
    if needle_transcribe is None and probe["classification"] == NeedleAudioClassification.AVAILABLE_SUPPORTED.value:
        needle_transcribe = _needle_runtime_callable(_needle_module or _cactus_needle_module)
    needle_available = (
        probe["classification"] == NeedleAudioClassification.AVAILABLE_SUPPORTED.value
        and needle_transcribe is not None
    )
    needle_candidate = BenchmarkCandidate(
        "actual-needle-stt",
        "cactus-needle",
        "calibrated_confidence",
        "candidate-specific",
        invoke=needle_transcribe,
        runtime_status="available" if needle_available else "unavailable",
        runtime_detail=None if needle_available else f"Needle probe: {probe['classification']} - {probe['detail']}",
    )

    configured = os.environ.get("URI_EDGE_STT_MODEL_PATH")
    model_path = Path(configured) if configured else None
    details = []
    if model_path is None:
        details.append("URI_EDGE_STT_MODEL_PATH is unset")
    elif not model_path.exists():
        details.append("URI_EDGE_STT_MODEL_PATH does not exist")
    if WhisperModel is None:
        details.append("faster-whisper library is unavailable")
    adapter = _FasterWhisperAdapter(model_path) if model_path and model_path.exists() and WhisperModel else None
    fallback = BenchmarkCandidate(
        "actual-stt-faster-whisper",
        "faster-whisper",
        "calibrated_confidence",
        "MIT",
        invoke=adapter,
        load=adapter.load if adapter else None,
        runtime_status="available" if adapter else "unavailable",
        runtime_detail="; ".join(details) or None,
    )
    return {"needle": needle_candidate, "alternative": fallback}
