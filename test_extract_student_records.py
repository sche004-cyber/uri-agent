"""Regression tests for the request-driven rework of
extract_student_records: proves the tool actually reads the roll
number out of the request instead of returning the same hardcoded
record for every input, and that a missing data source or an
unfound roll number is reported honestly rather than fabricated."""

import unittest

from uri_core.tools.extract_student_records import (
    StudentRecordExtractor,
    _extract_all_candidates,
    _extract_roll_number,
)


class _FakeQueryService:
    """Stands in for StudentQueryService so these tests never touch
    the filesystem - only StudentRecordExtractor's own request
    parsing and result-shaping logic is under test here."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def answer_student_query(self, roll_number):
        self.calls.append(roll_number)
        return self.responses.get(
            roll_number,
            {"success": True, "found": False, "answer": f"No record for {roll_number}."},
        )


class RollNumberExtractionTests(unittest.TestCase):

    def test_labeled_roll_number_is_extracted(self):
        self.assertEqual(
            _extract_roll_number("look up roll number BTECH-2023-001 please"),
            "BTECH-2023-001",
        )

    def test_labeled_enrollment_no_is_extracted(self):
        self.assertEqual(
            _extract_roll_number("what is the cgpa for enrollment no 22BCS045"),
            "22BCS045",
        )

    def test_unlabeled_identifier_shaped_token_is_extracted(self):
        self.assertEqual(
            _extract_roll_number("check the record for 22BCS045"),
            "22BCS045",
        )

    def test_plain_words_are_not_mistaken_for_an_identifier(self):
        self.assertIsNone(_extract_roll_number("what is my cgpa"))
        self.assertIsNone(_extract_roll_number("show me the student record"))


class MaterialInputDifferenceTests(unittest.TestCase):
    """The core defect being fixed: the same hardcoded CGPA/semester
    for every call regardless of input. These tests prove two
    materially different requests now produce materially different,
    correctly-attributed results."""

    def test_two_different_roll_numbers_produce_different_results(self):
        query_service = _FakeQueryService(
            {
                "BTECH-2023-001": {
                    "success": True,
                    "found": True,
                    "answer": "Student found: Asha Rai (BTECH-2023-001).",
                    "student": {
                        "roll_number": "BTECH-2023-001",
                        "name": "Asha Rai",
                        "record": {"CGPA": 8.42, "Semester": 6},
                    },
                    "evidence": [],
                    "raw_match_count": 1,
                },
                "BTECH-2023-002": {
                    "success": True,
                    "found": True,
                    "answer": "Student found: Nima Bhutia (BTECH-2023-002).",
                    "student": {
                        "roll_number": "BTECH-2023-002",
                        "name": "Nima Bhutia",
                        "record": {"CGPA": 7.10, "Semester": 4},
                    },
                    "evidence": [],
                    "raw_match_count": 1,
                },
            }
        )
        tool = StudentRecordExtractor(query_service=query_service)

        first = tool.execute(request_text="roll number BTECH-2023-001")
        second = tool.execute(request_text="roll number BTECH-2023-002")

        self.assertEqual(first["student_roll"], "BTECH-2023-001")
        self.assertEqual(second["student_roll"], "BTECH-2023-002")
        self.assertNotEqual(first["student_name"], second["student_name"])
        self.assertNotEqual(first["record"], second["record"])
        # The real service was actually queried with each distinct
        # roll number - not a single fixed default.
        self.assertEqual(
            query_service.calls, ["BTECH-2023-001", "BTECH-2023-002"]
        )

    def test_a_request_with_no_identifier_asks_for_one_instead_of_guessing(self):
        query_service = _FakeQueryService({})
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(request_text="what is my cgpa")

        self.assertEqual(result["status"], "input_required")
        self.assertIsNone(result["student_roll"])
        # No fabricated CGPA/semester/department must ever appear.
        self.assertNotIn("cgpa", result)
        self.assertEqual(query_service.calls, [])

    def test_an_unfound_roll_number_is_reported_honestly(self):
        query_service = _FakeQueryService(
            {"BTECH-2099-999": {"success": True, "found": False, "answer": "No matching record."}}
        )
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(request_text="roll number BTECH-2099-999")

        self.assertEqual(result["status"], "not_found")
        self.assertNotIn("cgpa", result)

    def test_a_missing_data_source_is_reported_as_unavailable_not_fabricated(self):
        query_service = _FakeQueryService(
            {
                "BTECH-2023-001": {
                    "success": False,
                    "answer": "URI could not search the available student records.",
                    "error": "Records path not found",
                }
            }
        )
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(request_text="roll number BTECH-2023-001")

        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("cgpa", result)


class AmbiguousInputTests(unittest.TestCase):
    """Milestone 8A correction: multiple plausible identifiers must
    trigger clarification, never a silent pick of one materially
    different candidate."""

    def test_one_clear_identifier_executes_normally(self):
        query_service = _FakeQueryService(
            {
                "BTECH-2023-001": {
                    "success": True,
                    "found": True,
                    "answer": "Student found: Asha Rai (BTECH-2023-001).",
                    "student": {
                        "roll_number": "BTECH-2023-001",
                        "name": "Asha Rai",
                        "record": {"CGPA": 8.42},
                    },
                    "evidence": [],
                    "raw_match_count": 1,
                }
            }
        )
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(
            request_text="what is the cgpa for roll number BTECH-2023-001"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(query_service.calls, ["BTECH-2023-001"])

    def test_two_distinct_identifiers_trigger_clarification_not_a_lookup(
        self,
    ):
        query_service = _FakeQueryService({})
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(
            request_text=(
                "look up roll number BTECH-2023-001 or BTECH-2023-002 "
                "whichever you find first"
            )
        )

        self.assertEqual(result["status"], "clarification_required")
        self.assertIsNone(result["student_roll"])
        self.assertEqual(
            set(result["candidates"]),
            {"BTECH-2023-001", "BTECH-2023-002"},
        )
        # The real service must never be queried for either candidate
        # until the ambiguity is resolved by the user.
        self.assertEqual(query_service.calls, [])

    def test_labeled_plus_unlabeled_second_identifier_is_still_ambiguous(
        self,
    ):
        # Only the first identifier is explicitly labeled "roll
        # number" - the second, unlabeled one is still a real
        # candidate the tool must not silently ignore.
        query_service = _FakeQueryService({})
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(
            request_text="compare roll number BTECH-2023-001 with BTECH-2023-002"
        )

        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(query_service.calls, [])

    def test_the_same_identifier_repeated_is_not_ambiguous(self):
        query_service = _FakeQueryService(
            {
                "BTECH-2023-001": {
                    "success": True,
                    "found": True,
                    "answer": "Student found: Asha Rai (BTECH-2023-001).",
                    "student": {
                        "roll_number": "BTECH-2023-001",
                        "name": "Asha Rai",
                        "record": {},
                    },
                    "evidence": [],
                    "raw_match_count": 1,
                }
            }
        )
        tool = StudentRecordExtractor(query_service=query_service)

        result = tool.execute(
            request_text=(
                "roll number BTECH-2023-001 - please confirm "
                "BTECH-2023-001 is correct"
            )
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(query_service.calls, ["BTECH-2023-001"])

    def test_extract_all_candidates_dedupes_case_insensitively(self):
        candidates = _extract_all_candidates(
            "roll number btech-2023-001, i.e. BTECH-2023-001"
        )
        self.assertEqual(len(candidates), 1)

    def test_single_candidate_helper_still_works_for_one_identifier(self):
        self.assertEqual(
            _extract_roll_number("roll number BTECH-2023-001"),
            "BTECH-2023-001",
        )


if __name__ == "__main__":
    unittest.main()
