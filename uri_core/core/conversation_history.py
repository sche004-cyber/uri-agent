"""M18: durable conversation transcript (user text + URI response) per
session.

Distinct from every other store this codebase keeps:
- SessionManager (state.py): the *task/fact/workflow* state of one
  in-progress conversation - not the dialogue itself.
- ExperienceStore: Brain-approved *summaries* of what was worth
  remembering - not the verbatim exchange.
- user_memory: durable facts ABOUT the user.

This store keeps the actual back-and-forth so URI can show a user their
past conversations and resume them, and so "recognise previous work"
rests on the real dialogue rather than only the bounded experience
summaries. It is a plain transcript: it records what was said and the
outcome status, never a judgement, never an instruction. Nothing read
back from here is authority - it is context the Brain may draw on,
exactly like experience, and it can never override Soul, the operating
policy, authorisation, or a safety boundary.

Mirrors the persistence discipline of MemoryStore/ExperienceStore
(schema-versioned per-session JSON, bounded, safe degrade-to-empty on a
corrupted file, never raises on read).
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"

# Bounds so a very long-lived session can never grow an unbounded file
# or an unbounded context read. Oldest turns beyond the cap are dropped
# from the persisted transcript (a transcript is a convenience, not an
# audit log - the AuditTrail remains the record of consequential
# actions).
MAX_TURNS_PER_SESSION = 200

# Field length caps so one enormous message cannot bloat the store.
MAX_TEXT_LENGTH = 8000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(value: Any, limit: int = MAX_TEXT_LENGTH) -> str:
    text = "" if value is None else str(value)
    return text[:limit]


@dataclass
class ConversationTurn:
    turn_id: str
    timestamp: str
    user_text: str
    response_text: str
    status: Optional[str] = None
    capability: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConversationHistoryStore:
    """One JSON file per session under `storage_dir`. The server points
    each user_id's orchestrator at that user's own directory, so a
    transcript is never shared across users (see server._build_user_
    context)."""

    def __init__(self, storage_dir: str = "uri_workspace/conversation_history"):
        self.storage_dir = os.path.normpath(storage_dir)

    # ---------------------------------------------------------------
    # Paths
    # ---------------------------------------------------------------

    def _safe_name(self, session_id: str) -> Optional[str]:
        """A filename derived from session_id that can never escape the
        store directory. Returns None for an unusable id rather than
        risking a traversal."""

        if not session_id or not isinstance(session_id, str):
            return None
        base = os.path.basename(session_id.strip())
        if not base or base in (".", ".."):
            return None
        # Keep it conservative - only characters real session ids use.
        cleaned = "".join(
            ch for ch in base if ch.isalnum() or ch in ("-", "_", ".")
        )
        return cleaned or None

    def _path_for(self, session_id: str) -> Optional[str]:
        name = self._safe_name(session_id)
        if name is None:
            return None
        return os.path.join(self.storage_dir, f"{name}.json")

    def _ensure_dir(self) -> None:
        if self.storage_dir and not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)

    # ---------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------

    def _load_raw(self, session_id: str) -> Dict[str, Any]:
        path = self._path_for(session_id)
        if path is None or not os.path.exists(path):
            return {"schema_version": SCHEMA_VERSION, "session_id": session_id, "turns": []}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {"schema_version": SCHEMA_VERSION, "session_id": session_id, "turns": []}
        if not isinstance(data, dict) or not isinstance(data.get("turns"), list):
            return {"schema_version": SCHEMA_VERSION, "session_id": session_id, "turns": []}
        return data

    def get_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Every recorded turn for one session, oldest first. Empty list
        for an unknown/corrupt session - never raises."""
        return list(self._load_raw(session_id).get("turns", []))

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """A bounded summary of the sessions this store holds, most
        recently active first: id, turn count, last activity, and a
        short preview of the first user message. Never raises."""
        summaries: List[Dict[str, Any]] = []
        if not os.path.isdir(self.storage_dir):
            return summaries
        try:
            names = os.listdir(self.storage_dir)
        except OSError:
            return summaries
        for name in names:
            if not name.endswith(".json"):
                continue
            session_id = name[: -len(".json")]
            turns = self.get_session(session_id)
            if not turns:
                continue
            summaries.append(
                {
                    "session_id": session_id,
                    "turn_count": len(turns),
                    "last_activity": turns[-1].get("timestamp"),
                    "preview": _clip(turns[0].get("user_text", ""), 120),
                }
            )
        summaries.sort(key=lambda item: item.get("last_activity") or "", reverse=True)
        return summaries[: max(0, limit)]

    # ---------------------------------------------------------------
    # Write
    # ---------------------------------------------------------------

    def append_turn(
        self,
        *,
        session_id: str,
        turn_id: str,
        user_text: str,
        response_text: str,
        status: Optional[str] = None,
        capability: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Append one exchange. Returns True on success, False on any
        failure (unusable id, write error) - a transcript write must
        never break the turn that produced it, so the caller treats a
        False as 'not recorded' and moves on."""

        path = self._path_for(session_id)
        if path is None:
            return False

        data = self._load_raw(session_id)
        turns = data.get("turns", [])

        turn = ConversationTurn(
            turn_id=str(turn_id),
            timestamp=_now(),
            user_text=_clip(user_text),
            response_text=_clip(response_text),
            status=status,
            capability=capability,
            attachments=attachments or [],
        )
        turns.append(turn.to_dict())

        # Drop the oldest turns beyond the cap.
        if len(turns) > MAX_TURNS_PER_SESSION:
            turns = turns[-MAX_TURNS_PER_SESSION:]

        data["schema_version"] = SCHEMA_VERSION
        data["session_id"] = session_id
        data["turns"] = turns

        try:
            self._ensure_dir()
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            return True
        except OSError:
            return False

    def delete_session(self, session_id: str) -> bool:
        """Remove one session's transcript entirely. Returns whether a
        file was actually deleted."""
        path = self._path_for(session_id)
        if path is None or not os.path.exists(path):
            return False
        try:
            os.remove(path)
            return True
        except OSError:
            return False
