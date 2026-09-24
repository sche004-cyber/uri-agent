"""Needle 3 narrow-schema extractors and deterministic normalizers (Batch A2.1).

Decomposes Step-1 semantic extraction into four independent, narrow tasks:
  - Schema A: Goal / Intent (extract_goal)
  - Schema B: Requested / Prohibited Operations (extract_operations)
  - Schema C: References / Temporal Expressions (extract_references)
  - Schema D: Constraints / Output Preferences (extract_constraints)

Each schema is small, flat, and focused. Each normalizer performs validation and
mapping only -- zero semantic reasoning, zero regex fallbacks, zero pronoun heuristics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from uri_v1.turn.contracts import (
    ConfidenceLevel,
    ConstraintScope,
    IntentFamily,
    OutputPreferences,
)
from uri_v1.turn.needle_decoder import NeedleBridgeTransport, NeedleTransportError
from uri_v1.turn.needle_wire import (
    DecodeError,
    DecodeErrorReason,
    _dedupe,
)

# ---------------------------------------------------------------------------
# Schema A: Goal / Intent
# ---------------------------------------------------------------------------

SCHEMA_A_TOOL_NAME = "extract_goal"

SCHEMA_GOAL: Dict[str, Any] = {
    "name": SCHEMA_A_TOOL_NAME,
    "description": "Always call this exactly once to extract the primary goal and intent family of the current message.",
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "One concise phrase stating the user's intended outcome.",
            },
            "intent_family": {
                "type": "string",
                "enum": [f.value for f in IntentFamily],
                "description": "The category of the user's intent.",
            },
        },
        "required": ["goal"],
        "additionalProperties": False,
    },
}

SYSTEM_GOAL = (
    "You are a goal extractor for the current user message only. "
    "You must always call extract_goal exactly once for every message, with no exceptions. "
    "State the user's primary intended outcome concisely in 'goal', and select the best matching "
    "'intent_family' from the allowed options. "
    "Do not use outside knowledge or prior turns. Never decline to call extract_goal."
)


@dataclass(frozen=True)
class NarrowGoalResult:
    """Outcome of Schema A extraction."""

    goal: str = ""
    intent_family: IntentFamily = IntentFamily.UNSPECIFIED
    raw_wire: Optional[Dict[str, Any]] = None
    raw_confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[DecodeError] = None
    call_count: int = 0
    declined: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.goal) and self.error is None and not self.declined


def normalize_goal(wire: Any) -> Tuple[str, IntentFamily]:
    """Deterministically normalizes Schema A wire output."""
    if not isinstance(wire, dict):
        raise DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, "Schema A wire is not an object")

    goal_text = wire.get("goal")
    if not isinstance(goal_text, str) or not goal_text.strip():
        raise DecodeError(
            DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
            "Schema A wire output has no non-empty 'goal' field",
        )

    raw_intent = wire.get("intent_family")
    try:
        intent_family = IntentFamily(raw_intent) if raw_intent else IntentFamily.UNSPECIFIED
    except ValueError:
        intent_family = IntentFamily.UNSPECIFIED

    return goal_text.strip(), intent_family


# ---------------------------------------------------------------------------
# Schema B: Requested / Prohibited Operations
# ---------------------------------------------------------------------------

SCHEMA_B_TOOL_NAME = "extract_operations"

SCHEMA_OPERATIONS: Dict[str, Any] = {
    "name": SCHEMA_B_TOOL_NAME,
    "description": "Always call this exactly once to extract requested and prohibited operations from the current message.",
    "parameters": {
        "type": "object",
        "properties": {
            "requested_operations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Operations or actions requested by the user.",
            },
            "prohibited_operations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Operations or actions explicitly prohibited, forbidden, or negated by the user (e.g., 'don't send', 'do not summarize').",
            },
        },
        "required": ["requested_operations", "prohibited_operations"],
        "additionalProperties": False,
    },
}

SYSTEM_OPERATIONS = (
    "You are an operations extractor for the current user message only. "
    "You must always call extract_operations exactly once for every message, with no exceptions. "
    "Extract all operations requested by the user into 'requested_operations'. "
    "Extract all operations explicitly negated, prohibited, or forbidden (e.g., 'don't send', "
    "'do not summarize', 'don't open') into 'prohibited_operations'. "
    "If no operations are requested or prohibited, emit empty lists. "
    "Do not use outside knowledge. Never decline to call extract_operations."
)


@dataclass(frozen=True)
class NarrowOperationsResult:
    """Outcome of Schema B extraction."""

    requested_operations: Tuple[str, ...] = ()
    prohibited_operations: Tuple[str, ...] = ()
    raw_wire: Optional[Dict[str, Any]] = None
    raw_confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[DecodeError] = None
    call_count: int = 0
    declined: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and not self.declined


def normalize_operations(wire: Any) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Deterministically normalizes Schema B wire output."""
    if not isinstance(wire, dict):
        raise DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, "Schema B wire is not an object")

    raw_req = wire.get("requested_operations")
    if raw_req is not None and not isinstance(raw_req, list):
        raise DecodeError(DecodeErrorReason.OPERATION_ERROR, "'requested_operations' must be an array")
    requested = _dedupe(tuple(str(x).strip() for x in (raw_req or ()) if str(x).strip()))

    raw_proh = wire.get("prohibited_operations")
    if raw_proh is not None and not isinstance(raw_proh, list):
        raise DecodeError(DecodeErrorReason.OPERATION_ERROR, "'prohibited_operations' must be an array")
    prohibited = _dedupe(tuple(str(x).strip() for x in (raw_proh or ()) if str(x).strip()))

    overlap = set(requested) & set(prohibited)
    if overlap:
        raise DecodeError(
            DecodeErrorReason.OPERATION_ERROR,
            f"operation(s) marked both requested and prohibited: {sorted(overlap)}",
        )

    return requested, prohibited


# ---------------------------------------------------------------------------
# Schema C: References / Temporal Expressions
# ---------------------------------------------------------------------------

SCHEMA_C_TOOL_NAME = "extract_references"

SCHEMA_REFERENCES: Dict[str, Any] = {
    "name": SCHEMA_C_TOOL_NAME,
    "description": "Always call this exactly once to record unresolved references and temporal expressions.",
    "parameters": {
        "type": "object",
        "properties": {
            "references": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Unresolved referring expressions such as pronouns ('this', 'that', 'it', 'them') or referring phrases ('that file', 'same thing', 'the earlier one'). Do not resolve them.",
            },
            "temporal_references": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Temporal expressions mentioned in the text (e.g., 'yesterday', 'tomorrow', '2025', 'earlier').",
            },
        },
        "required": ["references", "temporal_references"],
        "additionalProperties": False,
    },
}

SYSTEM_REFERENCES = (
    "You are a reference extractor for the current user message only. "
    "You must always call extract_references exactly once for every message, with no exceptions. "
    "Extract all unresolved referring expressions (pronouns like 'this', 'that', 'it', 'them', "
    "phrases like 'that file', 'same thing', 'earlier one') into 'references' without resolving them. "
    "Extract all temporal expressions (like 'yesterday', 'tomorrow', 'earlier') into 'temporal_references'. "
    "If none are present, emit empty lists. "
    "Do not resolve pronouns or invent identities. Never decline to call extract_references."
)


@dataclass(frozen=True)
class NarrowReferencesResult:
    """Outcome of Schema C extraction."""

    references: Tuple[str, ...] = ()
    temporal_references: Tuple[str, ...] = ()
    raw_wire: Optional[Dict[str, Any]] = None
    raw_confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[DecodeError] = None
    call_count: int = 0
    declined: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and not self.declined


def normalize_references(wire: Any) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Deterministically normalizes Schema C wire output."""
    if not isinstance(wire, dict):
        raise DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, "Schema C wire is not an object")

    raw_refs = wire.get("references")
    if raw_refs is not None and not isinstance(raw_refs, list):
        raise DecodeError(DecodeErrorReason.REFERENCE_ERROR, "'references' must be an array")
    references = _dedupe(tuple(str(x).strip() for x in (raw_refs or ()) if str(x).strip()))

    raw_trefs = wire.get("temporal_references")
    if raw_trefs is not None and not isinstance(raw_trefs, list):
        raise DecodeError(DecodeErrorReason.TEMPORAL_ERROR, "'temporal_references' must be an array")
    temporal_references = _dedupe(tuple(str(x).strip() for x in (raw_trefs or ()) if str(x).strip()))

    return references, temporal_references


# ---------------------------------------------------------------------------
# Schema D: Constraints / Output Preferences
# ---------------------------------------------------------------------------

SCHEMA_D_TOOL_NAME = "extract_constraints"

SCHEMA_CONSTRAINTS: Dict[str, Any] = {
    "name": SCHEMA_D_TOOL_NAME,
    "description": "Always call this exactly once to extract explicit constraints and output preferences.",
    "parameters": {
        "type": "object",
        "properties": {
            "constraints": {
                "type": "object",
                "properties": {
                    "included_items": {"type": "array", "items": {"type": "string"}},
                    "excluded_items": {"type": "array", "items": {"type": "string"}},
                    "length_limit": {"type": "string"},
                    "language_constraints": {"type": "string"},
                },
            },
            "output_preferences": {
                "type": "object",
                "properties": {
                    "artifact_type": {"type": "string"},
                    "tone": {"type": "string"},
                    "audience": {"type": "string"},
                    "language": {"type": "string"},
                    "language_variant": {"type": "string"},
                    "length": {"type": "string"},
                    "structure": {"type": "string"},
                },
            },
        },
        "required": ["constraints", "output_preferences"],
        "additionalProperties": False,
    },
}

SYSTEM_CONSTRAINTS = (
    "You are a constraints and output preferences extractor for the current user message only. "
    "You must always call extract_constraints exactly once for every message, with no exceptions. "
    "Extract inclusion, exclusion, length, or language limits into 'constraints'. "
    "Extract requested format (e.g. table), artifact (e.g. email, PDF), tone (e.g. formal), "
    "audience (e.g. Chief Warden), or language variant into 'output_preferences'. "
    "Leave unmentioned fields empty. "
    "Do not use outside knowledge. Never decline to call extract_constraints."
)


@dataclass(frozen=True)
class NarrowConstraintsResult:
    """Outcome of Schema D extraction."""

    constraints: ConstraintScope = field(default_factory=ConstraintScope)
    output_preferences: OutputPreferences = field(default_factory=OutputPreferences)
    raw_wire: Optional[Dict[str, Any]] = None
    raw_confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[DecodeError] = None
    call_count: int = 0
    declined: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and not self.declined


def normalize_constraints(wire: Any) -> Tuple[ConstraintScope, OutputPreferences]:
    """Deterministically normalizes Schema D wire output."""
    if not isinstance(wire, dict):
        raise DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, "Schema D wire is not an object")

    raw_c = wire.get("constraints") or {}
    if not isinstance(raw_c, dict):
        raise DecodeError(DecodeErrorReason.CONSTRAINT_ERROR, "'constraints' must be an object")

    inc_raw = raw_c.get("included_items") or ()
    if not isinstance(inc_raw, (list, tuple)):
        raise DecodeError(DecodeErrorReason.CONSTRAINT_ERROR, "'included_items' must be an array")
    included = _dedupe(tuple(str(x).strip() for x in inc_raw if str(x).strip()))

    exc_raw = raw_c.get("excluded_items") or ()
    if not isinstance(exc_raw, (list, tuple)):
        raise DecodeError(DecodeErrorReason.CONSTRAINT_ERROR, "'excluded_items' must be an array")
    excluded = _dedupe(tuple(str(x).strip() for x in exc_raw if str(x).strip()))

    overlap = set(included) & set(excluded)
    if overlap:
        raise DecodeError(
            DecodeErrorReason.CONSTRAINT_ERROR,
            f"item(s) both included and excluded: {sorted(overlap)}",
        )

    constraints = ConstraintScope(
        included_items=included,
        excluded_items=excluded,
        length_limit=raw_c.get("length_limit"),
        language_constraints=raw_c.get("language_constraints"),
    )

    raw_p = wire.get("output_preferences") or {}
    if not isinstance(raw_p, dict):
        raise DecodeError(DecodeErrorReason.OUTPUT_PREFERENCE_ERROR, "'output_preferences' must be an object")

    output_preferences = OutputPreferences(
        artifact_type=raw_p.get("artifact_type"),
        structure=raw_p.get("structure"),
        language=raw_p.get("language"),
        language_variant=raw_p.get("language_variant"),
        tone=raw_p.get("tone"),
        audience=raw_p.get("audience"),
        length=raw_p.get("length"),
    )

    return constraints, output_preferences


# ---------------------------------------------------------------------------
# NeedleNarrowSemanticExtractor: Subprocess extraction harness
# ---------------------------------------------------------------------------


class NeedleNarrowSemanticExtractor:
    """Invokes Needle 3 over subprocess transport for narrow semantic extractions."""

    def __init__(self, transport: NeedleBridgeTransport) -> None:
        self.transport = transport

    def _execute_schema_call(
        self,
        text: str,
        system: str,
        schema: Dict[str, Any],
        expected_tool_name: str,
        *,
        max_new_tokens: int = 250,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[float], float, int, bool, Optional[DecodeError], Optional[Dict[str, Any]]]:
        """Runs a single narrow call through the transport.

        Returns:
            (wire_args, raw_confidence, latency_ms, call_count, declined, error, raw_envelope)
        """
        started = time.perf_counter()
        try:
            raw_response = self.transport.decode(
                text,
                system=system,
                schema=schema,
                max_new_tokens=max_new_tokens,
            )
        except NeedleTransportError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return (
                None,
                None,
                elapsed_ms,
                0,
                False,
                DecodeError(DecodeErrorReason.MALFORMED_OUTPUT, f"transport failure: {exc}"),
                None,
            )

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        raw_confidence = raw_response.get("confidence")

        if raw_response.get("success") is False:
            return (
                None,
                raw_confidence,
                elapsed_ms,
                0,
                False,
                DecodeError(
                    DecodeErrorReason.MALFORMED_OUTPUT,
                    str(raw_response.get("error") or "Needle reported an unsuccessful response"),
                ),
                raw_response,
            )

        calls = raw_response.get("function_calls") or []
        call_count = len(calls)

        if call_count == 0:
            return (
                None,
                raw_confidence,
                elapsed_ms,
                0,
                True,
                DecodeError(
                    DecodeErrorReason.MISSING_REQUIRED_STRUCTURE,
                    f"Needle declined to call {expected_tool_name}",
                ),
                raw_response,
            )

        if call_count > 1:
            return (
                None,
                raw_confidence,
                elapsed_ms,
                call_count,
                False,
                DecodeError(
                    DecodeErrorReason.MALFORMED_OUTPUT,
                    f"Needle emitted {call_count} calls; expected exactly one {expected_tool_name}",
                ),
                raw_response,
            )

        call = calls[0]
        if not isinstance(call, dict) or call.get("name") != expected_tool_name:
            return (
                None,
                raw_confidence,
                elapsed_ms,
                call_count,
                False,
                DecodeError(
                    DecodeErrorReason.UNKNOWN_FIELD,
                    f"unexpected call shape or name: {call!r}",
                ),
                raw_response,
            )

        wire_args = call.get("arguments")
        if not isinstance(wire_args, dict):
            return (
                None,
                raw_confidence,
                elapsed_ms,
                call_count,
                False,
                DecodeError(
                    DecodeErrorReason.MALFORMED_OUTPUT,
                    f"tool arguments is not a dict: {wire_args!r}",
                ),
                raw_response,
            )

        return (wire_args, raw_confidence, elapsed_ms, 1, False, None, raw_response)

    def extract_goal(self, text: str, *, max_new_tokens: int = 250) -> NarrowGoalResult:
        """Extracts Schema A (Goal / Intent)."""
        wire, conf, lat, count, declined, err, raw_resp = self._execute_schema_call(
            text, SYSTEM_GOAL, SCHEMA_GOAL, SCHEMA_A_TOOL_NAME, max_new_tokens=max_new_tokens
        )
        if err is not None:
            return NarrowGoalResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=err,
                call_count=count,
                declined=declined,
            )

        try:
            goal, intent_family = normalize_goal(wire)
        except DecodeError as exc:
            return NarrowGoalResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=exc,
                call_count=count,
                declined=False,
            )

        return NarrowGoalResult(
            goal=goal,
            intent_family=intent_family,
            raw_wire=raw_resp,
            raw_confidence=conf,
            latency_ms=lat,
            error=None,
            call_count=count,
            declined=False,
        )

    def extract_operations(self, text: str, *, max_new_tokens: int = 250) -> NarrowOperationsResult:
        """Extracts Schema B (Requested / Prohibited Operations)."""
        wire, conf, lat, count, declined, err, raw_resp = self._execute_schema_call(
            text, SYSTEM_OPERATIONS, SCHEMA_OPERATIONS, SCHEMA_B_TOOL_NAME, max_new_tokens=max_new_tokens
        )
        if err is not None:
            return NarrowOperationsResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=err,
                call_count=count,
                declined=declined,
            )

        try:
            requested, prohibited = normalize_operations(wire)
        except DecodeError as exc:
            return NarrowOperationsResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=exc,
                call_count=count,
                declined=False,
            )

        return NarrowOperationsResult(
            requested_operations=requested,
            prohibited_operations=prohibited,
            raw_wire=raw_resp,
            raw_confidence=conf,
            latency_ms=lat,
            error=None,
            call_count=count,
            declined=False,
        )

    def extract_references(self, text: str, *, max_new_tokens: int = 250) -> NarrowReferencesResult:
        """Extracts Schema C (References / Temporal Expressions)."""
        wire, conf, lat, count, declined, err, raw_resp = self._execute_schema_call(
            text, SYSTEM_REFERENCES, SCHEMA_REFERENCES, SCHEMA_C_TOOL_NAME, max_new_tokens=max_new_tokens
        )
        if err is not None:
            return NarrowReferencesResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=err,
                call_count=count,
                declined=declined,
            )

        try:
            references, temporal_references = normalize_references(wire)
        except DecodeError as exc:
            return NarrowReferencesResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=exc,
                call_count=count,
                declined=False,
            )

        return NarrowReferencesResult(
            references=references,
            temporal_references=temporal_references,
            raw_wire=raw_resp,
            raw_confidence=conf,
            latency_ms=lat,
            error=None,
            call_count=count,
            declined=False,
        )

    def extract_constraints(self, text: str, *, max_new_tokens: int = 250) -> NarrowConstraintsResult:
        """Extracts Schema D (Constraints / Output Preferences)."""
        wire, conf, lat, count, declined, err, raw_resp = self._execute_schema_call(
            text, SYSTEM_CONSTRAINTS, SCHEMA_CONSTRAINTS, SCHEMA_D_TOOL_NAME, max_new_tokens=max_new_tokens
        )
        if err is not None:
            return NarrowConstraintsResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=err,
                call_count=count,
                declined=declined,
            )

        try:
            constraints, output_preferences = normalize_constraints(wire)
        except DecodeError as exc:
            return NarrowConstraintsResult(
                raw_wire=raw_resp,
                raw_confidence=conf,
                latency_ms=lat,
                error=exc,
                call_count=count,
                declined=False,
            )

        return NarrowConstraintsResult(
            constraints=constraints,
            output_preferences=output_preferences,
            raw_wire=raw_resp,
            raw_confidence=conf,
            latency_ms=lat,
            error=None,
            call_count=count,
            declined=False,
        )

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "NeedleNarrowSemanticExtractor":
        self.transport.load()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
