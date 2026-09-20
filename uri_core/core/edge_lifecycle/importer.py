"""Import user-supplied model files into URI-controlled storage."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .integrity import copy_and_hash, verify_digest
from .inventory import default_inventory
from .models import ModelArtifactRecord
from .storage import artifact_path
from .telemetry import record_lifecycle_event, utc_timestamp


def import_model_file(
    source_path: Path, runtime_id: str, model_id: str,
    expected_sha256: Optional[str] = None,
) -> ModelArtifactRecord:
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError("model source file does not exist or is not accessible")
    destination = artifact_path(runtime_id, model_id, create_parent=True)
    staging = destination.with_suffix(destination.suffix + ".staging")
    try:
        with source.open("rb") as reader, staging.open("wb") as writer:
            digest, byte_count = copy_and_hash(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
        if expected_sha256 is not None:
            verify_digest(digest, expected_sha256)
        os.replace(staging, destination)
    except Exception as exc:
        staging.unlink(missing_ok=True)
        record_lifecycle_event(
            "import_model_file", "failed", runtime_id=runtime_id, model_id=model_id,
            detail={"error": type(exc).__name__},
        )
        raise
    record = ModelArtifactRecord(
        artifact_id=f"sha256:{digest}", content_hash=digest, model_id=model_id,
        runtime_id=runtime_id, file_path=str(destination), byte_size=byte_count,
        source_type="local_path", source=str(source.resolve()), verified_at=utc_timestamp(),
    )
    default_inventory().register_artifact(record)
    record_lifecycle_event(
        "import_model_file", "verified", runtime_id=runtime_id, model_id=model_id,
        detail={"byte_count": byte_count, "content_hash": digest},
    )
    return record
