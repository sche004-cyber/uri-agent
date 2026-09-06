"""Real Internet web-search capability (Milestone 15 Part 1).

Architecture: the Brain decides whether research is needed, what to
search for, how to interpret results, and when evidence is sufficient
- none of that reasoning happens here. This class is pure machinery:
given the user's request text as the search query, it performs one
real web search via a real search API and returns the real results
(title/url/content) as structured evidence, exactly like
StudentRecordExtractor returns a record rather than a phrased answer.
It never decides what the results mean, never drafts an answer, and
never invents a result when the real search fails or returns nothing -
the same honesty discipline every other tool in this codebase already
follows (see extract_student_records.py).

The query is the request text itself, not something this tool (or
URI) composes - the same boundary already enforced for every other
capability (see orchestrator.py's docstring: "only a plain
capability-name string ever crosses this boundary - never the model's
proposed arguments"). The Brain's decision to select web_search, given
the user's own words, is what "deciding what to search for" means at
this boundary; this tool does not re-interpret or rewrite that query.
"""

import os

import requests

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_ENV_FILE_PATH = ".env"
_REQUEST_TIMEOUT_SECONDS = 15
_DEFAULT_MAX_RESULTS = 5


def _load_env_file(path=_ENV_FILE_PATH):
    """Minimal, dependency-free ".env" loader - KEY=VALUE lines, blank
    lines and lines starting with "#" ignored. A variable already
    present in the real process environment is never overwritten, so
    a real env var always wins over the file. Never raises - a
    missing or malformed .env degrades to "nothing loaded," exactly
    like a missing API key does further down (see execute())."""

    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key and key not in os.environ:
                    os.environ[key] = value

    except Exception:
        return


class WebSearchTool:
    """The only capability in this codebase that reaches the public
    Internet on the Brain's behalf. Every real outcome (a real result
    set, no results, a missing API key, or a network/service failure)
    is reported honestly and distinctly - never silently substituted
    with an invented result. See module docstring for the query
    boundary this respects."""

    def __init__(self, api_key=None, session=None, max_results=None):
        _load_env_file()
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self._session = session or requests
        self._max_results = max_results or _DEFAULT_MAX_RESULTS

    def execute(self, **kwargs):

        query = (kwargs.get("request_text") or "").strip()

        if not query:
            return {
                "status": "input_required",
                "query": None,
                "message": (
                    "No search query was found in the request."
                ),
            }

        if not self._api_key:
            return {
                "status": "unavailable",
                "query": query,
                "message": "URI could not perform a web search.",
                "error": (
                    "No web-search API key is configured "
                    "(TAVILY_API_KEY is not set)."
                ),
            }

        try:
            response = self._session.post(
                _TAVILY_ENDPOINT,
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": self._max_results,
                },
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )

        except requests.exceptions.RequestException as exc:
            return {
                "status": "unavailable",
                "query": query,
                "message": (
                    "URI could not reach the web-search service."
                ),
                "error": str(exc),
            }

        if response.status_code != 200:
            return {
                "status": "unavailable",
                "query": query,
                "message": (
                    "The web-search service returned an error."
                ),
                "error": (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                ),
            }

        try:
            data = response.json()
        except ValueError:
            return {
                "status": "unavailable",
                "query": query,
                "message": (
                    "The web-search service returned a response "
                    "URI could not read."
                ),
                "error": "Response was not valid JSON.",
            }

        raw_results = data.get("results") if isinstance(data, dict) else None

        if not isinstance(raw_results, list) or not raw_results:
            return {
                "status": "not_found",
                "query": query,
                "message": (
                    "The web search returned no results for this "
                    "query."
                ),
            }

        results = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
            }
            for item in raw_results
            if isinstance(item, dict)
        ]

        return {
            "status": "success",
            "query": query,
            "message": (
                f"Found {len(results)} web result(s) for this query."
            ),
            "results": results,
        }
