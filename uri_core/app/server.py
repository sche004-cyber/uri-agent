"""Minimal HTTP boundary between the Flutter client and UriOrchestrator.

This exposes UriOrchestrator.process_user_input() over HTTP, unmodified.
No new authorization, planning, or execution logic lives here — this
file only does request/response plumbing (JSON in, JSON out) so a real
network client can reach the existing orchestrator entry point.

Run with:
    uvicorn uri_core.app.server:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from uri_core.core.audit_comparison import build_shadow_comparison_report
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.growth_ledger import GrowthLedgerStore
from uri_core.core.identity import DeviceIdentityStore, UserIdentityStore
from uri_core.core.model_providers import OllamaProvider
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.personalization_context import (
    build_personalization_context,
)
from uri_core.core.portable_paths import (
    PortablePathValidationError,
    migrate_legacy_file_if_needed,
    user_scoped_path,
)
from uri_core.core.user_memory import (
    MemoryEntry,
    MemoryStore,
    MemoryValidationError,
)
from uri_core.core.user_profile import (
    UserProfile,
    UserProfileStore,
    UserProfileValidationError,
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
#
# enable_response_narrative=True is this milestone's one explicit
# opt-in: UriOrchestrator defaults it to False specifically so every
# existing test/caller keeps its exact prior behaviour (see
# orchestrator.py's __init__ comment) - this server is the one place
# that turns the live conversational surface on, matching how the
# model-reasoning shadow was already turned on here rather than as a
# class default. response.narrative stays additive - see
# _draft_narrative_safely - so this does not change what /ask returns
# for any client not yet reading that field.
_orchestrator = UriOrchestrator(
    model_reasoning_gateway=ModelReasoningGateway(
        model_callable=OllamaReasoningAdapter()
    ),
    enable_response_narrative=True,
)

# Identity/profile/memory/growth stores, constructed once for the
# process lifetime like _orchestrator above. Neither is wired into
# _orchestrator or into any request UriOrchestrator handles -
# user_id/device_id/profile/memory/growth stay entirely at this HTTP
# boundary. See uri_core/core/identity.py: a user_id carries no
# authentication or authorization meaning by itself, and there is
# exactly one ambient profile per install (no multi-user support
# exists yet, because no authentication exists yet).
#
# Constructing these stores does no filesystem I/O by itself (each
# store's __init__ only records its storage_path - see
# user_profile.py/user_memory.py/growth_ledger.py). They start out
# pointing at the legacy ambient paths used before this milestone, so
# importing this module remains completely side-effect-free, exactly
# as before. _initialize_user_scoped_stores() below - run only from
# the app's lifespan startup handler, never at import - resolves this
# install's user_id, migrates each legacy file into
# uri_workspace/users/<user_id>/ exactly once, and then rewires these
# same module globals to read/write there instead. If startup never
# runs (nothing currently does that except a real `uvicorn ...` launch
# or `with TestClient(app):`), these stores keep working exactly as
# they did before this milestone, at the legacy ambient paths.
_user_identity_store = UserIdentityStore()
_device_identity_store = DeviceIdentityStore()
_user_profile_store = UserProfileStore()
_memory_store = MemoryStore()

# Growth ledger: see growth_ledger.py. Every event is recorded only as
# a side effect of a real, already-succeeded user-driven write below
# (POST /memory, POST /profile) - there is no public "add XP" surface,
# and nothing here is ever read by _orchestrator or anything that
# plans/authorizes/approves/executes.
_growth_ledger_store = GrowthLedgerStore()

# Capability self-knowledge (Milestone 6): reporting-only, same as the
# growth ledger above. _capability_registry is also read by
# _orchestrator.capability_planner (its gap-reporting path only - never
# for selection, see capability_planner.py's _known_gaps()). Neither
# this registry read nor _model_provider.describe() below ever
# influences authorization, approval, or execution - GET /capabilities
# is the only thing that combines them, purely for display.
_capability_registry = CapabilityRegistry()

# A distinct OllamaProvider instance from whatever _orchestrator's
# semantic interpreter uses internally - deliberately not the same
# object, so this reporting-only self-knowledge query can never become
# entangled with the live request path. describe() is a cheap,
# timeout-bounded health check, never a real completion - see
# ModelProvider.describe's contract in model_providers/base.py.
_model_provider = OllamaProvider()


def _record_growth_event_safely(
    event_type: str, metadata: Optional[dict] = None
) -> None:
    """Never raises - a growth-ledger failure must never break the
    real user-driven action it's downstream of. Mirrors
    orchestrator.py's _record_skill_router_audit/
    _record_model_reasoning_audit's own never-breaks-the-live-request
    discipline."""
    try:
        _growth_ledger_store.record_event(event_type, metadata)
    except Exception:
        return


def _initialize_user_scoped_stores(
    root: str = "uri_workspace/users",
) -> None:
    """Runs once, at real application startup (see _lifespan) - never
    at module import. Resolves this install's durable user_id,
    migrates each legacy ambient state file into its user-scoped
    location exactly once (copy-only, idempotent, never overwrites an
    existing user-scoped file - see portable_paths.py), then rewires
    _user_profile_store/_memory_store/_growth_ledger_store to read and
    write there instead. device_id/_device_identity_store is
    deliberately untouched - it stays local-only, outside the
    user-scoped tree, per identity.py's user_id/device_id distinction.

    root is only overridden by tests, to keep this fully testable
    against a temp directory without ever touching a real
    uri_workspace/ install.

    If user_id somehow fails strict validation (a corrupted or
    hand-edited portable_identity.json - see
    PortablePathValidationError), this degrades safely by leaving the
    stores at whatever they already were (the legacy ambient paths on
    first startup), matching every other store in this codebase's
    existing "degrade rather than crash on corrupted local state"
    discipline - it does not raise and does not prevent the server
    from starting.
    """
    global _user_profile_store, _memory_store, _growth_ledger_store

    user_id = _user_identity_store.load_or_create().user_id

    legacy_stores = (
        (_user_profile_store, "user_profile.json"),
        (_memory_store, "user_memory.json"),
        (_growth_ledger_store, "growth_ledger.json"),
    )

    try:
        new_paths = {
            filename: user_scoped_path(user_id, filename, root=root)
            for _, filename in legacy_stores
        }
    except PortablePathValidationError:
        return

    for legacy_store, filename in legacy_stores:
        migrate_legacy_file_if_needed(
            legacy_store.storage_path, new_paths[filename]
        )

    _user_profile_store = UserProfileStore(
        storage_path=new_paths["user_profile.json"]
    )
    _memory_store = MemoryStore(storage_path=new_paths["user_memory.json"])
    _growth_ledger_store = GrowthLedgerStore(
        storage_path=new_paths["growth_ledger.json"]
    )


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """FastAPI/Starlette lifespan: the one place explicit application
    startup work belongs, as opposed to module import. Runs for a real
    `uvicorn uri_core.app.server:app` launch and for
    `with TestClient(app):`; does not run for a bare
    `TestClient(app)` with no `with` block, which every existing test
    in this repo uses - those tests are unaffected either way because
    they already override the store globals directly in setUp()."""
    _initialize_user_scoped_stores()
    yield


app = FastAPI(title="URI API", lifespan=_lifespan)

# Flutter web (flutter run -d chrome/edge) serves from a dev-server
# origin that isn't known ahead of time, so browser requests need CORS
# enabled. This is a local development server, not a deployed service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    session_id: str
    text: str


class ProfileUpdateRequest(BaseModel):
    communication_style: str
    autonomy_level: str
    focus_areas: List[str] = []


class MemoryWriteRequest(BaseModel):
    category: str
    content: str
    confidence: Optional[float] = None
    notes: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    action_id: str
    session_id: Optional[str] = None


def _memory_entry_to_dict(entry: MemoryEntry) -> dict:
    # Flattened, minimal view - not a raw dump of MemoryEntry/Fact's
    # full internal shape (source, source_date, retrieved_date,
    # evidence_ids, verified/verified_by/verified_at aren't exposed
    # here), matching the same "only what the client contract needs"
    # discipline /ask's response already follows.
    return {
        "memory_id": entry.memory_id,
        "category": entry.category,
        "consent": entry.consent,
        "content": entry.fact.value,
        "confidence": entry.fact.confidence,
        "notes": entry.fact.notes,
        "status": entry.fact.status,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask")
def ask(payload: AskRequest) -> dict:
    # Bounded personalization (Milestone 8A): only the confirmed
    # profile and consent-eligible memory (never pending_confirmation,
    # never growth/XP - see personalization_context.py) is assembled
    # here, at the HTTP boundary, using the same user-scoped stores
    # every other endpoint already reads - never inside
    # UriOrchestrator itself, preserving its existing zero-coupling to
    # profile/memory (see Milestone 5-7's structural boundary tests).
    # This can only ever influence how a response is *phrased* (see
    # _draft_narrative_safely) - it is never read by capability
    # selection, approval, or execution.
    personalization_context = build_personalization_context(
        _user_profile_store.load_or_create(),
        _memory_store.list_all(),
    )

    result = _orchestrator.process_user_input(
        session_id=payload.session_id,
        user_text=payload.text,
        personalization_context=personalization_context,
    )

    # UriOrchestrator's raw dict also carries shadow-evaluation internals
    # (model_reasoning, skill_router_shadow) - audit-trail data that
    # includes the full capability registry, machine-local file paths,
    # and unrelated tool metadata. No screen in the Flutter client uses
    # any of that, so it is not relayed over this boundary. Only the
    # fields the client contract actually consumes cross the wire.
    #
    # "narrative" is additive/shadow-rollout (Milestone 8A) - present
    # only when drafting+validation both succeeded; absent (None)
    # otherwise, in which case "response" (the pre-existing,
    # deterministic template/tool-output field, unchanged) remains the
    # only text a client has ever needed to render.
    return {
        "status": result.get("status"),
        "session_id": result.get("session_id"),
        "error": result.get("error"),
        "semantic_analysis": result.get("semantic_analysis"),
        "execution": result.get("execution"),
        "response": result.get("response"),
        "narrative": result.get("narrative"),
    }


@app.post("/approve")
def approve(payload: ApprovalDecisionRequest) -> dict:
    """
    Records a real, explicit user approval for one proposed action
    (Milestone 7) and, only if the deterministic ApprovalGate accepts
    it (matching action_id/capability/session/arguments, not expired,
    not already decided), executes it immediately and returns the
    execution result. Backs Flutter's real
    UriClient.approve(turnId)/TurnStage.awaitingApproval flow (see
    uri_ui/lib/services/http_uri_client.dart).

    Nothing here can be satisfied by model output: action_id must
    already exist as a real ApprovalStore record created by
    ApprovalGate.execute_tool() during a prior /ask call.

    Bounded personalization (same discipline as POST /ask - see
    build_personalization_context) is passed through so the
    additive/shadow-rolled-out "narrative" field (Milestone 8A) can
    explain this decision's real outcome in URI's voice too, not only
    the initial proposal.
    """
    personalization_context = build_personalization_context(
        _user_profile_store.load_or_create(),
        _memory_store.list_all(),
    )

    return _orchestrator.decide_action(
        action_id=payload.action_id,
        approved=True,
        session_id=payload.session_id,
        personalization_context=personalization_context,
    )


@app.post("/cancel")
def cancel(payload: ApprovalDecisionRequest) -> dict:
    """
    Records an explicit user rejection for one proposed action - the
    action is marked rejected and never executes. See POST /approve's
    docstring for the same contract notes.
    """
    personalization_context = build_personalization_context(
        _user_profile_store.load_or_create(),
        _memory_store.list_all(),
    )

    return _orchestrator.decide_action(
        action_id=payload.action_id,
        approved=False,
        session_id=payload.session_id,
        personalization_context=personalization_context,
    )


@app.get("/tasks")
def tasks() -> dict:
    """
    Read-only: every proposed action still awaiting a user decision,
    across all sessions - the backend for a cross-session "Tasks" view
    (UI prototype phase 1). Never mutates anything - approving or
    rejecting stays exclusively POST /approve / POST /cancel, exactly
    like every other read endpoint in this file never doubles as a
    write path.
    """
    pending = _orchestrator.approval_gate.approval_store.list_pending()

    task_list = []

    for action in pending:
        descriptor = _capability_registry.describe_status(
            action.capability_id
        )

        task_list.append(
            {
                "action_id": action.action_id,
                "capability_id": action.capability_id,
                "description": descriptor.description if descriptor else "",
                "risk": descriptor.risk if descriptor else "unknown",
                "session_id": action.session_id,
                "created_at": action.created_at,
            }
        )

    return {"tasks": task_list}


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

    communication_style/autonomy_level/focus_areas are validated
    (enum-constrained, length-capped, credential-shape rejected - see
    user_profile.py's _validate_profile_fields) before being saved -
    this stopped being optional hygiene once profile data started
    reaching a model prompt via personalization_context.py.
    """
    try:
        updated = _user_profile_store.save(
            UserProfile(
                communication_style=payload.communication_style,
                autonomy_level=payload.autonomy_level,
                focus_areas=list(payload.focus_areas),
            )
        )
    except UserProfileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _record_growth_event_safely("profile_updated")

    return {
        "communication_style": updated.communication_style,
        "autonomy_level": updated.autonomy_level,
        "focus_areas": updated.focus_areas,
        "updated_at": updated.updated_at,
    }


@app.get("/memory")
def list_memory() -> dict:
    """
    Every memory this install holds, including any pending proposals
    (labelled by their consent field) - visible to the user for
    review. Nothing in this milestone ever creates a
    pending_confirmation entry; see user_memory.py.

    Whole-store listing doubles as this milestone's export mechanism -
    no separate export endpoint yet.
    """
    return {
        "memories": [
            _memory_entry_to_dict(entry)
            for entry in _memory_store.list_all()
        ]
    }


@app.post("/memory")
def add_memory(payload: MemoryWriteRequest) -> dict:
    """
    The user explicitly asking URI to remember something -
    consent="user_provided" always, set unconditionally by MemoryStore
    itself, never taken from the request body. There is no path in
    this milestone for URI/the model to write a memory on its own.
    """
    try:
        entry = _memory_store.add(
            category=payload.category,
            content=payload.content,
            confidence=payload.confidence,
            notes=payload.notes,
        )
    except MemoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _record_growth_event_safely(
        "memory_recorded", {"category": entry.category}
    )

    return _memory_entry_to_dict(entry)


@app.put("/memory/{memory_id}")
def update_memory(memory_id: str, payload: MemoryWriteRequest) -> dict:
    """Whole-entry replace (edit), same pattern as POST /profile.
    consent is preserved, not editable via this endpoint."""
    try:
        updated = _memory_store.update(
            memory_id,
            category=payload.category,
            content=payload.content,
            confidence=payload.confidence,
            notes=payload.notes,
        )
    except MemoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if updated is None:
        raise HTTPException(status_code=404, detail="Memory not found.")

    return _memory_entry_to_dict(updated)


@app.delete("/memory/{memory_id}")
def delete_memory(memory_id: str) -> dict:
    """Real, complete removal - not a soft-delete/hide flag."""
    deleted = _memory_store.delete(memory_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")

    return {"deleted": True, "memory_id": memory_id}


@app.get("/growth")
def growth() -> dict:
    """
    Read-only summary: XP/level/achievements, always recomputed from
    the append-only growth event history (see
    growth_ledger.compute_summary - never a stored counter that could
    drift). Level is cosmetic only - see growth_ledger.py's module
    docstring. Nothing here is ever read by _orchestrator or anything
    that plans, authorizes, approves, or executes.
    """
    return _growth_ledger_store.summary()


@app.get("/capabilities")
def capabilities() -> dict:
    """
    URI's self-knowledge: what it can currently do, what is merely
    planned, and what model/provider is powering it right now - all
    read-only, purely for display. See capability_registry.py and
    model_providers/base.py's ModelProviderStatus for the invariant
    this endpoint depends on: neither section here is ever consulted
    by _orchestrator, capability_planner.py's selection logic, or
    dispatcher.py to decide what is authorized, approved, or executed.

    "model" reflects _model_provider.describe() - a cheap,
    timeout-bounded reachability check, never a real completion, so
    this endpoint stays fast even when the model backend is down
    (available: false with a detail message, not an error).
    """

    model_status = _model_provider.describe()

    return {
        "model": {
            "provider_name": model_status.provider_name,
            "model_name": model_status.model_name,
            "location": model_status.location,
            "context_window": model_status.context_window,
            "supports": list(model_status.supports),
            "available": model_status.available,
            "detail": model_status.detail,
        },
        "capabilities": [
            {
                "id": descriptor.id,
                "description": descriptor.description,
                "status": descriptor.status,
                "availability": descriptor.availability,
                "permissions": descriptor.permissions,
                "approval_requirement": descriptor.approval_requirement,
                "risk": descriptor.risk,
                "platform": descriptor.platform,
                "limitations": descriptor.limitations,
                "interface": descriptor.interface,
            }
            for descriptor in _capability_registry.list_capabilities()
        ],
    }
