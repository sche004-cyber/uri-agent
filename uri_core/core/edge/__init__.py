"""Edge / Second-Brain proposal and observation foundations.

This package deliberately has no dependency on URI execution or authority
modules.  It is a typed, fail-closed boundary for optional intelligence.
"""

from .contracts import (
    EdgeAssistanceRequest,
    EdgeAssistanceResult,
    EdgeIntelligenceProvider,
    EdgeRuntime,
    EdgeVisionProvider,
    EdgeSpeechProvider,
    EdgeEmbeddingProvider,
    NullEdgeProvider,
)
from .settings import EdgeSettings, EdgeSettingsStore

__all__ = [
    "EdgeAssistanceRequest", "EdgeAssistanceResult", "EdgeIntelligenceProvider",
    "EdgeRuntime", "EdgeVisionProvider", "EdgeSpeechProvider",
    "EdgeEmbeddingProvider", "NullEdgeProvider", "EdgeSettings", "EdgeSettingsStore",
]
