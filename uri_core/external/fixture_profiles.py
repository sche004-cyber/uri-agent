"""The three offline fixture profiles required by frozen M33 Batch D."""

from __future__ import annotations

from typing import Any, Dict, List


def fixture_profile(transport: str, *, transport_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "contract_version": "1.0", "id": f"fixture.{transport}_lookup",
        "name": f"Fixture {transport} lookup", "description": "Offline M33 transport fixture.",
        "category": "research", "transport": transport, "transport_config": transport_config,
        "intent_signals": ["research_lookup"], "aliases": [f"fixture {transport}"],
        "actions": {"lookup": {"name": "lookup", "description": "Returns fixture evidence.",
            "interface": {"parameters": {"query": {"type": "string", "minLength": 1, "maxLength": 120}},
                          "required": ["query"], "returns": {"type": "object"}},
            "effect_type": "read_only", "approval_requirement": "none", "risk": "low",
            "permissions": ["fixture.read"]}},
    }


def in_process_profile() -> Dict[str, Any]:
    return fixture_profile("in_process", transport_config={"fixture_result": {"evidence": "in-process fixture"}})


def cli_profile(command: List[str]) -> Dict[str, Any]:
    return fixture_profile("cli", transport_config={"command": command, "timeout_seconds": 3})


def http_profile(endpoint: str) -> Dict[str, Any]:
    return fixture_profile("http", transport_config={"endpoint": endpoint})
