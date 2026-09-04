"""Regression tests for the request-driven rework of
draft_institutional_note: proves the drafted note actually reflects
the requested subject instead of always producing the same
hardcoded LTC office-note template regardless of input."""

import unittest

from uri_core.tools.draft_institutional_note import InstitutionalNoteDraftCmp


class MaterialInputDifferenceTests(unittest.TestCase):

    def test_two_different_subjects_produce_differently_worded_notes(self):
        tool = InstitutionalNoteDraftCmp()

        insurance_note = tool.generate(
            request_text="draft a note about the group medical insurance renewal for 2026"
        )
        library_note = tool.generate(
            request_text="draft a note about extending library hours during exams"
        )

        self.assertIn("group medical insurance renewal", insurance_note["note_sheet"].lower())
        self.assertIn("extending library hours", library_note["note_sheet"].lower())
        self.assertNotEqual(insurance_note["note_sheet"], library_note["note_sheet"])

    def test_a_non_ltc_request_never_produces_ltc_boilerplate(self):
        # The old implementation always fell through to a fixed LTC
        # (Leave Travel Concession) template no matter the subject -
        # this is the exact defect being fixed.
        tool = InstitutionalNoteDraftCmp()

        result = tool.generate(request_text="draft a note about the insurance policy renewal")

        note = result["note_sheet"].lower()
        self.assertNotIn("leave travel concession", note)
        self.assertNotIn("ltc advance", note)

    def test_justification_is_included_when_actually_stated(self):
        tool = InstitutionalNoteDraftCmp()

        result = tool.generate(
            request_text=(
                "draft a note about the lab equipment purchase because the "
                "existing oscilloscopes are no longer functional"
            )
        )

        self.assertIn(
            "existing oscilloscopes are no longer functional",
            result["note_sheet"].lower(),
        )

    def test_no_justification_stated_produces_no_fabricated_justification(self):
        tool = InstitutionalNoteDraftCmp()

        result = tool.generate(request_text="draft a note about the seminar hall booking")

        # Nothing about "because"/justification content was given -
        # the note must not invent a reason that was never stated.
        self.assertNotIn("because", result["note_sheet"].lower())

    def test_a_generic_request_with_no_subject_falls_back_to_the_request_itself(self):
        tool = InstitutionalNoteDraftCmp()

        result = tool.generate(request_text="draft a note")

        self.assertEqual(result["status"], "success")
        self.assertIn("note_sheet", result)
        # Still not the old fixed LTC template.
        self.assertNotIn("leave travel concession", result["note_sheet"].lower())

    def test_empty_request_text_does_not_crash(self):
        tool = InstitutionalNoteDraftCmp()

        result = tool.generate(request_text="")

        self.assertEqual(result["status"], "success")
        self.assertIn("Administrative Matter", result["note_sheet"])


if __name__ == "__main__":
    unittest.main()
