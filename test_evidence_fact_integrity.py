import os
import tempfile
import unittest

from uri_core.core.facts import Fact, FactVerificationError
from uri_core.core.fact_manager import update_fact, update_evidence_fact
from uri_core.core.state import SessionManager, SessionState
from uri_core.core.evidence_fact_integrity import (
    EvidenceLedger,
    EvidenceRecord,
    EvidenceStore,
    IntegrityValidationError,
    InMemoryEvidenceStore,
    ProvenanceError,
)


class FactBackwardCompatibilityTests(unittest.TestCase):
    """
    Confirms Fact's pre-existing behavior is unchanged by the new,
    additive fields.
    """

    def test_minimal_construction_still_works(self):

        fact = Fact(name="insurer", value="SBI General")

        self.assertEqual(fact.status, "PROVISIONAL")

    def test_is_current_unchanged(self):

        fact = Fact(
            name="insurer", value="SBI General", status="CONFIRMED"
        )

        self.assertTrue(fact.is_current())

    def test_is_historical_unchanged(self):

        fact = Fact(
            name="insurer", value="SBI General", status="HISTORICAL"
        )

        self.assertTrue(fact.is_historical())

    def test_validate_status_unchanged(self):

        fact = Fact(
            name="insurer", value="SBI General", status="NOT_A_STATUS"
        )

        with self.assertRaises(ValueError):
            fact.validate_status()

    def test_update_fact_created_action_unchanged(self):

        session = SessionState(session_id="compat-test")

        result = update_fact(
            session, Fact(name="insurer", value="SBI General")
        )

        self.assertEqual(result["action"], "CREATED")


class FactNewFieldsTests(unittest.TestCase):

    def test_new_fields_default_safely(self):

        fact = Fact(name="insurer", value="SBI General")

        self.assertEqual(fact.evidence_ids, [])
        self.assertIsNone(fact.confidence)
        self.assertFalse(fact.verified)
        self.assertIsNone(fact.verified_by)
        self.assertIsNone(fact.verified_at)

    def test_evidence_ids_can_be_set_at_construction(self):

        fact = Fact(
            name="insurer",
            value="SBI General",
            evidence_ids=["e1", "e2"],
        )

        self.assertEqual(fact.evidence_ids, ["e1", "e2"])

    def test_confidence_can_be_set_at_construction(self):

        fact = Fact(
            name="insurer", value="SBI General", confidence=0.7
        )

        self.assertEqual(fact.confidence, 0.7)


class FactConfidenceValidationTests(unittest.TestCase):

    def test_confidence_in_range_passes_validation(self):

        fact = Fact(
            name="insurer", value="SBI General", confidence=0.5
        )

        fact.validate_confidence()

    def test_confidence_out_of_range_is_rejected(self):

        fact = Fact(
            name="insurer", value="SBI General", confidence=1.5
        )

        with self.assertRaises(ValueError):
            fact.validate_confidence()

    def test_no_confidence_passes_validation(self):

        Fact(name="insurer", value="SBI General").validate_confidence()


class FactVerificationTests(unittest.TestCase):

    def test_verify_sets_all_three_fields(self):

        fact = Fact(name="insurer", value="SBI General")

        fact.verify(verified_by="registrar")

        self.assertTrue(fact.verified)
        self.assertEqual(fact.verified_by, "registrar")
        self.assertTrue(fact.verified_at)

    def test_verify_requires_non_empty_actor(self):

        fact = Fact(name="insurer", value="SBI General")

        with self.assertRaises(FactVerificationError):
            fact.verify(verified_by="")

    def test_verify_rejects_generic_model_actor(self):

        fact = Fact(name="insurer", value="SBI General")

        with self.assertRaises(FactVerificationError):
            fact.verify(verified_by="model")

    def test_verify_rejects_named_llm_providers(self):

        fact = Fact(name="insurer", value="SBI General")

        for actor in ("gpt-4", "Claude", "the AI", "ChatGPT"):

            with self.assertRaises(FactVerificationError):
                fact.verify(verified_by=actor)

    def test_verify_rejects_bare_ai_and_system(self):

        for actor in ("AI", "system", "bot", "automatic"):

            fact = Fact(name="insurer", value="SBI General")

            with self.assertRaises(FactVerificationError):
                fact.verify(verified_by=actor)

    def test_verify_accepts_legitimate_human_titles(self):
        """
        Guards against overly broad substring matching - a real
        institutional title should never be rejected merely because
        it contains a common English word also used as a block
        marker (e.g. "assistant").
        """

        for actor in ("Assistant Registrar", "System Administrator"):

            fact = Fact(name="insurer", value="SBI General")

            fact.verify(verified_by=actor)

            self.assertTrue(fact.verified)

    def test_high_confidence_does_not_imply_verified(self):

        fact = Fact(
            name="insurer", value="SBI General", confidence=0.99
        )

        self.assertFalse(fact.verified)


class FactManagerHistoryTests(unittest.TestCase):
    """
    Proves conflicting/historical facts are preserved rather than
    silently overwritten, while historical_facts keeps its existing
    single-slot shape for backward compatibility.
    """

    def test_historical_facts_keeps_single_slot_shape(self):

        session = SessionState(session_id="history-test-1")

        update_fact(session, Fact(name="insurer", value="SBI General"))
        update_fact(session, Fact(name="insurer", value="LIC"))

        historical = session.historical_facts["insurer"]

        self.assertEqual(historical.value, "SBI General")

    def test_fact_history_accumulates_every_superseded_value(self):

        session = SessionState(session_id="history-test-2")

        update_fact(session, Fact(name="insurer", value="SBI General"))
        update_fact(session, Fact(name="insurer", value="LIC"))
        update_fact(session, Fact(name="insurer", value="New India"))

        history = session.fact_history["insurer"]

        self.assertEqual(
            [f.value for f in history], ["SBI General", "LIC"]
        )

    def test_second_supersession_does_not_erase_the_first(self):
        """
        The specific bug this change fixes: previously a second
        conflicting value silently discarded the first superseded
        fact from historical_facts. fact_history must retain both.
        """

        session = SessionState(session_id="history-test-3")

        update_fact(session, Fact(name="insurer", value="A"))
        update_fact(session, Fact(name="insurer", value="B"))
        update_fact(session, Fact(name="insurer", value="C"))

        history_values = [
            f.value for f in session.fact_history["insurer"]
        ]

        self.assertIn("A", history_values)
        self.assertIn("B", history_values)

    def test_update_evidence_fact_also_populates_fact_history(self):

        session = SessionState(session_id="history-test-4")

        update_evidence_fact(
            session, {"name": "insurer", "value": "SBI General"}
        )
        update_evidence_fact(
            session, {"name": "insurer", "value": "LIC"}
        )

        self.assertEqual(
            len(session.fact_history["insurer"]), 1
        )


class SessionPersistenceRoundTripTests(unittest.TestCase):
    """
    Confirms fact_history survives save/load, using an isolated
    temp directory rather than the live session store.
    """

    def test_fact_history_round_trips_through_save_and_load(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            manager = SessionManager(storage_path=tmp_dir)

            session = manager.get_session("roundtrip-test")

            update_fact(session, Fact(name="insurer", value="A"))
            update_fact(session, Fact(name="insurer", value="B"))

            manager.save_session("roundtrip-test")

            reloaded_manager = SessionManager(storage_path=tmp_dir)

            reloaded = reloaded_manager.get_session("roundtrip-test")

            self.assertEqual(
                [f.value for f in reloaded.fact_history["insurer"]],
                ["A"],
            )


class EvidenceRecordCreationTests(unittest.TestCase):

    def test_evidence_record_has_generated_id_and_timestamp(self):

        record = EvidenceRecord(source_type="email")

        self.assertTrue(record.evidence_id)
        self.assertTrue(record.retrieved_at)

    def test_missing_source_type_is_rejected(self):

        with self.assertRaises(IntegrityValidationError):
            EvidenceRecord(source_type="")

    def test_excerpt_within_bound_is_accepted(self):

        record = EvidenceRecord(
            source_type="pdf", excerpt="x" * 5000
        )

        self.assertEqual(len(record.excerpt), 5000)

    def test_excerpt_beyond_bound_is_rejected(self):

        with self.assertRaises(IntegrityValidationError):
            EvidenceRecord(source_type="pdf", excerpt="x" * 10001)


class EvidenceSecurityGuardTests(unittest.TestCase):

    def test_credential_shaped_metadata_key_is_rejected(self):

        with self.assertRaises(IntegrityValidationError):
            EvidenceRecord(
                source_type="email",
                metadata={"api_key": "irrelevant-value"},
            )

    def test_credential_shaped_metadata_value_is_rejected(self):

        with self.assertRaises(IntegrityValidationError):
            EvidenceRecord(
                source_type="email",
                metadata={
                    "note": "gsk_someobviouslygroqshapedvalue1234"
                },
            )

    def test_credential_shaped_excerpt_is_rejected(self):

        with self.assertRaises(IntegrityValidationError):
            EvidenceRecord(
                source_type="email", excerpt="Bearer abc.def.ghi"
            )

    def test_ordinary_metadata_is_accepted(self):

        record = EvidenceRecord(
            source_type="pdf",
            metadata={"page_count": 3, "language": "en"},
        )

        self.assertEqual(record.metadata["page_count"], 3)


class InMemoryEvidenceStoreTests(unittest.TestCase):

    def setUp(self):
        self.store = InMemoryEvidenceStore()

    def test_add_and_get_round_trip(self):

        record = EvidenceRecord(source_type="email")

        self.store.add(record)

        self.assertEqual(
            self.store.get(record.evidence_id), record
        )

    def test_only_evidence_record_instances_may_be_added(self):

        with self.assertRaises(IntegrityValidationError):
            self.store.add({"not": "a record"})

    def test_query_filters_by_source_type(self):

        self.store.add(EvidenceRecord(source_type="email"))
        self.store.add(EvidenceRecord(source_type="pdf"))
        self.store.add(EvidenceRecord(source_type="email"))

        emails = self.store.query(source_type="email")

        self.assertEqual(len(emails), 2)

    def test_query_returns_records_in_recording_order(self):

        recorded = [
            EvidenceRecord(source_type="email") for _ in range(4)
        ]

        for record in recorded:
            self.store.add(record)

        results = self.store.query()

        self.assertEqual(
            [r.evidence_id for r in results],
            [r.evidence_id for r in recorded],
        )

    def test_resolve_multiple_known_ids(self):

        first = EvidenceRecord(source_type="email")
        second = EvidenceRecord(source_type="pdf")

        self.store.add(first)
        self.store.add(second)

        resolved = self.store.resolve(
            [first.evidence_id, second.evidence_id]
        )

        self.assertEqual(len(resolved), 2)

    def test_resolve_unknown_id_raises_provenance_error(self):

        with self.assertRaises(ProvenanceError):
            self.store.resolve(["does-not-exist"])


class EvidenceLedgerFacadeTests(unittest.TestCase):

    def test_record_then_resolve_for_fact(self):

        ledger = EvidenceLedger()

        evidence = ledger.record(
            source_type="email", source_reference="thread-123"
        )

        fact = Fact(
            name="insurer",
            value="SBI General",
            evidence_ids=[evidence.evidence_id],
        )

        supporting = ledger.resolve_for_fact(fact)

        self.assertEqual(len(supporting), 1)
        self.assertEqual(
            supporting[0].evidence_id, evidence.evidence_id
        )

    def test_resolve_for_fact_with_invalid_provenance_raises(self):

        ledger = EvidenceLedger()

        fact = Fact(
            name="insurer",
            value="SBI General",
            evidence_ids=["does-not-exist"],
        )

        with self.assertRaises(ProvenanceError):
            ledger.resolve_for_fact(fact)

    def test_default_store_is_in_memory(self):

        ledger = EvidenceLedger()

        self.assertIsInstance(ledger.store, InMemoryEvidenceStore)

    def test_custom_store_can_be_injected(self):

        custom_store = InMemoryEvidenceStore()

        ledger = EvidenceLedger(store=custom_store)

        ledger.record(source_type="email")

        self.assertIs(ledger.store, custom_store)
        self.assertEqual(len(custom_store.query()), 1)


class ArchitectureCleanupRegressionTests(unittest.TestCase):
    """
    Guards against the previously-rejected design (a parallel
    FactClaim/EvidenceFactLedger fact system) silently reappearing.
    """

    def test_factclaim_no_longer_exists(self):

        import uri_core.core.evidence_fact_integrity as module

        self.assertFalse(hasattr(module, "FactClaim"))
        self.assertFalse(hasattr(module, "AuditEvent"))


if __name__ == "__main__":
    unittest.main()
