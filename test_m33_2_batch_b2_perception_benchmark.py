import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from uri_core.core.edge.adapters import benchmark
from uri_core.core.edge.adapters.benchmark import BenchmarkCandidate, run_benchmark
from uri_core.core.edge.adapters.speech import (
    NeedleAudioClassification,
    build_actual_speech_candidates,
    build_fixture_speech_candidates,
    character_error_rate,
    probe_needle_audio,
    word_error_rate,
)
from uri_core.core.edge.adapters.vision import (
    build_actual_vision_candidates,
    build_fixture_vision_candidates,
    field_f1_score,
    vqa_exact_match,
)


FIXTURE_ROOT = Path("fixtures/m33_2_edge_perception")


def _fixture(modality):
    manifest = json.loads((FIXTURE_ROOT / f"{modality}_manifest.json").read_text(encoding="utf-8"))
    corpus_path = Path(manifest["corpus"])
    return manifest, json.loads(corpus_path.read_text(encoding="utf-8")), corpus_path


@pytest.mark.parametrize(
    ("modality", "categories"),
    [
        (
            "vision",
            {
                "screenshot_error",
                "field_extraction",
                "ui_state",
                "vqa",
                "ambiguous_low_quality",
                "escalate",
            },
        ),
        ("audio", {"short_command", "dictation", "noisy_ambiguous", "escalate"}),
    ],
)
def test_perception_corpus_schema_and_sha256_are_frozen(modality, categories):
    manifest, corpus, corpus_path = _fixture(modality)
    assert manifest["schema_version"] == "1.0"
    assert manifest["modality"] == modality
    assert manifest["privacy"] == "synthetic-only"
    assert manifest["provenance"] == "URI-owned frozen fixture"
    assert manifest["outbound_deny_required"] is True
    assert hashlib.sha256(corpus_path.read_bytes()).hexdigest() == manifest["corpus_sha256"]
    assert {item["category"] for item in corpus} == categories
    assert len({item["id"] for item in corpus}) == len(corpus)
    if modality == "vision":
        assert all(item.get("image_ref") and (item.get("prompt") or item.get("query")) for item in corpus)
        assert all("expected" in item and (item.get("rubric") or item.get("evaluation_criteria")) for item in corpus)
    else:
        assert all(item.get("audio_ref") and item.get("expected_transcript") for item in corpus)
        assert all(item["reference_tokens"] == item["expected_transcript"].casefold().split() for item in corpus)


def test_vision_scoring_normalizes_keys_values_and_answers():
    expected = {"Reference Number": "URI-42", "Name": "Anika Rao", "Date": "2026-09-20"}
    precision, recall, f1 = field_f1_score(
        expected,
        {"reference_number": "uri 42", "name": "ANIKA   RAO", "extra": "ignored"},
    )
    assert precision == pytest.approx(2 / 3)
    assert recall == pytest.approx(2 / 3)
    assert f1 == pytest.approx(2 / 3)
    assert vqa_exact_match("Amber; warning banner present", " amber warning-banner PRESENT ") == 1.0
    assert vqa_exact_match("3", "four") == 0.0


def test_vision_v1_v2_v3_fixture_pathways_measure_complementary_strengths():
    _, corpus, _ = _fixture("vision")
    results = {
        name: run_benchmark(candidate, corpus)
        for name, candidate in build_fixture_vision_candidates().items()
    }
    assert set(results) == {"v1", "v2", "v3"}
    assert results["v1"].field_f1 == 1.0
    assert results["v1"].vqa_score < results["v2"].vqa_score
    assert results["v2"].field_f1 == 0.0
    assert results["v3"].field_f1 == 1.0
    assert results["v3"].vqa_score == 1.0
    assert results["v3"].correctness == 1.0
    assert all(result.qualification == "QUALIFIED_FOR_COMPARISON" for result in results.values())


def test_actual_vision_candidates_fail_closed_when_runtimes_are_absent(monkeypatch):
    monkeypatch.delenv("URI_EDGE_TESSERACT_PATH", raising=False)
    monkeypatch.delenv("URI_EDGE_VLM_MODEL_PATH", raising=False)
    monkeypatch.setattr("uri_core.core.edge.adapters.vision.shutil.which", lambda _: None)
    _, corpus, _ = _fixture("vision")
    actual = build_actual_vision_candidates()
    assert set(actual) == {"v1", "v2", "v3"}
    for candidate in actual.values():
        result = run_benchmark(candidate, corpus)
        assert result.runtime_status == "unavailable"
        assert result.qualification == "UNAVAILABLE"
        assert result.runtime_detail


def test_audio_wer_and_cer_use_normalized_levenshtein_sequences():
    assert word_error_rate("Open, calendar!", "open calendar") == 0.0
    assert word_error_rate("check unread email", "check email") == pytest.approx(1 / 3)
    assert character_error_rate("A-B", "ab") == 0.0
    assert character_error_rate("cat", "cut") == pytest.approx(1 / 3)


@pytest.mark.parametrize(
    ("module", "classification"),
    [
        (SimpleNamespace(__name__="needle", __version__="3.0.2", complete=lambda text: text), "NOT_SUPPORTED"),
        (
            SimpleNamespace(
                __name__="needle",
                __version__="3.0.2",
                complete=lambda audio, audio_format="wav", sample_rate=16000: (_ for _ in ()).throw(RuntimeError("weights absent")),
            ),
            "API_PRESENT_RUNTIME_UNAVAILABLE",
        ),
        (
            SimpleNamespace(
                __name__="needle",
                __version__="3.0.2",
                complete=lambda audio, audio_format="wav", sample_rate=16000: {"tokens": []},
            ),
            "FAILED_QUALIFICATION",
        ),
        (
            SimpleNamespace(
                __name__="needle",
                __version__="3.0.2",
                __commit__="abc123",
                complete=lambda audio, audio_format="wav", sample_rate=16000: {"transcript": "", "transcript_confidence": 0.8},
            ),
            "AVAILABLE_SUPPORTED",
        ),
    ],
)
def test_needle_audio_probe_has_exact_four_state_classification(module, classification):
    evidence = probe_needle_audio(module)
    assert evidence["classification"] == classification
    assert evidence["classification"] in {value.value for value in NeedleAudioClassification}
    assert evidence["package_version"] == "3.0.2"
    assert evidence["signatures"]
    assert set(evidence) >= {
        "git_commit_or_tag",
        "audio_input_capable",
        "transcription_output_capable",
        "transcript_confidence_capable",
        "runtime_status",
        "load_status",
        "local_offline_behavior",
    }


def test_needle_probe_distinguishes_package_not_installed_from_not_supported():
    evidence = probe_needle_audio(None)
    assert evidence["classification"] == "PACKAGE_NOT_INSTALLED"
    assert evidence["classification"] != "NOT_SUPPORTED"
    assert evidence["module_imported"] is False
    assert evidence["package_version"] is None


def test_needle_probe_recording_is_reproducible_for_same_api_surface():
    module = SimpleNamespace(
        __name__="needle",
        __version__="3.0.2",
        complete=lambda audio, audio_format="wav": {"transcript": "hello"},
    )
    assert probe_needle_audio(module) == probe_needle_audio(module)


def test_fixture_stt_has_realistic_errors_and_confidence_metrics():
    _, corpus, _ = _fixture("audio")
    candidate = build_fixture_speech_candidates()["stt"]
    result = run_benchmark(candidate, corpus)
    assert 0.0 < result.wer < 0.1
    assert 0.0 < result.cer < 0.1
    assert 0.0 < result.transcript_confidence < 1.0
    assert result.correctness == pytest.approx(7 / 8)
    assert result.qualification == "QUALIFIED_FOR_COMPARISON"


def test_alternative_stt_automatically_exists_and_is_truthfully_unavailable(monkeypatch):
    monkeypatch.delenv("URI_EDGE_STT_MODEL_PATH", raising=False)
    _, corpus, _ = _fixture("audio")
    candidates = build_actual_speech_candidates()
    assert set(candidates) == {"needle", "alternative"}
    result = run_benchmark(candidates["alternative"], corpus)
    assert result.runtime_status == "unavailable"
    assert result.qualification == "UNAVAILABLE"
    assert "URI_EDGE_STT_MODEL_PATH" in result.runtime_detail


def test_perception_resource_instrumentation_preserves_unavailable_gpu_ttft(monkeypatch):
    rss_values = iter((50.0, 55.0, 57.0))
    clock_values = iter((1.0, 1.010, 2.0, 2.005))
    monkeypatch.setattr(benchmark, "_rss_mb", lambda process: next(rss_values))
    monkeypatch.setattr(benchmark.time, "perf_counter", lambda: next(clock_values))
    monkeypatch.setattr(benchmark, "_gpu_resource", lambda: {"gpu": "unavailable", "vram_mb": "unavailable"})
    candidate = BenchmarkCandidate(
        "speech-instrumented",
        "fixture",
        "probability",
        "test",
        load=lambda: None,
        invoke=lambda item: {"answer": "hello", "transcript": "hello", "score": 0.9},
    )
    result = run_benchmark(
        candidate,
        [{"tier": "reflex", "category": "short_command", "audio_ref": "synthetic://hello", "expected_transcript": "hello"}],
    )
    assert result.resource["rss_load_delta_mb"] == 5.0
    assert result.resource["rss_benchmark_delta_mb"] == 2.0
    assert result.resource["load_time_ms"] == pytest.approx(10.0)
    assert result.p50_ms == pytest.approx(5.0)
    assert result.resource["gpu"] == "unavailable"
    assert result.resource["ttft_ms"] == "unavailable"


def test_perception_harness_requires_zero_egress_and_recursive_authority_boundary():
    candidate = build_fixture_speech_candidates()["stt"]
    with pytest.raises(ValueError, match="outbound-deny"):
        run_benchmark(candidate, [], outbound_deny=False)

    root = Path("uri_core/core/edge")
    forbidden_import_roots = {
        "approval",
        "canonical_execution",
        "capability_registry",
        "credential",
        "dispatcher",
        "multi_action_dispatch",
        "orchestrator",
        "permission_binding",
        "http",
        "httpx",
        "requests",
        "socket",
        "urllib",
    }
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports = {node.module.split(".")[0], node.module.split(".")[-1]}
            else:
                continue
            assert imports.isdisjoint(forbidden_import_roots), path
