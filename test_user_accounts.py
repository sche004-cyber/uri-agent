"""Unit tests for uri_core.core.user_accounts (Prototype 1)."""

import os
import tempfile
import unittest

from uri_core.core.user_accounts import (
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


if __name__ == "__main__":
    unittest.main()
