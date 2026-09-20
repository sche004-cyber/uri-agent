"""Read-only discovery of already-installed loopback model runtimes."""
from __future__ import annotations

import ipaddress
import shutil
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from .inventory import EdgeAssetInventory, default_inventory
from .models import DetectedModelRecord, EndpointDetail, RuntimeDetectionRecord
from .telemetry import record_network_event


OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/tags"
LMSTUDIO_ENDPOINT = "http://127.0.0.1:1234/v1/models"


class NonLoopbackEndpointError(ValueError):
    pass


def assert_loopback_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise NonLoopbackEndpointError("runtime endpoint must be an HTTP loopback URL")
    host = parsed.hostname.casefold()
    if host == "localhost":
        return parsed.hostname
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError as exc:
        raise NonLoopbackEndpointError("runtime endpoint must name localhost or a loopback address") from exc
    if not is_loopback:
        raise NonLoopbackEndpointError("runtime endpoint must name localhost or a loopback address")
    return parsed.hostname


class _RedirectRejected(requests.RequestException):
    pass


def _reject_redirects(response: "requests.Response") -> None:
    if 300 <= response.status_code < 400 or response.is_redirect or response.is_permanent_redirect:
        raise _RedirectRejected("loopback endpoint returned a redirect; refusing to follow off-host")


def _unreachable_record(runtime_id: str, url: str, executable: str, detail: str) -> RuntimeDetectionRecord:
    status = "found_unreachable" if shutil.which(executable) else "not_found"
    return RuntimeDetectionRecord(
        status=status, runtime_id=runtime_id, version=None, models_detected=(),
        endpoint=EndpointDetail(url=url, host=urlparse(url).hostname or "", reachable=False, detail=detail),
    )


def _ollama_models(payload: Dict[str, Any]) -> Tuple[DetectedModelRecord, ...]:
    models = []
    for item in payload.get("models", []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        name = item["name"]
        tag = name.rsplit(":", 1)[1] if ":" in name else None
        size = item.get("size") if isinstance(item.get("size"), int) else None
        digest = item.get("digest") if isinstance(item.get("digest"), str) else None
        models.append(DetectedModelRecord(name, tag=tag, byte_size=size, digest=digest))
    return tuple(models)


def detect_ollama_runtime(
    endpoint: str = OLLAMA_ENDPOINT, *, timeout_seconds: float = 2.0,
    inventory: Optional[EdgeAssetInventory] = None,
) -> RuntimeDetectionRecord:
    host = assert_loopback_url(endpoint)
    byte_count = 0
    try:
        response = requests.get(endpoint, timeout=timeout_seconds, allow_redirects=False)
        byte_count = len(response.content)
        _reject_redirects(response)
        response.raise_for_status()
        payload = response.json()
        record = RuntimeDetectionRecord(
            status="found_reachable", runtime_id="ollama",
            version=response.headers.get("Ollama-Version") or payload.get("version"),
            models_detected=_ollama_models(payload),
            endpoint=EndpointDetail(endpoint, host, True),
        )
        network_status, detail = "success", None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        record = _unreachable_record("ollama", endpoint, "ollama", type(exc).__name__)
        network_status, detail = "failed", type(exc).__name__
    record_network_event(
        url=endpoint, purpose="detect_ollama_runtime", byte_count=byte_count,
        checksum_result="not_applicable", status=network_status, detail=detail,
    )
    (inventory or default_inventory()).record_detection(record)
    return record


def detect_lmstudio_runtime(
    endpoint: str = LMSTUDIO_ENDPOINT, *, timeout_seconds: float = 2.0,
    inventory: Optional[EdgeAssetInventory] = None,
) -> RuntimeDetectionRecord:
    host = assert_loopback_url(endpoint)
    byte_count = 0
    try:
        response = requests.get(endpoint, timeout=timeout_seconds, allow_redirects=False)
        byte_count = len(response.content)
        _reject_redirects(response)
        response.raise_for_status()
        payload = response.json()
        models = tuple(
            DetectedModelRecord(item["id"])
            for item in payload.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        record = RuntimeDetectionRecord(
            status="found_reachable", runtime_id="lmstudio",
            version=response.headers.get("Server-Version"), models_detected=models,
            endpoint=EndpointDetail(endpoint, host, True),
        )
        network_status, detail = "success", None
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        record = _unreachable_record("lmstudio", endpoint, "lms", type(exc).__name__)
        network_status, detail = "failed", type(exc).__name__
    record_network_event(
        url=endpoint, purpose="detect_lmstudio_runtime", byte_count=byte_count,
        checksum_result="not_applicable", status=network_status, detail=detail,
    )
    (inventory or default_inventory()).record_detection(record)
    return record
