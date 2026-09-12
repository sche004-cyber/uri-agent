"""Real Gmail research capability (item 6 of the URI architecture spec:
"Ensure URI can use: ... Gmail research ... The Brain decides what is
needed. The Engine controls authorization and execution.").

This is pure machinery, exactly mirroring web_search.py's own
discipline: given the user's request text as the search query, it
performs one real Gmail search via GmailSearchService (already
implemented - see uri_core/services/gmail_search_service.py) and
returns the real results (subject/date/snippet) as structured
evidence. It never decides what the results mean, never drafts an
answer, and never invents a result when authentication fails or the
search finds nothing - the same honesty discipline every other tool in
this codebase already follows.

GmailSearchService.search_emails() itself returns a plain list
(including an inline {"error": ...} entry on failure, for its own
pre-existing callers) - this wrapper is the boundary that translates
that into the same {"status", "query", "message", ...} envelope shape
web_search.py already establishes, so the Brain sees one consistent
contract regardless of which real research tool it used.
"""

from uri_core.services.gmail_search_service import GmailSearchService

_DEFAULT_MAX_RESULTS = 5


class GmailSearchTool:
    """The query is the request text itself, not something this tool
    (or URI) composes - the same boundary already enforced for every
    other capability (see web_search.py's own module note)."""

    def __init__(self, service=None, max_results=None):
        self._service = service or GmailSearchService()
        self._max_results = max_results or _DEFAULT_MAX_RESULTS

    # 2026-09-12 (User directive): "how many unread emails do I have"
    # is a COUNT question, not a search-and-list one - routing it
    # through search_emails (capped at max_results, returning
    # subject/snippet rows) would under-report the real count whenever
    # more than max_results messages are unread, and answer a question
    # that was never asked. Detected narrowly (both "unread" and a
    # count-shaped word) so an ordinary "find my unread email from
    # Chetan" search-style request is unaffected.
    _UNREAD_COUNT_TRIGGERS = ("how many", "count", "number of")

    def execute(self, **kwargs):

        query = (kwargs.get("request_text") or "").strip()

        if not query:
            return {
                "status": "input_required",
                "query": None,
                "message": "No search query was found in the request.",
            }

        lowered = query.lower()
        if "unread" in lowered and any(
            trigger in lowered for trigger in self._UNREAD_COUNT_TRIGGERS
        ):
            return self._unread_count()

        if not self._service.authenticate():
            return {
                "status": "unavailable",
                "query": query,
                "message": "URI could not search Gmail.",
                "error": (
                    "Gmail authentication failed or credentials.json "
                    "is missing."
                ),
            }

        try:
            raw_results = self._service.search_emails(
                query=query, max_results=self._max_results
            )
        except Exception as exc:
            return {
                "status": "unavailable",
                "query": query,
                "message": "URI could not reach the Gmail service.",
                "error": str(exc),
            }

        if not isinstance(raw_results, list):
            return {
                "status": "unavailable",
                "query": query,
                "message": (
                    "Gmail search returned an unreadable response."
                ),
                "error": "search_emails() did not return a list.",
            }

        if len(raw_results) == 1 and isinstance(raw_results[0], dict) and (
            "error" in raw_results[0]
        ):
            return {
                "status": "unavailable",
                "query": query,
                "message": "URI could not complete the Gmail search.",
                "error": str(raw_results[0]["error"]),
            }

        if not raw_results:
            return {
                "status": "not_found",
                "query": query,
                "message": (
                    "The Gmail search returned no results for this "
                    "query."
                ),
            }

        results = [
            {
                "subject": item.get("subject"),
                "date": item.get("date"),
                "snippet": item.get("snippet"),
            }
            for item in raw_results
            if isinstance(item, dict)
        ]

        return {
            "status": "success",
            "query": query,
            "message": f"Found {len(results)} Gmail result(s) for this query.",
            "results": results,
        }

    def _unread_count(self) -> dict:
        result = self._service.get_unread_count()

        if not result.get("success"):
            return {
                "status": "unavailable",
                "query": "is:unread",
                "message": "URI could not check your unread Gmail count.",
                "error": result.get("error"),
            }

        count = result["unread_count"]
        return {
            "status": "success",
            "query": "is:unread",
            "unread_count": count,
            "message": (
                f"You have {count} unread Gmail message"
                f"{'s' if count != 1 else ''} right now."
            ),
        }
