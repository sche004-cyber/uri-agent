"""Pinned CLI runner for yt-dlp metadata extraction.

Developer-authored, committed, code-reviewed runner.
Reads JSON input with 'url' from stdin, executes pinned yt-dlp to extract
metadata (--dump-json), and outputs JSON to stdout.
No shell execution, no downloads, no credential handling, no transcript action.
"""

from __future__ import annotations

import json
import ipaddress
import socket
import subprocess
import sys
from typing import Any, Dict
from urllib.parse import urlparse

from uri_core.external.descriptors.yt_dlp import PINNED_YT_DLP_VERSION

_ALLOWED_HOST = "commons.wikimedia.org"
_ALLOWED_PATH_PREFIX = "/wiki/File:"
_MAX_INPUT_BYTES = 4096
_MAX_TEXT_LENGTH = 1000


def _installed_version() -> str:
    """Return the version loaded by this exact Python interpreter.

    The subsequent ``python -m yt_dlp`` call uses the same interpreter, so a
    mismatch is refused before any network-capable subprocess is launched.
    """
    try:
        from yt_dlp.version import __version__
    except Exception as exc:
        raise RuntimeError("pinned yt-dlp dependency is unavailable") from exc
    return str(__version__)


def _validate_url(url: str) -> str:
    """Restrict the entry slice to one trusted public metadata source.

    This is intentionally narrower than a general web fetcher: a read-only
    metadata command still makes network requests, so accepting arbitrary
    HTTP(S) URLs would expose loopback/private-network and local-service
    probing.  The source is developer-selected, not a user/model-controlled
    host, and its resolved addresses must be globally routable.
    """
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("URL must be a bounded string")
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.hostname != _ALLOWED_HOST
        or not parsed.path.startswith(_ALLOWED_PATH_PREFIX)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("URL is outside the bounded public metadata source")
    try:
        addresses = socket.getaddrinfo(
            _ALLOWED_HOST, 443, type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise ValueError("bounded metadata source could not be resolved") from exc
    if not addresses:
        raise ValueError("bounded metadata source has no resolved address")
    for _family, _type, _proto, _canonname, sockaddr in addresses:
        try:
            address = ipaddress.ip_address(sockaddr[0])
        except ValueError as exc:
            raise ValueError("bounded metadata source resolved invalid address") from exc
        if not address.is_global:
            raise ValueError("bounded metadata source resolved non-public address")
    return url


def _bounded_text(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > _MAX_TEXT_LENGTH:
        raise ValueError(f"yt-dlp output field {field} is invalid")
    return value


def _bounded_result(raw: Any) -> Dict[str, Any]:
    """Return only the reviewed metadata surface, never raw yt-dlp output."""
    if not isinstance(raw, dict):
        raise ValueError("yt-dlp output must be one JSON object")
    result: Dict[str, Any] = {}
    for name in ("id", "title", "extractor", "webpage_url", "uploader", "upload_date"):
        value = _bounded_text(raw.get(name), field=name)
        if value is not None:
            result[name] = value
    duration = raw.get("duration")
    if duration is not None:
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0 or duration > 86_400:
            raise ValueError("yt-dlp output duration is invalid")
        result["duration"] = duration
    if not result.get("id") or not result.get("title"):
        raise ValueError("yt-dlp output is missing required metadata")
    return result

# Ensure UTF-8 output encoding on all platforms including Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")


def extract_metadata(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    url = _validate_url(url)
    installed_version = _installed_version()
    if installed_version != PINNED_YT_DLP_VERSION:
        raise RuntimeError(
            f"yt-dlp version {installed_version!r} does not match pinned "
            f"version {PINNED_YT_DLP_VERSION!r}"
        )

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--ignore-config",
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        "--skip-download",
        "--",
        url,
    ]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        err = completed.stderr.strip() or f"yt-dlp exited with code {completed.returncode}"
        raise RuntimeError(err)

    try:
        return _bounded_result(json.loads(completed.stdout))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse yt-dlp JSON output: {exc}")


def main() -> None:
    try:
        raw_in = sys.stdin.read()
        if not raw_in.strip() or len(raw_in.encode("utf-8")) > _MAX_INPUT_BYTES:
            sys.stderr.write("Missing input JSON on stdin\n")
            sys.exit(1)
        raw_in = raw_in.lstrip("\ufeff").strip()
        data = json.loads(raw_in)
        if not isinstance(data, dict) or set(data) != {"url"}:
            sys.stderr.write("Input JSON must contain only the required url parameter\n")
            sys.exit(1)
        url = data.get("url")
        if not url:
            sys.stderr.write("Input JSON missing required 'url' parameter\n")
            sys.exit(1)
        metadata = extract_metadata(url)
        sys.stdout.write(json.dumps(metadata))
        sys.stdout.flush()
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
