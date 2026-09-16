"""ModelRouter: deterministic provider/model selection with health-tracked fallback (M22.6).

SECURITY INVARIANT: ProviderAuthenticationError is NEVER caught in this module.
Auth failures must propagate to callers unchanged — they stop the chain, never retry.

Import boundary (M22.6 §6, invariant #2):
This module MUST NOT import approval_gate, approval_store, dispatcher, or capability_registry.
"""
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from uri_core.core.model_providers.base import (
    ModelResponse,
    ProviderAuthenticationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ModelNotFoundError,
)
from uri_core.config.model_roles import (
    UnknownModelProviderError,
    apply_active_brain_override,
    build_provider,
    load_model_roles,
)
from uri_core.core.context_budget import estimate_tokens
from uri_core.core.usage_ceiling_store import UsageCeilingStore
from uri_core.core.usage_meter import UsageMeter, UsageRecord

try:
    from uri_core.core.principal_context import PrincipalContext
except ImportError:
    PrincipalContext = None  # type: ignore

HEALTH_COOLDOWN_SECONDS: int = 60

class AllProvidersUnreachableError(ProviderError):
    """All candidates in the fallback chain were exhausted without success."""

@dataclass(frozen=True)
class ProviderPlan:
    """Resolved routing decision for a single role+principal combination."""
    provider_id: Optional[str]  # None = degrade path
    model: str
    fallback_chain: List[str] = field(default_factory=list)

class ProviderHealthTracker:
    """In-memory, per-process health state. Keyed by (provider_id, model). Never persisted."""

    def __init__(self) -> None:
        self._unhealthy: Dict[Tuple[str, str], float] = {}

    def is_healthy(self, provider_id: str, model: str) -> bool:
        until = self._unhealthy.get((provider_id, model), 0.0)
        return time.monotonic() >= until

    def mark_unhealthy(self, provider_id: str, model: str) -> None:
        self._unhealthy[(provider_id, model)] = time.monotonic() + HEALTH_COOLDOWN_SECONDS

    def reset(self, provider_id: str, model: str) -> None:
        """Reset health state (test helper / explicit recovery)."""
        self._unhealthy.pop((provider_id, model), None)

class ModelRouter:
    """Deterministic provider/model selection with health-tracked fallback.

    Pipeline (M22.6 §7.1):
    1. User configured primary for role
    2. Health check (skip unhealthy candidates)
    3. Account-wide monthly budget pre-flight check
    4. User declared fallback order, including the role-configured "auto" chain
    5. Install default: 'ollama' always permitted
    6. Any other healthy local provider (same adapter type)
    7. Degrade: provider_id=None
    """

    def __init__(self, health_tracker: Optional[ProviderHealthTracker] = None) -> None:
        self._health = health_tracker or ProviderHealthTracker()

    def _budget_ok(
        self, provider_id: str, role: str, principal: Optional[object],
        system_text: str = "", user_text: str = "",
    ) -> bool:
        """Block when measured historical usage plus the pending estimate reaches ceiling."""
        user_id = getattr(principal, "user_id", None)
        if user_id is None:
            return True
        ceiling = UsageCeilingStore(user_id).get_ceiling()
        if ceiling is None:
            return True
        return (UsageMeter().estimate_current_month_tokens(user_id)
                + estimate_tokens(system_text + user_text)) < ceiling

    @staticmethod
    def _record_usage(
        role: str, principal: Optional[object], session_id: Optional[str],
        provider_id: Optional[str], model: Optional[str], tried: List[str],
        response: Optional[ModelResponse] = None,
    ) -> None:
        # Legacy/anonymous calls have no user identity to attribute storage to.
        user_id = getattr(principal, "user_id", None)
        if user_id is None:
            return

        def measured(name):
            value = getattr(response, name, None)
            return {"value": value, "confidence": "UNAVAILABLE" if value is None else "KNOWN"}

        UsageMeter().record(UsageRecord(
            ts=datetime.now(timezone.utc).isoformat(), user_id=user_id,
            session_id=session_id, role=role, provider_id=provider_id, model=model,
            prompt_tokens=measured("prompt_tokens"), eval_tokens=measured("eval_tokens"),
            duration_seconds=measured("duration_seconds"),
            outcome="success" if response is not None else "unreachable",
            fallback_from=list(tried),
            estimated_cost={"value": None, "confidence": "UNAVAILABLE"},
        ))

    def _ordered_candidates(self, role: str, principal: Optional[Any] = None) -> List[str]:
        """Build ordered candidate list from role config.

        Deliberately does NOT apply the per-user Active Brain override
        (see _model_for_role, which does, and apply_active_brain_
        override's own docstring): overriding which ADAPTER the router
        tries here as well would let a cloud-provider Active Brain change
        the fallback chain's provider_id resolution in build_provider()
        (which, when called with an explicit provider_id_override, does
        not re-derive a matching provider_id/key for that override) - a
        real, separate gap, out of this bounded repair's scope. Limiting
        the override to the model string keeps this fix exact for the
        reported defect (a local Ollama model never reaching the router)
        without touching cloud-provider candidate selection at all."""
        # No stored preference means the exact legacy branch below remains
        # unchanged.  Preferences are trusted only after the API validates
        # them against the verified inventory.
        user_id = getattr(principal, "user_id", None)
        if user_id:
            try:
                from uri_core.core.fallback_routing_store import FallbackRoutingStore
                routing = FallbackRoutingStore(user_id).load()
                selected = [routing.get("primary"), routing.get("fallback_1"), routing.get("fallback_2")]
                role_cfg = load_model_roles().get(role, {})
                role_primary = role_cfg.get("provider", "ollama")
                provider_ids: List[str] = []
                for item in selected:
                    if isinstance(item, dict) and isinstance(item.get("provider_id"), str):
                        provider_ids.append(item["provider_id"])
                    elif item == "auto":
                        provider_ids.extend([role_primary, "ollama"])
                if any(item is not None for item in selected):
                    if "ollama" not in provider_ids:
                        provider_ids.append("ollama")
                    return list(dict.fromkeys(provider_ids))
            except Exception:
                pass
        roles_config = load_model_roles()
        role_cfg = roles_config.get(role, {})
        primary = role_cfg.get("provider", "ollama")
        # Start with primary; always include 'ollama' as install default
        raw = [primary]
        if "ollama" not in raw:
            raw.append("ollama")
        # Deduplicate, preserve order
        seen: set = set()
        ordered: List[str] = []
        for c in raw:
            if c not in seen:
                seen.add(c)
                ordered.append(c)
        return ordered

    def _model_for_role(
        self, role: str, principal: Optional[Any] = None, pid: Optional[str] = None
    ) -> str:
        """The model string for one candidate attempt.

        Applies the per-user Active Brain override (apply_active_brain_
        override) only when the override's own provider adapter matches
        the candidate `pid` already selected by _ordered_candidates - so
        this never changes WHICH provider the router tries (that stays
        exactly the static deployment config's decision, see
        _ordered_candidates' own docstring for why), only which MODEL is
        requested once "ollama" is already the candidate being attempted.
        This is what makes a user's real Active Brain choice actually
        reach ModelRouter.attempt() for the first time (previously it
        never did, for any role - build_provider() only ever saw this
        override when called with no provider_id_override, and attempt()
        always passes one)."""
        role_config = load_model_roles().get(role, {})
        overridden = apply_active_brain_override(role, principal, role_config)
        if pid is not None and overridden.get("provider", "ollama") != pid:
            return role_config.get("model", "")
        return overridden.get("model", "")

    def resolve(
        self,
        role: str,
        principal: Optional[Any] = None,
    ) -> ProviderPlan:
        """Return routing decision without actually calling the provider."""
        candidates = self._ordered_candidates(role, principal)
        tried: List[str] = []
        for pid in candidates:
            model = self._model_for_role(role, principal, pid)
            if not self._health.is_healthy(pid, model):
                tried.append(f"{pid}(unhealthy)")
                continue
            if not self._budget_ok(pid, role, principal):
                tried.append(f"{pid}(over_budget)")
                continue
            tried.append(pid)
            return ProviderPlan(provider_id=pid, model=model, fallback_chain=list(tried))
        # Degrade
        return ProviderPlan(provider_id=None, model="", fallback_chain=list(tried))

    def attempt(
        self,
        role: str,
        principal: Optional[Any] = None,
        session_id: Optional[str] = None,
        **complete_kwargs: Any,
    ) -> ModelResponse:
        """Walk the fallback chain and return the first successful completion.

        Security invariant: ProviderAuthenticationError is NEVER caught here.
        It propagates immediately to the caller — auth failures stop the chain.
        """
        candidates = self._ordered_candidates(role, principal)
        tried: List[str] = []
        last_error: Optional[Exception] = None
        # Retain the original three-argument seam for empty-prompt callers.
        budget_text = {key + "_text": complete_kwargs[key] for key in ("system", "user")
                       if complete_kwargs.get(key)}
        for pid in candidates:
            model = self._model_for_role(role, principal, pid)
            if not self._health.is_healthy(pid, model):
                tried.append(f"{pid}(unhealthy)")
                continue
            if not self._budget_ok(pid, role, principal, **budget_text):
                tried.append(f"{pid}(over_budget)")
                continue
            try:
                provider = build_provider(role, principal, provider_id_override=pid)
                response = provider.complete(**complete_kwargs)
                self._record_usage(role, principal, session_id, pid,
                                   getattr(response, "model", model), tried, response)
                tried.append(pid)
                return response
            except ProviderAuthenticationError:
                # NEVER caught — auth failure stops the chain. Re-raise always.
                raise
            except (ProviderUnavailableError, ProviderTimeoutError, ModelNotFoundError, UnknownModelProviderError) as exc:
                if not isinstance(exc, UnknownModelProviderError):
                    self._health.mark_unhealthy(pid, model)
                tried.append(f"{pid}(failed:{type(exc).__name__})")
                last_error = exc
                continue
        self._record_usage(role, principal, session_id, None, None, tried)
        raise AllProvidersUnreachableError(
            f"All providers exhausted for role {role!r}. "
            f"Chain attempted: {tried}. Last error: {last_error!r}"
        )

# Module-level singleton — process-wide health tracking
_router = ModelRouter()

def get_router() -> ModelRouter:
    """Return the process-wide ModelRouter singleton."""
    return _router
