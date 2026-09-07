"""M16 Priority 1: secure storage and retrieval of user-supplied files.

This is ENGINE-side infrastructure, not Brain reasoning: it validates,
authorizes, stores and retrieves; it never decides whether a file is
relevant, what it means, or what should be done with it. The Brain sees
only a small, bounded reference to each attachment (see
attachment_context) and decides for itself whether to read one via the
registered `read_attached_file` capability - exactly the same
propose/validate/execute boundary every other capability already goes
through (see ADR-018's authority principle).

Security discipline, all enforced here rather than trusted from the
client:

    - The client's filename is NEVER used as a path. Every stored file
      is named by a server-generated UUID; the original name is kept
      only as metadata for display, after being stripped to its bare
      basename (os.path.basename) so a traversal-shaped value like
      "../../etc/passwd" can never influence where anything is written.
    - Files live under one dedicated directory, resolved once at
      construction, and every read path is re-checked to be inside it
      (see _resolve_within_root) - the same containment check
      gmail_service.delete_temporary_file already applies to
      temp_evidence.
    - An extension allow-list bounds what can be stored at all; a
      rejected type is reported honestly rather than silently dropped.
    - A size cap is enforced on the real byte count actually written,
      never on a client-declared length.
    - Nothing stored here is ever executed, imported, or evaluated.

User scoping mirrors the existing convention exactly: server.py passes
a user-scoped path (portable_paths.user_scoped_path) for a logged-in
user, and the ambient default is used otherwise - identical to how
MemoryStore/UserProfileStore are already wired in _build_user_context.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"

# 25 MB: comfortably covers institutional PDFs/spreadsheets while
# keeping one upload bounded. Enforced on real bytes written.
MAX_FILE_BYTES = 25 * 1024 * 1024

# What may be stored at all. Deliberately conservative and explicit -
# an unknown/execuable type is refused rather than stored "just in
# case". Extraction support is a SEPARATE question (see
# file_extraction.py): a type may be storable but not extractable, and
# that is reported honestly rather than hidden.
ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".txt",
        ".md",
        ".csv",
        ".json",
        ".log",
        ".xlsx",
        ".xls",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".webp",
        ".docx",
        # M19: generated presentations (see generate_document.py) - a
        # document URI itself produces is stored the same way a user's
        # own upload is, so it is downloadable via the existing
        # GET /files/{id}/content path.
        ".pptx",
    }
)

MAX_FILENAME_LENGTH = 200


class FileValidationError(ValueError):
    """Raised when an upload fails validation. The message is safe to
    show the user - it explains the real reason (type, size, empty)
    rather than a generic failure."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StoredFile:
    """One stored user file. `stored_name` is the server-generated
    on-disk name; `filename` is the (sanitized) original, kept for
    display only and never used to build a path."""

    file_id: str
    filename: str
    stored_name: str
    media_type: str
    size_bytes: int
    session_id: Optional[str]
    created_at: str
    schema_version: str = SCHEMA_VERSION

    def to_reference(self) -> Dict[str, Any]:
        """The small, bounded shape the Brain is allowed to see - never
        file content, never an on-disk path. Content only ever reaches
        the Brain when it explicitly selects the read_attached_file
        capability and the Engine executes it."""

        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
        }


def sanitize_filename(raw: Any) -> str:
    """The client's filename reduced to a bare, display-safe basename.
    Never used to construct a storage path - see the module docstring.
    Degrades to "upload" rather than raising, so a hostile or empty
    name can never break an otherwise valid upload."""

    if not isinstance(raw, str) or not raw.strip():
        return "upload"

    # Strip any directory component the client sent, in either
    # separator style, before anything else looks at this value.
    name = raw.replace("\\", "/").split("/")[-1].strip()

    # Drop control characters and the characters Windows forbids.
    cleaned = "".join(
        char
        for char in name
        if char.isprintable() and char not in '<>:"|?*'
    ).strip()

    cleaned = cleaned.lstrip(".") or "upload"

    return cleaned[:MAX_FILENAME_LENGTH]


def file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


class FileStore:
    """Stores user-supplied files and their metadata index. Mirrors
    MemoryStore/ExperienceStore's persistence discipline (schema-
    versioned JSON index, safe degrade-to-empty on a corrupted file)
    with the actual bytes kept alongside in the same directory."""

    def __init__(self, storage_dir: str = "uri_workspace/uploads"):
        self.storage_dir = os.path.normpath(storage_dir)
        self.index_path = os.path.join(self.storage_dir, "index.json")

    # ----------------------------------------------------------
    # Containment
    # ----------------------------------------------------------

    def _root(self) -> str:
        return os.path.realpath(self.storage_dir)

    def _resolve_within_root(self, stored_name: str) -> Optional[str]:
        """An absolute path for `stored_name`, but ONLY if it really
        resolves inside the store's own directory. Returns None
        otherwise - never raises, never returns a path outside the
        root, even if the index itself was tampered with."""

        try:
            root = self._root()
            candidate = os.path.realpath(
                os.path.join(root, os.path.basename(str(stored_name)))
            )

            if candidate == root or not candidate.startswith(
                root + os.sep
            ):
                return None

            return candidate

        except Exception:
            return None

    # ----------------------------------------------------------
    # Write
    # ----------------------------------------------------------

    def save(
        self,
        *,
        filename: str,
        content: bytes,
        media_type: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> StoredFile:
        """Validates and stores one file. Raises FileValidationError -
        with a reason safe to show the user - rather than storing
        anything questionable."""

        if not isinstance(content, (bytes, bytearray)):
            raise FileValidationError("File content was not readable.")

        if len(content) == 0:
            raise FileValidationError("The file is empty.")

        if len(content) > MAX_FILE_BYTES:
            raise FileValidationError(
                "The file is larger than the "
                f"{MAX_FILE_BYTES // (1024 * 1024)} MB limit."
            )

        safe_name = sanitize_filename(filename)
        extension = file_extension(safe_name)

        if extension not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"Files of type '{extension or 'unknown'}' are not "
                "accepted. Supported: "
                + ", ".join(sorted(ALLOWED_EXTENSIONS))
                + "."
            )

        os.makedirs(self.storage_dir, exist_ok=True)

        file_id = str(uuid.uuid4())
        stored_name = f"{file_id}{extension}"

        destination = self._resolve_within_root(stored_name)

        if destination is None:
            raise FileValidationError("The file could not be stored.")

        with open(destination, "wb") as handle:
            handle.write(content)

        record = StoredFile(
            file_id=file_id,
            filename=safe_name,
            stored_name=stored_name,
            media_type=str(media_type or "application/octet-stream"),
            size_bytes=len(content),
            session_id=session_id,
            created_at=_now(),
        )

        records = self._load()
        records.append(record)
        self._save(records)

        return record

    # ----------------------------------------------------------
    # Read
    # ----------------------------------------------------------

    def get(self, file_id: str) -> Optional[StoredFile]:

        for record in self._load():

            if record.file_id == file_id:
                return record

        return None

    def path_for(self, file_id: str) -> Optional[str]:
        """The real on-disk path for a stored file, or None when the
        id is unknown or the file is missing/outside the root. This is
        the ONLY way any other component may reach file bytes."""

        record = self.get(file_id)

        if record is None:
            return None

        path = self._resolve_within_root(record.stored_name)

        if path is None or not os.path.exists(path):
            return None

        return path

    def list_for_session(self, session_id: str) -> List[StoredFile]:

        return [
            record
            for record in self._load()
            if record.session_id == session_id
        ]

    def references_for(self, file_ids: Any) -> List[Dict[str, Any]]:
        """Bounded references for the ids given, silently skipping any
        id that does not resolve to a real stored file - so an unknown
        or stale id can never become a claim that a file exists."""

        if not isinstance(file_ids, (list, tuple)):
            return []

        references = []

        for file_id in file_ids:

            record = self.get(file_id) if isinstance(file_id, str) else None

            if record is not None:
                references.append(record.to_reference())

        return references

    def delete(self, file_id: str) -> bool:

        records = self._load()
        remaining = [r for r in records if r.file_id != file_id]

        if len(remaining) == len(records):
            return False

        target = next(r for r in records if r.file_id == file_id)
        path = self._resolve_within_root(target.stored_name)

        if path is not None and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

        self._save(remaining)

        return True

    # ----------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------

    def _load(self) -> List[StoredFile]:

        if not os.path.exists(self.index_path):
            return []

        try:

            with open(self.index_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            return [
                StoredFile(
                    file_id=raw["file_id"],
                    filename=raw["filename"],
                    stored_name=raw["stored_name"],
                    media_type=raw.get(
                        "media_type", "application/octet-stream"
                    ),
                    size_bytes=int(raw.get("size_bytes", 0)),
                    session_id=raw.get("session_id"),
                    created_at=raw.get("created_at", ""),
                    schema_version=raw.get(
                        "schema_version", SCHEMA_VERSION
                    ),
                )
                for raw in data.get("files", [])
            ]

        except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError):
            return []

    def _save(self, records: List[StoredFile]) -> None:

        os.makedirs(self.storage_dir, exist_ok=True)

        payload = {
            "schema_version": SCHEMA_VERSION,
            "files": [asdict(record) for record in records],
        }

        with open(self.index_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
