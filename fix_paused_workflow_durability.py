from pathlib import Path

path = Path("uri_core/core/orchestrator.py")

text = path.read_text(encoding="utf-8")

old = '''    def _save_paused_workflow(
        self,
        session,
        execution_result
    ):

        session.active_workflow = (
            execution_result.get("workflow")
        )

        session.active_workflow_status = (
            execution_result.get("status")
        )

        session.active_workflow_required_field = (
            execution_result.get("required_field")
            or session.last_question_field
        )

        session.active_workflow_question = (
            execution_result.get("message")
        )
'''

new = '''    def _save_paused_workflow(
        self,
        session,
        execution_result
    ):

        workflow = (
            execution_result.get("workflow")
        )

        # ------------------------------------------------------
        # Persisted workflows must always satisfy the durable
        # recovery envelope before entering active session state.
        #
        # The planner/executor may produce a valid runtime
        # workflow without all persistence metadata. A paused
        # workflow, however, must be restart-safe because the
        # next user message may arrive in a fresh process.
        # ------------------------------------------------------

        if isinstance(workflow, dict):

            if not workflow.get(
                "workflow_id"
            ):

                from uuid import uuid4

                workflow[
                    "workflow_id"
                ] = str(uuid4())

            if not workflow.get(
                "schema_version"
            ):

                workflow[
                    "schema_version"
                ] = "1.0"

            if not workflow.get(
                "created_at"
            ):

                from datetime import datetime, timezone

                workflow[
                    "created_at"
                ] = datetime.now(
                    timezone.utc
                ).isoformat()

            from datetime import datetime, timezone

            workflow[
                "updated_at"
            ] = datetime.now(
                timezone.utc
            ).isoformat()

            if "completed_at" not in workflow:

                workflow[
                    "completed_at"
                ] = None

            if "failed_at" not in workflow:

                workflow[
                    "failed_at"
                ] = None

            if not isinstance(
                workflow.get(
                    "execution_history"
                ),
                list
            ):

                workflow[
                    "execution_history"
                ] = []

            workflow[
                "status"
            ] = "waiting_for_input"

            session.active_workflow = workflow

        else:

            session.active_workflow = None

        session.active_workflow_status = (
            execution_result.get(
                "status"
            )
        )

        session.active_workflow_required_field = (
            execution_result.get(
                "required_field"
            )
            or session.last_question_field
        )

        session.active_workflow_question = (
            execution_result.get(
                "message"
            )
        )
'''

if old not in text:
    raise RuntimeError(
        "Could not find _save_paused_workflow."
    )

text = text.replace(
    old,
    new,
    1
)

path.write_text(
    text,
    encoding="utf-8"
)

print(
    "Paused-workflow durability normalization repaired successfully."
)
print(
    "Recovery validation remains strict."
)
print(
    "Newly paused workflows will now be persisted as schema 1.0."
)
