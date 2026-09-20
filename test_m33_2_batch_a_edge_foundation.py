"""Batch A contracts/settings/policy skeleton acceptance coverage."""
import ast
import pathlib
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import patch

from uri_core.core.edge.contracts import EdgeAssistanceRequest, EdgeRequest, NullEdgeProvider
from uri_core.core.edge.routing_policy import (
    IntelligenceRoutingDecision, RoutingInput, evaluate_routing,
)
from uri_core.core.edge.runtime_inventory import EdgeRuntimeInventory, RuntimeProfile
from uri_core.core.edge.settings import (
    EdgeSettingsConflictError, EdgeSettingsStore, EdgeSettingsValidationError,
)
from uri_core.core.edge.trace import EdgeRoutingTraceEvent, EdgeRoutingTraceStore
from uri_core.core.principal_context import PrincipalContext

USER_A = "11111111-1111-4111-8111-111111111111"
USER_B = "22222222-2222-4222-8222-222222222222"
INVENTORY = EdgeRuntimeInventory(runtimes={"test-runtime": RuntimeProfile("test-runtime", frozenset({"test-model"}))})


class EdgeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = EdgeSettingsStore(USER_A, root=self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_schema_threshold_and_mode_validation(self):
        for value in (-1, 101, True, 1.2):
            with self.assertRaises(EdgeSettingsValidationError):
                self.store.update({"reply_confidence_threshold_percent": value}, expected_revision=0, inventory=INVENTORY)
        for mode in ("admin", "tier1", "INVALID"):
            with self.assertRaises(EdgeSettingsValidationError):
                self.store.update({"intelligence_mode": mode}, expected_revision=0, inventory=INVENTORY)
        with self.assertRaises(EdgeSettingsValidationError):
            self.store.update({"schema_version": "99.0"}, expected_revision=0, inventory=INVENTORY)

    def test_revision_conflict_and_runtime_validation(self):
        saved = self.store.update({"edge": {"runtime_id": "test-runtime", "model_id": "test-model"}}, expected_revision=0, inventory=INVENTORY)
        self.assertEqual(saved.revision, 1)
        with self.assertRaises(EdgeSettingsConflictError):
            self.store.update({"enabled": False}, expected_revision=0, inventory=INVENTORY)
        with self.assertRaises(ValueError):
            self.store.update({"edge": {"runtime_id": "unknown", "model_id": "x"}}, expected_revision=1, inventory=INVENTORY)

    def test_policy_disabled_runtime_selection_is_rejected_at_write_time(self):
        disabled_runtime = EdgeRuntimeInventory(
            runtimes={"test-runtime": RuntimeProfile("test-runtime", frozenset({"test-model"}), enabled=False)}
        )
        with self.assertRaises(ValueError):
            self.store.update(
                {"edge": {"runtime_id": "test-runtime", "model_id": "test-model"}},
                expected_revision=0,
                inventory=disabled_runtime,
            )

    def test_caller_isolation(self):
        other = EdgeSettingsStore(USER_B, root=self.temp.name)
        self.store.update({"enabled": False}, expected_revision=0, inventory=INVENTORY)
        self.assertFalse(self.store.load().enabled)
        self.assertTrue(other.load().enabled)

    def test_deployment_policy_cannot_be_overridden(self):
        saved = self.store.update({"edge": {"runtime_id": "test-runtime", "model_id": "test-model"}}, expected_revision=0, inventory=INVENTORY)
        disabled = EdgeRuntimeInventory(enabled=False, runtimes=INVENTORY.runtimes)
        result = evaluate_routing(saved, disabled, RoutingInput(resource_admitted=True, proposal_valid=True))
        self.assertEqual(result.decision, IntelligenceRoutingDecision.SUPPRESS)
        self.assertIn("disabled_by_policy", result.reason_codes)


class EdgePolicyAndProviderTests(unittest.TestCase):
    def test_threshold_and_preflight_decisions(self):
        settings = EdgeSettingsStore(USER_A, root=tempfile.mkdtemp()).load()
        settings = replace(settings, edge={"runtime_id": "test-runtime", "model_id": "test-model"})
        low = evaluate_routing(settings, INVENTORY, RoutingInput(resource_admitted=True, reply_valid=True, calibration_current=True, calibrated_confidence=.8949))
        high = evaluate_routing(settings, INVENTORY, RoutingInput(resource_admitted=True, reply_valid=True, calibration_current=True, calibrated_confidence=.8951))
        self.assertEqual(low.decision, IntelligenceRoutingDecision.ESCALATE)
        self.assertEqual(high.decision, IntelligenceRoutingDecision.EDGE_REPLY)
        self.assertEqual(evaluate_routing(settings, INVENTORY, RoutingInput(uri_preflight_available=True)).decision, IntelligenceRoutingDecision.SUPPRESS)

    def test_null_provider_and_assistance_contract_are_truthful(self):
        provider = NullEdgeProvider()
        self.assertEqual(provider.health().status, "unavailable")
        result = provider.prepare_context(EdgeAssistanceRequest("context_prep", 10, EdgeRequest("context_prep")))
        self.assertEqual(result.status, "skipped")
        with self.assertRaises(ValueError):
            EdgeAssistanceRequest("unknown", 1, EdgeRequest("x"))
        self.assertFalse(hasattr(provider, "update_settings"))


class TraceAndBoundaryTests(unittest.TestCase):
    def setUp(self): self.temp = tempfile.TemporaryDirectory()
    def tearDown(self): self.temp.cleanup()

    def test_trace_redaction_isolation_and_failure_is_best_effort(self):
        store = EdgeRoutingTraceStore(USER_A, root=self.temp.name)
        event = EdgeRoutingTraceEvent(datetime.now(timezone.utc).isoformat(), "SUPPRESS", "URI_PREFLIGHT", reason_codes=("safe",))
        self.assertTrue(store.record(event))
        self.assertEqual(len(store.list_events()), 1)
        self.assertEqual(EdgeRoutingTraceStore(USER_B, root=self.temp.name).list_events(), [])
        self.assertNotIn("user_text", store.latest())
        self.assertIn("resource", store.latest())
        with patch("uri_core.core.edge.trace._locked_append", side_effect=OSError("boom")):
            self.assertFalse(store.record(event))

    def test_edge_has_no_static_authority_or_execution_imports(self):
        forbidden = ("approval", "dispatcher", "credential", "provider_keys", "capability_registry", "canonical_execution", "orchestrator", "graphify")
        root = pathlib.Path(__file__).parent / "uri_core" / "core" / "edge"
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module: imports.append(node.module)
            self.assertEqual([], [name for name in imports if any(word in name for word in forbidden)], path.name)

    def test_runtime_dynamic_import_residue_is_absent(self):
        root = pathlib.Path(__file__).parent / "uri_core" / "core" / "edge"
        source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
        self.assertNotIn("importlib", source)
        self.assertNotIn("__import__", source)

    def test_authority_modules_do_not_read_edge_preference(self):
        root = pathlib.Path(__file__).parent / "uri_core" / "core"
        for name in ("approval_gate.py", "approval_store.py", "dispatcher.py", "capability_resolver.py", "canonical_execution.py"):
            source = (root / name).read_text(encoding="utf-8")
            self.assertNotIn("edge.settings", source, name)
            self.assertNotIn("intelligence_mode", source, name)


class IntelligenceEndpointContractTests(unittest.TestCase):
    def test_authenticated_caller_scoped_settings_endpoint_contract(self):
        # Direct handler invocation keeps this focused on endpoint ownership,
        # avoiding unrelated account/session setup in the broad server suite.
        from fastapi import HTTPException
        from uri_core.app import server
        with tempfile.TemporaryDirectory() as root:
            factory = lambda user_id: EdgeSettingsStore(user_id, root=root)
            with patch.object(server, "EdgeSettingsStore", side_effect=factory):
                a = PrincipalContext(user_id=USER_A, role="USER", device_id=None, mode="office")
                b = PrincipalContext(user_id=USER_B, role="USER", device_id=None, mode="office")
                first = server.get_intelligence_settings(a)
                self.assertEqual(first["settings"]["revision"], 0)
                saved = server.update_intelligence_settings(
                    server.IntelligenceSettingsPayload(revision=0, enabled=False), a
                )
                self.assertEqual(saved["settings"]["revision"], 1)
                self.assertTrue(server.get_intelligence_settings(b)["settings"]["enabled"])
                with self.assertRaises(HTTPException) as denied:
                    server.get_intelligence_settings(PrincipalContext(user_id=None, role=None, device_id=None, mode="office"))
                self.assertEqual(denied.exception.status_code, 401)
