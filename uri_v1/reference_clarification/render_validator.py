"""Deterministic render validation for template and later supplied wording."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from uri_v1.turn.rar_clarification_contract import ClarificationContract
from .render_contracts import RenderOutput, make_render_request


_SELECTION = re.compile(r"\b(?:i'?ll use|i assume|i'?ve selected|going with|recommended)\b", re.I)
_WORD = re.compile(r"[\w.]+", re.UNICODE)
_ALLOW = {"which", "item", "do", "you", "mean", "by", "did", "matches", "what", "should", "i", "use",
          "could", "not", "find", "refers", "to", "there", "are", "other", "can", "enter", "one", "the",
          "owner", "type", "title", "recency", "and", "more", "document", "email", "person", "file"}


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    flags: tuple[str, ...]


def _tokens(text: str) -> set[str]:
    return {m.group().strip(".").casefold() for m in _WORD.finditer(text) if m.group().strip(".")}


def validate_render(contract: ClarificationContract, output: object,
                    *, excluded_facts: tuple[str, ...] = (),
                    question_limit: int = 300, label_limit: int = 180) -> ValidationResult:
    flags: list[str] = []
    if isinstance(output, str):
        try:
            def no_duplicate_keys(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate JSON key")
                    result[key] = value
                return result
            output = json.loads(output, object_pairs_hook=no_duplicate_keys)
        except (json.JSONDecodeError, ValueError):
            return ValidationResult(False, ("V-SCHEMA",))
    if isinstance(output, dict):
        if set(output) != {"question", "labels"} or not isinstance(output["labels"], dict):
            return ValidationResult(False, ("V-SCHEMA",))
        output = RenderOutput(output["question"], tuple(output["labels"].items()))
    if not isinstance(output, RenderOutput) or not isinstance(output.question, str) or not isinstance(output.labels, tuple):
        return ValidationResult(False, ("V-SCHEMA",))
    request = make_render_request(contract)
    expected = tuple(key for key, _ in request.slots)
    try:
        keys = tuple(key for key, label in output.labels)
        labels = tuple(label for _, label in output.labels)
        if any(not isinstance(key, str) or not isinstance(label, str) for key, label in output.labels):
            return ValidationResult(False, ("V-SCHEMA",))
    except (TypeError, ValueError):
        return ValidationResult(False, ("V-SCHEMA",))
    if any(key not in expected for key in keys):
        flags.append("V-SLOT-UNKNOWN")
    if any(key not in keys for key in expected):
        flags.append("V-SLOT-MISSING")
    if len(keys) != len(expected) or len(keys) != len(set(keys)):
        flags.append("V-EXTRA-OPTION")
    if keys != expected and set(keys) == set(expected):
        flags.append("V-ORDER")
    if len({" ".join(x.casefold().split()) for x in labels}) != len(labels):
        flags.append("V-LABEL-DUP")
    if len(output.question) > question_limit or any(len(x) > label_limit for x in labels):
        flags.append("V-LENGTH")
    slot_facts = {key: tuple(value for _, value in facts) for key, facts in request.slots}
    unsupported_selection = _SELECTION.search(output.question.replace(request.reference, ""))
    for key, label in output.labels:
        for match in _SELECTION.finditer(label):
            if not any(match.group().casefold() in fact.casefold() for fact in slot_facts.get(key, ())):
                unsupported_selection = match
    if unsupported_selection:
        flags.append("V-SELECTION")
    common = _tokens(request.reference) | _ALLOW | ({str(request.overflow)} if request.overflow else set())
    all_facts = {key: _tokens(" ".join(v for _, v in facts)) for key, facts in request.slots}
    if any(token not in common | set().union(*all_facts.values()) for token in _tokens(output.question)):
        flags.append("V-UNSUPPORTED-FACT")
    for key, label in output.labels:
        if key not in all_facts:
            continue
        tokens = _tokens(label)
        if any(t not in common | all_facts[key] for t in tokens):
            flags.append("V-UNSUPPORTED-FACT")
        other = set().union(*(v for k, v in all_facts.items() if k != key)) if len(all_facts) > 1 else set()
        if any(t in other - all_facts[key] - common for t in tokens):
            flags.append("V-CROSS-SLOT")
    if any(fact.casefold() in (output.question + " " + " ".join(labels)).casefold()
           for fact in (*contract.excluded_fact_values, *excluded_facts) if fact):
        flags.append("V-EXCLUSION")
    # Order is flagged but URI controls the final order itself.
    return ValidationResult(not any(f != "V-ORDER" for f in flags), tuple(dict.fromkeys(flags)))
