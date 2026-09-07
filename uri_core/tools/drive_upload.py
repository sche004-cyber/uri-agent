"""Capability: upload the most recently generated/attached file in this
conversation to Google Drive (M19) - never overwrites, moves, renames,
or deletes anything; only ever creates a new file.

Registered approval_requirement=user_approval_required (see
capabilities_registry.json) - never executes without an explicit human
decision, exactly like gmail_create_draft.

Deliberately does not accept a filename/file_id argument from the
model: the file is resolved deterministically from FileStore by
session_id (the runtime-supplied, real session this conversation is
actually in), taking the most recently stored record - the same file a
prior generate_document/draft_institutional_note step in THIS
conversation just produced, or a file the user themselves attached.
This is the one missing link for the audit's end-to-end office
workflow ("... generate DOCX/PPTX -> save to Drive -> ...").
"""

from typing import Any, Dict

from uri_core.core.file_store import FileStore
from uri_core.services.drive_service import DriveService


class DriveUploadTool:
    def __init__(self, drive_service=None, file_store=None):
        self._drive_service = drive_service or DriveService()
        self._file_store = file_store or FileStore()

    def generate(self, **kwargs) -> Dict[str, Any]:
        session_id = kwargs.get("session_id")

        if not session_id:
            return {
                "status": "input_required",
                "message": (
                    "No conversation session was identified, so URI "
                    "could not tell which file to upload."
                ),
            }

        records = self._file_store.list_for_session(session_id)

        if not records:
            return {
                "status": "not_found",
                "message": (
                    "No file has been generated or attached in this "
                    "conversation to upload."
                ),
            }

        record = records[-1]
        path = self._file_store.path_for(record.file_id)

        if path is None:
            return {
                "status": "unavailable",
                "message": "The file is no longer available to upload.",
            }

        with open(path, "rb") as handle:
            content = handle.read()

        result = self._drive_service.upload_file(
            record.filename, content, record.media_type
        )

        if not result.get("success"):
            return {
                "status": "unavailable",
                "message": "URI could not upload the file to Google Drive.",
                "error": result.get("reason", "Drive is not connected."),
            }

        return {
            "status": "success",
            "filename": record.filename,
            "drive_file_id": result.get("file_id"),
            "drive_link": result.get("web_view_link"),
        }
