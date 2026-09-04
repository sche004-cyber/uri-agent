from uri_core.core.clarification import (
    TASK_REQUIREMENTS,
    field_available_from_evidence,
)


def build_task_context(
    task: str,
    current_facts: dict,
    relevant_evidence: dict
) -> dict:
    """
    Build one structured context object for URI.

    Task facts remain separate from documentary
    evidence so the drafting system can distinguish
    user-provided information from VERIFIED facts.
    """

    if current_facts is None:
        current_facts = {}

    if relevant_evidence is None:
        relevant_evidence = {}

    requirements = TASK_REQUIREMENTS.get(
        task,
        []
    )

    missing_fields = []

    satisfied_fields = []

    for requirement in requirements:

        field_name = requirement["field"]

        # ---------------------------------------------
        # TASK FACT
        # ---------------------------------------------

        if field_name in current_facts:

            satisfied_fields.append(
                {
                    "field": field_name,
                    "source": "TASK_FACT",
                }
            )

            continue

        # ---------------------------------------------
        # VERIFIED EVIDENCE CONTEXT
        # ---------------------------------------------

        if field_available_from_evidence(
            field_name,
            relevant_evidence
        ):

            satisfied_fields.append(
                {
                    "field": field_name,
                    "source": "VERIFIED_EVIDENCE",
                }
            )

            continue

        # ---------------------------------------------
        # STILL MISSING
        # ---------------------------------------------

        missing_fields.append(
            field_name
        )

    return {
        "task": task,

        "task_facts": current_facts,

        "verified_evidence": relevant_evidence,

        "satisfied_fields": satisfied_fields,

        "missing_fields": missing_fields,

        "ready_to_draft": (
            len(missing_fields) == 0
        ),
    }


def get_draft_readiness(
    task: str,
    current_facts: dict,
    relevant_evidence: dict
) -> dict:
    """
    Return a simplified readiness report
    for the drafting workflow.
    """

    context = build_task_context(
        task=task,
        current_facts=current_facts,
        relevant_evidence=relevant_evidence,
    )

    return {
        "task": context["task"],

        "ready_to_draft": (
            context["ready_to_draft"]
        ),

        "missing_fields": (
            context["missing_fields"]
        ),

        "satisfied_fields": (
            context["satisfied_fields"]
        ),
    }

