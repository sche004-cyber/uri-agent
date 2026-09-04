import uuid
from datetime import datetime, timezone


class WorkflowPlanner:
    """
    Creates structured workflows for tasks that require
    multiple capabilities or execution stages.
    """

    WORKFLOW_SCHEMA_VERSION = "1.0"

    def create_workflow(
        self,
        semantic_result: dict,
        request_text: str
    ) -> dict:

        task = (
            semantic_result.get("task")
            or semantic_result.get("intent")
            or semantic_result.get("task_type")
            or "generic"
        )

        normalized_task = str(
            task
        ).strip().lower()

        workflow = {
            "workflow_id":
                self._generate_workflow_id(),
            "schema_version":
                self.WORKFLOW_SCHEMA_VERSION,
            "task":
                normalized_task,
            "goal":
                request_text,
            "request_text":
                request_text,
            "semantic_context":
                semantic_result,
            "status":
                "planned",
            "created_at":
                self._utc_timestamp(),
            "updated_at":
                self._utc_timestamp(),
            "completed_at":
                None,
            "failed_at":
                None,
            "execution_history":
                [],
            "steps":
                self._create_steps(
                    normalized_task,
                    semantic_result
                )
        }

        self._record_history(
            workflow,
            "workflow_created"
        )

        return {
            "status":
                "workflow_planned",
            "workflow":
                workflow
        }

    def _create_steps(
        self,
        task: str,
        semantic_result: dict = None
    ) -> list:

        semantic_result = (
            semantic_result or {}
        )

        combined = (
            task
            + " "
            + str(
                semantic_result.get(
                    "goal",
                    ""
                )
            ).lower()
            + " "
            + str(
                semantic_result.get(
                    "requested_output",
                    ""
                )
            ).lower()
        )

        if (
            "insurance" in combined
            or "renewal" in combined
        ):

            return [
                self._create_step(
                    "step_1",
                    "retrieve_evidence",
                    []
                ),
                self._create_step(
                    "step_2",
                    "verify_facts",
                    ["step_1"]
                ),
                self._create_step(
                    "step_3",
                    "identify_missing_information",
                    ["step_2"]
                ),
                self._create_step(
                    "step_4",
                    "prepare_decision_context",
                    ["step_3"]
                ),
                self._create_step(
                    "step_5",
                    "draft_output",
                    ["step_4"]
                ),
                self._create_step(
                    "step_6",
                    "review_result",
                    ["step_5"]
                )
            ]

        if (
            "note" in combined
            or "noting" in combined
        ):

            return [
                self._create_step(
                    "step_1",
                    "retrieve_evidence",
                    []
                ),
                self._create_step(
                    "step_2",
                    "verify_facts",
                    ["step_1"]
                ),
                self._create_step(
                    "step_3",
                    "identify_missing_information",
                    ["step_2"]
                ),
                self._create_step(
                    "step_4",
                    "prepare_decision_context",
                    ["step_3"]
                ),
                self._create_step(
                    "step_5",
                    "draft_output",
                    ["step_4"]
                ),
                self._create_step(
                    "step_6",
                    "review_result",
                    ["step_5"]
                )
            ]

        return [
            self._create_step(
                "step_1",
                "retrieve_evidence",
                []
            ),
            self._create_step(
                "step_2",
                "identify_missing_information",
                ["step_1"]
            ),
            self._create_step(
                "step_3",
                "prepare_output",
                ["step_2"]
            ),
            self._create_step(
                "step_4",
                "review_result",
                ["step_3"]
            )
        ]

    def _create_step(
        self,
        step_id: str,
        capability: str,
        depends_on: list
    ) -> dict:

        return {
            "step_id":
                step_id,
            "capability":
                capability,
            "status":
                "pending",
            "depends_on":
                depends_on,
            "created_at":
                self._utc_timestamp(),
            "started_at":
                None,
            "completed_at":
                None,
            "failed_at":
                None,
            "updated_at":
                self._utc_timestamp(),
            "output":
                None,
            "result":
                None,
            "error":
                None,
            "execution_count":
                0
        }

    def _generate_workflow_id(
        self
    ) -> str:

        return (
            "workflow-"
            + uuid.uuid4().hex
        )

    def _utc_timestamp(
        self
    ) -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()

    def _record_history(
        self,
        workflow: dict,
        event: str,
        step_id: str = None,
        details: dict = None
    ):

        workflow.setdefault(
            "execution_history",
            []
        ).append(
            {
                "timestamp":
                    self._utc_timestamp(),
                "event":
                    event,
                "step_id":
                    step_id,
                "details":
                    details or {}
            }
        )

        workflow[
            "updated_at"
        ] = self._utc_timestamp()
