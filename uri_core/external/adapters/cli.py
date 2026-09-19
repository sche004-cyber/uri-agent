"""Bounded local CLI fixture adapter (JSON stdin/stdout, no shell)."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Mapping


def execute(descriptor: Mapping[str, Any], _action_name: str, inputs: Mapping[str, Any]) -> dict:
    config = descriptor.get("transport_config")
    config = config if isinstance(config, Mapping) else {}
    command = config.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
        return {"status": "unavailable", "message": "CLI fixture command is not configured"}
    timeout = config.get("timeout_seconds", 3)
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 10:
        return {"status": "invalid_input", "message": "invalid CLI fixture timeout"}
    try:
        completed = subprocess.run(
            command, input=json.dumps(dict(inputs)), text=True, capture_output=True,
            timeout=timeout, shell=False, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "message": f"CLI fixture failed: {exc}"}
    if completed.returncode:
        return {"status": "unavailable", "message": "CLI fixture returned a non-zero status"}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "invalid_output", "message": "CLI fixture returned invalid JSON"}
    return {"status": "success", "result": payload}
