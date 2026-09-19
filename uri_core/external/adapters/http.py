from __future__ import annotations

import ipaddress
import json
from typing import Any, Mapping
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


def is_loopback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme != "http" or not parsed.hostname:
            return False
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except (ValueError, TypeError):
        return False


class SafeLoopbackRedirectHandler(HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 3

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_loopback_url(newurl):
            raise ValueError(f"HTTP fixture redirect target is not a permitted loopback URL: {newurl}")
        m = req.get_method()
        if code in (307, 308) and m == "POST":
            return Request(
                newurl,
                data=req.data,
                headers=dict(req.headers),
                origin_req_host=req.origin_req_host,
                unverifiable=True,
                method="POST",
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def execute(descriptor: Mapping[str, Any], _action_name: str, inputs: Mapping[str, Any]) -> dict:
    config = descriptor.get("transport_config")
    config = config if isinstance(config, Mapping) else {}
    endpoint = config.get("endpoint")
    if not isinstance(endpoint, str):
        return {"status": "unavailable", "message": "HTTP fixture endpoint is not configured"}
    if not is_loopback_url(endpoint):
        return {"status": "unavailable", "message": "HTTP fixture must use a loopback endpoint"}
    try:
        request = Request(endpoint, data=json.dumps(dict(inputs)).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        opener = build_opener(SafeLoopbackRedirectHandler())
        with opener.open(request, timeout=3) as response:  # nosec B310: endpoint and every redirect are loopback-validated
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "unavailable", "message": f"HTTP fixture failed: {exc}"}
    return {"status": "success", "result": payload}
