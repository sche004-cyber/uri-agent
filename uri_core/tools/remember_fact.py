"""Capability: save a fact the user explicitly asked URI to remember
(2026-09-12, User directive - "can you save it to my profile?" /
"add this to my profile" repeatedly landed nowhere, or was misrouted
to document drafting).

Deliberately narrow: only ever writes via MemoryStore.add(), which is
consent="user_provided" by construction - "the user directly told URI
to remember this. Consent is inherent in the request" (see
user_memory.py's own module docstring). This is NOT the auto-capture/
propose() path (consent="pending_confirmation", requiring separate
user confirmation before it can influence anything) - that remains
deliberately out of scope, exactly as user_memory.py's docstring
describes it as a distinct, separately-reviewed capability. This tool
only ever fires when the user's own words are an explicit save/
remember/add-to-profile instruction; capability_planner.py's scoring
keeps that narrow.
"""

import re
from typing import Any, Dict, Optional

from uri_core.core.portable_paths import user_scoped_path
from uri_core.core.user_memory import MemoryStore, MemoryValidationError

# Stripped only as a leading/trailing instruction phrase, never from
# the middle of a sentence - so "remember that I remember everything"
# keeps its real meaning intact.
_TRIGGER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^(can you |could you |please )?(add|save) (this|that|it) to my profile[,:]?\s*",
        r"\s*(so |and )?(please )?(add|save) (this|that|it) to my profile\.?$",
        r"^(please )?remember (that|this)?[,:]?\s*",
        r"^(please )?save (this|that)( to memory)?[,:]?\s*",
    )
]


class RememberFactTool:
    """`memory_store` is injectable for tests; the default derives a
    user-scoped store from the caller's own principal, mirroring
    recall_memory.py's identical convention."""

    def __init__(self, memory_store: Optional[MemoryStore] = None):
        self._memory_store = memory_store

    def _resolve_store(self, principal: Any) -> MemoryStore:
        if self._memory_store is not None:
            return self._memory_store

        user_id = getattr(principal, "user_id", None)
        if user_id:
            return MemoryStore(storage_path=user_scoped_path(user_id, "user_memory.json"))
        return MemoryStore()

    @staticmethod
    def _extract_content(request_text: str) -> str:
        content = request_text.strip()
        for pattern in _TRIGGER_PATTERNS:
            content = pattern.sub("", content).strip()
        return content

    def remember(self, **kwargs: Any) -> Dict[str, Any]:
        principal = kwargs.get("principal")
        request_text = (kwargs.get("request_text") or "").strip()

        if not request_text:
            return {
                "status": "input_required",
                "message": "There is nothing to remember yet - say what you'd like URI to save.",
            }

        content = self._extract_content(request_text)

        if not content or len(content) < 3:
            return {
                "status": "input_required",
                "message": (
                    "URI needs the actual fact to save, stated directly "
                    "(e.g. \"I work at NIT Sikkim\") - the request alone "
                    "doesn't say what to remember."
                ),
            }

        store = self._resolve_store(principal)

        try:
            entry = store.add(category="explicit_statement", content=content)
        except MemoryValidationError as exc:
            return {
                "status": "error",
                "message": f"URI could not save that to memory: {exc}",
            }

        return {
            "status": "success",
            "message": f'Saved to memory: "{content}"',
            "memory_id": entry.memory_id,
            "content": content,
        }
