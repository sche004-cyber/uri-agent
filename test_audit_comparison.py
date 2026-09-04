import unittest

from uri_core.core.audit_comparison import (
    MODEL_REASONING_EVENT_TYPE,
    SKILL_ROUTER_EVENT_TYPE,
    build_shadow_comparison_report,
    summarize_shadow_comparisons,
)
from uri_core.core.audit_trail import AuditEvent


def _event(
    event_type,
    agrees=None,
    capability="draft_institutional_note",
    planner_tool_name="draft_institutional_note",
    status="shadow_completed",
    timestamp=None,
):
    metadata = {"planner_tool_name": planner_tool_name}

    if agrees is not None:
        metadata["agrees_with_planner"] = agrees

    event = AuditEvent(
        event_type=event_type,
        status=status,
        capability=capability,
        metadata=metadata,
    )

    if timestamp is not None:
        event.timestamp = timestamp

    return event


class SummarizeShadowComparisonsTests(unittest.TestCase):

    def test_empty_list_produces_zeroed_summary_with_no_rate(self):
        summary = summarize_shadow_comparisons([])

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["agreements"], 0)
        self.assertEqual(summary["disagreements"], 0)
        self.assertEqual(summary["unknown"], 0)
        self.assertIsNone(summary["agreement_rate"])
        self.assertEqual(summary["recent"], [])

    def test_counts_agreements_and_disagreements(self):
        events = [
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True),
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True),
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=False),
        ]

        summary = summarize_shadow_comparisons(events)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["agreements"], 2)
        self.assertEqual(summary["disagreements"], 1)
        self.assertEqual(summary["unknown"], 0)
        self.assertAlmostEqual(summary["agreement_rate"], 2 / 3, places=4)

    def test_events_missing_agrees_with_planner_count_as_unknown(self):
        events = [
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True),
            AuditEvent(
                event_type=SKILL_ROUTER_EVENT_TYPE,
                status="shadow_disabled",
                metadata={},
            ),
        ]

        summary = summarize_shadow_comparisons(events)

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["agreements"], 1)
        self.assertEqual(summary["disagreements"], 0)
        self.assertEqual(summary["unknown"], 1)
        # Rate is computed only over agreements+disagreements, not the
        # unknown event, so 1 agreement out of 1 comparable = 1.0.
        self.assertEqual(summary["agreement_rate"], 1.0)

    def test_recent_is_most_recent_first_and_respects_limit(self):
        events = [
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True, timestamp="2026-01-01T00:00:00+00:00"),
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True, timestamp="2026-01-03T00:00:00+00:00"),
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=False, timestamp="2026-01-02T00:00:00+00:00"),
        ]

        summary = summarize_shadow_comparisons(events, recent_limit=2)

        self.assertEqual(len(summary["recent"]), 2)
        self.assertEqual(
            summary["recent"][0]["timestamp"], "2026-01-03T00:00:00+00:00"
        )
        self.assertEqual(
            summary["recent"][1]["timestamp"], "2026-01-02T00:00:00+00:00"
        )

    def test_recent_entries_never_include_raw_metadata_beyond_the_fixed_fields(self):
        events = [_event(SKILL_ROUTER_EVENT_TYPE, agrees=True)]

        summary = summarize_shadow_comparisons(events)

        self.assertEqual(
            set(summary["recent"][0].keys()),
            {
                "timestamp",
                "session_id",
                "status",
                "shadow_capability",
                "planner_tool_name",
                "agrees_with_planner",
            },
        )


class BuildShadowComparisonReportTests(unittest.TestCase):

    def test_splits_events_by_type_independently(self):
        events = [
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True),
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=False),
            _event(MODEL_REASONING_EVENT_TYPE, agrees=True),
        ]

        report = build_shadow_comparison_report(events)

        self.assertEqual(report["skill_router"]["total"], 2)
        self.assertEqual(report["model_reasoning"]["total"], 1)
        self.assertEqual(report["model_reasoning"]["agreements"], 1)

    def test_unrelated_event_types_are_ignored(self):
        events = [
            _event(SKILL_ROUTER_EVENT_TYPE, agrees=True),
            AuditEvent(event_type="capability_call", status="success"),
        ]

        report = build_shadow_comparison_report(events)

        self.assertEqual(report["skill_router"]["total"], 1)
        self.assertEqual(report["model_reasoning"]["total"], 0)

    def test_empty_input_produces_two_empty_summaries(self):
        report = build_shadow_comparison_report([])

        self.assertEqual(report["skill_router"]["total"], 0)
        self.assertEqual(report["model_reasoning"]["total"], 0)
        self.assertIsNone(report["skill_router"]["agreement_rate"])
        self.assertIsNone(report["model_reasoning"]["agreement_rate"])


if __name__ == "__main__":
    unittest.main()
