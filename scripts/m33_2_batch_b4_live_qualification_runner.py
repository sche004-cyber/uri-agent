"""Run M33.2 Batch B.4 real-model qualification without production promotion."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import psutil
import requests


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from uri_core.core.edge.adapters.benchmark import (  # noqa: E402
    BenchmarkCandidate,
    run_benchmark,
    write_artifacts,
)
from uri_core.core.edge.adapters.ensemble import (  # noqa: E402
    NeedleSubprocessAdapter,
    build_candidate_configurations,
)
from uri_core.core.edge.adapters.speech import (  # noqa: E402
    build_actual_speech_candidates,
)
from uri_core.core.edge.adapters.vision import (  # noqa: E402
    build_actual_vision_candidates,
)
from uri_core.core.edge_lifecycle import (  # noqa: E402
    LazyRuntimeStateManager,
    RuntimeLifecycleState,
    probe_hardware_capacity,
)
from uri_core.core.edge_lifecycle.integrity import sha256_file  # noqa: E402
from uri_core.core.edge_lifecycle.inventory import default_inventory  # noqa: E402
from uri_core.core.model_providers.base import ModelProviderConfig  # noqa: E402
from uri_core.core.model_providers.ollama_provider import OllamaProvider  # noqa: E402


EVIDENCE_ROOT = ROOT / "temp_evidence/m33_2_batch_b4"
BENCHMARK_ROOT = ROOT / "fixtures/m33_2_edge_benchmark"
PERCEPTION_ROOT = ROOT / "fixtures/m33_2_edge_perception"
LLAMA_ROOT = ROOT / "uri_workspace/edge_models/llama.cpp-b11063"
LLAMA_SERVER = LLAMA_ROOT / "windows-cpu-x64/runtime/llama-server.exe"
SMOL_MODEL = LLAMA_ROOT / "smollm2-135m-instruct-q3-k-m/artifact.bin"
QWEN_MODEL = LLAMA_ROOT / "qwen2.5-0.5b-instruct-q4-k-m/artifact.bin"

ASSETS = {
    "llama.cpp-b11063/windows-cpu-x64": {
        "path": LLAMA_ROOT / "windows-cpu-x64/artifact.bin",
        "sha256": "8c5dc1310d9c61953d8079ebe10ee156afa935837516fef3bcad29365ab12122",
        "source": "https://github.com/ggml-org/llama.cpp/releases/download/b11063/llama-b11063-bin-win-cpu-x64.zip",
        "version": "b11063",
        "license": "MIT",
    },
    "smollm2-135m-instruct-q3-k-m": {
        "path": SMOL_MODEL,
        "sha256": "61c69fc5ce91982e26c625d43be5c3c7f0f774da22f4fa4e45c37a80a22ddad4",
        "source": "https://huggingface.co/tensorblock/SmolLM2-135M-Instruct-GGUF",
        "version": "32db44d69cedb731dc0fc96f60e01a86c6f5919d",
        "license": "Apache-2.0",
    },
    "qwen2.5-0.5b-instruct-q4-k-m": {
        "path": QWEN_MODEL,
        "sha256": "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db",
        "source": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "version": "9217f5db79a29953eb74d5343926648285ec7e67",
        "license": "Apache-2.0",
    },
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_fixture(name: str, *, perception: bool = False) -> tuple[Dict[str, Any], list[Dict[str, Any]]]:
    if perception:
        manifest_path = PERCEPTION_ROOT / f"{name}_manifest.json"
    else:
        manifest_path = BENCHMARK_ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["corpus"] = str(ROOT / manifest["corpus"])
    corpus = json.loads(Path(manifest["corpus"]).read_text(encoding="utf-8"))
    return manifest, corpus


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _short_answer(value: str) -> str:
    answer = value.strip().splitlines()[0].strip() if value.strip() else ""
    for prefix in ("answer:", "final answer:"):
        if answer.casefold().startswith(prefix):
            answer = answer[len(prefix) :].strip()
    answer = answer.strip(" `*_\"'.")
    lowered = answer.casefold()
    if lowered in {"yes", "no"}:
        return lowered
    if lowered.startswith("in the "):
        return answer.rsplit(" ", 1)[-1]
    marker = " is in the "
    if marker in lowered:
        return answer.rsplit(" ", 1)[-1]
    return answer


class LlamaServerComponent:
    def __init__(self, model_path: Path, role: str) -> None:
        self.model_path = model_path
        self.role = role
        self.port = _free_port()
        self.process: Optional[subprocess.Popen[bytes]] = None
        self.load_time_ms: Optional[float] = None
        self.rss_after_load_mb: Any = "unavailable"
        self.peak_rss_mb: Any = "unavailable"
        self.records: list[Dict[str, Any]] = []

    def load(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        for required in (LLAMA_SERVER, self.model_path):
            if not required.is_file():
                raise FileNotFoundError(str(required))
        started = time.perf_counter()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(
            [
                str(LLAMA_SERVER),
                "-m",
                str(self.model_path),
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "-c",
                "1024",
                "-t",
                "4",
                "--log-disable",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"llama-server exited with {self.process.returncode}")
            try:
                response = requests.get(self._url("/health"), timeout=0.25)
                if response.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.1)
        else:
            raise TimeoutError("llama-server did not become ready")
        self.load_time_ms = (time.perf_counter() - started) * 1000.0
        self._sample_rss()
        self.rss_after_load_mb = self.peak_rss_mb

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _sample_rss(self) -> None:
        if self.process is None:
            return
        try:
            rss = psutil.Process(self.process.pid).memory_info().rss / (1024 * 1024)
            if not isinstance(self.peak_rss_mb, (int, float)) or rss > self.peak_rss_mb:
                self.peak_rss_mb = rss
        except (psutil.Error, OSError):
            pass

    def __call__(self, item: Dict[str, Any]) -> Dict[str, Any]:
        self.load()
        if self.role == "language":
            system = (
                "Follow the request directly. Keep the response to one short sentence and "
                "do not claim to execute tools or actions."
            )
            max_tokens = 64
        else:
            system = (
                "Solve the bounded reasoning question. Return only the shortest exact final "
                "answer, without explanation or punctuation."
            )
            max_tokens = 32
        started = time.perf_counter()
        response = requests.post(
            self._url("/v1/chat/completions"),
            json={
                "model": "local",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": str(item.get("input", ""))},
                ],
                "temperature": 0,
                "seed": 1,
                "max_tokens": max_tokens,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        data = response.json()
        content = str(data["choices"][0]["message"]["content"])
        answer = content.strip() if self.role == "language" else _short_answer(content)
        usage = data.get("usage") or {}
        timings = data.get("timings") or {}
        self._sample_rss()
        record = {
            "item_id": item.get("id"),
            "raw_answer": content,
            "normalized_answer": answer,
            "latency_ms": elapsed_ms,
            "usage": usage,
            "timings": timings,
        }
        self.records.append(record)
        output: Dict[str, Any] = {
            "answer": answer,
            "score": None,
            "status": "completed",
            "provider_latency_ms": elapsed_ms,
        }
        if self.role == "reasoner":
            output["steps_used"] = 1
            output["tokens_used"] = int(usage.get("completion_tokens") or 0)
        return output

    def resource(self) -> Dict[str, Any]:
        return {
            "runtime": "llama.cpp",
            "runtime_version": "b11063",
            "model_path": str(self.model_path),
            "load_time_ms": self.load_time_ms,
            "rss_after_load_mb": self.rss_after_load_mb,
            "peak_rss_mb": self.peak_rss_mb,
            "gpu": "unavailable",
            "vram_mb": "unavailable",
        }

    def close(self) -> None:
        process = self.process
        self.process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


class OllamaReasonerComponent:
    def __init__(self, model: str) -> None:
        self.model = model
        self.provider = OllamaProvider(
            ModelProviderConfig(
                base_url="http://127.0.0.1:11434",
                model=model,
                timeout_seconds=120.0,
                context_tokens=4096,
            )
        )
        self.records: list[Dict[str, Any]] = []

    def __call__(self, item: Dict[str, Any]) -> Dict[str, Any]:
        response = self.provider.complete(
            system=(
                "This is a bounded local benchmark. Return only the shortest exact final "
                "answer, without explanation or punctuation."
            ),
            user=str(item.get("input", "")),
            temperature=0.0,
            max_tokens=32,
        )
        answer = _short_answer(response.content)
        self.records.append(
            {
                "item_id": item.get("id"),
                "raw_answer": response.content,
                "normalized_answer": answer,
                "prompt_tokens": response.prompt_tokens,
                "eval_tokens": response.eval_tokens,
                "duration_seconds": response.duration_seconds,
            }
        )
        return {
            "answer": answer,
            "score": None,
            "status": "completed",
            "steps_used": 1,
            "tokens_used": int(response.eval_tokens or 0),
        }


def _needle_adapter() -> NeedleSubprocessAdapter:
    cache = Path.home() / ".cache/cactus-needle/v3/3.0.1"
    return NeedleSubprocessAdapter(
        ROOT / ".venv-needle/Scripts/python.exe",
        ROOT / "scripts/m33_2_needle_bridge.py",
        environment={
            "NEEDLE_TELEMETRY": "0",
            "DO_NOT_TRACK": "1",
            "HF_HUB_OFFLINE": "1",
            "NEEDLE3_LIB_PATH": str(cache / "libneedle.dll"),
        },
    )


def _normalize_arguments(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_arguments(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_arguments(item) for item in value]
    if isinstance(value, str):
        return value.strip().strip(".,;:!?\"'").casefold()
    return value


def _exact_supplemental(
    records: Iterable[Dict[str, Any]],
    expected_key: str,
    actual_key: str,
    *,
    normalize_arguments: bool = False,
) -> Dict[str, Any]:
    selected = [row for row in records if row.get(expected_key) is not None]
    matches = []
    for row in selected:
        actual = row.get("output", {}).get(actual_key)
        expected = row.get(expected_key)
        if normalize_arguments:
            actual = _normalize_arguments(actual)
            expected = _normalize_arguments(expected)
        matches.append(actual == expected)
    return {
        "item_count": len(selected),
        "exact_matches": sum(matches),
        "accuracy": sum(matches) / len(matches) if matches else None,
    }


def _verify_assets() -> Dict[str, Any]:
    evidence: Dict[str, Any] = {}
    for asset_id, metadata in ASSETS.items():
        path = Path(metadata["path"])
        actual, byte_size = sha256_file(path)
        if actual != metadata["sha256"]:
            raise RuntimeError(f"asset checksum mismatch: {asset_id}")
        evidence[asset_id] = {
            **{key: value for key, value in metadata.items() if key != "path"},
            "path": str(path),
            "byte_size": byte_size,
            "actual_sha256": actual,
            "verified": True,
            "sourced_via": "edge_lifecycle.download_model_artifact",
        }
    return evidence


def _run_configuration(name: str, manifest: Dict[str, Any], corpus: list[Dict[str, Any]]) -> Dict[str, Any]:
    needle = _needle_adapter()
    language = LlamaServerComponent(SMOL_MODEL, "language") if name in {"B", "D"} else None
    reasoner = LlamaServerComponent(QWEN_MODEL, "reasoner") if name in {"C", "D"} else None
    lifecycle = LazyRuntimeStateManager("m33.2-b4", f"configuration-{name.lower()}")
    candidate = build_candidate_configurations(
        tiny_reasoner_id="qwen2.5-0.5b-instruct",
        needle=needle,
        language=language,
        reasoner=reasoner,
    )[name]
    try:
        result = run_benchmark(candidate, corpus, outbound_deny=True)
        lifecycle.load(on_demand=name != "A")
        out = EVIDENCE_ROOT / f"configuration-{name.lower()}"
        write_artifacts(out, manifest, result)
        needle_resource: Dict[str, Any] = {
            "runtime_info": needle.runtime_info,
            "provider_peak_ram_mb": max(
                (
                    float(row["output"]["provider_peak_ram_mb"])
                    for row in needle.records
                    if isinstance(row.get("output", {}).get("provider_peak_ram_mb"), (int, float))
                ),
                default="unavailable",
            ),
            "gpu": "unavailable",
            "vram_mb": "unavailable",
        }
        try:
            if needle.pid is not None:
                needle_resource["bridge_rss_mb"] = psutil.Process(needle.pid).memory_info().rss / (1024 * 1024)
        except (psutil.Error, OSError):
            needle_resource["bridge_rss_mb"] = "unavailable"
        supplemental = {
            "argument_extraction": _exact_supplemental(
                needle.records,
                "expected_arguments",
                "arguments",
                normalize_arguments=True,
            ),
            "structured_record_extraction": _exact_supplemental(needle.records, "expected_record", "answer"),
        }
        _write_json(out / "needle_provider_records.json", needle.records)
        _write_json(out / "needle_resource.json", needle_resource)
        _write_json(out / "supplemental_metrics.json", supplemental)
        if language is not None:
            _write_json(out / "language_provider_records.json", language.records)
            _write_json(out / "language_resource.json", language.resource())
        if reasoner is not None:
            _write_json(out / "reasoner_provider_records.json", reasoner.records)
            _write_json(out / "reasoner_resource.json", reasoner.resource())
        return {
            "result": asdict(result),
            "supplemental": supplemental,
            "needle_resource": needle_resource,
            "language_resource": language.resource() if language else None,
            "reasoner_resource": reasoner.resource() if reasoner else None,
        }
    finally:
        if language is not None:
            language.close()
        if reasoner is not None:
            reasoner.close()
        needle.close()
        if lifecycle.state in {RuntimeLifecycleState.RESIDENT, RuntimeLifecycleState.ON_DEMAND}:
            lifecycle.unload()
        _write_json(
            EVIDENCE_ROOT / f"configuration-{name.lower()}/lifecycle.json",
            {"history": [state.value for state in lifecycle.history]},
        )


def _run_main_brain_controls(corpus: list[Dict[str, Any]]) -> Dict[str, Any]:
    reasoning = [item for item in corpus if item.get("tier") == "bounded-reasoning"]
    manifest = {
        "schema_version": "1.0",
        "corpus": str(BENCHMARK_ROOT / "corpus.json"),
        "corpus_filter": "bounded-reasoning",
        "outbound_deny_required": False,
        "control_path": "existing OllamaProvider on loopback",
    }
    controls: Dict[str, Any] = {}
    for model in ("qwen3.5:9b", "gemma4:12b"):
        component = OllamaReasonerComponent(model)
        candidate = BenchmarkCandidate(
            candidate_id=f"main-brain-control-{model.replace(':', '-')}",
            provider="ollama-main-brain-control",
            score_semantics="none",
            licence="installed-model-metadata-not-asserted",
            invoke=component,
        )
        result = run_benchmark(candidate, reasoning, outbound_deny=True)
        key = model.replace(":", "-")
        out = EVIDENCE_ROOT / f"main-brain-{key}"
        write_artifacts(out, manifest, result)
        _write_json(out / "provider_records.json", component.records)
        controls[model] = asdict(result)
    return controls


def _run_perception() -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for modality, candidates in (
        ("audio", build_actual_speech_candidates()),
        ("vision", build_actual_vision_candidates()),
    ):
        manifest, corpus = _load_fixture(modality, perception=True)
        results[modality] = {}
        for name, candidate in candidates.items():
            result = run_benchmark(candidate, corpus, outbound_deny=True)
            out = EVIDENCE_ROOT / f"{modality}-{name}"
            write_artifacts(out, manifest, result)
            results[modality][name] = asdict(result)
    return results


def main() -> int:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    source_assets = _verify_assets()
    _write_json(EVIDENCE_ROOT / "source_assets.json", source_assets)
    _write_json(EVIDENCE_ROOT / "edge_inventory.json", default_inventory().snapshot())
    _write_json(EVIDENCE_ROOT / "hardware.json", asdict(probe_hardware_capacity()))

    manifest, corpus = _load_fixture("language")
    corpus_sha256 = hashlib.sha256(Path(manifest["corpus"]).read_bytes()).hexdigest()
    configurations: Dict[str, Any] = {}
    for name in ("A", "B", "C", "D"):
        print(f"running configuration {name}", flush=True)
        configurations[name] = _run_configuration(name, manifest, corpus)

    print("running main-brain controls", flush=True)
    controls = _run_main_brain_controls(corpus)
    print("recording perception availability", flush=True)
    perception = _run_perception()

    summary = {
        "milestone": "M33.2 Batch B.4",
        "status": "qualification evidence generated; no production promotion",
        "corpus_sha256": corpus_sha256,
        "configurations": configurations,
        "main_brain_controls": controls,
        "perception": perception,
        "limitations": {
            "audio_corpus": "synthetic:// references are not materialized audio files",
            "vision_corpus": "synthetic:// references are not materialized image files",
            "stt": "faster-whisper checkpoint is multi-file and no accepted published SHA-256 manifest was available for every required file",
            "ocr": "no verified portable Windows Tesseract distribution was adopted",
            "vlm": "no <=1B candidate reusing the accepted text runtime was available without a second ML framework",
        },
    }
    _write_json(EVIDENCE_ROOT / "consolidated_results.json", summary)
    print(str(EVIDENCE_ROOT / "consolidated_results.json"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
