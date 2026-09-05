import re

from uri_core.services.student_query_service import StudentQueryService

# Matches an explicit "roll no / roll number / enrollment no" label
# followed by the identifier itself - the strongest signal a request
# actually names a specific student.
_LABELED_ROLL_RE = re.compile(
    r"(?:roll\s*(?:no\.?|number)|enroll?ment\s*no\.?)\s*[:\-]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9/\-]{2,})",
    re.IGNORECASE,
)

# Fallback for requests that state an identifier-shaped token without
# an explicit label (e.g. "BTECH-2023-001" or "22BCS045") - requires
# both a letter and a digit so ordinary words are never mistaken for
# a roll number.
_GENERIC_ID_RE = re.compile(
    r"\b([A-Za-z]{2,6}[-/]?\d{2,4}[-/]?[A-Za-z0-9]{0,6}"
    r"|\d{2,4}[A-Za-z]{2,6}\d{0,6})\b"
)


def _extract_roll_number(request_text: str):
    """Single-candidate convenience wrapper kept for any caller still
    passing one identifier directly - internal execute() now always
    goes through _extract_all_candidates so it can detect ambiguity
    rather than silently taking the first match."""

    candidates = _extract_all_candidates(request_text)
    return candidates[0] if candidates else None


def _extract_all_candidates(request_text: str) -> list:
    """Every distinct identifier-shaped token actually present in the
    request - labeled ("roll number X") and unlabeled alike, deduped
    case-insensitively, order preserved. A label on one candidate is
    not treated as "safely ignore the others": if the request also
    names a second, different identifier-shaped token, that is a real
    ambiguity the caller must ask about, not silently resolve by
    picking whichever the label happened to sit next to."""

    text = request_text or ""

    raw_candidates = list(_LABELED_ROLL_RE.findall(text))

    for match in _GENERIC_ID_RE.finditer(text):
        candidate = match.group(1)
        if any(c.isdigit() for c in candidate) and any(
            c.isalpha() for c in candidate
        ):
            raw_candidates.append(candidate)

    seen = set()
    unique = []

    for candidate in raw_candidates:
        cleaned = candidate.strip().rstrip(".,")
        key = cleaned.upper()

        if key and key not in seen:
            seen.add(key)
            unique.append(cleaned)

    return unique


class StudentRecordExtractor:
    """Looks up a student record for the identifier actually named in
    the request, via StudentQueryService - the same authorized,
    already-built service chain that searches the real institutional
    spreadsheets and honestly reports "not found" or "records
    unavailable" rather than ever inventing data."""

    def __init__(self, query_service=None):
        self._query_service = query_service or StudentQueryService()

    def execute(self, **kwargs):
        request_text = kwargs.get("request_text", "") or ""
        explicit_roll_number = kwargs.get("roll_number")

        candidates = (
            [explicit_roll_number]
            if explicit_roll_number
            else _extract_all_candidates(request_text)
        )

        if not candidates:
            return {
                "status": "input_required",
                "student_roll": None,
                "message": (
                    "No student roll number or enrollment identifier was "
                    "found in the request. Please specify the roll number "
                    "to look up."
                ),
            }

        if len(candidates) > 1:
            return {
                "status": "clarification_required",
                "student_roll": None,
                "candidates": candidates,
                "message": (
                    "The request names more than one possible student "
                    "identifier (" + ", ".join(candidates) + "). Please "
                    "specify which one you mean."
                ),
            }

        roll_number = candidates[0]

        result = self._query_service.answer_student_query(roll_number)

        if not result.get("success"):
            return {
                "status": "unavailable",
                "student_roll": roll_number,
                "message": result.get(
                    "answer",
                    "URI could not search the available student records.",
                ),
                "error": result.get("error"),
            }

        if not result.get("found"):
            return {
                "status": "not_found",
                "student_roll": roll_number,
                "message": result.get("answer"),
            }

        student = result.get("student", {}) or {}
        return {
            "status": "success",
            "student_roll": student.get("roll_number", roll_number),
            "student_name": student.get("name"),
            "message": result.get("answer"),
            "record": student.get("record"),
            "evidence": result.get("evidence"),
            "raw_match_count": result.get("raw_match_count", 0),
        }
