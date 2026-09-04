import unittest

from uri_core.core.workflow_capability_router import (
    WorkflowCapabilityRouter
)


class FakeDispatcher:

    def __init__(self):
        self.calls = []

    def execute_tool(
        self,
        tool_name,
        **kwargs
    ):

        self.calls.append(
            {
                "tool_name": tool_name,
                "kwargs": kwargs
            }
        )

        return {
            "status": "success",
            "data": {
                "draft":
                    "Generated institutional draft."
            }
        }


class FakeFact:

    def __init__(self, value):
        self.value = value


class FakeSession:

    def __init__(self):
        self.current_facts = {
            "subject":
                FakeFact(
                    "Group Medical Insurance Renewal"
                ),
            "approval_requested":
                FakeFact(
                    "Approval for renewal"
                ),
            "justification":
                FakeFact(
                    "Continuation of student insurance coverage"
                )
        }

        self.evidence_facts = {}


class TestWorkflowCapabilityRouter(
    unittest.TestCase
):

    def setUp(self):

        self.dispatcher = (
            FakeDispatcher()
        )

        self.session = FakeSession()

        self.router = (
            WorkflowCapabilityRouter(
                dispatcher=self.dispatcher,
                session=self.session
            )
        )

        self.executor = (
            self.router.create_executor()
        )

    def test_noting_workflow_routes_to_drafting_tool(
        self
    ):

        workflow = {
            "workflow_id": "test-1",
            "goal":
                "Prepare renewal noting",
            "status": "planned",
            "semantic_context": {
                "requested_output":
                    "office note"
            },
            "steps": [
                {
                    "step_id": "step_1",
                    "capability":
                        "retrieve_evidence",
                    "depends_on": [],
                    "status": "pending"
                },
                {
                    "step_id": "step_2",
                    "capability":
                        "verify_facts",
                    "depends_on":
                        ["step_1"],
                    "status": "pending"
                },
                {
                    "step_id": "step_3",
                    "capability":
                        "identify_missing_information",
                    "depends_on":
                        ["step_2"],
                    "status": "pending"
                },
                {
                    "step_id": "step_4",
                    "capability":
                        "draft_output",
                    "depends_on":
                        ["step_3"],
                    "status": "pending"
                },
                {
                    "step_id": "step_5",
                    "capability":
                        "review_result",
                    "depends_on":
                        ["step_4"],
                    "status": "pending"
                }
            ]
        }

        result = self.executor.execute(
            workflow
        )

        self.assertEqual(
            result["status"],
            "success"
        )

        self.assertEqual(
            len(self.dispatcher.calls),
            1
        )

        self.assertEqual(
            self.dispatcher.calls[0][
                "tool_name"
            ],
            "draft_institutional_note"
        )

    def test_missing_information_pauses_workflow(
        self
    ):

        self.session.current_facts = {}

        workflow = {
            "workflow_id": "test-2",
            "goal":
                "Prepare insurance noting",
            "status": "planned",
            "semantic_context": {
                "requested_output":
                    "office note"
            },
            "steps": [
                {
                    "step_id": "step_1",
                    "capability":
                        "identify_missing_information",
                    "depends_on": [],
                    "status": "pending"
                }
            ]
        }

        result = self.executor.execute(
            workflow
        )

        self.assertEqual(
            result["status"],
            "waiting_for_input"
        )

        self.assertEqual(
            result["required_field"],
            "subject"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
