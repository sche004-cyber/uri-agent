"""Small, deterministic session context for conversational follow-ups.

M33 Batch B (D6): generalized beyond Gmail. `record_action_result`/
`resolve` used to hard-branch on the literal string "Gmail"
(`capability != "Gmail": return`) - every chained external action got no
context grounding at all. Gmail's own extraction logic is unchanged
byte-for-byte, moved into `_extract_gmail` and registered as this
resolver's "Gmail" extractor via the same `_extractors` mechanism any
other capability id can use - Gmail keeps its behavior through
registration, not through a branch, matching `canonical_execution.py`'s
own D6 generalization. A capability with no registered extractor falls
back to `_extract_generic`, which stores its last result verbatim,
namespaced by capability id, so a later single-action `resolve(...,
capability=that_id)` call can still ground a follow-up reference -
coarser than Gmail's own field-aware extraction, but real, not absent.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

Extractor = Callable[["CapabilityContextResolver", str, Mapping[str, Any]], None]


class CapabilityContextResolver:
    """Retains identifiers already returned by an action, never inventing one."""

    def __init__(self, extractors: Optional[Mapping[str, Extractor]] = None) -> None:
        self._current: Dict[str, Any] = {}
        self._external_current: Dict[str, Dict[str, Any]] = {}
        self._extractors: Dict[str, Extractor] = {"Gmail": CapabilityContextResolver._extract_gmail}
        if extractors:
            self._extractors.update(extractors)

    def register_extractor(self, capability: str, extractor: Extractor) -> None:
        """Lets a capability declare its own grounding logic (D6) -
        never required; `_extract_generic` is used for any capability
        with no registered extractor."""
        self._extractors[capability] = extractor

    def record_action_result(self, capability: str, action: str, result: Mapping[str, Any]) -> None:
        if not isinstance(result, Mapping):
            return
        extractor = self._extractors.get(capability)
        if extractor is not None:
            extractor(self, action, result)
            return
        # No registered extractor for this capability id (every external
        # capability, until it declares its own via `register_extractor`):
        # keep its last result verbatim, namespaced by capability id, so
        # `resolve(..., capability=capability)` can still ground a
        # follow-up reference. Coarser than a field-aware extractor, but
        # real grounding, never silently absent (D6).
        self._external_current[capability] = dict(result)

    def _extract_gmail(self, action: str, result: Mapping[str, Any]) -> None:
        message = self._first_message(result)
        if message:
            self._current["message"] = message
            if message.get("thread_id"):
                self._current["thread_id"] = message["thread_id"]
            attachment = self._first_attachment(message)
            if attachment:
                self._current["attachment"] = attachment
        if result.get("thread_id"):
            self._current["thread_id"] = result["thread_id"]
        attachment = self._first_attachment(result)
        if attachment:
            self._current["attachment"] = attachment
        if action == "read_message" and isinstance(result.get("message"), Mapping):
            self._current["message"] = dict(result["message"])
        if action == "read_thread" and isinstance(result.get("messages"), list) and result["messages"]:
            self._current["message"] = dict(result["messages"][-1])

    def resolve(
        self, action_name: str, request_text: str = "", *, capability: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return only grounded IDs suitable for a selected action.

        The caller has already selected the action; this resolver merely binds
        pronouns such as ``that one`` and ``its attachment`` to prior evidence.

        `capability` is optional and additive (M33 Batch B / D6): every
        existing call site that omits it sees exactly the Gmail-shaped
        behavior below, unchanged. When supplied and the Gmail-specific
        rules find nothing to ground, the capability's own last recorded
        result (`_external_current`, generic extraction) is returned
        verbatim - explicit `inputs` still win in `_bind_context`'s own
        merge, so this can only fill in what the caller omitted.
        """
        message = self._current.get("message", {})
        attachment = self._current.get("attachment", {})
        if action_name == "read_message" and message.get("message_id"):
            return {"message_id": message["message_id"]}
        if action_name == "read_thread":
            thread_id = self._current.get("thread_id") or message.get("thread_id")
            return {"thread_id": thread_id} if thread_id else {}
        if action_name == "read_attachment":
            message_id = attachment.get("message_id") or message.get("message_id")
            resolved = {
                key: value
                for key, value in {
                    "message_id": message_id,
                    "attachment_id": attachment.get("attachment_id"),
                    "filename": attachment.get("filename"),
                }.items()
                if value
            }
            return resolved
        if action_name == "create_draft":
            return {
                key: value
                for key, value in {
                    "in_reply_to_thread_id": self._current.get("thread_id") or message.get("thread_id"),
                    # The sender is evidence returned by Gmail, not a model
                    # inference.  Draft creation remains approval-gated by
                    # MultiActionExecutor regardless of this grounding.
                    "to": message.get("from"),
                    "reply_to": message.get("from"),
                    "subject": message.get("subject"),
                }.items()
                if value
            }
        if capability is not None:
            return dict(self._external_current.get(capability, {}))
        return {}

    @staticmethod
    def _first_message(result: Mapping[str, Any]) -> Dict[str, Any]:
        if isinstance(result.get("message"), Mapping):
            return dict(result["message"])
        messages = result.get("messages")
        if isinstance(messages, list) and messages and isinstance(messages[0], Mapping):
            return dict(messages[0])
        groups = result.get("results")
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, Mapping):
                    found = CapabilityContextResolver._first_message(group)
                    if found:
                        return found
        return {}

    @staticmethod
    def _first_attachment(value: Mapping[str, Any]) -> Dict[str, Any]:
        attachments = value.get("attachments")
        if isinstance(attachments, list) and attachments and isinstance(attachments[0], Mapping):
            return dict(attachments[0])
        return {}
