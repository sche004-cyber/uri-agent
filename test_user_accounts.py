"""Unit tests for uri_core.core.user_accounts (Prototype 1; role/
experience_tier/status added M22.2 - see this module's own docstring)."""

import json
import os
import tempfile
import unittest

from uri_core.core.user_accounts import (
    EXPERIENCE_TIER_ADVANCED,
    EXPERIENCE_TIER_BASIC,
    ROLE_ADMIN,
    ROLE_USER,
    STATUS_ACTIVE,
    UserAccountError,
    UserAccountStore,
    UsernameTakenError,
)


class UserAccountStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = UserAccountStore(
            storage_path=os.path.join(
                self.temp_dir.name, "user_accounts.json"
            )
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_account_returns_a_uuid_shaped_user_id(self):
        account = self.store.create_account("alice", "correct-horse-1")
        # Loosely validated - a real strict UUID check lives in
        # portable_paths.py; this just confirms create_account doesn't
        # hand back something obviously wrong (e.g. the username).
        self.assertNotEqual(account.user_id, "alice")
        self.assertEqual(len(account.user_id), 36)

    def test_password_is_never_stored_in_plaintext(self):
        account = self.store.create_account("bob", "super-secret-pw")

        with open(self.store.storage_path, "r", encoding="utf-8") as file:
            raw_contents = file.read()

        self.assertNotIn("super-secret-pw", raw_contents)
        self.assertNotEqual(account.password_hash, "super-secret-pw")

    def test_two_accounts_never_share_a_salt(self):
        first = self.store.create_account("carol", "carols-password-1")
        second = self.store.create_account("dave", "carols-password-1")

        # Even with the identical password, salts (and therefore
        # hashes) must differ.
        self.assertNotEqual(first.password_salt, second.password_salt)
        self.assertNotEqual(first.password_hash, second.password_hash)

    def test_duplicate_username_is_rejected_case_insensitively(self):
        self.store.create_account("Erin", "erins-password-1")

        with self.assertRaises(UsernameTakenError):
            self.store.create_account("erin", "different-password-1")

    def test_authenticate_succeeds_with_correct_credentials(self):
        account = self.store.create_account("frank", "franks-password-1")

        authenticated = self.store.authenticate(
            "frank", "franks-password-1"
        )

        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.user_id, account.user_id)

    def test_authenticate_fails_with_wrong_password(self):
        self.store.create_account("grace", "graces-password-1")

        self.assertIsNone(
            self.store.authenticate("grace", "wrong-password")
        )

    def test_authenticate_fails_for_unknown_username(self):
        self.assertIsNone(
            self.store.authenticate("nobody", "whatever-password-1")
        )

    def test_authenticate_is_case_insensitive_on_username(self):
        self.store.create_account("Henry", "henrys-password-1")

        self.assertIsNotNone(
            self.store.authenticate("henry", "henrys-password-1")
        )

    def test_username_shape_is_validated(self):
        with self.assertRaises(UserAccountError):
            self.store.create_account("ab", "a-valid-password-1")  # too short

        with self.assertRaises(UserAccountError):
            self.store.create_account(
                "has a space", "a-valid-password-1"
            )

    def test_password_length_is_validated(self):
        with self.assertRaises(UserAccountError):
            self.store.create_account("short-pw-user", "1234567")

    def test_get_by_user_id_round_trips(self):
        account = self.store.create_account("iris", "iris-password-1")

        fetched = self.store.get_by_user_id(account.user_id)

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.username, "iris")

    def test_get_by_user_id_returns_none_for_unknown_id(self):
        self.assertIsNone(self.store.get_by_user_id("does-not-exist"))

    def test_corrupted_file_degrades_to_no_accounts(self):
        with open(self.store.storage_path, "w", encoding="utf-8") as file:
            file.write("{not valid json")

        self.assertIsNone(self.store.authenticate("anyone", "anything1"))
        self.assertIsNone(self.store.get_by_user_id("anyone"))


class RoleExperienceTierAndMigrationTests(unittest.TestCase):
    """M22.2 additions: bootstrap (first account -> ADMIN), the
    experience_tier preference (zero authority, never role), account
    status, and migration of pre-M22.2 (schema_version "1.0") accounts
    that have no role/experience_tier/status fields at all."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "user_accounts.json"
        )
        self.store = UserAccountStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_legacy_accounts(self, accounts: list) -> None:
        """Writes a hand-built, pre-M22.2-shaped accounts file - no
        role/experience_tier/status keys at all, mirroring exactly what
        schema_version "1.0" persisted (see the pre-M22.2 UserAccount
        dataclass)."""
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(
                {"schema_version": "1.0", "accounts": accounts}, file
            )

    # ------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------

    def test_first_account_created_is_admin(self):
        account = self.store.create_account("alice", "alices-password-1")
        self.assertEqual(account.role, ROLE_ADMIN)

    def test_second_account_created_is_ordinary_user(self):
        self.store.create_account("alice", "alices-password-1")
        second = self.store.create_account("bob", "bobs-password-1")
        self.assertEqual(second.role, ROLE_USER)

    def test_only_one_account_is_ever_admin_across_many_signups(self):
        roles = [
            self.store.create_account(
                f"user-{i}", f"a-strong-password-{i}"
            ).role
            for i in range(10)
        ]
        self.assertEqual(roles.count(ROLE_ADMIN), 1)
        self.assertEqual(roles[0], ROLE_ADMIN)
        self.assertEqual(roles.count(ROLE_USER), 9)

    # ------------------------------------------------------------
    # experience_tier / status defaults
    # ------------------------------------------------------------

    def test_new_account_defaults_to_basic_tier_and_active_status(self):
        account = self.store.create_account("carol", "carols-password-1")
        self.assertEqual(account.experience_tier, EXPERIENCE_TIER_BASIC)
        self.assertEqual(account.status, STATUS_ACTIVE)

    def test_set_experience_tier_updates_only_that_field(self):
        account = self.store.create_account("dave", "daves-password-1")

        updated = self.store.set_experience_tier(
            account.user_id, EXPERIENCE_TIER_ADVANCED
        )

        self.assertEqual(updated.experience_tier, EXPERIENCE_TIER_ADVANCED)
        self.assertEqual(updated.role, account.role)
        self.assertEqual(updated.password_hash, account.password_hash)

    def test_set_experience_tier_rejects_an_invalid_value(self):
        account = self.store.create_account("erin", "erins-password-1")

        with self.assertRaises(UserAccountError):
            self.store.set_experience_tier(account.user_id, "SUPER_MODE")

    def test_set_experience_tier_for_unknown_user_returns_none(self):
        self.assertIsNone(
            self.store.set_experience_tier(
                "does-not-exist", EXPERIENCE_TIER_ADVANCED
            )
        )

    def test_set_experience_tier_never_changes_role(self):
        account = self.store.create_account("frank", "franks-password-1")
        self.assertEqual(account.role, ROLE_ADMIN)

        updated = self.store.set_experience_tier(
            account.user_id, EXPERIENCE_TIER_ADVANCED
        )
        self.assertEqual(updated.role, ROLE_ADMIN)

    # ------------------------------------------------------------
    # Migration of pre-M22.2 accounts
    # ------------------------------------------------------------

    def test_legacy_account_with_no_role_field_is_migrated_to_admin(self):
        self._write_legacy_accounts(
            [
                {
                    "user_id": "legacy-user-1",
                    "username": "legacyuser",
                    "password_salt": "aa",
                    "password_hash": "bb",
                    "created_at": "2020-01-01T00:00:00+00:00",
                }
            ]
        )

        account = self.store.get_by_user_id("legacy-user-1")

        self.assertEqual(account.role, ROLE_ADMIN)
        self.assertEqual(account.experience_tier, EXPERIENCE_TIER_BASIC)
        self.assertEqual(account.status, STATUS_ACTIVE)

    def test_earliest_legacy_account_becomes_admin_rest_become_user(self):
        self._write_legacy_accounts(
            [
                {
                    "user_id": "legacy-second",
                    "username": "second",
                    "password_salt": "aa",
                    "password_hash": "bb",
                    "created_at": "2020-06-01T00:00:00+00:00",
                },
                {
                    "user_id": "legacy-first",
                    "username": "first",
                    "password_salt": "cc",
                    "password_hash": "dd",
                    "created_at": "2020-01-01T00:00:00+00:00",
                },
                {
                    "user_id": "legacy-third",
                    "username": "third",
                    "password_salt": "ee",
                    "password_hash": "ff",
                    "created_at": "2020-09-01T00:00:00+00:00",
                },
            ]
        )

        self.assertEqual(
            self.store.get_by_user_id("legacy-first").role, ROLE_ADMIN
        )
        self.assertEqual(
            self.store.get_by_user_id("legacy-second").role, ROLE_USER
        )
        self.assertEqual(
            self.store.get_by_user_id("legacy-third").role, ROLE_USER
        )

    def test_migration_is_idempotent_across_repeated_loads(self):
        self._write_legacy_accounts(
            [
                {
                    "user_id": "legacy-a",
                    "username": "a",
                    "password_salt": "aa",
                    "password_hash": "bb",
                    "created_at": "2020-01-01T00:00:00+00:00",
                },
                {
                    "user_id": "legacy-b",
                    "username": "b",
                    "password_salt": "cc",
                    "password_hash": "dd",
                    "created_at": "2020-02-01T00:00:00+00:00",
                },
            ]
        )

        first_pass = {
            uid: self.store.get_by_user_id(uid).role
            for uid in ("legacy-a", "legacy-b")
        }
        second_pass = {
            uid: self.store.get_by_user_id(uid).role
            for uid in ("legacy-a", "legacy-b")
        }

        self.assertEqual(first_pass, second_pass)
        self.assertEqual(first_pass["legacy-a"], ROLE_ADMIN)
        self.assertEqual(first_pass["legacy-b"], ROLE_USER)

    def test_a_new_signup_after_legacy_migration_never_becomes_a_second_admin(
        self,
    ):
        self._write_legacy_accounts(
            [
                {
                    "user_id": "legacy-only",
                    "username": "legacyonly",
                    "password_salt": "aa",
                    "password_hash": "bb",
                    "created_at": "2020-01-01T00:00:00+00:00",
                }
            ]
        )
        # The legacy account is migrated to ADMIN the moment anything
        # reads it (see _load()) - a brand-new signup afterward must
        # see that and become USER, never a second ADMIN.
        new_account = self.store.create_account(
            "freshuser", "freshusers-password-1"
        )

        self.assertEqual(new_account.role, ROLE_USER)
        self.assertEqual(
            self.store.get_by_user_id("legacy-only").role, ROLE_ADMIN
        )

    def test_account_that_already_has_a_persisted_role_is_never_recomputed(
        self,
    ):
        # A record that already has an explicit role (even one that
        # looks like it could be "reconsidered") must be respected
        # as-is, not re-migrated - only records with NO role key at
        # all are eligible for the earliest-wins computation.
        self._write_legacy_accounts(
            [
                {
                    "user_id": "already-user",
                    "username": "alreadyuser",
                    "password_salt": "aa",
                    "password_hash": "bb",
                    "created_at": "2019-01-01T00:00:00+00:00",
                    "role": ROLE_USER,
                },
                {
                    "user_id": "legacy-unassigned",
                    "username": "unassigned",
                    "password_salt": "cc",
                    "password_hash": "dd",
                    "created_at": "2020-01-01T00:00:00+00:00",
                },
            ]
        )

        self.assertEqual(
            self.store.get_by_user_id("already-user").role, ROLE_USER
        )
        self.assertEqual(
            self.store.get_by_user_id("legacy-unassigned").role,
            ROLE_ADMIN,
        )


if __name__ == "__main__":
    unittest.main()
