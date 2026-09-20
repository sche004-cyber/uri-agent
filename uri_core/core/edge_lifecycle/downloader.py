"""Explicit URI-managed downloads with verify-before-swap semantics."""
from __future__ import annotations

import os
import shutil
from typing import Optional
from urllib.parse import urlparse

import requests

from .integrity import IntegrityVerificationError, normalize_sha256
from .inventory import default_inventory
from .models import ModelArtifactRecord
from .storage import artifact_path, assert_confined, model_directory
from .telemetry import record_lifecycle_event, record_network_event, utc_timestamp


def download_model_artifact(
    url: str, runtime_id: str, model_id: str, expected_sha256: str,
) -> ModelArtifactRecord:
    expected = normalize_sha256(expected_sha256)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("download URL must use HTTP or HTTPS")
    destination = artifact_path(runtime_id, model_id, create_parent=True)
    staging = destination.with_suffix(destination.suffix + ".staging")
    byte_count = 0
    actual: Optional[str] = None
    try:
        import hashlib
        digest = hashlib.sha256()
        with requests.get(url, stream=True, timeout=(5.0, 60.0)) as response:
            response.raise_for_status()
            with staging.open("wb") as writer:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    writer.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)
                writer.flush()
                os.fsync(writer.fileno())
        actual = digest.hexdigest()
        if actual != expected:
            raise IntegrityVerificationError("SHA-256 mismatch")
        os.replace(staging, destination)
    except Exception as exc:
        staging.unlink(missing_ok=True)
        checksum = "mismatch" if actual is not None and actual != expected else "not_verified"
        record_network_event(
            url=url, purpose="download_model_artifact", byte_count=byte_count,
            checksum_result=checksum, status="failed", detail=type(exc).__name__,
        )
        record_lifecycle_event(
            "download_model_artifact", "failed", runtime_id=runtime_id, model_id=model_id,
            detail={"error": type(exc).__name__, "last_known_good_preserved": destination.exists()},
        )
        raise
    record = ModelArtifactRecord(
        artifact_id=f"sha256:{actual}", content_hash=actual, model_id=model_id,
        runtime_id=runtime_id, file_path=str(destination), byte_size=byte_count,
        source_type="url", source=url, verified_at=utc_timestamp(),
    )
    default_inventory().register_artifact(record)
    record_network_event(
        url=url, purpose="download_model_artifact", byte_count=byte_count,
        checksum_result="verified", status="success",
    )
    record_lifecycle_event(
        "download_model_artifact", "verified", runtime_id=runtime_id, model_id=model_id,
        detail={"byte_count": byte_count, "content_hash": actual},
    )
    return record


def remove_model_artifact(runtime_id: str, model_id: str) -> bool:
    directory = assert_confined(model_directory(runtime_id, model_id))
    existed = directory.exists()
    if existed:
        if directory.is_symlink():
            directory.unlink()
        else:
            shutil.rmtree(directory)
    deregistered = default_inventory().deregister_artifact(runtime_id, model_id)
    record_lifecycle_event(
        "remove_model_artifact", "removed" if existed or deregistered else "not_found",
        runtime_id=runtime_id, model_id=model_id,
    )
    return existed or deregistered
