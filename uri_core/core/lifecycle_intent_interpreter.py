"""M33.1 Batch 4 - deterministic (model-free) interpretation for the live
`/ask` lifecycle seam.

Recognizes only one fixed, narrow command shape: ``"<verb> skill|service
<target>"`` (e.g. "enable skill yt_dlp", "connect service github"). Any text
that does not match this shape returns ``None`` and is left completely
untouched by the seam that calls this - ordinary conversational `/ask`
behavior is unaffected. ``verb``/``target`` are passed through UNVALIDATED:
whether either names a real operation/target is decided entirely downstream
by ``uri_core.external.lifecycle_intent.execute_lifecycle_intent``'s own
catalog and state-machine checks - this module only recognizes shape, it
never grants authority and never touches a package name, URL, path, or argv.

Deliberately OFF by default (`lifecycle_intent_seam_enabled()`), the same
"materially newer, not yet earning the default-on bar" convention
`native_tool_loop.py` established - not because this is unsafe (every
outcome fails closed through the same catalog Batches 1-3 already proved),
but because it is new, live, model-facing `/ask` surface added in a
milestone-closure batch.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

LIFECYCLE_INTENT_SEAM_ENV_VAR = "URI_ENABLE_LIFECYCLE_INTENT_SEAM"

_COMMAND_PATTERN = re.compile(
    r"^\s*(?P<operation>install|enable|disable|update|remove|connect|disconnect)"
    r"\s+(?P<kind>skill|service)\s+(?P<target>[A-Za-z0-9][A-Za-z0-9_-]*)\s*[.!?]?\s*$",
    re.IGNORECASE,
)

_SKILL_OPERATIONS = frozenset({"install", "enable", "disable", "update", "remove"})
_SERVICE_OPERATIONS = frozenset({"connect", "disconnect"})


def lifecycle_intent_seam_enabled() -> bool:
    """Set to "1" to opt in. Unset (production default) leaves every
    `/ask` call byte-identical to before this batch."""
    return os.environ.get(LIFECYCLE_INTENT_SEAM_ENV_VAR) == "1"


def _normalize_target(raw: str) -> str:
    return raw.strip().strip(".!?").lower().replace("-", "_").replace(" ", "_")


def interpret(user_text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return ``{"operation", "target_id"}`` for a recognized lifecycle-
    shaped command, else ``None``. Never raises."""
    if not isinstance(user_text, str) or not user_text.strip():
        return None
    match = _COMMAND_PATTERN.match(user_text)
    if match is None:
        return None
    operation = match.group("operation").lower()
    kind = match.group("kind").lower()
    if (kind == "skill" and operation not in _SKILL_OPERATIONS) or (
        kind == "service" and operation not in _SERVICE_OPERATIONS
    ):
        return None
    return {"operation": operation, "target_id": _normalize_target(match.group("target"))}
