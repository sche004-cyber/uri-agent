import unittest

from uri_core.core.capability_registry import CapabilityDescriptor
from uri_core.core.evidence_context import (
    evidence_summary,
    get_verified_evidence,
)
from uri_core.core.facts import Fact
from uri_core.core.personalization_context import (
    build_personalization_context,
)
from uri_core.core.query_context import build_query_context
from uri_core.core.user_memory import MemoryEntry
from uri_core.core.user_profile import UserProfile


class _FakeSession:
    """Minimal stand-in for state.SessionState - only carries the one
    attribute evidence_context.py actually reads, so these tests do
    not depend on SessionManager/session persistence at all."""

    def __init__(self, evidence_facts):
        self.evidence_facts = evidence_facts


def _capability(
    id="draft_institutional_note",
    description="Drafts an office note.",
    status="implemented",
    availability="available",
    permissions=None,
    approval_requirement="user_approval_required",
    risk="low",
    limitations="Requires evidence context.",
):
    return CapabilityDescriptor(
        id=id,
        description=description,
        status=status,
        availability=availability,
        permissions=permissions or ["file_write"],
        approval_requirement=approval_requirement,
        risk=risk,
        limitations=limitations,
    )


class BuildQueryContextTests(unittest.TestCase):

    def test_all_sections_present_with_no_arguments(self):
        context = build_query_context()

        self.assertEqual(
            set(context.keys()),
            {
                "identity",
                "soul",
                "personalization",
                "session",
                "verified_facts",
                "capabilities",
                "diagnostics",
                "experience",
                "attachments",
                "conversation",
            },
        )
        self.assertEqual(context["identity"], "")
        self.assertEqual(context["soul"], "")
        self.assertEqual(context["personalization"], {})
        self.assertEqual(context["session"], {})
        self.assertEqual(context["verified_facts"], {})
        self.assertEqual(context["capabilities"], [])
        self.assertEqual(context["experience"], [])
        self.assertEqual(context["attachments"], [])
        self.assertEqual(context["diagnostics"], {})
        self.assertEqual(context["conversation"], [])

    def test_identity_policy_text_is_passed_through_verbatim(self):
        context = build_query_context(policy_text="UNIQUE-POLICY-MARKER")

        self.assertEqual(context["identity"], "UNIQUE-POLICY-MARKER")

    def test_soul_text_is_passed_through_verbatim_and_separate_from_identity(
        self,
    ):
        context = build_query_context(
            policy_text="UNIQUE-POLICY-MARKER",
            soul_text="UNIQUE-SOUL-MARKER",
        )

        self.assertEqual(context["soul"], "UNIQUE-SOUL-MARKER")
        self.assertEqual(context["identity"], "UNIQUE-POLICY-MARKER")
        self.assertNotEqual(context["soul"], context["identity"])

    def test_diagnostics_is_passed_through_unchanged(self):
        diagnostics = {
            "last_operation": {"capability": "web_search", "status": "error"},
            "recent_events": [],
            "known_gaps": [],
        }

        context = build_query_context(diagnostics=diagnostics)

        self.assertEqual(context["diagnostics"], diagnostics)

    def test_experience_is_passed_through_unchanged(self):
        experience = [
            {
                "category": "reference_pattern",
                "intent": "draft an office order",
                "summary": "Office orders follow a fixed format.",
                "actions": [],
                "results": "",
                "unresolved": [],
                "created_at": "2026-09-07T00:00:00+00:00",
            }
        ]

        context = build_query_context(experience=experience)

        self.assertEqual(context["experience"], experience)

    def test_attachments_are_references_only_never_content(self):
        # M16: the Brain may see THAT a file is attached and what it is,
        # never its content - reading requires selecting the
        # read_attached_file capability.
        attachments = [
            {
                "file_id": "f1",
                "filename": "minutes.pdf",
                "media_type": "application/pdf",
                "size_bytes": 2048,
            }
        ]

        context = build_query_context(attachments=attachments)

        self.assertEqual(context["attachments"], attachments)
        self.assertNotIn("text", context["attachments"][0])
        self.assertNotIn("stored_name", context["attachments"][0])

    def test_session_context_is_passed_through_unchanged(self):
        session_context = {"task": "noting", "active_workflow_status": None}

        context = build_query_context(session_context=session_context)

        self.assertEqual(context["session"], session_context)

    def test_result_is_json_shaped_data(self):
        context = build_query_context(
            policy_text="policy",
            personalization={"communication_style": "formal"},
            session_context={"task": "noting"},
            verified_facts={"institution": {"value": "NIT Sikkim"}},
            capabilities=[_capability()],
        )

        self.assertIsInstance(context, dict)
        self.assertIsInstance(context["capabilities"], list)


class PersonalizationPassThroughTests(unittest.TestCase):
    """Proves query_context relays build_personalization_context's own
    consent decision unchanged - it must never re-derive or re-filter
    eligibility itself (see personalization_context.py's own boundary
    doc)."""

    def _memory(self, consent):
        return MemoryEntry(
            memory_id="m1",
            category="interest",
            consent=consent,
            fact=Fact(name="interest", value="badminton", status="CONFIRMED"),
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

    def test_eligible_memory_reaches_query_context(self):
        profile = UserProfile(communication_style="formal")
        personalization = build_personalization_context(
            profile, [self._memory(consent="user_confirmed")]
        )

        context = build_query_context(personalization=personalization)

        self.assertEqual(
            context["personalization"]["communication_style"], "formal"
        )
        self.assertEqual(len(context["personalization"]["memory"]), 1)

    def test_pending_confirmation_memory_never_reaches_query_context(self):
        personalization = build_personalization_context(
            None, [self._memory(consent="pending_confirmation")]
        )

        context = build_query_context(personalization=personalization)

        self.assertEqual(context["personalization"]["memory"], [])


class VerifiedEvidenceOnlyTests(unittest.TestCase):
    """Proves the verified-only boundary survives end to end: only
    VERIFIED-status facts make it into query_context, via
    evidence_context.get_verified_evidence()/evidence_summary() - never
    evidence_context.get_relevant_evidence()'s scenario-specific
    keyword taxonomy."""

    def test_only_verified_status_facts_reach_query_context(self):
        session = _FakeSession(
            evidence_facts={
                "institution": Fact(
                    name="institution",
                    value="NIT Sikkim",
                    status="VERIFIED",
                    source="Evidence",
                ),
                "draft_guess": Fact(
                    name="draft_guess",
                    value="unverified",
                    status="PROVISIONAL",
                    source="User",
                ),
            }
        )

        verified_facts = evidence_summary(get_verified_evidence(session))
        context = build_query_context(verified_facts=verified_facts)

        self.assertIn("institution", context["verified_facts"])
        self.assertNotIn("draft_guess", context["verified_facts"])

    def test_no_verified_facts_produces_empty_section(self):
        session = _FakeSession(
            evidence_facts={
                "draft_guess": Fact(
                    name="draft_guess",
                    value="unverified",
                    status="PROVISIONAL",
                    source="User",
                ),
            }
        )

        verified_facts = evidence_summary(get_verified_evidence(session))
        context = build_query_context(verified_facts=verified_facts)

        self.assertEqual(context["verified_facts"], {})


class CapabilityDescriptorFieldsTests(unittest.TestCase):
    """Proves the fields the Brain needs to reason about capability
    relevance and constraints itself all survive serialization -
    without this module ever scoring or selecting among them."""

    def test_constraint_approval_and_risk_fields_are_retained(self):
        descriptor = _capability(
            id="draft_institutional_order",
            approval_requirement="user_approval_required",
            risk="variable",
            permissions=["file_write", "external_send"],
            limitations="Cannot send externally without approval.",
        )

        context = build_query_context(capabilities=[descriptor])

        entry = context["capabilities"][0]
        self.assertEqual(entry["id"], "draft_institutional_order")
        self.assertEqual(
            entry["approval_requirement"], "user_approval_required"
        )
        self.assertEqual(entry["risk"], "variable")
        self.assertEqual(
            entry["permissions"], ["file_write", "external_send"]
        )
        self.assertEqual(
            entry["limitations"],
            "Cannot send externally without approval.",
        )

    def test_not_implemented_gap_reason_is_retained(self):
        descriptor = _capability(
            id="pc_system_optimization",
            status="not_implemented",
            availability="unknown",
        )

        context = build_query_context(capabilities=[descriptor])

        self.assertEqual(
            context["capabilities"][0]["gap_reason"], "not_implemented"
        )

    def test_unavailable_runtime_gap_reason_is_retained(self):
        descriptor = _capability(
            id="gmail_send",
            status="implemented",
            availability="unavailable_missing_dependency",
        )

        context = build_query_context(capabilities=[descriptor])

        self.assertEqual(
            context["capabilities"][0]["gap_reason"],
            "unavailable_runtime",
        )

    def test_interface_schema_is_retained_for_body_awareness(self):
        descriptor = CapabilityDescriptor(
            id="pc_system_optimization",
            description="Inspect/optimize this device.",
            status="not_implemented",
            availability="unavailable_missing_dependency",
            interface={
                "kind": "system_diagnostics",
                "summary_fields": ["cpu_usage", "ram_usage"],
            },
        )

        context = build_query_context(capabilities=[descriptor])

        self.assertEqual(
            context["capabilities"][0]["interface"],
            {
                "kind": "system_diagnostics",
                "summary_fields": ["cpu_usage", "ram_usage"],
            },
        )

    def test_available_capability_has_no_gap_reason(self):
        descriptor = _capability(status="implemented", availability="available")

        context = build_query_context(capabilities=[descriptor])

        self.assertIsNone(context["capabilities"][0]["gap_reason"])

    def test_no_selection_or_scoring_all_capabilities_pass_through(self):
        # M10A must not filter/score capabilities - every descriptor
        # given must survive, regardless of status/availability.
        descriptors = [
            _capability(id="a", status="implemented"),
            _capability(id="b", status="not_implemented"),
            _capability(id="c", status="planned"),
        ]

        context = build_query_context(capabilities=descriptors)

        self.assertEqual(
            {entry["id"] for entry in context["capabilities"]},
            {"a", "b", "c"},
        )

    def test_non_descriptor_entries_are_dropped_defensively(self):
        context = build_query_context(
            capabilities=[_capability(id="a"), "not-a-descriptor", None]
        )

        self.assertEqual(len(context["capabilities"]), 1)
        self.assertEqual(context["capabilities"][0]["id"], "a")


if __name__ == "__main__":
    unittest.main()
