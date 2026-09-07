"""Capability: draft an institutional office note / noting (M17).

This capability no longer contains a document template. It provides the
document *kind* (a noting) and delegates to the single institutional
drafting path (services/institutional_drafting.py), which supplies the
Brain with the institution's conventions, the operating policy's
drafting rules, any attached-file evidence, and the caller's
preferences, then asks the Brain to author the body. Structure adapts
to the request's purpose (an approval note, a committee-recommendation
note, an urgent note and a procurement note come out differently),
because the Brain - not this file - decides it.

The prior version derived a fixed NOTING/Subject/Background/
justification/proposal skeleton in Python (via the retired
noting_generator) regardless of purpose; that hardcoded generator is
gone.
"""

from uri_core.services.institutional_drafting import (
    draft_institutional_document,
)


class InstitutionalNoteDraftCmp:
    """Thin capability wrapper - fixes only the document kind, then hands
    off to the Brain-centric drafting path. `composer` is injectable for
    tests; the default path constructs the real (Ollama-backed) composer
    lazily, and falls back to a plain honest draft when the model is
    unreachable, so this tool never requires a running model to return a
    document."""

    def __init__(self, composer=None):
        self._composer = composer

    def generate(self, **kwargs):
        request_text = kwargs.get("request_text", "") or ""
        session_id = kwargs.get("session_id")
        decision_context = kwargs.get("decision_context") or {}
        requested_output = kwargs.get("requested_output", "") or ""

        return draft_institutional_document(
            request_text=request_text,
            document_type="noting",
            session_id=session_id,
            decision_context=decision_context,
            requested_output=requested_output,
            composer=self._composer,
        )
