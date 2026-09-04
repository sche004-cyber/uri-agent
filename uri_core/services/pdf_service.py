from pathlib import Path
from pypdf import PdfReader


class PDFService:
    """
    PDF evidence reader for URI.

    Responsibilities:
    - Read PDF documents temporarily retrieved as evidence
    - Extract text from each page
    - Return structured extraction results

    This service does NOT:
    - Modify the original document
    - Store knowledge permanently
    - Update URI facts
    """

    def extract_text(
        self,
        file_path: str
    ) -> dict:
        """
        Extract text from a PDF file.
        """

        path = Path(file_path)

        if not path.exists():

            return {
                "success": False,
                "reason": "PDF file was not found."
            }

        if path.suffix.lower() != ".pdf":

            return {
                "success": False,
                "reason": "The selected file is not a PDF."
            }

        try:

            reader = PdfReader(path)

            pages = []

            full_text = ""

            for page_number, page in enumerate(
                reader.pages,
                start=1
            ):

                page_text = page.extract_text()

                if page_text is None:

                    page_text = ""

                pages.append(
                    {
                        "page_number": page_number,
                        "text": page_text
                    }
                )

                full_text += (
                    f"\n\n--- PAGE {page_number} ---\n\n"
                    f"{page_text}"
                )

            return {
                "success": True,

                "filename": path.name,

                "pages_found": len(
                    reader.pages
                ),

                "text": full_text,

                "pages": pages
            }

        except Exception as error:

            return {
                "success": False,
                "reason": str(error)
            }