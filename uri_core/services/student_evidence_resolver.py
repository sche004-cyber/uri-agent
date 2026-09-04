from uri_core.services.student_record_service import StudentRecordService

class StudentEvidenceResolver:

    def __init__(self):
        self.student_service = StudentRecordService()

    def resolve_student(self, roll_number):

        search_result = self.student_service.search_student(
            roll_number
        )

        if not search_result.get("success"):
            return {
                "success": False,
                "error": search_result.get("error")
            }

        matches = [
            match for match in search_result.get("matches", [])
            if "error" not in match
        ]

        if not matches:
            return {
                "success": True,
                "found": False,
                "roll_number": roll_number,
                "student": None,
                "evidence": []
            }

        ranked_matches = sorted(
            matches,
            key=self._evidence_score,
            reverse=True
        )

        best_match = ranked_matches[0]

        # SURGICAL FIX: Keep all data columns from the Excel row, don't throw them away.
        student = dict(best_match)
        # Ensure name and roll_number keys always exist for the UI payload format
        student["name"] = best_match.get("student_name", best_match.get("name", "Unknown"))
        student["roll_number"] = best_match.get("roll_number", roll_number)

        evidence = []

        for match in ranked_matches:

            evidence.append({
                "source_file": match.get("source_file"),
                "sheet": match.get("sheet"),
                "source_type": self._classify_source(
                    match.get("source_file", "")
                ),
                "confidence": self._confidence_label(
                    self._evidence_score(match)
                ),
                "score": self._evidence_score(match)
            })

        insurance_records = [
            match for match in ranked_matches
            if "insurance" in match.get(
                "source_file", ""
            ).lower()
        ]

        registration_records = [
            match for match in ranked_matches
            if "registration" in match.get(
                "source_file", ""
            ).lower()
        ]

        dropout_records = [
            match for match in ranked_matches
            if "drop" in match.get(
                "source_file", ""
            ).lower()
        ]

        return {
            "success": True,
            "found": True,
            "student": student,
            "registration_found": bool(
                registration_records
            ),
            "insurance_found": bool(
                insurance_records
            ),
            "dropout_record_found": bool(
                dropout_records
            ),
            "best_evidence": {
                "source_file": best_match.get(
                    "source_file"
                ),
                "sheet": best_match.get("sheet")
            },
            "evidence": evidence,
            "raw_match_count": len(matches)
        }

    def _evidence_score(self, match):

        filename = match.get(
            "source_file", ""
        ).lower()

        score = 10

        if "registration" in filename:
            score += 50

        if "insurance 2025" in filename:
            score += 45

        elif "insurance 2024" in filename:
            score += 30

        elif "insurance" in filename:
            score += 25

        if "student list" in filename:
            score += 20

        if "drop" in filename:
            score += 40

        if "2025" in filename:
            score += 15

        elif "2024" in filename:
            score += 10

        elif "2023" in filename:
            score += 5

        return score

    def _classify_source(self, filename):

        filename = filename.lower()

        if "registration" in filename:
            return "REGISTRATION_RECORD"

        if "insurance" in filename:
            return "INSURANCE_RECORD"

        if "drop" in filename:
            return "DROPOUT_STATUS_RECORD"

        if "student list" in filename:
            return "STUDENT_LIST"

        return "STUDENT_DOCUMENT"

    def _confidence_label(self, score):

        if score >= 70:
            return "HIGH"

        if score >= 40:
            return "MEDIUM"

        return "LOW"
