import unittest

from uri_core.core.audit_trail import AuditEvent
from uri_core.core.capability_registry import CapabilityDescriptor
from uri_core.core.diagnostics_context import build_diagnostics_context


class BuildDiagnosticsContextTests(unittest.TestCase):

    def test_all_sections_present_with_no_arguments(self):
        diagnostics = build_diagnostics_context()

        self.assertEqual(
            set(diagnostics.keys()),
            {"last_operation", "recent_events", "known_gaps"},
        )
        self.assertEqual(diagnostics["last_operation"], {})
        self.assertEqual(diagnostics["recent_events"], [])
        self.assertEqual(diagnostics["known_gaps"], [])

    def test_last_operation_fields_are_retained(self):
        diagnostics = build_diagnostics_context(
            last_operation={
                "capability": "web_search",
                "status": "unavailable",
                "error": "No web-search API key is configured.",
                "message": "URI could not perform a web search.",
                "component": "WebSearchTool",
            }
        )

        self.assertEqual(
            diagnostics["last_operation"],
            {
                "capability": "web_search",
                "status": "unavailable",
                "error": "No web-search API key is configured.",
                "message": "URI could not perform a web search.",
                "component": "WebSearchTool",
            },
        )

    def test_last_operation_never_invents_a_missing_field(self):
        diagnostics = build_diagnostics_context(
            last_operation={"capability": "web_search", "status": "success"}
        )

        self.assertIsNone(diagnostics["last_operation"]["error"])
        self.assertIsNone(diagnostics["last_operation"]["message"])

    def test_non_dict_last_operation_degrades_to_empty(self):
        diagnostics = build_diagnostics_context(last_operation="not-a-dict")
        self.assertEqual(diagnostics["last_operation"], {})

    def test_audit_events_are_condensed_and_bounded(self):
        events = [
            AuditEvent(
                event_type="capability_execution",
                status="error",
                session_id="s1",
                capability="web_search",
                metadata={"reason": "unavailable"},
            )
            for _ in range(10)
        ]

        diagnostics = build_diagnostics_context(recent_events=events)

        self.assertEqual(len(diagnostics["recent_events"]), 5)
        entry = diagnostics["recent_events"][0]
        self.assertEqual(entry["event_type"], "capability_execution")
        self.assertEqual(entry["status"], "error")
        self.assertEqual(entry["capability"], "web_search")
        self.assertEqual(entry["metadata"]["reason"], "unavailable")

    def test_known_gaps_only_include_entries_with_a_real_gap_reason(self):
        available = CapabilityDescriptor(
            id="web_search",
            description="Search the web.",
            status="implemented",
            availability="available",
        )
        not_implemented = CapabilityDescriptor(
            id="pc_system_optimization",
            description="Optimize this device.",
            status="not_implemented",
            availability="unavailable_missing_dependency",
            limitations="No execution adapter exists yet.",
        )

        diagnostics = build_diagnostics_context(
            known_gaps=[available, not_implemented]
        )

        self.assertEqual(len(diagnostics["known_gaps"]), 1)
        self.assertEqual(
            diagnostics["known_gaps"][0]["id"], "pc_system_optimization"
        )
        self.assertEqual(
            diagnostics["known_gaps"][0]["gap_reason"], "not_implemented"
        )

    def test_malformed_event_is_dropped_not_raised(self):
        diagnostics = build_diagnostics_context(
            recent_events=[None, "not-an-event", 42]
        )

        self.assertEqual(diagnostics["recent_events"], [])


if __name__ == "__main__":
    unittest.main()
