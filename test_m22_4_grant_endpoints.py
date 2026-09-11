"""M22.4 Integration Tests for Admin Grant Endpoints and Authority (AO-4).

Covers §7 Test Plan categories 4 through 10:
4. Unauthorized USER attempts (403 on all three admin grant endpoints).
5. Unauthorized anonymous attempts (401 on all three admin grant endpoints).
6. ADMIN grant/revoke (reflected in subsequent GET and resolved /capabilities).
7. Per-user isolation (granting/revoking user A never leaks to user B or admin B).
8. Migration default (every pre-existing user defaults to full current registry).
9. Audit evidence (successful PUT writes exactly one AuditTrail record with acting admin, target user, resulting grants).
10. UI cannot bypass backend authorization (direct ApprovalGate.execute_tool rejection).
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, server
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.capability_resolver import CapabilityGrantsStore
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.principal_context import PrincipalContext
from uri_core.core.user_accounts import ROLE_ADMIN, ROLE_USER, UserAccountStore


class AdminGrantEndpointsTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Store backups
        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_capability_grants_store = server._capability_grants_store
        self._original_audit_trail = server._audit_trail
        self._original_user_contexts = server._user_contexts

        # Wire isolated test stores
        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(self.temp_dir.name, "user_accounts.json")
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(self.temp_dir.name, "auth_sessions.json")
        )
        server._capability_grants_store = CapabilityGrantsStore(
            storage_path=os.path.join(self.temp_dir.name, "capability_grants.json")
        )
        server._audit_trail = AuditTrail()
        server._user_contexts = {}

        edge.reset_rate_limiters()
        self.client = TestClient(server.app)

        # First signup is automatically ADMIN (M22.2 deterministic bootstrap)
        admin = self._signup("admin_m22_4")
        self.admin_token = admin["token"]
        self.admin_user_id = admin["user_id"]
        self.assertEqual(
            self.client.get("/auth/me", headers=self._auth(self.admin_token)).json()["role"],
            ROLE_ADMIN,
        )

        # Second signup is standard USER
        user = self._signup("user_m22_4")
        self.user_token = user["token"]
        self.user_id = user["user_id"]
        self.assertEqual(
            self.client.get("/auth/me", headers=self._auth(self.user_token)).json()["role"],
            ROLE_USER,
        )

        # Third signup: second USER
        user2 = self._signup("user2_m22_4")
        self.user2_token = user2["token"]
        self.user2_id = user2["user_id"]

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._capability_grants_store = self._original_capability_grants_store
        server._audit_trail = self._original_audit_trail
        server._user_contexts = self._original_user_contexts
        edge.reset_rate_limiters()

    def _signup(self, username: str, password: str = "CorrectHorseBattery99!"):
        resp = self.client.post(
            "/auth/signup", json={"username": username, "password": password}
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def _auth(self, token: str):
        return {"Authorization": f"Bearer {token}"}

    def test_anonymous_requests_get_401(self):
        """Category 5: 401 anonymous on all three endpoints."""
        self.assertEqual(self.client.get("/admin/users").status_code, 401)
        self.assertEqual(self.client.get(f"/admin/users/{self.user_id}/grants").status_code, 401)
        self.assertEqual(
            self.client.put(f"/admin/users/{self.user_id}/grants", json={"grants": []}).status_code,
            401,
        )

    def test_non_admin_user_gets_403(self):
        """Category 4: 403 non-admin on all three endpoints."""
        headers = self._auth(self.user_token)
        self.assertEqual(self.client.get("/admin/users", headers=headers).status_code, 403)
        self.assertEqual(self.client.get(f"/admin/users/{self.user_id}/grants", headers=headers).status_code, 403)
        self.assertEqual(
            self.client.put(f"/admin/users/{self.user_id}/grants", json={"grants": []}, headers=headers).status_code,
            403,
        )

    def test_admin_list_users(self):
        """ADMIN successfully lists users for the picker."""
        headers = self._auth(self.admin_token)
        resp = self.client.get("/admin/users", headers=headers)
        self.assertEqual(resp.status_code, 200)
        users = resp.json()["users"]
        self.assertGreaterEqual(len(users), 2)
        user_ids = {u["user_id"] for u in users}
        self.assertIn(self.admin_user_id, user_ids)
        self.assertIn(self.user_id, user_ids)

    def test_admin_grant_and_revoke_and_capabilities_view(self):
        """Category 6: ADMIN can PUT narrower grants and inspect resolved /capabilities."""
        headers = self._auth(self.admin_token)
        all_caps = server._capability_registry.list_capabilities()
        registered_ids = sorted([c.id for c in all_caps])
        self.assertGreaterEqual(len(registered_ids), 2)

        # 1. Initially, user has default full registry
        get_init = self.client.get(f"/admin/users/{self.user_id}/grants", headers=headers)
        self.assertEqual(get_init.status_code, 200)
        self.assertEqual(set(get_init.json()["grants"]), set(registered_ids))

        # 2. Admin narrows grants to just 1 capability
        narrowed_id = registered_ids[0]
        put_resp = self.client.put(
            f"/admin/users/{self.user_id}/grants",
            json={"grants": [narrowed_id]},
            headers=headers,
        )
        self.assertEqual(put_resp.status_code, 200)
        self.assertEqual(put_resp.json()["grants"], [narrowed_id])

        # 3. Verify user's GET /capabilities reflects the narrowed set
        user_headers = self._auth(self.user_token)
        caps_resp = self.client.get("/capabilities", headers=user_headers)
        self.assertEqual(caps_resp.status_code, 200)
        user_cap_ids = [c["id"] for c in caps_resp.json()["capabilities"]]
        self.assertEqual(user_cap_ids, [narrowed_id])

        # 4. Unknown capability ID is rejected with 400
        bad_put = self.client.put(
            f"/admin/users/{self.user_id}/grants",
            json={"grants": [narrowed_id, "nonexistent_capability_12345"]},
            headers=headers,
        )
        self.assertEqual(bad_put.status_code, 400)
        self.assertIn("Unknown capability ID", bad_put.json()["detail"])

    def test_per_user_isolation(self):
        """Category 7: Modifying user A's grants does not affect user B's."""
        headers = self._auth(self.admin_token)
        all_caps = server._capability_registry.list_capabilities()
        registered_ids = sorted([c.id for c in all_caps])

        # Narrow user 1 to first capability
        self.client.put(
            f"/admin/users/{self.user_id}/grants",
            json={"grants": [registered_ids[0]]},
            headers=headers,
        )

        # Narrow user 2 to second capability
        self.client.put(
            f"/admin/users/{self.user2_id}/grants",
            json={"grants": [registered_ids[1]]},
            headers=headers,
        )

        # User 1 sees only cap 0
        u1_resp = self.client.get("/capabilities", headers=self._auth(self.user_token))
        u1_caps = [c["id"] for c in u1_resp.json()["capabilities"]]
        self.assertEqual(u1_caps, [registered_ids[0]])

        # User 2 sees only cap 1
        u2_resp = self.client.get("/capabilities", headers=self._auth(self.user2_token))
        u2_caps = [c["id"] for c in u2_resp.json()["capabilities"]]
        self.assertEqual(u2_caps, [registered_ids[1]])

    def test_migration_default_for_unrecorded_users(self):
        """Category 8: Unrecorded user_id defaults to full registry, for USER and ADMIN alike."""
        all_caps = server._capability_registry.list_capabilities()
        registered_ids = {c.id for c in all_caps}

        # Neither user nor admin has been explicitly mutated yet
        self.assertFalse(server._capability_grants_store.has_user_record(self.user_id))
        self.assertFalse(server._capability_grants_store.has_user_record(self.admin_user_id))

        user_grants = server._capability_grants_store.get_grants(self.user_id, registry_ceiling_ids=registered_ids)
        admin_grants = server._capability_grants_store.get_grants(self.admin_user_id, registry_ceiling_ids=registered_ids)

        self.assertEqual(user_grants, registered_ids)
        self.assertEqual(admin_grants, registered_ids)

    def test_audit_evidence_on_grant_mutation(self):
        """Category 9: Successful PUT produces exactly one AuditTrail record with acting admin, target, and grants."""
        headers = self._auth(self.admin_token)
        all_caps = server._capability_registry.list_capabilities()
        first_id = all_caps[0].id

        events_before = server._audit_trail.all_events(event_type="admin_grant_mutation")
        count_before = len(events_before)

        resp = self.client.put(
            f"/admin/users/{self.user_id}/grants",
            json={"grants": [first_id]},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200)

        events_after = server._audit_trail.all_events(event_type="admin_grant_mutation")
        self.assertEqual(len(events_after), count_before + 1)

        audit_event = events_after[-1]
        self.assertEqual(audit_event.status, "success")
        self.assertEqual(audit_event.metadata["acting_user_id"], self.admin_user_id)
        self.assertEqual(audit_event.metadata["target_user_id"], self.user_id)
        self.assertEqual(audit_event.metadata["resulting_grants"], first_id)

    def test_ui_cannot_bypass_backend_authorization(self):
        """Category 10: Calling ApprovalGate.execute_tool directly for ungranted capability rejects."""
        all_caps = server._capability_registry.list_capabilities()
        registered_ids = sorted([c.id for c in all_caps])

        # Restrict user to cap 0 only
        server._capability_grants_store.set_grants(
            self.user_id, [registered_ids[0]], set(registered_ids)
        )

        gate = ApprovalGate(
            dispatcher=ToolDispatcher(),
            capability_registry=server._capability_registry,
            approval_store=ApprovalStore(),
            capability_grants_store=server._capability_grants_store,
        )

        # Call execute_tool directly for cap 1 (ungranted)
        principal = PrincipalContext(user_id=self.user_id, role=ROLE_USER, device_id=None)
        result = gate.execute_tool(
            tool_name=registered_ids[1],
            session_id="session_direct_bypass",
            principal=principal,
        )

        self.assertEqual(result.get("status"), "rejected")
        self.assertIn("not granted", result.get("message", ""))

    def test_e2e_per_user_capability_restriction_through_orchestrator(self):
        """Gap 3: Proves per-user capability restriction through the real orchestrator
        dispatch call path WITHOUT manually passing principal to execute_tool.
        """
        all_caps = server._capability_registry.list_capabilities()
        registered_ids = sorted([c.id for c in all_caps])
        cap_allowed = registered_ids[0]
        cap_forbidden = registered_ids[1]

        # 1. Restrict self.user_id to cap_allowed only
        server._capability_grants_store.set_grants(
            self.user_id, [cap_allowed], set(registered_ids)
        )

        # 2. Get user's context from server._get_user_context
        ctx_user = server._get_user_context(self.user_id)

        # 3. Direct execution through user's ApprovalGate without passing principal=
        # The gate must enforce self.user_id's restriction from its bound principal
        result_forbidden = ctx_user.orchestrator.approval_gate.execute_tool(
            tool_name=cap_forbidden,
            session_id="session_user1",
        )
        self.assertEqual(result_forbidden.get("status"), "rejected")
        self.assertIn("not granted for this user", result_forbidden.get("message", ""))

        # 4. Allowed capability is permitted through user's ApprovalGate
        from unittest.mock import patch
        with patch.object(
            ctx_user.orchestrator.approval_gate.dispatcher,
            "execute_tool",
            return_value={"status": "success", "data": {}},
        ):
            result_allowed = ctx_user.orchestrator.approval_gate.execute_tool(
                tool_name=cap_allowed,
                session_id="session_user1",
            )
            self.assertNotEqual(result_allowed.get("status"), "rejected")

        # 5. User 2 (unrestricted / migration default) CAN execute cap_forbidden
        ctx_user2 = server._get_user_context(self.user2_id)
        with patch.object(
            ctx_user2.orchestrator.approval_gate.dispatcher,
            "execute_tool",
            return_value={"status": "success", "data": {}},
        ):
            result_u2 = ctx_user2.orchestrator.approval_gate.execute_tool(
                tool_name=cap_forbidden,
                session_id="session_user2",
            )
            self.assertNotEqual(result_u2.get("status"), "rejected")

        # 6. Anonymous gate (no principal at all) fails closed on execute_tool
        anon_gate = ApprovalGate(
            dispatcher=ToolDispatcher(),
            capability_registry=server._capability_registry,
            capability_grants_store=server._capability_grants_store,
        )
        result_anon = anon_gate.execute_tool(
            tool_name=cap_allowed,
            session_id="session_anon",
        )
        self.assertEqual(result_anon.get("status"), "rejected")


if __name__ == "__main__":
    unittest.main()
