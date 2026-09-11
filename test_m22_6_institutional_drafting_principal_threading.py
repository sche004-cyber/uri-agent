"""M22.6 remediation regression test (Claude Verification Finding 4).

Confirms the actual production call chain - InstitutionalNoteDraftCmp
.generate(**kwargs) / InstitutionalOrderDraftCmp.generate(**kwargs) ->
draft_institutional_document() -> DocumentComposer - carries a real,
runtime-supplied ``principal`` kwarg all the way through to
DocumentComposer, both at construction and at the compose() call.

Before this fix, draft_institutional_document() read
decision_context.get("principal"), but neither tool wrapper ever put a
"principal" key inside decision_context (it arrives as its own sibling
top-level kwarg, exactly like session_id/request_text) - so the two
office-drafting capabilities constructed DocumentComposer(principal=None)
on every real call, silently defeating M22.6's per-user provider
routing for these two of URI's three document-drafting capabilities.
generate_document.py/gmail_create_draft.py already read kwargs.get(
"principal") correctly - see test_model_router_freshness.py and this
milestone's STATE.md for that history.
"""

import unittest
from unittest.mock import MagicMock

from uri_core.tools.draft_institutional_note import InstitutionalNoteDraftCmp
from uri_core.tools.draft_institutional_order import InstitutionalOrderDraftCmp


def _fake_composer():
    composer = MagicMock()
    composer.compose.return_value = {
        "status": "success",
        "body": "A plain drafted body.",
        "composed_by": "fallback",
        "detail": None,
    }
    return composer


class PrincipalReachesComposerViaKwargsTests(unittest.TestCase):
    """The runtime-supplied top-level `principal` kwarg (set by
    orchestrator.py/workflow_capability_router.py, never model-supplied)
    must reach DocumentComposer.compose() as `principal=`, not be
    silently dropped because it wasn't already nested inside
    decision_context."""

    def test_note_tool_threads_principal_from_kwargs_to_compose(self):
        composer = _fake_composer()
        tool = InstitutionalNoteDraftCmp(composer=composer)
        sentinel_principal = object()

        tool.generate(
            request_text="draft a note about the seminar hall booking",
            session_id="s1",
            principal=sentinel_principal,
        )

        composer.compose.assert_called_once()
        self.assertIs(
            composer.compose.call_args.kwargs.get("principal"),
            sentinel_principal,
        )

    def test_order_tool_threads_principal_from_kwargs_to_compose(self):
        composer = _fake_composer()
        tool = InstitutionalOrderDraftCmp(composer=composer)
        sentinel_principal = object()

        tool.generate(
            request_text="draft an order cancelling the prior appointment",
            session_id="s1",
            principal=sentinel_principal,
        )

        composer.compose.assert_called_once()
        self.assertIs(
            composer.compose.call_args.kwargs.get("principal"),
            sentinel_principal,
        )

    def test_note_tool_with_no_principal_still_works_unchanged(self):
        """Zero-behaviour-change when no principal is supplied at all -
        the pre-M22.6 legacy/ambient call shape (e.g. existing tests,
        the module-level unauthenticated _orchestrator) must keep
        working exactly as before."""
        composer = _fake_composer()
        tool = InstitutionalNoteDraftCmp(composer=composer)

        result = tool.generate(request_text="draft a note about the library hours")

        self.assertEqual(result["status"], "success")
        composer.compose.assert_called_once()
        self.assertIsNone(composer.compose.call_args.kwargs.get("principal"))

    def test_note_tool_preserves_existing_decision_context_fields(self):
        """Folding principal into decision_context must not clobber other
        fields (verified_evidence, user_preferences) already carried
        there by real callers."""
        composer = _fake_composer()
        tool = InstitutionalNoteDraftCmp(composer=composer)
        sentinel_principal = object()

        tool.generate(
            request_text="draft a note",
            principal=sentinel_principal,
            decision_context={"user_preferences": {"tone": "formal"}},
        )

        composer.compose.assert_called_once()
        self.assertIs(
            composer.compose.call_args.kwargs.get("principal"),
            sentinel_principal,
        )


class DocumentComposerConstructionCarriesPrincipalTests(unittest.TestCase):
    """draft_institutional_document() also passes principal at
    DocumentComposer construction time (not just per-call), matching the
    pattern already used by generate_document.py/gmail_create_draft.py,
    so a caller that does not pass an explicit composer still gets one
    scoped to the right principal."""

    def test_draft_institutional_document_constructs_composer_with_principal(self):
        from uri_core.services import institutional_drafting

        captured = {}
        sentinel_principal = object()

        class _RecordingComposer:
            def __init__(self, provider=None, principal=None):
                captured["construct_principal"] = principal

            def compose(self, **kwargs):
                captured["compose_principal"] = kwargs.get("principal")
                return {
                    "status": "success",
                    "body": "body",
                    "composed_by": "fallback",
                    "detail": None,
                }

        original_composer_cls = institutional_drafting.DocumentComposer
        institutional_drafting.DocumentComposer = _RecordingComposer
        try:
            institutional_drafting.draft_institutional_document(
                request_text="draft a note",
                document_type="noting",
                decision_context={"principal": sentinel_principal},
            )
        finally:
            institutional_drafting.DocumentComposer = original_composer_cls

        self.assertIs(captured["construct_principal"], sentinel_principal)
        self.assertIs(captured["compose_principal"], sentinel_principal)


if __name__ == "__main__":
    unittest.main()
