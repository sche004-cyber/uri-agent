from pathlib import Path

path = Path("uri_core/core/orchestrator.py")

text = path.read_text(encoding="utf-8")

# ============================================================
# Replace _recover_active_workflow completely
# ============================================================

start_marker = "    def _recover_active_workflow(\n"
end_marker = "    # ==========================================================\n    # RESUME ACTIVE WORKFLOW\n"

start = text.find(start_marker)

if start == -1:
    raise RuntimeError(
        "Could not find _recover_active_workflow."
    )

end = text.find(
    end_marker,
    start
)

if end == -1:
    raise RuntimeError(
        "Could not find resume-workflow marker."
    )

new_recovery = r'''    def _recover_active_workflow(
        self,
        session,
        session_id
    ):

        workflow = session.active_workflow

        # ------------------------------------------------------
        # WAITING FOR INPUT IS PART OF THE NORMAL RESUME
        # LIFECYCLE, NOT CRASH RECOVERY.
        #
        # This must remain compatible with the established
        # clarification/resume pipeline.
        # ------------------------------------------------------

        if (
            session.active_workflow_status
            == "waiting_for_input"
        ):

            return None

        # ------------------------------------------------------
        # Validate persisted workflow structure first.
        # ------------------------------------------------------

        validation = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        recovery = (
            WorkflowRecoveryValidator.recovery_action(
                workflow
            )
        )

        action = recovery.get(
            "action"
        )

        recovery_metadata = dict(
            recovery
        )

        recovery_metadata[
            "validation"
        ] = validation

        # ------------------------------------------------------
        # INVALID WORKFLOW
        # ------------------------------------------------------

        if (
            not validation.get(
                "valid",
                False
            )
            or action == "reject"
        ):

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_rejected",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "URI rejected the persisted workflow "
                            "because its recovery state is invalid."
                        ),

                    "workflow":
                        workflow,

                    "recovery":
                        recovery_metadata
                }
            }

        # ------------------------------------------------------
        # COMPLETED WORKFLOW
        #
        # Never re-execute it.
        # Clear the active workflow from the session so a future
        # user message is treated as a new request.
        # ------------------------------------------------------

        if action == "already_complete":

            self._clear_active_workflow(
                session
            )

            self._persist_session(
                session_id
            )

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "already_complete",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow was already completed. "
                            "URI will not re-execute it."
                        ),

                    "workflow":
                        workflow
                }
            }

        # ------------------------------------------------------
        # WORKFLOW WAS RUNNING WHEN URI RECOVERED
        #
        # Never automatically replay potentially side-effecting
        # work.
        # ------------------------------------------------------

        if action == "recovery_review":

            session.active_workflow_status = (
                "recovery_review"
            )

            self._persist_session(
                session_id
            )

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_review",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow was running when URI "
                            "recovered. Automatic replay is blocked "
                            "pending recovery review."
                        ),

                    "workflow":
                        workflow,

                    "recovery_required":
                        True
                }
            }

        # ------------------------------------------------------
        # FAILED WORKFLOW
        # ------------------------------------------------------

        if action == "failed":

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_failed",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow previously failed. "
                            "URI will not retry it automatically."
                        ),

                    "workflow":
                        workflow,

                    "retry_required":
                        True
                }
            }

        # ------------------------------------------------------
        # BLOCKED WORKFLOW
        # ------------------------------------------------------

        if action == "blocked":

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_blocked",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow is blocked and "
                            "requires resolution before it can continue."
                        ),

                    "workflow":
                        workflow
                }
            }

        # ------------------------------------------------------
        # PLANNED / RESUMABLE WORKFLOW
        # ------------------------------------------------------

        if action == "resume":

            return None

        # ------------------------------------------------------
        # UNKNOWN ACTION
        # ------------------------------------------------------

        return {
            "status":
                "success",

            "workflow":
                workflow,

            "execution": {
                "status":
                    "recovery_rejected",

                "recovery": {
                    "action":
                        "reject",

                    "reason":
                        (
                            "Unknown recovery action returned by "
                            "WorkflowRecoveryValidator."
                        ),

                    "validation":
                        validation
                },

                "reason":
                    (
                        "Unknown recovery action returned by "
                        "WorkflowRecoveryValidator."
                    ),

                "validation":
                    validation
            },

            "response": {
                "message":
                    (
                        "URI could not determine a safe recovery "
                        "action for the persisted workflow."
                    ),

                "workflow":
                    workflow
            }
        }

'''

text = (
    text[:start]
    + new_recovery
    + text[end:]
)


# ============================================================
# Repair main recovery gate.
#
# waiting_for_input must reach the existing resume path.
# ============================================================

old_gate = '''            if session.active_workflow is not None:

                recovery_result = (
                    self._recover_active_workflow(
                        session=session,
                        session_id=session_id
                    )
                )

                if recovery_result is not None:

                    recovery_result[
                        "session_id"
                    ] = session_id

                    self._persist_session(
                        session_id
                    )

                    return recovery_result

'''

if old_gate not in text:

    raise RuntimeError(
        "Could not find current recovery gate."
    )


new_gate = '''            if session.active_workflow is not None:

                recovery_result = (
                    self._recover_active_workflow(
                        session=session,
                        session_id=session_id
                    )
                )

                if recovery_result is not None:

                    recovery_result[
                        "session_id"
                    ] = session_id

                    return recovery_result

'''

text = text.replace(
    old_gate,
    new_gate,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)

print(
    "Recovery lifecycle repaired successfully."
)

print(
    "Waiting-for-input remains on the normal resume path."
)

print(
    "Recovery metadata restored under execution.recovery."
)

print(
    "Completed workflows are cleared from active session state."
)
