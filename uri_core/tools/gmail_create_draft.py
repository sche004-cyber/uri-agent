"""Capability: create a Gmail DRAFT (M19) - never sends anything.

Registered approval_requirement=user_approval_required (see
capabilities_registry.json), so this never executes without an
explicit human decision (see ApprovalGate.execute_tool - the same gate
every other approval-required capability goes through). Even once
approved, the result is only ever a draft sitting in the user's own
Gmail account; the user still reviews and sends it themselves. There is
no send capability anywhere in this codebase.

Argument boundary, unchanged from every other capability: the
recipient address is extracted DETERMINISTICALLY from request_text (the
runtime-supplied user/goal text) via a plain regex - never a
model-supplied argument, exactly the same discipline fetch_url.py uses
for URLs. The subject/body are composed by the Brain from a drafting
brief, reusing the identical policy/evidence/soul assembly
institutional document drafting already uses (services/
institutional_drafting.py) - there is no second, parallel composition
path for an email versus a document.
"""

import re
from typing import Any, Dict, Optional

from uri_core.config.institutional_rules import load_institutional_rules
from uri_core.services.document_composer import DocumentComposer
from uri_core.services.drafting_guidance import build_drafting_brief
from uri_core.services.gmail_service import GmailService
from uri_core.services.institutional_drafting import (
    POLICY_PATH,
    SOUL_PATH,
    extract_drafting_rules,
    gather_session_evidence,
    read_text_file,
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _extract_recipient(request_text: str) -> Optional[str]:
    match = _EMAIL_RE.search(request_text or "")
    return match.group(0) if match else None


def _derive_subject(body_text: str) -> str:
    for line in body_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            return stripped.split(":", 1)[1].strip()[:200]

    first_line = next(
        (line.strip() for line in body_text.splitlines() if line.strip()), ""
    )
    return first_line[:100] or "Message from URI"


class GmailCreateDraftTool:
    """`composer`/`gmail_service` are injectable for tests; defaults
    lazily construct the real objects, so importing/instantiating this
    tool never requires a running model or a Gmail connection."""

    def __init__(self, gmail_service=None, composer: Optional[DocumentComposer] = None):
        self._gmail_service = gmail_service or GmailService()
        self._composer = composer

    def generate(self, **kwargs) -> Dict[str, Any]:
        request_text = kwargs.get("request_text", "") or ""
        session_id = kwargs.get("session_id")
        decision_context = kwargs.get("decision_context") or {}

        recipient = _extract_recipient(request_text)

        if recipient is None:
            return {
                "status": "input_required",
                "message": (
                    "No recipient email address was found in the request, "
                    "so URI does not know who to draft this to."
                ),
            }

        rules = load_institutional_rules()
        policy_rules = extract_drafting_rules(read_text_file(POLICY_PATH))
        soul_text = read_text_file(SOUL_PATH)

        evidence = gather_session_evidence(session_id, None)
        if isinstance(decision_context.get("verified_evidence"), dict):
            evidence = {**decision_context["verified_evidence"], **evidence}

        preferences = {}
        if isinstance(decision_context.get("user_preferences"), dict):
            preferences = decision_context["user_preferences"]

        brief = build_drafting_brief(
            request_text=request_text,
            requested_output="email",
            document_type="email",
            evidence=evidence,
            preferences=preferences,
            institutional_rules=rules,
            policy_rules=policy_rules,
        )

        principal = kwargs.get("principal")
        composer = self._composer or DocumentComposer(principal=principal)
        result = composer.compose(
            brief=brief,
            request_text=request_text,
            evidence=evidence,
            preferences=preferences,
            soul_text=soul_text,
            principal=principal,
        )
        body_text = result["body"]
        subject = _derive_subject(body_text)

        draft_result = self._gmail_service.create_draft(
            to=recipient, subject=subject, body=body_text
        )

        if not draft_result.get("success"):
            return {
                "status": "unavailable",
                "message": "URI could not create the Gmail draft.",
                "error": draft_result.get("reason", "Gmail is not connected."),
            }

        return {
            "status": "success",
            "to": recipient,
            "subject": subject,
            "draft_id": draft_result.get("draft_id"),
            "composed_by": result["composed_by"],
            "preview": body_text[:500],
        }
