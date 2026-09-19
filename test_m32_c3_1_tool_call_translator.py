"""M32 Batch C, C3.1: tool-call -> Decision Contract translator - unit tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from uri_core.core.model_providers.base import ToolCall
from uri_core.core.tool_call_translator import translate_tool_call, translate_tool_calls
from uri_core.core.decision_engine import DecisionOutcome
from uri_core.core.decision_gates import GateResult
from uri_core.core.native_tool_loop import execute_translated_batch

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

    def test_offered_tool_without_a_capability_mapping_fails_closed(self):
        call = ToolCall(id="c1", name="mapped_nowhere", arguments={})
        with patch("uri_core.core.tool_call_translator.tool_name_to_contract_target", return_value=None):
            result = translate_tool_call(call, offered_tool_names=["mapped_nowhere"], principal=None)
        self.assertFalse(result["ok"])
        self.assertNotIn("contract", result)

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

    def test_cross_capability_batch_becomes_heterogeneous_contract(self):
        calls = [
            ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"}),
            ToolCall(id="c2", name="remember_fact", arguments={"request_text": "x"}),
        ]
        result = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)

        self.assertTrue(result["ok"])
        self.assertEqual(result["contract"]["mode"], "multi_action")
        self.assertEqual(result["contract"]["capability"], "Gmail")
        self.assertEqual(
            result["contract"]["actions"],
            [
                {"name": "search_messages", "inputs": {"query": "invoice"}, "capability": "Gmail"},
                {"name": "remember_fact", "inputs": {"request_text": "x"}, "capability": "remember_fact"},
            ],
        )

    def test_batch_with_one_unknown_call_is_refused_entirely(self):
        calls = [
            ToolCall(id="c1", name="remember_fact", arguments={"request_text": "x"}),
            ToolCall(id="c2", name="not_a_real_tool", arguments={}),
        ]
        result = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)

        self.assertFalse(result["ok"])

    def test_mixed_contract_reaches_aggregate_gate_and_canonical_execution(self):
        calls = [
            ToolCall(id="c1", name="gmail_search_messages", arguments={"query": "invoice"}),
            ToolCall(id="c2", name="remember_fact", arguments={"request_text": "x"}),
        ]
        translated = translate_tool_calls(calls, offered_tool_names=OFFERED, principal=None)
        self.assertTrue(translated["ok"])
        with patch("uri_core.core.native_tool_loop.evaluate_gates", return_value=GateResult(outcome="READY", capability_id="Gmail")) as gate, \
             patch("uri_core.core.native_tool_loop._execute_canonical", return_value={"status": "success", "execution": {"status": "success"}, "response": {}}) as execute:
            results = execute_translated_batch(
                translated["contract"], results_meta=translated["results"], orchestrator=object(),
                session_id="s1", user_text="x", principal=None, directory=object(), turn_state_data={},
                capability_registry=object(), executed_signatures=set(),
            )
        gate.assert_called_once()
        self.assertIsInstance(gate.call_args.args[0], DecisionOutcome)
        self.assertEqual(gate.call_args.args[0].contract, translated["contract"])
        execute.assert_called_once()
        self.assertEqual([result["capability"] for result in results], ["Gmail", "remember_fact"])

    def test_empty_batch_is_refused(self):
        result = translate_tool_calls([], offered_tool_names=OFFERED, principal=None)
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
