"""The single institutional-document drafting entry point (M17).

Both drafting capabilities (draft_institutional_note,
draft_institutional_order) are thin wrappers over this one function -
there is deliberately no second, parallel drafting path. It gathers the
inputs the Brain needs (institutional conventions, the operating
policy's drafting rules, any attached-file evidence, the caller's
preferences), builds a drafting brief (drafting_guidance), and asks the
Brain to author the body (document_composer). The tools only fix the
document *kind*; everything structural is decided downstream by the
Brain from the brief.
"""

import os
from typing import Any, Dict, Optional

from uri_core.config.institutional_rules import load_institutional_rules
from uri_core.core.file_store import FileStore
from uri_core.services.document_composer import DocumentComposer
from uri_core.services.drafting_guidance import build_drafting_brief
from uri_core.services.file_extraction import extract_file_text


_POLICY_PATH = os.path.join(
    "URI_Model_Centric_Architecture_Docs", "URI_AI_OPERATING_POLICY.md"
)
_SOUL_PATH = os.path.join(
    "URI_Model_Centric_Architecture_Docs", "soul.md"
)

# How many attached files' text is fed into a single drafting call, and
# how much text per file, so a session with many/large attachments can
# never produce an unbounded drafting prompt. Bounded exactly as
# read_attached_file.py bounds its own reads.
_MAX_EVIDENCE_FILES = 3
_MAX_EVIDENCE_CHARS_PER_FILE = 4000


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return handle.read()
    except OSError:
        return ""


def _extract_drafting_rules(policy_text: str) -> str:
    """The operating policy's own Drafting and Review sections (11 and
    12), sliced out verbatim so the drafting rules the Brain follows ARE
    the policy's rules, not a paraphrase maintained here. Degrades to
    the whole policy tail, then to empty, rather than raising."""

    if not policy_text:
        return ""

    marker = "## 11. Drafting"
    start = policy_text.find(marker)
    if start == -1:
        return ""

    # End at section 13 (Workflow Planning) if present, so only the
    # drafting-relevant rules (11 Drafting + 12 Review) are carried.
    end_marker = "## 13."
    end = policy_text.find(end_marker, start)
    if end == -1:
        return policy_text[start:].strip()

    return policy_text[start:end].strip()


def _gather_attachment_evidence(
    session_id: Optional[str],
    file_store: Optional[FileStore],
) -> Dict[str, Any]:
    """Extracted text from files the user attached to THIS session, so
    attached-file evidence can genuinely shape the drafted document.
    Reuses FileStore + file_extraction exactly like read_attached_file.py
    (no new extraction/path logic). Returns an empty dict - never
    fabricated content - when there is nothing readable."""

    if not session_id:
        return {}

    store = file_store or FileStore()

    try:
        records = store.list_for_session(session_id)
    except Exception:
        return {}

    if not records:
        return {}

    # Most-recent first, bounded.
    records = list(reversed(records))[:_MAX_EVIDENCE_FILES]

    documents = []
    for record in records:
        path = store.path_for(record.file_id)
        if path is None:
            continue
        extraction = extract_file_text(path)
        if extraction.get("status") != "success":
            continue
        text = str(extraction.get("text", ""))[:_MAX_EVIDENCE_CHARS_PER_FILE]
        if not text.strip():
            continue
        documents.append(
            {
                "filename": record.filename,
                "text": text,
                "truncated": bool(extraction.get("truncated"))
                or len(str(extraction.get("text", ""))) > _MAX_EVIDENCE_CHARS_PER_FILE,
            }
        )

    if not documents:
        return {}

    return {"attached_documents": documents}


def _bounded_brief(brief: Dict[str, Any]) -> Dict[str, Any]:
    """A compact copy of the brief safe to return to the client for
    transparency - drops the (potentially large) verbatim policy text
    and raw evidence body, keeping the decisions that shaped the draft."""

    return {
        "document_type": brief.get("document_type"),
        "purpose": brief.get("purpose"),
        "is_urgent": brief.get("is_urgent"),
        "tone": brief.get("tone"),
        "suggested_sections": brief.get("suggested_sections"),
    }


def draft_institutional_document(
    *,
    request_text: str,
    document_type: str,
    session_id: Optional[str] = None,
    decision_context: Optional[Dict[str, Any]] = None,
    requested_output: str = "",
    composer: Optional[DocumentComposer] = None,
    file_store: Optional[FileStore] = None,
    institutional_rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Draft one institutional document. Returns the tool contract the
    rest of URI already consumes - {"status": "success", "note_sheet":
    <body>} - plus transparency fields (composed_by, drafting_brief,
    detail) that existing consumers simply ignore."""

    decision_context = decision_context or {}

    rules = institutional_rules or load_institutional_rules()
    policy_rules = _extract_drafting_rules(_read_file(_POLICY_PATH))
    soul_text = _read_file(_SOUL_PATH)

    evidence = _gather_attachment_evidence(session_id, file_store)
    # A caller may also pass already-verified evidence and preferences
    # through the decision context; merge without letting it fabricate.
    if isinstance(decision_context.get("verified_evidence"), dict):
        evidence = {**decision_context["verified_evidence"], **evidence}

    preferences = {}
    if isinstance(decision_context.get("user_preferences"), dict):
        preferences = decision_context["user_preferences"]

    brief = build_drafting_brief(
        request_text=request_text,
        requested_output=requested_output,
        document_type=document_type,
        evidence=evidence,
        preferences=preferences,
        institutional_rules=rules,
        policy_rules=policy_rules,
    )

    composer = composer or DocumentComposer()
    result = composer.compose(
        brief=brief,
        request_text=request_text,
        evidence=evidence,
        preferences=preferences,
        soul_text=soul_text,
    )

    return {
        "status": "success",
        "note_sheet": result["body"],
        "composed_by": result["composed_by"],
        "detail": result.get("detail"),
        "drafting_brief": _bounded_brief(brief),
    }


# M19: public aliases so generate_document.py (a generic Brain-authored
# document, not only a note/order) can reuse this module's policy/
# evidence/soul assembly exactly as-is, rather than re-implementing it -
# there is one place attachment evidence is gathered for drafting, one
# place the policy's drafting rules are sliced out, one place soul.md is
# read.
read_text_file = _read_file
extract_drafting_rules = _extract_drafting_rules
gather_session_evidence = _gather_attachment_evidence
POLICY_PATH = _POLICY_PATH
SOUL_PATH = _SOUL_PATH
