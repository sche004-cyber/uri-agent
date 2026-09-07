import json
import os
import tempfile
import unittest

from uri_core.core.model_reasoning_gateway import (
    ModelReasoningGateway
)


class ModelReasoningGatewayTests(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.policy_path = os.path.join(
            self.temp_dir.name,
            "policy.md"
        )

        self.soul_path = os.path.join(
            self.temp_dir.name,
            "soul.md"
        )

        self.registry_path = os.path.join(
            self.temp_dir.name,
            "registry.json"
        )

        with open(
            self.policy_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "URI test policy. Never execute model proposals directly."
            )

        with open(
            self.soul_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "URI test soul. A grounded, loyal companion."
            )

        with open(
            self.registry_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "active_tools": {
                        "draft_institutional_note": {
                            "description":
                                "Draft an institutional note."
                        },
                        "extract_student_records": {
                            "description":
                                "Extract student records."
                        }
                    }
                },
                file
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def gateway(
        self,
        model_callable=None
    ):

        return ModelReasoningGateway(
            policy_path=self.policy_path,
            soul_path=self.soul_path,
            registry_path=self.registry_path,
            model_callable=model_callable
        )

    def test_policy_and_capabilities_are_loaded(self):

        gateway = self.gateway()

        request = (
            gateway.build_reasoning_request(
                "Prepare a note."
            )
        )

        self.assertIn(
            "Never execute",
            request["system_policy"]
        )

        names = {
            item["name"]
            for item
            in request["available_capabilities"]
        }

        self.assertEqual(
            names,
            {
                "draft_institutional_note",
                "extract_student_records"
            }
        )

    def test_load_soul_reads_the_soul_file_independently_of_policy(self):
        # gateway.load_soul() itself is a real, independent load path
        # (see model_reasoning_gateway.py) - proven here directly.
        # It is deliberately NOT added to build_reasoning_request's
        # structured-JSON payload: live testing against a real model
        # showed unconditionally adding soul.md text to every
        # reasoning/proposal call increased how often the model
        # returned an unparseable response, the same prompt-bulk
        # sensitivity already documented for system_policy - soul
        # reaches the Brain instead via query_context (drafting/
        # narrative calls), not this narrow structured-proposal path.
        # See orchestrator.py's _run_model_reasoning for that decision.
        gateway = self.gateway()

        self.assertIn("grounded, loyal companion", gateway.load_soul())

        request = gateway.build_reasoning_request("Prepare a note.")

        self.assertNotIn("grounded, loyal companion", request["system_policy"])
        self.assertNotIn("system_soul", request)

    def test_missing_soul_file_degrades_to_empty_string(self):

        gateway = ModelReasoningGateway(
            policy_path=self.policy_path,
            soul_path=os.path.join(self.temp_dir.name, "missing_soul.md"),
            registry_path=self.registry_path,
        )

        self.assertEqual(gateway.load_soul(), "")

    def test_model_is_not_required_to_be_configured(self):

        result = (
            self.gateway().reason(
                "Do something new."
            )
        )

        self.assertEqual(
            result["status"],
            "model_not_configured"
        )

        self.assertIsNone(
            result["proposal"]
        )

    def test_valid_model_proposal_is_accepted(self):

        proposal = {
            "intent": {
                "task_type":
                    "document drafting",
                "goal":
                    "Prepare an institutional note"
            },
            "facts": [
                {
                    "name":
                        "subject",
                    "value":
                        "Insurance renewal",
                    "status":
                        "CONFIRMED"
                }
            ],
            "workflow": {
                "goal":
                    "Prepare the note",
                "steps": [
                    {
                        "step_id":
                            "step_1",
                        "capability":
                            "extract_student_records",
                        "depends_on": []
                    },
                    {
                        "step_id":
                            "step_2",
                        "capability":
                            "draft_institutional_note",
                        "depends_on":
                            ["step_1"]
                    }
                ]
            },
            "clarification":
                None,
            "action":
                None
        }

        def fake_model(_request):
            return json.dumps(
                proposal
            )

        result = (
            self.gateway(
                model_callable=fake_model
            ).reason(
                "Prepare an insurance note."
            )
        )

        self.assertEqual(
            result["status"],
            "proposal_ready"
        )

        self.assertTrue(
            result["validation"]["valid"]
        )

        self.assertEqual(
            len(
                result["proposal"]["workflow"]["steps"]
            ),
            2
        )

    def test_unregistered_capability_is_rejected(self):

        proposal = {
            "intent": {
                "goal":
                    "Do something"
            },
            "action": {
                "capability":
                    "invented_capability",
                "arguments": {}
            }
        }

        def fake_model(_request):
            return json.dumps(
                proposal
            )

        result = (
            self.gateway(
                model_callable=fake_model
            ).reason(
                "Do something."
            )
        )

        self.assertEqual(
            result["status"],
            "model_proposal_rejected"
        )

        self.assertFalse(
            result["validation"]["valid"]
        )

        self.assertTrue(
            any(
                "unregistered capability"
                in error
                for error
                in result["validation"]["errors"]
            )
        )

    def test_invalid_fact_status_is_rejected(self):

        proposal = {
            "facts": [
                {
                    "name":
                        "subject",
                    "value":
                        "test",
                    "status":
                        "MADE_UP_STATUS"
                }
            ]
        }

        def fake_model(_request):
            return json.dumps(
                proposal
            )

        result = (
            self.gateway(
                model_callable=fake_model
            ).reason(
                "test"
            )
        )

        self.assertEqual(
            result["status"],
            "model_proposal_rejected"
        )

        self.assertFalse(
            result["validation"]["valid"]
        )

    def test_fenced_json_is_supported(self):

        proposal = {
            "intent": {
                "goal":
                    "Test"
            }
        }

        raw = (
            "```json\n"
            + json.dumps(proposal)
            + "\n```"
        )

        parsed = (
            self.gateway().parse_model_response(
                raw
            )
        )

        self.assertEqual(
            parsed,
            proposal
        )

    def test_model_proposal_never_executes_a_capability(self):

        calls = []

        def fake_model(request):
            calls.append(
                request
            )

            return json.dumps(
                {
                    "action": {
                        "capability":
                            "draft_institutional_note",
                        "arguments": {
                            "request":
                                "Prepare a note."
                        }
                    }
                }
            )

        gateway = self.gateway(
            model_callable=fake_model
        )

        result = gateway.reason(
            "Prepare a note."
        )

        self.assertEqual(
            result["status"],
            "proposal_ready"
        )

        self.assertEqual(
            len(calls),
            1
        )

        # The gateway only returns a proposal.
        # No dispatcher/executor exists here.
        self.assertNotIn(
            "execution",
            result
        )


class ModelReasoningGatewayDefaultPolicyPathTests(unittest.TestCase):
    """Regression test for a bug found while auditing the identity
    architecture: the default policy_path pointed at a repo-root file
    that did not exist (the real document lives under
    URI_Model_Centric_Architecture_Docs/). load_policy() degrades to
    an empty string on FileNotFoundError, so URI's own operating
    policy/identity document was never actually included in a live
    model request. These tests exercise the *default* (no override),
    unlike every other test in this file, which always overrides
    policy_path with a temp fixture."""

    def test_default_policy_path_loads_the_real_operating_policy(self):
        gateway = ModelReasoningGateway()

        policy_text = gateway.load_policy()

        self.assertNotEqual(policy_text, "")
        self.assertIn("You are URI", policy_text)
        self.assertIn("NIT Sikkim Administrative AI Assistant", policy_text)

    def test_default_policy_text_reaches_the_built_reasoning_request(self):
        gateway = ModelReasoningGateway()

        request = gateway.build_reasoning_request("Prepare a note.")

        self.assertIn("You are URI", request["system_policy"])

    def test_policy_text_reaches_what_would_be_sent_to_the_model(self):
        # No mocking of ModelReasoningGateway or the adapter's own
        # logic - only the final network call is intercepted, by a
        # spy standing in for OllamaProvider.complete(). Proves the
        # real policy document's text actually flows all the way from
        # disk, through the real (default) ModelReasoningGateway,
        # through the real OllamaReasoningAdapter, into what would
        # become the request body sent to Ollama.
        from uri_core.core.model_reasoning_adapter import (
            OllamaReasoningAdapter,
        )
        from uri_core.core.model_providers.base import ModelResponse

        captured = {}

        class _SpyProvider:
            def complete(self, *, system, user, temperature=0.0, max_tokens=None):
                captured["system"] = system
                captured["user"] = user
                return ModelResponse(
                    content="{}", model="spy", provider="spy"
                )

        adapter = OllamaReasoningAdapter(provider=_SpyProvider())
        gateway = ModelReasoningGateway(model_callable=adapter)

        gateway.reason("Prepare a note about the insurance policy.")

        self.assertIn("system", captured)
        self.assertIn("user", captured)

        # The full JSON request (including system_policy) is sent as
        # the user message - see OllamaReasoningAdapter.__call__.
        self.assertIn("You are URI", captured["user"])
        self.assertIn(
            "NIT Sikkim Administrative AI Assistant", captured["user"]
        )


if __name__ == "__main__":
    unittest.main()