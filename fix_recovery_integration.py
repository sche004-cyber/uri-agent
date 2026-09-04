from pathlib import Path

path = Path("uri_core/core/orchestrator.py")

text = path.read_text(
    encoding="utf-8"
)

# ------------------------------------------------------------
# 1. Add recovery validator import.
# ------------------------------------------------------------

import_marker = """from uri_core.core.model_reasoning_gateway import (
    ModelReasoningGateway
)
"""

recovery_import = """from uri_core.core.workflow_recovery import (
    WorkflowRecoveryValidator
)
"""

if recovery_import not in text:

    if import_marker not in text:
        raise RuntimeError(
            "Could not find ModelReasoningGateway import marker."
        )

    text = text.replace(
        import_marker,
        import_marker + recovery_import,
        1
    )


# ------------------------------------------------------------
# 2. Add recovery helper methods.
# ------------------------------------------------------------

method_marker = """    # ==========================================================
    # RESUME ACTIVE WORKFLOW
    # ==========================================================
"""

recovery_methods = r'''    # ==========================================================
    # WORKFLOW RECOVERY
    # ==========================================================

    def _recover_active_workflow(
        self,
        session,
        session_id
    ):

        workflow = session.active_workflow

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

        # ------------------------------------------------------
        # Invalid persisted workflow.
        # ------------------------------------------------------

        if action == "reject":

            return {
                "status": "success",
                "workflow": workflow,
                "execution": {
                    "status":
                        "recovery_rejected",

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

                    "validation":
                        validation
                }
            }

        # ------------------------------------------------------
        # Already completed.
        #
        # Never send a completed workflow back to the executor.
        # ------------------------------------------------------

        if action == "already_complete":

            return {
                "status": "success",
                "workflow": workflow,
                "execution": {
                    "status":
                        "already_complete",

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },
                "response": {
                    "message":
                        "This workflow was already completed. URI will not re-execute it.",

                    "workflow":
                        workflow
                }
            }

        # ------------------------------------------------------
        # Running after restart.
        #
        # Never automatically replay a potentially side-effecting
        # running capability.
        # ------------------------------------------------------

        if action == "recovery_review":

            return {
                "status": "success",
                "workflow": workflow,
                "execution": {
                    "status":
                        "recovery_review",

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
        # Failed workflow.
        #
        # Do not silently retry a failed workflow.
        # ------------------------------------------------------

        if action == "failed":

            return {
                "status": "success",
                "workflow": workflow,
                "execution": {
                    "status":
                        "recovery_failed",

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
        # Blocked workflow.
        # ------------------------------------------------------

        if action == "blocked":

            return {
                "status": "success",
                "workflow": workflow,
                "execution": {
                    "status":
                        "recovery_blocked",

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
        # Planned or waiting_for_input.
        #
        # These states are safe to continue through the existing
        # deterministic resume path.
        # ------------------------------------------------------

        if action == "resume":

            return None

        # ------------------------------------------------------
        # Defensive fallback.
        # ------------------------------------------------------

        return {
            "status": "success",
            "workflow": workflow,
            "execution": {
                "status":
                    "recovery_rejected",

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

if recovery_methods not in text:

    if method_marker not in text:
        raise RuntimeError(
            "Could not find active-workflow resume marker."
        )

    text = text.replace(
        method_marker,
        recovery_methods + method_marker,
        1
    )


# ------------------------------------------------------------
# 3. Insert recovery gate before the existing waiting-for-input
#    resume logic.
# ------------------------------------------------------------

old_gate = """            # --------------------------------------------------
            # Resume a previously paused workflow first.
            # --------------------------------------------------

            if (
                session.active_workflow is not None
                and
                session.active_workflow_status
                == "waiting_for_input"
            ):
"""

new_gate = """            # --------------------------------------------------
            # Recover any persisted active workflow before normal
            # request processing.
            #
            # The recovery validator is authoritative for persisted
            # workflow state. The model never decides recovery.
            # --------------------------------------------------

            if session.active_workflow is not None:

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

            # --------------------------------------------------
            # Resume a previously paused workflow first.
            # --------------------------------------------------

            if (
                session.active_workflow is not None
                and
                session.active_workflow_status
                == "waiting_for_input"
            ):
"""

if old_gate not in text:

    # The current file may use the shorter legacy comment.
    old_gate_legacy = """            # -----------------------------------------
            # Resume paused workflow
            # -----------------------------------------

            if (
                session.active_workflow is not None
                and session.active_workflow_status
                == "waiting_for_input"
            ):
"""

    if old_gate_legacy in text:

        new_gate = new_gate.replace(
            """            # --------------------------------------------------
            # Resume a previously paused workflow first.
            # --------------------------------------------------
""",
            """            # --------------------------------------------------
            # Resume a previously paused workflow first.
            # --------------------------------------------------
"""
        )

        text = text.replace(
            old_gate_legacy,
            new_gate,
            1
        )

    else:
        raise RuntimeError(
            "Could not find the existing active-workflow resume gate."
        )

else:

    text = text.replace(
        old_gate,
        new_gate,
        1
    )


# ------------------------------------------------------------
# 4. Keep the persisted workflow state intact for recovery
#    review / already-complete / rejection.
# ------------------------------------------------------------

path.write_text(
    text,
    encoding="utf-8"
)

print(
    "Recovery integration repaired successfully."
)

print(
    "Updated:",
    path
)
