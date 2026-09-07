"""M18: the smallest SAFE foundation for installing external (e.g.
GitHub) skills.

The audit found URI has a capability registry + dispatcher, but the
dispatcher blindly imports and executes whatever a registry entry points
at (fully trusted, no validation), the one code-writing primitive
(hermes_forge) writes raw executable Python with no checks, and there is
NO import / validation / version-tracking / enable-disable / safe-
execution story for third-party skills. This module supplies that
missing foundation WITHOUT duplicating the existing registry/dispatcher:

  1. Discovery/import: a skill is imported from a local checkout
     directory (a GitHub clone is just such a directory - fetching over
     the network is a thin adapter a caller supplies; this core never
     reaches out on its own).
  2. Validation BEFORE installation: a static manifest + file check.
     Nothing is imported or executed to validate it.
  3. Controlled installation: a validated skill is recorded in an
     install ledger with status "quarantined" - installed and tracked,
     but NOT yet runnable. It is deliberately never auto-written into
     capabilities_registry.json (the live dispatcher's trusted set), so
     importing a skill can never, by itself, make untrusted code
     executable.
  4. Version/source tracking: source, version, and a content digest are
     recorded, so what is installed and where it came from is always
     known and update can detect a change.
  5. Lifecycle: enable / disable / remove / update, all metadata-only.
  6. Dependency & capability tracking: the manifest's declared
     dependencies and capabilities are recorded and surfaced.
  7. Runtime validation & failure reporting: every operation returns a
     structured result; a rejected skill reports exactly why.
  8. Safe, non-trusted execution boundary: THIS module never imports,
     executes, evals, or dynamically loads skill code. Promoting a
     skill from "enabled here" to "registered in the dispatcher" is a
     separate, explicit, human-gated step that lives outside this
     module by design. A skill is data until a human decides otherwise.

A skill is advisory infrastructure like every other M18 store: it can
never override Soul, the operating policy, authorization, or a safety
boundary, and being "installed" grants it nothing at runtime on its own.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"

# Lifecycle states. A skill is "quarantined" the moment it is installed
# and stays there until a human explicitly enables it; even "enabled"
# only means "the operator has vouched for it here", never "the runtime
# will execute it" - that remains a separate registry step.
STATUS_QUARANTINED = "quarantined"
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"

VALID_STATUSES = {STATUS_QUARANTINED, STATUS_ENABLED, STATUS_DISABLED}

# Manifest fields a skill package MUST declare. Kept minimal - this is a
# foundation, not a full package spec.
REQUIRED_MANIFEST_FIELDS = ("name", "version", "entrypoint", "capabilities")

# Bounds so a hostile package can never exhaust resources during the
# static check.
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ENTRYPOINT_BYTES = 2 * 1024 * 1024
MANIFEST_FILENAME = "skill.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ValidationResult:
    valid: bool
    reasons: List[str] = field(default_factory=list)
    manifest: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "reasons": list(self.reasons),
        }


class SkillValidator:
    """Static, execution-free validation of a skill checkout directory.
    It reads the manifest and confirms the declared entrypoint file
    exists and is contained within the package - it NEVER imports or runs
    anything. A failure lists every reason, so 'why was this rejected?'
    is always answerable."""

    def validate(self, package_dir: str) -> ValidationResult:
        reasons: List[str] = []

        if not package_dir or not os.path.isdir(package_dir):
            return ValidationResult(False, ["Package directory does not exist."])

        manifest_path = os.path.join(package_dir, MANIFEST_FILENAME)
        if not os.path.isfile(manifest_path):
            return ValidationResult(
                False, [f"Missing {MANIFEST_FILENAME} manifest at package root."]
            )

        try:
            if os.path.getsize(manifest_path) > MAX_MANIFEST_BYTES:
                return ValidationResult(False, ["Manifest is implausibly large."])
        except OSError as exc:
            return ValidationResult(False, [f"Manifest not readable: {exc}"])

        try:
            with open(manifest_path, "r", encoding="utf-8-sig") as handle:
                manifest = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            return ValidationResult(False, [f"Manifest is not valid JSON: {exc}"])

        if not isinstance(manifest, dict):
            return ValidationResult(False, ["Manifest must be a JSON object."])

        for missing in REQUIRED_MANIFEST_FIELDS:
            if missing not in manifest:
                reasons.append(f"Manifest missing required field: {missing}.")

        # Structural checks on the fields that are present.
        capabilities = manifest.get("capabilities")
        if capabilities is not None and not isinstance(capabilities, list):
            reasons.append("Manifest 'capabilities' must be a list.")

        dependencies = manifest.get("dependencies", [])
        if dependencies is not None and not isinstance(dependencies, list):
            reasons.append("Manifest 'dependencies' must be a list.")

        entrypoint = manifest.get("entrypoint")
        if isinstance(entrypoint, str) and entrypoint:
            # The entrypoint must resolve INSIDE the package - never an
            # absolute path or a "../" escape that could point at
            # arbitrary files on the host.
            if os.path.isabs(entrypoint) or ".." in entrypoint.replace("\\", "/").split("/"):
                reasons.append("Manifest 'entrypoint' must be a path inside the package.")
            else:
                entry_path = os.path.realpath(os.path.join(package_dir, entrypoint))
                root = os.path.realpath(package_dir)
                if not entry_path.startswith(root + os.sep):
                    reasons.append("Manifest 'entrypoint' resolves outside the package.")
                elif not os.path.isfile(entry_path):
                    reasons.append("Manifest 'entrypoint' file does not exist.")
                else:
                    try:
                        if os.path.getsize(entry_path) > MAX_ENTRYPOINT_BYTES:
                            reasons.append("Entrypoint file is implausibly large.")
                    except OSError:
                        reasons.append("Entrypoint file is not readable.")
        elif entrypoint is not None:
            reasons.append("Manifest 'entrypoint' must be a non-empty string.")

        return ValidationResult(
            valid=not reasons,
            reasons=reasons,
            manifest=manifest if not reasons else None,
        )


def _digest_of_dir(package_dir: str) -> str:
    """A stable content digest over the package's files, so an update can
    detect that the source content actually changed. Never executes;
    only reads bytes. Bounded traversal."""
    hasher = hashlib.sha256()
    root = os.path.realpath(package_dir)
    for current, _dirs, files in os.walk(root):
        for name in sorted(files):
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace("\\", "/")
            hasher.update(rel.encode("utf-8"))
            try:
                with open(path, "rb") as handle:
                    hasher.update(handle.read(MAX_ENTRYPOINT_BYTES))
            except OSError:
                continue
    return hasher.hexdigest()


class InstalledSkillStore:
    """The install ledger - one JSON file recording every installed
    skill's source, version, digest, status, declared capabilities and
    dependencies, and validation report. Mirrors the persistence
    discipline of the other stores (schema-versioned, safe
    degrade-to-empty). This is NOT the capability registry the dispatcher
    reads; it is a separate, quarantined ledger, which is exactly what
    keeps an installed-but-unvetted skill out of the trusted execution
    path."""

    def __init__(self, storage_path: str = "uri_workspace/installed_skills.json"):
        self.storage_path = os.path.normpath(storage_path)

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.storage_path):
            return {"schema_version": SCHEMA_VERSION, "skills": {}}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {"schema_version": SCHEMA_VERSION, "skills": {}}
        if not isinstance(data, dict) or not isinstance(data.get("skills"), dict):
            return {"schema_version": SCHEMA_VERSION, "skills": {}}
        return data

    def _save(self, data: Dict[str, Any]) -> None:
        folder = os.path.dirname(self.storage_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def get(self, skill_id: str) -> Optional[Dict[str, Any]]:
        return self._load().get("skills", {}).get(skill_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._load().get("skills", {}).values())

    def put(self, record: Dict[str, Any]) -> None:
        data = self._load()
        data["skills"][record["id"]] = record
        self._save(data)

    def remove(self, skill_id: str) -> bool:
        data = self._load()
        if skill_id in data.get("skills", {}):
            del data["skills"][skill_id]
            self._save(data)
            return True
        return False


@dataclass
class InstallResult:
    ok: bool
    skill_id: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "skill_id": self.skill_id,
            "status": self.status,
            "detail": self.detail,
            "validation": self.validation,
        }


class SkillInstaller:
    """The controlled lifecycle over installed skills. Every install is
    validated first and lands quarantined; enable/disable/update/remove
    are metadata-only. Nothing here ever imports or runs skill code."""

    def __init__(
        self,
        store: Optional[InstalledSkillStore] = None,
        validator: Optional[SkillValidator] = None,
    ):
        self.store = store or InstalledSkillStore()
        self.validator = validator or SkillValidator()

    def install_from_path(
        self,
        package_dir: str,
        *,
        source: str = "local",
    ) -> InstallResult:
        """Validate a skill checkout and, only if it passes, record it as
        QUARANTINED. Source (e.g. a GitHub URL) and version come from the
        manifest and caller; a content digest is stored so a later update
        can tell whether anything changed. A validation failure installs
        NOTHING and reports every reason."""

        result = self.validator.validate(package_dir)
        if not result.valid:
            return InstallResult(
                ok=False,
                detail="Skill failed validation and was not installed.",
                validation=result.to_dict(),
            )

        manifest = result.manifest or {}
        skill_id = str(manifest.get("name"))
        record = {
            "id": skill_id,
            "name": manifest.get("name"),
            "version": manifest.get("version"),
            "source": source,
            "digest": _digest_of_dir(package_dir),
            "status": STATUS_QUARANTINED,
            "capabilities": manifest.get("capabilities", []),
            "dependencies": manifest.get("dependencies", []),
            "entrypoint": manifest.get("entrypoint"),
            "validation": result.to_dict(),
            "installed_at": _now(),
            "updated_at": _now(),
        }
        self.store.put(record)
        return InstallResult(
            ok=True,
            skill_id=skill_id,
            status=STATUS_QUARANTINED,
            detail="Skill installed in quarantine; enable it explicitly to vouch for it.",
            validation=result.to_dict(),
        )

    def set_status(self, skill_id: str, status: str) -> InstallResult:
        if status not in VALID_STATUSES:
            return InstallResult(ok=False, detail=f"Unknown status: {status}.")
        record = self.store.get(skill_id)
        if record is None:
            return InstallResult(ok=False, detail="Skill is not installed.")
        record["status"] = status
        record["updated_at"] = _now()
        self.store.put(record)
        return InstallResult(ok=True, skill_id=skill_id, status=status)

    def enable(self, skill_id: str) -> InstallResult:
        return self.set_status(skill_id, STATUS_ENABLED)

    def disable(self, skill_id: str) -> InstallResult:
        return self.set_status(skill_id, STATUS_DISABLED)

    def remove(self, skill_id: str) -> InstallResult:
        removed = self.store.remove(skill_id)
        if not removed:
            return InstallResult(ok=False, detail="Skill is not installed.")
        return InstallResult(ok=True, skill_id=skill_id, detail="Skill removed.")

    def update_from_path(
        self,
        package_dir: str,
        *,
        source: Optional[str] = None,
    ) -> InstallResult:
        """Re-validate a skill's new checkout and, if it passes, update
        its record - preserving its current enable/disable status but
        refreshing version/digest/capabilities. Reports when the content
        digest is unchanged so a no-op update is honest rather than
        silently claiming success."""

        result = self.validator.validate(package_dir)
        if not result.valid:
            return InstallResult(
                ok=False,
                detail="Updated skill failed validation; nothing was changed.",
                validation=result.to_dict(),
            )
        manifest = result.manifest or {}
        skill_id = str(manifest.get("name"))
        existing = self.store.get(skill_id)
        if existing is None:
            return InstallResult(ok=False, detail="Skill is not installed; use install.")

        new_digest = _digest_of_dir(package_dir)
        unchanged = new_digest == existing.get("digest")

        existing["version"] = manifest.get("version")
        existing["digest"] = new_digest
        existing["capabilities"] = manifest.get("capabilities", [])
        existing["dependencies"] = manifest.get("dependencies", [])
        existing["entrypoint"] = manifest.get("entrypoint")
        existing["validation"] = result.to_dict()
        if source is not None:
            existing["source"] = source
        existing["updated_at"] = _now()
        self.store.put(existing)

        return InstallResult(
            ok=True,
            skill_id=skill_id,
            status=existing["status"],
            detail="Skill content unchanged." if unchanged else "Skill updated.",
        )

    def list_installed(self) -> List[Dict[str, Any]]:
        return self.store.list_all()
