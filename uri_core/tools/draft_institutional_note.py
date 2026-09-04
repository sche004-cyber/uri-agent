import re

from uri_core.services.noting_generator import generate_noting

# Strips a leading drafting instruction ("draft a note about ...",
# "prepare a noting regarding ...") so the remaining text is the
# actual subject matter, not the command that asked for it.
_LEADING_COMMAND_RE = re.compile(
    r"^\s*(?:please\s+)?(?:draft|prepare|write|create|generate)\s+"
    r"(?:a|an|the)?\s*(?:noting|note|office\s+note)s?\s*"
    r"(?:regarding|about|for|on|concerning)?\s*",
    re.IGNORECASE,
)

_JUSTIFICATION_RE = re.compile(r"\b(?:because|since)\s+(.+)$", re.IGNORECASE)

_APPROVAL_RE = re.compile(
    r"\b((?:approval|sanction|permission)\s+(?:for|of|to)\s+.+?)(?:\.|$)",
    re.IGNORECASE,
)


def _extract_subject(request_text: str) -> str:
    text = request_text.strip()

    if not text:
        return "Administrative Matter"

    # Cut before any justification/approval clause so the subject
    # doesn't duplicate text that is drafted separately below.
    for clause_re in (_JUSTIFICATION_RE, _APPROVAL_RE):
        clause_match = clause_re.search(text)
        if clause_match:
            text = text[:clause_match.start()].strip()

    if not text:
        return "Administrative Matter"

    stripped = _LEADING_COMMAND_RE.sub("", text).strip()
    subject = (stripped or text).rstrip(".")

    if not subject:
        return "Administrative Matter"

    return subject[0].upper() + subject[1:]


def _extract_justification(request_text: str) -> str:
    match = _JUSTIFICATION_RE.search(request_text)
    return match.group(1).strip() if match else ""


def _extract_approval_requested(request_text: str) -> str:
    match = _APPROVAL_RE.search(request_text)
    return match.group(1).strip() if match else ""


class InstitutionalNoteDraftCmp:
    """Drafts an administrative noting from the actual request text,
    via the real noting_generator - the same document generator used
    elsewhere in URI's drafting architecture. The subject,
    justification, and approval being sought are all derived from
    what was actually asked; no institutional fact is claimed as
    verified evidence unless a verified fact source is actually
    wired in (there isn't one on this single-turn tool call), so
    evidence is left empty rather than invented."""

    def __init__(self):
        pass

    def generate(self, **kwargs):
        request_text = kwargs.get("request_text", "") or ""

        task_facts = {
            "subject": _extract_subject(request_text),
            "justification": _extract_justification(request_text),
            "approval_requested": _extract_approval_requested(request_text),
        }

        note_content = generate_noting(
            {
                "task": "noting",
                "task_facts": task_facts,
                "verified_evidence": {},
            }
        )

        return {"status": "success", "note_sheet": note_content}
