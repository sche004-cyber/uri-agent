"""M32 Batch C, C3.2: Brain-facing tool schema catalogue - unit tests."""

import unittest

from uri_core.capabilities import MultiActionCapabilityRegistry
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.tool_schema import (
    _RUNTIME_INJECTED_FIELDS,
    build_tool_schemas,
    tool_name_to_contract_target,
)
from test_multi_action_capabilities import FakeGmailService


def _real_schemas():
    return build_tool_schemas(
        capability_registry=CapabilityRegistry(),
        multi_action_registry=MultiActionCapabilityRegistry([GmailCapability(FakeGmailService())]),
    )


class ToolSchemaCatalogueTests(unittest.TestCase):
    def test_every_entry_is_openai_compatible_shape(self):
        for tool in _real_schemas():
            self.assertEqual(tool["type"], "function")
            self.assertIn("name", tool["function"])
            self.assertIn("description", tool["function"])
            parameters = tool["function"]["parameters"]
            self.assertEqual(parameters["type"], "object")
            self.assertIn("properties", parameters)
            self.assertIn("required", parameters)

    def test_suppressed_legacy_gmail_overlaps_are_excluded(self):
        schemas = _real_schemas()
        names = {t["function"]["name"] for t in schemas}
        # 3 of the 4 overlapping legacy ids have names distinct from any
        # Gmail-action-flattened name, so their absence alone proves
        # suppression.
        for suppressed in ("gmail_search", "gmail_find_draft", "drive_search"):
            self.assertNotIn(suppressed, names, f"{suppressed} should be suppressed as a Gmail overlap")
        # The 4th, "gmail_create_draft", collides by name with the Gmail
        # multi-action "create_draft" action (gmail_ + create_draft) -
        # exactly one "gmail_create_draft" entry must exist, and it must
        # be the multi-action one (its description names Gmail's own
        # create_draft wording), never both.
        matches = [t for t in schemas if t["function"]["name"] == "gmail_create_draft"]
        self.assertEqual(len(matches), 1, "gmail_create_draft must appear exactly once")
        self.assertIn("draft", matches[0]["function"]["description"].lower())
        self.assertIn("to", matches[0]["function"]["parameters"]["properties"])  # Gmail action's real param

    def test_gmail_actions_are_flattened_with_prefix(self):
        names = {t["function"]["name"] for t in _real_schemas()}
        self.assertIn("gmail_search_messages", names)
        self.assertIn("gmail_create_draft", names)  # the multi-action "create_draft" action, not the suppressed legacy tool
        self.assertIn("gmail_list_labels", names)

    def test_gmail_search_messages_has_required_query(self):
        tool = next(t for t in _real_schemas() if t["function"]["name"] == "gmail_search_messages")
        self.assertIn("query", tool["function"]["parameters"]["properties"])
        self.assertIn("query", tool["function"]["parameters"]["required"])

    def test_runtime_injected_fields_never_appear_in_any_schema(self):
        for tool in _real_schemas():
            properties = tool["function"]["parameters"]["properties"]
            for injected in _RUNTIME_INJECTED_FIELDS:
                self.assertNotIn(injected, properties, f"{injected} leaked into {tool['function']['name']}'s schema")

    def test_read_attached_file_is_a_real_zero_argument_tool(self):
        tool = next(t for t in _real_schemas() if t["function"]["name"] == "read_attached_file")
        self.assertEqual(tool["function"]["parameters"]["properties"], {})
        self.assertEqual(tool["function"]["parameters"]["required"], [])

    def test_no_duplicate_tool_names(self):
        names = [t["function"]["name"] for t in _real_schemas()]
        self.assertEqual(len(names), len(set(names)), "duplicate tool name in catalogue")

    def test_remember_fact_present_with_request_text(self):
        tool = next(t for t in _real_schemas() if t["function"]["name"] == "remember_fact")
        self.assertIn("request_text", tool["function"]["parameters"]["required"])


class ToolNameToContractTargetTests(unittest.TestCase):
    def test_legacy_tool_name_maps_to_itself(self):
        self.assertEqual(
            tool_name_to_contract_target("remember_fact"),
            {"capability": "remember_fact", "action": "remember_fact"},
        )

    def test_gmail_prefixed_name_maps_to_gmail_action(self):
        self.assertEqual(
            tool_name_to_contract_target("gmail_search_messages"),
            {"capability": "Gmail", "action": "search_messages"},
        )

    def test_gmail_create_draft_maps_to_the_multi_action_create_draft_action(self):
        self.assertEqual(
            tool_name_to_contract_target("gmail_create_draft"),
            {"capability": "Gmail", "action": "create_draft"},
        )

    def test_unrecognized_name_returns_none(self):
        self.assertIsNone(tool_name_to_contract_target("delete_the_entire_mailbox"))

    def test_bare_gmail_prefix_with_no_action_returns_none(self):
        self.assertIsNone(tool_name_to_contract_target("gmail_"))


if __name__ == "__main__":
    unittest.main()
