"""Validation profile for Brain-composed DOCUMENT bodies (M17).

Deliberately separate from response_validation.py, which validates the
short *narrative* URI shows when explaining an outcome and is bounded
by tight length caps (MAX_NARRATIVE_LENGTH=2000, non-success <=400,
a 3x evidence-expansion ratio). Those caps are correct for a status
explanation and completely wrong for a real institutional document -
an office order or a detailed noting legitimately runs to many
paragraphs. Reusing the narrative profile would reject every genuine
document, which is one reason the old architecture never let the Brain
author document bodies at all.

This profile enforces what actually matters for a drafted document:
  - it is non-empty and within a generous ceiling (a guard against a
    runaway generation, not a stylistic cap);
  - it reads as an institutional document, not an AI chat turn (policy
    section 11: "A draft should look like an institutional document,
    not an AI explanation.") - so an opening like "Sure, here's the
    draft" or "I have drafted..." is rejected;
  - it contains no credential-shaped material (reusing the same
    security screen the rest of the codebase uses).

It intentionally does NOT apply the narrative success-claim guard:
phrases such as "sanction is hereby accorded" are legitimate *document
content*, not URI falsely claiming it performed an action. Whether URI
actually issued/filed anything is decided and reported entirely
separately (the tool's own status and the outcome narrative), never
inferred from the document's words.
"""

from typing import Any, Dict, Optional

from uri_core.core.security_guards import looks_like_credential_value


# A generous ceiling: large enough for a long multi-clause order or a
# detailed noting, small enough to catch a degenerate runaway
# generation. This is a safety bound, not a style limit.
MAX_DOCUMENT_LENGTH = 12000

# A minimal floor - a real document is more than a fragment. Kept low so
# a deliberately terse notice is still allowed.
MIN_DOCUMENT_LENGTH = 40


# Opening phrasings that mark the text as an assistant talking *about* a
# draft rather than the draft itself. Matched only at the very start
# (after stripping), so the same words appearing inside legitimate
# document prose never trip this.
_CHATTY_OPENERS = (
    "sure",
    "certainly",
    "here is",
    "here's",
    "here you go",
    "i have drafted",
    "i've drafted",
    "i have prepared",
    "i've prepared",
    "below is",
    "as requested, here",
    "of course",
    "okay,",
    "ok,",
    "i can help",
    "i'll draft",
    "i will draft",
    "certainly!",
)


def _looks_like_chat_preamble(body: str) -> bool:
    head = body.strip().lower()
    return any(head.startswith(opener) for opener in _CHATTY_OPENERS)


def validate_drafted_document(
    body: Optional[str],
    brief: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Returns {"valid": bool, "reason": str | None}. A rejected draft
    is never shown; the caller falls back to a plain, honest rendering
    (see document_composer.py). False positives (a good draft rejected)
    are the acceptable failure direction - the fallback is still a real,
    if plainer, document."""

    if not isinstance(body, str):
        return {"valid": False, "reason": "Draft was not text."}

    stripped = body.strip()

    if len(stripped) < MIN_DOCUMENT_LENGTH:
        return {
            "valid": False,
            "reason": "Draft was too short to be a real document.",
        }

    if len(stripped) > MAX_DOCUMENT_LENGTH:
        return {
            "valid": False,
            "reason": (
                f"Draft exceeded {MAX_DOCUMENT_LENGTH} characters, which "
                "suggests a runaway generation rather than a document."
            ),
        }

    if _looks_like_chat_preamble(stripped):
        return {
            "valid": False,
            "reason": (
                "Draft opened like an AI chat reply rather than an "
                "institutional document."
            ),
        }

    # Credential-shaped material must never appear in a drafted document
    # (the model could echo something it was mistakenly given). Screen
    # line by line so one bad line rejects the whole draft.
    for line in stripped.splitlines():
        if looks_like_credential_value(line.strip()):
            return {
                "valid": False,
                "reason": "Draft contained credential-shaped text.",
            }

    return {"valid": True, "reason": None}
