"""Regression tests for condense_known_gaps - the fix that bounds
the known_gaps evidence handed to the response-drafting model to a
small, fixed-size structured summary, so the model has structurally
too little material to free-associate troubleshooting advice from,
rather than relying only on a prompt instruction not to."""

import unittest

from uri_core.core.response_drafting import (
    MAX_GAP_ENTRIES,
    MAX_GAP_FIELD_LENGTH,
    condense_known_gaps,
)


class CondenseKnownGapsTests(unittest.TestCase):

    def test_long_description_and_limitations_are_truncated(self):
        long_text = "x" * 600
        gaps = [
            {
                "id": "pc_system_optimization",
                "status": "planned",
                "description": long_text,
                "limitations": long_text,
            }
        ]

        condensed = condense_known_gaps(gaps)

        self.assertEqual(len(condensed[0]["description"]), MAX_GAP_FIELD_LENGTH + 1)
        self.assertEqual(len(condensed[0]["limitations"]), MAX_GAP_FIELD_LENGTH + 1)
        self.assertTrue(condensed[0]["description"].endswith("…"))

    def test_short_fields_are_left_unchanged(self):
        gaps = [
            {
                "id": "pc_system_optimization",
                "status": "planned",
                "description": "Optimize PC performance.",
                "limitations": "No execution adapter yet.",
            }
        ]

        condensed = condense_known_gaps(gaps)

        self.assertEqual(condensed[0]["description"], "Optimize PC performance.")
        self.assertEqual(condensed[0]["limitations"], "No execution adapter yet.")

    def test_entry_count_is_capped(self):
        gaps = [
            {"id": f"gap_{i}", "status": "planned", "description": "d", "limitations": "l"}
            for i in range(10)
        ]

        condensed = condense_known_gaps(gaps)

        self.assertEqual(len(condensed), MAX_GAP_ENTRIES)

    def test_id_and_status_are_preserved_verbatim(self):
        gaps = [{"id": "pc_system_optimization", "status": "planned", "description": "d", "limitations": "l"}]

        condensed = condense_known_gaps(gaps)

        self.assertEqual(condensed[0]["id"], "pc_system_optimization")
        self.assertEqual(condensed[0]["status"], "planned")

    def test_non_list_input_passes_through_unchanged(self):
        self.assertIsNone(condense_known_gaps(None))
        self.assertEqual(condense_known_gaps("not a list"), "not a list")

    def test_empty_list_stays_empty(self):
        self.assertEqual(condense_known_gaps([]), [])


if __name__ == "__main__":
    unittest.main()
