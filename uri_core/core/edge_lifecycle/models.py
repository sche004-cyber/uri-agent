"""Immutable observation records for the Edge asset lifecycle.

These records describe local assets and host observations.  They do not grant
execution authority and are never used to promote a model into routing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union


UnavailableMetric = Union[int, float, str]


@dataclass(frozen=True)
class EndpointDetail:
    url: str
    host: str
    reachable: bool
    detail: Optional[str] = None


@dataclass(frozen=True)
class DetectedModelRecord:
    model_id: str
    tag: Optional[str] = None
    byte_size: Optional[int] = None
    digest: Optional[str] = None


@dataclass(frozen=True)
class RuntimeDetectionRecord:
    status: str
    runtime_id: str
    version: Optional[str]
    models_detected: Tuple[DetectedModelRecord, ...]
    endpoint: EndpointDetail


@dataclass(frozen=True)
class ModelArtifactRecord:
    artifact_id: str
    content_hash: str
    model_id: str
    runtime_id: str
    file_path: str
    byte_size: int
    source_type: str
    source: str
    version: Optional[str] = None
    license: str = "unknown"
    verified_at: Optional[str] = None


@dataclass(frozen=True)
class HardwareCapacityRecord:
    physical_cpu_cores: Optional[int]
    logical_cpu_cores: Optional[int]
    architecture: str
    cpu_frequency_mhz: Optional[float]
    total_ram_mib: float
    available_ram_mib: float
    free_disk_mib: float
    gpu: str
    vram_mib: UnavailableMetric
    gpu_detail: Optional[str] = None


@dataclass(frozen=True)
class InvocationTelemetryRecord:
    timestamp: str
    model_id: str
    invoked: bool
    bypass_reason: Optional[str]
    latency_ms: Optional[float]
    rss_memory_bytes: Optional[int]


@dataclass(frozen=True)
class LifecycleEventRecord:
    timestamp: str
    event: str
    status: str
    runtime_id: Optional[str] = None
    model_id: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)
