TASK_REQUIREMENTS = {

    "noting": [
        {
            "field": "subject",
            "question": (
                "What is the subject or matter "
                "for the noting?"
            ),
        },
        {
            "field": "approval_requested",
            "question": (
                "What approval or decision is "
                "being requested?"
            ),
        },
        {
            "field": "justification",
            "question": (
                "What is the reason or justification "
                "for the proposal?"
            ),
        },
    ],

    "letter": [
        {
            "field": "recipient",
            "question": (
                "Who is the recipient of the letter?"
            ),
        },
        {
            "field": "subject",
            "question": (
                "What is the subject of the letter?"
            ),
        },
        {
            "field": "purpose",
            "question": (
                "What is the purpose or main message "
                "of the letter?"
            ),
        },
    ],
}


def field_available_from_evidence(
    field_name: str,
    relevant_evidence
) -> bool:
    """
    Check whether a required field is already
    satisfied by relevant verified evidence.

    Supports both dictionaries and lists of
    evidence dictionaries.
    """

    if not relevant_evidence:
        return False

    # Direct evidence dictionary
    if isinstance(relevant_evidence, dict):
        return field_name in relevant_evidence

    # Collection of evidence dictionaries
    if isinstance(relevant_evidence, (list, tuple, set)):

        for evidence in relevant_evidence:

            if not isinstance(evidence, dict):
                continue

            # Direct field match
            if field_name in evidence:
                return True

            # Nested facts / metadata if present
            for key in (
                "facts",
                "verified_facts",
                "current_facts",
                "data",
            ):

                nested = evidence.get(key)

                if isinstance(nested, dict):

                    if field_name in nested:
                        return True

        return False

    return False

def get_next_question(
    task: str,
    current_facts: dict,
    relevant_evidence: dict = None
):
    """
    Find the first required field that has not
    been provided by task facts or satisfied by
    relevant verified evidence.

    Returns one clarification question at a time.
    """

    requirements = TASK_REQUIREMENTS.get(
        task,
        []
    )

    if relevant_evidence is None:
        relevant_evidence = {}

    for requirement in requirements:

        field_name = requirement["field"]

        # -----------------------------------------------
        # TASK FACT AVAILABLE
        # -----------------------------------------------

        if field_name in current_facts:
            continue

        # -----------------------------------------------
        # VERIFIED EVIDENCE AVAILABLE
        # -----------------------------------------------

        if field_available_from_evidence(
            field_name,
            relevant_evidence
        ):
            continue

        return {
            "field": field_name,
            "question": requirement["question"],
        }

    return None

