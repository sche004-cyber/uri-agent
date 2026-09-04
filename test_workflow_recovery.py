import unittest

from uri_core.core.workflow_recovery import (
    WorkflowRecoveryValidator
)


class TestWorkflowRecoveryValidator(
    unittest.TestCase
):

    def make_workflow(self):

        return {
            "workflow_id": "wf-test-001",
            "schema_version": "1.0",
            "status": "waiting_for_input",
            "created_at": "2026-09-03T00:00:00+00:00",
            "updated_at": "2026-09-03T00:00:00+00:00",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "test_capability",
                    "status": "waiting_for_input",
                    "depends_on": [],
                    "created_at":
                        "2026-09-03T00:00:00+00:00",
                    "started_at":
                        "2026-09-03T00:00:00+00:00",
                    "completed_at": None,
                    "failed_at": None,
                    "updated_at":
                        "2026-09-03T00:00:00+00:00",
                    "output": None,
                    "result": None,
                    "error": None,
                    "execution_count": 1
                }
            ]
        }

    def test_valid_waiting_workflow(self):

        workflow = self.make_workflow()

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertTrue(
            result["valid"]
        )

    def test_missing_workflow_id_is_rejected(self):

        workflow = self.make_workflow()

        del workflow["workflow_id"]

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertFalse(
            result["valid"]
        )

    def test_duplicate_step_ids_are_rejected(self):

        workflow = self.make_workflow()

        workflow["steps"].append(
            dict(
                workflow["steps"][0]
            )
        )

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertFalse(
            result["valid"]
        )

    def test_missing_dependency_is_rejected(self):

        workflow = self.make_workflow()

        workflow["steps"][0]["depends_on"] = [
            "missing_step"
        ]

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertFalse(
            result["valid"]
        )

    def test_dependency_cycle_is_rejected(self):

        workflow = self.make_workflow()

        workflow["steps"] = [
            {
                "step_id": "step_1",
                "status": "pending",
                "depends_on": ["step_2"]
            },
            {
                "step_id": "step_2",
                "status": "pending",
                "depends_on": ["step_1"]
            }
        ]

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertFalse(
            result["valid"]
        )

    def test_completed_step_requires_timestamp(self):

        workflow = self.make_workflow()

        workflow["status"] = "completed"
        workflow["steps"][0]["status"] = "completed"

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertFalse(
            result["valid"]
        )

    def test_failed_step_requires_error(self):

        workflow = self.make_workflow()

        workflow["status"] = "failed"
        workflow["steps"][0]["status"] = "failed"

        result = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        self.assertFalse(
            result["valid"]
        )

    def test_running_workflow_requires_recovery_review(self):

        workflow = self.make_workflow()

        workflow["status"] = "running"
        workflow["steps"][0]["status"] = "running"

        result = (
            WorkflowRecoveryValidator.recovery_action(
                workflow
            )
        )

        self.assertEqual(
            result["action"],
            "recovery_review"
        )

    def test_waiting_workflow_can_resume(self):

        workflow = self.make_workflow()

        result = (
            WorkflowRecoveryValidator.recovery_action(
                workflow
            )
        )

        self.assertEqual(
            result["action"],
            "resume"
        )

        self.assertTrue(
            WorkflowRecoveryValidator.is_safe_to_resume(
                workflow
            )
        )

    def test_completed_workflow_is_not_reexecuted(self):

        workflow = self.make_workflow()

        workflow["status"] = "completed"
        workflow["steps"][0]["status"] = "completed"
        workflow["steps"][0]["completed_at"] = (
            "2026-09-03T00:01:00+00:00"
        )

        result = (
            WorkflowRecoveryValidator.recovery_action(
                workflow
            )
        )

        self.assertEqual(
            result["action"],
            "already_complete"
        )

        self.assertFalse(
            WorkflowRecoveryValidator.is_safe_to_resume(
                workflow
            )
        )


if __name__ == "__main__":
    unittest.main()
