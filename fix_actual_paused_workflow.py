from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

path = Path("uri_core/core/orchestrator.py")

text = path.read_text(encoding="utf-8")

start_marker = "    def _save_paused_workflow(\n"
end_marker = "    def _clear_active_workflow(\n"

start = text.find(start_marker)

if start == -1:
    raise RuntimeError(
        "Could not find _save_paused_workflow."
    )

end = text.find(
    end_marker,
    start
)

if end == -1:
    raise RuntimeError(
        "Could not find _clear_active_workflow."
    )

new_method = '''    def _save_paused_workflow(
        self,
        session,
        execution_result
    ):

        workflow = (
            execution_result.get(
                "workflow"
            )
        )

        # ------------------------------------------------------
        # Normalize a newly paused workflow before it enters
        # durable session state.
        #
        # Recovery validation is intentionally strict. Therefore
        # the persistence boundary must guarantee that workflows
        # created by the normal execution path contain the
        # required durable metadata.
        # ------------------------------------------------------

        if isinstance(
            workflow,
            dict
        ):

            if not workflow.get(
                "workflow_id"
            ):

                workflow[
                    "workflow_id"
                ] = str(
                    uuid4()
                )

            if not workflow.get(
                "schema_version"
            ):

                workflow[
                    "schema_version"
                ] = "1.0"

            if not workflow.get(
                "created_at"
            ):

                workflow[
                    "created_at"
                ] = datetime.now(
                    timezone.utc
                ).isoformat()

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

            # The workflow is paused for user input.
            workflow[
                "status"
            ] = "waiting_for_input"

        session.active_workflow = workflow

        session.active_workflow_status = (
            execution_result.get(
                "status"
            )
        )

        session.active_workflow_required_field = (
            execution_result.get(
                "required_field"
            )
            or
            session.last_question_field
        )

        session.active_workflow_question = (
            execution_result.get(
                "message"
            )
        )

'''

text = (
    text[:start]
    + new_method
    + text[end:]
)

path.write_text(
    text,
    encoding="utf-8"
)

print(
    "Actual orchestrator.py paused-workflow persistence repaired."
)
print(
    "Strict recovery validation preserved."
)
print(
    "Paused workflows now receive durable recovery metadata."
)
