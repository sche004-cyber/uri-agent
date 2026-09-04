import re
from datetime import datetime


class EvidenceFactExtractor:
    """
    Extracts structured facts from evidence text.

    Facts extracted from documents are marked as VERIFIED
    and include source metadata.
    """

    def extract(self, text, source=None):

        if not text:
            return []

        facts = []

        # --------------------------------------------------
        # INSTITUTION
        # --------------------------------------------------

        institution_patterns = [
            r"National Institute of Technology Sikkim",
            r"NIT Sikkim"
        ]

        for pattern in institution_patterns:

            if re.search(pattern, text, re.IGNORECASE):

                facts.append(
                    self._fact(
                        name="institution",
                        value="NIT Sikkim",
                        source=source
                    )
                )

                break

        # --------------------------------------------------
        # ACADEMIC YEAR
        # --------------------------------------------------

        academic_year = re.search(
            r"\b(20\d{2}\s*[-–]\s*\d{2,4})\b",
            text
        )

        if academic_year:

            value = academic_year.group(1)
            value = re.sub(r"\s+", "", value)

            facts.append(
                self._fact(
                    name="academic_year",
                    value=value,
                    source=source
                )
            )

        # --------------------------------------------------
        # INSURANCE TYPE
        # --------------------------------------------------

        if re.search(
            r"Group\s+(Medical\s+)?Insurance",
            text,
            re.IGNORECASE
        ):

            facts.append(
                self._fact(
                    name="insurance_type",
                    value="Group Medical Insurance",
                    source=source
                )
            )

        # --------------------------------------------------
        # INSURER
        # --------------------------------------------------

        insurers = [
            "SBI General Insurance",
            "New India Assurance",
            "United India Insurance",
            "National Insurance Company",
            "Oriental Insurance"
        ]

        for insurer in insurers:

            if insurer.lower() in text.lower():

                facts.append(
                    self._fact(
                        name="insurer",
                        value=insurer,
                        source=source
                    )
                )

                break

        # --------------------------------------------------
        # TOTAL STUDENTS
        # --------------------------------------------------

        total_students = re.search(
            r"approximately\s+(\d+)\s+students",
            text,
            re.IGNORECASE
        )

        if total_students:

            facts.append(
                self._fact(
                    name="approx_total_students",
                    value=total_students.group(1),
                    source=source
                )
            )

        # --------------------------------------------------
        # RENEWAL STUDENTS
        # --------------------------------------------------

        renewal_students = re.search(
            r"approximately\s+(\d+)\s*[-–]\s*(\d+)\s+students.*?renewal",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if renewal_students:

            value = (
                renewal_students.group(1)
                + "-"
                + renewal_students.group(2)
            )

            facts.append(
                self._fact(
                    name="renewal_students",
                    value=value,
                    source=source
                )
            )

        # --------------------------------------------------
        # FRESH STUDENTS
        # --------------------------------------------------

        fresh_students = re.search(
            r"approximately\s+(\d+)\s+newly admitted students",
            text,
            re.IGNORECASE
        )

        if fresh_students:

            facts.append(
                self._fact(
                    name="fresh_students",
                    value=fresh_students.group(1),
                    source=source
                )
            )

        return facts

    # --------------------------------------------------
    # FACT BUILDER
    # --------------------------------------------------

    def _fact(self, name, value, source):

        return {
            "name": name,
            "value": value,
            "status": "VERIFIED",
            "source": source or {},
            "extracted_at": datetime.now().isoformat()
        }