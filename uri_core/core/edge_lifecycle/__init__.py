"""URI-managed user-space lifecycle for Edge model assets.

The package is intentionally sibling to :mod:`uri_core.core.edge`: network
egress exists only in named detection/download entry points here, while the
Edge inference and benchmark package remains offline-only.
"""
from .detection import (
    NonLoopbackEndpointError,
    assert_loopback_url,
    detect_lmstudio_runtime,
    detect_ollama_runtime,
)
from .downloader import download_model_artifact, remove_model_artifact
from .edge_pack import DEVELOPMENT_EDGE_PACK, inspect_development_edge_pack
from .hardware import can_host_model, probe_hardware_capacity
from .importer import import_model_file
from .integrity import IntegrityVerificationError, sha256_file
from .inventory import EdgeAssetInventory
from .models import HardwareCapacityRecord, ModelArtifactRecord, RuntimeDetectionRecord
from .state_manager import LazyRuntimeStateManager, RuntimeLifecycleState
from .storage import DEFAULT_EDGE_MODEL_ROOT, EdgeStorageValidationError
from .telemetry import record_invocation_attempt

__all__ = [
    "DEFAULT_EDGE_MODEL_ROOT",
    "DEVELOPMENT_EDGE_PACK",
    "EdgeAssetInventory",
    "EdgeStorageValidationError",
    "HardwareCapacityRecord",
    "IntegrityVerificationError",
    "LazyRuntimeStateManager",
    "ModelArtifactRecord",
    "NonLoopbackEndpointError",
    "RuntimeDetectionRecord",
    "RuntimeLifecycleState",
    "assert_loopback_url",
    "can_host_model",
    "detect_lmstudio_runtime",
    "detect_ollama_runtime",
    "download_model_artifact",
    "import_model_file",
    "inspect_development_edge_pack",
    "probe_hardware_capacity",
    "record_invocation_attempt",
    "remove_model_artifact",
    "sha256_file",
]
