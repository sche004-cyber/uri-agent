"""M33 Batch A — qualification record, bound to an exact source revision,
dependency lock, and profile digest, per the frozen blueprint's §6 Batch
A spec.

Detection here is entirely static: no importing, no package-discovery
hooks, no dependency fetching. This mirrors `uri_core/skills/skill_
installer.py`'s `SkillValidator`/`_digest_of_dir` discipline (reused
deliberately, per the blueprint's explicit instruction) — a digest is
computed over the descriptor's own declared content, never over
anything on disk that this process would have to import or execute to
read.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from uri_core.external.contract import ExternalCapabilityDescriptor, validate_descriptor

STATUS_QUALIFIED = "qualified"
STATUS_REJECTED = "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def profile_digest(
    descriptor_data: Mapping[str, Any], dependency_lock: Mapping[str, str]
) -> str:
    """A stable content digest over the descriptor's own declared shape
    plus its pinned dependency lock — never over anything fetched or
    imported. Canonical (sorted-key) JSON serialization keeps the digest
    stable regardless of dict insertion order."""

    canonical = json.dumps(
        {"descriptor": descriptor_data, "dependency_lock": dict(dependency_lock)},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class QualificationRecord:
    descriptor_id: str
    source_revision: Optional[str]
    dependency_lock: Dict[str, str] = field(default_factory=dict)
    profile_digest: str = ""
    status: str = STATUS_REJECTED
    reasons: List[str] = field(default_factory=list)
    qualified_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "descriptor_id": self.descriptor_id,
            "source_revision": self.source_revision,
            "dependency_lock": dict(self.dependency_lock),
            "profile_digest": self.profile_digest,
            "status": self.status,
            "reasons": list(self.reasons),
            "qualified_at": self.qualified_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "QualificationRecord":
        return cls(
            descriptor_id=str(data.get("descriptor_id", "")),
            source_revision=data.get("source_revision"),
            dependency_lock=dict(data.get("dependency_lock", {})),
            profile_digest=str(data.get("profile_digest", "")),
            status=str(data.get("status", STATUS_REJECTED)),
            reasons=list(data.get("reasons", [])),
            qualified_at=str(data.get("qualified_at", _now())),
        )


class Qualifier:
    """Static-only qualification. `qualify()` never imports, never
    executes, never fetches a dependency — it re-runs `contract.py`'s
    structural validation (the descriptor may have changed since it was
    first registered) and binds the result to an exact source revision,
    a caller-supplied dependency lock (declared, not resolved), and a
    content digest over both."""

    def qualify(
        self,
        descriptor_data: Mapping[str, Any],
        *,
        source_revision: Optional[str],
        dependency_lock: Optional[Mapping[str, str]] = None,
    ) -> QualificationRecord:
        dependency_lock = dict(dependency_lock or {})
        result = validate_descriptor(descriptor_data)
        digest = profile_digest(descriptor_data, dependency_lock)
        descriptor_id = str(descriptor_data.get("id", ""))
        if not result.valid:
            return QualificationRecord(
                descriptor_id=descriptor_id,
                source_revision=source_revision,
                dependency_lock=dependency_lock,
                profile_digest=digest,
                status=STATUS_REJECTED,
                reasons=list(result.reasons),
            )
        return QualificationRecord(
            descriptor_id=descriptor_id,
            source_revision=source_revision,
            dependency_lock=dependency_lock,
            profile_digest=digest,
            status=STATUS_QUALIFIED,
            reasons=[],
        )
