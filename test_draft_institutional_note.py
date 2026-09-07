"""Regression tests for draft_institutional_note.

Updated for M17: the tool no longer emits a fixed Python template - it
delegates to the Brain-centric drafting path (services/
institutional_drafting.py -> document_composer.py), which authors the
body via the reasoning model. A Brain-authored body is non-deterministic,
so these tests pin the tool to its DETERMINISTIC FALLBACK (by injecting
an unreachable provider) and assert the invariants that must hold
regardless of the model: the subject is reflected, a stated
justification survives, nothing is fabricated when unstated, no fixed
legacy template leaks, and an empty request never crashes. The
Brain-authored happy path and purpose-differentiation are covered
separately in test_m17_drafting_architecture.py.
"""

import unittest

from uri_core.core.model_providers import ProviderUnavailableError
from uri_core.services.document_composer import DocumentComposer
from uri_core.tools.draft_institutional_note import InstitutionalNoteDraftCmp


class _UnavailableProvider:
    """Forces the composer's deterministic fallback, so these tests are
    hermetic and never depend on a running model."""

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        raise ProviderUnavailableError("model intentionally unavailable in test")


def _tool():
    return InstitutionalNoteDraftCmp(
        composer=DocumentComposer(provider=_UnavailableProvider())
    )


class MaterialInputDifferenceTests(unittest.TestCase):

    def test_two_different_subjects_produce_different_notes(self):
        tool = _tool()

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
        # The original defect was a fixed LTC (Leave Travel Concession)
        # template regardless of subject. No template exists now, so this
        # can never reappear.
        tool = _tool()

        result = tool.generate(request_text="draft a note about the insurance policy renewal")

        note = result["note_sheet"].lower()
        self.assertNotIn("leave travel concession", note)
        self.assertNotIn("ltc advance", note)

    def test_justification_is_included_when_actually_stated(self):
        tool = _tool()

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
        tool = _tool()

        result = tool.generate(request_text="draft a note about the seminar hall booking")

        # Nothing about a reason was given - the deterministic fallback
        # must not invent one.
        self.assertNotIn("because", result["note_sheet"].lower())

    def test_a_generic_request_with_no_subject_does_not_crash_or_templatise(self):
        tool = _tool()

        result = tool.generate(request_text="draft a note")

        self.assertEqual(result["status"], "success")
        self.assertIn("note_sheet", result)
        self.assertNotIn("leave travel concession", result["note_sheet"].lower())

    def test_empty_request_text_does_not_crash(self):
        tool = _tool()

        result = tool.generate(request_text="")

        self.assertEqual(result["status"], "success")
        self.assertIn("Administrative Matter", result["note_sheet"])


if __name__ == "__main__":
    unittest.main()
