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

    def test_awaiting_approval_pauses_rather_than_fails(self):
        # Milestone 11 Phase 2: a handler result whose status is
        # "awaiting_approval" (e.g. ApprovalGate.execute_tool's own
        # result for an approval-required capability) must pause the
        # workflow generically, exactly like "waiting_for_input" -
        # before this fix it fell through to the generic "else"
        # branch and was treated as an outright step failure, which
        # would have wrongly ended the workflow instead of letting the
        # caller await a real approval decision.
        workflow = {
            "workflow_id": "test-6",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "needs_approval_capability",
                    "depends_on": [],
                    "status": "pending",
                }
            ],
        }

        def handler(step, workflow):
            return {
                "status": "awaiting_approval",
                "action_id": "abc-123",
                "risk": "high",
                "message": "This action requires your explicit approval.",
            }

        result = self.executor.execute(workflow, step_handler=handler)

        self.assertEqual(result["status"], "waiting_for_input")
        self.assertEqual(result["workflow"]["status"], "waiting_for_input")
        # Approval-specific fields survive the generic pause path -
        # WorkflowExecutor itself never interprets them, but a caller
        # (e.g. process_user_input) can still read them from the
        # generic result.
        self.assertEqual(result["action_id"], "abc-123")
        self.assertEqual(result["risk"], "high")

    def test_complete_step_externally_unblocks_a_dependent_step(self):
        # Milestone 11 Phase 2.1: proves the generic escape hatch a
        # real out-of-band decision (e.g. an approval) needs -
        # completing a paused step externally, without re-invoking its
        # handler, still lets execute() continue the dependency graph
        # normally afterwards.
        workflow = {
            "workflow_id": "test-7",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "needs_approval_capability",
                    "depends_on": [],
                    "status": "pending",
                },
                {
                    "step_id": "step_2",
                    "capability": "draft_output",
                    "depends_on": ["step_1"],
                    "status": "pending",
                },
            ],
        }

        def handler(step, workflow):
            if step["step_id"] == "step_1":
                return {"status": "awaiting_approval", "action_id": "a1"}
            return {"status": "success", "data": {"ok": True}}

        paused = self.executor.execute(workflow, step_handler=handler)
        self.assertEqual(paused["status"], "waiting_for_input")

        completed = self.executor.complete_step_externally(
            workflow, "step_1", output={"approved": True}
        )
        self.assertTrue(completed)
        self.assertEqual(workflow["steps"][0]["status"], "completed")
        self.assertEqual(workflow["steps"][0]["output"], {"approved": True})

        resumed = self.executor.execute(workflow, step_handler=handler)

        self.assertEqual(resumed["status"], "success")
        self.assertEqual(workflow["steps"][1]["status"], "completed")

    def test_complete_step_externally_refuses_a_step_not_paused(self):
        workflow = {
            "workflow_id": "test-8",
            "status": "planned",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "x",
                    "depends_on": [],
                    "status": "pending",
                },
            ],
        }

        completed = self.executor.complete_step_externally(
            workflow, "step_1"
        )

        self.assertFalse(completed)
        self.assertEqual(workflow["steps"][0]["status"], "pending")

    def test_fail_step_externally_marks_workflow_failed(self):
        workflow = {
            "workflow_id": "test-9",
            "status": "waiting_for_input",
            "steps": [
                {
                    "step_id": "step_1",
                    "capability": "needs_approval_capability",
                    "depends_on": [],
                    "status": "waiting_for_input",
                },
            ],
        }

        failed = self.executor.fail_step_externally(
            workflow, "step_1", error="Approval was rejected."
        )

        self.assertTrue(failed)
        self.assertEqual(workflow["status"], "failed")
        self.assertEqual(workflow["steps"][0]["status"], "failed")
        self.assertEqual(
            workflow["steps"][0]["error"], "Approval was rejected."
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
