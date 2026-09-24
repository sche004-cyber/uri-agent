"""Semantic Decoder provider slot (Step 1).

Belongs to the turn/request layer, not to the Edge subsystem, even though
Needle 3 is the planned first implementation. No concrete implementation
here — interface only.

The decoder receives ONLY current-request input encapsulated in DecodeInput:
raw text and current turn attachment metadata. It never receives or queries
session history, Graphify, prior turns, ARN, or tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from uri_v1.turn.contracts import AttachmentReference, DecodedRequest


@dataclass(frozen=True)
class DecodeInput:
    """Current turn input to the SemanticDecoder.

    Contains ONLY current-prompt material: raw text and current attachment
    metadata. Never contains session history, Graphify, prior turns, ARN,
    or tool data. Genuinely frozen and immutable (no mutable dict/list).
    """

    raw_text: str
    attachments: Tuple[AttachmentReference, ...] = ()

    @classmethod
    def from_text(
        cls,
        raw_text: str,
        attachments: Tuple[AttachmentReference, ...] = (),
    ) -> DecodeInput:
        """Convenience constructor from plain text and optional attachments."""
        return cls(raw_text=raw_text, attachments=attachments)


class SemanticDecoder(ABC):
    """Replaceable provider slot: DecodeInput -> DecodedRequest."""

    @abstractmethod
    def decode(self, input_data: DecodeInput) -> DecodedRequest:
        raise NotImplementedError
