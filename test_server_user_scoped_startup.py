"""Tests for Milestone 5 (User-Scoped Portable State Storage): that
importing uri_core.app.server performs no filesystem mutation, that
_initialize_user_scoped_stores() (run only from the app's lifespan
startup handler) resolves user_id, migrates legacy files exactly once
without altering them, and rewires the module's store singletons -
and that this all actually fires across a real TestClient startup/
shutdown cycle. No Ollama or network involved."""

import importlib
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from uri_core.app import server
from uri_core.core.growth_ledger import GrowthLedgerStore
from uri_core.core.identity import UserIdentityStore
from uri_core.core.user_memory import MemoryStore
from uri_core.core.user_profile import UserProfileStore

VALID_USER_ID = "8fd65c6b-3298-4efc-8196-a4d98145562b"


class ImportHasNoFilesystemSideEffectsTests(unittest.TestCase):
    """Scoped to what Milestone 5 actually controls: identity, profile,
    memory, and growth-ledger state. Importing server.py already has
    pre-existing, unrelated filesystem side effects on this baseline
    (SkillMemory/FrictionLogger write uri_workspace/skill_memory.json
    and uri_workspace/friction_log.json at construction time, verified
    present even on commit bf303d0 before this milestone) - fixing
    that is out of scope here (a different, unrelated system; see
    milestone principle "do not modify unrelated working systems
    merely for cleanup"). What this test asserts is narrower and
    exact: nothing this milestone touches - portable_identity.json,
    device_identity.json, user_profile.json, user_memory.json,
    growth_ledger.json, or the uri_workspace/users/ directory - is
    created merely by importing the module.
    """

    _MILESTONE_5_PATHS = (
        "uri_workspace/portable_identity.json",
        "uri_workspace/device_identity.json",
        "uri_workspace/user_profile.json",
        "uri_workspace/user_memory.json",
        "uri_workspace/growth_ledger.json",
        "uri_workspace/users",
    )

    def test_importing_server_module_creates_no_identity_or_state_files(
        self,
    ):
        temp_dir = tempfile.TemporaryDirectory()

        try:
            original_cwd = os.getcwd()
            os.chdir(temp_dir.name)

            try:
                importlib.reload(server)

                for relative_path in self._MILESTONE_5_PATHS:
                    self.assertFalse(
                        os.path.exists(
                            os.path.join(temp_dir.name, relative_path)
                        ),
                        f"{relative_path} was created merely by "
                        "importing server.py",
                    )
            finally:
                os.chdir(original_cwd)
                # Restore the module to its normal (real-cwd) state
                # for every later test in the suite.
                importlib.reload(server)
        finally:
            temp_dir.cleanup()


class InitializeUserScopedStoresTests(unittest.TestCase):
    """Exercises _initialize_user_scoped_stores() directly, entirely
    against a temp directory - never the real uri_workspace/."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.temp_dir.name, "users")

        self._original_user_identity_store = server._user_identity_store
        self._original_user_profile_store = server._user_profile_store
        self._original_memory_store = server._memory_store
        self._original_growth_ledger_store = server._growth_ledger_store

        server._user_identity_store = UserIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "portable_identity.json"
            )
        )

        self.legacy_profile_path = os.path.join(
            self.temp_dir.name, "user_profile.json"
        )
        self.legacy_memory_path = os.path.join(
            self.temp_dir.name, "user_memory.json"
        )
        self.legacy_growth_path = os.path.join(
            self.temp_dir.name, "growth_ledger.json"
        )

        server._user_profile_store = UserProfileStore(
            storage_path=self.legacy_profile_path
        )
        server._memory_store = MemoryStore(
            storage_path=self.legacy_memory_path
        )
        server._growth_ledger_store = GrowthLedgerStore(
            storage_path=self.legacy_growth_path
        )

    def tearDown(self):
        server._user_identity_store = self._original_user_identity_store
        server._user_profile_store = self._original_user_profile_store
        server._memory_store = self._original_memory_store
        server._growth_ledger_store = self._original_growth_ledger_store
        self.temp_dir.cleanup()

    def _write(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

    def test_rewires_stores_to_user_scoped_paths(self):
        server._initialize_user_scoped_stores(root=self.root)

        user_id = server._user_identity_store.load_or_create().user_id

        self.assertIn(
            os.path.join(self.root, user_id),
            server._user_profile_store.storage_path,
        )
        self.assertIn(
            os.path.join(self.root, user_id),
            server._memory_store.storage_path,
        )
        self.assertIn(
            os.path.join(self.root, user_id),
            server._growth_ledger_store.storage_path,
        )

    def test_migrates_existing_legacy_files_byte_identical(self):
        profile_content = (
            '{"communication_style": "concise", "autonomy_level": '
            '"askEveryTime", "focus_areas": [], "updated_at": "x", '
            '"schema_version": "1.0"}'
        )
        memory_content = '{"schema_version": "1.0", "memories": []}'

        self._write(self.legacy_profile_path, profile_content)
        self._write(self.legacy_memory_path, memory_content)
        # growth_ledger.json intentionally left absent - matches the
        # real repository's current state (no growth event has ever
        # been recorded against the ambient store yet).

        server._initialize_user_scoped_stores(root=self.root)

        with open(
            server._user_profile_store.storage_path, "r", encoding="utf-8"
        ) as file:
            self.assertEqual(file.read(), profile_content)

        with open(
            server._memory_store.storage_path, "r", encoding="utf-8"
        ) as file:
            self.assertEqual(file.read(), memory_content)

        # Legacy originals remain untouched (copy-only, non-destructive).
        with open(
            self.legacy_profile_path, "r", encoding="utf-8"
        ) as file:
            self.assertEqual(file.read(), profile_content)

        with open(self.legacy_memory_path, "r", encoding="utf-8") as file:
            self.assertEqual(file.read(), memory_content)

    def test_missing_legacy_growth_ledger_is_not_an_error(self):
        # No growth_ledger.json on disk at all - must not raise, and
        # the rewired store must still work (start empty).
        server._initialize_user_scoped_stores(root=self.root)

        self.assertEqual(
            server._growth_ledger_store.summary()["total_xp"], 0
        )

    def test_is_idempotent_across_repeated_startups(self):
        self._write(self.legacy_profile_path, "original")

        server._initialize_user_scoped_stores(root=self.root)
        first_path = server._user_profile_store.storage_path

        # Simulate a second startup writing new data to the
        # user-scoped file, then re-running init - must not clobber it
        # with the legacy content again.
        self._write(first_path, "diverged after first startup")

        server._initialize_user_scoped_stores(root=self.root)

        self.assertEqual(server._user_profile_store.storage_path, first_path)

        with open(first_path, "r", encoding="utf-8") as file:
            self.assertEqual(file.read(), "diverged after first startup")

    def test_invalid_user_id_degrades_to_leaving_stores_unchanged(self):
        # Corrupt the identity file so user_id is not a valid UUID.
        self._write(
            server._user_identity_store.storage_path,
            '{"user_id": "not-a-valid-uuid", "created_at": "x"}',
        )

        before_profile_path = server._user_profile_store.storage_path
        before_memory_path = server._memory_store.storage_path
        before_growth_path = server._growth_ledger_store.storage_path

        # Must not raise.
        server._initialize_user_scoped_stores(root=self.root)

        self.assertEqual(
            server._user_profile_store.storage_path, before_profile_path
        )
        self.assertEqual(
            server._memory_store.storage_path, before_memory_path
        )
        self.assertEqual(
            server._growth_ledger_store.storage_path, before_growth_path
        )


class LifespanFiresOnRealStartupTests(unittest.TestCase):
    """Proves the wiring actually fires end-to-end through FastAPI's
    lifespan protocol via `with TestClient(app):`, and does NOT fire
    for the bare TestClient(app) pattern every other test in this repo
    uses - both are asserted explicitly so this milestone's central
    assumption stays covered by a real test, not just documentation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self._original_user_identity_store = server._user_identity_store
        self._original_user_profile_store = server._user_profile_store
        self._original_memory_store = server._memory_store
        self._original_growth_ledger_store = server._growth_ledger_store
        self._original_initialize = server._initialize_user_scoped_stores

        self.calls = []
        real_initialize = server._initialize_user_scoped_stores

        def _spy(root="uri_workspace/users"):
            self.calls.append(root)
            real_initialize(root=os.path.join(self.temp_dir.name, "users"))

        server._initialize_user_scoped_stores = _spy

        server._user_identity_store = UserIdentityStore(
            storage_path=os.path.join(
                self.temp_dir.name, "portable_identity.json"
            )
        )
        server._user_profile_store = UserProfileStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_profile.json"
            )
        )
        server._memory_store = MemoryStore(
            storage_path=os.path.join(self.temp_dir.name, "user_memory.json")
        )
        server._growth_ledger_store = GrowthLedgerStore(
            storage_path=os.path.join(
                self.temp_dir.name, "growth_ledger.json"
            )
        )

    def tearDown(self):
        server._initialize_user_scoped_stores = self._original_initialize
        server._user_identity_store = self._original_user_identity_store
        server._user_profile_store = self._original_user_profile_store
        server._memory_store = self._original_memory_store
        server._growth_ledger_store = self._original_growth_ledger_store
        self.temp_dir.cleanup()

    def test_bare_testclient_does_not_run_startup(self):
        client = TestClient(server.app)
        client.get("/health")
        self.assertEqual(self.calls, [])

    def test_context_manager_testclient_runs_startup_exactly_once(self):
        with TestClient(server.app) as client:
            client.get("/health")

        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
