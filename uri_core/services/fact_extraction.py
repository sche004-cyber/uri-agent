import re

from uri_core.core.facts import Fact


def extract_facts(
    message: str
) -> list[Fact]:
    """
    Extract simple structured facts from a user message.

    All extracted facts begin as PROVISIONAL.
    They must later be confirmed or verified.
    """

    facts = []

    message_lower = message.lower()

    # Current insurer
    insurer_match = re.search(
        r"(?:current\s+)?insurer\s+is\s+(.+?)(?:\.|$)",
        message,
        re.IGNORECASE
    )

    if insurer_match:

        insurer = insurer_match.group(1).strip()

        facts.append(
            Fact(
                name="insurer",
                value=insurer,
                status="PROVISIONAL",
                source="User",
            )
        )

    # Current expiry date
    expiry_match = re.search(
        r"(?:current\s+)?expiry\s+date\s+is\s+(.+?)(?:\.|$)",
        message,
        re.IGNORECASE
    )

    if expiry_match:

        expiry_date = (
            expiry_match.group(1).strip()
        )

        facts.append(
            Fact(
                name="expiry_date",
                value=expiry_date,
                status="PROVISIONAL",
                source="User",
            )
        )

    return facts