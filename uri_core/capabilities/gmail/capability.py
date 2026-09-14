"""Gmail's reusable multi-action capability adapter.

The adapter deliberately owns no OAuth flow and never sends email.  It uses
``GmailService`` as the sole connection/service boundary and exposes only the
operations already supported by the installed service or its authenticated
Gmail API client.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, Iterable, List, Mapping, Optional

from uri_core.services.gmail_service import GmailService

from ..base import Action, ActionSchema, ApprovalRequirement, Capability, RiskLevel


class GmailCapability(Capability):
    """Reference capability for Gmail, including safe draft creation only.

    ``apply_label`` and ``archive_message`` remain visible so the model knows
    their semantic affordance, but both intentionally return ``unsupported``:
    GmailService does not request the gmail.modify scope.
    """

    def __init__(self, gmail_service: Optional[GmailService] = None):
        self.gmail_service = gmail_service or GmailService()
        super().__init__(
            name="Gmail",
            description=(
                "Search and inspect Gmail messages, threads, labels, unread "
                "counts, and attachments; prepare email drafts but never send email."
            ),
            category="communication",
            permissions=["gmail.readonly"],
            preconditions=["gmail_connected"],
            availability_check=self._availability,
            actions={
                "list_labels": Action(
                    name="list_labels",
                    description="List Gmail labels with total and unread email message counts; use for unread-count questions.",
                    parameters=ActionSchema(),
                    returns={"labels": "list[label metadata]"},
                    read_only=True,
                    risk=RiskLevel.LOW,
                    handler=self.list_labels,
                ),
                "search_messages": Action(
                    name="search_messages",
                    description="Find or search Gmail messages using Gmail search syntax such as unread, sender, subject, or attachment filters.",
                    parameters={"query": {"type": "string", "required": True}, "max_results": {"type": "integer"}},
                    returns={"results": "list[message search result]"},
                    read_only=True,
                    risk=RiskLevel.LOW,
                    handler=self.search_messages,
                ),
                "read_message": Action(
                    name="read_message",
                    description="Read one email's headers, subject, sender, date, snippet, body, thread ID, and attachment inventory.",
                    parameters={"message_id": {"type": "string", "required": True}},
                    returns={"message": "message metadata and body"},
                    read_only=True,
                    risk=RiskLevel.LOW,
                    handler=self.read_message,
                ),
                "read_thread": Action(
                    name="read_thread",
                    description="Read the full conversation in a Gmail thread, including message and attachment inventory.",
                    parameters={"thread_id": {"type": "string", "required": True}},
                    returns={"messages": "list[message]", "attachments": "list[attachment]"},
                    read_only=True,
                    risk=RiskLevel.LOW,
                    handler=self.read_thread,
                ),
                "read_attachment": Action(
                    name="read_attachment",
                    description="Inspect an email attachment inventory or download one explicitly identified attachment as temporary evidence.",
                    parameters={
                        "message_id": {"type": "string", "required": True},
                        "attachment_id": {"type": "string"},
                        "filename": {"type": "string"},
                        "thread_id": {"type": "string"},
                    },
                    returns={"attachments": "list[attachment]", "file_path": "temporary file path when downloaded"},
                    read_only=True,
                    risk=RiskLevel.CONTROLLED,
                    handler=self.read_attachment,
                ),
                "create_draft": Action(
                    name="create_draft",
                    description="Prepare or create a Gmail reply draft for the user to review in Gmail. It never sends email.",
                    parameters={
                        "to": {"type": "string", "required": True},
                        "subject": {"type": "string", "required": True},
                        "body": {"type": "string", "required": True},
                        "in_reply_to_thread_id": {"type": "string"},
                        "reply_to": {"type": "string"},
                    },
                    returns={"draft_id": "string"},
                    read_only=False,
                    approval_requirement=ApprovalRequirement.USER_APPROVAL_REQUIRED,
                    risk=RiskLevel.HIGH,
                    handler=self.create_draft,
                ),
                "apply_label": self._unsupported_action(
                    "apply_label",
                    "Apply a Gmail label to a message.",
                    {"message_id": {"type": "string", "required": True}, "label_id": {"type": "string", "required": True}},
                ),
                "archive_message": self._unsupported_action(
                    "archive_message",
                    "Archive a Gmail message by removing it from Inbox.",
                    {"message_id": {"type": "string", "required": True}},
                ),
            },
        )

    def _availability(self) -> Dict[str, Any]:
        try:
            status = self.gmail_service.get_connection_status()
            connected = bool(status.get("connected")) if isinstance(status, Mapping) else False
        except Exception:
            connected = bool(getattr(self.gmail_service, "service", None))
        return {
            "available": connected,
            "missing_preconditions": [] if connected else ["gmail_connected"],
        }

    @staticmethod
    def _unsupported_action(name: str, description: str, parameters: Dict[str, Dict[str, Any]]) -> Action:
        return Action(
            name=name,
            description=description,
            parameters=parameters,
            returns={"status": "unsupported"},
            read_only=False,
            approval_requirement=ApprovalRequirement.USER_APPROVAL_REQUIRED,
            risk=RiskLevel.HIGH,
            handler=lambda **_: {
                "status": "unsupported",
                "message": (
                    f"{name} is not supported by current GmailService backend without gmail.modify OAuth scope. "
                    "(Intentionally left untouched to protect concurrent Claude workstream.)"
                ),
            },
        )

    def list_labels(self) -> Dict[str, Any]:
        client = self._client_or_none()
        if client is None:
            return self._disconnected()
        try:
            label_resource = client.users().labels()
            listed = label_resource.list(userId="me").execute().get("labels", [])
            labels = []
            for label in listed:
                label_id = label.get("id")
                detail = label_resource.get(userId="me", id=label_id).execute() if label_id else label
                labels.append({
                    "id": detail.get("id", label_id),
                    "name": detail.get("name", label.get("name", "")),
                    "messages_total": detail.get("messagesTotal", 0),
                    "messages_unread": detail.get("messagesUnread", 0),
                    "threads_total": detail.get("threadsTotal", 0),
                    "threads_unread": detail.get("threadsUnread", 0),
                })
            return {"status": "success", "labels": labels}
        except Exception as exc:
            return {"status": "unavailable", "message": "URI could not list Gmail labels.", "error": str(exc)}

    def search_messages(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        try:
            result = self.gmail_service.search_evidence([query])
        except Exception as exc:
            return {"status": "unavailable", "message": "URI could not search Gmail.", "error": str(exc)}
        if not result.get("success"):
            return {"status": "unavailable", "message": "URI could not search Gmail.", "error": result.get("reason")}
        groups = result.get("results", [])
        messages = [message for group in groups if isinstance(group, Mapping) for message in group.get("messages", [])]
        return {"status": "success", "query": query, "messages": messages[:max_results], "results": groups}

    def read_message(self, message_id: str) -> Dict[str, Any]:
        method = getattr(self.gmail_service, "get_message_metadata", None)
        try:
            if callable(method):
                result = method(message_id)
                return self._normalise_service_result(result, "message")
            client = self._client_or_none()
            if client is None:
                return self._disconnected()
            raw = client.users().messages().get(userId="me", id=message_id, format="full").execute()
            return {"status": "success", "message": self._message_from_raw(raw)}
        except Exception as exc:
            return {"status": "unavailable", "message": "URI could not read the Gmail message.", "error": str(exc)}

    def read_thread(self, thread_id: str) -> Dict[str, Any]:
        method = getattr(self.gmail_service, "get_thread", None)
        try:
            if callable(method):
                return self._normalise_service_result(method(thread_id), "thread")
            return self._normalise_service_result(self.gmail_service.get_thread_evidence(thread_id), "thread")
        except Exception as exc:
            return {"status": "unavailable", "message": "URI could not read the Gmail thread.", "error": str(exc)}

    def read_attachment(
        self,
        message_id: str,
        attachment_id: Optional[str] = None,
        filename: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            if attachment_id and filename:
                result = self.gmail_service.download_attachment(message_id, attachment_id, filename)
                return self._normalise_service_result(result, "attachment")
            inventory = self._attachment_inventory(message_id, thread_id)
            return {"status": "success", "attachments": inventory}
        except Exception as exc:
            return {"status": "unavailable", "message": "URI could not inspect the Gmail attachment.", "error": str(exc)}

    def create_draft(self, to: str, subject: str, body: str, **_: Any) -> Dict[str, Any]:
        result = self.gmail_service.create_draft(to=to, subject=subject, body=body)
        return self._normalise_service_result(result, "draft")

    def _attachment_inventory(self, message_id: str, thread_id: Optional[str]) -> List[Dict[str, Any]]:
        method = getattr(self.gmail_service, "build_attachment_inventory", None)
        if callable(method):
            inventory = method(message_id)
            return inventory if isinstance(inventory, list) else inventory.get("attachments", [])
        if thread_id:
            thread = self.gmail_service.get_thread_evidence(thread_id)
            return [item for item in thread.get("attachments", []) if item.get("message_id") == message_id]
        message = self.read_message(message_id)
        return message.get("message", {}).get("attachments", [])

    def _client_or_none(self) -> Any:
        return getattr(self.gmail_service, "service", None)

    @staticmethod
    def _disconnected() -> Dict[str, Any]:
        return {"status": "unavailable", "message": "Gmail is not connected.", "missing_preconditions": ["gmail_connected"]}

    @staticmethod
    def _normalise_service_result(result: Any, noun: str) -> Dict[str, Any]:
        if not isinstance(result, Mapping):
            return {"status": "unavailable", "message": f"Gmail {noun} returned an unreadable response."}
        response = dict(result)
        if "status" in response:
            return response
        if noun == "message" and ("message_id" in response or "id" in response):
            return {"status": "success", "message": response}
        if noun == "thread" and ("thread_id" in response or "messages" in response):
            return {"status": "success", **response}
        if response.get("success"):
            response["status"] = "success"
        else:
            response["status"] = "unavailable"
            response.setdefault("message", f"URI could not read the Gmail {noun}.")
        return response

    @classmethod
    def _message_from_raw(cls, raw: Mapping[str, Any]) -> Dict[str, Any]:
        payload = raw.get("payload", {})
        headers = {item.get("name", "").lower(): item.get("value", "") for item in payload.get("headers", [])}
        return {
            "message_id": raw.get("id"),
            "thread_id": raw.get("threadId"),
            "subject": headers.get("subject", ""),
            "from": headers.get("from", ""),
            "date": headers.get("date", ""),
            "snippet": raw.get("snippet", ""),
            "body": cls._body_text(payload),
            "attachments": cls._attachments(payload),
        }

    @classmethod
    def _body_text(cls, part: Mapping[str, Any]) -> str:
        data = part.get("body", {}).get("data")
        if data and str(part.get("mimeType", "")).startswith("text/"):
            try:
                return base64.urlsafe_b64decode(str(data) + "==").decode("utf-8", errors="replace")
            except Exception:
                return ""
        return "\n".join(filter(None, (cls._body_text(child) for child in part.get("parts", []))))

    @classmethod
    def _attachments(cls, part: Mapping[str, Any]) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        body = part.get("body", {})
        if part.get("filename") and body.get("attachmentId"):
            found.append({"filename": part["filename"], "attachment_id": body["attachmentId"], "mime_type": part.get("mimeType", "")})
        for child in part.get("parts", []):
            found.extend(cls._attachments(child))
        return found
