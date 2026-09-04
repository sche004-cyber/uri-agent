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
from typing import Optional


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


@dataclass(frozen=True)
class ModelResponse:
    """A completed model response. Deliberately minimal - no raw backend
    payload is carried here, so a provider can never leak backend-internal
    debugging data to callers by accident."""

    content: str
    model: str
    provider: str


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_TIMEOUT_SECONDS = 60.0


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

    @classmethod
    def from_env(cls) -> "ModelProviderConfig":
        return cls(
            base_url=os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            model=os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            timeout_seconds=float(
                os.environ.get("OLLAMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            ),
        )


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
