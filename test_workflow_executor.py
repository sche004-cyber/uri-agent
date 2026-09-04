import unittest

from uri_core.core.workflow_executor import (
    WorkflowExecutor
)


class TestWorkflowExecutor(unittest.TestCase):

    def setUp(self):

        self.executor = WorkflowExecutor()

    def test_executes_steps_in_dependency_order(self):

        execution_order = []

        def handler(step, workflow):

            execution_order.append(
                step["step_id"]
            )

            return {
                "status": "success",
                "data": {
                    "completed_capability":
                        step["capability"]
                }
            }

        workflow = {
            "workflow_id": "test-1",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "retrieve_evidence",
                    "depends_on": [],
                    "status": "pending"
                },
                {
                    "step_id": "step_2",
                    "capability": "verify_facts",
                    "depends_on": ["step_1"],
                    "status": "pending"
                },
                {
                    "step_id": "step_3",
                    "capability": "draft_output",
                    "depends_on": ["step_2"],
                    "status": "pending"
                }
            ]
        }

        result = self.executor.execute(
            workflow,
            step_handler=handler
        )

        self.assertEqual(
            result["status"],
            "success"
        )

        self.assertEqual(
            result["workflow"]["status"],
            "completed"
        )

        self.assertEqual(
            execution_order,
            [
                "step_1",
                "step_2",
                "step_3"
            ]
        )

        statuses = [
            step["status"]
            for step in result["workflow"]["steps"]
        ]

        self.assertEqual(
            statuses,
            [
                "completed",
                "completed",
                "completed"
            ]
        )

    def test_failed_step_stops_workflow(self):

        workflow = {
            "workflow_id": "test-2",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "retrieve_evidence",
                    "depends_on": [],
                    "status": "pending"
                },
                {
                    "step_id": "step_2",
                    "capability": "verify_facts",
                    "depends_on": ["step_1"],
                    "status": "pending"
                }
            ]
        }

        def handler(step, workflow):

            if step["step_id"] == "step_1":

                return {
                    "status": "failed",
                    "error":
                        "Evidence source unavailable."
                }

            return {
                "status": "success"
            }

        result = self.executor.execute(
            workflow,
            step_handler=handler
        )

        self.assertEqual(
            result["status"],
            "failed"
        )

        self.assertEqual(
            result["failed_step"],
            "step_1"
        )

        self.assertEqual(
            result["workflow"]["steps"][1]["status"],
            "pending"
        )

    def test_waiting_for_user_input_pauses_workflow(self):

        workflow = {
            "workflow_id": "test-3",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "retrieve_evidence",
                    "depends_on": [],
                    "status": "pending"
                },
                {
                    "step_id": "step_2",
                    "capability":
                        "identify_missing_information",
                    "depends_on": ["step_1"],
                    "status": "pending"
                }
            ]
        }

        def handler(step, workflow):

            if step["step_id"] == "step_2":

                return {
                    "status":
                        "waiting_for_input",
                    "message":
                        "Policy number is required."
                }

            return {
                "status": "success"
            }

        result = self.executor.execute(
            workflow,
            step_handler=handler
        )

        self.assertEqual(
            result["status"],
            "waiting_for_input"
        )

        self.assertEqual(
            result["workflow"]["status"],
            "waiting_for_input"
        )

        self.assertEqual(
            result["workflow"]["steps"][0]["status"],
            "completed"
        )

        self.assertEqual(
            result["workflow"]["steps"][1]["status"],
            "waiting_for_input"
        )

    def test_missing_dependency_blocks_workflow(self):

        workflow = {
            "workflow_id": "test-4",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_2",
                    "capability": "draft_output",
                    "depends_on": ["missing_step"],
                    "status": "pending"
                }
            ]
        }

        result = self.executor.execute(
            workflow
        )

        self.assertEqual(
            result["status"],
            "blocked"
        )

        self.assertIn(
            "step_2",
            result["blocked_steps"]
        )

    def test_unknown_capability_pauses_safely(self):

        workflow = {
            "workflow_id": "test-5",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability":
                        "unknown_capability",
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

        self.assertIn(
            "no executable handler",
            result["message"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
