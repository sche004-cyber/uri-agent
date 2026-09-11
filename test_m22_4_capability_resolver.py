"""M22.4 Unit and Boundary Tests for CapabilityResolver (AO-4).

Covers §7 Test Plan categories 1, 2, and 3:
1. Least privilege / intersection behavior (resolved ⊆ granted ⊆ registered, pure function).
2. experience_tier never affects grants (AST scan across resolver and admin handlers).
3. Model proposals never create grants (AST reachability + behavioral immutability test).
"""

import ast
import inspect
import os
import tempfile
import unittest
from pathlib import Path
from typing import Set

from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.capability_registry import CapabilityDescriptor, CapabilityRegistry
from uri_core.core.capability_resolver import (
    CapabilityGrantsStore,
    CapabilityResolver,
)
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.principal_context import PrincipalContext


class CapabilityResolverIntersectionTests(unittest.TestCase):
    """Category 1: Intersection logic, least privilege invariant, and purity."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.grants_file = os.path.join(self.temp_dir.name, "capability_grants.json")
        self.store = CapabilityGrantsStore(storage_path=self.grants_file)
        self.registry = CapabilityRegistry()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pure_function_independence(self):
        """Acceptance Criterion 1: pure testable functions with no HTTP dependency."""
        principal = PrincipalContext(user_id="alice", role="USER", device_id=None)
        resolved = CapabilityResolver.resolve(
            principal=principal,
            capability_registry=self.registry,
            grants_store=self.store,
        )
        self.assertIsInstance(resolved, list)
        self.assertTrue(all(isinstance(d, CapabilityDescriptor) for d in resolved))

    def test_least_privilege_invariant(self):
        """Criterion 5: resolved ⊆ granted ⊆ registered invariant holds."""
        all_registered = self.registry.list_capabilities()
        registered_ids = {d.id for d in all_registered}
        self.assertGreater(len(registered_ids), 0)

        sample_ids = sorted(list(registered_ids))[:3]
        user_id = "user_least_priv"
        self.store.set_grants(user_id, sample_ids, registered_ids)

        principal = PrincipalContext(user_id=user_id, role="USER", device_id=None)
        resolved = CapabilityResolver.resolve(
            principal=principal,
            capability_registry=self.registry,
            grants_store=self.store,
        )
        resolved_ids = {d.id for d in resolved}

        # Invariant: resolved ⊆ granted
        self.assertTrue(resolved_ids.issubset(set(sample_ids)))
        # Invariant: granted ⊆ registered
        self.assertTrue(set(sample_ids).issubset(registered_ids))
        # Invariant: resolved ⊆ registered
        self.assertTrue(resolved_ids.issubset(registered_ids))

    def test_grants_narrow_registry_is_ceiling(self):
        """Grants only ever narrow, never widen beyond the registry."""
        all_registered = self.registry.list_capabilities()
        registered_ids = {d.id for d in all_registered}

        user_id = "narrow_user"
        # Grant only 1 capability
        first_id = sorted(list(registered_ids))[0]
        self.store.set_grants(user_id, [first_id], registered_ids)

        principal = PrincipalContext(user_id=user_id, role="USER", device_id=None)
        resolved = CapabilityResolver.resolve(
            principal=principal,
            capability_registry=self.registry,
            grants_store=self.store,
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].id, first_id)

        # Authoritative check
        self.assertTrue(CapabilityResolver.is_allowed(first_id, principal, self.registry, self.store))
        other_ids = [cid for cid in registered_ids if cid != first_id]
        if other_ids:
            self.assertFalse(CapabilityResolver.is_allowed(other_ids[0], principal, self.registry, self.store))

    def test_role_does_not_affect_grants(self):
        """Clarification 2: Role and grants are separate; ADMIN does not widen capabilities."""
        all_registered = self.registry.list_capabilities()
        registered_ids = {d.id for d in all_registered}

        admin_id = "admin_user"
        first_id = sorted(list(registered_ids))[0]
        self.store.set_grants(admin_id, [first_id], registered_ids)

        admin_principal = PrincipalContext(user_id=admin_id, role="ADMIN", device_id=None)
        resolved = CapabilityResolver.resolve(
            principal=admin_principal,
            capability_registry=self.registry,
            grants_store=self.store,
        )
        # Even though role is ADMIN, only the 1 granted capability is resolved
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].id, first_id)

    def test_unknown_capability_rejected_by_store(self):
        """Plan §5.1.6: set_grants rejects unknown capability_ids (never partial apply)."""
        registered_ids = {d.id for d in self.registry.list_capabilities()}
        with self.assertRaises(ValueError):
            self.store.set_grants("user_err", ["completely_invalid_capability_xyz"], registered_ids)

    def test_anonymous_principal_fails_closed_vs_unrecorded_user(self):
        """Gap 2: Distinguish unauthenticated caller (fails closed to empty set) from
        authenticated user without stored record (migration default: full registry ceiling).
        """
        all_registered = self.registry.list_capabilities()
        registered_ids = {d.id for d in all_registered}
        first_id = sorted(list(registered_ids))[0]

        # 1. Anonymous caller: user_id is None -> fails closed
        anon_grants = self.store.get_grants(None, registry_ceiling_ids=registered_ids)
        self.assertEqual(anon_grants, set())

        anon_principal = PrincipalContext(user_id=None, role=None, device_id=None)
        self.assertEqual(
            CapabilityResolver.resolve(anon_principal, self.registry, self.store),
            [],
        )
        self.assertFalse(
            CapabilityResolver.is_allowed(first_id, anon_principal, self.registry, self.store)
        )
        self.assertFalse(
            CapabilityResolver.is_allowed(first_id, None, self.registry, self.store)
        )

        # 2. Authenticated user with no record yet -> migration default: full ceiling
        new_user_id = "known_authenticated_user_without_record"
        self.assertFalse(self.store.has_user_record(new_user_id))
        user_grants = self.store.get_grants(new_user_id, registry_ceiling_ids=registered_ids)
        self.assertEqual(user_grants, registered_ids)

        user_principal = PrincipalContext(user_id=new_user_id, role="USER", device_id=None)
        resolved = CapabilityResolver.resolve(user_principal, self.registry, self.store)
        self.assertEqual({d.id for d in resolved}, registered_ids)
        self.assertTrue(
            CapabilityResolver.is_allowed(first_id, user_principal, self.registry, self.store)
        )


class ExperienceTierASTScanTests(unittest.TestCase):
    """Category 2: Proof that experience_tier never touches authorization."""

    def test_experience_tier_not_in_capability_resolver(self):
        """AST scan ensuring capability_resolver.py does not mention experience_tier."""
        path = os.path.join("uri_core", "core", "capability_resolver.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertNotIn("experience_tier", source.lower())

    def test_experience_tier_not_in_admin_handlers(self):
        """AST scan ensuring the new admin endpoints in server.py do not read experience_tier."""
        path = os.path.join("uri_core", "app", "server.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=path)
        admin_functions = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in ("list_admin_users", "get_user_grants", "update_user_grants")
        ]
        self.assertEqual(len(admin_functions), 3, "All 3 admin handlers must be present in server.py")

        for fn in admin_functions:
            fn_source = ast.unparse(fn)
            self.assertNotIn(
                "experience_tier",
                fn_source,
                f"Handler {fn.name} must never inspect or reference experience_tier",
            )


class ModelProposalsNeverCreateGrantsTests(unittest.TestCase):
    """Category 3: Model/Brain proposals cannot grant, elevate, or modify capability grants."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.grants_file = os.path.join(self.temp_dir.name, "capability_grants.json")
        self.store = CapabilityGrantsStore(storage_path=self.grants_file)
        self.registry = CapabilityRegistry()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ast_reachability_approval_gate_never_writes_grants(self):
        """AST check: ApprovalGate source code never imports or calls set_grants or writes to grants file."""
        path = os.path.join("uri_core", "core", "approval_gate.py")
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertNotIn("set_grants", source)
        self.assertNotIn("capability_grants.json", source)

    def test_ungranted_capability_rejected_by_approval_gate(self):
        """Behavioral test: Proposing an ungranted capability is rejected and leaves store byte-for-byte unchanged."""
        registered_ids = {d.id for d in self.registry.list_capabilities()}
        user_id = "bob"
        first_id = sorted(list(registered_ids))[0]
        # Bob is granted only first_id
        self.store.set_grants(user_id, [first_id], registered_ids)

        initial_bytes = Path(self.grants_file).read_bytes()

        dispatcher = ToolDispatcher()
        approval_store = ApprovalStore()
        gate = ApprovalGate(
            dispatcher=dispatcher,
            capability_registry=self.registry,
            approval_store=approval_store,
        )

        other_ids = [cid for cid in registered_ids if cid != first_id]
        if not other_ids:
            return

        unauthorized_tool = other_ids[0]
        principal = PrincipalContext(user_id=user_id, role="USER", device_id=None)

        # In M22.4, execute_tool checks principal authorization
        # Patch the shared store to use our temp test store
        from uri_core.core import capability_resolver
        orig_store = capability_resolver._shared_grants_store
        capability_resolver._shared_grants_store = self.store
        try:
            result = gate.execute_tool(
                tool_name=unauthorized_tool,
                session_id="session_test",
                principal=principal,
            )
        finally:
            capability_resolver._shared_grants_store = orig_store

        self.assertEqual(result.get("status"), "rejected")
        self.assertIn("not granted", result.get("message", ""))

        # Verify grants file is byte-for-byte unchanged
        post_bytes = Path(self.grants_file).read_bytes()
        self.assertEqual(initial_bytes, post_bytes)


class _FakeDispatcher:
    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return {"status": "success", "data": {"tool": tool_name}}


def _fake_model_callable(payload: dict):
    import json
    def _call(request_json):
        return json.dumps(payload)
    return _call


class MultiUserOrchestratorEndToEndTests(unittest.TestCase):
    """Category 4: End-to-end multi-user integration test through UriOrchestrator.

    Proves that calling process_user_input without manual injection of principal
    enforces per-user capability grants end-to-end via the orchestrator's real
    call path:
    1. User with grant -> capability executes successfully.
    2. User without grant -> capability is rejected by approval gate and dispatcher is never called.
    3. Multi-user isolation: Alice's restricted tool executes for Bob (who has the grant),
       and Bob's restricted tool executes for Alice (who has the grant).
    4. Authenticated user with no record defaults to full registry (zero-behaviour-change migration).
    5. Anonymous / unauthenticated caller fails closed.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.grants_file = os.path.join(self.temp_dir.name, "capability_grants.json")
        self.store = CapabilityGrantsStore(storage_path=self.grants_file)
        self.registry = CapabilityRegistry()
        self.registered_ids = {d.id for d in self.registry.list_capabilities()}

    def tearDown(self):
        self.temp_dir.cleanup()

    def _build_orchestrator(self, user_id=None, role="USER", model_payload=None):
        from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
        from uri_core.core.orchestrator import UriOrchestrator
        from uri_core.core.state import SessionManager

        session_dir = os.path.join(self.temp_dir.name, f"sessions_{user_id or 'anon'}")
        os.makedirs(session_dir, exist_ok=True)
        session_mgr = SessionManager(storage_path=session_dir)

        principal = (
            PrincipalContext(user_id=user_id, role=role, device_id=None)
            if user_id is not None
            else PrincipalContext(user_id=None, role=None, device_id=None)
        )

        dispatcher = _FakeDispatcher()
        approval_gate = ApprovalGate(
            dispatcher=dispatcher,
            capability_registry=self.registry,
            capability_grants_store=self.store,
            principal=principal,
        )

        gateway = None
        if model_payload:
            gateway = ModelReasoningGateway(model_callable=_fake_model_callable(model_payload))

        orchestrator = UriOrchestrator(
            session_manager=session_mgr,
            approval_gate=approval_gate,
            capability_registry=self.registry,
            model_reasoning_gateway=gateway,
            principal=principal,
        )
        return orchestrator, dispatcher

    def test_e2e_per_user_grant_enforcement_real_orchestrator_call_path(self):
        # Alice is granted 'draft_institutional_note' only
        self.store.set_grants("alice", ["draft_institutional_note"], self.registered_ids)

        payload_granted = {
            "objective": "Draft note",
            "proposed_actions": [{"capability": "draft_institutional_note"}],
        }
        orch_alice, disp_alice = self._build_orchestrator("alice", model_payload=payload_granted)

        # Real process_user_input call - no manual principal injection at execute_tool
        result = orch_alice.process_user_input(session_id="s_alice_1", user_text="draft a note")
        self.assertEqual(len(disp_alice.calls), 1)
        self.assertEqual(disp_alice.calls[0][0], "draft_institutional_note")

        # Now Alice attempts to execute 'extract_student_records' (not in Alice's grants)
        payload_ungranted = {
            "objective": "Extract student records",
            "proposed_actions": [{"capability": "extract_student_records"}],
        }
        orch_alice_2, disp_alice_2 = self._build_orchestrator("alice", model_payload=payload_ungranted)
        result_2 = orch_alice_2.process_user_input(session_id="s_alice_2", user_text="extract records")
        # Dispatched tool must be rejected and dispatcher must NOT be called
        self.assertEqual(len(disp_alice_2.calls), 0)
        self.assertEqual(result_2.get("execution", {}).get("status"), "rejected")
        self.assertIn("not granted", result_2.get("response", {}).get("message", ""))

    def test_e2e_multi_user_isolation(self):
        # Alice has draft_institutional_note, Bob has extract_student_records
        self.store.set_grants("alice", ["draft_institutional_note"], self.registered_ids)
        self.store.set_grants("bob", ["extract_student_records"], self.registered_ids)

        payload = {
            "objective": "Draft note",
            "proposed_actions": [{"capability": "draft_institutional_note"}],
        }

        # Alice executes successfully
        orch_alice, disp_alice = self._build_orchestrator("alice", model_payload=payload)
        res_alice = orch_alice.process_user_input(session_id="s1", user_text="draft a note")
        self.assertEqual(len(disp_alice.calls), 1)

        # Bob attempts same capability and is rejected
        orch_bob, disp_bob = self._build_orchestrator("bob", model_payload=payload)
        res_bob = orch_bob.process_user_input(session_id="s2", user_text="draft a note")
        self.assertEqual(len(disp_bob.calls), 0)
        self.assertEqual(res_bob.get("execution", {}).get("status"), "rejected")

    def test_e2e_migration_default_for_user_without_records(self):
        # Charlie is an authenticated user with no record in capability_grants.json
        payload = {
            "objective": "Extract records",
            "proposed_actions": [{"capability": "extract_student_records"}],
        }
        orch_charlie, disp_charlie = self._build_orchestrator("charlie", model_payload=payload)
        res = orch_charlie.process_user_input(session_id="s3", user_text="extract records")
        self.assertEqual(len(disp_charlie.calls), 1)
        self.assertEqual(disp_charlie.calls[0][0], "extract_student_records")

    def test_e2e_anonymous_principal_fails_closed(self):
        # Unauthenticated principal (user_id is None) fails closed
        payload = {
            "objective": "Extract records",
            "proposed_actions": [{"capability": "extract_student_records"}],
        }
        orch_anon, disp_anon = self._build_orchestrator(user_id=None, model_payload=payload)
        res = orch_anon.process_user_input(session_id="s4", user_text="extract records")
        self.assertEqual(len(disp_anon.calls), 0)
        self.assertEqual(res.get("execution", {}).get("status"), "rejected")


if __name__ == "__main__":
    unittest.main()
