from datetime import datetime, timezone
from uuid import uuid4


class WorkflowExecutor:
    """
    Executes URI workflows.

    The workflow object supplied by the caller is updated in place.
    This is required for session persistence and restart recovery.
    """

    SUCCESS_STATES = {
        "completed",
        "skipped"
    }

    SCHEMA_VERSION = "1.0"

    def __init__(self, capability_handlers=None):

        self.capability_handlers = (
            capability_handlers or {}
        )

    def register_handler(self, capability: str, handler):

        self.capability_handlers[capability] = handler

    def complete_step_externally(
        self,
        workflow: dict,
        step_id: str,
        output=None
    ) -> bool:
        """Marks one currently-paused ("waiting_for_input") step
        completed using a result obtained OUTSIDE a normal execute()
        call - e.g. a real, asynchronous human decision (an approval)
        recorded elsewhere, after which the underlying capability has
        already actually run exactly once. execute() itself has no
        way to resume a paused step without re-invoking its handler
        (which would re-run - and for an approval-required capability,
        re-propose - the exact action that already executed); this is
        the generic escape hatch for "the real answer already exists,
        just record it and let the dependency graph continue."

        Mirrors execute()'s own "success" branch bookkeeping exactly
        (status/timestamps/output/history), so a workflow completed
        this way is indistinguishable in shape from one that completed
        entirely inside execute(). A subsequent execute() call then
        naturally continues with whatever remaining steps this
        completion unblocks - it is not itself re-invoked here.

        Returns False (no-op) when step_id does not exist or is not
        currently "waiting_for_input" - callers must not use this to
        complete a step that was never actually paused, or to
        double-complete one already finished.
        """

        step = None

        for candidate in workflow.get("steps", []):

            if (
                isinstance(candidate, dict)
                and candidate.get("step_id") == step_id
            ):
                step = candidate
                break

        if step is None or step.get("status") != "waiting_for_input":
            return False

        now = self._now()

        step["status"] = "completed"
        step["completed_at"] = now
        step["updated_at"] = now

        if output is not None:
            step["output"] = output
            step["result"] = output

        self._append_history(
            workflow,
            {
                "step_id": step_id,
                "event": "step_completed_externally",
                "timestamp": now,
            }
        )

        workflow["updated_at"] = now

        # This step's own pause no longer applies - clear the
        # top-level marker so the next execute() call reports whatever
        # actually applies now (success, blocked, or paused on a
        # different step) instead of appearing stuck on the old pause.
        if workflow.get("status") == "waiting_for_input":
            workflow["status"] = "planned"

        return True

    def fail_step_externally(
        self,
        workflow: dict,
        step_id: str,
        error: str = "Step failed."
    ) -> bool:
        """The fail-closed counterpart to complete_step_externally:
        marks one step (and the whole workflow) failed using an
        outcome obtained outside a normal execute() call - e.g. a
        rejected approval, for which the paused step can never
        actually complete (its action_id can only ever be decided
        once). Mirrors execute()'s own "failed" branch bookkeeping
        exactly.

        Returns False (no-op) when step_id does not exist - callers
        must not use this on a step that was never actually paused."""

        step = None

        for candidate in workflow.get("steps", []):

            if (
                isinstance(candidate, dict)
                and candidate.get("step_id") == step_id
            ):
                step = candidate
                break

        if step is None:
            return False

        now = self._now()

        step["status"] = "failed"
        step["error"] = error
        step["failed_at"] = now
        step["updated_at"] = now

        workflow["status"] = "failed"
        workflow["failed_at"] = now
        workflow["updated_at"] = now

        self._append_history(
            workflow,
            {
                "step_id": step_id,
                "event": "step_failed_externally",
                "timestamp": now,
                "error": error,
            }
        )

        return True

    def execute(self, workflow: dict, step_handler=None) -> dict:

        if not isinstance(workflow, dict):

            return {
                "status": "failed",
                "error": "Workflow must be a dictionary."
            }

        steps = workflow.get("steps", [])

        if not isinstance(steps, list):

            return {
                "status": "failed",
                "error": "Workflow steps must be a list."
            }

        self._ensure_workflow_metadata(workflow)

        step_map = {
            step.get("step_id"): step
            for step in steps
            if (
                isinstance(step, dict)
                and step.get("step_id")
            )
        }

        execution_log = []
        progress_made = True

        while progress_made:

            progress_made = False

            for step in steps:

                if not isinstance(step, dict):
                    continue

                step_status = step.get("status")

                # A waiting step is being resumed.
                resumed_from_waiting = (
                    step_status == "waiting_for_input"
                )

                if resumed_from_waiting:

                    step["status"] = "pending"
                    step["updated_at"] = self._now()

                if step.get("status") != "pending":
                    continue

                dependency_state = self._dependency_state(
                    step,
                    step_map
                )

                if dependency_state == "missing":

                    error = (
                        "A required dependency is missing."
                    )

                    self._mark_step_blocked(
                        workflow,
                        step,
                        error
                    )

                    return {
                        "status": "blocked",
                        "workflow": workflow,
                        "execution_log": execution_log,
                        "blocked_steps": [
                            step.get("step_id")
                        ],
                        "error":
                            "Workflow cannot continue because a required dependency is missing."
                    }

                if dependency_state == "incomplete":
                    continue

                step_id = step.get("step_id")
                now = self._now()

                step["status"] = "running"
                step["started_at"] = (
                    step.get("started_at") or now
                )
                step["updated_at"] = now
                step["execution_count"] = (
                    int(
                        step.get(
                            "execution_count",
                            0
                        )
                    ) + 1
                )

                workflow["status"] = "running"
                workflow["updated_at"] = now

                start_log = {
                    "step_id": step_id,
                    "event": "started",
                    "timestamp": now,
                    "execution_count":
                        step["execution_count"]
                }

                execution_log.append(start_log)

                self._append_history(
                    workflow,
                    {
                        "step_id": step_id,
                        "event": "step_started",
                        "timestamp": now,
                        "execution_count":
                            step["execution_count"]
                    }
                )

                # Do not ask again when this is an actual resume
                # of a step that was already waiting for input.
                if (
                    step.get(
                        "requires_user_input",
                        False
                    )
                    and not resumed_from_waiting
                ):

                    return self._pause_for_input(
                        workflow,
                        step,
                        execution_log,
                        "Additional information is required."
                    )

                handler_result = self._execute_step(
                    step=step,
                    workflow=workflow,
                    step_handler=step_handler
                )

                result_status = handler_result.get(
                    "status"
                )

                if result_status == "success":

                    completed_at = self._now()

                    step["status"] = "completed"
                    step["completed_at"] = completed_at
                    step["updated_at"] = completed_at

                    output = handler_result.get(
                        "data"
                    )

                    if output is None:
                        output = handler_result.get(
                            "output"
                        )

                    if output is not None:

                        step["output"] = output
                        step["result"] = output

                    completed_log = {
                        "step_id": step_id,
                        "event": "completed",
                        "timestamp": completed_at,
                        "execution_count":
                            step["execution_count"]
                    }

                    execution_log.append(
                        completed_log
                    )

                    self._append_history(
                        workflow,
                        {
                            "step_id": step_id,
                            "event": "step_completed",
                            "timestamp":
                                completed_at,
                            "execution_count":
                                step["execution_count"]
                        }
                    )

                    workflow["updated_at"] = completed_at

                    progress_made = True
                    continue

                if (
                    result_status
                    == "waiting_for_input"
                    or result_status
                    == "awaiting_approval"
                ):

                    # "awaiting_approval" (e.g. ApprovalGate.execute_tool's
                    # result for an approval-required capability) is a
                    # second, generic pause state alongside
                    # "waiting_for_input" (a handler asking for more
                    # information) - WorkflowExecutor treats both the
                    # same way structurally (pause this step, mark the
                    # workflow waiting, let the caller resume it later)
                    # without needing to know what "approval" means -
                    # see _pause_for_input's extra= passthrough below,
                    # which is what lets a caller still recover
                    # approval-specific fields like action_id.
                    return self._pause_for_input(
                        workflow,
                        step,
                        execution_log,
                        handler_result.get(
                            "message",
                            "Additional information is required."
                        ),
                        handler_result.get(
                            "required_field"
                        ),
                        extra=handler_result
                    )

                error_message = (
                    handler_result.get("error")
                    or handler_result.get("message")
                    or "Workflow step failed."
                )

                failed_at = self._now()

                step["status"] = "failed"
                step["error"] = error_message
                step["failed_at"] = failed_at
                step["updated_at"] = failed_at

                workflow["status"] = "failed"
                workflow["failed_at"] = failed_at
                workflow["updated_at"] = failed_at

                failed_log = {
                    "step_id": step_id,
                    "event": "failed",
                    "timestamp": failed_at,
                    "error": error_message,
                    "execution_count":
                        step["execution_count"]
                }

                execution_log.append(
                    failed_log
                )

                self._append_history(
                    workflow,
                    {
                        "step_id": step_id,
                        "event": "step_failed",
                        "timestamp": failed_at,
                        "error": error_message,
                        "execution_count":
                            step["execution_count"]
                    }
                )

                return {
                    "status": "failed",
                    "workflow": workflow,
                    "execution_log": execution_log,
                    "failed_step": step_id,
                    "error": error_message
                }

        executable_steps = [
            step
            for step in steps
            if isinstance(step, dict)
        ]

        if not executable_steps:

            return self._complete_workflow(
                workflow,
                execution_log
            )

        if all(
            step.get("status")
            in self.SUCCESS_STATES
            for step in executable_steps
        ):

            return self._complete_workflow(
                workflow,
                execution_log
            )

        blocked_steps = [
            step.get("step_id")
            for step in executable_steps
            if step.get("status") == "pending"
        ]

        workflow["status"] = "blocked"

        blocked_at = self._now()
        workflow["updated_at"] = blocked_at

        blocked_event = {
            "event": "workflow_blocked",
            "timestamp": blocked_at,
            "blocked_steps": blocked_steps
        }

        self._append_history(
            workflow,
            blocked_event
        )

        execution_log.append(
            blocked_event
        )

        return {
            "status": "blocked",
            "workflow": workflow,
            "execution_log": execution_log,
            "blocked_steps": blocked_steps,
            "error":
                "Workflow cannot continue because dependencies are incomplete."
        }

    def _execute_step(
        self,
        step: dict,
        workflow: dict,
        step_handler
    ) -> dict:

        if step_handler is not None:

            try:

                result = step_handler(
                    step=step,
                    workflow=workflow
                )

                return self._validate_result(
                    result
                )

            except Exception as e:

                return {
                    "status": "failed",
                    "error": str(e)
                }

        capability = step.get("capability")

        handler = self.capability_handlers.get(
            capability
        )

        if handler is None:

            return {
                "status": "waiting_for_input",
                "message":
                    (
                        "URI has planned this step but "
                        f"no executable handler is registered "
                        f"for capability: {capability}"
                    )
            }

        try:

            result = handler(
                step=step,
                workflow=workflow
            )

            return self._validate_result(
                result
            )

        except Exception as e:

            return {
                "status": "failed",
                "error": str(e)
            }

    def _validate_result(self, result) -> dict:

        if not isinstance(result, dict):

            return {
                "status": "failed",
                "error":
                    "Workflow handler returned an invalid result."
            }

        if "status" not in result:

            return {
                "status": "failed",
                "error":
                    "Workflow handler result has no status."
            }

        return result

    def _pause_for_input(
        self,
        workflow: dict,
        step: dict,
        execution_log: list,
        message: str,
        required_field=None,
        extra: dict = None
    ) -> dict:

        now = self._now()

        step["status"] = "waiting_for_input"
        step["updated_at"] = now

        workflow["status"] = "waiting_for_input"
        workflow["updated_at"] = now

        event = {
            "step_id": step.get("step_id"),
            "event": "waiting_for_input",
            "timestamp": now
        }

        execution_log.append(event)

        self._append_history(
            workflow,
            event
        )

        result = {
            "status": "waiting_for_input",
            "workflow": workflow,
            "execution_log": execution_log,
            "message": message
        }

        if required_field:

            result["required_field"] = required_field

            workflow["active_required_field"] = (
                required_field
            )

        # Generic passthrough: any additional fields the handler's
        # own pause result carried (e.g. ApprovalGate.execute_tool's
        # action_id/risk/description for an "awaiting_approval"
        # result) are merged in without ever overwriting a field
        # already set above - WorkflowExecutor itself never
        # interprets these; it only relays them so a caller can still
        # reach domain-specific pause data through this one generic
        # path.
        if isinstance(extra, dict):

            for key, value in extra.items():

                if key not in result and key != "status":
                    result[key] = value

        return result

    def _dependency_state(
        self,
        step: dict,
        step_map: dict
    ) -> str:

        dependencies = step.get(
            "depends_on",
            []
        )

        if not dependencies:
            return "complete"

        for dependency_id in dependencies:

            dependency = step_map.get(
                dependency_id
            )

            if dependency is None:
                return "missing"

            if (
                dependency.get("status")
                not in self.SUCCESS_STATES
            ):
                return "incomplete"

        return "complete"

    def _dependencies_completed(
        self,
        step: dict,
        step_map: dict
    ) -> bool:

        return (
            self._dependency_state(
                step,
                step_map
            )
            == "complete"
        )

    def _mark_step_blocked(
        self,
        workflow: dict,
        step: dict,
        error: str
    ):

        now = self._now()

        step["status"] = "blocked"
        step["error"] = error
        step["updated_at"] = now

        workflow["status"] = "blocked"
        workflow["updated_at"] = now

        self._append_history(
            workflow,
            {
                "step_id": step.get("step_id"),
                "event": "step_blocked",
                "timestamp": now,
                "error": error
            }
        )

    def _complete_workflow(
        self,
        workflow: dict,
        execution_log: list
    ) -> dict:

        completed_at = self._now()

        workflow["status"] = "completed"
        workflow["completed_at"] = (
            workflow.get("completed_at")
            or completed_at
        )
        workflow["updated_at"] = completed_at

        completion_event = {
            "event": "workflow_completed",
            "timestamp": completed_at
        }

        self._append_history(
            workflow,
            completion_event
        )

        return {
            "status": "success",
            "workflow": workflow,
            "execution_log": execution_log
        }

    def _ensure_workflow_metadata(
        self,
        workflow: dict
    ):

        now = self._now()

        workflow.setdefault(
            "workflow_id",
            str(uuid4())
        )

        workflow.setdefault(
            "schema_version",
            self.SCHEMA_VERSION
        )

        workflow.setdefault(
            "status",
            "planned"
        )

        workflow.setdefault(
            "created_at",
            now
        )

        workflow.setdefault(
            "updated_at",
            now
        )

        workflow.setdefault(
            "completed_at",
            None
        )

        workflow.setdefault(
            "failed_at",
            None
        )

        workflow.setdefault(
            "execution_history",
            []
        )

        if not isinstance(
            workflow["execution_history"],
            list
        ):

            workflow["execution_history"] = []

        for index, step in enumerate(
            workflow.get("steps", [])
        ):

            if not isinstance(step, dict):
                continue

            step.setdefault(
                "step_id",
                f"step_{index + 1}"
            )

            step.setdefault(
                "status",
                "pending"
            )

            step.setdefault(
                "depends_on",
                []
            )

            step.setdefault(
                "created_at",
                now
            )

            step.setdefault(
                "started_at",
                None
            )

            step.setdefault(
                "completed_at",
                None
            )

            step.setdefault(
                "failed_at",
                None
            )

            step.setdefault(
                "updated_at",
                now
            )

            step.setdefault(
                "output",
                None
            )

            step.setdefault(
                "result",
                None
            )

            step.setdefault(
                "error",
                None
            )

            step.setdefault(
                "execution_count",
                0
            )

    def _append_history(
        self,
        workflow: dict,
        event: dict
    ):

        workflow.setdefault(
            "execution_history",
            []
        ).append(
            dict(event)
        )

    @staticmethod
    def _now() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()
