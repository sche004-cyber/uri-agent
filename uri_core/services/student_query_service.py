from uri_core.services.student_evidence_resolver import (
    StudentEvidenceResolver
)

class StudentQueryService:

    def __init__(self):
        self.resolver = StudentEvidenceResolver()

    def answer_student_query(self, roll_number):

        result = self.resolver.resolve_student(
            roll_number
        )

        if not result.get("success"):
            return {
                "success": False,
                "answer": (
                    "URI could not search the available "
                    "student records."
                ),
                "error": result.get("error")
            }

        if not result.get("found"):
            return {
                "success": True,
                "found": False,
                "answer": (
                    f"No matching record for {roll_number} "
                    "was found in the currently indexed documents."
                ),
                "evidence": []
            }

        student = result.get("student", {})
        name = student.get("name") or "Name not available"
        roll = student.get("roll_number") or roll_number

        best = result.get("best_evidence", {})
        evidence = result.get("evidence", [])

        parts = [f"Student found: {name} ({roll})."]

        # Extract and display all active database record fields
        record_data = student.get("record", {})
        if record_data and isinstance(record_data, dict):
            details = []
            for k, v in record_data.items():
                if v is not None and str(v).strip() != "":
                    details.append(f"{k}: {v}")
            if details:
                parts.append("\nRecord Details:\n- " + "\n- ".join(details))

        if best.get("source_file"):
            parts.append(
                f"\nSource: {best.get('source_file')} (Sheet: '{best.get('sheet')}')"
            )

        return {
            "success": True,
            "found": True,
            "answer": "\n".join(parts),
            "student": student,
            "best_evidence": best,
            "evidence": evidence,
            "raw_match_count": result.get("raw_match_count", 0)
        }
