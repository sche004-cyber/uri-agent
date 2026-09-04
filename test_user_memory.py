import json
import os
import tempfile
import unittest

from uri_core.core.user_memory import (
    MemoryEntry,
    MemoryStore,
    MemoryValidationError,
    is_eligible_for_personalization,
)
from uri_core.core.facts import Fact


class MemoryStoreAddTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "user_memory.json"
        )
        self.store = MemoryStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_creates_a_user_provided_entry(self):
        entry = self.store.add(
            category="preference", content="prefers terse office notes"
        )

        self.assertIsInstance(entry, MemoryEntry)
        self.assertTrue(entry.memory_id)
        self.assertEqual(entry.category, "preference")
        self.assertEqual(entry.consent, "user_provided")
        self.assertEqual(entry.fact.value, "prefers terse office notes")
        self.assertEqual(entry.fact.status, "CONFIRMED")
        self.assertTrue(os.path.exists(self.storage_path))

    def test_add_persists_across_separate_store_instances(self):
        self.store.add(category="interest", content="badminton")

        reloaded = MemoryStore(
            storage_path=self.storage_path
        ).list_all()

        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].fact.value, "badminton")

    def test_add_stores_confidence_and_notes(self):
        entry = self.store.add(
            category="interaction_pattern",
            content="asks for a summary before full detail",
            confidence=0.6,
            notes="observed across three conversations",
        )

        self.assertEqual(entry.fact.confidence, 0.6)
        self.assertEqual(
            entry.fact.notes, "observed across three conversations"
        )

    def test_add_rejects_invalid_category(self):
        with self.assertRaises(MemoryValidationError):
            self.store.add(category="not_a_real_category", content="x")

    def test_add_rejects_empty_content(self):
        with self.assertRaises(MemoryValidationError):
            self.store.add(category="preference", content="")

    def test_add_rejects_credential_shaped_content(self):
        with self.assertRaises(MemoryValidationError):
            self.store.add(
                category="other",
                content="sk-obviouslysecretvalue",
            )

    def test_add_rejects_oversized_content(self):
        with self.assertRaises(MemoryValidationError):
            self.store.add(category="other", content="x" * 501)

    def test_add_rejects_invalid_confidence(self):
        with self.assertRaises(ValueError):
            self.store.add(
                category="other", content="x", confidence=1.5
            )

    def test_multiple_entries_get_distinct_ids(self):
        first = self.store.add(category="preference", content="a")
        second = self.store.add(category="preference", content="b")

        self.assertNotEqual(first.memory_id, second.memory_id)
        self.assertEqual(len(self.store.list_all()), 2)

    def test_add_always_marks_the_entry_user_stated_not_inferred(self):
        # The only write path in this milestone is the user explicitly
        # asking URI to remember something - there is no code path
        # yet for URI to record its own inference, and add() must
        # never produce anything that looks like one.
        entry = self.store.add(category="preference", content="a")

        self.assertEqual(entry.consent, "user_provided")
        self.assertEqual(entry.fact.source, "user_explicit")
        self.assertNotEqual(entry.consent, "pending_confirmation")
        self.assertNotEqual(entry.fact.source, "conversation_inferred")


class PersonalizationEligibilityTests(unittest.TestCase):
    """Direct, tested enforcement of the rule a future personalization
    consumer must follow: only user_provided/user_confirmed memories
    are ever eligible - a pending_confirmation entry (not created by
    anything in this milestone, but a real value the schema allows)
    must never be treated as established."""

    def _entry(self, consent):
        return MemoryEntry(
            memory_id="m1",
            category="preference",
            consent=consent,
            fact=Fact(name="preference", value="x"),
            created_at="t",
            updated_at="t",
        )

    def test_user_provided_is_eligible(self):
        self.assertTrue(
            is_eligible_for_personalization(
                self._entry("user_provided")
            )
        )

    def test_user_confirmed_is_eligible(self):
        self.assertTrue(
            is_eligible_for_personalization(
                self._entry("user_confirmed")
            )
        )

    def test_pending_confirmation_is_not_eligible(self):
        self.assertFalse(
            is_eligible_for_personalization(
                self._entry("pending_confirmation")
            )
        )


class MemoryStoreReadUpdateDeleteTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "user_memory.json"
        )
        self.store = MemoryStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_returns_none_for_unknown_id(self):
        self.assertIsNone(self.store.get("does-not-exist"))

    def test_get_returns_the_matching_entry(self):
        created = self.store.add(category="preference", content="a")

        fetched = self.store.get(created.memory_id)

        self.assertEqual(fetched.memory_id, created.memory_id)
        self.assertEqual(fetched.fact.value, "a")

    def test_update_replaces_content_and_bumps_updated_at(self):
        created = self.store.add(category="preference", content="a")

        updated = self.store.update(
            created.memory_id, category="interest", content="b"
        )

        self.assertEqual(updated.category, "interest")
        self.assertEqual(updated.fact.value, "b")
        self.assertEqual(updated.created_at, created.created_at)
        self.assertNotEqual(updated.updated_at, created.updated_at)

    def test_update_preserves_consent(self):
        created = self.store.add(category="preference", content="a")

        updated = self.store.update(
            created.memory_id, category="preference", content="b"
        )

        self.assertEqual(updated.consent, "user_provided")

    def test_update_returns_none_for_unknown_id(self):
        result = self.store.update(
            "does-not-exist", category="preference", content="x"
        )

        self.assertIsNone(result)

    def test_update_rejects_credential_shaped_content(self):
        created = self.store.add(category="preference", content="a")

        with self.assertRaises(MemoryValidationError):
            self.store.update(
                created.memory_id,
                category="preference",
                content="AIzaSomeFakeGoogleKeyShapedString",
            )

    def test_delete_removes_the_entry_and_returns_true(self):
        created = self.store.add(category="preference", content="a")

        result = self.store.delete(created.memory_id)

        self.assertTrue(result)
        self.assertIsNone(self.store.get(created.memory_id))
        self.assertEqual(self.store.list_all(), [])

    def test_delete_is_real_not_a_soft_delete(self):
        created = self.store.add(category="preference", content="a")
        self.store.delete(created.memory_id)

        with open(self.storage_path, "r", encoding="utf-8") as file:
            raw = json.load(file)

        self.assertEqual(raw["memories"], [])

    def test_delete_returns_false_for_unknown_id(self):
        self.assertFalse(self.store.delete("does-not-exist"))

    def test_corrupted_file_degrades_to_an_empty_list(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("{ not valid json")

        self.assertEqual(self.store.list_all(), [])


if __name__ == "__main__":
    unittest.main()
