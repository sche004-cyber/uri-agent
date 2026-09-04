import unittest

from uri_core.core.workflow_planner import WorkflowPlanner


class TestWorkflowPlanner(unittest.TestCase):

    def setUp(self):
        self.planner = WorkflowPlanner()

    def test_insurance_renewal_creates_workflow(self):

        semantic_result = {
            "goal":
                "Renew the group medical insurance policy",
            "task_type":
                "administrative task",
            "domain":
                "insurance administration",
            "requested_output":
                "renewal noting"
        }

        result = self.planner.create_workflow(
            semantic_result=semantic_result,
            request_text=(
                "I need to renew the group medical "
                "insurance policy."
            )
        )

        self.assertEqual(
            result["status"],
            "workflow_planned"
        )

        workflow = result["workflow"]

        self.assertEqual(
            workflow["status"],
            "planned"
        )

        self.assertGreaterEqual(
            len(workflow["steps"]),
            6
        )

        self.assertEqual(
            workflow["steps"][0]["capability"],
            "retrieve_evidence"
        )

        self.assertEqual(
            workflow["steps"][1]["depends_on"],
            ["step_1"]
        )

    def test_generic_task_creates_workflow(self):

        semantic_result = {
            "goal":
                "Complete a complex administrative request",
            "task_type":
                "administrative task",
            "domain":
                "administrative",
            "requested_output":
                "completed response"
        }

        result = self.planner.create_workflow(
            semantic_result=semantic_result,
            request_text=(
                "Complete this complex administrative task."
            )
        )

        self.assertEqual(
            result["status"],
            "workflow_planned"
        )

        workflow = result["workflow"]

        self.assertEqual(
            workflow["steps"][0]["step_id"],
            "step_1"
        )

        self.assertEqual(
            workflow["steps"][1]["depends_on"],
            ["step_1"]
        )

    def test_workflow_steps_start_pending(self):

        semantic_result = {
            "goal":
                "Renew an insurance policy"
        }

        result = self.planner.create_workflow(
            semantic_result=semantic_result,
            request_text="Renew the insurance policy."
        )

        for step in result["workflow"]["steps"]:

            self.assertEqual(
                step["status"],
                "pending"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
