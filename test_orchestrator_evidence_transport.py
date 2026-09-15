"""Offline/unit tests for the generalized trusted inter-step evidence
transport (orchestrator.py: _extract_evidence_items_from_step_output /
_resolve_step_decision_context), approved as the smallest URI-native
generalization of Pilot 2's URL-only mechanism (docs/plans/
URI_NATIVE_TOOL_PILOTS.md's "Recommended migration path", closed via
the accepted architecture plan).

Reuses decision_context["verified_evidence"] - the seam institutional_
drafting.py/generate_document.py already merge attached-file evidence
through - never a new store, never a second workflow engine. All tests
are pure/offline: no live model, no live network, no live account.
"""

import unittest

from uri_core.core.orchestrator import UriOrchestrator


def _orchestrator():
    # No collaborators are used by the methods under test (they read
    # only class constants and their own arguments) - a bare instance
    # via __new__ is sufficient and keeps these tests fully offline.
    return UriOrchestrator.__new__(UriOrchestrator)


class WebSearchEvidenceExtractionTests(unittest.TestCase):
    def test_extracts_typed_items_from_real_result_shape(self):
        orch = _orchestrator()
        output = {
            "status": "success",
            "results": [
                {"title": "NIT Sikkim - Home", "url": "https://nitsikkim.ac.in", "content": "Welcome to NIT Sikkim."},
                {"title": "Student Welfare", "url": "https://nitsikkim.ac.in/welfare", "content": "Welfare activities."},
            ],
        }
        items = orch._extract_evidence_items_from_step_output("web_search", output)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["evidence_type"], "web_result")
        self.assertEqual(items[0]["summary"], "NIT Sikkim - Home")
        self.assertEqual(items[0]["content"], "Welcome to NIT Sikkim.")
        self.assertEqual(items[0]["metadata"]["url"], "https://nitsikkim.ac.in")
        self.assertFalse(items[0]["truncated"])

    def test_no_results_yields_no_evidence(self):
        orch = _orchestrator()
        output = {"status": "not_found", "message": "The web search returned no results for this query."}
        self.assertEqual(orch._extract_evidence_items_from_step_output("web_search", output), [])


class GmailSearchEvidenceExtractionTests(unittest.TestCase):
    def test_extracts_typed_items_from_real_result_shape(self):
        orch = _orchestrator()
        output = {
            "status": "success",
            "results": [
                {"subject": "Query about mess fee refund amount", "date": "Mon, 14 Sep 2026", "snippet": "refund settlement details for roll MS240005CY"},
            ],
        }
        items = orch._extract_evidence_items_from_step_output("gmail_search", output)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["evidence_type"], "email_message")
        self.assertEqual(items[0]["summary"], "Query about mess fee refund amount")
        self.assertIn("refund settlement", items[0]["content"])
        self.assertEqual(items[0]["metadata"]["date"], "Mon, 14 Sep 2026")

    def test_input_required_yields_no_evidence(self):
        orch = _orchestrator()
        output = {"status": "input_required", "query": None}
        self.assertEqual(orch._extract_evidence_items_from_step_output("gmail_search", output), [])


class GmailFindDraftEvidenceExtractionTests(unittest.TestCase):
    def test_extracts_single_item_from_real_draft_shape(self):
        orch = _orchestrator()
        output = {
            "status": "success",
            "draft": {
                "message_id": "1a089826c5e71080",
                "thread_id": "1a089822f8ae6366",
                "subject": "Day Scholar list 2026",
                "body": "Student's Welfare Office, NIT Sikkim.",
                "attachments": [],
            },
        }
        items = orch._extract_evidence_items_from_step_output("gmail_find_draft", output)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["evidence_type"], "email_draft")
        self.assertEqual(items[0]["summary"], "Day Scholar list 2026")
        self.assertEqual(items[0]["content"], "Student's Welfare Office, NIT Sikkim.")
        self.assertEqual(items[0]["metadata"]["message_id"], "1a089826c5e71080")

    def test_not_found_yields_no_evidence(self):
        orch = _orchestrator()
        output = {"status": "not_found", "message": "No relevant Gmail draft was found."}
        self.assertEqual(orch._extract_evidence_items_from_step_output("gmail_find_draft", output), [])


class DriveSearchEvidenceExtractionTests(unittest.TestCase):
    def test_extracts_typed_items_from_real_files_shape(self):
        orch = _orchestrator()
        output = {
            "status": "success",
            "files": [
                {"id": "1gfg349G2F3ymupKB-t0sRv8rKrM9PbMKn-iOPzgBm7w", "name": "ROOM WISE HOSTEL ALLOTMENT LIST 2026", "mimeType": "application/vnd.google-apps.spreadsheet"},
            ],
        }
        items = orch._extract_evidence_items_from_step_output("drive_search", output)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["evidence_type"], "drive_file")
        self.assertEqual(items[0]["summary"], "ROOM WISE HOSTEL ALLOTMENT LIST 2026")
        self.assertEqual(items[0]["metadata"]["mimeType"], "application/vnd.google-apps.spreadsheet")

    def test_unavailable_yields_no_evidence(self):
        orch = _orchestrator()
        output = {"status": "unavailable", "error": "Drive is not connected."}
        self.assertEqual(orch._extract_evidence_items_from_step_output("drive_search", output), [])


class FetchUrlEvidenceExtractionTests(unittest.TestCase):
    def test_extracts_single_item_from_real_success_shape(self):
        orch = _orchestrator()
        output = {
            "status": "success",
            "url": "https://nitsikkim.ac.in",
            "content_type": "text/html",
            "text": "Jobs / Tenders / Administration / Deans / HODs",
            "truncated": False,
        }
        items = orch._extract_evidence_items_from_step_output("fetch_url", output)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["evidence_type"], "fetched_page")
        self.assertEqual(items[0]["summary"], "https://nitsikkim.ac.in")
        self.assertEqual(items[0]["metadata"]["url"], "https://nitsikkim.ac.in")

    def test_empty_page_yields_no_evidence(self):
        orch = _orchestrator()
        output = {"status": "empty", "message": "The page was fetched but contained no readable text.", "url": "https://x"}
        self.assertEqual(orch._extract_evidence_items_from_step_output("fetch_url", output), [])


class CapAndTruncationTests(unittest.TestCase):
    def test_per_source_item_cap_enforced(self):
        orch = _orchestrator()
        output = {
            "status": "success",
            "results": [
                {"title": f"Result {i}", "url": f"https://x/{i}", "content": "text"} for i in range(10)
            ],
        }
        items = orch._extract_evidence_items_from_step_output("web_search", output)
        self.assertEqual(len(items), orch._MAX_EVIDENCE_ITEMS_PER_SOURCE)

    def test_content_truncated_at_cap(self):
        orch = _orchestrator()
        long_text = "x" * (orch._MAX_EVIDENCE_CONTENT_CHARS + 500)
        output = {"status": "success", "results": [{"subject": "s", "date": "d", "snippet": long_text}]}
        items = orch._extract_evidence_items_from_step_output("gmail_search", output)
        self.assertEqual(len(items[0]["content"]), orch._MAX_EVIDENCE_CONTENT_CHARS)
        self.assertTrue(items[0]["truncated"])


class ResolveStepDecisionContextTests(unittest.TestCase):
    def _workflow_with_search_and_draft(self, search_capability, search_output):
        workflow = {
            "steps": [
                {
                    "step_id": "search_step",
                    "capability": search_capability,
                    "status": "completed",
                    "output": search_output,
                    "depends_on": [],
                },
                {
                    "step_id": "draft_step",
                    "capability": "draft_institutional_note",
                    "status": "pending",
                    "depends_on": ["search_step"],
                },
            ]
        }
        return workflow

    def test_gmail_search_evidence_reaches_draft_step_decision_context(self):
        orch = _orchestrator()
        workflow = self._workflow_with_search_and_draft(
            "gmail_search",
            {"status": "success", "results": [{"subject": "Refund query", "date": "Mon", "snippet": "refund details"}]},
        )
        draft_step = workflow["steps"][1]
        decision_context = orch._resolve_step_decision_context(
            capability_id="draft_institutional_note", step=draft_step, workflow=workflow,
        )
        self.assertIn("verified_evidence", decision_context)
        retrieved = decision_context["verified_evidence"]["retrieved_evidence"]
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["evidence_type"], "email_message")
        self.assertEqual(
            draft_step["evidence_provenance"],
            [{
                "source_step": "search_step",
                "source_capability": "gmail_search",
                "evidence_type": "email_message",
                "trust": "runtime_verified_same_workflow",
            }],
        )

    def test_drive_search_evidence_reaches_generate_document_step(self):
        orch = _orchestrator()
        workflow = {
            "steps": [
                {
                    "step_id": "drive_step",
                    "capability": "drive_search",
                    "status": "completed",
                    "output": {"status": "success", "files": [{"id": "f1", "name": "Report.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}]},
                    "depends_on": [],
                },
                {
                    "step_id": "gen_step",
                    "capability": "generate_document",
                    "status": "pending",
                    "depends_on": ["drive_step"],
                },
            ]
        }
        gen_step = workflow["steps"][1]
        decision_context = orch._resolve_step_decision_context(
            capability_id="generate_document", step=gen_step, workflow=workflow,
        )
        self.assertEqual(
            decision_context["verified_evidence"]["retrieved_evidence"][0]["evidence_type"],
            "drive_file",
        )

    def test_insufficient_evidence_returns_empty_no_fabrication(self):
        orch = _orchestrator()
        workflow = self._workflow_with_search_and_draft(
            "gmail_search",
            {"status": "not_found", "message": "The Gmail search returned no results for this query."},
        )
        draft_step = workflow["steps"][1]
        decision_context = orch._resolve_step_decision_context(
            capability_id="draft_institutional_note", step=draft_step, workflow=workflow,
        )
        self.assertEqual(decision_context, {})
        self.assertNotIn("evidence_provenance", draft_step)

    def test_dependency_not_yet_completed_is_ignored(self):
        orch = _orchestrator()
        workflow = self._workflow_with_search_and_draft(
            "gmail_search",
            {"status": "success", "results": [{"subject": "s", "date": "d", "snippet": "x"}]},
        )
        workflow["steps"][0]["status"] = "pending"
        draft_step = workflow["steps"][1]
        decision_context = orch._resolve_step_decision_context(
            capability_id="draft_institutional_note", step=draft_step, workflow=workflow,
        )
        self.assertEqual(decision_context, {})

    def test_overall_item_cap_enforced_across_multiple_dependencies(self):
        orch = _orchestrator()
        workflow = {
            "steps": [
                {
                    "step_id": "s1", "capability": "web_search", "status": "completed",
                    "output": {"status": "success", "results": [{"title": f"a{i}", "url": "https://x", "content": "c"} for i in range(3)]},
                    "depends_on": [],
                },
                {
                    "step_id": "s2", "capability": "gmail_search", "status": "completed",
                    "output": {"status": "success", "results": [{"subject": f"b{i}", "date": "d", "snippet": "c"} for i in range(3)]},
                    "depends_on": [],
                },
                {
                    "step_id": "draft_step", "capability": "draft_institutional_note", "status": "pending",
                    "depends_on": ["s1", "s2"],
                },
            ]
        }
        draft_step = workflow["steps"][2]
        decision_context = orch._resolve_step_decision_context(
            capability_id="draft_institutional_note", step=draft_step, workflow=workflow,
        )
        retrieved = decision_context["verified_evidence"]["retrieved_evidence"]
        self.assertEqual(len(retrieved), orch._MAX_EVIDENCE_ITEMS_TOTAL)
        self.assertEqual(len(draft_step["evidence_provenance"]), orch._MAX_EVIDENCE_ITEMS_TOTAL)


class BoundaryPreservationTests(unittest.TestCase):
    """fetch_url is not in _EVIDENCE_CONSUMING_CAPABILITIES - its own
    strict literal-URL-in-request-text boundary (Pilot 2) must be
    completely unaffected by this generalization."""

    def test_fetch_url_as_consumer_never_receives_verified_evidence(self):
        orch = _orchestrator()
        workflow = {
            "steps": [
                {
                    "step_id": "search_step", "capability": "web_search", "status": "completed",
                    "output": {"status": "success", "results": [{"title": "t", "url": "https://nitsikkim.ac.in", "content": "c"}]},
                    "depends_on": [],
                },
                {"step_id": "fetch_step", "capability": "fetch_url", "status": "pending", "depends_on": ["search_step"]},
            ]
        }
        fetch_step = workflow["steps"][1]
        decision_context = orch._resolve_step_decision_context(
            capability_id="fetch_url", step=fetch_step, workflow=workflow,
        )
        self.assertEqual(decision_context, {})

        # The pre-existing URL-literal mechanism still fires unchanged.
        request_text = orch._resolve_step_request_text(
            capability_id="fetch_url", step=fetch_step, workflow=workflow, goal="fetch the page",
        )
        self.assertEqual(request_text, "fetch the page\n\nSource URL to fetch: https://nitsikkim.ac.in")
        self.assertEqual(
            fetch_step["evidence_provenance"],
            {
                "source_step": "search_step",
                "source_capability": "web_search",
                "value_type": "url",
                "value": "https://nitsikkim.ac.in",
                "trust": "runtime_verified_same_workflow",
            },
        )

    def test_non_evidence_consuming_capability_gets_no_decision_context(self):
        orch = _orchestrator()
        workflow = {
            "steps": [
                {
                    "step_id": "search_step", "capability": "gmail_search", "status": "completed",
                    "output": {"status": "success", "results": [{"subject": "s", "date": "d", "snippet": "c"}]},
                    "depends_on": [],
                },
                {"step_id": "other_step", "capability": "extract_student_records", "status": "pending", "depends_on": ["search_step"]},
            ]
        }
        other_step = workflow["steps"][1]
        decision_context = orch._resolve_step_decision_context(
            capability_id="extract_student_records", step=other_step, workflow=workflow,
        )
        self.assertEqual(decision_context, {})


if __name__ == "__main__":
    unittest.main()
