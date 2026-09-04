import re
from typing import Dict, List, Optional

from uri_core.services.gmail_draft_service import (
    GmailDraftService
)


class DraftContextService:
    """
    Builds structured context from the latest
    relevant Gmail draft.

    A draft is reference material, not verified
    documentary evidence.
    """

    def __init__(
        self,
        gmail_draft_service: Optional[
            GmailDraftService
        ] = None
    ):

        self.gmail_draft_service = (
            gmail_draft_service
            if gmail_draft_service is not None
            else GmailDraftService()
        )


    def get_latest_draft_context(
        self,
        query: str
    ) -> Optional[Dict]:
        """
        Find the latest relevant Gmail draft and
        build structured reference context.
        """

        draft = (
            self.gmail_draft_service
            .search_latest_relevant_draft(
                query=query
            )
        )

        if draft is None:
            return None

        body = draft.get(
            "body",
            ""
        )

        attachments = draft.get(
            "attachments",
            []
        )

        drive_links = (
            self._extract_google_drive_links(
                body
            )
        )

        referenced_files = (
            self._extract_referenced_files(
                body
            )
        )

        meaningful_content = (
            self._has_meaningful_draft_content(
                body
            )
        )

        return {

            "classification": (
                "REFERENCE_DRAFT_CONTEXT"
            ),

            "query": query,

            "draft": draft,

            "draft_content": {

                "subject": (
                    draft.get(
                        "subject",
                        ""
                    )
                ),

                "body": body,

                "meaningful_content": (
                    meaningful_content
                ),
            },

            "gmail_attachments": (
                attachments
            ),

            "linked_references": {

                "google_drive_links": (
                    drive_links
                ),

                "referenced_files": (
                    referenced_files
                ),
            },

            "summary": (
                self._build_summary(
                    draft=draft,
                    drive_links=drive_links,
                    referenced_files=(
                        referenced_files
                    ),
                    meaningful_content=(
                        meaningful_content
                    ),
                )
            ),
        }


    def _extract_google_drive_links(
        self,
        text: str
    ) -> List[str]:
        """
        Extract Google Drive URLs from draft text.
        """

        if not text:
            return []

        pattern = (
            r"https?://drive\.google\.com/"
            r"[^\s<>]+"
        )

        links = re.findall(
            pattern,
            text
        )

        return list(
            dict.fromkeys(links)
        )


    def _extract_referenced_files(
        self,
        text: str
    ) -> List[str]:
        """
        Detect filenames mentioned in the draft.
        """

        if not text:
            return []

        pattern = (
            r"\b[^\s<>]+"
            r"\.(?:pdf|docx|doc|xlsx|xls|"
            r"zip|png|jpg|jpeg)\b"
        )

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        return list(
            dict.fromkeys(matches)
        )


    def _has_meaningful_draft_content(
        self,
        text: str
    ) -> bool:
        """
        Estimate whether the Gmail body itself
        contains a meaningful draft.

        Short signatures, links, filenames and
        forwarding text do not count as a useful
        document draft.
        """

        if not text:
            return False

        cleaned = text

        cleaned = re.sub(
            r"https?://\S+",
            "",
            cleaned
        )

        cleaned = re.sub(
            r"\b[^\s<>]+"
            r"\.(?:pdf|docx|doc|xlsx|xls|"
            r"zip|png|jpg|jpeg)\b",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        signature_phrases = [

            "thanking you",

            "sincerely",

            "regards",

            "student's welfare office",

            "student welfare office",

            "national institute of technology",

            "nit sikkim",
        ]

        for phrase in signature_phrases:

            cleaned = cleaned.replace(
                phrase,
                ""
            )

            cleaned = cleaned.replace(
                phrase.title(),
                ""
            )

        words = cleaned.split()

        return len(words) >= 25


    def _build_summary(
        self,
        draft: Dict,
        drive_links: List[str],
        referenced_files: List[str],
        meaningful_content: bool
    ) -> Dict:
        """
        Produce a compact machine-readable summary.
        """

        return {

            "draft_found": True,

            "has_subject": bool(
                draft.get(
                    "subject",
                    ""
                ).strip()
            ),

            "has_meaningful_body": (
                meaningful_content
            ),

            "gmail_attachment_count": len(
                draft.get(
                    "attachments",
                    []
                )
            ),

            "google_drive_link_count": len(
                drive_links
            ),

            "referenced_file_count": len(
                referenced_files
            ),

            "requires_linked_content_processing": (
                bool(drive_links)
                or bool(referenced_files)
            ),
        }
