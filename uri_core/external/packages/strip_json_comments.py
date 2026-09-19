"""Reviewed lifecycle for the single M33.1 Batch 3 package acceptance case.

This is deliberately *not* an ecosystem package manager.  Both accepted
revisions, their developer-reviewed manifests/locks, the executable layout,
and the one capability projection are static code.  Repository metadata is
never parsed as authority and callers cannot supply a package name, revision,
installer command, executable, path, or argv.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from uri_core.external.descriptors.strip_json_comments import (
    PACKAGE_NAME,
    V2_REVISION,
    V3_REVISION,
    strip_json_comments_descriptor,
)
from uri_core.external.runtime_lifecycle import (
    remove_and_refresh as generic_remove_and_refresh,
    register_and_refresh,
    replace_qualified_and_refresh,
)

_ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "package_artifacts" / "strip_json_comments"
_REVISIONS = {
    V2_REVISION: "v2.0.2",
    V3_REVISION: "v3.0.0",
}


class PackageQualificationError(ValueError):
    """The static reviewed package artifact cannot be safely staged."""


@dataclass(frozen=True)
class StagedPackage:
    revision: str
    lock_sha256: str
    path: Path

    @property
    def dependency_lock(self) -> Mapping[str, str]:
        return {
            "package": PACKAGE_NAME,
            "revision": self.revision,
            "lock_sha256": self.lock_sha256,
        }


def _reviewed_source(revision: str) -> Path:
    try:
        name = _REVISIONS[revision]
    except KeyError as exc:
        raise PackageQualificationError("unreviewed package revision") from exc
    source = _ARTIFACT_ROOT / name
    if not (source / "package.json").is_file() or not (source / "package-lock.json").is_file():
        raise PackageQualificationError("reviewed package artifact is incomplete")
    return source


def _read_and_validate_lock(source: Path, revision: str) -> tuple[bytes, Mapping[str, Any]]:
    raw = (source / "package-lock.json").read_bytes()
    try:
        lock = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageQualificationError("reviewed lockfile is corrupt") from exc
    if not isinstance(lock, Mapping) or lock.get("lockfileVersion") != 3:
        raise PackageQualificationError("reviewed lockfile version is unsupported")
    packages = lock.get("packages")
    if not isinstance(packages, Mapping) or not isinstance(packages.get(""), Mapping):
        raise PackageQualificationError("reviewed lockfile has no root package")
    expected_version = _REVISIONS[revision].removeprefix("v")
    root_dependencies = packages[""].get("dependencies")
    if root_dependencies != {PACKAGE_NAME: expected_version}:
        raise PackageQualificationError("reviewed root dependency does not match pinned revision")
    for package_path, package in packages.items():
        if not package_path:
            continue
        if not isinstance(package, Mapping):
            raise PackageQualificationError("reviewed lockfile contains malformed package entry")
        resolved, integrity = package.get("resolved"), package.get("integrity")
        if not (
            isinstance(resolved, str)
            and resolved.startswith("https://registry.npmjs.org/")
            and isinstance(integrity, str)
            and integrity.startswith("sha512-")
        ):
            raise PackageQualificationError("reviewed lockfile lacks npm integrity metadata")
    return raw, lock


def _staging_npm_environment(staging: Path) -> Mapping[str, str]:
    """Give npm only OS launch variables plus a staging-local npm identity.

    In particular, do not inherit the real user home, npmrc, token, cache, or
    proxy configuration into third-party package installation.
    """
    home = staging / ".npm-home"
    appdata = staging / ".npm-appdata"
    localappdata = staging / ".npm-localappdata"
    cache = staging / ".npm-cache"
    for directory in (home, appdata, localappdata, cache):
        directory.mkdir(exist_ok=True)
    env = {"PATH": os.environ.get("PATH", ""), "NO_UPDATE_NOTIFIER": "1"}
    for name in ("SYSTEMROOT", "ComSpec", "PATHEXT", "WINDIR"):
        value = os.environ.get(name)
        if value:
            env[name] = value
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(appdata),
        "LOCALAPPDATA": str(localappdata),
        "NPM_CONFIG_USERCONFIG": str(staging / ".npmrc"),
        "NPM_CONFIG_CACHE": str(cache),
        "NPM_CONFIG_AUDIT": "false",
        "NPM_CONFIG_FUND": "false",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false",
    })
    return env


def _fixed_executable(name: str) -> Path:
    executable = shutil.which(name)
    if not executable:
        raise PackageQualificationError(f"required fixed runtime {name!r} is unavailable")
    path = Path(executable).resolve()
    if not path.is_file():
        raise PackageQualificationError(f"required fixed runtime {name!r} is invalid")
    return path


def _artifact_path_from_record(record: Mapping[str, Any] | None) -> Path | None:
    """Extract only this descriptor's developer-authored staged path."""
    if not isinstance(record, Mapping):
        return None
    descriptor = record.get("descriptor")
    if not isinstance(descriptor, Mapping) or descriptor.get("id") != "skill.strip_json_comments":
        return None
    config = descriptor.get("transport_config")
    command = config.get("command") if isinstance(config, Mapping) else None
    if not isinstance(command, list) or len(command) != 5:
        return None
    artifact = command[-2]
    if not isinstance(artifact, str):
        return None
    return Path(artifact).resolve()


def _artifact_is_referenced(*, state_root: str, artifact: Path) -> bool:
    """Fail closed: corrupt/unknown user state means retain the shared cache."""
    root = Path(state_root).resolve()
    try:
        user_dirs = list(root.iterdir())
    except OSError:
        return True
    for user_dir in user_dirs:
        if not user_dir.is_dir():
            continue
        try:
            uuid.UUID(user_dir.name)
        except ValueError:
            continue
        state_path = user_dir / "external_capabilities.json"
        if not state_path.exists():
            continue
        try:
            document = json.loads(state_path.read_text(encoding="utf-8"))
            records = document.get("capabilities", {})
            if not isinstance(records, Mapping):
                return True
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return True
        for record in records.values():
            if _artifact_path_from_record(record) == artifact:
                return True
    return False


def _garbage_collect_if_unreferenced(*, state_root: str, artifact: Path | None) -> None:
    if artifact is None or _artifact_is_referenced(state_root=state_root, artifact=artifact):
        return
    cache_root = Path(state_root).resolve() / "external_artifact_cache" / PACKAGE_NAME
    try:
        artifact.relative_to(cache_root)
    except ValueError:
        return
    # The target is a content-addressed immutable cache leaf, never a user
    # state directory.  Failure leaves harmless cache data; it never affects
    # the already-completed lifecycle mutation.
    shutil.rmtree(artifact, ignore_errors=True)


def stage_install(
    *, state_root: str, revision: str, npm_executable: str | None = None,
) -> StagedPackage:
    """Install one reviewed closure into an immutable shared cache.

    The sole installation command is ``npm ci --ignore-scripts --omit=dev``.
    It runs only in a fresh staging directory; a successful, validated tree is
    atomically renamed to its lock-hash address and is never mutated in place.
    """
    source = _reviewed_source(revision)
    lock_bytes, _lock = _read_and_validate_lock(source, revision)
    lock_sha256 = hashlib.sha256(lock_bytes).hexdigest()
    cache_root = Path(state_root).resolve() / "external_artifact_cache" / PACKAGE_NAME / revision
    target = cache_root / lock_sha256
    cli_path = target / "node_modules" / PACKAGE_NAME / "cli.js"
    if cli_path.is_file():
        return StagedPackage(revision=revision, lock_sha256=lock_sha256, path=target)
    cache_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=str(cache_root)))
    try:
        shutil.copy2(source / "package.json", staging / "package.json")
        shutil.copy2(source / "package-lock.json", staging / "package-lock.json")
        # PowerShell exposes npm as npm.ps1, which CreateProcess cannot run
        # with shell=False.  npm.cmd is the same fixed npm executable on
        # Windows; POSIX uses npm directly.  Neither is descriptor input.
        npm_command = npm_executable or str(_fixed_executable("npm.cmd" if os.name == "nt" else "npm"))
        completed = subprocess.run(
            [npm_command, "ci", "--ignore-scripts", "--omit=dev"],
            cwd=str(staging),
            text=True,
            capture_output=True,
            timeout=120,
            shell=False,
            check=False,
            env=_staging_npm_environment(staging),
        )
        if completed.returncode != 0:
            raise PackageQualificationError("reviewed package staging failed")
        staged_cli = staging / "node_modules" / PACKAGE_NAME / "cli.js"
        if not staged_cli.is_file():
            raise PackageQualificationError("reviewed package staging produced no fixed CLI")
        try:
            os.replace(staging, target)
        except FileExistsError:
            # Another user/process completed the same immutable artifact first.
            if not cli_path.is_file():
                raise PackageQualificationError("immutable artifact publication conflicted")
        return StagedPackage(revision=revision, lock_sha256=lock_sha256, path=target)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def install_and_register(context: Any, user_id: str, *, revision: str) -> Any:
    """Stage a reviewed package then persist its initially-disabled descriptor."""
    with context.external_lifecycle_lock:
        staged = stage_install(state_root=context.external_capability_store.root, revision=revision)
        descriptor = strip_json_comments_descriptor(
            artifact_path=staged.path,
            node_executable=_fixed_executable("node.exe" if os.name == "nt" else "node"),
            source_revision=revision,
        )
        return register_and_refresh(
            context, user_id, descriptor, source_revision=revision, dependency_lock=staged.dependency_lock
        )


def update_and_refresh(context: Any, user_id: str, *, revision: str) -> Any:
    """Stage and validate a new immutable revision before atomically activating it."""
    with context.external_lifecycle_lock:
        prior = context.external_capability_store.get(user_id, "skill.strip_json_comments")
        prior_artifact = _artifact_path_from_record(prior)
        staged = stage_install(state_root=context.external_capability_store.root, revision=revision)
        descriptor = strip_json_comments_descriptor(
            artifact_path=staged.path,
            node_executable=_fixed_executable("node.exe" if os.name == "nt" else "node"),
            source_revision=revision,
        )
        result = replace_qualified_and_refresh(
            context, user_id, descriptor, source_revision=revision, dependency_lock=staged.dependency_lock
        )
        if result.ok:
            _garbage_collect_if_unreferenced(
                state_root=context.external_capability_store.root, artifact=prior_artifact
            )
        return result


def remove_and_refresh(context: Any, user_id: str) -> bool:
    """Hard-remove this user's package record then collect only unreferenced cache data."""
    with context.external_lifecycle_lock:
        prior = context.external_capability_store.get(user_id, "skill.strip_json_comments")
        artifact = _artifact_path_from_record(prior)
        removed = generic_remove_and_refresh(context, user_id, "skill.strip_json_comments")
        if removed:
            _garbage_collect_if_unreferenced(
                state_root=context.external_capability_store.root, artifact=artifact
            )
        return removed
