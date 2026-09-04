from pathlib import Path

path = Path("uri_core/core/orchestrator.py")

text = path.read_text(encoding="utf-8")

old = '''        # ------------------------------------------------------
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
'''

new = '''        # ------------------------------------------------------
        # Validate persisted workflow structure FIRST.
        #
        # Even a waiting_for_input workflow must be structurally
        # valid before URI allows it to enter the normal resume
        # path.
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

        # ------------------------------------------------------
        # WAITING FOR INPUT IS PART OF THE NORMAL RESUME
        # LIFECYCLE, NOT CRASH RECOVERY.
        #
        # This bypass is allowed only after validation succeeds.
        # ------------------------------------------------------

        if (
            validation.get(
                "valid",
                False
            )
            and
            session.active_workflow_status
            == "waiting_for_input"
        ):

            return None
'''

if old not in text:
    raise RuntimeError(
        "Could not find the recovery validation block."
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
    "Recovery validation ordering repaired successfully."
)
