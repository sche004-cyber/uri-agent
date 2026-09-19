"""Loopback-only HTTP fixture adapter for offline Batch D proof."""

from __future__ import annotations

import ipaddress
import json
from typing import Any, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def execute(descriptor: Mapping[str, Any], _action_name: str, inputs: Mapping[str, Any]) -> dict:
    config = descriptor.get("transport_config")
    config = config if isinstance(config, Mapping) else {}
    endpoint = config.get("endpoint")
    if not isinstance(endpoint, str):
        return {"status": "unavailable", "message": "HTTP fixture endpoint is not configured"}
    parsed = urlparse(endpoint)
    try:
        loopback = parsed.scheme == "http" and parsed.hostname and ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        loopback = False
    if not loopback:
        return {"status": "unavailable", "message": "HTTP fixture must use a loopback endpoint"}
    try:
        request = Request(endpoint, data=json.dumps(dict(inputs)).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=3) as response:  # nosec B310: endpoint is loopback-validated above
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "unavailable", "message": f"HTTP fixture failed: {exc}"}
    return {"status": "success", "result": payload}
