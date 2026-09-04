from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import List, Optional


FACT_STATUSES = {
    "CONFIRMED",
    "VERIFIED",
    "PROVISIONAL",
    "HISTORICAL",
    "SUPERSEDED",
    "EXPIRED",
}

# Verifier identities that indicate a model/AI actor rather than an
# accountable human or institutional process. Matched as either an
# exact (normalized) value or a substring for unambiguous provider
# names, so legitimate human titles ("Assistant Registrar", "System
# Administrator") are not caught by this check.
_MODEL_ACTOR_EXACT = {
    "ai",
    "model",
    "bot",
    "system",
    "automatic",
    "auto",
    "assistant",
    "ai assistant",
    "the model",
    "the ai",
}

_MODEL_ACTOR_SUBSTRINGS = (
    "gpt",
    "claude",
    "chatgpt",
    "openai",
    "anthropic",
    "groq",
    "gemini",
    "llm",
    "language model",
    "chatbot",
    "autonomous agent",
)


def _looks_like_model_actor(verified_by: str) -> bool:

    normalized = verified_by.strip().lower()

    if normalized in _MODEL_ACTOR_EXACT:
        return True

    return any(
        marker in normalized for marker in _MODEL_ACTOR_SUBSTRINGS
    )


class FactVerificationError(ValueError):
    """Raised when a verification action is invalid - missing
    actor, or an actor that looks like a model/AI rather than an
    accountable human or institutional process."""


@dataclass
class Fact:
    """
    Represents one piece of information known to URI.

    Facts carry a status so historical information
    is not accidentally treated as current.
    """

    name: str
    value: str

    status: str = "PROVISIONAL"

    source: Optional[str] = None
    source_date: Optional[str] = None

    retrieved_date: str = (
        date.today().isoformat()
    )

    confirmed_by: Optional[str] = None

    notes: Optional[str] = None

    # ---------------------------------------------------------
    # Provenance, confidence, and verification.
    #
    # These are additive and backward-compatible: every existing
    # Fact(...) call site continues to work unchanged, since all
    # of these fields have defaults.
    #
    # `confidence` is a numeric signal only. It is never read by
    # this class to set `verified` - verification only happens
    # through verify(), which requires an explicit, non-model
    # `verified_by` actor.
    # ---------------------------------------------------------

    evidence_ids: List[str] = field(default_factory=list)

    confidence: Optional[float] = None

    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None

    def is_current(self) -> bool:
        return self.status == "CONFIRMED"

    def is_historical(self) -> bool:
        return self.status == "HISTORICAL"

    def validate_status(self):
        if self.status not in FACT_STATUSES:
            raise ValueError(
                f"Invalid fact status: {self.status}"
            )

    def validate_confidence(self):

        if self.confidence is None:
            return

        if not isinstance(self.confidence, (int, float)):
            raise ValueError(
                f"Invalid confidence value: {self.confidence!r}; "
                "must be a number"
            )

        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"Invalid confidence value: {self.confidence}; "
                "must be between 0 and 1"
            )

    def verify(
        self,
        verified_by: str,
        verified_at: Optional[str] = None
    ) -> None:
        """
        Explicitly mark this fact as verified.

        Verification must be an accountable, non-model action:
        it always requires a `verified_by` actor, and that actor
        must not look like a model/AI identity. A fact is never
        verified merely because it was produced by, or assigned
        high confidence by, a model.
        """

        if not verified_by or not isinstance(verified_by, str):
            raise FactVerificationError(
                "verify() requires a non-empty verified_by actor"
            )

        if _looks_like_model_actor(verified_by):
            raise FactVerificationError(
                f"'{verified_by}' looks like a model/AI actor; "
                "verification requires an explicit, accountable "
                "non-model actor"
            )

        self.verified = True
        self.verified_by = verified_by
        self.verified_at = (
            verified_at
            or datetime.now(timezone.utc).isoformat()
        )