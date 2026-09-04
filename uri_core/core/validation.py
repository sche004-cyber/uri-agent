from typing import List

from uri_core.core.facts import Fact


def validate_fact(
    fact: Fact
) -> List[str]:
    """
    Validate a single URI fact.

    Returns a list of warnings or errors.
    """

    issues = []

    try:
        fact.validate_status()

    except ValueError as error:
        issues.append(str(error))

    if not fact.name.strip():
        issues.append(
            "Fact name cannot be empty."
        )

    if not fact.value.strip():
        issues.append(
            f"Fact '{fact.name}' has no value."
        )

    if (
        fact.status == "CONFIRMED"
        and not fact.confirmed_by
    ):
        issues.append(
            f"Confirmed fact '{fact.name}' "
            "does not record who confirmed it."
        )

    return issues


def validate_facts(
    facts: List[Fact]
) -> List[str]:
    """
    Validate multiple facts.
    """

    issues = []

    for fact in facts:

        fact_issues = validate_fact(fact)

        issues.extend(
            fact_issues
        )

    return issues


def can_use_as_current(
    fact: Fact
) -> bool:
    """
    Historical, expired, superseded and provisional
    facts cannot automatically be used as current facts.
    """

    return (
        fact.status == "CONFIRMED"
    )