import unittest

from uri_core.core.workflow_executor import (
    WorkflowExecutor
)


class TestWorkflowResume(
    unittest.TestCase
):

    def test_waiting_step_resumes_and_completes(self):

        workflow = {
            "workflow_id": "resume-test",
            "status": "waiting_for_input",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "first",
                    "status": "completed",
                    "depends_on": []
                },
                {
                    "step_id": "step_2",
                    "capability": "second",
                    "status": "waiting_for_input",
                    "depends_on": [
                        "step_1"
                    ]
                }
            ]
        }

        executor = WorkflowExecutor()

        executor.register_handler(
            "second",
            lambda step, workflow: {
                "status": "success",
                "data": {
                    "resumed": True
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

        steps = result[
            "workflow"
        ]["steps"]

        self.assertEqual(
            steps[1]["status"],
            "completed"
        )

        self.assertEqual(
            steps[1]["result"]["resumed"],
            True
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
