import unittest

from uri_core.core.workflow_planner import (
    WorkflowPlanner
)
from uri_core.core.workflow_executor import (
    WorkflowExecutor
)


class TestWorkflowDurability(
    unittest.TestCase):

    def test_workflow_has_unique_id_and_metadata(
        self
    ):

        planner = WorkflowPlanner()

        first = planner.create_workflow(
            semantic_result={
                "task": "noting"
            },
            request_text="Prepare a noting"
        )["workflow"]

        second = planner.create_workflow(
            semantic_result={
                "task": "noting"
            },
            request_text="Prepare another noting"
        )["workflow"]

        self.assertNotEqual(
            first["workflow_id"],
            second["workflow_id"]
        )

        self.assertIn(
            "schema_version",
            first
        )

        self.assertIsNotNone(
            first["created_at"]
        )

        self.assertIsNotNone(
            first["updated_at"]
        )

        self.assertIsNone(
            first["completed_at"]
        )

        self.assertGreater(
            len(
                first["execution_history"]
            ),
            0
        )

    def test_step_output_and_history_are_recorded(
        self
    ):

        workflow = {
            "workflow_id":
                "durability-test",
            "status": "pending",
            "steps": [
                {
                    "step_id":
                        "step_1",
                    "capability":
                        "first",
                    "status":
                        "pending",
                    "depends_on": []
                },
                {
                    "step_id":
                        "step_2",
                    "capability":
                        "second",
                    "status":
                        "pending",
                    "depends_on":
                        ["step_1"]
                }
            ]
        }

        executor = WorkflowExecutor()

        executor.register_handler(
            "first",
            lambda step, workflow: {
                "status": "success",
                "data": {
                    "value": "first-output"
                }
            }
        )

        executor.register_handler(
            "second",
            lambda step, workflow: {
                "status": "success",
                "data": {
                    "value": "second-output"
                }
            }
        )

        result = executor.execute(
            workflow
        )

        self.assertEqual(
            result["status"],
            "success"
        )

        self.assertEqual(
            workflow["status"],
            "completed"
        )

        self.assertIsNotNone(
            workflow["completed_at"]
        )

        self.assertEqual(
            workflow["steps"][0]["output"],
            {
                "value": "first-output"
            }
        )

        self.assertEqual(
            workflow["steps"][1]["output"],
            {
                "value": "second-output"
            }
        )

        events = [
            item["event"]
            for item in workflow[
                "execution_history"
            ]
        ]

        self.assertIn(
            "step_started",
            events
        )

        self.assertIn(
            "step_completed",
            events
        )

        self.assertIn(
            "workflow_completed",
            events
        )

    def test_failure_records_step_error(
        self
    ):

        workflow = {
            "workflow_id":
                "failure-test",
            "status": "pending",
            "steps": [
                {
                    "step_id":
                        "step_1",
                    "capability":
                        "broken",
                    "status":
                        "pending",
                    "depends_on": []
                }
            ]
        }

        executor = WorkflowExecutor()

        executor.register_handler(
            "broken",
            lambda step, workflow: {
                "status": "failed",
                "error": (
                    "Intentional failure"
                )
            }
        )

        result = executor.execute(
            workflow
        )

        self.assertEqual(
            result["status"],
            "failed"
        )

        self.assertEqual(
            workflow["status"],
            "failed"
        )

        self.assertIsNotNone(
            workflow["failed_at"]
        )

        self.assertEqual(
            workflow["steps"][0]["error"],
            "Intentional failure"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
