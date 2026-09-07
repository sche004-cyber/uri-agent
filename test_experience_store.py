"""Item 7 of the URI architecture spec: structured, retrievable
experience/history records, distinct from user profile/personal
memory/temporary session state - see experience_store.py's module
docstring for the exact separation this mirrors from user_memory.py.
"""

import json
import os
import tempfile
import unittest

from uri_core.core.experience_store import (
    ExperienceRecord,
    ExperienceStore,
    ExperienceValidationError,
    summarize_for_query_context,
)


class ExperienceStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "experience.json"
        )
        self.store = ExperienceStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_store_returns_no_records(self):
        self.assertEqual(self.store.list_all(), [])
        self.assertEqual(self.store.recent(), [])

    def test_add_persists_a_record_across_a_new_store_instance(self):
        self.store.add(
            category="successful_approach",
            intent="renew student insurance",
            summary="extract_student_records then draft a note works.",
            actions=["extract_student_records", "draft_institutional_note"],
            results="success",
        )

        reloaded = ExperienceStore(storage_path=self.storage_path)
        records = reloaded.list_all()

        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], ExperienceRecord)
        self.assertEqual(records[0].category, "successful_approach")
        self.assertEqual(records[0].intent, "renew student insurance")
        self.assertEqual(
            records[0].actions,
            ["extract_student_records", "draft_institutional_note"],
        )

    def test_every_retention_category_can_be_persisted(self):
        for category in (
            "successful_approach",
            "user_preference",
            "reference_pattern",
            "other",
        ):
            self.store.add(category=category, summary=f"{category} summary")

        self.assertEqual(len(self.store.list_all()), 4)

    def test_invalid_category_is_rejected(self):
        with self.assertRaises(ExperienceValidationError):
            self.store.add(category="not_a_real_category", summary="x")

    def test_empty_summary_is_rejected(self):
        with self.assertRaises(ExperienceValidationError):
            self.store.add(category="other", summary="")

    def test_credential_looking_content_is_rejected(self):
        with self.assertRaises(ExperienceValidationError):
            self.store.add(
                category="other",
                summary="sk-abcdef1234567890abcdef1234567890",
            )

    def test_recent_returns_most_recently_added_first_and_is_bounded(self):
        for index in range(7):
            self.store.add(category="other", summary=f"summary {index}")

        recent = self.store.recent(limit=3)

        self.assertEqual(len(recent), 3)
        self.assertEqual(
            [record.summary for record in recent],
            ["summary 6", "summary 5", "summary 4"],
        )

    def test_corrupted_file_degrades_to_empty_rather_than_raising(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("not valid json{{{")

        self.assertEqual(self.store.list_all(), [])

    def test_storage_directory_is_created_when_missing(self):
        nested_path = os.path.join(
            self.temp_dir.name, "nested", "dir", "experience.json"
        )
        store = ExperienceStore(storage_path=nested_path)

        store.add(category="other", summary="nested write works")

        self.assertTrue(os.path.exists(nested_path))


class SummarizeForQueryContextTests(unittest.TestCase):

    def test_records_are_shaped_into_small_labeled_dicts(self):
        store = ExperienceStore(
            storage_path=os.path.join(
                tempfile.mkdtemp(), "experience.json"
            )
        )
        store.add(
            category="reference_pattern",
            intent="draft an office order",
            summary="Office orders follow a fixed subject/authority format.",
            unresolved=["confirm the signing authority"],
        )

        summarized = summarize_for_query_context(store.recent())

        self.assertEqual(len(summarized), 1)
        entry = summarized[0]
        self.assertEqual(entry["category"], "reference_pattern")
        self.assertEqual(
            entry["unresolved"], ["confirm the signing authority"]
        )
        self.assertIn("summary", entry)
        self.assertIn("created_at", entry)

    def test_non_record_entries_are_dropped_defensively(self):
        summarized = summarize_for_query_context([None, "not-a-record", 42])
        self.assertEqual(summarized, [])


if __name__ == "__main__":
    unittest.main()
