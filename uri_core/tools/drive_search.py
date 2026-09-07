"""Capability: search/read files the user already has access to in
Google Drive (M19).

Read-only - reuses DriveService exactly as it already exists (no new
OAuth scope, no change to what URI is authorized to do in Drive).
Closes the audit's #3 gap that DriveService was never registered as a
capability at all, so the Brain could never search or read Drive
despite the service already being real and working.
"""

from typing import Any, Dict

from uri_core.services.drive_service import DriveService


class DriveSearchTool:
    """Pure machinery: connects (if needed), searches, and returns real
    Drive file metadata as evidence. Never decides what a result means
    and never fabricates a result when Drive is not connected."""

    def __init__(self, drive_service=None):
        self._drive_service = drive_service or DriveService()

    def execute(self, **kwargs) -> Dict[str, Any]:
        request_text = kwargs.get("request_text", "") or ""

        query = request_text.strip()
        if not query:
            return {
                "status": "input_required",
                "message": "No search text was found in the request.",
            }

        result = self._drive_service.search_drive(query)

        if not result.get("success"):
            return {
                "status": "unavailable",
                "message": "URI could not search Google Drive.",
                "error": result.get("reason", "Drive is not connected."),
            }

        return {
            "status": "success",
            "query": query,
            "files": result.get("files", []),
        }
