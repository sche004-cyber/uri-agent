"""Developer-authored descriptor for the M33.1 Batch 3 GitHub package proof."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

DESCRIPTOR_ID = "skill.strip_json_comments"
PACKAGE_NAME = "strip-json-comments-cli"
V2_REVISION = "f820f90720ae34faf0b05dea82c99432da4131dc"
V3_REVISION = "d1f67f37c0543fbc06a107b7df4ea034476c98d7"


def strip_json_comments_descriptor(
    *, artifact_path: Path, node_executable: Path, source_revision: str,
) -> Dict[str, Any]:
    """Return the one reviewed action bound to one staged immutable artifact.

    ``artifact_path`` is produced only by the developer-authored package
    lifecycle module.  It is not a model/UI/request parameter.
    """
    return {
        "contract_version": "1.0",
        "id": DESCRIPTOR_ID,
        "name": "Strip JSON Comments",
        "description": "Removes comments from supplied JSON text using a pinned reviewed package.",
        "category": "data",
        "transport": "cli",
        "transport_config": {
            "command": [
                sys.executable,
                "-m",
                "uri_core.external.runners.strip_json_comments_runner",
                str(artifact_path),
                str(node_executable),
            ],
            "timeout_seconds": 10,
            "output": "text",
        },
        "source_revision": source_revision,
        "dependencies": [PACKAGE_NAME],
        "intent_signals": ["strip_json_comments", "clean_json", "remove_json_comments"],
        "aliases": ["strip_json_comments"],
        "actions": {
            "strip_json_comments": {
                "name": "strip_json_comments",
                "description": "Remove comments from supplied JSON text without reading or writing caller paths.",
                "interface": {
                    "parameters": {
                        "text": {"type": "string", "required": True, "minLength": 1, "maxLength": 262144},
                        "remove_whitespace": {"type": "boolean", "default": False},
                    },
                    "required": ["text"],
                    "returns": {
                        "type": "object",
                        "properties": {"text": {"type": "string", "maxLength": 1048576}},
                    },
                },
                "effect_type": "read_only",
                "approval_requirement": "none",
                "risk": "low",
                "permissions": ["skill.strip_json_comments.read"],
            }
        },
    }
