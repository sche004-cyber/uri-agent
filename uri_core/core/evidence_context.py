from typing import Dict


def get_verified_evidence(
    session
) -> Dict[str, object]:
    """
    Return only VERIFIED evidence facts from
    persistent session evidence memory.
    """

    verified_facts = {}

    for name, fact in (
        session.evidence_facts.items()
    ):

        if fact.status == "VERIFIED":

            verified_facts[name] = fact

    return verified_facts


def get_relevant_evidence(
    session,
    task: str,
    message: str = ""
) -> Dict[str, object]:
    """
    Return VERIFIED evidence relevant to the
    current administrative task.

    The active evidence context is retained so
    follow-up drafting tasks can continue the
    same documentary matter.
    """

    verified_facts = get_verified_evidence(
        session
    )

    if not verified_facts:
        return {}

    message_lower = message.lower()

    active_context = (
        getattr(
            session,
            "active_evidence_context",
            None
        )
        or ""
    ).lower()

    relevant_facts = {}

    # =====================================================
    # GENERAL RELEVANCE
    # =====================================================

    general_fields = {
        "institution",
        "academic_year",
    }

    for field_name in general_fields:

        if field_name in verified_facts:

            relevant_facts[
                field_name
            ] = verified_facts[field_name]

    # =====================================================
    # INSURANCE CONTEXT
    # =====================================================

    insurance_keywords = {
        "insurance",
        "medical",
        "student health",
        "group medical",
        "sbi general",
    }

    is_insurance_context = (
        any(
            keyword in message_lower
            for keyword in insurance_keywords
        )
        or any(
            keyword in active_context
            for keyword in insurance_keywords
        )
    )

    if is_insurance_context:

        insurance_fields = {
            "insurance_type",
            "insurer",
            "approx_total_students",
            "renewal_students",
            "fresh_students",
        }

        for field_name in insurance_fields:

            if field_name in verified_facts:

                relevant_facts[
                    field_name
                ] = verified_facts[field_name]

    return relevant_facts


def evidence_summary(
    evidence_facts: Dict[str, object]
) -> dict:
    """
    Create a simple serializable summary of
    evidence selected for the current task.
    """

    return {
        name: {
            "value": fact.value,
            "status": fact.status,
            "source": fact.source,
        }
        for name, fact in evidence_facts.items()
    }
