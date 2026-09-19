"""Fixed, descriptor-owned runner for the reviewed strip-json-comments package.

The generic CLI adapter supplies one JSON object on stdin.  This runner is
the capability-owned boundary that validates that object, forwards *only* its
``text`` value to the package's fixed stdin interface, and emits raw text for
the generic adapter's ``output: text`` envelope.  It never accepts a path,
executable, argv, credential, URL, or command from the caller.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

_MAX_INPUT_BYTES = 262144
_MAX_OUTPUT_BYTES = 1048576


def _artifact_cli(artifact_root: str) -> Path:
    root = Path(artifact_root).resolve()
    cli = root / "node_modules" / "strip-json-comments-cli" / "cli.js"
    try:
        cli.relative_to(root)
    except ValueError as exc:  # defensive, although the path is constructed above
        raise ValueError("package CLI path escaped staged artifact") from exc
    if not cli.is_file():
        raise ValueError("reviewed package CLI is unavailable")
    return cli


def _parse_input(raw: str) -> tuple[str, bool]:
    if not raw or len(raw.encode("utf-8")) > _MAX_INPUT_BYTES:
        raise ValueError("input is missing or too large")
    value: Any = json.loads(raw.lstrip("\ufeff"))
    if not isinstance(value, Mapping) or set(value) - {"text", "remove_whitespace"}:
        raise ValueError("input contains unsupported fields")
    text = value.get("text")
    remove_whitespace = value.get("remove_whitespace", False)
    if not isinstance(text, str) or not text:
        raise ValueError("text must be a non-empty string")
    if not isinstance(remove_whitespace, bool):
        raise ValueError("remove_whitespace must be boolean")
    return text, remove_whitespace


def execute_text(
    artifact_root: str, node_executable: str, text: str, *, remove_whitespace: bool,
) -> str:
    cli = _artifact_cli(artifact_root)
    node = Path(node_executable).resolve()
    if not node.is_absolute() or not node.is_file():
        raise ValueError("fixed Node runtime is unavailable")
    command = [str(node), str(cli)]
    if remove_whitespace:
        command.append("--no-whitespace")
    completed = subprocess.run(
        command,
        input=text,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=8,
        shell=False,
        check=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "ComSpec": os.environ.get("ComSpec", ""),
            "NO_UPDATE_NOTIFIER": "1",
        },
    )
    if completed.returncode != 0:
        raise RuntimeError("reviewed package CLI failed")
    if len(completed.stdout.encode("utf-8")) > _MAX_OUTPUT_BYTES:
        raise ValueError("package output is too large")
    return completed.stdout


def main() -> None:
    try:
        if len(sys.argv) != 3:
            raise ValueError("runner requires fixed staged artifact and Node paths")
        text, remove_whitespace = _parse_input(sys.stdin.read())
        sys.stdout.write(execute_text(sys.argv[1], sys.argv[2], text, remove_whitespace=remove_whitespace))
        sys.stdout.flush()
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
