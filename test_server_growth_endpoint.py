"""Tests for GET /growth and its wiring as a downstream side effect of
POST /memory and POST /profile. No Ollama or network involved."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.growth_ledger import GrowthLedgerStore
from uri_core.core.user_memory import MemoryStore
from uri_core.core.user_profile import UserProfileStore


class GrowthEndpointTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_growth_ledger_store = server._growth_ledger_store
        self._original_memory_store = server._memory_store
        self._original_user_profile_store = server._user_profile_store

        server._growth_ledger_store = GrowthLedgerStore(
            storage_path=os.path.join(
                self.temp_dir.name, "growth_ledger.json"
            )
        )
        server._memory_store = MemoryStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_memory.json"
            )
        )
        server._user_profile_store = UserProfileStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_profile.json"
            )
        )

        self.client = TestClient(server.app)

    def tearDown(self):
        server._growth_ledger_store = self._original_growth_ledger_store
        server._memory_store = self._original_memory_store
        server._user_profile_store = self._original_user_profile_store
        self.temp_dir.cleanup()

    def test_growth_starts_at_zero_xp_level_one(self):
        response = self.client.get("/growth")

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["total_xp"], 0)
        self.assertEqual(body["level"], 1)
        self.assertEqual(body["achievements"], [])

    def test_posting_a_memory_awards_xp(self):
        self.client.post(
            "/memory", json={"category": "preference", "content": "a"}
        )

        summary = self.client.get("/growth").json()

        self.assertEqual(summary["total_xp"], 10)
        self.assertIn("first_memory", summary["achievements"])

    def test_posting_a_profile_awards_xp(self):
        self.client.post(
            "/profile",
            json={
                "communication_style": "formal",
                "autonomy_level": "askEveryTime",
                "focus_areas": [],
            },
        )

        summary = self.client.get("/growth").json()

        self.assertEqual(summary["total_xp"], 5)
        self.assertIn("profile_configured", summary["achievements"])

    def test_editing_a_memory_via_put_does_not_award_additional_xp(self):
        # Scope decision: only creation (POST) is a growth event.
        # Editing an existing memory is not treated as a fresh
        # "taught URI something new" moment.
        created = self.client.post(
            "/memory", json={"category": "preference", "content": "a"}
        ).json()

        self.client.put(
            f"/memory/{created['memory_id']}",
            json={"category": "preference", "content": "b"},
        )

        summary = self.client.get("/growth").json()

        self.assertEqual(summary["total_xp"], 10)

    def test_deleting_a_memory_does_not_remove_earned_xp(self):
        # Growth history is append-only - deleting the memory later
        # does not retroactively un-happen the fact that the user
        # taught URI something at the time.
        created = self.client.post(
            "/memory", json={"category": "preference", "content": "a"}
        ).json()

        self.client.delete(f"/memory/{created['memory_id']}")

        summary = self.client.get("/growth").json()

        self.assertEqual(summary["total_xp"], 10)

    def test_rejected_memory_post_awards_no_xp(self):
        response = self.client.post(
            "/memory", json={"category": "not_real", "content": "x"}
        )
        self.assertEqual(response.status_code, 400)

        summary = self.client.get("/growth").json()

        self.assertEqual(summary["total_xp"], 0)
        self.assertEqual(summary["event_count"], 0)


if __name__ == "__main__":
    unittest.main()
