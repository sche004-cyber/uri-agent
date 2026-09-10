"""M21 item 6: the file-store isolation fix.

Before M21, uri_core/core/file_store.py's own module docstring claimed
"User scoping mirrors the existing convention exactly ... identical to
how MemoryStore/UserProfileStore are already wired in
_build_user_context" - but server.py actually constructed exactly one
ambient, global FileStore() shared by every request regardless of login,
and never passed a user-scoped FileStore into UriOrchestrator either.
Two different logged-in users who happened to reuse the same
client-supplied session_id (the only key /files ever filtered on) could
list, download, or delete each other's attachments.

This test proves the fix using the exact same setUp/signup pattern as
test_multi_user_isolation.py (the existing profile/memory/tasks/session
isolation suite this mirrors) - real HTTP via FastAPI TestClient, no
Ollama/network involved.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import edge, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import UserAccountStore


class FileStoreIsolationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_user_account_store = server._user_account_store
        self._original_auth_session_store = server._auth_session_store
        self._original_user_contexts = server._user_contexts
        self._original_user_state_root = server._USER_STATE_ROOT
        self._original_file_store = server._file_store

        server._user_account_store = UserAccountStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_accounts.json"
            )
        )
        server._auth_session_store = AuthSessionStore(
            storage_path=os.path.join(
                self.temp_dir.name, "auth_sessions.json"
            )
        )
        server._user_contexts = {}
        server._USER_STATE_ROOT = os.path.join(self.temp_dir.name, "users")

        from uri_core.core.file_store import FileStore

        server._file_store = FileStore(
            storage_dir=os.path.join(self.temp_dir.name, "legacy-uploads")
        )

        # M22.3: several accounts are signed up per test method here,
        # all from TestClient's single fixed fake client host - without
        # a reset, the module-level rate limiter (shared process state,
        # keyed by client IP - see edge.py) would otherwise carry a
        # count across every test in this file (and every other test
        # module run in the same process), tripping on a later,
        # legitimate call.
        edge.reset_rate_limiters()

        self.client = TestClient(server.app)

    def tearDown(self):
        server._user_account_store = self._original_user_account_store
        server._auth_session_store = self._original_auth_session_store
        server._user_contexts = self._original_user_contexts
        server._USER_STATE_ROOT = self._original_user_state_root
        server._file_store = self._original_file_store
        edge.reset_rate_limiters()
        self.temp_dir.cleanup()

    def _signup(self, username: str, password: str = "correct-horse-1"):
        response = self.client.post(
            "/auth/signup",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _upload(self, token, name, content, session_id="shared-session-id"):
        return self.client.post(
            "/files",
            headers=self._auth(token),
            data={"session_id": session_id},
            files={"file": (name, content, "text/plain")},
        )

    # ------------------------------------------------------------
    # Two users reusing the SAME client-supplied session_id - the
    # exact scenario the M21 audit flagged as a real leak.
    # ------------------------------------------------------------

    def test_same_session_id_never_leaks_attachments_across_users(self):
        alice = self._signup("files-alice")
        bob = self._signup("files-bob")

        self._upload(alice["token"], "alice-only.txt", b"alice's data")

        alice_files = self.client.get(
            "/files",
            headers=self._auth(alice["token"]),
            params={"session_id": "shared-session-id"},
        ).json()["files"]
        bob_files = self.client.get(
            "/files",
            headers=self._auth(bob["token"]),
            params={"session_id": "shared-session-id"},
        ).json()["files"]

        self.assertEqual(len(alice_files), 1)
        self.assertEqual(alice_files[0]["filename"], "alice-only.txt")
        self.assertEqual(bob_files, [])

    def test_user_cannot_download_another_users_file_by_id(self):
        alice = self._signup("dl-alice")
        bob = self._signup("dl-bob")

        file_id = self._upload(
            alice["token"], "secret.txt", b"alice's secret"
        ).json()["file"]["file_id"]

        bob_attempt = self.client.get(
            f"/files/{file_id}/content", headers=self._auth(bob["token"])
        )
        self.assertEqual(bob_attempt.status_code, 404)

        alice_attempt = self.client.get(
            f"/files/{file_id}/content", headers=self._auth(alice["token"])
        )
        self.assertEqual(alice_attempt.status_code, 200)
        self.assertEqual(alice_attempt.content, b"alice's secret")

    def test_user_cannot_delete_another_users_file_by_id(self):
        alice = self._signup("del-alice")
        bob = self._signup("del-bob")

        file_id = self._upload(
            alice["token"], "keep-me.txt", b"data"
        ).json()["file"]["file_id"]

        bob_attempt = self.client.delete(
            f"/files/{file_id}", headers=self._auth(bob["token"])
        )
        self.assertFalse(bob_attempt.json()["deleted"])

        # Alice's file is untouched by Bob's failed attempt.
        alice_files = self.client.get(
            "/files",
            headers=self._auth(alice["token"]),
            params={"session_id": "shared-session-id"},
        ).json()["files"]
        self.assertEqual(len(alice_files), 1)

        alice_attempt = self.client.delete(
            f"/files/{file_id}", headers=self._auth(alice["token"])
        )
        self.assertTrue(alice_attempt.json()["deleted"])

    # ------------------------------------------------------------
    # Each logged-in user gets their own on-disk FileStore, rooted
    # under their own user_id - not the single ambient store.
    # ------------------------------------------------------------

    def test_each_user_gets_a_distinct_file_store_rooted_at_their_own_directory(
        self,
    ):
        alice = self._signup("store-alice")
        bob = self._signup("store-bob")

        alice_store = server._get_user_context(alice["user_id"]).file_store
        bob_store = server._get_user_context(bob["user_id"]).file_store

        self.assertIsNot(alice_store, bob_store)
        self.assertNotEqual(alice_store.storage_dir, bob_store.storage_dir)
        self.assertIn(alice["user_id"], alice_store.storage_dir)
        self.assertIn(bob["user_id"], bob_store.storage_dir)

    def test_orchestrator_file_store_matches_the_endpoints_file_store(self):
        # The Brain's own attachment_context (UriOrchestrator.file_store)
        # must be the SAME per-user store the /files endpoints write to -
        # otherwise an upload would never be visible to the Brain, or
        # vice versa. See _build_user_context wiring file_store into both
        # the returned _UserContext and UriOrchestrator(file_store=...).
        alice = self._signup("wiring-alice")

        context = server._get_user_context(alice["user_id"])
        self.assertIs(context.file_store, context.orchestrator.file_store)

    # ------------------------------------------------------------
    # Backward compatibility: an unauthenticated request still uses the
    # single legacy ambient store, exactly as before login existed.
    # ------------------------------------------------------------

    def test_no_authorization_header_falls_back_to_legacy_ambient_store(self):
        response = self.client.post(
            "/files",
            data={"session_id": "legacy-session"},
            files={"file": ("legacy.txt", b"legacy data", "text/plain")},
        )
        self.assertEqual(response.status_code, 200)

        listed = self.client.get(
            "/files", params={"session_id": "legacy-session"}
        ).json()["files"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["filename"], "legacy.txt")


if __name__ == "__main__":
    unittest.main()
