from typing import Optional


TASK_PATTERNS = {
    "noting": [
        "draft a noting",
        "prepare a noting",
        "make a noting",
        "draft noting",
    ],

    "office_order": [
        "draft an office order",
        "draft office order",
        "prepare an office order",
        "make an office order",
    ],

    "notice": [
        "draft a notice",
        "prepare a notice",
        "make a notice",
    ],

    "letter": [
        "draft a letter",
        "prepare a letter",
        "make a letter",
    ],

    "mom": [
        "draft minutes",
        "prepare minutes",
        "draft a mom",
        "prepare a mom",
    ],

    "precedent_search": [
        "find previous",
        "find an old",
        "previous order",
        "previous noting",
        "previous notice",
        "previous minutes",
        "similar example",
        "historical precedent",
    ],

    "rules": [
        "what rule",
        "which rule",
        "applicable rule",
        "what is the procedure",
        "is it permissible",
    ],
}


def detect_intent(
    text: str
) -> Optional[str]:
    """
    Detect the main administrative task
    requested by the user.
    """

    text = text.lower()

    for task, patterns in TASK_PATTERNS.items():

        for pattern in patterns:

            if pattern in text:
                return task

    return "general"