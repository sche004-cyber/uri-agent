"""Capability: draft an institutional office order (M17).

This capability no longer contains a document template. The prior
version returned a single hardcoded f-string - a frozen institution
banner, a literal reference number, a hardcoded date, fixed sanction
boilerplate and a fixed signature block - with the request dropped into
one slot, so every "order" came out identical and a cancellation order
was rendered with "sanction is hereby accorded" (semantically wrong).

It now provides only the document *kind* (an office order) and
delegates to the single institutional drafting path
(services/institutional_drafting.py). The Brain authors the body from
the institution's conventions (configurable data, not literals), the
operating policy's drafting rules, any attached-file evidence, and the
request's purpose - so an appointment order, a cancellation order and a
delegation order are each structured correctly and differently.
"""

from uri_core.services.institutional_drafting import (
    draft_institutional_document,
)


class InstitutionalOrderDraftCmp:
    """Thin capability wrapper - fixes only the document kind, then hands
    off to the Brain-centric drafting path. `composer` is injectable for
    tests; the default constructs the real composer lazily and falls
    back to a plain honest draft when the model is unreachable."""

    def __init__(self, composer=None):
        self._composer = composer

    def generate(self, **kwargs):
        request_text = kwargs.get("request_text", "") or ""
        session_id = kwargs.get("session_id")
        decision_context = kwargs.get("decision_context") or {}
        requested_output = kwargs.get("requested_output", "") or ""

        # M22.6 remediation: see draft_institutional_note.py's identical
        # comment - the runtime-supplied principal arrives as its own
        # top-level kwarg; fold it into decision_context so
        # draft_institutional_document's decision_context.get("principal")
        # reads a real value instead of always None.
        principal = kwargs.get("principal")
        if principal is not None:
            decision_context = dict(decision_context)
            decision_context["principal"] = principal

        return draft_institutional_document(
            request_text=request_text,
            document_type="office_order",
            session_id=session_id,
            decision_context=decision_context,
            requested_output=requested_output,
            composer=self._composer,
        )
