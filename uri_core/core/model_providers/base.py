"""Provider-agnostic model interaction boundary.

A ModelProvider's only job is turning (system prompt, user text) into a
text completion from some model backend. It knows nothing about URI's
semantic-interpretation contract, prompt content, capability registry,
or orchestration - that domain logic stays in whatever calls the
provider (see provider_semantic_interpreter.py). This keeps provider
code swappable: changing which model or backend URI uses is a matter
of constructing a different ModelProvider, never editing orchestration
logic.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse


class ProviderError(Exception):
    """Base class for all model-provider failures."""


class ProviderUnavailableError(ProviderError):
    """The provider's backend could not be reached (e.g. not running)."""


class ProviderTimeoutError(ProviderError):
    """The provider's backend did not respond in time."""


class ModelNotFoundError(ProviderError):
    """The requested model is not available on the backend."""


class ProviderResponseError(ProviderError):
    """The backend responded, but not in a shape this provider understands."""


class ProviderAuthenticationError(ProviderResponseError):
    """The backend rejected the supplied API key / bearer token (HTTP 401/403).

    Kept distinct from ProviderUnavailableError so callers (and M22.6's
    ModelRouter) can implement 'auth failure stops, never silently falls back
    to a different provider or key' without matching on status-code strings.
    Raised only on explicit credential rejection, not network errors."""


@dataclass(frozen=True)
class ModelResponse:
    """A completed model response. Deliberately minimal - no raw backend
    payload is carried here, so a provider can never leak backend-internal
    debugging data to callers by accident.

    M21: prompt_tokens/eval_tokens/duration_seconds are plain numbers, not
    raw payload - the same "reporting-only self-knowledge" discipline
    ModelProviderStatus already applies. They exist so a caller (or a test)
    can verify a real prompt was NOT silently truncated by comparing
    prompt_tokens against what was actually sent, and so latency is
    measurable at all - see the M21 audit's finding that no latency
    instrumentation existed anywhere in this pipeline. All three default to
    None (unknown) rather than 0, so a provider that cannot report them is
    never mistaken for one that measured zero."""

    content: str
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    eval_tokens: Optional[int] = None
    duration_seconds: Optional[float] = None


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_TIMEOUT_SECONDS = 60.0

# M21: the actual runtime context window Ollama loads a model with when a
# request does not otherwise specify options.num_ctx - measured during the
# M21 audit at 4096 (Ollama's own hardcoded default), far below qwen3:14b's
# real 40960-token trained context. Every URI Brain call was silently
# truncated to this window (prompt_eval_count == ~num_ctx/2 on a prompt
# almost 5000 tokens long) with no error, no log, and no field anywhere
# reporting the true number - see ModelProviderStatus.context_window below,
# previously hardcoded to None. 8192 is a deliberate, conservative default:
# comfortably larger than URI's real measured reasoning (~4935 tok) and
# drafting (~4595 tok) prompts even before the M21 request-shrinking work,
# while staying far under qwen3:14b's 40960-token ceiling so ordinary
# hardware is not forced to allocate a window it will rarely use.
# Overridable per deployment via OLLAMA_NUM_CTX - see ModelProviderConfig.
DEFAULT_CONTEXT_TOKENS = 8192

# Self-knowledge status checks must stay cheap regardless of how long a
# real completion is allowed to take (ModelProviderConfig.timeout_seconds
# defaults to 60s) - reporting-only callers (see capability_registry.py,
# server.py's GET /capabilities) need an answer quickly even when Ollama
# is unreachable, not a 60s hang.
DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS = 3.0

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _location_from_base_url(base_url: str) -> str:
    """"local" only for an actual loopback host in the configured URL -
    never a guess. Anything else (a real hostname/IP, or a URL that
    fails to parse a host at all) is "external": safer to under-claim
    locality than to assume a remote server is local."""

    try:
        host = urlparse(base_url).hostname
    except ValueError:
        return "external"

    return "local" if host in _LOCAL_HOSTS else "external"


@dataclass(frozen=True)
class ModelProviderConfig:
    """Connection details for a provider backend.

    Never hardcode a base_url/model/timeout at a call site - construct
    (or default-build via from_env()) one of these instead, so every
    place that needs to know "which model, which server" reads it from
    one source. base_url is a plain URL rather than always "localhost"
    so a future remote Ollama server is just a different config value,
    not a code change.
    """

    base_url: str = DEFAULT_OLLAMA_BASE_URL
    model: str = DEFAULT_OLLAMA_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    # M21: the num_ctx sent on every real completion request - see
    # DEFAULT_CONTEXT_TOKENS above for why this exists and what its default
    # covers. Never inferred from the model - always an explicit, known
    # value so "how much context does this call actually have" is answered
    # by config, not by an undocumented backend default.
    context_tokens: int = DEFAULT_CONTEXT_TOKENS

    @classmethod
    def from_env(cls) -> "ModelProviderConfig":
        return cls(
            base_url=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            model=os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            timeout_seconds=float(
                os.environ.get("OLLAMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            ),
            context_tokens=int(
                os.environ.get("OLLAMA_NUM_CTX", DEFAULT_CONTEXT_TOKENS)
            ),
        )


@dataclass(frozen=True)
class ModelProviderStatus:
    """Reporting-only self-knowledge about the model/provider currently
    configured to power URI - see capability_registry.py and server.py's
    GET /capabilities, the only places this is ever consumed.

    Never treat any field here as authority, a capability grant, or an
    approval signal - model identity/availability is informational
    context for a human or a future reasoning layer to read, exactly
    like growth_ledger.py's XP is informational and never read by
    capability_planner.py/dispatcher.py. capability_planner.py and
    dispatcher.py must never import this module or ModelProvider.

    Unknown-safe by design: context_window is None rather than guessed
    (Ollama does not cheaply expose this without an extra network call
    this milestone deliberately does not make - see describe()'s
    docstring), and available/detail always come from an actual,
    cheap, timeout-bounded reachability check, never assumed True.
    """

    provider_name: str
    model_name: str
    location: str  # "local" | "external" - derived from config, never guessed
    context_window: Optional[int]  # None when not reliably knowable
    supports: Tuple[str, ...]  # what this provider's interface does, e.g. ("text",)
    available: bool
    detail: Optional[str] = None


class ModelProvider(ABC):
    """Anything that can turn a (system, user) prompt pair into text."""

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> ModelProviderStatus:
        """Cheap, timeout-bounded, exception-safe self-knowledge about
        this provider - must never call complete() or otherwise perform
        a real model invocation, and must never raise: an unreachable
        backend is a normal, expected describe() result
        (available=False, detail explaining why), not an error."""
        raise NotImplementedError
