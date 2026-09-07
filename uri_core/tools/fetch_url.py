"""Capability: fetch and read one web page/document by URL (M19).

Closes the audit's #5 gap: web_search can find a source, but URI had
no way to actually open it - so "public documents/PDFs and meeting
minutes" was limited to whatever short snippet Tavily returned. This
tool fetches the URL and extracts its readable text, reusing
file_extraction.py's existing PDF/text/spreadsheet/docx extractors
(the identical machinery read_attached_file.py already uses for user
uploads) rather than adding a second extraction path.

Argument boundary, unchanged from every other capability (see
orchestrator.py's "only a plain capability-name string ever crosses
this boundary" - the model's own proposed arguments are never read):
this tool takes NO model-supplied url argument. The URL is extracted
deterministically from request_text - the runtime-supplied user/goal
text - via a plain regex, exactly the same discipline
draft_institutional_note.py already uses to extract a subject from
request_text. If the Brain wants URI to read a specific page, the user
(or the Brain's own workflow goal, which always originates from the
user's real text - see orchestrator.py's fallback_goal) must actually
say the URL; URI never lets a model choose what to fetch.

Bounded and safe: a strict http(s)-only scheme check, a content-length
cap enforced on real bytes received (never a client-declared header),
a short timeout, and no redirect to a non-http(s) scheme. Never
invents content when a fetch fails - reports the real reason.
"""

import os
import re
import tempfile
from html.parser import HTMLParser
from typing import Optional

import requests

from uri_core.services.file_extraction import extract_file_text

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

_TIMEOUT_SECONDS = 15
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB - a research fetch, not a big-file store.

# Content-types this tool knows how to turn into readable text. Anything
# else is reported honestly as unsupported rather than guessed at.
_EXTENSION_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


class _TextExtractingHTMLParser(HTMLParser):
    """A minimal, dependency-free HTML-to-text reader - deliberately
    not a full renderer, just enough to turn a page into readable
    prose for the Brain to cite, without adding a new parsing library
    (no BeautifulSoup/lxml) for what is otherwise a small, bounded
    need."""

    _SKIP_TAGS = {"script", "style", "noscript", "head"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.chunks.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.chunks)


def _extract_url(request_text: str) -> Optional[str]:
    match = _URL_RE.search(request_text or "")
    if not match:
        return None
    url = match.group(0).rstrip(").,;:!?")
    return url


class FetchUrlTool:
    """Fetches one URL and returns its readable text as evidence. Pure
    machinery, exactly like web_search.py/read_attached_file.py: it
    never decides what a page means, never drafts an answer from it,
    and never invents content when a fetch fails."""

    def __init__(self, session=None, timeout: int = _TIMEOUT_SECONDS):
        self._session = session or requests
        self._timeout = timeout

    def execute(self, **kwargs) -> dict:
        request_text = kwargs.get("request_text", "") or ""

        url = _extract_url(request_text)

        if url is None:
            return {
                "status": "input_required",
                "message": (
                    "No URL was found in the request, so URI does not "
                    "know what to fetch."
                ),
            }

        if not url.lower().startswith(("http://", "https://")):
            return {
                "status": "input_required",
                "message": "Only http(s) URLs can be fetched.",
                "url": url,
            }

        try:
            response = self._session.get(
                url,
                timeout=self._timeout,
                headers={"User-Agent": "URI/1.0 (institutional research assistant)"},
                stream=True,
            )
        except requests.RequestException as error:
            return {
                "status": "unavailable",
                "message": "URI could not reach that URL.",
                "error": str(error),
                "url": url,
            }

        if response.status_code != 200:
            return {
                "status": "unavailable",
                "message": f"The page returned HTTP {response.status_code}.",
                "url": url,
            }

        content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()

        content = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > _MAX_BYTES:
                    return {
                        "status": "unavailable",
                        "message": (
                            f"The page exceeded the {_MAX_BYTES // (1024 * 1024)} MB "
                            "fetch limit."
                        ),
                        "url": url,
                    }
        finally:
            response.close()

        if content_type in ("text/html", "application/xhtml+xml") or not content_type:
            try:
                html_text = bytes(content).decode(response.encoding or "utf-8", errors="replace")
            except (LookupError, TypeError):
                html_text = bytes(content).decode("utf-8", errors="replace")

            parser = _TextExtractingHTMLParser()
            parser.feed(html_text)
            text = parser.text().strip()

            if not text:
                return {
                    "status": "empty",
                    "message": "The page was fetched but contained no readable text.",
                    "url": url,
                }

            return {
                "status": "success",
                "url": url,
                "content_type": content_type or "text/html",
                "text": text[:8000],
                "truncated": len(text) > 8000,
            }

        extension = _EXTENSION_BY_CONTENT_TYPE.get(content_type)

        if extension is None:
            return {
                "status": "unsupported",
                "message": (
                    f"URI has no reader for content type '{content_type or 'unknown'}'."
                ),
                "url": url,
                "content_type": content_type,
            }

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as handle:
                handle.write(bytes(content))
                tmp_path = handle.name

            extraction = extract_file_text(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        extraction["url"] = url
        extraction["content_type"] = content_type
        return extraction
