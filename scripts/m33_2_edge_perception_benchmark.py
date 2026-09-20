"""Run the M33.2 B.2 perception matrix and write raw evidence."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from uri_core.core.edge.adapters.benchmark import run_benchmark, write_artifacts
from uri_core.core.edge.adapters.speech import (
    NeedleAudioClassification,
    build_actual_speech_candidates,
    build_fixture_speech_candidates,
    probe_needle_audio,
)
from uri_core.core.edge.adapters.vision import (
    build_actual_vision_candidates,
    build_fixture_vision_candidates,
)


def _load(modality: str) -> tuple[dict, list[dict]]:
    manifest_path = ROOT / f"fixtures/m33_2_edge_perception/{modality}_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["corpus"] = str(ROOT / manifest["corpus"])
    corpus = json.loads(Path(manifest["corpus"]).read_text(encoding="utf-8"))
    return manifest, corpus


def _rss_mb() -> float | str:
    try:
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except (psutil.Error, OSError):
        return "unavailable"


def _write_probe(manifest: dict, probe: dict, elapsed_ms: float, before: object, after: object) -> None:
    output = ROOT / "temp_evidence/m33_2_batch_b2/needle-audio-probe"
    output.mkdir(parents=True, exist_ok=True)
    corpus = Path(manifest["corpus"])
    materialized = {
        **manifest,
        "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
    }
    resource = {
        "cpu": platform.processor() or "unavailable",
        "rss_before_load_mb": before,
        "rss_after_load_mb": after,
        "rss_load_delta_mb": after - before if isinstance(before, float) and isinstance(after, float) else "unavailable",
        "load_time_ms": elapsed_ms,
        "p50_ms": "unavailable",
        "p95_ms": "unavailable",
        "ttft_ms": "unavailable",
        "gpu": "unavailable",
        "vram_mb": "unavailable",
    }
    (output / "manifest.json").write_text(
        json.dumps(materialized, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output / "result.json").write_text(
        json.dumps(
            {
                "candidate_id": "needle-audio-probe",
                "runtime_status": probe["runtime_status"],
                "classification": probe["classification"],
                "probe": probe,
                "resource": resource,
                "outbound_deny": True,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def main() -> None:
    vision_manifest, vision_corpus = _load("vision")
    audio_manifest, audio_corpus = _load("audio")
    evidence_root = ROOT / "temp_evidence/m33_2_batch_b2"

    vision_candidates = {}
    vision_candidates.update(build_fixture_vision_candidates())
    vision_candidates.update({f"actual-{key}": value for key, value in build_actual_vision_candidates().items()})
    for candidate in vision_candidates.values():
        result = run_benchmark(candidate, vision_corpus, outbound_deny=True)
        write_artifacts(evidence_root / candidate.candidate_id, vision_manifest, result)
        print(
            f"{candidate.candidate_id}: runtime={result.runtime_status} "
            f"qualification={result.qualification} correctness={result.correctness:.3f}"
        )

    before = _rss_mb()
    started = time.perf_counter()
    probe = probe_needle_audio()
    elapsed_ms = (time.perf_counter() - started) * 1000
    after = _rss_mb()
    _write_probe(audio_manifest, probe, elapsed_ms, before, after)
    print(f"needle-audio-probe: classification={probe['classification']}")

    actual_speech = build_actual_speech_candidates()
    if probe["classification"] == NeedleAudioClassification.AVAILABLE_SUPPORTED.value:
        speech_candidates = {"needle": actual_speech["needle"]}
    else:
        speech_candidates = build_fixture_speech_candidates()
        speech_candidates["alternative"] = actual_speech["alternative"]
    for candidate in speech_candidates.values():
        result = run_benchmark(candidate, audio_corpus, outbound_deny=True)
        write_artifacts(evidence_root / candidate.candidate_id, audio_manifest, result)
        print(
            f"{candidate.candidate_id}: runtime={result.runtime_status} "
            f"qualification={result.qualification} wer={result.wer} cer={result.cer}"
        )


if __name__ == "__main__":
    main()
