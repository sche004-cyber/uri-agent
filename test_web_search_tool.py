"""Milestone 15 Part 1: real Internet web-search capability. Never
touches the real network here - a fake HTTP session stands in for
`requests`, mirroring test_extract_student_records.py's exact
discipline (fake the underlying network/service, test only this
tool's own request-shaping/result-honesty logic). Real, live network
verification happens separately, against the actual Tavily API.
"""

import unittest

from uri_core.tools.web_search import WebSearchTool


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


class _FakeSession:
    """Stands in for the `requests` module - only .post(...) is used
    by WebSearchTool. Records every call for assertions."""

    def __init__(self, response=None, raises=None):
        self._response = response
        self._raises = raises
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        if self._raises:
            raise self._raises
        return self._response


class MissingQueryTests(unittest.TestCase):

    def test_empty_request_text_asks_for_a_query_instead_of_guessing(self):
        session = _FakeSession()
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute(request_text="")

        self.assertEqual(result["status"], "input_required")
        self.assertEqual(session.calls, [])

    def test_missing_request_text_key_is_handled_safely(self):
        session = _FakeSession()
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute()

        self.assertEqual(result["status"], "input_required")
        self.assertEqual(session.calls, [])


class MissingApiKeyTests(unittest.TestCase):

    def test_no_api_key_is_reported_honestly_not_as_a_fake_result(self):
        session = _FakeSession()
        tool = WebSearchTool(api_key=None, session=session)
        tool._api_key = None  # guard against a real .env/.env.example leaking in

        result = tool.execute(request_text="latest Mars rover news")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("API key", result["error"])
        self.assertEqual(session.calls, [])
        self.assertNotIn("results", result)


class RealResultsAreReturnedAsEvidenceTests(unittest.TestCase):
    """The core property: real results (title/url/content) reach the
    caller as structured evidence - URI never phrases an answer from
    them here, only relays them."""

    def test_successful_search_returns_the_real_results_as_evidence(self):
        session = _FakeSession(
            response=_FakeResponse(
                status_code=200,
                json_data={
                    "results": [
                        {
                            "title": "Mars rover update",
                            "url": "https://example.com/mars",
                            "content": "The rover found new evidence of ...",
                        },
                        {
                            "title": "NASA press release",
                            "url": "https://nasa.gov/press",
                            "content": "Official statement about the mission.",
                        },
                    ]
                },
            )
        )
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute(request_text="latest Mars rover news")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["query"], "latest Mars rover news")
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(
            result["results"][0]["url"], "https://example.com/mars"
        )
        self.assertEqual(
            result["results"][1]["title"], "NASA press release"
        )
        # The real query actually sent matches the request text -
        # never a fixed/default query regardless of input.
        self.assertEqual(
            session.calls[0]["json"]["query"], "latest Mars rover news"
        )
        self.assertEqual(session.calls[0]["json"]["api_key"], "fake-key")

    def test_two_different_queries_produce_different_real_requests(self):
        session = _FakeSession(
            response=_FakeResponse(
                status_code=200, json_data={"results": []}
            )
        )
        tool = WebSearchTool(api_key="fake-key", session=session)

        tool.execute(request_text="query about topic A")
        tool.execute(request_text="query about topic B")

        self.assertEqual(
            [call["json"]["query"] for call in session.calls],
            ["query about topic A", "query about topic B"],
        )


class HonestFailureTests(unittest.TestCase):
    """Every real failure mode is reported plainly and distinctly -
    never silently replaced with an invented result."""

    def test_no_results_is_reported_as_not_found_not_invented(self):
        session = _FakeSession(
            response=_FakeResponse(
                status_code=200, json_data={"results": []}
            )
        )
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute(request_text="an extremely obscure query")

        self.assertEqual(result["status"], "not_found")
        self.assertNotIn("results", result)

    def test_non_200_response_is_reported_as_unavailable(self):
        session = _FakeSession(
            response=_FakeResponse(status_code=401, text="invalid key")
        )
        tool = WebSearchTool(api_key="wrong-key", session=session)

        result = tool.execute(request_text="anything")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("401", result["error"])

    def test_network_failure_is_reported_as_unavailable(self):
        import requests

        session = _FakeSession(
            raises=requests.exceptions.ConnectionError("no route to host")
        )
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute(request_text="anything")

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("no route to host", result["error"])

    def test_unparseable_response_is_reported_as_unavailable(self):
        session = _FakeSession(
            response=_FakeResponse(status_code=200, json_data=None)
        )
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute(request_text="anything")

        self.assertEqual(result["status"], "unavailable")

    def test_malformed_results_shape_is_reported_as_not_found(self):
        session = _FakeSession(
            response=_FakeResponse(
                status_code=200, json_data={"results": "not a list"}
            )
        )
        tool = WebSearchTool(api_key="fake-key", session=session)

        result = tool.execute(request_text="anything")

        self.assertEqual(result["status"], "not_found")


if __name__ == "__main__":
    unittest.main()
