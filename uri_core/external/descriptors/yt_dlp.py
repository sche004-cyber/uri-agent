"""Pinned yt-dlp CLI skill descriptor for M33.1 Batch 2.

Developer-authored, committed, and code-reviewed descriptor.
Exposes strictly ONE read-only action: dump_json.
Uses pinned yt-dlp release: 2026.8.19.
Must never be model-generated or end-user-defined at runtime.
"""

from __future__ import annotations

import sys
from typing import Any, Dict

PINNED_YT_DLP_VERSION = "2026.08.19"
DESCRIPTOR_ID = "skill.yt_dlp"


def yt_dlp_descriptor() -> Dict[str, Any]:
    """Return the committed, code-reviewed yt-dlp descriptor.

    Exposes strictly ONE read-only action (dump_json) executing through
    the generic CLI adapter with no shell execution and no credentials.
    """
    cmd = [sys.executable, "-m", "uri_core.external.runners.yt_dlp_runner"]
    return {
        "contract_version": "1.0",
        "id": DESCRIPTOR_ID,
        "name": "yt-dlp Video Metadata Extractor",
        "description": "Extracts structured video metadata using pinned yt-dlp CLI (2026.08.19).",
        "category": "media",
        "transport": "cli",
        "transport_config": {
            "command": list(cmd),
            "timeout_seconds": 10,
        },
        "source_revision": PINNED_YT_DLP_VERSION,
        "dependencies": [f"yt-dlp=={PINNED_YT_DLP_VERSION}"],
        "intent_signals": ["video_metadata", "video_info", "youtube_info"],
        "aliases": ["yt_dlp", "video_info"],
        "actions": {
            "dump_json": {
                "name": "dump_json",
                "description": "Extract video metadata from a public URL using yt-dlp --dump-json.",
                "interface": {
                    "parameters": {
                        "url": {
                            "type": "string",
                            "required": True,
                            "minLength": 1,
                            "maxLength": 2048,
                            "pattern": "https://commons\\.wikimedia\\.org/wiki/File:[^?#\\s]+",
                            "description": "HTTPS Wikimedia Commons File URL for the bounded acceptance source.",
                        }
                    },
                    "required": ["url"],
                    "returns": {"type": "object", "description": "Structured video metadata object."},
                },
                "effect_type": "read_only",
                "approval_requirement": "none",
                "risk": "low",
                "permissions": ["skill.yt_dlp.read"],
            }
        },
    }
