"""M33.3 Batch A (WP-A3): experimental proposal-only Needle bridge.

A new sibling of the accepted ``scripts/m33_2_needle_bridge.py``, which is a
protected M33.2 artifact with fixed tool schemas and is not modified.  This
bridge keeps the same posture and differs only in accepting the offered tool
schemas per request and returning every proposed call:

- runs inside the dedicated ``.venv-needle`` interpreter as a JSONL subprocess;
- telemetry off and offline mode set before ``import needle``;
- ``tools`` are JSON schemas only, never executable callables;
- only ``Needle.complete()`` is called, never ``Needle.run()``.

Returned calls are untrusted proposal observations.  Nothing is executed.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List

os.environ.setdefault("NEEDLE_TELEMETRY", "0")
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import needle  # noqa: E402  (offline environment must be fixed before import)


class Bridge:
    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}

    def _agent(self, system: str, tools: List[Dict[str, Any]]) -> Any:
        for schema in tools:
            if not isinstance(schema, dict) or callable(schema):
                raise ValueError("tool schemas must be plain JSON objects")
        key = json.dumps([system, tools], sort_keys=True)
        if key not in self._agents:
            self._agents[key] = needle.Needle(tools=tools, system=system, generation=3)
        return self._agents[key]

    def propose(self, request: Dict[str, Any]) -> Dict[str, Any]:
        started = time.perf_counter()
        agent = self._agent(str(request["system"]), list(request.get("tool_schemas") or []))
        load_ms = (time.perf_counter() - started) * 1000.0
        started = time.perf_counter()
        response = agent.complete(str(request.get("input", "")), max_new_tokens=int(request.get("max_new_tokens", 128)))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        calls = [c for c in (response.get("function_calls") or []) if isinstance(c, dict)]
        return {
            "status": "ok",
            "calls": [{"name": c.get("name"),
                       "arguments": c.get("arguments") if isinstance(c.get("arguments"), dict) else {}} for c in calls],
            "confidence": response.get("confidence"),
            "provider_latency_ms": elapsed_ms,
            "agent_setup_ms": load_ms,
            "provider_peak_ram_mb": response.get("peak_ram_mb"),
            "provider_prefill_tps": response.get("prefill_tps"),
            "provider_decode_tps": response.get("decode_tps"),
        }

    def close(self) -> None:
        for agent in self._agents.values():
            agent.close()


def _write(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    bridge = Bridge()
    try:
        for raw in sys.stdin:
            try:
                request = json.loads(raw)
                operation = request.get("operation")
                if operation == "ping":
                    _write({"status": "ready", "package": "cactus-needle", "package_version": needle.__version__,
                            "generation": 3, "pid": os.getpid(),
                            "telemetry_disabled": os.environ.get("NEEDLE_TELEMETRY") == "0",
                            "offline_mode": os.environ.get("HF_HUB_OFFLINE") == "1"})
                elif operation == "propose":
                    _write(bridge.propose(request))
                elif operation == "close":
                    return 0
                else:
                    raise ValueError("unknown bridge operation")
            except Exception as exc:  # reported, never swallowed
                _write({"status": "error", "detail": f"{type(exc).__name__}: {exc}"})
    finally:
        bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
