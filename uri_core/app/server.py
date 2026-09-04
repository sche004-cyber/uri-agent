"""Minimal HTTP boundary between the Flutter client and UriOrchestrator.

This exposes UriOrchestrator.process_user_input() over HTTP, unmodified.
No new authorization, planning, or execution logic lives here — this
file only does request/response plumbing (JSON in, JSON out) so a real
network client can reach the existing orchestrator entry point.

Run with:
    uvicorn uri_core.app.server:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from typing import List

from uri_core.core.audit_comparison import build_shadow_comparison_report
from uri_core.core.identity import DeviceIdentityStore, UserIdentityStore
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.user_profile import UserProfile, UserProfileStore

app = FastAPI(title="URI API")

# Flutter web (flutter run -d chrome/edge) serves from a dev-server
# origin that isn't known ahead of time, so browser requests need CORS
# enabled. This is a local development server, not a deployed service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One orchestrator instance for the process lifetime, matching how the
# existing PyQt prototype uses it — session state lives inside
# UriOrchestrator.session_manager, keyed by the session_id each request
# supplies, not by HTTP connection.
#
# The model-reasoning shadow is wired to Ollama/qwen3:14b here, at the
# application boundary, rather than as UriOrchestrator's own default -
# every other test/caller that constructs UriOrchestrator() with no
# args keeps the previous, network-free model_callable=None behaviour.
# The shadow remains strictly observational: UriOrchestrator's existing
# _run_model_reasoning_shadow (unmodified) already never lets it affect
# plan/execution, and already catches any failure (Ollama unreachable,
# timeout, malformed response) into a "shadow_failed" status rather
# than raising.
_orchestrator = UriOrchestrator(
    model_reasoning_gateway=ModelReasoningGateway(
        model_callable=OllamaReasoningAdapter()
    )
)

# Identity/profile stores, loaded once for the process lifetime like
# _orchestrator above. Neither is wired into _orchestrator or into any
# request UriOrchestrator handles - user_id/device_id/profile stay
# entirely at this HTTP boundary this milestone. See
# uri_core/core/identity.py and uri_core/core/user_profile.py: a
# user_id carries no authentication or authorization meaning by
# itself, and there is exactly one ambient profile per install (no
# multi-user support exists yet, because no authentication exists
# yet).
_user_identity_store = UserIdentityStore()
_device_identity_store = DeviceIdentityStore()
_user_profile_store = UserProfileStore()


class AskRequest(BaseModel):
    session_id: str
    text: str


class ProfileUpdateRequest(BaseModel):
    communication_style: str
    autonomy_level: str
    focus_areas: List[str] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask")
def ask(payload: AskRequest) -> dict:
    result = _orchestrator.process_user_input(
        session_id=payload.session_id,
        user_text=payload.text,
    )

    # UriOrchestrator's raw dict also carries shadow-evaluation internals
    # (model_reasoning, skill_router_shadow) - audit-trail data that
    # includes the full capability registry, machine-local file paths,
    # and unrelated tool metadata. No screen in the Flutter client uses
    # any of that, so it is not relayed over this boundary. Only the
    # fields the client contract actually consumes cross the wire.
    return {
        "status": result.get("status"),
        "session_id": result.get("session_id"),
        "error": result.get("error"),
        "semantic_analysis": result.get("semantic_analysis"),
        "execution": result.get("execution"),
        "response": result.get("response"),
    }


@app.get("/audit/shadow-comparison")
def shadow_comparison() -> dict:
    """
    Read-only view over this process's audit trail: for each shadow
    path (Skill Router V1, model reasoning), how often it agreed with
    the deterministic runtime's actual choice. Never gates or affects
    any request - it only summarizes what UriOrchestrator already
    recorded (see _record_skill_router_audit /
    _record_model_reasoning_audit in orchestrator.py). AuditEvent
    metadata is validated at write time to reject anything
    credential-shaped and to cap value length, so nothing new needs
    filtering here.

    Audit events live only in this process's memory (no persistence
    layer exists yet) and reset on restart.
    """
    return build_shadow_comparison_report(
        _orchestrator.audit_trail.all_events()
    )


@app.get("/identity")
def identity() -> dict:
    """
    Read-only: this install's durable user_id (portable - see
    identity.py) and device_id (local-only). Neither is a credential
    and neither grants access to anything by itself; there is no
    authentication yet, so this endpoint is unauthenticated like every
    other endpoint in this file today.
    """
    user_identity = _user_identity_store.load_or_create()
    device_identity = _device_identity_store.load_or_create()

    return {
        "user_id": user_identity.user_id,
        "device_id": device_identity.device_id,
    }


@app.get("/profile")
def get_profile() -> dict:
    """Read-only view of this install's single ambient user profile."""
    profile = _user_profile_store.load_or_create()

    return {
        "communication_style": profile.communication_style,
        "autonomy_level": profile.autonomy_level,
        "focus_areas": profile.focus_areas,
        "updated_at": profile.updated_at,
    }


@app.post("/profile")
def update_profile(payload: ProfileUpdateRequest) -> dict:
    """
    Replaces the whole profile (no partial-patch semantics yet).
    Unauthenticated, same trust level as every other endpoint here
    today - there is exactly one ambient profile per install, so this
    is equivalent in scope to /ask already being unauthenticated.
    """
    updated = _user_profile_store.save(
        UserProfile(
            communication_style=payload.communication_style,
            autonomy_level=payload.autonomy_level,
            focus_areas=list(payload.focus_areas),
        )
    )

    return {
        "communication_style": updated.communication_style,
        "autonomy_level": updated.autonomy_level,
        "focus_areas": updated.focus_areas,
        "updated_at": updated.updated_at,
    }
