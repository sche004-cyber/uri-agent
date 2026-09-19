import json
import os
import unittest

from uri_core.core.evidence_fact_integrity import EVIDENCE_STORE_FILENAME, EvidenceLedger, EvidenceRecord, FileEvidenceStore
from uri_core.external.evidence_adapter import complete_operation_feedback, make_legacy_evidence_projection, resolve_legacy_evidence_projection
from uri_core.external.operation_store import FileOperationStore, OperationRecord
from uri_core.external.result_normalizer import MAX_EVIDENCE_PROJECTION_LENGTH, normalize_evidence_result, project_evidence

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"
TEST_ROOT = os.path.join(os.getcwd(), ".tmp_m33_c2_pytest")


def _root(name):
    """Pre-provisioned workspace root; Windows sandbox blocks tempfile children."""
    return os.path.join(TEST_ROOT, name)


def _remove(path):
    if os.path.exists(path):
        os.remove(path)


class DurableEvidencePrimitiveTests(unittest.TestCase):
    def test_atomic_persistence_uses_replace_and_never_leaves_temp_file(self):
        root = _root("evidence_atomic")
        path = os.path.join(root, USER_A, EVIDENCE_STORE_FILENAME)
        _remove(path)
        FileEvidenceStore(user_id=USER_A, root=root).add(EvidenceRecord(source_type="fixture", excerpt="safe"))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(len(json.load(handle)["records"]), 1)
        self.assertFalse(any(name.startswith(".tmp-") for name in os.listdir(os.path.dirname(path))))

    def test_restart_readback_and_cross_user_isolation(self):
        root = _root("evidence_restart")
        for user_id in (USER_A, USER_B):
            _remove(os.path.join(root, user_id, EVIDENCE_STORE_FILENAME))
        record = EvidenceRecord(source_type="fixture", excerpt="A only")
        FileEvidenceStore(user_id=USER_A, root=root).add(record)
        restarted = FileEvidenceStore(user_id=USER_A, root=root)
        other = FileEvidenceStore(user_id=USER_B, root=root)
        self.assertEqual(restarted.resolve([record.evidence_id])[0].excerpt, "A only")
        self.assertIsNone(other.get(record.evidence_id))
        self.assertEqual(other.query(), [])

    def test_redaction_and_bounds_survive_storage(self):
        root = _root("evidence_redaction")
        path = os.path.join(root, USER_A, EVIDENCE_STORE_FILENAME)
        _remove(path)
        record = normalize_evidence_result(source_type="fixture", excerpt="x" * 12000 + " Authorization: Bearer abc.def.ghi and api_key=sk-secret-value", metadata={"api_key": "sk-secret-value", "nested": {"token": "abc123456"}})
        FileEvidenceStore(user_id=USER_A, root=root).add(record)
        restored = FileEvidenceStore(user_id=USER_A, root=root).get(record.evidence_id)
        projection = project_evidence(restored)
        self.assertEqual(len(restored.excerpt), 10000)
        self.assertTrue(restored.metadata["excerpt_truncated"])
        self.assertEqual(len(projection["content"]), MAX_EVIDENCE_PROJECTION_LENGTH)
        self.assertTrue(projection["truncated"])
        with open(path, encoding="utf-8") as handle:
            serialized = handle.read()
        self.assertNotIn("abc.def.ghi", serialized)
        self.assertNotIn("sk-secret-value", serialized)
        self.assertNotIn("api_key", restored.metadata)
        self.assertNotIn("token", restored.metadata["nested"])

    def test_corrupt_or_unknown_version_evidence_fails_closed(self):
        root = _root("evidence_corrupt")
        path = os.path.join(root, USER_A, EVIDENCE_STORE_FILENAME)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"schema_version": "unknown", "records": []}, handle)
        with self.assertRaises(Exception):
            FileEvidenceStore(user_id=USER_A, root=root)


class DurableOperationPrimitiveTests(unittest.TestCase):
    def test_restart_idempotency_and_one_time_completion_claim(self):
        root = _root("operation_restart")
        path = os.path.join(root, USER_A, "operations.json")
        _remove(path)
        operation = FileOperationStore(user_id=USER_A, root=root).create(OperationRecord(capability_id="fixture", action="run", scope={"read": True}, version="1", budget={"steps": 1}, session_id="s1"))
        restarted = FileOperationStore(user_id=USER_A, root=root)
        self.assertEqual(restarted.get(operation.operation_id).status, "pending")
        restarted.mark_outcome_unknown(operation.operation_id)
        completed = restarted.complete(operation.operation_id, {"status": "success"})
        self.assertIs(completed, restarted.complete(operation.operation_id, {"status": "different"}))
        self.assertIsNotNone(restarted.claim_completion(operation.operation_id))
        self.assertIsNone(FileOperationStore(user_id=USER_A, root=root).claim_completion(operation.operation_id))

    def test_rehydrated_pending_work_is_visible_but_never_resubmitted(self):
        root = _root("operation_pending")
        _remove(os.path.join(root, USER_A, "operations.json"))
        operation = FileOperationStore(user_id=USER_A, root=root).create(OperationRecord(capability_id="fixture", action="run", upstream_job_id="job-7"))
        restarted = FileOperationStore(user_id=USER_A, root=root)
        self.assertEqual([item.operation_id for item in restarted.recovered_pending()], [operation.operation_id])
        self.assertEqual(restarted.get(operation.operation_id).status, "pending")

    def test_corrupt_operation_fails_closed_and_users_are_isolated(self):
        root = _root("operation_corrupt")
        path = os.path.join(root, USER_A, "operations.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"schema_version": "unknown", "operations": []}, handle)
        with self.assertRaises(Exception):
            FileOperationStore(user_id=USER_A, root=root)
        root = _root("operation_isolation")
        for user_id in (USER_A, USER_B):
            _remove(os.path.join(root, user_id, "operations.json"))
        operation = FileOperationStore(user_id=USER_A, root=root).create(OperationRecord(capability_id="fixture", action="run"))
        other = FileOperationStore(user_id=USER_B, root=root)
        self.assertIsNone(other.get(operation.operation_id))
        self.assertEqual(other.list_all(), [])


class ProductionCompositionTests(unittest.TestCase):
    def setUp(self):
        from uri_core.app import server
        self.server = server
        self.root = _root("composition")
        self.old_root = server._USER_STATE_ROOT
        server._USER_STATE_ROOT = self.root
        server._user_contexts.clear()

    def tearDown(self):
        self.server._user_contexts.clear()
        self.server._USER_STATE_ROOT = self.old_root
        for user_id in (USER_A, USER_B):
            _remove(os.path.join(self.root, user_id, EVIDENCE_STORE_FILENAME))
            _remove(os.path.join(self.root, user_id, "operations.json"))

    def test_authenticated_context_rehydrates_durable_stores_without_legacy_cutover(self):
        first = self.server._build_user_context(USER_A)
        record = normalize_evidence_result(source_type="fixture", excerpt="x" * 12000, metadata={"token": "secret-value"})
        first.evidence_ledger.store.add(record)
        operation = first.operation_store.create(OperationRecord(capability_id="fixture", action="run", session_id="s1"))
        restarted = self.server._build_user_context(USER_A)
        other = self.server._build_user_context(USER_B)
        restored = restarted.evidence_ledger.get(record.evidence_id)
        self.assertEqual(len(restored.excerpt), 10000)
        self.assertTrue(restored.metadata["excerpt_truncated"])
        self.assertNotIn("secret-value", str(restored.to_dict()))
        self.assertEqual(restarted.operation_store.get(operation.operation_id).status, "pending")
        self.assertIsNone(other.evidence_ledger.get(record.evidence_id))
        self.assertIsNone(other.operation_store.get(operation.operation_id))

    def test_context_completion_callback_enqueues_one_brain_visible_projection(self):
        context = self.server._build_user_context(USER_A)
        operation = context.operation_store.create(
            OperationRecord(capability_id="fixture", action="run")
        )
        projection = context.complete_operation_feedback(
            operation.operation_id, {"excerpt": "completed"}
        )
        first = context.orchestrator._resolve_step_decision_context(
            capability_id="draft_institutional_note",
            step={"depends_on": []}, workflow={"steps": []},
        )
        second = context.orchestrator._resolve_step_decision_context(
            capability_id="draft_institutional_note",
            step={"depends_on": []}, workflow={"steps": []},
        )
        self.assertIsNotNone(projection)
        self.assertEqual(len(first["verified_evidence"]["retrieved_evidence"]), 1)
        self.assertEqual(second, {})


class EvidenceAuthorityCutoverTests(unittest.TestCase):
    def test_orchestrator_projects_from_ledger_once_for_repeated_dependents(self):
        from uri_core.core.orchestrator import UriOrchestrator

        root = _root("c3_orchestrator")
        _remove(os.path.join(root, USER_A, EVIDENCE_STORE_FILENAME))
        ledger = EvidenceLedger(store=FileEvidenceStore(user_id=USER_A, root=root))
        orchestrator = object.__new__(UriOrchestrator)
        orchestrator.evidence_ledger = ledger
        workflow = {"steps": [
            {"step_id": "source", "status": "completed", "capability": "web_search", "output": {"status": "success", "results": [{"title": "Source", "url": "https://example.test", "content": "x" * 12000}]}},
        ]}
        dependent = {"depends_on": ["source"]}
        first = orchestrator._resolve_step_decision_context(
            capability_id="draft_institutional_note", step=dependent, workflow=workflow
        )
        second = orchestrator._resolve_step_decision_context(
            capability_id="draft_institutional_note", step=dependent, workflow=workflow
        )
        self.assertEqual(len(ledger.store.query()), 1)
        self.assertEqual(first["verified_evidence"]["retrieved_evidence"], second["verified_evidence"]["retrieved_evidence"])
        item = first["verified_evidence"]["retrieved_evidence"][0]
        evidence_id = item["metadata"]["evidence_id"]
        self.assertEqual(len(item["content"]), 4000)
        self.assertIn("truncation_disclosure", item["metadata"])
        self.assertEqual(ledger.get(evidence_id).evidence_id, evidence_id)
        other = EvidenceLedger(store=FileEvidenceStore(user_id=USER_B, root=root))
        with self.assertRaises(ValueError):
            resolve_legacy_evidence_projection(
                ledger=other, item=item, max_content_chars=4000
            )

    def test_legacy_view_is_a_single_ledger_write_and_preserves_its_shape(self):
        root = _root("c3_adapter")
        path = os.path.join(root, USER_A, EVIDENCE_STORE_FILENAME)
        _remove(path)
        ledger = EvidenceLedger(store=FileEvidenceStore(user_id=USER_A, root=root))
        item = make_legacy_evidence_projection(
            source_type="fixture", source_id="source-1", title="A title",
            content="x" * 12000, metadata={"token": "secret-value"},
            max_content_chars=4000, ledger=ledger,
        )
        self.assertEqual(len(ledger.store.query()), 1)
        self.assertEqual(item["source_id"], "source-1")
        self.assertEqual(item["title"], "A title")
        self.assertEqual(len(item["content"]), 4000)
        self.assertTrue(item["truncated"])
        self.assertIn("truncation_disclosure", item["metadata"])
        self.assertNotIn("secret-value", str(ledger.store.query()[0].to_dict()))

    def test_duplicate_completion_creates_one_authoritative_record_across_restart(self):
        root = _root("c3_completion")
        for name in (EVIDENCE_STORE_FILENAME, "operations.json"):
            _remove(os.path.join(root, USER_A, name))
        ledger = EvidenceLedger(store=FileEvidenceStore(user_id=USER_A, root=root))
        operations = FileOperationStore(user_id=USER_A, root=root)
        operation = operations.create(OperationRecord(capability_id="fixture", action="run"))
        first = complete_operation_feedback(
            operation_store=operations, ledger=ledger, operation_id=operation.operation_id,
            completion={"excerpt": "Authorization: Bearer abc.def.ghi"},
        )
        restarted_ledger = EvidenceLedger(store=FileEvidenceStore(user_id=USER_A, root=root))
        restarted_operations = FileOperationStore(user_id=USER_A, root=root)
        replay = complete_operation_feedback(
            operation_store=restarted_operations, ledger=restarted_ledger,
            operation_id=operation.operation_id, completion={"excerpt": "different"},
        )
        self.assertIsNotNone(first)
        self.assertIsNone(replay)
        self.assertEqual(len(restarted_ledger.store.query()), 1)
        self.assertNotIn("abc.def.ghi", str(restarted_ledger.store.query()[0].to_dict()))

    def test_claimed_completion_is_brain_visible_once_without_resubmission(self):
        from uri_core.core.orchestrator import UriOrchestrator

        root = _root("c3_brain_feedback")
        for name in (EVIDENCE_STORE_FILENAME, "operations.json"):
            _remove(os.path.join(root, USER_A, name))
        ledger = EvidenceLedger(store=FileEvidenceStore(user_id=USER_A, root=root))
        operations = FileOperationStore(user_id=USER_A, root=root)
        operation = operations.create(OperationRecord(capability_id="fixture", action="run"))
        projection = complete_operation_feedback(
            operation_store=operations, ledger=ledger,
            operation_id=operation.operation_id, completion={"excerpt": "completed"},
        )
        orchestrator = object.__new__(UriOrchestrator)
        orchestrator.evidence_ledger = ledger
        orchestrator.pending_completion_evidence = [projection]
        first = orchestrator._resolve_step_decision_context(
            capability_id="draft_institutional_note", step={"depends_on": []}, workflow={"steps": []}
        )
        second = orchestrator._resolve_step_decision_context(
            capability_id="draft_institutional_note", step={"depends_on": []}, workflow={"steps": []}
        )
        self.assertEqual(len(first["verified_evidence"]["retrieved_evidence"]), 1)
        self.assertEqual(first["verified_evidence"]["retrieved_evidence"][0]["metadata"]["evidence_id"], operation.completion_evidence_id)
        self.assertEqual(second, {})
        self.assertEqual(len(ledger.store.query()), 1)
        self.assertEqual(operations.get(operation.operation_id).status, "completed")


if __name__ == "__main__":
    unittest.main()
