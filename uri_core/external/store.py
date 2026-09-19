"""M33 Batch A — the external-capability store: ties a validated
descriptor, its qualification record, and its lifecycle state together,
one JSON file per user, via `portable_paths.user_scoped_path` (the same
strict-UUID-validated, per-user directory every other user-scoped store
in this repository uses).

Writes are atomic (temp file in the same directory + `os.replace`),
unlike `ConversationHistoryStore`'s plain `open(path, "w")` pattern —
an interrupted write must never corrupt this store, mirroring the
discipline the blueprint's D5 requires for Batch C's evidence/operation
stores, applied here too since the same failure mode (partial write on
crash) is possible for any durable store, not only Batch C's.

Nothing registered here is reachable from any execution/dispatch path.
Registering, qualifying, configuring, or even enabling a capability
through this store grants it no runtime authority by itself — matching
`SkillInstaller`'s own "installed is not the same as trusted to run"
discipline. Wiring an enabled capability into real dispatch is Batch
B's explicit, separate step.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

from uri_core.core.portable_paths import DEFAULT_USER_STATE_ROOT, user_scoped_path
from uri_core.external.lifecycle import LifecycleController, LifecycleState
from uri_core.external.qualification import QualificationRecord, Qualifier

SCHEMA_VERSION = "1.0"
STORE_FILENAME = "external_capabilities.json"


def _empty_document() -> Dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "capabilities": {}}


def _atomic_write_json(path: str, data: Mapping[str, Any]) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


@dataclass
class RegistrationResult:
    ok: bool
    descriptor_id: Optional[str] = None
    lifecycle: Optional[Dict[str, Any]] = None
    qualification: Optional[Dict[str, Any]] = None
    reasons: List[str] = None

    def __post_init__(self) -> None:
        if self.reasons is None:
            self.reasons = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "descriptor_id": self.descriptor_id,
            "lifecycle": self.lifecycle,
            "qualification": self.qualification,
            "reasons": list(self.reasons),
        }


class ExternalCapabilityStore:
    """Per-user durable store. `user_id` must be a real UUID (per
    `user_scoped_path`'s own strict validation) — there is no
    "no session recorded" fallback path here, matching M32.1's own
    session-isolation discipline for `ApprovalStore`."""

    def __init__(
        self,
        *,
        root: str = DEFAULT_USER_STATE_ROOT,
        qualifier: Optional[Qualifier] = None,
        lifecycle_controller: Optional[LifecycleController] = None,
    ):
        self.root = root
        self.qualifier = qualifier or Qualifier()
        self.lifecycle_controller = lifecycle_controller or LifecycleController()

    def _path(self, user_id: str) -> str:
        return user_scoped_path(user_id, STORE_FILENAME, root=self.root)

    def _load(self, user_id: str) -> Dict[str, Any]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return _empty_document()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return _empty_document()
        if not isinstance(data, dict) or not isinstance(data.get("capabilities"), dict):
            return _empty_document()
        return data

    def _save(self, user_id: str, data: Mapping[str, Any]) -> None:
        _atomic_write_json(self._path(user_id), data)

    def register_descriptor(
        self,
        descriptor_data: Mapping[str, Any],
        *,
        user_id: str,
        source_revision: Optional[str] = None,
        dependency_lock: Optional[Mapping[str, str]] = None,
    ) -> RegistrationResult:
        """Qualify → record, all statically, all scoped to `user_id`. A
        structurally invalid descriptor still produces an observable
        `rejected` record (matching `lifecycle.py`'s own reachable
        `QUALIFICATION_REJECTED` state) rather than vanishing silently -
        `Qualifier.qualify()` re-runs the same structural validation
        `register_descriptor` would otherwise duplicate, so there is one
        validation pass, not two. Never enables the capability (that is
        a separate, explicit `enable()` call) and never touches any
        other user's store file."""

        descriptor_id = str(descriptor_data.get("id", "")) or None
        if descriptor_id is None:
            return RegistrationResult(ok=False, descriptor_id=None, reasons=["descriptor has no usable id"])

        qualification = self.qualifier.qualify(
            descriptor_data, source_revision=source_revision, dependency_lock=dependency_lock
        )

        state = self.lifecycle_controller.detect(descriptor_id)
        state = self.lifecycle_controller.apply_qualification(
            state, qualified=(qualification.status == "qualified")
        )

        document = self._load(user_id)
        document["capabilities"][descriptor_id] = {
            "descriptor": dict(descriptor_data),
            "qualification": qualification.to_dict(),
            "lifecycle": state.to_dict(),
        }
        self._save(user_id, document)

        return RegistrationResult(
            ok=qualification.status == "qualified",
            descriptor_id=descriptor_id,
            lifecycle=state.to_dict(),
            qualification=qualification.to_dict(),
            reasons=list(qualification.reasons),
        )

    def get(self, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
        return self._load(user_id).get("capabilities", {}).get(descriptor_id)

    def list_all(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self._load(user_id).get("capabilities", {}).values())

    def _mutate_lifecycle(self, user_id: str, descriptor_id: str, mutator) -> Optional[Dict[str, Any]]:
        document = self._load(user_id)
        record = document.get("capabilities", {}).get(descriptor_id)
        if record is None:
            return None
        state = LifecycleState.from_dict(record["lifecycle"])
        state = mutator(state)
        record["lifecycle"] = state.to_dict()
        document["capabilities"][descriptor_id] = record
        self._save(user_id, document)
        return record["lifecycle"]

    def configure(self, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
        return self._mutate_lifecycle(user_id, descriptor_id, self.lifecycle_controller.configure)

    def authenticate(self, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
        return self._mutate_lifecycle(user_id, descriptor_id, self.lifecycle_controller.authenticate)

    def report_health(self, user_id: str, descriptor_id: str, *, healthy: bool) -> Optional[Dict[str, Any]]:
        return self._mutate_lifecycle(
            user_id, descriptor_id, lambda s: self.lifecycle_controller.report_health(s, healthy=healthy)
        )

    def enable(self, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
        return self._mutate_lifecycle(user_id, descriptor_id, self.lifecycle_controller.enable)

    def disable(self, user_id: str, descriptor_id: str) -> Optional[Dict[str, Any]]:
        return self._mutate_lifecycle(user_id, descriptor_id, self.lifecycle_controller.disable)

    def remove(self, user_id: str, descriptor_id: str) -> bool:
        document = self._load(user_id)
        capabilities = document.get("capabilities", {})
        if descriptor_id not in capabilities:
            return False
        del capabilities[descriptor_id]
        document["capabilities"] = capabilities
        self._save(user_id, document)
        from uri_core.external.credentials import ExternalCredentialStore
        ExternalCredentialStore(root=self.root).delete_credential(user_id, descriptor_id)
        return True
