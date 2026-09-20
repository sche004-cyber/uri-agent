import ast
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from uri_core.core.edge_lifecycle import (
    EdgeAssetInventory,
    EdgeStorageValidationError,
    IntegrityVerificationError,
    LazyRuntimeStateManager,
    NonLoopbackEndpointError,
    RuntimeLifecycleState,
    can_host_model,
    detect_lmstudio_runtime,
    detect_ollama_runtime,
    download_model_artifact,
    import_model_file,
    probe_hardware_capacity,
    record_invocation_attempt,
    remove_model_artifact,
)
from uri_core.core.edge_lifecycle import hardware, storage


@pytest.fixture
def managed_root(tmp_path, monkeypatch):
    root = tmp_path / "uri_workspace" / "edge_models"
    monkeypatch.setattr(storage, "DEFAULT_EDGE_MODEL_ROOT", root)
    return root


def _response(payload, *, content=None, headers=None):
    response = Mock()
    response.status_code = 200
    response.is_redirect = False
    response.is_permanent_redirect = False
    response.content = content if content is not None else json.dumps(payload).encode()
    response.headers = headers or {}
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_runtime_detection_loopback_only_and_discovery(managed_root, monkeypatch):
    ollama = _response(
        {"models": [{"name": "qwen:1.5b", "size": 42, "digest": "sha256:abc"}]},
        headers={"Ollama-Version": "0.12.0"},
    )
    lmstudio = _response({"data": [{"id": "local/vlm"}, {"id": "local/stt"}]})
    responses = iter((ollama, lmstudio))
    monkeypatch.setattr("uri_core.core.edge_lifecycle.detection.requests.get", lambda *a, **k: next(responses))

    found_ollama = detect_ollama_runtime()
    found_lmstudio = detect_lmstudio_runtime()
    assert found_ollama.status == "found_reachable"
    assert found_ollama.version == "0.12.0"
    assert found_ollama.models_detected[0].tag == "1.5b"
    assert found_ollama.models_detected[0].byte_size == 42
    assert [item.model_id for item in found_lmstudio.models_detected] == ["local/vlm", "local/stt"]
    with pytest.raises(NonLoopbackEndpointError):
        detect_ollama_runtime("http://192.0.2.1:11434/api/tags")


def _redirect_response(location="https://attacker.example/exfil"):
    response = Mock()
    response.status_code = 302
    response.is_redirect = True
    response.is_permanent_redirect = False
    response.content = b""
    response.headers = {"Location": location}
    return response


def test_runtime_detection_refuses_to_follow_redirect_off_loopback(managed_root, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        return _redirect_response()

    monkeypatch.setattr("uri_core.core.edge_lifecycle.detection.requests.get", fake_get)

    found_ollama = detect_ollama_runtime()
    found_lmstudio = detect_lmstudio_runtime()

    assert found_ollama.status in {"found_unreachable", "not_found"}
    assert found_ollama.endpoint.reachable is False
    assert found_lmstudio.status in {"found_unreachable", "not_found"}
    assert found_lmstudio.endpoint.reachable is False
    assert all(kwargs.get("allow_redirects") is False for kwargs in calls)


def test_manual_import_and_sha256_verification(managed_root, tmp_path):
    source = tmp_path / "model.gguf"
    source.write_bytes(b"verified model")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    record = import_model_file(source, "portable", "tiny-model", digest)
    assert record.content_hash == digest
    assert record.byte_size == len(b"verified model")
    assert Path(record.file_path).read_bytes() == b"verified model"
    inventory = json.loads((managed_root / "inventory.json").read_text(encoding="utf-8"))
    metadata = inventory["artifacts"]["portable/tiny-model"]
    assert metadata["source_type"] == "local_path"
    assert metadata["license"] == "unknown"
    with pytest.raises(IntegrityVerificationError):
        import_model_file(source, "portable", "wrong-model", "0" * 64)
    assert not (managed_root / "portable" / "wrong-model" / "artifact.bin.staging").exists()
    with pytest.raises(EdgeStorageValidationError):
        import_model_file(source, "../outside", "model", digest)
    with pytest.raises(EdgeStorageValidationError):
        EdgeAssetInventory(tmp_path / "outside-inventory.json")
    assert remove_model_artifact("portable", "tiny-model") is True
    inventory = json.loads((managed_root / "inventory.json").read_text(encoding="utf-8"))
    assert "portable/tiny-model" not in inventory["artifacts"]


class _StreamingResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        midpoint = max(1, len(self.content) // 2)
        yield self.content[:midpoint]
        yield self.content[midpoint:]


def test_download_atomic_swap_and_rollback_on_failure(managed_root, monkeypatch):
    good = b"last known good"
    replacement = b"verified replacement"
    corrupted = b"corrupted download"
    responses = iter((_StreamingResponse(good), _StreamingResponse(replacement), _StreamingResponse(corrupted)))
    monkeypatch.setattr("uri_core.core.edge_lifecycle.downloader.requests.get", lambda *a, **k: next(responses))

    first = download_model_artifact(
        "https://models.example/asset", "portable", "reasoner",
        hashlib.sha256(good).hexdigest(),
    )
    final_path = Path(first.file_path)
    assert final_path.read_bytes() == good
    download_model_artifact(
        "https://models.example/asset", "portable", "reasoner",
        hashlib.sha256(replacement).hexdigest(),
    )
    assert final_path.read_bytes() == replacement
    with pytest.raises(IntegrityVerificationError):
        download_model_artifact(
            "https://models.example/asset", "portable", "reasoner",
            hashlib.sha256(b"expected other bytes").hexdigest(),
        )
    assert final_path.read_bytes() == replacement
    assert not final_path.with_suffix(".bin.staging").exists()
    events = (managed_root / "logs" / "network_events.jsonl").read_text(encoding="utf-8")
    assert '"checksum_result": "verified"' in events
    assert '"checksum_result": "mismatch"' in events


def test_hardware_probe_and_capacity_check(managed_root, monkeypatch):
    monkeypatch.setattr(hardware, "_gpu_capacity", lambda: ("unavailable", "unavailable", "not observable"))
    capacity = probe_hardware_capacity()
    assert capacity.logical_cpu_cores is None or capacity.logical_cpu_cores > 0
    assert capacity.total_ram_mib > 0
    assert capacity.available_ram_mib > 0
    assert capacity.free_disk_mib > 0
    assert capacity.gpu == "unavailable"
    assert capacity.vram_mib == "unavailable"
    assert can_host_model(1, 1) == (True, "capacity requirements satisfied")
    admitted, reason = can_host_model(10**30, 1)
    assert admitted is False and "disk" in reason


def test_lifecycle_state_transitions(managed_root):
    manager = LazyRuntimeStateManager("portable", "tiny")
    assert manager.load().value == "RESIDENT"
    assert manager.suspend().value == "SUSPENDED"
    assert manager.unload().value == "NOT_LOADED"
    assert manager.load(on_demand=True).value == "ON_DEMAND"
    assert manager.unload().value == "NOT_LOADED"
    with pytest.raises(RuntimeError):
        manager.load(lambda: (_ for _ in ()).throw(RuntimeError("load failed")))
    assert manager.state is RuntimeLifecycleState.FAILED
    unavailable = LazyRuntimeStateManager("missing", "missing")
    unavailable.mark_unavailable()
    observed = {state.value for state in manager.history + unavailable.history}
    assert observed == {state.value for state in RuntimeLifecycleState}


def test_network_calls_restricted_to_named_lifecycle_entry_points():
    root = Path("uri_core/core/edge_lifecycle")
    allowed = {"download_model_artifact", "detect_ollama_runtime", "detect_lmstudio_runtime"}
    found = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            if not isinstance(owner, ast.Name) or owner.id != "requests":
                continue
            current = node
            while current in parents and not isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                current = parents[current]
            assert isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)), path
            assert current.name in allowed, f"{path}:{node.lineno}"
            found.append((path.name, current.name, node.func.attr))
    assert {(name, function) for name, function, _ in found} == {
        ("detection.py", "detect_ollama_runtime"),
        ("detection.py", "detect_lmstudio_runtime"),
        ("downloader.py", "download_model_artifact"),
    }


def test_edge_core_zero_egress_remains_unweakened():
    root = Path("uri_core/core/edge")
    forbidden = {"http", "httpx", "requests", "socket", "urllib"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert imports.isdisjoint(forbidden), path


def test_telemetry_recording_no_chain_of_thought_leakage(managed_root):
    invoked = record_invocation_attempt("tiny", invoked=True, latency_ms=3.5, rss_memory_bytes=100)
    bypassed = record_invocation_attempt("vision", invoked=False, bypass_reason="resource_limit")
    assert invoked.invoked is True
    assert bypassed.bypass_reason == "resource_limit"
    log = (managed_root / "logs" / "invocations.jsonl").read_text(encoding="utf-8")
    assert "chain_of_thought" not in log
    assert "reasoning" not in log
    assert set(json.loads(log.splitlines()[0])) == {
        "timestamp", "model_id", "invoked", "bypass_reason", "latency_ms", "rss_memory_bytes",
    }


def test_still_excluded_operations_remain_unreachable():
    root = Path("uri_core/core/edge_lifecycle")
    forbidden_imports = {"winreg", "subprocess", "ctypes"}
    forbidden_calls = {"chmod", "putenv", "system", "popen"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert {alias.name.split(".")[0] for alias in node.names}.isdisjoint(forbidden_imports)
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden_imports
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
