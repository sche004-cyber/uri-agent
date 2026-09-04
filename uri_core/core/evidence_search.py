def build_evidence_queries(
    task: str,
    current_facts: dict
) -> list:
    """
    Build focused evidence search queries
    from the active task and known facts.
    """

    queries = []

    subject_fact = current_facts.get(
        "subject"
    )

    insurer_fact = current_facts.get(
        "insurer"
    )

    if subject_fact:
        queries.append(
            subject_fact.value
        )

    if insurer_fact:
        queries.append(
            insurer_fact.value
        )

    if task == "noting":

        queries.append(
            "office order"
        )

        queries.append(
            "approval"
        )

        queries.append(
            "approved noting"
        )

    return queries


def evidence_search_required(
    approval_document_required: bool
) -> bool:
    """
    Decide whether URI should search
    for documentary evidence.
    """

    return approval_document_required