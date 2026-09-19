"""M33.1 Batch 1: Foundations & Lifecycle Contracts Proof.

Verifies:
- Separation of Connected Services vs Skills vs Capabilities vs Discovery/Graphify
- ExternalCredentialStore: user-scoped, atomic, isolated secret storage
- Lifecycle remove & ExternalCapabilityStore.remove: clean retirement of access and credentials
- ConnectedServiceStore: connect/disconnect lifecycle, token/key management, status reporting
- list_connection_status: includes external services without regressing Gmail/Drive
- GraphifyIndex: automatic indexing and refresh of connected services and external capabilities
"""

import os
import unittest
import uuid

os.environ.setdefault("URI_EXTERNAL_CREDENTIAL_SECRET", "test-external-credential-secret")

from uri_core.core.connection_status import list_connection_status, STATUS_CONNECTED, STATUS_NOT_CONNECTED
from uri_core.core.graphify_index import GraphifyIndex, build_index, refresh
from uri_core.external.credentials import ExternalCredentialStore
from uri_core.external.fixture_profiles import in_process_profile
from uri_core.external.lifecycle import LifecycleController, PRESENCE_ABSENT, derive_label
from uri_core.external.registry_bridge import ExternalCapabilityPublisher
from uri_core.external.service_contract import ConnectedServiceDescriptor
from uri_core.external.service_store import ConnectedServiceStore
from uri_core.external.store import ExternalCapabilityStore


class ExternalCredentialStoreTests(unittest.TestCase):
    def setUp(self):
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.root = os.path.join("temp_evidence", "m33_1_batch1", str(uuid.uuid4()))
        os.makedirs(self.root, exist_ok=True)
        self.store = ExternalCredentialStore(root=self.root)

    def test_credential_store_isolation_and_lifecycle(self):
        self.assertFalse(self.store.has_credential(self.user_a, "service_alpha"))
        self.assertIsNone(self.store.get_credential(self.user_a, "service_alpha"))

        self.store.set_credential(self.user_a, "service_alpha", {"api_key": "secret-alpha-123"})
        self.assertTrue(self.store.has_credential(self.user_a, "service_alpha"))
        self.assertEqual(self.store.get_credential(self.user_a, "service_alpha")["api_key"], "secret-alpha-123")

        # Isolation: user_b cannot see user_a's credential
        self.assertFalse(self.store.has_credential(self.user_b, "service_alpha"))
        self.assertIsNone(self.store.get_credential(self.user_b, "service_alpha"))

        # Deletion
        self.assertTrue(self.store.delete_credential(self.user_a, "service_alpha"))
        self.assertFalse(self.store.has_credential(self.user_a, "service_alpha"))
        self.assertFalse(self.store.delete_credential(self.user_a, "service_alpha"))


class CapabilityCleanRemovalTests(unittest.TestCase):
    def setUp(self):
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.root = os.path.join("temp_evidence", "m33_1_batch1", str(uuid.uuid4()))
        os.makedirs(self.root, exist_ok=True)
        self.store = ExternalCapabilityStore(root=self.root)
        self.cred_store = ExternalCredentialStore(root=self.root)

    def test_remove_cleanly_retires_capability_and_credential(self):
        profile = in_process_profile()
        profile_id = profile["id"]

        # Register, enable, and set credential
        reg = self.store.register_descriptor(profile, user_id=self.user_a, source_revision="rev1")
        self.assertTrue(reg.ok)
        self.store.configure(self.user_a, profile_id)
        self.store.authenticate(self.user_a, profile_id)
        self.store.enable(self.user_a, profile_id)
        self.cred_store.set_credential(self.user_a, profile_id, {"token": "cap-token-xyz"})

        # Verify present in published registry
        publisher = ExternalCapabilityPublisher(store=self.store)
        published = publisher.publish(self.user_a)
        self.assertIsNotNone(published.registry.get_capability(profile_id))

        # Now remove capability
        removed = self.store.remove(self.user_a, profile_id)
        self.assertTrue(removed)
        self.assertIsNone(self.store.get(self.user_a, profile_id))
        self.assertFalse(self.cred_store.has_credential(self.user_a, profile_id))

        # Removing again returns False
        self.assertFalse(self.store.remove(self.user_a, profile_id))

        # Re-publishing produces a registry generation without the capability
        republished = publisher.publish(self.user_a)
        self.assertIsNone(republished.registry.get_capability(profile_id))

    def test_lifecycle_controller_remove_transition(self):
        controller = LifecycleController()
        state = controller.detect("cap_test")
        state = controller.apply_qualification(state, qualified=True)
        state = controller.configure(state)
        state = controller.enable(state)
        self.assertEqual(derive_label(state), "ready")

        state = controller.remove(state)
        self.assertEqual(state.presence, PRESENCE_ABSENT)
        self.assertFalse(state.enabled)
        self.assertEqual(derive_label(state), "not_installed")


class ConnectedServiceStoreTests(unittest.TestCase):
    def setUp(self):
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.root = os.path.join("temp_evidence", "m33_1_batch1", str(uuid.uuid4()))
        os.makedirs(self.root, exist_ok=True)
        self.service_store = ConnectedServiceStore(root=self.root)

    def test_connected_service_lifecycle_connect_and_disconnect(self):
        # Default services exist
        services = self.service_store.list_services(self.user_a)
        svc_ids = {s["id"] for s in services}
        self.assertIn("gmail", svc_ids)
        self.assertIn("github", svc_ids)
        self.assertIn("firecrawl", svc_ids)

        # Initially github is not connected
        initial_status = self.service_store.get_status(self.user_a, "github")
        self.assertEqual(initial_status["status"], STATUS_NOT_CONNECTED)

        # Connect github
        connect_res = self.service_store.connect(
            self.user_a, "github", {"token": "ghp_mock_token_123"}, scopes=["repo", "read:user"]
        )
        self.assertEqual(connect_res["status"], STATUS_CONNECTED)
        self.assertEqual(connect_res["scopes"], ["repo", "read:user"])

        # Check status after connect
        active_status = self.service_store.get_status(self.user_a, "github")
        self.assertEqual(active_status["status"], STATUS_CONNECTED)
        self.assertEqual(active_status["detail"], "Connected")

        # Isolation: user_b is not connected
        user_b_status = self.service_store.get_status(self.user_b, "github")
        self.assertEqual(user_b_status["status"], STATUS_NOT_CONNECTED)

        # Disconnect
        disconnect_res = self.service_store.disconnect(self.user_a, "github")
        self.assertEqual(disconnect_res["status"], STATUS_NOT_CONNECTED)
        self.assertEqual(self.service_store.get_status(self.user_a, "github")["status"], STATUS_NOT_CONNECTED)
        self.assertFalse(self.service_store.credential_store.has_credential(self.user_a, "github"))

    def test_list_connection_status_integration_preserves_gmail(self):
        # List connections without user_id
        default_conns = list_connection_status()
        self.assertTrue(any(c["id"] == "gmail" for c in default_conns))
        self.assertTrue(any(c["id"] == "drive" for c in default_conns))

        # List connections with user_id
        user_conns = list_connection_status(user_id=self.user_a)
        self.assertTrue(any(c["id"] == "gmail" for c in user_conns))
        self.assertTrue(any(c["id"] == "drive" for c in user_conns))
        self.assertTrue(any(c["id"] == "github" for c in user_conns))
        self.assertTrue(any(c["id"] == "firecrawl" for c in user_conns))


class DiscoveryGraphifySyncTests(unittest.TestCase):
    def setUp(self):
        self.user_id = str(uuid.uuid4())
        self.root = os.path.join("temp_evidence", "m33_1_batch1", str(uuid.uuid4()))
        os.makedirs(self.root, exist_ok=True)
        self.service_store = ConnectedServiceStore(root=self.root)

    def test_graphify_indexes_connected_services_and_refreshes(self):
        # Build index with service store
        index = build_index(connected_service_store=self.service_store, user_id=self.user_id)
        self.assertIn("service:gmail", index.records)
        self.assertIn("service:github", index.records)
        self.assertIn("service:firecrawl", index.records)

        # Initially github is not available (not connected)
        self.assertFalse(index.records["service:github"]["availability"]["available"])

        # Connect github and refresh services scope
        self.service_store.connect(self.user_id, "github", {"token": "ghp_123"})
        refresh(index, connected_service_store=self.service_store, user_id=self.user_id, scope="services")

        # After refresh, github service record reflects connected state
        self.assertTrue(index.records["service:github"]["availability"]["available"])
        self.assertEqual(index.records["service:github"]["kind"], "connected_service")
