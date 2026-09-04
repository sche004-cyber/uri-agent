import unittest

from uri_core.core.audit_trail import (
    AuditEvent,
    AuditTrail,
    AuditValidationError,
    InMemoryAuditEventStore,
)


class AuditEventCreationTests(unittest.TestCase):

    def test_event_has_generated_id_and_timestamp(self):

        event = AuditEvent(
            event_type="capability_call", status="started"
        )

        self.assertTrue(event.event_id)

        self.assertTrue(event.timestamp)

    def test_two_events_get_different_ids(self):

        first = AuditEvent(
            event_type="capability_call", status="started"
        )

        second = AuditEvent(
            event_type="capability_call", status="started"
        )

        self.assertNotEqual(first.event_id, second.event_id)

    def test_optional_fields_default_to_none_or_empty(self):

        event = AuditEvent(
            event_type="capability_call", status="started"
        )

        self.assertIsNone(event.session_id)

        self.assertIsNone(event.workflow_id)

        self.assertIsNone(event.capability)

        self.assertEqual(event.metadata, {})

    def test_missing_event_type_is_rejected(self):

        with self.assertRaises(AuditValidationError):

            AuditEvent(event_type="", status="started")

    def test_missing_status_is_rejected(self):

        with self.assertRaises(AuditValidationError):

            AuditEvent(event_type="capability_call", status="")


class AuditEventCredentialValidationTests(unittest.TestCase):

    def test_credential_shaped_key_is_rejected(self):

        with self.assertRaises(AuditValidationError):

            AuditEvent(
                event_type="capability_call",
                status="started",
                metadata={"api_key": "irrelevant-value"},
            )

    def test_credential_shaped_value_is_rejected(self):

        with self.assertRaises(AuditValidationError):

            AuditEvent(
                event_type="capability_call",
                status="started",
                metadata={
                    "note": "gsk_someobviouslygroqshapedvalue1234"
                },
            )

    def test_bearer_token_value_is_rejected(self):

        with self.assertRaises(AuditValidationError):

            AuditEvent(
                event_type="capability_call",
                status="started",
                metadata={"header": "Bearer abc.def.ghi"},
            )

    def test_oversized_metadata_value_is_rejected(self):

        with self.assertRaises(AuditValidationError):

            AuditEvent(
                event_type="capability_call",
                status="started",
                metadata={"payload": "x" * 501},
            )

    def test_ordinary_metadata_is_accepted(self):

        event = AuditEvent(
            event_type="capability_call",
            status="success",
            metadata={
                "argument_count": 2,
                "duration_ms": 45,
                "note": "looked up student record",
            },
        )

        self.assertEqual(event.metadata["argument_count"], 2)


class InMemoryAuditEventStoreTests(unittest.TestCase):

    def setUp(self):
        self.store = InMemoryAuditEventStore()

    def test_append_and_query_round_trip(self):

        event = AuditEvent(
            event_type="capability_call",
            status="success",
            session_id="s1",
        )

        self.store.append(event)

        results = self.store.query(session_id="s1")

        self.assertEqual(results, [event])

    def test_only_audit_events_may_be_appended(self):

        with self.assertRaises(AuditValidationError):

            self.store.append({"not": "an event"})

    def test_query_filters_by_session_and_workflow(self):

        self.store.append(
            AuditEvent(
                event_type="capability_call",
                status="success",
                session_id="s1",
                workflow_id="w1",
            )
        )

        self.store.append(
            AuditEvent(
                event_type="capability_call",
                status="success",
                session_id="s2",
                workflow_id="w1",
            )
        )

        by_session = self.store.query(session_id="s1")

        self.assertEqual(len(by_session), 1)

        self.assertEqual(by_session[0].session_id, "s1")

        by_workflow = self.store.query(workflow_id="w1")

        self.assertEqual(len(by_workflow), 2)

    def test_query_filters_by_event_type_and_status(self):

        self.store.append(
            AuditEvent(
                event_type="capability_call", status="started"
            )
        )

        self.store.append(
            AuditEvent(
                event_type="capability_call", status="success"
            )
        )

        self.store.append(
            AuditEvent(
                event_type="workflow_transition", status="success"
            )
        )

        successful_calls = self.store.query(
            event_type="capability_call", status="success"
        )

        self.assertEqual(len(successful_calls), 1)

        self.assertEqual(successful_calls[0].status, "success")

    def test_query_with_no_matches_returns_empty_list(self):

        results = self.store.query(session_id="does-not-exist")

        self.assertEqual(results, [])

    def test_events_are_returned_in_recording_order(self):

        recorded = [
            AuditEvent(
                event_type="capability_call",
                status="started",
                workflow_id="w1",
            )
            for _ in range(5)
        ]

        for event in recorded:
            self.store.append(event)

        results = self.store.query(workflow_id="w1")

        self.assertEqual(
            [e.event_id for e in results],
            [e.event_id for e in recorded],
        )


class AuditTrailFacadeTests(unittest.TestCase):

    def test_record_creates_and_stores_an_event(self):

        trail = AuditTrail()

        event = trail.record(
            event_type="capability_call",
            status="success",
            session_id="s1",
            workflow_id="w1",
            capability="draft_institutional_note",
            metadata={"argument_count": 1},
        )

        self.assertEqual(trail.for_session("s1"), [event])

        self.assertEqual(trail.for_workflow("w1"), [event])

    def test_default_store_is_in_memory(self):

        trail = AuditTrail()

        self.assertIsInstance(trail.store, InMemoryAuditEventStore)

    def test_custom_store_can_be_injected(self):

        custom_store = InMemoryAuditEventStore()

        trail = AuditTrail(store=custom_store)

        trail.record(event_type="capability_call", status="success")

        self.assertIs(trail.store, custom_store)

        self.assertEqual(len(custom_store.query()), 1)

    def test_record_rejects_credential_shaped_metadata(self):

        trail = AuditTrail()

        with self.assertRaises(AuditValidationError):

            trail.record(
                event_type="capability_call",
                status="success",
                metadata={"token": "sk-obviouslysecretvalue"},
            )

        self.assertEqual(trail.for_session("anything"), [])

    def test_all_events_returns_every_recorded_event(self):

        trail = AuditTrail()

        first = trail.record(
            event_type="skill_router_shadow_evaluation",
            status="shadow_completed",
            session_id="s1",
        )

        second = trail.record(
            event_type="model_reasoning_shadow_evaluation",
            status="proposal_ready",
            session_id="s2",
        )

        self.assertEqual(trail.all_events(), [first, second])

    def test_all_events_can_be_filtered_by_event_type(self):

        trail = AuditTrail()

        trail.record(
            event_type="skill_router_shadow_evaluation",
            status="shadow_completed",
        )

        model_event = trail.record(
            event_type="model_reasoning_shadow_evaluation",
            status="proposal_ready",
        )

        self.assertEqual(
            trail.all_events(event_type="model_reasoning_shadow_evaluation"),
            [model_event],
        )


if __name__ == "__main__":
    unittest.main()
