from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DraftingMemory:
    """
    Stores URI drafting preferences and reusable
    document-writing guidance.

    This memory is separate from factual evidence.

    Evidence answers:
        What is true?

    Drafting memory answers:
        How should URI write?
    """

    global_preferences: Dict[str, object] = field(
        default_factory=dict
    )

    document_preferences: Dict[
        str,
        Dict[str, object]
    ] = field(
        default_factory=dict
    )

    style_examples: List[dict] = field(
        default_factory=list
    )


def create_default_drafting_memory() -> DraftingMemory:
    """
    Create URI's initial controlled drafting preferences.

    These defaults can later be learned, updated,
    reviewed, or edited by the user.
    """

    memory = DraftingMemory()

    memory.global_preferences = {

        "tone": "formal_administrative",

        "clarity": "clear_and_direct",

        "verbosity": "concise",

        "avoid_unverified_claims": True,

        "suggest_improvements": True,

        "ask_only_necessary_clarifications": True,
    }

    memory.document_preferences = {

        "noting": {

            "tone": "formal_administrative",

            "structure": [
                "subject",
                "background",
                "verified_context",
                "justification",
                "proposal",
            ],
        },

        "letter": {

            "tone": "formal_official",

            "structure": [
                "recipient",
                "subject",
                "reference_or_context",
                "main_message",
                "closing",
            ],
        },

        "notice": {

            "tone": "clear_official",

            "structure": [
                "heading",
                "subject",
                "instructions",
                "deadline",
                "authority",
            ],
        },

        "office_order": {

            "tone": "formal_administrative",

            "structure": [
                "order_heading",
                "authority",
                "decision",
                "instructions",
                "effective_date",
            ],
        },

        "minutes": {

            "tone": "formal_record",

            "structure": [
                "meeting_details",
                "agenda",
                "observations",
                "decisions",
                "action_points",
            ],
        },
    }

    return memory


def get_document_preferences(
    memory: DraftingMemory,
    document_type: str
) -> Dict[str, object]:
    """
    Return drafting preferences for a document type.
    """

    return memory.document_preferences.get(
        document_type,
        {}
    )


def update_global_preference(
    memory: DraftingMemory,
    name: str,
    value
):
    """
    Update a user-approved global drafting preference.
    """

    memory.global_preferences[name] = value


def update_document_preference(
    memory: DraftingMemory,
    document_type: str,
    name: str,
    value
):
    """
    Update a user-approved preference for a
    specific document type.
    """

    if document_type not in (
        memory.document_preferences
    ):

        memory.document_preferences[
            document_type
        ] = {}

    memory.document_preferences[
        document_type
    ][name] = value
