"""M17 architecture tests: URI drafting is instruction/rule-driven and
Brain-authored, not a fixed Python template.

These tests drive the drafting path with a FAKE ModelProvider (the
"Brain") so they are deterministic and need no running model. The fake
records the exact system/user prompts it was given and returns a body
built from them - which lets the tests assert two things the old
architecture could not deliver:

  1. The Brain is genuinely handed rules/conventions/purpose/evidence
     (not a finished template), and is the thing that authors the body.
  2. Different purposes produce genuinely different guidance/structure -
     an appointment order and a cancellation order are not the same
     document with one slot swapped.
"""

import json
import unittest

from uri_core.config.institutional_rules import (
    DEFAULT_INSTITUTIONAL_RULES,
    load_institutional_rules,
)
from uri_core.core.document_validation import validate_drafted_document
from uri_core.core.model_providers import (
    ModelResponse,
    ProviderUnavailableError,
)
from uri_core.services.document_composer import DocumentComposer
from uri_core.services.drafting_guidance import (
    build_drafting_brief,
    classify_purpose,
    infer_document_type,
    is_urgent,
)
from uri_core.services.institutional_drafting import (
    draft_institutional_document,
)
from uri_core.tools.draft_institutional_note import InstitutionalNoteDraftCmp
from uri_core.tools.draft_institutional_order import (
    InstitutionalOrderDraftCmp,
)


class _RecordingProvider:
    """A fake Brain. Records every prompt pair, and returns a document
    body that echoes the request and the suggested sections it was
    given, so a test can prove the Brain (not a template) shaped the
    output and that it received real guidance."""

    def __init__(self):
        self.calls = []

    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        self.calls.append({"system": system, "user": user})
        payload = {}
        start = user.find("{")
        end = user.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                payload = json.loads(user[start:end + 1])
            except json.JSONDecodeError:
                payload = {}
        request = payload.get("request", "")
        purpose = payload.get("purpose", "general")
        body = (
            f"OFFICE DOCUMENT\n\n"
            f"Purpose: {purpose}\n\n"
            f"This document addresses: {request}\n\n"
            f"It is submitted for the consideration of the competent authority."
        )
        return ModelResponse(content=body, model="fake", provider="fake")


class _UnavailableProvider:
    def complete(self, *, system, user, temperature=0.0, max_tokens=None):
        raise ProviderUnavailableError("no model in this test")


class PurposeClassificationTests(unittest.TestCase):

    def test_cancellation_beats_approval(self):
        # "cancel the approval granted earlier" must read as a
        # cancellation, not an approval.
        self.assertEqual(
            classify_purpose("cancel the approval granted earlier"),
            "cancellation",
        )

    def test_appointment_recognised(self):
        self.assertEqual(
            classify_purpose("constitute a committee to review the mess"),
            "appointment",
        )

    def test_recommendation_recognised(self):
        self.assertEqual(
            classify_purpose("prepare a note where the committee recommends option B"),
            "recommendation",
        )

    def test_procurement_recognised(self):
        self.assertEqual(
            classify_purpose("note seeking approval for purchase of 10 laptops"),
            "procurement",
        )

    def test_plain_approval_recognised(self):
        self.assertEqual(
            classify_purpose("seek approval for the seminar"),
            "approval",
        )

    def test_unknown_purpose_is_general_not_error(self):
        self.assertEqual(classify_purpose("write something about the library"), "general")

    def test_urgency_is_a_modifier(self):
        self.assertTrue(is_urgent("urgent approval needed immediately"))
        self.assertFalse(is_urgent("approval needed for the seminar"))

    def test_document_type_inference(self):
        self.assertEqual(infer_document_type("issue an office order"), "office_order")
        self.assertEqual(infer_document_type("draft a note about X"), "noting")


class BriefIsGuidanceNotTemplateTests(unittest.TestCase):

    def test_brief_carries_purpose_specific_suggested_sections(self):
        cancellation = build_drafting_brief(
            request_text="cancel office order NITS/2025/12 constituting the mess committee",
            document_type="office_order",
        )
        appointment = build_drafting_brief(
            request_text="constitute a committee to review the mess",
            document_type="office_order",
        )

        # Same document KIND, different PURPOSE -> genuinely different
        # suggested structure. This is the axis the old architecture
        # ignored entirely.
        self.assertEqual(cancellation["document_type"], "office_order")
        self.assertEqual(appointment["document_type"], "office_order")
        self.assertNotEqual(
            cancellation["suggested_sections"],
            appointment["suggested_sections"],
        )
        self.assertTrue(
            any("cancellation" in s.lower() for s in cancellation["suggested_sections"])
        )
        self.assertTrue(
            any(
                "member" in s.lower() or "terms of reference" in s.lower()
                for s in appointment["suggested_sections"]
            )
        )

    def test_sections_are_suggested_not_mandated(self):
        # The brief labels sections as suggested; the composer prompt
        # must present them as adaptable, not a checklist.
        brief = build_drafting_brief(request_text="draft a note", document_type="noting")
        self.assertIn("suggested_sections", brief)
        self.assertNotIn("required_sections", brief)


class BrainAuthorsTheBodyTests(unittest.TestCase):

    def test_composer_calls_the_brain_and_uses_its_output(self):
        provider = _RecordingProvider()
        composer = DocumentComposer(provider=provider)
        brief = build_drafting_brief(
            request_text="seek approval for a seminar", document_type="noting"
        )

        result = composer.compose(
            brief=brief,
            request_text="seek approval for a seminar",
            evidence={},
            preferences={},
            soul_text="URI voice.",
        )

        self.assertEqual(result["composed_by"], "brain")
        self.assertEqual(len(provider.calls), 1)
        # The Brain was handed the institutional conventions and the
        # policy-driven "compose the document itself" instruction, i.e.
        # rules/guidance - not a finished body to return verbatim.
        system = provider.calls[0]["system"]
        self.assertIn("institutional", system.lower())
        self.assertIn("document itself", system.lower())
        self.assertIn("seek approval for a seminar", result["body"])

    def test_two_purposes_produce_different_documents_through_the_brain(self):
        provider = _RecordingProvider()

        appointment = draft_institutional_document(
            request_text="constitute a committee to review the mess",
            document_type="office_order",
            composer=DocumentComposer(provider=provider),
        )
        cancellation = draft_institutional_document(
            request_text="cancel the order constituting the mess committee",
            document_type="office_order",
            composer=DocumentComposer(provider=provider),
        )

        self.assertEqual(appointment["composed_by"], "brain")
        self.assertEqual(cancellation["composed_by"], "brain")
        self.assertNotEqual(appointment["note_sheet"], cancellation["note_sheet"])
        self.assertEqual(appointment["drafting_brief"]["purpose"], "appointment")
        self.assertEqual(cancellation["drafting_brief"]["purpose"], "cancellation")

    def test_no_hardcoded_nit_banner_in_output_when_brain_composes(self):
        # The old order tool emitted a frozen "NATIONAL INSTITUTE OF
        # TECHNOLOGY SIKKIM" banner and a literal "NITS/2026/Admin/
        # Order/___" reference regardless of input. With the Brain
        # authoring, no such literal is injected by URI code.
        provider = _RecordingProvider()
        result = draft_institutional_document(
            request_text="issue an office order appointing a warden",
            document_type="office_order",
            composer=DocumentComposer(provider=provider),
        )
        self.assertNotIn("NITS/2026/Admin/Order/___", result["note_sheet"])


class InstitutionIsConfigurableTests(unittest.TestCase):

    def test_default_rules_are_data_not_rendered_text(self):
        rules = load_institutional_rules(path="/does/not/exist.json")
        self.assertEqual(rules["short_name"], DEFAULT_INSTITUTIONAL_RULES["short_name"])
        # A format string, never a pre-rendered literal reference number.
        self.assertIn("{year}", rules["reference_number_format"])

    def test_institution_can_be_overridden_and_reaches_the_brain(self):
        provider = _RecordingProvider()
        composer = DocumentComposer(provider=provider)
        brief = build_drafting_brief(
            request_text="issue an order",
            document_type="office_order",
            institutional_rules={
                "institution_name": "Example University",
                "short_name": "ExU",
            },
        )
        composer.compose(
            brief=brief,
            request_text="issue an order",
            evidence={},
            preferences={},
        )
        system = provider.calls[0]["system"]
        self.assertIn("Example University", system)
        self.assertNotIn("National Institute of Technology Sikkim", system)


class EvidenceInfluencesDraftingTests(unittest.TestCase):

    def test_evidence_is_passed_to_the_brain(self):
        provider = _RecordingProvider()
        composer = DocumentComposer(provider=provider)
        brief = build_drafting_brief(
            request_text="draft a note summarising the attached report",
            document_type="noting",
            evidence={"attached_documents": [{"filename": "report.pdf", "text": "Budget overrun of 12 lakh."}]},
        )
        composer.compose(
            brief=brief,
            request_text="draft a note summarising the attached report",
            evidence={"attached_documents": [{"filename": "report.pdf", "text": "Budget overrun of 12 lakh."}]},
            preferences={},
        )
        user_prompt = provider.calls[0]["user"]
        self.assertIn("Budget overrun of 12 lakh.", user_prompt)
        self.assertIn("report.pdf", user_prompt)


class DocumentValidationProfileTests(unittest.TestCase):

    def test_long_document_is_accepted(self):
        # A real order can be long; the narrative 400/2000-char caps must
        # not apply here.
        body = "OFFICE ORDER\n\n" + ("This clause is operative. " * 120)
        verdict = validate_drafted_document(body)
        self.assertTrue(verdict["valid"])
        self.assertGreater(len(body), 2000)

    def test_chat_preamble_is_rejected(self):
        verdict = validate_drafted_document(
            "Sure! Here is the office order you asked for:\n\nOFFICE ORDER..."
        )
        self.assertFalse(verdict["valid"])

    def test_empty_is_rejected(self):
        self.assertFalse(validate_drafted_document("")["valid"])

    def test_composer_falls_back_when_draft_fails_validation(self):
        class _ChattyProvider:
            def complete(self, *, system, user, temperature=0.0, max_tokens=None):
                return ModelResponse(
                    content="Sure, here is your draft!", model="f", provider="f"
                )

        composer = DocumentComposer(provider=_ChattyProvider())
        brief = build_drafting_brief(request_text="draft a note", document_type="noting")
        result = composer.compose(
            brief=brief, request_text="draft a note", evidence={}, preferences={}
        )
        self.assertEqual(result["composed_by"], "fallback")
        self.assertIsNotNone(result["detail"])


class FallbackIsHonestNotATemplateTests(unittest.TestCase):

    def test_unreachable_model_yields_plain_labelled_draft(self):
        composer = DocumentComposer(provider=_UnavailableProvider())
        result = draft_institutional_document(
            request_text="cancel the mess committee order",
            document_type="office_order",
            composer=composer,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["composed_by"], "fallback")
        # The fallback is honest about being an unpolished draft and does
        # NOT fabricate an institutional banner/reference/signatory.
        self.assertIn("unpolished draft", result["note_sheet"].lower())
        self.assertNotIn("NITS/2026/Admin/Order/___", result["note_sheet"])

    def test_tools_return_note_sheet_contract(self):
        # Existing consumers depend on {"status","note_sheet"}.
        note = InstitutionalNoteDraftCmp(composer=DocumentComposer(provider=_UnavailableProvider()))
        order = InstitutionalOrderDraftCmp(composer=DocumentComposer(provider=_UnavailableProvider()))
        note_result = note.generate(request_text="draft a note about the seminar")
        order_result = order.generate(request_text="issue an order appointing a warden")
        for result in (note_result, order_result):
            self.assertEqual(result["status"], "success")
            self.assertIn("note_sheet", result)
            self.assertTrue(result["note_sheet"].strip())


if __name__ == "__main__":
    unittest.main()
