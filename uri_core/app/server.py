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

from uri_core.core.audit_comparison import build_shadow_comparison_report
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator

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


class AskRequest(BaseModel):
    session_id: str
    text: str


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
