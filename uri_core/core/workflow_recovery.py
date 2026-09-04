from typing import Dict, List, Any


class WorkflowRecoveryValidator:

    SUPPORTED_SCHEMA_VERSIONS = {
        "1.0"
    }

    VALID_WORKFLOW_STATUSES = {
        "planned",
        "running",
        "waiting_for_input",
        "completed",
        "failed",
        "blocked"
    }

    VALID_STEP_STATUSES = {
        "pending",
        "running",
        "waiting_for_input",
        "completed",
        "failed",
        "blocked",
        "skipped"
    }

    TERMINAL_STEP_STATUSES = {
        "completed",
        "skipped"
    }

    TERMINAL_WORKFLOW_STATUSES = {
        "completed",
        "failed",
        "blocked"
    }

    @classmethod
    def validate(
        cls,
        workflow: Dict[str, Any]
    ) -> Dict[str, Any]:

        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(workflow, dict):

            return {
                "valid": False,
                "recoverable": False,
                "errors": [
                    "Workflow must be a dictionary."
                ],
                "warnings": []
            }

        workflow_id = workflow.get(
            "workflow_id"
        )

        if not workflow_id:

            errors.append(
                "Workflow is missing workflow_id."
            )

        schema_version = workflow.get(
            "schema_version"
        )

        if schema_version not in (
            cls.SUPPORTED_SCHEMA_VERSIONS
        ):

            errors.append(
                "Unsupported or missing workflow schema_version."
            )

        workflow_status = workflow.get(
            "status"
        )

        if workflow_status not in (
            cls.VALID_WORKFLOW_STATUSES
        ):

            errors.append(
                f"Invalid workflow status: {workflow_status!r}."
            )

        steps = workflow.get(
            "steps"
        )

        if not isinstance(steps, list):

            errors.append(
                "Workflow steps must be a list."
            )

            return cls._result(
                errors,
                warnings
            )

        step_ids = set()

        for index, step in enumerate(steps):

            if not isinstance(step, dict):

                errors.append(
                    f"Step {index} is not a dictionary."
                )

                continue

            step_id = step.get(
                "step_id"
            )

            if not step_id:

                errors.append(
                    f"Step {index} is missing step_id."
                )

            elif step_id in step_ids:

                errors.append(
                    f"Duplicate step_id: {step_id}."
                )

            else:

                step_ids.add(
                    step_id
                )

            status = step.get(
                "status"
            )

            if status not in (
                cls.VALID_STEP_STATUSES
            ):

                errors.append(
                    f"Invalid status for step "
                    f"{step_id!r}: {status!r}."
                )

            depends_on = step.get(
                "depends_on",
                []
            )

            if not isinstance(
                depends_on,
                list
            ):

                errors.append(
                    f"depends_on for step "
                    f"{step_id!r} must be a list."
                )

            else:

                if step_id in depends_on:

                    errors.append(
                        f"Step {step_id!r} cannot depend on itself."
                    )

            if (
                status == "completed"
                and not step.get("completed_at")
            ):

                errors.append(
                    f"Completed step {step_id!r} "
                    "is missing completed_at."
                )

            if (
                status == "failed"
                and not step.get("error")
            ):

                errors.append(
                    f"Failed step {step_id!r} "
                    "is missing error."
                )

        # Dependency references must point to real steps.
        for step in steps:

            if not isinstance(step, dict):
                continue

            step_id = step.get(
                "step_id"
            )

            for dependency in step.get(
                "depends_on",
                []
            ):

                if dependency not in step_ids:

                    errors.append(
                        f"Step {step_id!r} references "
                        f"missing dependency {dependency!r}."
                    )

        cycle = cls._find_dependency_cycle(
            steps
        )

        if cycle:

            errors.append(
                "Workflow contains a dependency cycle: "
                + " -> ".join(cycle)
            )

        waiting_steps = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and step.get("status")
                == "waiting_for_input"
            )
        ]

        failed_steps = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and step.get("status")
                == "failed"
            )
        ]

        running_steps = [
            step
            for step in steps
            if (
                isinstance(step, dict)
                and step.get("status")
                == "running"
            )
        ]

        if (
            workflow_status
            == "waiting_for_input"
            and not waiting_steps
        ):

            errors.append(
                "Workflow is waiting_for_input "
                "but has no waiting step."
            )

        if (
            workflow_status
            == "failed"
            and not failed_steps
        ):

            errors.append(
                "Workflow is failed "
                "but has no failed step."
            )

        if (
            workflow_status
            == "completed"
        ):

            incomplete = [
                step.get("step_id")
                for step in steps
                if (
                    isinstance(step, dict)
                    and step.get("status")
                    not in cls.TERMINAL_STEP_STATUSES
                )
            ]

            if incomplete:

                errors.append(
                    "Completed workflow contains "
                    "non-terminal steps: "
                    + ", ".join(
                        str(x)
                        for x in incomplete
                    )
                )

        # A running workflow loaded after a process restart is
        # potentially ambiguous. Do not silently rerun it.
        if (
            workflow_status == "running"
            and running_steps
        ):

            warnings.append(
                "Workflow contains running steps. "
                "A restart may have interrupted execution; "
                "automatic replay is unsafe without recovery review."
            )

        if (
            workflow_status
            in cls.TERMINAL_WORKFLOW_STATUSES
            and running_steps
        ):

            errors.append(
                "Terminal workflow contains running steps."
            )

        return cls._result(
            errors,
            warnings
        )

    @classmethod
    def is_safe_to_resume(
        cls,
        workflow: Dict[str, Any]
    ) -> bool:

        result = cls.validate(
            workflow
        )

        if not result["valid"]:
            return False

        status = workflow.get(
            "status"
        )

        if status == "waiting_for_input":

            return True

        if status == "planned":

            return True

        # Running workflows are deliberately NOT automatically
        # resumed because a running capability may have performed
        # an external side effect before the process stopped.
        return False

    @classmethod
    def recovery_action(
        cls,
        workflow: Dict[str, Any]
    ) -> Dict[str, Any]:

        validation = cls.validate(
            workflow
        )

        if not validation["valid"]:

            return {
                "action": "reject",
                "reason":
                    "Workflow failed structural validation.",
                "validation": validation
            }

        status = workflow.get(
            "status"
        )

        if status == "waiting_for_input":

            return {
                "action": "resume",
                "reason":
                    "Workflow is waiting for explicit user input.",
                "validation": validation
            }

        if status == "planned":

            return {
                "action": "resume",
                "reason":
                    "Workflow has not started execution.",
                "validation": validation
            }

        if status == "running":

            return {
                "action": "recovery_review",
                "reason":
                    "Workflow was running when recovery occurred; "
                    "automatic replay could duplicate a capability action.",
                "validation": validation
            }

        if status == "completed":

            return {
                "action": "already_complete",
                "reason":
                    "Workflow is already completed.",
                "validation": validation
            }

        if status == "failed":

            return {
                "action": "failed",
                "reason":
                    "Workflow previously failed and requires deliberate retry.",
                "validation": validation
            }

        if status == "blocked":

            return {
                "action": "blocked",
                "reason":
                    "Workflow is blocked and requires resolution.",
                "validation": validation
            }

        return {
            "action": "reject",
            "reason":
                f"Unknown workflow recovery state: {status!r}.",
            "validation": validation
        }

    @classmethod
    def _find_dependency_cycle(
        cls,
        steps: List[Dict[str, Any]]
    ):

        graph = {}

        for step in steps:

            if not isinstance(step, dict):
                continue

            step_id = step.get(
                "step_id"
            )

            if not step_id:
                continue

            graph[step_id] = list(
                step.get(
                    "depends_on",
                    []
                )
            )

        visiting = set()
        visited = set()
        path = []

        def visit(node):

            if node in visiting:

                try:
                    start = path.index(
                        node
                    )
                except ValueError:
                    start = 0

                return (
                    path[start:]
                    + [node]
                )

            if node in visited:
                return None

            visiting.add(node)
            path.append(node)

            for dependency in graph.get(
                node,
                []
            ):

                if dependency not in graph:
                    continue

                result = visit(
                    dependency
                )

                if result:
                    return result

            path.pop()
            visiting.remove(node)
            visited.add(node)

            return None

        for node in graph:

            result = visit(
                node
            )

            if result:
                return result

        return None

    @staticmethod
    def _result(
        errors,
        warnings
    ):

        return {
            "valid": len(errors) == 0,
            "recoverable": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
