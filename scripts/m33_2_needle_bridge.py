"""Offline JSONL bridge for the dedicated M33.2 Needle virtualenv.

This process is qualification-only.  It returns model proposals and never
passes executable functions to Needle or invokes Needle's execution loop.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, Iterable


os.environ.setdefault("NEEDLE_TELEMETRY", "0")
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import needle  # noqa: E402  (offline environment must be fixed before import)


_SYSTEM = (
    "You are a proposal-only URI edge classifier. Select at most one offered "
    "tool and copy arguments only from the user text. Never execute a tool. "
    "If no offered tool applies, return no call."
)

_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "weather.lookup": {
        "name": "weather.lookup",
        "description": "Look up weather for a stated place or date.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "date": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "Gmail.search_messages": {
        "name": "Gmail.search_messages",
        "description": "Search email messages using stated filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "unread": {"type": "boolean"},
                "query": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "read_attached_file": {
        "name": "read_attached_file",
        "description": "Read a named file attached to the current request.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    "calendar.list_events": {
        "name": "calendar.list_events",
        "description": "List calendar events for a stated date.",
        "parameters": {
            "type": "object",
            "properties": {"date": {"type": "string"}},
            "additionalProperties": False,
        },
    },
}

_INTENTS = {
    "weather.lookup": "weather",
    "Gmail.search_messages": "email_search",
    "read_attached_file": "read_file",
    "calendar.list_events": "calendar_list",
}


def _record_schema(item: Dict[str, Any]) -> Dict[str, Any]:
    schema = item.get("structured_schema")
    if not isinstance(schema, dict):
        raise ValueError("structured extraction item has no schema")
    return {
        "name": "record.extract",
        "description": "Extract the requested structured record from the text.",
        "parameters": schema,
    }


def _schemas(names: Iterable[str]) -> list[Dict[str, Any]]:
    return [_TOOL_SCHEMAS[name] for name in names if name in _TOOL_SCHEMAS]


class Bridge:
    def __init__(self) -> None:
        started = time.perf_counter()
        self._base = needle.Needle(tools=[], system=_SYSTEM, generation=3)
        self.load_time_ms = (time.perf_counter() - started) * 1000.0
        self._agents: Dict[str, Any] = {}

    def _agent(self, item: Dict[str, Any]) -> Any:
        if item.get("operation") == "structured_extract":
            schema = _record_schema(item)
            key = json.dumps(schema, sort_keys=True)
            tools = [schema]
        else:
            offered = tuple(str(value) for value in item.get("offered_capabilities", ()))
            key = json.dumps(offered)
            tools = _schemas(offered)
        if key not in self._agents:
            self._agents[key] = needle.Needle(
                tools=tools,
                system=_SYSTEM,
                generation=3,
            )
        return self._agents[key]

    def qualify(self, item: Dict[str, Any]) -> Dict[str, Any]:
        agent = self._agent(item)
        started = time.perf_counter()
        response = agent.complete(str(item.get("input", "")), max_new_tokens=128)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        calls = response.get("function_calls") or []
        call = calls[0] if calls and isinstance(calls[0], dict) else {}
        capability_id = call.get("name")
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        confidence = response.get("confidence")

        if item.get("operation") == "structured_extract":
            answer: Any = arguments if capability_id == "record.extract" else {}
        else:
            answer = {
                "intent": _INTENTS.get(str(capability_id), "unknown"),
                "capability_id": capability_id,
            }

        output = {
            "answer": answer,
            "capability_id": capability_id,
            "arguments": arguments,
            "score": confidence,
            "status": "completed" if capability_id else "escalated",
            "escalated": not bool(capability_id),
            "provider_latency_ms": elapsed_ms,
            "provider_peak_ram_mb": response.get("peak_ram_mb"),
            "provider_prefill_tps": response.get("prefill_tps"),
            "provider_decode_tps": response.get("decode_tps"),
        }
        return {
            "status": "ok",
            "output": output,
            "provider_response": response,
        }

    def close(self) -> None:
        for agent in self._agents.values():
            agent.close()
        self._base.close()


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
                    _write(
                        {
                            "status": "ready",
                            "package": "cactus-needle",
                            "package_version": needle.__version__,
                            "generation": 3,
                            "load_time_ms": bridge.load_time_ms,
                            "telemetry_disabled": os.environ.get("NEEDLE_TELEMETRY") == "0",
                            "offline_mode": os.environ.get("HF_HUB_OFFLINE") == "1",
                        }
                    )
                elif operation == "qualify":
                    item = request.get("item")
                    if not isinstance(item, dict):
                        raise ValueError("qualify request requires an item object")
                    _write(bridge.qualify(item))
                elif operation == "close":
                    return 0
                else:
                    raise ValueError("unknown bridge operation")
            except Exception as exc:
                _write({"status": "error", "detail": f"{type(exc).__name__}: {exc}"})
    finally:
        bridge.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
