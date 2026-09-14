"""Small, deterministic session context for conversational follow-ups."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional


class CapabilityContextResolver:
    """Retains identifiers already returned by an action, never inventing one."""

    def __init__(self) -> None:
        self._current: Dict[str, Any] = {}

    def record_action_result(self, capability: str, action: str, result: Mapping[str, Any]) -> None:
        if capability != "Gmail" or not isinstance(result, Mapping):
            return
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

    def resolve(self, action_name: str, request_text: str = "") -> Dict[str, Any]:
        """Return only grounded IDs suitable for a selected action.

        The caller has already selected the action; this resolver merely binds
        pronouns such as ``that one`` and ``its attachment`` to prior evidence.
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
