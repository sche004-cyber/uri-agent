"""M30.5A: generic, directory-derived term relevance.

Shared by the tightened Unsupported Gate (decision_gates.py) and the
offline over-tooling evaluator (decision_engine.py) - one scoring
function, not two. This is NOT a phrase-specific word list: which
terms count as "generic" (down-weighted, carry little discriminating
power) is computed FROM the Capability Directory itself - any term
that appears in more than one registered capability's own summary is
generic for THIS directory, at THIS moment, automatically. Nothing
here hardcodes "search"/"unread email"/or any other literal phrase -
adding a tenth capability that also happens to say "search" simply
makes "search" generic for a tenth reason, with zero code change.

Root cause this addresses (M30.5's own finding): a bare term-overlap
score treated one shared generic word (e.g. "search", appearing in
web_search, gmail_search, and Gmail's own description alike) as a
"plausible match" regardless of real fit. Down-weighting document-
frequent terms is the standard, generic fix for exactly this - not a
new heuristic invented for Gmail specifically.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

_STOP_WORDS = {
    "a", "an", "and", "are", "do", "for", "have", "i", "in", "is", "it",
    "me", "my", "of", "on", "the", "that", "to", "with", "you", "your",
}


def _terms(text: str) -> Set[str]:
    """Mirrors uri_core.capabilities.discovery's own tokenization
    convention (regex word extraction + naive plural-stripping) rather
    than importing that module's private helper across a package
    boundary - the two are allowed to drift independently if either
    module's own needs change, without coupling them."""
    tokens = re.findall(r"[a-z0-9_]+", (text or "").lower())
    return {
        token[:-1] if token.endswith("s") and len(token) > 3 else token
        for token in tokens
        if token not in _STOP_WORDS
    }


def compute_term_document_frequency(directory: Any) -> Dict[str, int]:
    """capability_id count per term, across every entry's own name +
    summary + actions - the ONLY input to what counts as "generic."
    Recomputed fresh from whatever `directory.summaries()` returns
    right now - never cached, never stale, never a fixed list."""
    doc_freq: Dict[str, int] = {}
    try:
        summaries = directory.summaries()
    except Exception:
        return doc_freq
    for entry in summaries:
        text = " ".join(
            [
                str(entry.get("capability_id") or ""),
                str(entry.get("summary") or ""),
                " ".join(entry.get("actions") or []),
            ]
        )
        for term in _terms(text):
            doc_freq[term] = doc_freq.get(term, 0) + 1
    return doc_freq


def discriminating_overlap(
    goal_text: str, capability_text: str, doc_freq: Dict[str, int]
) -> Dict[str, Any]:
    """Real overlap terms, split into discriminating (appears in <= 1
    capability in this directory) vs. generic (appears in 2+). Returns
    both so a caller can decide its own threshold - this function makes
    no pass/fail judgment itself."""
    query = _terms(goal_text)
    affordance = _terms(capability_text)
    shared = query & affordance
    discriminating = {t for t in shared if doc_freq.get(t, 0) <= 1}
    generic = shared - discriminating
    denominator = max(1, len(query | affordance))
    return {
        "shared_terms": sorted(shared),
        "discriminating_terms": sorted(discriminating),
        "generic_terms": sorted(generic),
        "discriminating_score": len(discriminating) / denominator,
        "raw_score": len(shared) / denominator,
    }


def plausible_matches(
    directory: Any, goal_text: str, limit: int = 5, min_discriminating_score: float = 0.02
) -> List[Dict[str, Any]]:
    """The tightened replacement for a bare "any shared word" check:
    requires at least one DISCRIMINATING (non-generic-for-this-
    directory) shared term, at or above a real minimum score - never a
    hardcoded phrase, always derived from the directory's own current
    contents. Conservative by design (per the accepted M30.5A
    principle: false UNSUPPORTED is worse than an unresolved/low-
    confidence match) - min_discriminating_score is deliberately low,
    so this only excludes matches that are PURELY generic-word
    coincidence, not genuinely weak-but-real ones."""
    doc_freq = compute_term_document_frequency(directory)
    try:
        summaries = directory.summaries()
    except Exception:
        return []

    candidates = []
    for entry in summaries:
        text = " ".join(
            [
                str(entry.get("capability_id") or ""),
                str(entry.get("summary") or ""),
                " ".join(entry.get("actions") or []),
            ]
        )
        overlap = discriminating_overlap(goal_text, text, doc_freq)
        if overlap["discriminating_score"] >= min_discriminating_score:
            candidates.append(
                {
                    "capability": entry.get("capability_id"),
                    "score": overlap["discriminating_score"],
                    "matched_terms": overlap["discriminating_terms"],
                }
            )
    return sorted(candidates, key=lambda c: (-c["score"], c["capability"]))[:limit]
