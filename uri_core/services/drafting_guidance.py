"""Builds a *drafting brief* - the rules, conventions, and suggested
(never mandatory) structure the Brain is given to compose a document
(M17).

This is the piece the audit found missing: the layer that turns "the
user wants an office note / office order" plus a purpose plus the
institution's conventions into guidance the Brain can reason over,
rather than a Python template that emits a finished body. It wires in
the previously-orphaned drafting_memory (per-document-type suggested
sections and tone), augments it with purpose-specific *suggested*
sections, and attaches the institutional conventions and the operating
policy's drafting rules.

Nothing here writes document prose. `classify_purpose` produces a
label that *informs* structure; `build_drafting_brief` assembles
guidance. The Brain decides the actual structure and wording - a brief
is a set of options and constraints, never a fixed template. Memory
contributes suggested sections and tone; it can never force one layout,
because the composer is instructed to treat sections as a starting
point to adapt to the request, not a checklist to fill.
"""

from typing import Any, Dict, List, Optional

from uri_core.core.drafting_memory import (
    DraftingMemory,
    create_default_drafting_memory,
    get_document_preferences,
)


# Document-type inference from what was requested. A note and an order
# are genuinely different document *kinds*; this only picks the kind,
# never the structure (purpose does the structural shaping, and the
# Brain has final say over both).
def infer_document_type(request_text: str, requested_output: str = "") -> str:
    text = f"{requested_output} {request_text}".lower()

    if "order" in text or "sanction order" in text or "office order" in text:
        return "office_order"

    # Default administrative writing is a noting.
    return "noting"


# Purpose is the axis the old architecture completely ignored - it only
# ever saw the document noun. Two office orders (an appointment and a
# cancellation) need materially different structures; two notings (an
# approval request and a committee recommendation) do too. These labels
# are deliberately coarse and extensible: they nudge which *suggested*
# sections the brief offers, and are handed to the Brain so it can
# reason about intent. They never select a template.
_PURPOSE_KEYWORDS = {
    "cancellation": [
        "cancel", "cancellation", "rescind", "withdraw", "revoke",
        "annul", "supersede",
    ],
    "appointment": [
        "appoint", "appointment", "constitute", "constitution of",
        "nominate", "nomination", "committee to", "designate",
    ],
    "recommendation": [
        "recommend", "recommendation", "propose that", "suggest that",
        "committee recommends", "options",
    ],
    "procurement": [
        "procure", "procurement", "purchase", "purchasing", "buy",
        "tender", "quotation", "supply of",
    ],
    "approval": [
        "approval", "approve", "sanction", "permission", "kind approval",
    ],
    "delegation": [
        "delegate", "delegation of", "authorise", "authorize",
    ],
    "notice": [
        "notice", "notify", "circular", "inform all",
    ],
}

# Whether a request is urgent is a *modifier* on any purpose (an urgent
# approval, an urgent cancellation) - it changes tone/prominence, not
# the document's fundamental structure, so it is tracked separately.
_URGENCY_KEYWORDS = [
    "urgent", "urgently", "immediate", "immediately", "at the earliest",
    "time-sensitive", "expedite", "priority",
]


def classify_purpose(request_text: str) -> str:
    """A single best-guess purpose label from the request text. Falls
    back to "general" rather than forcing one of the known purposes - an
    unrecognised purpose is a normal case the Brain still drafts for,
    not an error. Order matters: more specific/structural purposes
    (cancellation, appointment) are checked before the very common
    "approval", so "cancel the approval granted earlier" reads as a
    cancellation, not an approval."""

    text = (request_text or "").lower()

    for purpose in (
        "cancellation",
        "appointment",
        "recommendation",
        "procurement",
        "delegation",
        "notice",
        "approval",
    ):
        for keyword in _PURPOSE_KEYWORDS[purpose]:
            if keyword in text:
                return purpose

    return "general"


def is_urgent(request_text: str) -> bool:
    text = (request_text or "").lower()
    return any(keyword in text for keyword in _URGENCY_KEYWORDS)


# Purpose-specific *suggested* sections, layered on top of the document
# type's base structure from drafting_memory. These are hints ("a
# cancellation usually references the original order and states its
# effect"), not required fields - the composer is told they are
# optional and adaptable. This is what lets an appointment order and a
# cancellation order come out genuinely differently while both remain
# the Brain's own composition.
_PURPOSE_SECTION_HINTS = {
    "cancellation": [
        "reference to the original order/decision being cancelled",
        "the operative statement of cancellation",
        "the effect and effective date of the cancellation",
    ],
    "appointment": [
        "the body/committee/person being appointed or constituted",
        "the members or appointee and their roles",
        "the terms of reference / duties / tenure",
    ],
    "recommendation": [
        "the matter and background",
        "the options or considerations examined",
        "the specific recommendation being put forward",
    ],
    "procurement": [
        "the item/service and quantity required",
        "the justification and, where known, the approximate cost",
        "the proposed mode of procurement",
    ],
    "approval": [
        "the specific approval/sanction being sought",
        "the justification for it",
    ],
    "delegation": [
        "the authority being delegated and to whom",
        "the scope and any limits of the delegation",
    ],
    "notice": [
        "the subject of the notice",
        "the instruction or information being conveyed",
        "any deadline and the issuing authority",
    ],
}


def _base_sections(
    drafting_memory: DraftingMemory,
    document_type: str,
) -> List[str]:
    prefs = get_document_preferences(drafting_memory, document_type)
    structure = prefs.get("structure")
    if isinstance(structure, list) and structure:
        return [str(item) for item in structure]
    # Unknown type: a minimal, neutral spine the Brain freely adapts.
    return ["subject", "body", "closing"]


def _base_tone(
    drafting_memory: DraftingMemory,
    document_type: str,
    global_default: str,
) -> str:
    prefs = get_document_preferences(drafting_memory, document_type)
    tone = prefs.get("tone")
    return str(tone) if tone else global_default


def build_drafting_brief(
    *,
    request_text: str,
    requested_output: str = "",
    document_type: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    preferences: Optional[Dict[str, Any]] = None,
    institutional_rules: Optional[Dict[str, Any]] = None,
    drafting_memory: Optional[DraftingMemory] = None,
    policy_rules: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the guidance the Brain composes from. Every field is
    advisory except the factual/evidence constraints and the
    institutional conventions, which are constraints the Brain must
    honour but still applies itself. `suggested_sections` combines the
    document type's remembered structure with purpose-specific hints -
    presented to the composer as a starting point to adapt, explicitly
    not a mandatory checklist."""

    memory = drafting_memory or create_default_drafting_memory()

    doc_type = document_type or infer_document_type(request_text, requested_output)
    purpose = classify_purpose(request_text)
    urgent = is_urgent(request_text)

    global_prefs = memory.global_preferences or {}
    base_tone = _base_tone(
        memory, doc_type, str(global_prefs.get("tone", "formal_administrative"))
    )

    suggested_sections = list(_base_sections(memory, doc_type))
    for hint in _PURPOSE_SECTION_HINTS.get(purpose, []):
        if hint not in suggested_sections:
            suggested_sections.append(hint)

    return {
        "document_type": doc_type,
        "purpose": purpose,
        "is_urgent": urgent,
        "tone": base_tone,
        # Guidance, adaptable - NOT a required list. The composer prompt
        # states this explicitly.
        "suggested_sections": suggested_sections,
        # Global writing preferences (concise, avoid unverified claims,
        # etc.) straight from drafting_memory - guidance the Brain
        # follows, learnable/editable, never a template.
        "writing_preferences": dict(global_prefs),
        # Institutional conventions the Brain must observe (name, offices,
        # signatory roles, reference-number FORMAT, register, formatting)
        # - all configurable data, no pre-rendered text.
        "institutional_rules": institutional_rules or {},
        # The operating policy's own drafting/review rules (section 11/12),
        # passed through verbatim so the single source of drafting rules
        # is the policy, not this module.
        "policy_rules": policy_rules or "",
        # Factual/evidence constraints: what the Brain may rely on. Empty
        # when nothing was verified - the Brain must then not invent facts.
        "evidence": evidence or {},
        # User preferences (communication style, autonomy) if the caller
        # had them - shape phrasing, never structure.
        "user_preferences": preferences or {},
    }
