"""Path confinement for URI-managed Edge assets."""
from __future__ import annotations

import os
import re
from pathlib import Path


DEFAULT_EDGE_MODEL_ROOT = Path("uri_workspace/edge_models")
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class EdgeStorageValidationError(ValueError):
    pass


def _validated_component(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_COMPONENT.fullmatch(value):
        raise EdgeStorageValidationError(f"invalid {label}")
    if value in {".", ".."}:
        raise EdgeStorageValidationError(f"invalid {label}")
    return value


def storage_root(*, create: bool = False) -> Path:
    root = DEFAULT_EDGE_MODEL_ROOT.resolve()
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def confined_path(*parts: str, create_parent: bool = False) -> Path:
    root = storage_root(create=create_parent)
    candidate = root.joinpath(*parts).resolve()
    try:
        confined = os.path.commonpath((str(root), str(candidate))) == str(root)
    except ValueError as exc:
        raise EdgeStorageValidationError("asset path is outside URI storage") from exc
    if not confined or candidate == root:
        raise EdgeStorageValidationError("asset path is outside URI storage")
    if create_parent:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def model_directory(runtime_id: str, model_id: str, *, create: bool = False) -> Path:
    runtime = _validated_component(runtime_id, "runtime_id")
    model = _validated_component(model_id, "model_id")
    directory = confined_path(runtime, model)
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def artifact_path(runtime_id: str, model_id: str, *, create_parent: bool = False) -> Path:
    directory = model_directory(runtime_id, model_id, create=create_parent)
    return confined_path(directory.relative_to(storage_root()).as_posix(), "artifact.bin")


def assert_confined(path: Path) -> Path:
    root = storage_root()
    resolved = path.resolve()
    try:
        confined = os.path.commonpath((str(root), str(resolved))) == str(root)
    except ValueError as exc:
        raise EdgeStorageValidationError("asset path is outside URI storage") from exc
    if not confined or resolved == root:
        raise EdgeStorageValidationError("asset path is outside URI storage")
    return resolved
