"""M35 URIv1 -- A2.8H: D1RQ, a bounded query-construction repair on top of D1R.

Benchmark-only. Does NOT modify uri_v1/turn/*. Does NOT modify or overwrite
scripts/m35_a2_8f_detector_d1r.py (D1R's own telemetry stays reproducible
from its own file, exactly as A2.8F measured it, as the comparison point).
This is a fork of D1R into a SEPARATE module -- identical to D1R except for
the two frozen repairs below.

Frozen repair scope (per M35_URIV1_A2_8H's governing task, evidence-derived
from M35_URIV1_A2_8G_DETECTION_TO_RAR_BOUNDARY_AUDIT.md S3.1/S3.2/S4):

Q1 -- T1 (code/ID) no longer asserts an unsupported semantic type.
    A2.8G found the code/UUID mechanism hardcoded target_type_hint to the
    literal string "document" regardless of what the referenced object
    actually is, causing RAR's Level 4b to reject the pool (real candidate
    types are "pdf"/"approval") before Level 6's lexical evidence is ever
    tried. Repair: the code/UUID mechanism no longer asserts ANY type --
    coarse_type is None, exactly like every other mechanism whose head noun
    does not map to a known type word. This is not "code -> pdf" or
    "code -> approval" (explicitly prohibited); it is the removal of an
    unjustified assertion, not the addition of a benchmark-fitted one. The
    literal code/ID text itself is unchanged and unaffected.

Q2 -- T3 (possessive-'s NP) span boundary tightened by a general structural
    rule, not by comparison to any expected answer.
    A2.8G found the possessive-NP body could capture 1-2 words of
    unrelated following sentence content (a following prepositional phrase
    or a sentence-final adverb), which then poisons Level 6's absent-entity
    check. Repair, both changes general and corpus-independent:
      (a) the body-capture cap is reduced from 3 words to 2 -- English
          possessive-headed noun phrases ("X's [adjective] noun") are
          typically no longer than this, and a shorter cap mechanically
          reduces the chance of crossing into unrelated content, in any
          domain, not just this corpus;
      (b) the body stops at a small, closed, general set of English
          prepositions and degree/repetition adverbs (against/under/
          over/without/within/during/before/after/since/until/upon/
          despite/near/beside, and again/already/still/yet/once/twice/
          merely/simply/alone/just/too/also) -- both are genuinely closed
          English grammatical word classes, not phrases read off this
          corpus's own sentences (contrast with the negation-pattern
          overfitting A2.8E/A2.8F already found and repaired: that was one
          near-verbatim corpus phrase; this is two complete, independently
          enumerable closed word classes).
    This repair is NOT tuned to make any specific case's span exactly
    match its ground-truth span -- e.g. NB-G-03's true reference is
    "Tom's" alone, but nothing in "Tom's extension number" trips either
    stop condition (no preposition, no adverb -- "extension"/"number" are
    ordinary nouns), so D1RQ's span for that case remains the fuller
    "Tom's extension number", exactly as a general rule (not a benchmark
    memorization) predicts. This is reported honestly in the A2.8H
    execution report as "query repair insufficient" for that case, per
    the governing task's explicit instruction not to force it.

Explicitly out of scope for this repair (A2.8H's governing task, restated
here so this file's own diff stays self-documenting): NB-J-01's
"reply"->email vocabulary gap; RAR's stemming/plural gap; RAR's
all-or-nothing absent-entity check; candidate aliasing/identifier systems;
clause_text wiring; recency_rank/candidate-construction changes. None of
these six items is touched anywhere in this file.

Frozen boundary (unchanged from D1/D1R): may output presence/span/coarse-
type/recency-hint/scoped-negation only. MUST NOT output a candidate ID, a
ranking, or a resolution decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Type vocabulary -- overfitting repair (A2.8F S4, per A2.8E S9 finding 4).
#
# A2.8E found D1's TYPE_HEAD_WORDS mixed two things: (a) genuinely reusable,
# domain-neutral words already present in rar_deterministic.py's own
# GENERIC_TYPE_WORDS vocabulary (an existing, already-approved vocabulary,
# not corpus-derived), and (b) nine additions ("letter", "invoice", "roster",
# "minutes", "agenda", "certificate", "scan") that were plausibly chosen by
# reading this specific corpus's own candidate titles.
#
# Repair: GENERAL_TYPE_HEAD_WORDS below keeps ONLY words that also appear in
# rar_deterministic.py's own GENERIC_TYPE_WORDS set (mechanical reuse of an
# existing vocabulary, not a new one) plus the closed set of literal
# candidate_type values RARCandidate itself already documents in its own
# module docstring ("document", "email", "workflow", "spreadsheet",
# "person", "media") -- i.e. words this repository's OWN contracts already
# name, not words read off this corpus's fixtures. The nine corpus-flavored
# additions are removed entirely from D1R's default vocabulary. Effect on
# resolution coverage is measured and reported (A2.8F S4/S5), not assumed.
# ---------------------------------------------------------------------------
GENERAL_TYPE_HEAD_WORDS = {
    "document": "document", "documents": "document",
    "file": "document", "files": "document",
    "spreadsheet": "spreadsheet", "spreadsheets": "spreadsheet",
    "pdf": "pdf",
    "image": "image", "images": "image", "photo": "image", "photos": "image",
    "picture": "image", "pictures": "image",
    "email": "email", "emails": "email", "message": "email",
    "person": "person", "record": "record", "records": "record",
    "workflow": "workflow",
    "spreadsheet_file": "spreadsheet",
}

# ---------------------------------------------------------------------------
# T1 -- alphanumeric code/ID shape.
# residual cluster:        T1 (4 refs: NB-A-01/A-03/A-04/A-05)
# general mechanism:       orthographic shape of a short code/ID token
#                           (a run of 2-6 uppercase letters, an optional
#                           hyphen, and 2-6 digits) or a UUID
# implementation rule:     regex \b[A-Z]{2,6}-?\d{2,6}\b  and the standard
#                           8-4-4-4-12 hex UUID shape
# expected generalization: any invoice/PO/ticket/reference-number style
#                           code in any domain, not specific to this corpus
# false-positive risk:     low -- the shape (letters immediately followed
#                           by digits, or a UUID) rarely occurs by accident
#                           in ordinary prose
# ---------------------------------------------------------------------------
_CODE_ID_RE = re.compile(r"\b[A-Z]{2,6}-?\d{2,6}\b")
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
# A code/UUID is often introduced by a generic noun ("invoice INV-20417",
# "file <uuid>") -- when present, the noun is included in the span (matches
# what a human would mark), but the code/UUID alone is still sufficient to
# trigger detection when no such noun precedes it.
_CODE_INTRO_WORDS = {"invoice", "order", "po", "file", "ticket", "ref", "reference", "id"}

_FILENAME_RE = re.compile(
    r"\b[\w][\w\-]*\.(?:pdf|docx?|xlsx?|csv|jpe?g|png|pptx?|txt)\b", re.IGNORECASE
)
_QUOTED_RE = re.compile(r"(?<![A-Za-z])'([^']{2,80})'(?!s\b)|\"([^\"]{2,80})\"")

# ---------------------------------------------------------------------------
# T3 -- possessive-'s noun phrase.
# residual cluster:        T3 (5 refs: NB-C-03, F-02, G-03, J-03, L-11:r2)
# general mechanism:       English possessive marker ('s) attached to a
#                           capitalized or lowercase noun, optionally
#                           followed by a short head-noun phrase
# implementation rule:     regex \b\w+'s(\s+\w+){0,3}\b, using the same
#                           widened word-shape token as the NP scanner below
# expected generalization: any possessive-headed reference ("X's Y"),
#                           proper or common noun, not specific to any
#                           named person in this corpus
# false-positive risk:     low-moderate -- "it's"/"that's"/"what's"
#                           (contractions, not possessives) must be
#                           excluded; handled by excluding a small closed
#                           set of contraction stems, not corpus phrases
# ---------------------------------------------------------------------------
_CONTRACTION_STEMS = {"it", "that", "this", "what", "there", "he", "she", "who", "let"}

# Q2 repair -- two general, closed, corpus-independent English word classes
# the possessive-NP body must not cross into: prepositions (which typically
# introduce a prepositional phrase attached elsewhere in the sentence, not
# a continuation of the possessed noun) and degree/repetition adverbs
# (which typically modify the whole clause, not the possessed noun).
_POSSESSIVE_BODY_STOP_WORDS = {
    "against", "under", "over", "without", "within", "during", "before",
    "after", "since", "until", "upon", "despite", "near", "beside",
    "again", "already", "still", "yet", "once", "twice", "merely",
    "simply", "alone", "just", "too", "also",
}
_POSSESSIVE_BODY_STOP_RE = "|".join(_POSSESSIVE_BODY_STOP_WORDS)

# Body words deliberately exclude the apostrophe character so the greedy
# body-capture cannot swallow a SECOND, later possessive marker into one
# match (e.g. "what's Tom's extension number" must not be consumed as one
# unit with stem="what" -- excluding "'" from body words forces the regex
# to stop right before "Tom's", letting it start a fresh match there).
# Q2 repair: cap reduced from {0,3} to {0,2} (English possessive-headed NPs
# are typically no more than a short adjective+noun), and each body word is
# additionally barred from being one of _POSSESSIVE_BODY_STOP_WORDS, so the
# capture stops before crossing into a following prepositional phrase or a
# clause-final adverb rather than swallowing it.
_POSSESSIVE_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9&]*)'s\b"
    r"((?:\s+(?![A-Za-z][A-Za-z0-9&]*'s\b)(?!(?:" + _POSSESSIVE_BODY_STOP_RE + r")\b)"
    r"[A-Za-z][A-Za-z0-9&\-]*){0,2})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# T4 -- possessive-pronoun determiner NP; T5-simple -- quantifier NP.
# residual cluster:        T4 (4 refs), T5-simple (1 ref: NB-L-11:r1)
# general mechanism:       both are the SAME existing mechanism D1 already
#                           has (determiner-headed noun phrase) -- the only
#                           change is completing the determiner word class
#                           to include the closed sets of English possessive
#                           pronouns and simple quantifiers
# implementation rule:     widen the determiner alternation from
#                           (the|this|that|these|those) to also include
#                           (my|your|our|his|her|its|their) [T4] and
#                           (both|all|any) [T5-simple only -- "either"/
#                           "neither" deliberately excluded, since T5's
#                           compound case ("either...except") is explicitly
#                           out of scope per the task's S2 instruction]
# expected generalization: these are closed, complete English word classes
#                           (7 possessive pronouns, a handful of simple
#                           quantifiers) -- not corpus-specific
# false-positive risk:     same as D1's existing determiner mechanism,
#                           which A2.8E's overfitting audit found genuinely
#                           general; no new risk category introduced
# ---------------------------------------------------------------------------
_DETERMINERS = (
    "the", "this", "that", "these", "those",       # D1's original set
    "my", "your", "our", "his", "her", "its", "their",  # T4
    "both", "all", "any",                          # T5-simple
)

# ---------------------------------------------------------------------------
# T6 -- missing pronoun.
# residual cluster:        T6 (1 ref: NB-G-01)
# general mechanism:       none new -- pure completion of D1's own already-
#                           implemented closed 9-pronoun class
# implementation rule:     add "she" and "he" to the bare-pronoun set
# expected generalization: these are two of the most common English
#                           pronouns; omitting them was an oversight, not a
#                           deliberate scope boundary
# false-positive risk:     identical to D1's existing bare-pronoun
#                           mechanism (already measured, already accepted)
# ---------------------------------------------------------------------------
_BARE_PRONOUN_RE = re.compile(
    r"\b(it|this|that|them|him|her|they|these|those|she|he)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# T7 -- regex right-boundary fragility.
# residual cluster:        T7 (3 refs: NB-F-03, NB-L-10:r1, NB-L-10:r2)
# general mechanism:       two independent engineering fixes to the SAME
#                           existing NP-scanning mechanism, not a new
#                           linguistic capability:
#                           (a) the per-word token shape now accepts digits
#                               and "&" (so "Q3", "P&L"-style tokens do not
#                               break tokenization);
#                           (b) the NP scanner is rewritten from a single
#                               greedy regex with a fixed word cap (which
#                               fails the WHOLE match if no satisfying
#                               right boundary is found within the cap) to
#                               a token-based scan that always returns the
#                               longest valid prefix it actually found, with
#                               no all-or-nothing failure mode
# implementation rule:     see _scan_noun_phrases() below
# expected generalization: any noun phrase containing a digit/alphanumeric
#                           token, or any noun phrase whose real end
#                           boundary lies beyond the previous fixed cap, in
#                           any domain
# false-positive risk:     the token-scan approach is, if anything, LESS
#                           prone to over-matching than the old regex,
#                           because it stops deterministically at the first
#                           real stop-word/punctuation rather than
#                           attempting a long greedy consumption and only
#                           failing (or partially succeeding) at the cap
# ---------------------------------------------------------------------------
_WORD_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9&\'\-]*")

_NP_STOP_WORDS = {
    "and", "but", "so", "because", "which", "who", "that",
    "to", "for", "with", "by", "from", "about", "of", "under", "into",
}

# ---------------------------------------------------------------------------
# Negation -- overfitting repair (A2.8F S4, per A2.8E S9 finding 3).
#
# D1's original per-clause negation scoping included a literal pattern,
# r"\bno,?\s+the\s+other\b", that closely mirrors NB-H-06's exact wording
# ("no, the other scan..."). Repair: replaced with a general STRUCTURAL
# rule -- a relational exclusion is recognized when a negation cue
# (any of NEGATION_PATTERNS, or "not"/"no"/"never"/"except") co-occurs in
# the SAME clause as the demonstrative phrase "the other" or "another",
# regardless of their exact relative wording or punctuation. This keeps the
# same general CAPABILITY (detecting a purely relational exclusion with no
# named content) without requiring the specific corpus phrase "no, the
# other" to appear verbatim.
# ---------------------------------------------------------------------------
_NEGATION_CUE_RE = re.compile(
    r"\b(don't|dont|do not|not|never|no|cannot|can't|shouldn't|won't|except)\b",
    re.IGNORECASE,
)
_RELATIONAL_EXCLUSION_RE = re.compile(r"\b(the other|another)\b", re.IGNORECASE)


def _unmask(s: str, placeholders: List[str]) -> str:
    for i, orig in enumerate(placeholders):
        s = s.replace(f"\x00FN{i}\x00", orig)
    return s


def _split_clauses(text: str) -> Tuple[str, ...]:
    """Unchanged in mechanism from D1 -- masks filename tokens before
    sentence splitting so an internal "." is never treated as a sentence
    terminal, then splits on terminals/semicolons/strong conjunctions."""
    masked = text
    placeholders: List[str] = []
    for m in _FILENAME_RE.finditer(text):
        token = f"\x00FN{len(placeholders)}\x00"
        placeholders.append(m.group(0))
        masked = masked.replace(m.group(0), token, 1)
    sentences = re.split(r"[.?!]+", masked)
    sentences = [_unmask(s, placeholders) if placeholders else s for s in sentences]
    clauses: List[str] = []
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        parts = re.split(r";|\s*,\s*(?:and|but|while|so)\s+|\s*-\s*", s_clean)
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                clauses.append(p_clean)
    return tuple(clauses) if clauses else (text.strip(),)


_RECENCY_LEXICON: Tuple[Tuple[str, str], ...] = (
    (r"\bmost recent\b", "latest"),
    (r"\blatest\b", "latest"),
    (r"\bcurrent\b", "current"),
    (r"\bsame\b", "same"),
    (r"\bthe one before\b", "previous"),
    (r"\bone before\b", "previous"),
    (r"\bbefore (?:that|it)\b", "previous"),
    (r"\bprevious\b", "previous"),
    (r"\bearlier\b", "earlier"),
    (r"\bearliest\b", "earlier"),
    (r"\blast week\b", "earlier"),
    (r"\byesterday\b", "earlier"),
    (r"\brevised\b", "revised"),
    (r"\boriginal\b", "original"),
    (r"\bthe other\b", "other"),
)


def _recency_hint_for_text(text: str) -> Optional[str]:
    low = text.lower()
    for pat, hint in _RECENCY_LEXICON:
        if re.search(pat, low):
            return hint
    return None


def _type_hint_for_phrase(phrase: str) -> Optional[str]:
    tokens = re.findall(r"[a-zA-Z]+", phrase.lower())
    for tok in reversed(tokens):
        if tok in GENERAL_TYPE_HEAD_WORDS:
            return GENERAL_TYPE_HEAD_WORDS[tok]
    return None


def _clause_negation_spans(clause: str) -> Tuple[str, ...]:
    spans: List[str] = []
    for m in _NEGATION_CUE_RE.finditer(clause):
        spans.append(m.group(0))
    # General relational-exclusion structural rule (overfitting repair)
    if _NEGATION_CUE_RE.search(clause) and _RELATIONAL_EXCLUSION_RE.search(clause):
        m = _RELATIONAL_EXCLUSION_RE.search(clause)
        spans.append(m.group(0))
    seen: List[str] = []
    for s in spans:
        if s not in seen:
            seen.append(s)
    return tuple(seen)


def _scan_noun_phrases(clause: str) -> List[Tuple[str, str, int, int]]:
    """Token-based determiner-NP scan (T7 fix). Returns
    (full_span, np_body, start_idx, end_idx) tuples. Unlike D1's single
    greedy regex with a fixed cap, this always returns the longest run of
    non-stop-word tokens found after a determiner, with no failure mode:
    if the run is short, the match is short; it is never rejected outright
    for exceeding an artificial length limit.
    """
    tokens = [(m.group(0), m.start(), m.end()) for m in _WORD_TOKEN_RE.finditer(clause)]
    results: List[Tuple[str, str, int, int]] = []
    i = 0
    while i < len(tokens):
        word, start, end = tokens[i]
        if word.lower() in _DETERMINERS:
            body_tokens: List[Tuple[str, int, int]] = []
            j = i + 1
            prev_end = end
            while j < len(tokens) and len(body_tokens) < 12:
                w, s, e = tokens[j]
                if w.lower() in _NP_STOP_WORDS:
                    break
                # A comma is a general, deterministic phrase boundary --
                # stop the noun phrase there rather than crossing into
                # what is grammatically a separate clause/appositive.
                if "," in clause[prev_end:s]:
                    break
                body_tokens.append((w, s, e))
                prev_end = e
                j += 1
            if body_tokens:
                full_start = start
                full_end = body_tokens[-1][2]
                full_span = clause[full_start:full_end]
                np_body = " ".join(w for w, _, _ in body_tokens)
                results.append((full_span, np_body, i, j - 1))
                i = j
                continue
        i += 1
    return results


@dataclass(frozen=True)
class D1RReference:
    span: str
    clause_text: str
    coarse_type: Optional[str] = None
    recency_hint: Optional[str] = None
    negation_spans: Tuple[str, ...] = ()
    mechanism: str = ""


def detect_references(raw_text: str) -> Tuple[D1RReference, ...]:
    whole_text_spans: List[Tuple[str, str, str]] = []

    for m in _FILENAME_RE.finditer(raw_text):
        span = m.group(0)
        whole_text_spans.append((span, _type_hint_for_phrase(span) or "document", "filename_shape"))

    for m in _QUOTED_RE.finditer(raw_text):
        inner = (m.group(1) or m.group(2) or "").strip()
        if inner:
            whole_text_spans.append((inner, _type_hint_for_phrase(inner), "quoted_span"))

    for m in _UUID_RE.finditer(raw_text):
        span = m.group(0)
        # Include a preceding intro word if present (e.g. "file <uuid>")
        pre = raw_text[max(0, m.start() - 6):m.start()].strip().lower()
        full_span = f"file {span}" if pre.endswith("file") else span
        # Q1 repair: no type asserted -- a bare code/UUID carries no
        # deterministic evidence of what kind of object it names (it could
        # be an invoice, a purchase order, a file, a ticket...). Asserting
        # "document" was an unsupported guess; asserting "pdf" or
        # "approval" instead would just be a different unsupported guess
        # fitted to these specific corpus cases. None is the honest
        # representation of what the detector actually knows.
        whole_text_spans.append((full_span, None, "code_id_shape"))

    for m in _CODE_ID_RE.finditer(raw_text):
        span = m.group(0)
        if any(span in s for s, _, _ in whole_text_spans):
            continue
        # Include a preceding intro word if present (e.g. "invoice INV-20417")
        prefix_words = re.findall(r"[a-zA-Z]+", raw_text[max(0, m.start() - 12):m.start()])
        full_span = f"{prefix_words[-1]} {span}" if prefix_words and prefix_words[-1].lower() in _CODE_INTRO_WORDS else span
        whole_text_spans.append((full_span, None, "code_id_shape"))  # Q1 repair, same rationale

    for m in _POSSESSIVE_RE.finditer(raw_text):
        stem = m.group(1)
        if stem.lower() in _CONTRACTION_STEMS:
            continue
        full_span = (stem + "'s" + (m.group(2) or "")).strip()
        head = (m.group(2) or "").strip()
        whole_text_spans.append((full_span, _type_hint_for_phrase(head) if head else None, "possessive_np"))

    clauses = _split_clauses(raw_text)
    found: List[D1RReference] = []
    global_used_spans: List[str] = [s.lower() for s, _, _ in whole_text_spans]

    def _clause_containing(span: str) -> str:
        for c in clauses:
            if span.lower() in c.lower():
                return c
        return raw_text

    for span, coarse_type, mechanism in whole_text_spans:
        home_clause = _clause_containing(span)
        found.append(D1RReference(
            span=span, clause_text=home_clause, coarse_type=coarse_type,
            recency_hint=_recency_hint_for_text(home_clause),
            negation_spans=_clause_negation_spans(home_clause), mechanism=mechanism,
        ))

    for clause in clauses:
        clause_negation = _clause_negation_spans(clause)
        clause_recency = _recency_hint_for_text(clause)
        used_spans: List[str] = list(global_used_spans)

        for full_span, np_body, _, _ in _scan_noun_phrases(clause):
            if full_span.lower() in used_spans:
                continue
            body_tokens = np_body.lower().split()
            if all(t in {"one", "ones", "thing", "things"} for t in body_tokens):
                continue
            found.append(D1RReference(
                span=full_span, clause_text=clause,
                coarse_type=_type_hint_for_phrase(np_body),
                recency_hint=clause_recency or _recency_hint_for_text(full_span),
                negation_spans=clause_negation, mechanism="determiner_noun_phrase",
            ))
            used_spans.append(full_span.lower())

        for m in _BARE_PRONOUN_RE.finditer(clause):
            word = m.group(0)
            if any(word.lower() in s for s in used_spans):
                continue
            found.append(D1RReference(
                span=word.lower(), clause_text=clause, coarse_type=None,
                recency_hint=clause_recency, negation_spans=clause_negation, mechanism="bare_pronoun",
            ))
            used_spans.append(word.lower())

    return tuple(found)
