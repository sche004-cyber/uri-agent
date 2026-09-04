from pathlib import Path

# ============================================================
# 1. PATCH SESSION STATE
# ============================================================

state_path = Path("uri_core/core/state.py")

state_text = state_path.read_text(
    encoding="utf-8"
)

old_state = '''    active_workflow_question: Optional[str] = None
'''

new_state = '''    active_workflow_question: Optional[str] = None

    # True only when the active workflow was restored from
    # persistent storage and has not yet re-entered the normal
    # in-process workflow lifecycle.
    #
    # This is intentionally transient and is NOT serialized.
    active_workflow_recovered: bool = False
'''

if old_state not in state_text:
    raise RuntimeError(
        "Could not find SessionState active_workflow_question field."
    )

state_text = state_text.replace(
    old_state,
    new_state,
    1
)

old_load = '''            session.active_workflow_question = (
                data.get(
                    "active_workflow_question"
                )
            )

            return session
'''

new_load = '''            session.active_workflow_question = (
                data.get(
                    "active_workflow_question"
                )
            )

            # --------------------------------------------------
            # Mark the session as having restored workflow state.
            #
            # This flag is transient. It tells the orchestrator
            # that active_workflow came from persistent storage
            # and therefore must pass recovery validation before
            # URI allows automatic continuation.
            # --------------------------------------------------

            session.active_workflow_recovered = (
                session.active_workflow is not None
            )

            return session
'''

if old_load not in state_text:
    raise RuntimeError(
        "Could not find SessionManager workflow load block."
    )

state_text = state_text.replace(
    old_load,
    new_load,
    1
)

state_path.write_text(
    state_text,
    encoding="utf-8"
)

print(
    "SessionState recovery-origin tracking added."
)


# ============================================================
# 2. PATCH ORCHESTRATOR
# ============================================================

orch_path = Path(
    "uri_core/core/orchestrator.py"
)

orch_text = orch_path.read_text(
    encoding="utf-8"
)

# ------------------------------------------------------------
# Replace _save_paused_workflow so a newly paused workflow is
# explicitly considered an in-process workflow.
# ------------------------------------------------------------

start_marker = "    def _save_paused_workflow(\n"
end_marker = "    def _clear_active_workflow(\n"

start = orch_text.find(
    start_marker
)

if start == -1:
    raise RuntimeError(
        "Could not find _save_paused_workflow."
    )

end = orch_text.find(
    end_marker,
    start
)

if end == -1:
    raise RuntimeError(
        "Could not find _clear_active_workflow."
    )

new_save_method = '''    def _save_paused_workflow(
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
        # A workflow produced by the current execution path is
        # no longer considered a recovered workflow.
        # ------------------------------------------------------

        session.active_workflow_recovered = False

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

orch_text = (
    orch_text[:start]
    + new_save_method
    + orch_text[end:]
)

# ------------------------------------------------------------
# Replace recovery method with recovery-origin-aware logic.
# ------------------------------------------------------------

start_marker = "    def _recover_active_workflow(\n"
end_marker = "    # ==========================================================\n    # RESUME ACTIVE WORKFLOW\n"

start = orch_text.find(
    start_marker
)

if start == -1:
    raise RuntimeError(
        "Could not find _recover_active_workflow."
    )

end = orch_text.find(
    end_marker,
    start
)

if end == -1:
    raise RuntimeError(
        "Could not find resume-workflow marker."
    )

new_recovery_method = '''    def _recover_active_workflow(
        self,
        session,
        session_id
    ):

        workflow = session.active_workflow

        # ------------------------------------------------------
        # IMPORTANT LIFECYCLE RULE
        #
        # Only workflows restored from persistent storage enter
        # crash/restart recovery.
        #
        # A workflow created directly in the current process is
        # handled by the normal resume path.
        # ------------------------------------------------------

        if not getattr(
            session,
            "active_workflow_recovered",
            False
        ):

            return None

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
        # INVALID RESTORED WORKFLOW
        # ------------------------------------------------------

        if (
            not validation.get(
                "valid",
                False
            )
            or
            action == "reject"
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
        # WAITING FOR INPUT
        #
        # Valid restored paused workflows re-enter the established
        # clarification/resume lifecycle.
        # ------------------------------------------------------

        if (
            action == "resume"
            and
            session.active_workflow_status
            == "waiting_for_input"
        ):

            return None

        # ------------------------------------------------------
        # PLANNED WORKFLOW
        # ------------------------------------------------------

        if action == "resume":

            return None

        # ------------------------------------------------------
        # COMPLETED WORKFLOW
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
        # RUNNING WORKFLOW
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

orch_text = (
    orch_text[:start]
    + new_recovery_method
    + orch_text[end:]
)

# ------------------------------------------------------------
# Mark a recovered workflow as actively resumed once the user
# provides the clarification answer.
# ------------------------------------------------------------

old_resume = '''        if required_field:

            new_fact = Fact(
'''

new_resume = '''        if required_field:

            # The recovered workflow is now re-entering the
            # normal in-process execution lifecycle.
            session.active_workflow_recovered = False

            new_fact = Fact(
'''

if old_resume not in orch_text:
    raise RuntimeError(
        "Could not find clarification fact block."
    )

orch_text = orch_text.replace(
    old_resume,
    new_resume,
    1
)

orch_path.write_text(
    orch_text,
    encoding="utf-8"
)

print(
    "Orchestrator recovery-origin lifecycle repaired."
)
print(
    "Persisted workflows remain strictly validated."
)
print(
    "In-memory workflows use the normal resume path."
)
