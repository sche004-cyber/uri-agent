"""M32 Batch C, C3.1: tool-call -> Decision Contract translator - unit tests."""

import unittest
from types import SimpleNamespace

from uri_core.core.model_providers.base import ToolCall
from uri_core.core.tool_call_translator import translate_tool_call, translate_tool_calls

OFFERED = [
    "gmail_search_messages",
    "gmail_create_draft",
    "gmail_list_labels",
    "remember_fact",
    "read_attached_file",
]


class TranslateSingleCallTests(unittest.TestCase):
    def test_legacy_tool_call_becomes_single_action_contract(self):
        call = ToolCall(id="c1", name="remember_fact", arguments={"request_text": "I work at NIT Sikkim."})
        result = translate_tool_call(call, offered_tool_names=OFFERED, principal=None)

        self.assertTrue(result["ok"])
        self.assertEqual(result["contract"]["mode"], "single_action")
        self.assertEqual(result["contract"]["capability"], "remember_fact")
        self.assertEqual(result["contract"]["actions"], [{"name": "remember_fact", "inputs": {"request_text": "I work at NIT Sikkim."}}])

    def test_gmail_prefixed_call_becomes_gmail_capability_contract(self):
        call = ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"})
        result = translate_tool_call(call, offered_tool_names=OFFERED, principal=None)

        self.assertTrue(result["ok"])
        self.assertEqual(result["contract"]["capability"], "Gmail")
        self.assertEqual(result["contract"]["actions"], [{"name": "search_messages", "inputs": {"query": "invoice"}}])

    def test_unknown_tool_name_never_dispatches(self):
        call = ToolCall(id="c1", name="delete_everything", arguments={})
        result = translate_tool_call(call, offered_tool_names=OFFERED, principal=None)

        self.assertFalse(result["ok"])
        self.assertNotIn("contract", result)
        self.assertIn("error", result)

    def test_tool_not_offered_this_turn_is_rejected_even_if_name_is_real(self):
        # gmail_create_draft IS a real, resolvable tool name in general,
        # but if it wasn't offered THIS call, it must not be trusted.
        call = ToolCall(id="c1", name="gmail_create_draft", arguments={"to": "a@b.com"})
        result = translate_tool_call(call, offered_tool_names=["remember_fact"], principal=None)

        self.assertFalse(result["ok"])
        self.assertIn("not offered", result["error"])

    def test_principal_is_never_read_from_tool_call_arguments(self):
        # SR-5: an attempt to smuggle a principal through arguments must
        # be ignored - the real principal always comes from the caller's
        # own kwarg, never from the model-controlled payload.
        smuggled_principal = SimpleNamespace(user_id="attacker-controlled")
        real_principal = SimpleNamespace(user_id="real-authenticated-user")
        call = ToolCall(id="c1", name="remember_fact", arguments={"request_text": "x", "principal": smuggled_principal})

        result = translate_tool_call(call, offered_tool_names=OFFERED, principal=real_principal)

        self.assertIs(result["principal"], real_principal)
        self.assertIsNot(result["principal"], smuggled_principal)
        # The smuggled "principal" key stays in `inputs` (inert - it is
        # never read as authority by anything downstream, exactly like any
        # other unrecognized model-supplied field), but the real
        # authorization principal used by the caller is untouched.
        self.assertEqual(result["contract"]["actions"][0]["inputs"]["principal"], smuggled_principal)


class TranslateBatchTests(unittest.TestCase):
    def test_single_call_batch_matches_single_translation(self):
        calls = [ToolCall(id="c1", name="remember_fact", arguments={"request_text": "x"})]
        result = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)

        self.assertTrue(result["ok"])
        self.assertEqual(result["contract"]["mode"], "single_action")

    def test_same_capability_multi_call_batch_becomes_multi_action(self):
        calls = [
            ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"}),
            ToolCall(id="c2", name="gmail_list_labels", arguments={}),
        ]
        result = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)

        self.assertTrue(result["ok"])
        self.assertEqual(result["contract"]["mode"], "multi_action")
        self.assertEqual(result["contract"]["capability"], "Gmail")
        self.assertEqual(len(result["contract"]["actions"]), 2)

    def test_cross_capability_batch_is_refused_not_partially_dispatched(self):
        calls = [
            ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"}),
            ToolCall(id="c2", name="remember_fact", arguments={"request_text": "x"}),
        ]
        result = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)

        self.assertFalse(result["ok"])
        self.assertNotIn("contract", result)
        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(all(not r["ok"] for r in result["results"]))

    def test_batch_with_one_unknown_call_is_refused_entirely(self):
        calls = [
            ToolCall(id="c1", name="remember_fact", arguments={"request_text": "x"}),
            ToolCall(id="c2", name="not_a_real_tool", arguments={}),
        ]
        result = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)

        self.assertFalse(result["ok"])

    def test_empty_batch_is_refused(self):
        result = translate_tool_calls([], offered_tool_names=OFFERED, principal=None)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
