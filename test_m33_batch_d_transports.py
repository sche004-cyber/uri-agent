"""Frozen M33 Batch D: offline transport and remember_fact pilot proof."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.core.canonical_execution import _execute_canonical
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.core.user_memory import MemoryStore
from uri_core.external.adapters.in_process import remember_fact_capability
from uri_core.external.fixture_profiles import cli_profile, http_profile, in_process_profile
from uri_core.external.registry_bridge import ExternalCapabilityPublisher
from uri_core.external.store import ExternalCapabilityStore
from uri_core.external.operation_store import FileOperationStore, OperationRecord
from uri_core.external.evidence_adapter import complete_operation_feedback
from uri_core.core.evidence_fact_integrity import EvidenceLedger, FileEvidenceStore


def _enabled(root, user_id, descriptor):
    store = ExternalCapabilityStore(root=root)
    registered = store.register_descriptor(descriptor, user_id=user_id, source_revision="batch-d")
    assert registered.ok, registered.reasons
    store.configure(user_id, descriptor["id"])
    store.authenticate(user_id, descriptor["id"])
    store.enable(user_id, descriptor["id"])
    return store


class _Orchestrator:
    def __init__(self, dispatch): self.multi_action_dispatch = dispatch


class TransportProfilesTests(unittest.TestCase):
    def setUp(self):
        self.user_id = str(uuid.uuid4())
        # Windows TEMP ACLs are not reliable in the test sandbox.  This
        # pre-provisioned, ignored workspace root is the established durable
        # store test strategy; no test deletes it.
        self.root = os.path.join("temp_evidence", "m33_batch_d", self.user_id)
        os.makedirs(self.root, exist_ok=True)

    def _dispatch(self, descriptor):
        store = _enabled(self.root, self.user_id, descriptor)
        registry = ExternalCapabilityPublisher(store=store).publish(self.user_id).registry
        return MultiActionDispatch(registry=registry, external_permission_resolver=lambda *_: True)

    def _execute(self, descriptor):
        dispatch = self._dispatch(descriptor)
        return dispatch.dispatch_explicit(descriptor["id"], "lookup", {"query": "alpha"},
                                          session_id="s", user_text="find alpha", principal=SimpleNamespace(user_id=self.user_id))

    def test_in_process_profile_executes_through_registry(self):
        result = self._execute(in_process_profile())
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["response"]["result"]["evidence"], "in-process fixture")

    def test_cli_profile_executes_json_fixture_without_shell(self):
        profile = cli_profile([sys.executable, "-c", "import json,sys; print(json.dumps({'echo': json.load(sys.stdin)['query']}))"])
        result = self._execute(profile)
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["response"]["result"]["echo"], "alpha")

    def test_http_profile_executes_loopback_fixture(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"]); value = json.loads(self.rfile.read(length))
                body = json.dumps({"echo": value["query"]}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        result = self._execute(http_profile(f"http://127.0.0.1:{server.server_port}/fixture"))
        self.assertEqual(result["execution"]["status"], "success")
        self.assertEqual(result["response"]["result"]["echo"], "alpha")

    def test_profile_and_durable_completion_are_user_scoped_and_replay_safe(self):
        profile = in_process_profile()
        result = self._execute(profile)
        other = str(uuid.uuid4())
        self.assertIsNone(ExternalCapabilityStore(root=self.root).get(other, profile["id"]))
        operations = FileOperationStore(user_id=self.user_id, root=self.root)
        operation = operations.create(OperationRecord(capability_id=profile["id"], action="lookup"))
        ledger = EvidenceLedger(store=FileEvidenceStore(user_id=self.user_id, root=self.root))
        completion = {"excerpt": json.dumps(result["response"])}
        first = complete_operation_feedback(operation_store=operations, ledger=ledger,
                                            operation_id=operation.operation_id, completion=completion)
        restarted_ops = FileOperationStore(user_id=self.user_id, root=self.root)
        restarted_ledger = EvidenceLedger(store=FileEvidenceStore(user_id=self.user_id, root=self.root))
        replay = complete_operation_feedback(operation_store=restarted_ops, ledger=restarted_ledger,
                                             operation_id=operation.operation_id, completion={"excerpt": "replay"})
        self.assertIsNotNone(first)
        self.assertIsNone(replay)
        self.assertEqual(len(restarted_ledger.store.query()), 1)
        self.assertEqual(FileOperationStore(user_id=other, root=self.root).list_all(), [])

    def test_transport_profile_reaches_canonical_execution_and_brain_envelope(self):
        descriptor = in_process_profile()
        dispatch = self._dispatch(descriptor)
        envelope = _execute_canonical(
            {"capability": descriptor["id"], "actions": [{"name": "lookup", "inputs": {"query": "canonical"}}]},
            orchestrator=_Orchestrator(dispatch), session_id="canonical-session",
            user_text="find canonical", principal=SimpleNamespace(user_id=self.user_id),
        )
        self.assertEqual(envelope["execution"]["status"], "success")
        self.assertEqual(envelope["response"]["result"]["evidence"], "in-process fixture")
        other_user = str(uuid.uuid4())
        other_dispatch = MultiActionDispatch(
            registry=dispatch.registry,
            external_permission_resolver=lambda capability, principal: getattr(principal, "user_id", None) == self.user_id,
        )
        denied = other_dispatch.dispatch_explicit(
            descriptor["id"], "lookup", {"query": "cross-user"}, session_id="other",
            user_text="cross-user", principal=SimpleNamespace(user_id=other_user),
        )
        self.assertEqual(denied["execution"]["status"], "permission_denied")


class RememberFactPilotTests(unittest.TestCase):
    def test_descriptor_path_preserves_envelope_consent_and_approval_gate(self):
        from uri_core.core.capability_registry import CapabilityRegistry
        descriptor = CapabilityRegistry().describe_status("remember_fact")
        principal = SimpleNamespace(user_id=str(uuid.uuid4()))
        root = os.path.join("temp_evidence", "m33_batch_d", str(uuid.uuid4()))
        os.makedirs(root, exist_ok=True)
        with patch(
            "uri_core.tools.remember_fact.RememberFactTool._resolve_store",
            return_value=MemoryStore(storage_path=f"{root}/memory.json"),
        ):
            capability = remember_fact_capability(descriptor, principal=principal)
            dispatch = MultiActionDispatch(registry=MultiActionCapabilityRegistry([capability]), permission_checker=lambda *_: True)
            envelope = _execute_canonical(
                {"capability": "remember_fact", "actions": [{"name": "remember_fact", "inputs": {}}]},
                orchestrator=_Orchestrator(dispatch), session_id="s", user_text="remember that I work at NIT Sikkim", principal=principal,
            )
            self.assertEqual(envelope["plan"]["capability"], "remember_fact")
            self.assertEqual(envelope["plan"]["action"], "remember_fact")
            self.assertEqual(envelope["execution"]["raw_status"], "success")
            self.assertIn("NIT Sikkim", envelope["response"]["content"])
            capability.get_action("remember_fact").approval_requirement = __import__("uri_core.capabilities.base", fromlist=["ApprovalRequirement"]).ApprovalRequirement.USER_APPROVAL_REQUIRED
            denied = dispatch.dispatch_explicit("remember_fact", "remember_fact", {"request_text": "remember this too"}, session_id="s2", user_text="remember this too", principal=principal)
            self.assertEqual(denied["execution"]["status"], "awaiting_approval")
