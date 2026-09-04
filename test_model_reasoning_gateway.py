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


if __name__ == "__main__":
    unittest.main()