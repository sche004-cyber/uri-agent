from email.mime.text import MIMEText
from pathlib import Path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GmailService:
    """
    Gmail integration service for URI.

    Capabilities:
    - Connect to Gmail
    - Search Gmail for evidence
    - Read message metadata
    - Reconstruct complete Gmail threads
    - Build attachment inventories
    - Download one explicitly selected attachment temporarily
    - Safely delete temporary evidence files
    - Create a DRAFT (M19) - see create_draft() below

    URI does NOT send, modify, delete, or archive existing emails, and
    does not send the drafts it creates. Creating a draft is the one
    write operation this service performs; it is only ever reachable
    through the gmail_create_draft capability, which is registered
    approval_requirement=user_approval_required (see
    capabilities_registry.json) - it never runs without an explicit
    human decision, and the resulting draft still requires the user to
    review and send it themselves in Gmail. There is no send_message/
    send_draft method anywhere in this class, and none should be added
    without the same explicit consideration this one required
    (M19 audit finding #2: "other consequential actions through URI
    permission/approval").

    M19 note on scope: the gmail.compose scope below is Google's own
    OAuth scope for draft creation, requested specifically so it can be
    granted WITHOUT also granting gmail.send (a separate, broader
    scope this class deliberately never requests). Google's own scope
    documentation for gmail.compose also permits sending a draft via
    the API; this class's safety boundary is that no code path in this
    service (or anywhere else in URI) ever calls a send endpoint - the
    boundary is enforced by what URI's own code does, not solely by
    the OAuth scope, exactly like every other capability in this
    codebase (see orchestrator.py's capability-registry-gated
    execution boundary).
    """

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/drive.readonly',
        # M19: least-privilege upload scope - covers only files this
        # app itself creates (see DriveService.upload_file), never the
        # broader 'drive' scope that would grant read/write over the
        # user's entire Drive.
        'https://www.googleapis.com/auth/drive.file',
    ]

    def __init__(self):

        project_root = Path(__file__).resolve().parents[2]

        self.credentials_path = (
            project_root / "credentials.json"
        )

        self.token_path = (
            project_root / "token.json"
        )

        self.service = None


    def connect(self) -> dict:
        """
        Connect URI to Gmail using READ_ONLY access.
        """

        creds = None

        if self.token_path.exists():

            creds = Credentials.from_authorized_user_file(
                self.token_path,
                self.SCOPES
            )

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(
                Request()
            )

        elif not creds or not creds.valid:

            if not self.credentials_path.exists():

                return {
                    "success": False,
                    "reason": (
                        "credentials.json was not found."
                    )
                }

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    self.credentials_path,
                    self.SCOPES
                )
            )

            creds = flow.run_local_server(
                port=0
            )

        with open(
            self.token_path,
            "w"
        ) as token:

            token.write(
                creds.to_json()
            )

        self.service = build(
            "gmail",
            "v1",
            credentials=creds
        )

        return {
            "success": True,
            "mode": "READ_ONLY"
        }


    def get_connection_status(self) -> dict:
        """
        Return Gmail connection status.
        """

        return {
            "connected": self.service is not None,
            "mode": "READ_ONLY"
        }

    def create_draft(self, to: str, subject: str, body: str) -> dict:
        """M19: creates a real Gmail DRAFT - never sends it. The
        caller (gmail_create_draft.py) supplies `to` extracted
        deterministically from the user's own request text, and
        `subject`/`body` composed by the Brain from a drafting brief -
        this method itself makes no decision about content, exactly
        like every other write in this codebase leaves composition to
        its caller and only performs the mechanical action.

        Returns {"success": True, "draft_id": ...} or
        {"success": False, "reason": ...}. Never raises."""

        if not self.service:
            connection = self.connect()
            if not connection.get("success"):
                return connection

        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode("utf-8")

            created = self.service.users().drafts().create(
                userId="me",
                body={"message": {"raw": raw}},
            ).execute()

            return {
                "success": True,
                "draft_id": created.get("id"),
            }

        except Exception as e:
            return {"success": False, "reason": str(e)}


    def _get_header_map(
        self,
        payload: dict
    ) -> dict:
        """
        Convert Gmail headers into a dictionary.
        """

        headers = payload.get(
            "headers",
            []
        )

        header_map = {}

        for header in headers:

            header_map[
                header["name"]
            ] = header["value"]

        return header_map


    def _find_attachment_details(
        self,
        payload: dict
    ) -> list:
        """
        Recursively search Gmail MIME payloads.

        Returns attachment metadata only.

        No attachment content is downloaded here.
        """

        attachments = []

        filename = payload.get(
            "filename",
            ""
        )

        mime_type = payload.get(
            "mimeType",
            ""
        )

        body = payload.get(
            "body",
            {}
        )

        attachment_id = body.get(
            "attachmentId"
        )

        if filename and attachment_id:

            attachments.append(
                {
                    "filename": filename,
                    "attachment_id": attachment_id,
                    "mime_type": mime_type
                }
            )

        for part in payload.get(
            "parts",
            []
        ):

            attachments.extend(
                self._find_attachment_details(
                    part
                )
            )

        return attachments


    def search_evidence(
        self,
        queries: list
    ) -> dict:
        """
        Search Gmail for evidence.

        Retrieves message metadata and attachment
        metadata only.

        Attachments are NOT downloaded.
        """

        if self.service is None:

            return {
                "success": False,
                "reason": (
                    "Gmail is not connected."
                ),
                "results": []
            }

        results = []

        for query in queries:

            response = (
                self.service
                .users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=10
                )
                .execute()
            )

            messages = response.get(
                "messages",
                []
            )

            detailed_messages = []

            for message in messages:

                message_data = (
                    self.service
                    .users()
                    .messages()
                    .get(
                        userId="me",
                        id=message["id"],
                        format="full"
                    )
                    .execute()
                )

                payload = message_data.get(
                    "payload",
                    {}
                )

                header_map = (
                    self._get_header_map(
                        payload
                    )
                )

                attachments = (
                    self._find_attachment_details(
                        payload
                    )
                )

                detailed_messages.append(
                    {
                        "message_id": message["id"],

                        "thread_id": message[
                            "threadId"
                        ],

                        "subject": header_map.get(
                            "Subject",
                            ""
                        ),

                        "from": header_map.get(
                            "From",
                            ""
                        ),

                        "date": header_map.get(
                            "Date",
                            ""
                        ),

                        "snippet": message_data.get(
                            "snippet",
                            ""
                        ),

                        "has_attachments": (
                            len(attachments) > 0
                        ),

                        "attachments": attachments
                    }
                )

            results.append(
                {
                    "query": query,

                    "messages_found": len(
                        messages
                    ),

                    "messages": detailed_messages
                }
            )

        return {
            "success": True,
            "results": results
        }


    def get_thread_evidence(
        self,
        thread_id: str
    ) -> dict:
        """
        Retrieve every message in a Gmail thread.

        Builds a complete attachment inventory.

        Attachment contents are NOT downloaded.
        """

        if self.service is None:

            return {
                "success": False,
                "reason": (
                    "Gmail is not connected."
                )
            }

        thread_data = (
            self.service
            .users()
            .threads()
            .get(
                userId="me",
                id=thread_id,
                format="full"
            )
            .execute()
        )

        messages = thread_data.get(
            "messages",
            []
        )

        thread_messages = []

        all_attachments = []

        for message in messages:

            payload = message.get(
                "payload",
                {}
            )

            header_map = (
                self._get_header_map(
                    payload
                )
            )

            attachments = (
                self._find_attachment_details(
                    payload
                )
            )

            for attachment in attachments:

                all_attachments.append(
                    {
                        "filename": attachment[
                            "filename"
                        ],

                        "attachment_id": attachment[
                            "attachment_id"
                        ],

                        "mime_type": attachment[
                            "mime_type"
                        ],

                        "message_id": message[
                            "id"
                        ],

                        "subject": header_map.get(
                            "Subject",
                            ""
                        )
                    }
                )

            thread_messages.append(
                {
                    "message_id": message[
                        "id"
                    ],

                    "subject": header_map.get(
                        "Subject",
                        ""
                    ),

                    "from": header_map.get(
                        "From",
                        ""
                    ),

                    "date": header_map.get(
                        "Date",
                        ""
                    ),

                    "snippet": message.get(
                        "snippet",
                        ""
                    ),

                    "has_attachments": (
                        len(attachments) > 0
                    ),

                    "attachments": attachments
                }
            )

        return {
            "success": True,

            "thread_id": thread_id,

            "messages_found": len(
                thread_messages
            ),

            "messages": thread_messages,

            "attachments_found": len(
                all_attachments
            ),

            "attachments": all_attachments
        }


    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str
    ) -> dict:
        """
        Download one explicitly selected Gmail attachment.

        IMPORTANT:
        This method should only be called after
        explicit user approval.

        The file is stored temporarily inside:

        temp_evidence/

        URI does not permanently retain
        the downloaded document.
        """

        if self.service is None:

            return {
                "success": False,
                "reason": (
                    "Gmail is not connected."
                )
            }

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        temp_folder = (
            project_root /
            "temp_evidence"
        )

        temp_folder.mkdir(
            exist_ok=True
        )

        try:

            attachment_data = (
                self.service
                .users()
                .messages()
                .attachments()
                .get(
                    userId="me",
                    messageId=message_id,
                    id=attachment_id
                )
                .execute()
            )

            encoded_data = (
                attachment_data.get(
                    "data"
                )
            )

            if not encoded_data:

                return {
                    "success": False,
                    "reason": (
                        "Attachment contains no data."
                    )
                }

            file_data = (
                base64.urlsafe_b64decode(
                    encoded_data.encode(
                        "UTF-8"
                    )
                )
            )

            # Prevent path manipulation through
            # a malicious filename.

            safe_filename = (
                Path(filename).name
            )

            file_path = (
                temp_folder /
                safe_filename
            )

            with open(
                file_path,
                "wb"
            ) as file:

                file.write(
                    file_data
                )

            return {
                "success": True,

                "filename": safe_filename,

                "file_path": str(
                    file_path
                ),

                "temporary": True
            }

        except Exception as error:

            return {
                "success": False,
                "reason": str(error)
            }


    def delete_temporary_file(
        self,
        file_path: str
    ) -> dict:
        """
        Safely delete a temporary evidence file.

        URI can ONLY delete files located
        inside its own temp_evidence folder.
        """

        try:

            path = Path(
                file_path
            )

            project_root = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

            temp_folder = (
                project_root /
                "temp_evidence"
            ).resolve()

            resolved_path = (
                path.resolve()
            )

            # Critical safety check:
            # Never allow URI to delete files
            # outside temp_evidence.

            if (
                resolved_path.parent
                != temp_folder
            ):

                return {
                    "success": False,

                    "reason": (
                        "Refusing to delete a file "
                        "outside temp_evidence."
                    )
                }

            if resolved_path.exists():

                resolved_path.unlink()

                return {
                    "success": True,
                    "deleted": True
                }

            return {
                "success": True,

                "deleted": False,

                "reason": (
                    "File not found."
                )
            }

        except Exception as error:

            return {
                "success": False,
                "reason": str(error)
            }


