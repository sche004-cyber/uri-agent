import io
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from googleapiclient.http import MediaIoBaseDownload
from uri_core.services.gmail_service import GmailService


class LinkedDocumentService:

    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc",
        ".xlsx", ".xls", ".csv",
        ".txt", ".png", ".jpg", ".jpeg"
    }

    def __init__(
        self,
        gmail_service: Optional[GmailService] = None,
        workspace_dir: str = "uri_workspace/linked_documents"
    ):

        self.gmail_service = (
            gmail_service
            if gmail_service is not None
            else GmailService()
        )

        self.workspace_dir = Path(workspace_dir)

        self.workspace_dir.mkdir(
            parents=True,
            exist_ok=True
        )


    def fetch_google_drive_link(
        self,
        url: str
    ) -> Dict:

        connection = self._ensure_connected()

        if not connection.get("success"):
            return {
                "success": False,
                "error": "Google account connection failed."
            }

        file_id = self._extract_drive_file_id(url)

        if not file_id:
            return {
                "success": False,
                "error": "Could not identify Google Drive file ID."
            }

        try:

            drive_service = self._get_drive_service()

            metadata = (
                drive_service.files()
                .get(
                    fileId=file_id,
                    fields="id,name,mimeType,size"
                )
                .execute()
            )

            filename = metadata.get(
                "name",
                f"{file_id}.bin"
            )

            destination = (
                self.workspace_dir / filename
            )

            self._download_drive_file(
                drive_service,
                file_id,
                destination
            )

            return {
                "success": True,
                "file_id": file_id,
                "filename": filename,
                "mime_type": metadata.get(
                    "mimeType",
                    ""
                ),
                "path": str(destination),
                "classification": "LINKED_REFERENCE_DOCUMENT"
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }


    def process_file(
        self,
        path: str
    ) -> Dict:

        file_path = Path(path)

        if not file_path.exists():

            return {
                "success": False,
                "error": f"File not found: {path}"
            }

        extension = file_path.suffix.lower()

        if extension == ".zip":
            return self._process_zip(file_path)

        if extension in self.SUPPORTED_EXTENSIONS:

            return {
                "success": True,
                "source_file": str(file_path),
                "documents": [
                    {
                        "path": str(file_path),
                        "filename": file_path.name,
                        "extension": extension,
                        "classification": "REFERENCE_DOCUMENT"
                    }
                ]
            }

        return {
            "success": False,
            "error": f"Unsupported file type: {extension}"
        }


    def _process_zip(
        self,
        zip_path: Path
    ) -> Dict:

        extract_dir = (
            self.workspace_dir /
            f"{zip_path.stem}_extracted"
        )

        extract_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        documents = []

        try:

            with zipfile.ZipFile(
                zip_path,
                "r"
            ) as archive:

                for member in archive.infolist():

                    if member.is_dir():
                        continue

                    safe_name = Path(
                        member.filename
                    ).name

                    if not safe_name:
                        continue

                    extension = (
                        Path(safe_name)
                        .suffix
                        .lower()
                    )

                    if (
                        extension
                        not in self.SUPPORTED_EXTENSIONS
                    ):
                        continue

                    destination = (
                        extract_dir / safe_name
                    )

                    with archive.open(member) as source:
                        with open(
                            destination,
                            "wb"
                        ) as target:

                            target.write(
                                source.read()
                            )

                    documents.append(
                        {
                            "path": str(destination),
                            "filename": safe_name,
                            "extension": extension,
                            "classification": "REFERENCE_DOCUMENT"
                        }
                    )

            return {
                "success": True,
                "source_file": str(zip_path),
                "documents": documents,
                "extraction_directory": str(
                    extract_dir
                )
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }


    def _extract_drive_file_id(
        self,
        url: str
    ) -> Optional[str]:

        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",
            r"[?&]id=([a-zA-Z0-9_-]+)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                url
            )

            if match:
                return match.group(1)

        return None


    def _ensure_connected(self) -> Dict:

        status = (
            self.gmail_service
            .get_connection_status()
        )

        if status.get("connected"):
            return {"success": True}

        return self.gmail_service.connect()


    def _get_drive_service(self):

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = (
            Credentials
            .from_authorized_user_file(
                str(
                    self.gmail_service.token_path
                ),
                GmailService.SCOPES
            )
        )

        return build(
            "drive",
            "v3",
            credentials=credentials
        )


    def _download_drive_file(
        self,
        drive_service,
        file_id: str,
        destination: Path
    ):

        request = (
            drive_service.files()
            .get_media(
                fileId=file_id
            )
        )

        with open(
            destination,
            "wb"
        ) as file_handle:

            downloader = (
                MediaIoBaseDownload(
                    file_handle,
                    request
                )
            )

            finished = False

            while not finished:

                _status, finished = (
                    downloader.next_chunk()
                )
