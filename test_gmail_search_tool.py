"""Item 6 of the URI architecture spec: real Gmail research capability.
Never touches the real network/Gmail API here - a fake GmailSearchService
stands in, mirroring test_web_search_tool.py's exact discipline (fake
the underlying service, test only this wrapper's own request-shaping/
result-honesty logic). Real, live verification (with no credentials
configured in this environment) happens separately.
"""

import unittest

from uri_core.tools.gmail_search import GmailSearchTool


class _FakeGmailSearchService:

    def __init__(self, authenticated=True, search_return=None, search_raises=None):
        self._authenticated = authenticated
        self._search_return = search_return if search_return is not None else []
        self._search_raises = search_raises
        self.search_calls = []

    def authenticate(self):
        return self._authenticated

    def search_emails(self, query, max_results=5):
        self.search_calls.append({"query": query, "max_results": max_results})
        if self._search_raises:
            raise self._search_raises
        return self._search_return


class MissingQueryTests(unittest.TestCase):

    def test_empty_request_text_asks_for_a_query_instead_of_guessing(self):
        service = _FakeGmailSearchService()
        tool = GmailSearchTool(service=service)

        result = tool.execute(request_text="")

        self.assertEqual(result["status"], "input_required")
        self.assertEqual(service.search_calls, [])

    def test_missing_request_text_key_is_handled_safely(self):
        service = _FakeGmailSearchService()
        tool = GmailSearchTool(service=service)

        result = tool.execute()

        self.assertEqual(result["status"], "input_required")
        self.assertEqual(service.search_calls, [])


class MissingCredentialsTests(unittest.TestCase):

    def test_authentication_failure_is_reported_honestly_not_as_a_fake_result(
        self,
    ):
        service = _FakeGmailSearchService(authenticated=False)
        tool = GmailSearchTool(service=service)

        result = tool.execute(request_text="student insurance renewal")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("credentials.json", result["error"])
        self.assertEqual(service.search_calls, [])
        self.assertNotIn("results", result)


class RealResultsAreReturnedAsEvidenceTests(unittest.TestCase):
    """The core property: real Gmail results reach the caller as
    structured evidence - URI never phrases an answer from them here,
    only relays them."""

    def test_successful_search_returns_the_real_results_as_evidence(self):
        service = _FakeGmailSearchService(
            search_return=[
                {
                    "subject": "Insurance renewal notice",
                    "date": "Mon, 1 Sep 2026 10:00:00",
                    "snippet": "Please renew before ...",
                },
                {
                    "subject": "Re: Insurance renewal notice",
                    "date": "Tue, 2 Sep 2026 09:00:00",
                    "snippet": "Acknowledged, submitting ...",
                },
            ]
        )
        tool = GmailSearchTool(service=service)

        result = tool.execute(request_text="student insurance renewal")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["query"], "student insurance renewal")
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(
            result["results"][0]["subject"], "Insurance renewal notice"
        )
        # The real query actually sent matches the request text - never
        # a fixed/default query regardless of input.
        self.assertEqual(
            service.search_calls[0]["query"], "student insurance renewal"
        )


class HonestFailureTests(unittest.TestCase):
    """Every real failure mode is reported plainly and distinctly -
    never silently replaced with an invented result."""

    def test_no_results_is_reported_as_not_found_not_invented(self):
        service = _FakeGmailSearchService(search_return=[])
        tool = GmailSearchTool(service=service)

        result = tool.execute(request_text="an extremely obscure query")

        self.assertEqual(result["status"], "not_found")
        self.assertNotIn("results", result)

    def test_inline_error_entry_is_reported_as_unavailable(self):
        service = _FakeGmailSearchService(
            search_return=[{"error": "Gmail API quota exceeded."}]
        )
        tool = GmailSearchTool(service=service)

        result = tool.execute(request_text="anything")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("quota", result["error"])

    def test_search_exception_is_reported_as_unavailable(self):
        service = _FakeGmailSearchService(
            search_raises=RuntimeError("no route to host")
        )
        tool = GmailSearchTool(service=service)

        result = tool.execute(request_text="anything")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("no route to host", result["error"])


if __name__ == "__main__":
    unittest.main()
