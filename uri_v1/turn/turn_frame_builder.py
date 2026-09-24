"""Deterministic Turn Preprocessor: builds TurnFrame from raw user text (Batch A2.3).

Performs lexical, grammatical, and surface extraction only.
ZERO semantic inference:
  - Does NOT decide whether an action is requested or prohibited.
  - Does NOT resolve references to specific files or prior sessions.
  - Does NOT choose the user's primary goal.
  - Does NOT choose tools or capabilities.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from uri_v1.turn.contracts import AttachmentReference
from uri_v1.turn.turn_frame import CandidateAction, CandidateReference, TurnFrame

# Lexical dictionaries for surface detection
NEGATION_PATTERNS = [
    r"\bdon't\b",
    r"\bdont\b",
    r"\bdo not\b",
    r"\bnot\b",
    r"\bnever\b",
    r"\bno\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bshouldn't\b",
    r"\bwon't\b",
]

COMMON_ACTION_VERBS = [
    "convert",
    "send",
    "draft",
    "bring",
    "find",
    "compare",
    "open",
    "make",
    "submit",
    "use",
    "summarize",
    "revise",
    "review",
    "shorten",
    "repeat",
    "explain",
    "change",
    "identify",
    "show",
    "list",
    "tell",
    "create",
    "write",
    "compose",
    "delete",
    "move",
    "check",
    "update",
    "export",
    "share",
    "schedule",
    "rewrite",
    "translate",
    "archive",
    "generate",
    "reply",
]

# Ordered multi-word and single-word reference patterns
REFERENCE_PATTERNS = [
    r"\bthe one we just created\b",
    r"\bthe earlier one\b",
    r"\bearlier one\b",
    r"\bsame thing\b",
    r"\bsame version\b",
    r"\bthat file\b",
    r"\bthis file\b",
    r"\bthis one\b",
    r"\blatest letter\b",
    r"\bprevious approval\b",
    r"\battached PDF\b",
    r"\bthis spreadsheet\b",
    r"\bthis\b",
    r"\bthat\b",
    r"\bit\b",
    r"\bthem\b",
    r"\bhim\b",
    r"\bher\b",
    r"\bthey\b",
    r"\bthese\b",
    r"\bthose\b",
]

TEMPORAL_PATTERNS = [
    r"\bafter they approve it\b",
    r"\bafter they have approved it\b",
    r"\bafter approval\b",
    r"\bbefore 2025\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\bearlier\b",
    r"\blatest\b",
    r"\btwice\b",
    r"\b2025\b",
    r"\b2026\b",
]

EXPLICIT_NUMBER_PATTERNS = [
    r"\b\d+\b",
    r"\bone page\b",
    r"\bone\b",
    r"\btwice\b",
    r"\btwo\b",
    r"\bthree\b",
]

FORMAT_PATTERNS = [
    r"\bPDF\b",
    r"\btable\b",
    r"\bspreadsheet\b",
    r"\bemail\b",
    r"\bdocx?\b",
    r"\bIndian English\b",
    r"\bHinglish\b",
    r"\bformal\b",
    r"\bshort\b",
]

ARTIFACT_PATTERNS = [
    r"\bfile\b",
    r"\bemail\b",
    r"\border\b",
    r"\bletter\b",
    r"\bcalculator\b",
    r"\bdraft\b",
    r"\bspreadsheet\b",
    r"\bapproval\b",
    r"\bdocument\b",
]

ENTITY_PATTERNS = [
    r"\bChief Warden\b",
    r"\bcommittee\b",
]


def _dedupe_keep_order(items: Sequence[str]) -> Tuple[str, ...]:
    seen: List[str] = []
    for item in items:
        item_str = item.strip()
        if item_str and item_str not in seen:
            seen.append(item_str)
    return tuple(seen)


def _split_clauses(text: str) -> Tuple[str, ...]:
    """Splits text into clauses on punctuation and coordinating conjunctions."""
    # Split on sentence terminals first
    sentences = re.split(r"[.?!]+", text)
    clauses: List[str] = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        # Split on semicolons or strong clause conjunctions
        parts = re.split(r";|\s*,\s*(?:and|but|while)\s+|\s*,\s*", s_clean)
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                clauses.append(p_clean)
    return tuple(clauses) if clauses else (text.strip(),)


def build_turn_frame(
    raw_text: str,
    attachments: Optional[Sequence[AttachmentReference]] = None,
) -> TurnFrame:
    """Deterministically extracts surface observations from the raw user turn."""
    normalized_text = " ".join(raw_text.split())
    clauses = _split_clauses(raw_text)

    # 1. Negation spans
    negations: List[str] = []
    for pat in NEGATION_PATTERNS:
        for match in re.finditer(pat, normalized_text, re.IGNORECASE):
            negations.append(match.group(0))

    # 2. Candidate actions
    candidate_actions: List[CandidateAction] = []
    action_counter = 1
    seen_verbs: List[str] = []
    for c_idx, clause in enumerate(clauses):
        clause_lower = clause.lower()
        for verb in COMMON_ACTION_VERBS:
            if re.search(r"\b" + re.escape(verb) + r"\b", clause_lower):
                if verb not in seen_verbs:
                    candidate_actions.append(
                        CandidateAction(
                            id=f"a{action_counter}",
                            verb=verb,
                            clause_index=c_idx,
                        )
                    )
                    action_counter += 1
                    seen_verbs.append(verb)

    # 3. Candidate references
    candidate_references: List[CandidateReference] = []
    ref_counter = 1
    seen_refs: List[str] = []
    for c_idx, clause in enumerate(clauses):
        clause_lower = clause.lower()
        for pat in REFERENCE_PATTERNS:
            for match in re.finditer(pat, clause_lower):
                expr = match.group(0).strip()
                if expr not in seen_refs:
                    candidate_references.append(
                        CandidateReference(
                            id=f"r{ref_counter}",
                            expression=expr,
                            clause_index=c_idx,
                        )
                    )
                    ref_counter += 1
                    seen_refs.append(expr)

    # 4. Temporal surface spans
    temporals: List[str] = []
    for pat in TEMPORAL_PATTERNS:
        for match in re.finditer(pat, normalized_text, re.IGNORECASE):
            temporals.append(match.group(0))

    # 5. Explicit numbers
    numbers: List[str] = []
    for pat in EXPLICIT_NUMBER_PATTERNS:
        for match in re.finditer(pat, normalized_text, re.IGNORECASE):
            numbers.append(match.group(0))

    # 6. Explicit formats
    formats: List[str] = []
    for pat in FORMAT_PATTERNS:
        for match in re.finditer(pat, normalized_text, re.IGNORECASE):
            formats.append(match.group(0))

    # 7. Artifact mentions
    artifacts: List[str] = []
    for pat in ARTIFACT_PATTERNS:
        for match in re.finditer(pat, normalized_text, re.IGNORECASE):
            artifacts.append(match.group(0).lower())

    # 8. Entity surface mentions
    entities: List[str] = []
    for pat in ENTITY_PATTERNS:
        for match in re.finditer(pat, normalized_text, re.IGNORECASE):
            entities.append(match.group(0))

    # 9. Quoted spans
    quotes: List[str] = []
    for match in re.finditer(r"['\"]([^'\"]+)['\"]", raw_text):
        quotes.append(match.group(1).strip())

    # Attachments
    att_tuple = tuple(attachments or ())

    return TurnFrame(
        raw_text=raw_text,
        normalized_text=normalized_text,
        clauses=clauses,
        negation_spans=_dedupe_keep_order(negations),
        candidate_actions=tuple(candidate_actions),
        candidate_references=tuple(candidate_references),
        temporal_surface_spans=_dedupe_keep_order(temporals),
        explicit_numbers=_dedupe_keep_order(numbers),
        explicit_formats=_dedupe_keep_order(formats),
        artifact_mentions=_dedupe_keep_order(artifacts),
        entity_surface_mentions=_dedupe_keep_order(entities),
        quoted_spans=_dedupe_keep_order(quotes),
        attachments=att_tuple,
    )
