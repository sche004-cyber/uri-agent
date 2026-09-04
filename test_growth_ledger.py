import json
import os
import tempfile
import unittest

from uri_core.core.growth_ledger import (
    GrowthEvent,
    GrowthLedgerStore,
    GrowthLedgerValidationError,
    compute_level,
    compute_summary,
)


class GrowthLedgerStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(
            self.temp_dir.name, "growth_ledger.json"
        )
        self.store = GrowthLedgerStore(storage_path=self.storage_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_event_creates_and_persists(self):
        event = self.store.record_event("memory_recorded")

        self.assertIsInstance(event, GrowthEvent)
        self.assertEqual(event.event_type, "memory_recorded")
        self.assertEqual(event.xp_delta, 10)
        self.assertTrue(os.path.exists(self.storage_path))

    def test_unknown_event_type_awards_zero_xp_not_an_error(self):
        event = self.store.record_event("something_new")

        self.assertEqual(event.xp_delta, 0)

    def test_events_persist_across_separate_store_instances(self):
        self.store.record_event("memory_recorded")

        reloaded = GrowthLedgerStore(
            storage_path=self.storage_path
        ).list_all()

        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].event_type, "memory_recorded")

    def test_events_accumulate_append_only(self):
        self.store.record_event("memory_recorded")
        self.store.record_event("profile_updated")
        self.store.record_event("memory_recorded")

        self.assertEqual(len(self.store.list_all()), 3)

    def test_record_event_rejects_credential_shaped_metadata_value(self):
        with self.assertRaises(GrowthLedgerValidationError):
            self.store.record_event(
                "memory_recorded",
                metadata={"note": "sk-obviouslysecretvalue"},
            )

    def test_record_event_rejects_credential_shaped_metadata_key(self):
        with self.assertRaises(GrowthLedgerValidationError):
            self.store.record_event(
                "memory_recorded", metadata={"api_key": "x"}
            )

    def test_corrupted_file_degrades_to_an_empty_list(self):
        with open(self.storage_path, "w", encoding="utf-8") as file:
            file.write("{ not valid json")

        self.assertEqual(self.store.list_all(), [])

    def test_summary_reflects_recorded_events(self):
        self.store.record_event("memory_recorded")
        self.store.record_event("memory_recorded")
        self.store.record_event("profile_updated")

        summary = self.store.summary()

        self.assertEqual(summary["total_xp"], 25)
        self.assertEqual(summary["event_count"], 3)


class ComputeLevelTests(unittest.TestCase):

    def test_zero_xp_is_level_one(self):
        self.assertEqual(compute_level(0), 1)

    def test_negative_xp_is_still_level_one(self):
        self.assertEqual(compute_level(-50), 1)

    def test_level_increases_every_100_xp(self):
        self.assertEqual(compute_level(99), 1)
        self.assertEqual(compute_level(100), 2)
        self.assertEqual(compute_level(250), 3)


class ComputeSummaryTests(unittest.TestCase):

    def _event(self, event_type, xp_delta, timestamp="t"):
        return GrowthEvent(
            event_id="e",
            event_type=event_type,
            xp_delta=xp_delta,
            timestamp=timestamp,
        )

    def test_empty_history_produces_zeroed_summary(self):
        summary = compute_summary([])

        self.assertEqual(summary["total_xp"], 0)
        self.assertEqual(summary["level"], 1)
        self.assertEqual(summary["achievements"], [])
        self.assertEqual(summary["event_count"], 0)

    def test_total_xp_is_the_sum_of_deltas_not_a_stored_counter(self):
        events = [
            self._event("memory_recorded", 10),
            self._event("memory_recorded", 10),
            self._event("profile_updated", 5),
        ]

        summary = compute_summary(events)

        self.assertEqual(summary["total_xp"], 25)
        self.assertEqual(
            summary["counts_by_type"],
            {"memory_recorded": 2, "profile_updated": 1},
        )

    def test_first_memory_achievement_unlocks_at_one(self):
        summary = compute_summary(
            [self._event("memory_recorded", 10)]
        )

        self.assertIn("first_memory", summary["achievements"])
        self.assertNotIn(
            "getting_to_know_you", summary["achievements"]
        )

    def test_getting_to_know_you_achievement_unlocks_at_five(self):
        events = [
            self._event("memory_recorded", 10) for _ in range(5)
        ]

        summary = compute_summary(events)

        self.assertIn("first_memory", summary["achievements"])
        self.assertIn(
            "getting_to_know_you", summary["achievements"]
        )

    def test_profile_configured_achievement(self):
        summary = compute_summary(
            [self._event("profile_updated", 5)]
        )

        self.assertIn("profile_configured", summary["achievements"])

    def test_recent_is_most_recent_first_and_respects_limit(self):
        events = [
            self._event("memory_recorded", 10, timestamp="2026-01-01"),
            self._event("memory_recorded", 10, timestamp="2026-01-03"),
            self._event("memory_recorded", 10, timestamp="2026-01-02"),
        ]

        summary = compute_summary(events, recent_limit=2)

        self.assertEqual(len(summary["recent"]), 2)
        self.assertEqual(summary["recent"][0]["timestamp"], "2026-01-03")
        self.assertEqual(summary["recent"][1]["timestamp"], "2026-01-02")

    def test_achievements_are_recomputed_not_stored(self):
        # Two independent summary calls over the same growing history
        # must agree - achievements are derived fresh every time, not
        # a flag set once and persisted.
        one_event = [self._event("memory_recorded", 10)]
        five_events = [
            self._event("memory_recorded", 10) for _ in range(5)
        ]

        self.assertNotIn(
            "getting_to_know_you",
            compute_summary(one_event)["achievements"],
        )
        self.assertIn(
            "getting_to_know_you",
            compute_summary(five_events)["achievements"],
        )


if __name__ == "__main__":
    unittest.main()
