from typing import Dict, Any


def _get_value(
    facts: Dict[str, Any],
    field_name: str,
    default: str = ""
) -> str:

    fact = facts.get(field_name)

    if not fact:
        return default

    if hasattr(fact, "value"):
        return str(fact.value).strip()

    if isinstance(fact, dict):
        return str(
            fact.get("value", default)
        ).strip()

    return str(fact).strip()


def _clean_text(text: str) -> str:
    return text.strip().rstrip(".")


def _normalise_sentence(text: str) -> str:

    text = text.strip()

    if not text:
        return ""

    if text[-1] not in ".!?":
        text += "."

    return text


def _format_approval_request(
    approval_requested: str
) -> str:
    """
    Convert approval request text into natural
    administrative language.
    """

    approval = _clean_text(
        approval_requested
    )

    if not approval:
        return ""

    lower_approval = approval.lower()

    prefixes = [
        "approval for ",
        "approval of ",
        "sanction for ",
        "sanction of ",
        "permission for ",
        "permission to ",
    ]

    for prefix in prefixes:

        if lower_approval.startswith(prefix):

            remainder = approval[
                len(prefix):
            ].strip()

            return (
                prefix
                + remainder
            )

    return (
        approval[0].lower()
        + approval[1:]
    )


def _format_justification(
    justification: str
) -> str:
    """
    Convert justification input into a natural
    sentence without duplicating 'to'.
    """

    text = _clean_text(
        justification
    )

    if not text:
        return ""

    lower_text = text.lower()

    # Example:
    # "To provide insurance coverage"
    # becomes:
    # "The proposal is intended to provide..."

    if lower_text.startswith("to "):

        return (
            "The proposal is intended "
            + text[0].lower()
            + text[1:]
        )

    # Example:
    # "Provide insurance coverage"
    # becomes:
    # "The proposal is intended to provide..."

    return (
        "The proposal is intended to "
        + text[0].lower()
        + text[1:]
    )


def generate_noting(
    task_context: dict
) -> str:
    """
    Generate a controlled administrative noting
    using task facts and verified evidence only.
    """

    task = task_context.get("task")

    if task != "noting":

        raise ValueError(
            "Noting generator can only generate "
            "a noting task."
        )


    # =====================================================
    # CONTEXT
    # =====================================================

    task_facts = task_context.get(
        "task_facts",
        {}
    )

    evidence_facts = task_context.get(
        "verified_evidence",
        {}
    )


    # =====================================================
    # TASK INFORMATION
    # =====================================================

    subject = _get_value(
        task_facts,
        "subject"
    )

    if not subject:

        subject = _get_value(
            evidence_facts,
            "insurance_type",
            "Administrative Matter"
        )

    approval_requested = _get_value(
        task_facts,
        "approval_requested"
    )

    justification = _get_value(
        task_facts,
        "justification"
    )


    # =====================================================
    # VERIFIED EVIDENCE
    # =====================================================

    institution = _get_value(
        evidence_facts,
        "institution"
    )

    academic_year = _get_value(
        evidence_facts,
        "academic_year"
    )

    insurance_type = _get_value(
        evidence_facts,
        "insurance_type"
    )

    insurer = _get_value(
        evidence_facts,
        "insurer"
    )

    approx_total_students = _get_value(
        evidence_facts,
        "approx_total_students"
    )


    # =====================================================
    # BUILD DOCUMENT
    # =====================================================

    paragraphs = []

    paragraphs.append(
        "NOTING"
    )

    paragraphs.append(
        f"Subject: {subject}"
    )


    # -----------------------------------------------------
    # BACKGROUND
    # -----------------------------------------------------

    background_parts = []

    if institution:

        background_parts.append(
            f"The matter pertains to {institution}"
        )

    if insurance_type:

        if background_parts:

            background_parts.append(
                f"and concerns {insurance_type}"
            )

        else:

            background_parts.append(
                f"The matter concerns {insurance_type}"
            )

    if background_parts:

        paragraphs.append(
            " ".join(background_parts)
        )


    # -----------------------------------------------------
    # VERIFIED EVIDENCE SUMMARY
    # -----------------------------------------------------

    evidence_details = []

    if academic_year:

        evidence_details.append(
            f"the relevant academic year is "
            f"{academic_year}"
        )

    if insurer:

        evidence_details.append(
            f"the available documentary records "
            f"reference {insurer}"
        )

    if approx_total_students:

        evidence_details.append(
            f"the verified records indicate an "
            f"approximate student population of "
            f"{approx_total_students}"
        )

    if evidence_details:

        paragraphs.append(
            "Further, "
            + "; ".join(evidence_details)
        )


    # -----------------------------------------------------
    # JUSTIFICATION
    # -----------------------------------------------------

    formatted_justification = (
        _format_justification(
            justification
        )
    )

    if formatted_justification:

        paragraphs.append(
            formatted_justification
        )


    # -----------------------------------------------------
    # APPROVAL
    # -----------------------------------------------------

    formatted_approval = (
        _format_approval_request(
            approval_requested
        )
    )

    if formatted_approval:

        paragraphs.append(
            "In view of the above, "
            + formatted_approval
            + " is submitted for kind consideration "
            "and approval"
        )

    else:

        paragraphs.append(
            "The matter is submitted for "
            "kind consideration"
        )


    # =====================================================
    # FINAL CLEANUP
    # =====================================================

    final_paragraphs = []

    for paragraph in paragraphs:

        if paragraph == "NOTING":

            final_paragraphs.append(
                paragraph
            )

        elif paragraph.startswith(
            "Subject:"
        ):

            final_paragraphs.append(
                paragraph
            )

        else:

            final_paragraphs.append(
                _normalise_sentence(
                    paragraph
                )
            )


    return "\n\n".join(
        final_paragraphs
    )
