"""M16 Priority 4: find an existing Gmail draft relevant to a request.

Wires the already-built, READ-ONLY GmailDraftService (see
services/gmail_draft_service.py) into the capability registry so the
Brain can actually select it. Before M16 that service existed but was
reachable from nothing.

Strictly read-only, matching GmailService's own discipline: this
searches existing drafts and returns what it finds. It never creates,
modifies, sends, or deletes anything - there is deliberately no
write path here.

Pure machinery, mirroring web_search.py/gmail_search.py: the Brain
decides whether an existing draft is worth looking for; this returns
the real draft as evidence and never composes or invents one. A
missing credential, an unreachable service, or simply no relevant
draft are each reported distinctly rather than collapsed into a
generic failure.
"""

from uri_core.services.gmail_draft_service import GmailDraftService


class GmailFindDraftTool:
    """The query is the request text itself - the same argument
    boundary every other capability respects (see web_search.py)."""

    def __init__(self, draft_service=None):
        self._draft_service = draft_service or GmailDraftService()

    def execute(self, **kwargs):

        query = (kwargs.get("request_text") or "").strip()

        if not query:
            return {
                "status": "input_required",
                "query": None,
                "message": "No search query was found in the request.",
            }

        try:
            draft = self._draft_service.search_latest_relevant_draft(
                query=query
            )

        except Exception as error:
            return {
                "status": "unavailable",
                "query": query,
                "message": "URI could not search Gmail drafts.",
                "error": str(error),
            }

        if draft is None:
            # GmailDraftService returns None both for "not connected"
            # and for "genuinely nothing relevant". URI cannot tell
            # those apart from this return value alone, and says so
            # rather than asserting one of them.
            return {
                "status": "not_found",
                "query": query,
                "message": (
                    "No relevant Gmail draft was found. If Gmail is "
                    "not connected, that would also produce this "
                    "result."
                ),
            }

        return {
            "status": "success",
            "query": query,
            "message": "Found a relevant existing Gmail draft.",
            "draft": draft,
        }
