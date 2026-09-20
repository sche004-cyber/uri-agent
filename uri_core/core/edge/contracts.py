"""Provider-neutral, non-authoritative Edge contracts.

Values in this module are proposals or observations only.  In particular no
type here represents a grant, approval, credential, dispatch request, or an
execution result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

UNAVAILABLE = "UNAVAILABLE"
EDGE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class EdgeProviderDescriptor:
    provider_id: str
    display_name: str
    operations: Tuple[str, ...]
    schema_version: str = EDGE_SCHEMA_VERSION


@dataclass(frozen=True)
class EdgeHealth:
    status: str
    provider_id: str
    runtime_id: Optional[str] = None
    model_id: Optional[str] = None
    error_code: Optional[str] = None


@dataclass(frozen=True)
class EdgeRequest:
    """Bounded request inventory; content is never trace material."""
    operation: str
    user_text: Optional[str] = None
    conversation_excerpt: Tuple[str, ...] = ()
    offered_capabilities: Tuple[Dict[str, Any], ...] = ()
    attachment_derived_text: Optional[str] = None
    transcript: Optional[str] = None
    transcript_confidence: Optional[float] = None
    schema: Optional[Dict[str, Any]] = None
    untrusted_content_present: bool = False


@dataclass(frozen=True)
class EdgeToolRequest(EdgeRequest):
    operation: str = "tool_proposal"


@dataclass(frozen=True)
class EdgeExtractionRequest(EdgeRequest):
    operation: str = "extraction"


@dataclass(frozen=True)
class EdgeReplyRequest(EdgeRequest):
    operation: str = "reply"


@dataclass(frozen=True)
class EdgeCompanionRequest(EdgeRequest):
    operation: str = "companion_event"


@dataclass(frozen=True)
class EdgeProposal:
    provider_id: str
    runtime_id: str
    model_id: str
    artifact_hash: Optional[str]
    operation: str
    result: Dict[str, Any]
    raw_confidence: Optional[float] = None
    raw_confidence_semantics: str = UNAVAILABLE
    latency_ms: Optional[int] = None
    errors: Tuple[str, ...] = ()
    schema_version: str = EDGE_SCHEMA_VERSION


EdgeClassification = EdgeProposal
EdgeToolProposal = EdgeProposal
EdgeExtractionProposal = EdgeProposal
EdgeReplyProposal = EdgeProposal
EdgeCompanionProposal = EdgeProposal


@dataclass(frozen=True)
class ModelArtifact:
    artifact_id: str
    content_hash: str
    model_id: str


@dataclass(frozen=True)
class ResourceBudget:
    max_rss_bytes: Optional[int] = None
    max_cpu_ms: Optional[int] = None


@dataclass(frozen=True)
class RuntimeInventory:
    runtime_id: str
    status: str
    models: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeLease:
    lease_id: str
    runtime_id: str


RuntimeStatus = EdgeHealth


@dataclass(frozen=True)
class VisionRequest:
    source_id: str


@dataclass(frozen=True)
class VisionObservationProposal(EdgeProposal):
    pass


@dataclass(frozen=True)
class AudioRequest:
    source_id: str


@dataclass(frozen=True)
class TranscriptProposal(EdgeProposal):
    pass


@dataclass(frozen=True)
class EmbeddingRequest:
    text: str


@dataclass(frozen=True)
class EmbeddingProposal(EdgeProposal):
    pass


@dataclass(frozen=True)
class EdgeAssistancePayload:
    kind: str
    schema_version: str
    fields: Dict[str, Any]


@dataclass(frozen=True)
class EdgeAssistanceRequest:
    kind: str
    deadline_ms: int
    inputs: EdgeRequest

    def __post_init__(self) -> None:
        if self.kind not in {"retrieval", "extraction", "ocr_preprocess", "shortlist", "evidence_gather", "context_prep"}:
            raise ValueError("unsupported assistance kind")
        if type(self.deadline_ms) is not int or self.deadline_ms <= 0:
            raise ValueError("deadline_ms must be a positive integer")


@dataclass(frozen=True)
class EdgeAssistanceResult:
    status: str
    provider_id: str
    runtime_id: str
    content: EdgeAssistancePayload
    provenance: Tuple[Dict[str, str], ...] = ()
    uncertainty: Optional[float] = None
    completeness: str = "unknown"
    latency_ms: int = 0
    errors: Tuple[str, ...] = ()


class EdgeIntelligenceProvider(Protocol):
    def health(self) -> EdgeHealth: ...
    def classify(self, request: EdgeRequest) -> EdgeClassification: ...
    def propose_tools(self, request: EdgeToolRequest) -> EdgeToolProposal: ...
    def extract(self, request: EdgeExtractionRequest) -> EdgeExtractionProposal: ...
    def propose_response(self, request: EdgeReplyRequest) -> EdgeReplyProposal: ...
    def propose_companion_event(self, request: EdgeCompanionRequest) -> EdgeCompanionProposal: ...
    def prepare_context(self, request: EdgeAssistanceRequest) -> EdgeAssistanceResult: ...
    def describe(self) -> EdgeProviderDescriptor: ...


class EdgeRuntime(Protocol):
    def inventory(self) -> RuntimeInventory: ...
    def load(self, artifact: ModelArtifact, budget: ResourceBudget) -> RuntimeLease: ...
    def unload(self, lease_id: str, reason: str) -> None: ...
    def status(self) -> RuntimeStatus: ...


class EdgeVisionProvider(Protocol):
    def observe(self, request: VisionRequest) -> VisionObservationProposal: ...


class EdgeSpeechProvider(Protocol):
    def transcribe(self, request: AudioRequest) -> TranscriptProposal: ...


class EdgeEmbeddingProvider(Protocol):
    def embed(self, request: EmbeddingRequest) -> EmbeddingProposal: ...


class NullEdgeProvider:
    """Truthful unavailable provider used until a deployment qualifies one."""
    provider_id = "none"

    def health(self) -> EdgeHealth:
        return EdgeHealth("unavailable", self.provider_id, error_code="not_configured")

    def describe(self) -> EdgeProviderDescriptor:
        return EdgeProviderDescriptor(self.provider_id, "No Edge provider configured", ())

    def _unavailable(self, operation: str) -> EdgeProposal:
        return EdgeProposal(self.provider_id, "none", "none", None, operation, {}, errors=("not_configured",))

    def classify(self, request: EdgeRequest) -> EdgeClassification: return self._unavailable("classification")
    def propose_tools(self, request: EdgeToolRequest) -> EdgeToolProposal: return self._unavailable("tool_proposal")
    def extract(self, request: EdgeExtractionRequest) -> EdgeExtractionProposal: return self._unavailable("extraction")
    def propose_response(self, request: EdgeReplyRequest) -> EdgeReplyProposal: return self._unavailable("reply")
    def propose_companion_event(self, request: EdgeCompanionRequest) -> EdgeCompanionProposal: return self._unavailable("companion_event")
    def prepare_context(self, request: EdgeAssistanceRequest) -> EdgeAssistanceResult:
        return EdgeAssistanceResult("skipped", self.provider_id, "none", EdgeAssistancePayload(request.kind, EDGE_SCHEMA_VERSION, {}), errors=("not_configured",))
