"""Tests for GET/POST /memory and PUT/DELETE /memory/{id}. No Ollama
or network involved - these only exercise MemoryStore through the real
FastAPI app."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.user_memory import MemoryStore


class MemoryEndpointTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_memory_store = server._memory_store

        server._memory_store = MemoryStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_memory.json"
            )
        )

        self.client = TestClient(server.app)

    def tearDown(self):
        server._memory_store = self._original_memory_store
        self.temp_dir.cleanup()

    def test_list_memory_starts_empty(self):
        response = self.client.get("/memory")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"memories": []})

    def test_post_memory_creates_a_user_provided_entry(self):
        response = self.client.post(
            "/memory",
            json={
                "category": "preference",
                "content": "prefers terse office notes",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertTrue(body["memory_id"])
        self.assertEqual(body["category"], "preference")
        self.assertEqual(body["consent"], "user_provided")
        self.assertEqual(body["content"], "prefers terse office notes")

    def test_posted_memory_appears_in_list(self):
        self.client.post(
            "/memory",
            json={"category": "interest", "content": "badminton"},
        )

        listed = self.client.get("/memory").json()["memories"]

        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["content"], "badminton")

    def test_post_memory_rejects_invalid_category(self):
        response = self.client.post(
            "/memory",
            json={"category": "not_real", "content": "x"},
        )

        self.assertEqual(response.status_code, 400)

    def test_post_memory_rejects_credential_shaped_content(self):
        response = self.client.post(
            "/memory",
            json={"category": "other", "content": "sk-secretvalue"},
        )

        self.assertEqual(response.status_code, 400)

    def test_put_memory_updates_existing_entry(self):
        created = self.client.post(
            "/memory",
            json={"category": "preference", "content": "a"},
        ).json()

        response = self.client.put(
            f"/memory/{created['memory_id']}",
            json={"category": "interest", "content": "b"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["category"], "interest")
        self.assertEqual(body["content"], "b")
        self.assertEqual(body["consent"], "user_provided")

    def test_put_memory_returns_404_for_unknown_id(self):
        response = self.client.put(
            "/memory/does-not-exist",
            json={"category": "preference", "content": "x"},
        )

        self.assertEqual(response.status_code, 404)

    def test_delete_memory_removes_it(self):
        created = self.client.post(
            "/memory",
            json={"category": "preference", "content": "a"},
        ).json()

        response = self.client.delete(
            f"/memory/{created['memory_id']}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted"], True)

        listed = self.client.get("/memory").json()["memories"]
        self.assertEqual(listed, [])

    def test_delete_memory_returns_404_for_unknown_id(self):
        response = self.client.delete("/memory/does-not-exist")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
