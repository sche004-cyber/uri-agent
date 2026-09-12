"""Capability: answer a question from what URI already remembers about
the user (2026-09-12, User directive - "URI cannot retrieve its hard
fed memory").

Before this, a question like "What is my name?" or a bare
self-introduction ("Hi, my name is Chetan") matched none of
conversational_classifier.py's narrow greeting/farewell/thanks patterns
(correctly - those patterns are deliberately conservative), so it fell
through to capability selection, where no registered capability fit it
either - an honest, but unhelpful, "no implemented capability" gap
report, even though the exact fact the user needed WAS already sitting
in their own confirmed MemoryStore.

This tool closes that specific gap without expanding the conversational
classifier and without writing any new memory itself (a name/fact
still only enters memory the existing, explicit way - Settings > Memory
> "Remember something", or a future, separately-reviewed auto-capture
milestone - see user_memory.py's own module docstring on why that
remains deferred). It only ever READS already-consented memory
(user_provided/user_confirmed - never pending_confirmation, via the
same is_eligible_for_personalization() every other personalization
consumer already uses) and hands the real entries back as structured
data; the Brain's own narrative-drafting step (already given this
tool's "response" verbatim as outcome.response - see
orchestrator.py._draft_narrative_safely) is what phrases the actual
answer, never this tool.
"""

from typing import Any, Dict, Optional

from uri_core.core.portable_paths import user_scoped_path
from uri_core.core.user_memory import MemoryStore, is_eligible_for_personalization


class RecallMemoryTool:
    """`memory_store` is injectable for tests; the default derives a
    user-scoped store from the caller's own principal (mirroring
    server.py's own per-user MemoryStore construction), falling back to
    the ambient legacy store only when no principal is available at
    all (the same "unauthenticated legacy" convention every other
    ambient-default store in this codebase already follows)."""

    def __init__(self, memory_store: Optional[MemoryStore] = None):
        self._memory_store = memory_store

    def _resolve_store(self, principal: Any) -> MemoryStore:
        if self._memory_store is not None:
            return self._memory_store

        user_id = getattr(principal, "user_id", None)
        if user_id:
            return MemoryStore(storage_path=user_scoped_path(user_id, "user_memory.json"))
        return MemoryStore()

    def recall(self, **kwargs: Any) -> Dict[str, Any]:
        principal = kwargs.get("principal")
        store = self._resolve_store(principal)

        entries = [
            entry for entry in store.list_all()
            if is_eligible_for_personalization(entry)
        ]

        if not entries:
            return {
                "status": "success",
                "message": "URI has no saved memory entries for this user yet.",
                "entries": [],
            }

        return {
            "status": "success",
            "message": "Here is what URI currently remembers about this user.",
            "entries": [
                {"category": entry.category, "content": entry.fact.value}
                for entry in entries
            ],
        }
