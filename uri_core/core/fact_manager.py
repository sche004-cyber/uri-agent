from uri_core.core.facts import Fact


def update_fact(
    session,
    new_fact: Fact
) -> dict:
    """
    Store a new task-specific fact while preserving
    the history of any previous value.
    """

    previous_fact = session.current_facts.get(
        new_fact.name
    )

    replaced = False
    previous_value = None

    if previous_fact:

        previous_value = previous_fact.value

        if previous_fact.value == new_fact.value:

            if (
                previous_fact.status != "VERIFIED"
                and new_fact.status == "VERIFIED"
            ):

                session.current_facts[
                    new_fact.name
                ] = new_fact

                return {
                    "fact": new_fact,
                    "replaced": False,
                    "previous_fact": previous_fact,
                    "action": "UPGRADED_TO_VERIFIED",
                }

            return {
                "fact": previous_fact,
                "replaced": False,
                "previous_fact": previous_fact,
                "action": "UNCHANGED",
            }

        previous_fact.status = "SUPERSEDED"

        session.historical_facts[
            new_fact.name
        ] = previous_fact

        # Full, append-only conflict history: unlike
        # historical_facts (kept above for backward compatibility,
        # holding only the most recently superseded value),
        # fact_history preserves every prior value for this name -
        # a second supersession never silently discards the first.
        session.fact_history.setdefault(
            new_fact.name, []
        ).append(previous_fact)

        replaced = True

    session.current_facts[
        new_fact.name
    ] = new_fact

    return {
        "fact": new_fact,
        "replaced": replaced,
        "previous_fact": previous_fact,
        "previous_value": previous_value,
        "action": (
            "SUPERSEDED"
            if replaced
            else "CREATED"
        ),
    }


def update_evidence_fact(
    session,
    evidence_fact: dict
) -> dict:
    """
    Convert documentary evidence into reusable
    URI evidence knowledge.
    """

    fact = Fact(
        name=evidence_fact["name"],
        value=evidence_fact["value"],
        status=evidence_fact.get(
            "status",
            "VERIFIED"
        ),
        source=evidence_fact.get(
            "source",
            "Evidence"
        )
    )

    previous_fact = session.evidence_facts.get(
        fact.name
    )

    replaced = False
    previous_value = None

    if previous_fact:

        previous_value = previous_fact.value

        if previous_fact.value == fact.value:

            if (
                previous_fact.status != "VERIFIED"
                and fact.status == "VERIFIED"
            ):

                session.evidence_facts[
                    fact.name
                ] = fact

                return {
                    "fact": fact,
                    "replaced": False,
                    "previous_fact": previous_fact,
                    "action": "UPGRADED_TO_VERIFIED",
                }

            return {
                "fact": previous_fact,
                "replaced": False,
                "previous_fact": previous_fact,
                "action": "UNCHANGED",
            }

        previous_fact.status = "SUPERSEDED"

        session.historical_facts[
            fact.name
        ] = previous_fact

        # See update_fact() above: fact_history is the full,
        # append-only conflict record; historical_facts keeps only
        # the most recent superseded value for backward
        # compatibility.
        session.fact_history.setdefault(
            fact.name, []
        ).append(previous_fact)

        replaced = True

    session.evidence_facts[
        fact.name
    ] = fact

    return {
        "fact": fact,
        "replaced": replaced,
        "previous_fact": previous_fact,
        "previous_value": previous_value,
        "action": (
            "SUPERSEDED"
            if replaced
            else "CREATED"
        ),
    }


def requires_approval_document(
    fact: Fact
) -> bool:

    approval_sensitive_fields = {
        "approval_requested",
        "approved_period",
        "financial_amount",
        "authority",
        "sanction",
        "decision",
    }

    return fact.name in approval_sensitive_fields
