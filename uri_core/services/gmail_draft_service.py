from typing import Dict, List, Optional
import base64

from uri_core.services.gmail_service import GmailService


class GmailDraftService:
    """
    Discovers relevant Gmail drafts for URI.

    Gmail drafts are reference material and are NOT
    treated as verified evidence.

    URI may use drafts to understand:
    - previous wording
    - document structure
    - drafting context
    - unfinished work
    """

    def __init__(
        self,
        gmail_service: Optional[GmailService] = None
    ):
        self.gmail_service = (
            gmail_service
            if gmail_service is not None
            else GmailService()
        )


    def search_latest_relevant_draft(
        self,
        query: str,
        max_results: int = 20
    ) -> Optional[Dict]:
        """
        Search Gmail drafts and return the newest
        relevant draft.

        Returns None when no relevant draft exists.
        """

        connection = self._ensure_connected()

        if not connection.get("success"):
            return None

        drafts = self._get_drafts(
            max_results=max_results
        )

        relevant_drafts = []

        for draft in drafts:

            draft_data = (
                self._extract_draft_data(
                    draft
                )
            )

            if self._is_relevant(
                query=query,
                draft=draft_data
            ):
                relevant_drafts.append(
                    draft_data
                )

        if not relevant_drafts:
            return None

        relevant_drafts.sort(
            key=lambda item: item.get(
                "internal_date",
                0
            ),
            reverse=True
        )

        latest_draft = relevant_drafts[0]

        latest_draft[
            "classification"
        ] = "REFERENCE_DRAFT"

        return latest_draft


    def _ensure_connected(self) -> Dict:
        """
        Ensure the underlying Gmail service is connected.
        """

        status = (
            self.gmail_service
            .get_connection_status()
        )

        if status.get("connected"):
            return {
                "success": True
            }

        return self.gmail_service.connect()


    def _get_drafts(
        self,
        max_results: int
    ) -> List[Dict]:
        """
        Retrieve Gmail messages stored as drafts.
        """

        service = (
            self.gmail_service.service
        )

        if service is None:
            return []

        try:

            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q="in:drafts",
                    maxResults=max_results
                )
                .execute()
            )

        except Exception:

            return []

        messages = results.get(
            "messages",
            []
        )

        drafts = []

        for message in messages:

            message_id = message.get("id")

            if not message_id:
                continue

            try:

                full_message = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="full"
                    )
                    .execute()
                )

                drafts.append(
                    full_message
                )

            except Exception:
                continue

        return drafts


    def _extract_draft_data(
        self,
        message: Dict
    ) -> Dict:
        """
        Extract useful information from one draft.
        """

        payload = message.get(
            "payload",
            {}
        )

        headers = payload.get(
            "headers",
            []
        )

        subject = ""

        for header in headers:

            name = header.get(
                "name",
                ""
            ).lower()

            if name == "subject":

                subject = header.get(
                    "value",
                    ""
                )

                break

        body = self._extract_body(
            payload
        )

        attachments = (
            self._extract_attachments(
                payload
            )
        )

        internal_date = message.get(
            "internalDate",
            "0"
        )

        try:
            internal_date = int(
                internal_date
            )

        except (
            TypeError,
            ValueError
        ):
            internal_date = 0

        return {

            "message_id": message.get(
                "id"
            ),

            "thread_id": message.get(
                "threadId"
            ),

            "subject": subject,

            "body": body,

            "attachments": attachments,

            "internal_date": (
                internal_date
            ),

            "classification": (
                "REFERENCE_DRAFT"
            ),
        }


    def _decode_data(
        self,
        data: str
    ) -> str:
        """
        Decode Gmail base64 content safely.
        """

        if not data:
            return ""

        try:

            decoded = (
                base64.urlsafe_b64decode(
                    data
                    + "=" * (
                        -len(data) % 4
                    )
                )
            )

            return decoded.decode(
                "utf-8",
                errors="ignore"
            )

        except Exception:

            return ""


    def _extract_body(
        self,
        payload: Dict
    ) -> str:
        """
        Recursively extract text from Gmail MIME parts.

        Plain text is preferred over HTML.
        """

        mime_type = payload.get(
            "mimeType",
            ""
        )

        body_data = (
            payload.get(
                "body",
                {}
            ).get(
                "data"
            )
        )

        if (
            mime_type == "text/plain"
            and body_data
        ):

            return self._decode_data(
                body_data
            )


        plain_parts = []
        html_parts = []

        for part in payload.get(
            "parts",
            []
        ):

            extracted = (
                self._extract_body(
                    part
                )
            )

            if not extracted.strip():
                continue

            part_type = part.get(
                "mimeType",
                ""
            )

            if part_type == "text/plain":

                plain_parts.append(
                    extracted
                )

            elif part_type == "text/html":

                html_parts.append(
                    extracted
                )


        if plain_parts:

            return "\n".join(
                plain_parts
            ).strip()


        if html_parts:

            return "\n".join(
                html_parts
            ).strip()


        if body_data:

            return self._decode_data(
                body_data
            )

        return ""


    def _extract_attachments(
        self,
        payload: Dict
    ) -> List[Dict]:
        """
        Recursively extract attachment metadata.
        """

        attachments = []


        def scan_part(
            part: Dict
        ):

            filename = part.get(
                "filename",
                ""
            )

            body = part.get(
                "body",
                {}
            )

            attachment_id = body.get(
                "attachmentId"
            )

            if (
                filename
                and attachment_id
            ):

                attachments.append(
                    {

                        "filename": filename,

                        "mime_type": (
                            part.get(
                                "mimeType",
                                ""
                            )
                        ),

                        "attachment_id": (
                            attachment_id
                        ),

                        "classification": (
                            "REFERENCE_ATTACHMENT"
                        ),
                    }
                )

            for child in part.get(
                "parts",
                []
            ):

                scan_part(child)


        scan_part(payload)

        return attachments


    def _is_relevant(
        self,
        query: str,
        draft: Dict
    ) -> bool:
        """
        Basic keyword relevance matching.

        This can later be upgraded to URI's semantic
        retrieval system.
        """

        if not query:
            return True

        query_words = (
            query.lower().split()
        )

        searchable_text = (
            draft.get(
                "subject",
                ""
            )
            + " "
            + draft.get(
                "body",
                ""
            )
        ).lower()

        matches = 0

        for word in query_words:

            if len(word) < 3:
                continue

            if word in searchable_text:
                matches += 1

        return matches > 0
