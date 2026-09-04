import unittest

from uri_core.core.facts import Fact
from uri_core.core.personalization_context import (
    MAX_MEMORY_ENTRIES,
    build_personalization_context,
)
from uri_core.core.user_memory import MemoryEntry
from uri_core.core.user_profile import UserProfile


def _memory(
    consent="user_provided",
    category="interest",
    value="badminton",
    updated_at="2026-01-01T00:00:00+00:00",
):
    return MemoryEntry(
        memory_id="m1",
        category=category,
        consent=consent,
        fact=Fact(name=category, value=value, status="CONFIRMED"),
        created_at=updated_at,
        updated_at=updated_at,
    )


class PersonalizationContextTests(unittest.TestCase):

    def test_none_profile_and_empty_memory_produces_empty_context(self):
        context = build_personalization_context(None, [])

        self.assertIsNone(context["communication_style"])
        self.assertIsNone(context["autonomy_level"])
        self.assertEqual(context["focus_areas"], [])
        self.assertEqual(context["memory"], [])

    def test_profile_fields_are_included(self):
        profile = UserProfile(
            communication_style="formal",
            autonomy_level="askEveryTime",
            focus_areas=["insurance", "student records"],
        )

        context = build_personalization_context(profile, [])

        self.assertEqual(context["communication_style"], "formal")
        self.assertEqual(context["autonomy_level"], "askEveryTime")
        self.assertEqual(
            context["focus_areas"], ["insurance", "student records"]
        )

    def test_user_provided_memory_is_included(self):
        context = build_personalization_context(
            None, [_memory(consent="user_provided")]
        )

        self.assertEqual(len(context["memory"]), 1)
        self.assertEqual(context["memory"][0]["content"], "badminton")

    def test_user_confirmed_memory_is_included(self):
        context = build_personalization_context(
            None, [_memory(consent="user_confirmed")]
        )

        self.assertEqual(len(context["memory"]), 1)

    def test_pending_confirmation_memory_is_excluded(self):
        context = build_personalization_context(
            None, [_memory(consent="pending_confirmation")]
        )

        self.assertEqual(context["memory"], [])

    def test_memory_is_capped_at_max_entries(self):
        entries = [
            _memory(
                value=f"fact-{i}",
                updated_at=f"2026-01-{i + 1:02d}T00:00:00+00:00",
            )
            for i in range(MAX_MEMORY_ENTRIES + 5)
        ]

        context = build_personalization_context(None, entries)

        self.assertEqual(len(context["memory"]), MAX_MEMORY_ENTRIES)

    def test_most_recently_updated_memory_is_kept_when_capped(self):
        entries = [
            _memory(
                value=f"fact-{i}",
                updated_at=f"2026-01-{i + 1:02d}T00:00:00+00:00",
            )
            for i in range(MAX_MEMORY_ENTRIES + 1)
        ]

        context = build_personalization_context(None, entries)

        contents = {m["content"] for m in context["memory"]}
        self.assertNotIn("fact-0", contents)  # the oldest, dropped
        self.assertIn(
            f"fact-{MAX_MEMORY_ENTRIES}", contents
        )  # the newest, kept

    def test_growth_or_xp_is_never_part_of_the_context(self):
        # There is no growth/XP parameter to this function at all -
        # this test documents that exclusion is structural, not a
        # runtime check.
        import inspect

        signature = inspect.signature(build_personalization_context)
        self.assertNotIn("growth", signature.parameters)
        self.assertNotIn("xp", signature.parameters)

    def test_credential_shaped_memory_content_is_dropped_defensively(
        self,
    ):
        context = build_personalization_context(
            None, [_memory(value="sk-obviouslysecretvalue")]
        )

        self.assertEqual(context["memory"], [])

    def test_result_is_json_shaped_data_not_free_text(self):
        profile = UserProfile(
            communication_style="concise", autonomy_level="askEveryTime"
        )
        context = build_personalization_context(profile, [])

        self.assertIsInstance(context, dict)
        for key in (
            "communication_style",
            "autonomy_level",
            "focus_areas",
            "memory",
        ):
            self.assertIn(key, context)


if __name__ == "__main__":
    unittest.main()
