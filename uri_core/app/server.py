"""Minimal HTTP boundary between the Flutter client and UriOrchestrator.

This exposes UriOrchestrator.process_user_input() over HTTP, unmodified.
No new authorization, planning, or execution logic lives here — this
file only does request/response plumbing (JSON in, JSON out) so a real
network client can reach the existing orchestrator entry point.

Run with (localhost-only, e.g. Flutter desktop/web on the same machine):
    uvicorn uri_core.app.server:app --reload --port 8000

M22.3: the server itself has no opinion on how uvicorn was launched, so
a raw `uvicorn ... --host 0.0.0.0` invocation is not guarded by this
file — see docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md section 5.3.
The SANCTIONED launcher for anything beyond localhost is
`scripts/run_uri_server.py`, which defaults to loopback-only and
refuses a non-loopback bind unless TLS is configured or
--allow-insecure-bind is explicitly passed (loud, logged):
    python scripts/run_uri_server.py --host 0.0.0.0 --allow-insecure-bind
This is a local development/LAN convenience, not production remote
access, when the insecure override is used - no TLS, no reverse proxy,
no authentication beyond this file's own login endpoints.
"""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, StrictInt

from uri_core.app.edge import (
    enforce_ask_content_length,
    enforce_login_rate_limit,
    enforce_signup_rate_limit,
)
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.approval_store import ApprovalStore
from uri_core.core.audit_comparison import build_shadow_comparison_report
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.authorization import AuthorizationError, require_admin
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.capability_resolver import (
    CapabilityGrantsStore,
    CapabilityResolver,
)
from uri_core.core import connection_status as connection_status_module
from uri_core.core.connection_status import list_connection_status
from uri_core.core.file_store import FileStore, FileValidationError
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.growth_ledger import GrowthLedgerStore
from uri_core.core.conversation_history import ConversationHistoryStore
from uri_core.core.experience_store import ExperienceStore
from uri_core.core.skill_memory import SkillMemory
from uri_core.skills.skill_installer import SkillInstaller
from uri_core.core.identity import DeviceIdentityStore, UserIdentityStore
from uri_core.config.model_roles import ROLE_REASONING, build_provider
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.personalization_context import (
    build_personalization_context,
)
from uri_core.core.devices import list_devices_for_user, revoke_device
from uri_core.core.portable_paths import (
    PortablePathValidationError,
    migrate_legacy_file_if_needed,
    user_scoped_path,
)
from uri_core.core.principal_context import PrincipalContext
from uri_core.core.state import SessionManager
from uri_core.core.user_accounts import (
    VALID_EXPERIENCE_TIERS,
    UserAccountError,
    UserAccountStore,
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
# Model reasoning is wired to Ollama/qwen3:14b here, at the application
# boundary, rather than as UriOrchestrator's own default - every other
# test/caller that constructs UriOrchestrator() with no args keeps the
# previous, network-free model_callable=None behaviour.
#
# As of Milestone 11 Phase 1, this is no longer purely observational:
# UriOrchestrator._run_model_reasoning's result may become the real
# plan for the direct single-capability path (see
# _model_proposed_capability/process_user_input's capability-selection
# step, both unmodified here) whenever the model proposes a registered
# capability that ModelReasoningGateway.validate_proposal() already
# accepted. CapabilityPlanner remains the deterministic fallback for
# everything else (model not configured/disabled, an invalid/
# unregistered proposal, or a proposed workflow rather than a single
# action), and any failure here (Ollama unreachable, timeout,
# malformed response) still degrades to a "reasoning_failed" status -
# same fallback either way - rather than raising. The execution
# boundary itself (ApprovalGate/ToolDispatcher) is unchanged regardless
# of which of these actually chose the tool_name.
#
# enable_response_narrative=True is this milestone's one explicit
# opt-in: UriOrchestrator defaults it to False specifically so every
# existing test/caller keeps its exact prior behaviour (see
# orchestrator.py's __init__ comment) - this server is the one place
# that turns the live conversational surface on, matching how model
# reasoning was already turned on here rather than as a class default.
# response.narrative stays additive - see _draft_narrative_safely - so
# this does not change what /ask returns for any client not yet
# reading that field.
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
_capability_grants_store = CapabilityGrantsStore()
_audit_trail = AuditTrail()

# A distinct provider instance from whatever _orchestrator's semantic
# interpreter/reasoning adapter use internally - deliberately not the
# same object, so this reporting-only self-knowledge query can never
# become entangled with the live request path. describe() is a cheap,
# timeout-bounded health check, never a real completion - see
# ModelProvider.describe's contract in model_providers/base.py.
#
# M21: built via the same role-based factory every real call site now
# uses (see config/model_roles.py), configured for ROLE_REASONING - the
# role GET /capabilities is most meaningfully reporting on, since that
# is the call that actually selects/proposes what URI does.
_model_provider = build_provider(ROLE_REASONING)

# ------------------------------------------------------------------
# Prototype 1 — multi-user identity + login foundation.
#
# _user_account_store is the install-wide login directory (username ->
# account, see user_accounts.py) - ambient/global like
# _capability_registry above, because it is the directory of who can
# log in, not per-user state itself.
#
# _auth_session_store maps an opaque, in-memory login token to a
# user_id (see auth_session.py) - a THIRD identifier, distinct from
# user_id/device_id (identity.py) and from the conversation session_id
# every /ask call already carries (state.py). Resetting the process
# always requires logging in again; this is a deliberate prototype
# simplification, not durable session persistence.
#
# Every endpoint below stays backward compatible with every existing,
# unauthenticated test/caller: _resolve_authenticated_user_id returns
# None when no Authorization header is sent at all, and _resolve_context
# maps None to the pre-existing legacy ambient globals
# (_user_profile_store/_memory_store/_growth_ledger_store/_orchestrator)
# untouched above - so a request that never logs in behaves exactly as
# it did before this milestone. Only a request that DOES present a
# valid bearer token gets routed to that user_id's own isolated
# context (see _get_user_context) - built lazily, once per user_id,
# and cached for the process lifetime in _user_contexts below.
# ------------------------------------------------------------------

_user_account_store = UserAccountStore()
_auth_session_store = AuthSessionStore()

# Overridable only by tests (mirrors _initialize_user_scoped_stores's
# own root parameter) so _build_user_context never has to touch the
# real uri_workspace/users/ tree during an automated test run - every
# other store in this codebase's test suite follows this same
# tempfile.TemporaryDirectory() isolation discipline.
_USER_STATE_ROOT = "uri_workspace/users"


@dataclass
class _UserContext:
    """Everything one logged-in user_id's request needs, all pointed
    at that user_id's own uri_workspace/users/<user_id>/ subtree (see
    portable_paths.user_scoped_path) - profile, memory, growth ledger,
    conversation sessions, and pending approvals. Nothing here is
    shared with any other user_id's _UserContext; nothing here is
    shared with the legacy ambient globals used when a request carries
    no Authorization header."""

    profile_store: UserProfileStore
    memory_store: MemoryStore
    growth_ledger_store: GrowthLedgerStore
    orchestrator: UriOrchestrator
    file_store: FileStore


_user_contexts: dict = {}


def _build_user_context(user_id: str) -> _UserContext:
    """Constructs a brand-new, fully isolated _UserContext for one
    user_id. Called at most once per user_id per process lifetime -
    see _get_user_context's cache. capability_registry is intentionally
    the shared, global _capability_registry (static, read-only
    configuration, not per-user secret data - identical to how every
    _UserContext's orchestrator already shares the same
    ModelReasoningGateway/OllamaReasoningAdapter shape the legacy
    _orchestrator above uses); everything else - approval store,
    session manager, profile/memory/growth stores - is constructed
    fresh, pointed only at this user_id's own directory."""

    profile_store = UserProfileStore(
        storage_path=user_scoped_path(
            user_id, "user_profile.json", root=_USER_STATE_ROOT
        )
    )
    memory_store = MemoryStore(
        storage_path=user_scoped_path(
            user_id, "user_memory.json", root=_USER_STATE_ROOT
        )
    )
    growth_ledger_store = GrowthLedgerStore(
        storage_path=user_scoped_path(
            user_id, "growth_ledger.json", root=_USER_STATE_ROOT
        )
    )

    approval_store = ApprovalStore(
        storage_path=user_scoped_path(
            user_id, "approvals.json", root=_USER_STATE_ROOT
        )
    )
    account = _user_account_store.get_by_user_id(user_id)
    role = account.role if account is not None else None
    principal = PrincipalContext(user_id=user_id, role=role, device_id=None)

    approval_gate = ApprovalGate(
        dispatcher=ToolDispatcher(),
        capability_registry=_capability_registry,
        approval_store=approval_store,
        audit_trail=AuditTrail(),
        capability_grants_store=_capability_grants_store,
        principal=principal,
    )

    session_manager = SessionManager(
        storage_path=user_scoped_path(
            user_id, "sessions", root=_USER_STATE_ROOT
        )
    )

    # M18: experience, skill memory, and the conversation transcript are
    # now user-scoped exactly like profile/memory/growth/sessions above -
    # before M18 they defaulted to global uri_workspace files, so one
    # user's learned skills, experience records, and past conversations
    # leaked into every other user's Brain context. Each is now pointed
    # only at this user_id's own directory.
    experience_store = ExperienceStore(
        storage_path=user_scoped_path(
            user_id, "experience.json", root=_USER_STATE_ROOT
        )
    )
    skill_memory = SkillMemory(
        storage_path=user_scoped_path(
            user_id, "skill_memory.json", root=_USER_STATE_ROOT
        )
    )
    conversation_history = ConversationHistoryStore(
        storage_dir=user_scoped_path(
            user_id, "conversation_history", root=_USER_STATE_ROOT
        )
    )

    # M21: file_store now follows the exact same per-user-directory
    # discipline as experience_store/skill_memory/conversation_history
    # above - before this, file_store.py's own docstring CLAIMED user
    # scoping "mirrors the existing convention exactly", but server.py
    # never actually constructed a per-user FileStore or passed one into
    # UriOrchestrator; every logged-in user shared the single ambient
    # _file_store (see below), so a client-supplied session_id could
    # collide across different user_id's and leak attachments between
    # them. Passed into UriOrchestrator(file_store=...) so the Brain's
    # own attachment_context (see orchestrator.py's file_store usage)
    # is scoped identically to the /files endpoints below.
    file_store = FileStore(
        storage_dir=user_scoped_path(
            user_id, "uploads", root=_USER_STATE_ROOT
        )
    )

    orchestrator = UriOrchestrator(
        model_reasoning_gateway=ModelReasoningGateway(
            model_callable=OllamaReasoningAdapter(principal=principal)
        ),
        enable_response_narrative=True,
        approval_gate=approval_gate,
        session_manager=session_manager,
        experience_store=experience_store,
        file_store=file_store,
        skill_memory=skill_memory,
        conversation_history=conversation_history,
        principal=principal,
    )

    return _UserContext(
        profile_store=profile_store,
        memory_store=memory_store,
        growth_ledger_store=growth_ledger_store,
        orchestrator=orchestrator,
        file_store=file_store,
    )


def _get_user_context(user_id: str) -> _UserContext:
    if user_id not in _user_contexts:
        _user_contexts[user_id] = _build_user_context(user_id)
    return _user_contexts[user_id]


def _resolve_context(user_id: Optional[str]) -> _UserContext:
    """The one place every endpoint below picks which state to read/
    write. user_id is None for a request with no (or no valid) login -
    see _resolve_authenticated_user_id - in which case this returns
    the pre-existing legacy ambient globals completely unchanged, so
    every test/caller that predates login keeps working exactly as it
    did before. A non-None user_id always returns that user_id's own
    isolated _UserContext, never anything shared with another user_id
    or with the legacy globals."""

    if user_id is None:
        return _UserContext(
            profile_store=_user_profile_store,
            memory_store=_memory_store,
            growth_ledger_store=_growth_ledger_store,
            orchestrator=_orchestrator,
            file_store=_file_store,
        )

    return _get_user_context(user_id)


def _resolve_authenticated_user_id(
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    """FastAPI dependency: None when no Authorization header is sent
    at all (preserves every existing endpoint's unauthenticated
    behaviour exactly). Raises 401 - never silently falls back to the
    legacy ambient state - when a header IS sent but is malformed,
    unknown, or expired, since silently downgrading a bad token to
    "no login" would let an expired/mistyped token quietly leak into
    someone else's ambient session instead of failing visibly."""

    if authorization is None:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be 'Bearer <token>'.",
        )

    token = authorization[len("Bearer "):].strip()
    user_id = _auth_session_store.resolve(token)

    if user_id is None:
        raise HTTPException(
            status_code=401, detail="Invalid or expired session token."
        )

    return user_id


def _resolve_principal(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
    authorization: Optional[str] = Header(default=None),
) -> PrincipalContext:
    """FastAPI dependency: the M22.2 PrincipalContext for the calling
    request, built only here (the edge - see principal_context.py's
    own docstring on why construction is confined to this file). Chains
    off _resolve_authenticated_user_id unmodified, so every existing
    401/legacy-ambient behaviour that dependency already provides is
    preserved exactly - this only ADDS role/device_id once user_id is
    already known.

    role is None whenever user_id is None (no login at all) - never
    guessed, never defaulted to a privileged value. device_id is looked
    up the same way GET /auth/me already does (via the raw token bound
    to THIS request), not persisted anywhere as authoritative state.

    M22.2 uses this only for its own new self-scoped endpoints (see
    POST /auth/experience-tier, GET/DELETE /auth/devices below) -
    existing endpoints are not retrofitted to depend on this in this
    milestone; see principal_context.py's module docstring."""

    if user_id is None:
        return PrincipalContext(user_id=None, role=None, device_id=None)

    account = _user_account_store.get_by_user_id(user_id)
    role = account.role if account is not None else None

    device_id = None
    if authorization is not None and authorization.startswith("Bearer "):
        device_id = _auth_session_store.get_device_id(
            authorization[len("Bearer "):].strip()
        )

    return PrincipalContext(
        user_id=user_id, role=role, device_id=device_id
    )


def _resolve_admin_principal(
    principal: PrincipalContext = Depends(_resolve_principal),
) -> PrincipalContext:
    """M22.3: FastAPI dependency wiring only - the actual ADMIN decision
    is authorization.require_admin(), a pure function with no FastAPI
    dependency (see its own docstring). This function's only job is to
    translate that pure decision's AuthorizationError into the exact
    HTTPException status code it already chose: 401 when there is no
    logged-in principal at all, 403 when a real principal's role is
    insufficient. Attached to the five endpoints M22.3 closes (S1):
    /skills/{id}/enable, /skills/{id}/disable, DELETE /skills/{id},
    POST /connections/{id}/authorize, DELETE /connections/{id} - none of
    which ever had a legacy-ambient anonymous fallback to preserve."""

    try:
        return require_admin(principal)
    except AuthorizationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


def _record_growth_event_safely(
    growth_ledger_store: GrowthLedgerStore,
    event_type: str,
    metadata: Optional[dict] = None,
) -> None:
    """Never raises - a growth-ledger failure must never break the
    real user-driven action it's downstream of. Mirrors
    orchestrator.py's _record_skill_router_audit/
    _record_model_reasoning_audit's own never-breaks-the-live-request
    discipline. Takes the store explicitly (rather than reaching for
    the legacy global) so it records to whichever user's context the
    calling endpoint resolved via _resolve_context."""
    try:
        growth_ledger_store.record_event(event_type, metadata)
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

# M22.3 (Decision 7, docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md
# section 6.6): CORS is never left at allow_origins=["*"]. Production
# deployments set URI_CORS_ALLOWED_ORIGINS to an explicit,
# comma-separated list of exact origins. With no env var set (the local
# dev default), only loopback origins are allowed, matched by an
# anchored regex covering any port - Flutter web's dev-server origin is
# not known ahead of time, but is always http(s)://localhost:<port> or
# http(s)://127.0.0.1:<port>. This governs browser-origin (Flutter web)
# callers only: native Android/iOS/desktop HTTP clients (the LAN-phone
# scenario documented above) neither send nor enforce CORS at all, so
# they are unaffected by this lockdown either way.
LOOPBACK_CORS_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


def _resolve_cors_kwargs(allowed_origins_env: str) -> dict:
    """Pure - given the raw URI_CORS_ALLOWED_ORIGINS value (possibly
    empty), returns the exact CORSMiddleware kwargs to use. Kept
    separate from app construction so the decision itself
    (explicit-allowlist vs loopback-only-regex) can be unit-tested
    without touching the live app's already-configured middleware - see
    test_m22_3_cors.py.

    A literal "*" is never honoured, even if someone sets
    URI_CORS_ALLOWED_ORIGINS=* by mistake - Decision 7 is "never *",
    not "never * unless configured otherwise". A misconfigured wildcard
    is dropped from the list rather than passed through; if that leaves
    no real origins, this falls back to the same loopback-only regex as
    an unset env var, rather than silently granting every origin."""

    origins = [
        origin.strip()
        for origin in allowed_origins_env.strip().split(",")
        if origin.strip() and origin.strip() != "*"
    ]

    if origins:
        return {"allow_origins": origins}

    return {"allow_origin_regex": LOOPBACK_CORS_ORIGIN_REGEX}


app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    **_resolve_cors_kwargs(os.environ.get("URI_CORS_ALLOWED_ORIGINS", "")),
)


class AskRequest(BaseModel):
    session_id: str
    # M22.3 (Decision 6): 64 KB maximum conversational text - the
    # field-level bound. edge.enforce_ask_content_length is the
    # lower-level Content-Length precheck that rejects an oversized body
    # before this field is ever parsed - see that module's docstring.
    text: str = Field(..., max_length=65536)


class ProfileUpdateRequest(BaseModel):
    communication_style: str
    autonomy_level: str
    focus_areas: List[str] = []


class MemoryWriteRequest(BaseModel):
    category: str
    content: str
    confidence: Optional[float] = None
    notes: Optional[str] = None


class MemoryConfirmRequest(BaseModel):
    # M18: optional correction applied when confirming a URI-proposed
    # memory. Both omitted = confirm as proposed.
    category: Optional[str] = None
    content: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    action_id: str
    session_id: Optional[str] = None


class SignupRequest(BaseModel):
    username: str
    password: str
    # Prototype 2 (multi-client + runtime awareness): the CLIENT's own
    # self-reported device_id (see auth_session.py's module docstring
    # and uri_ui/lib/services/device_identity.dart) - optional so every
    # Prototype 1 caller/test that predates this field keeps working
    # unchanged. Never validated against a shape (unlike user_id) and
    # never used for anything beyond GET /auth/me's informational
    # read-back - it carries no authentication or authorization
    # meaning by itself.
    device_id: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: Optional[str] = None


class UpdateGrantsRequest(BaseModel):
    grants: List[str]


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


@app.post("/auth/signup")
def signup(
    payload: SignupRequest,
    _rate_limit: None = Depends(enforce_signup_rate_limit),
) -> dict:
    """
    Prototype 1 (multi-user identity): creates a new login account and
    a fresh, isolated user_id for it (see user_accounts.py) - never the
    single ambient install-level user_id from GET /identity, which
    predates login and is unrelated to any account. Auto-logs-in on
    success (returns a real bearer token) so a client can go straight
    from signup to an authenticated request without a second call.

    Rejects a username that's already registered (case-insensitively)
    or fails the username/password shape checks in user_accounts.py -
    never overwrites an existing account.
    """
    try:
        account = _user_account_store.create_account(
            payload.username, payload.password
        )
    except UserAccountError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    token = _auth_session_store.create(
        account.user_id, device_id=payload.device_id
    )

    return {
        "user_id": account.user_id,
        "username": account.username,
        "token": token,
    }


@app.post("/auth/login")
def login(
    payload: LoginRequest,
    _rate_limit: None = Depends(enforce_login_rate_limit),
) -> dict:
    """
    Verifies username + password against user_accounts.py's stored
    PBKDF2 hash and, only on an exact match, issues a fresh bearer
    token bound to that account's user_id. Returns 401 (never 404 or a
    field-specific error) for both an unknown username and a wrong
    password, so this endpoint can never be used to enumerate valid
    usernames.
    """
    account = _user_account_store.authenticate(
        payload.username, payload.password
    )

    if account is None:
        raise HTTPException(
            status_code=401, detail="Invalid username or password."
        )

    # A fresh, independent token/device binding every login - this is
    # what lets the same account be logged in from two clients (e.g. a
    # phone and a PC) at once, each with its own token and its own
    # device_id, without one login displacing the other (see
    # test_multi_client_runtime.py).
    token = _auth_session_store.create(
        account.user_id, device_id=payload.device_id
    )

    return {
        "user_id": account.user_id,
        "username": account.username,
        "token": token,
    }


@app.post("/auth/logout")
def logout(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Revokes the presented token so it can never be resolved again.
    Requires a currently-valid token (a request with no/invalid token
    already fails via _resolve_authenticated_user_id before this body
    runs)."""
    if authorization is not None and authorization.startswith("Bearer "):
        _auth_session_store.revoke(authorization[len("Bearer "):].strip())

    return {"logged_out": True}


@app.get("/auth/me")
def auth_me(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Read-only: which user_id (if any) the presented token resolves
    to right now - lets a client check whether it's still logged in
    without side effects. authenticated is False (not a 401) when no
    Authorization header was sent at all, since that's a normal,
    supported "not logged in yet" state for every other endpoint in
    this file.

    Prototype 2 (multi-client + runtime awareness) adds two more,
    deliberately distinct fields so a client can tell all three kinds
    of identity apart at a glance:
        - device_id: THIS login's own client-reported device_id (see
          auth_session.py), i.e. "which of my devices am I on" - null
          when the login/signup call never supplied one.
        - runtime_device_id: the install this backend/Ollama runtime is
          actually running on (see identity.py's DeviceIdentityStore,
          unchanged from GET /identity) - i.e. "which PC is serving me
          right now". Two different clients of the same user talking
          to the same backend always see the identical
          runtime_device_id, even though each has its own device_id.
    Neither field is a credential and neither grants access to
    anything by itself.

    M22.2 adds two more read-only fields, sourced from the same
    account this endpoint already loads - see user_accounts.py's
    module docstring for why these are two deliberately separate,
    non-interchangeable concepts:
        - role: USER | ADMIN - a privilege, never self-assigned.
        - experience_tier: BASIC | ADVANCED - a zero-authority
          preference; see POST /auth/experience-tier to change it.
    Both are null only when not authenticated at all, exactly like
    every other field here.
    """
    if user_id is None:
        return {
            "authenticated": False,
            "user_id": None,
            "username": None,
            "role": None,
            "experience_tier": None,
            "device_id": None,
            "runtime_device_id": None,
        }

    account = _user_account_store.get_by_user_id(user_id)

    device_id = None
    if authorization is not None and authorization.startswith("Bearer "):
        device_id = _auth_session_store.get_device_id(
            authorization[len("Bearer "):].strip()
        )

    runtime_device_id = _device_identity_store.load_or_create().device_id

    return {
        "authenticated": True,
        "user_id": user_id,
        "username": account.username if account is not None else None,
        "role": account.role if account is not None else None,
        "experience_tier": (
            account.experience_tier if account is not None else None
        ),
        "device_id": device_id,
        "runtime_device_id": runtime_device_id,
    }


class ExperienceTierUpdateRequest(BaseModel):
    experience_tier: str


@app.post("/auth/experience-tier")
def update_experience_tier(
    payload: ExperienceTierUpdateRequest,
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """M22.2: the user changing their OWN experience_tier - a
    zero-authority display/guidance preference (see user_accounts.py's
    module docstring). principal.user_id is resolved only from the
    caller's own authenticated token (see _resolve_principal), never
    accepted as a request field, so this can never be used to change
    another account's tier. Requires a valid login (401 otherwise) -
    there is no legacy-ambient account to update for an unauthenticated
    caller."""

    if principal.user_id is None:
        raise HTTPException(
            status_code=401, detail="Login is required to change this."
        )

    if payload.experience_tier not in VALID_EXPERIENCE_TIERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "experience_tier must be one of "
                f"{sorted(VALID_EXPERIENCE_TIERS)}."
            ),
        )

    updated = _user_account_store.set_experience_tier(
        principal.user_id, payload.experience_tier
    )

    if updated is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    return {
        "user_id": updated.user_id,
        "experience_tier": updated.experience_tier,
    }


@app.get("/auth/devices")
def list_my_devices(
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """M22.2: the logged-in user's own currently-active devices (see
    devices.py) - each a distinct client-reported device_id with at
    least one still-valid login session. Self-scoped only:
    principal.user_id comes from the caller's own token (see
    _resolve_principal), never a request parameter, so this can never
    list another account's devices. Requires a valid login (401
    otherwise)."""

    if principal.user_id is None:
        raise HTTPException(
            status_code=401, detail="Login is required to view this."
        )

    devices = list_devices_for_user(
        _auth_session_store, principal.user_id
    )

    return {
        "devices": [
            {
                "device_id": device.device_id,
                "session_count": device.session_count,
                "most_recent_expires_at": device.most_recent_expires_at,
            }
            for device in devices
        ]
    }


@app.delete("/auth/devices/{device_id}")
def revoke_my_device(
    device_id: str,
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """M22.2: revokes every session the logged-in user has on ONE of
    their own devices (see devices.py.revoke_device) - e.g. "log out my
    phone from my desktop". Self-scoped only: only ever revokes
    sessions bound to the caller's OWN principal.user_id (see
    _resolve_principal), even if another account happens to report the
    identical device_id string (see devices.py's own test coverage on
    this). Reports honestly how many sessions were actually revoked; 0
    for an unknown device_id rather than an error. Requires a valid
    login (401 otherwise)."""

    if principal.user_id is None:
        raise HTTPException(
            status_code=401, detail="Login is required to do this."
        )

    revoked_count = revoke_device(
        _auth_session_store, principal.user_id, device_id
    )

    return {"device_id": device_id, "revoked_sessions": revoked_count}


@app.post("/ask")
def ask(
    payload: AskRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
    _size_check: None = Depends(enforce_ask_content_length),
) -> dict:
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
    #
    # Prototype 1 (multi-user identity): context resolves to the
    # logged-in user_id's own isolated profile/memory/orchestrator
    # when an Authorization header is present, and to the pre-existing
    # legacy ambient globals otherwise - see _resolve_context.
    context = _resolve_context(user_id)

    personalization_context = build_personalization_context(
        context.profile_store.load_or_create(),
        context.memory_store.list_all(),
    )

    principal = None
    if user_id is not None:
        account = _user_account_store.get_by_user_id(user_id)
        role = account.role if account is not None else None
        principal = PrincipalContext(user_id=user_id, role=role, device_id=None)

    result = context.orchestrator.process_user_input(
        session_id=payload.session_id,
        user_text=payload.text,
        personalization_context=personalization_context,
        principal=principal,
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
def approve(
    payload: ApprovalDecisionRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
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

    Prototype 1 (multi-user identity): resolves to the same per-user
    context /ask used to propose this action (see _resolve_context) -
    a logged-in user_id only ever reaches their own ApprovalStore, so
    User A can never approve/consume an action_id that only exists in
    User B's approvals.json.

    Bounded personalization (same discipline as POST /ask - see
    build_personalization_context) is passed through so the
    additive/shadow-rolled-out "narrative" field (Milestone 8A) can
    explain this decision's real outcome in URI's voice too, not only
    the initial proposal.
    """
    context = _resolve_context(user_id)

    personalization_context = build_personalization_context(
        context.profile_store.load_or_create(),
        context.memory_store.list_all(),
    )

    return context.orchestrator.decide_action(
        action_id=payload.action_id,
        approved=True,
        session_id=payload.session_id,
        personalization_context=personalization_context,
    )


@app.post("/cancel")
def cancel(
    payload: ApprovalDecisionRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """
    Records an explicit user rejection for one proposed action - the
    action is marked rejected and never executes. See POST /approve's
    docstring for the same contract notes, including per-user
    isolation.
    """
    context = _resolve_context(user_id)

    personalization_context = build_personalization_context(
        context.profile_store.load_or_create(),
        context.memory_store.list_all(),
    )

    return context.orchestrator.decide_action(
        action_id=payload.action_id,
        approved=False,
        session_id=payload.session_id,
        personalization_context=personalization_context,
    )


@app.get("/tasks")
def tasks(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """
    Read-only: every proposed action still awaiting a user decision,
    across all of THIS user's sessions - the backend for a
    cross-session "Tasks" view (UI prototype phase 1). Never mutates
    anything - approving or rejecting stays exclusively POST /approve /
    POST /cancel, exactly like every other read endpoint in this file
    never doubles as a write path.

    Prototype 1 (multi-user identity): a logged-in user_id only ever
    sees pending actions from their own ApprovalStore (see
    _resolve_context) - User A's /tasks list can never include an
    action proposed under User B's login.
    """
    context = _resolve_context(user_id)
    pending = context.orchestrator.approval_gate.approval_store.list_pending()

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
def get_profile(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Read-only view of the current user's profile - the logged-in
    user's own when authenticated, the legacy single ambient profile
    otherwise (see _resolve_context)."""
    context = _resolve_context(user_id)
    profile = context.profile_store.load_or_create()

    return {
        "communication_style": profile.communication_style,
        "autonomy_level": profile.autonomy_level,
        "focus_areas": profile.focus_areas,
        "updated_at": profile.updated_at,
    }


@app.post("/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """
    Replaces the whole profile (no partial-patch semantics yet).
    Prototype 1 (multi-user identity): writes to the logged-in user's
    own profile store when authenticated, or the legacy single ambient
    profile otherwise (see _resolve_context) - User A can never write
    to User B's profile.json.

    communication_style/autonomy_level/focus_areas are validated
    (enum-constrained, length-capped, credential-shape rejected - see
    user_profile.py's _validate_profile_fields) before being saved -
    this stopped being optional hygiene once profile data started
    reaching a model prompt via personalization_context.py.
    """
    context = _resolve_context(user_id)

    try:
        updated = context.profile_store.save(
            UserProfile(
                communication_style=payload.communication_style,
                autonomy_level=payload.autonomy_level,
                focus_areas=list(payload.focus_areas),
            )
        )
    except UserProfileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _record_growth_event_safely(
        context.growth_ledger_store, "profile_updated"
    )

    return {
        "communication_style": updated.communication_style,
        "autonomy_level": updated.autonomy_level,
        "focus_areas": updated.focus_areas,
        "updated_at": updated.updated_at,
    }


@app.get("/memory")
def list_memory(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """
    Every memory the current user holds, including any pending
    proposals (labelled by their consent field) - visible to the user
    for review. Nothing in this milestone ever creates a
    pending_confirmation entry; see user_memory.py. Prototype 1: a
    logged-in user_id only ever sees their own memory store (see
    _resolve_context) - User A can never list User B's memories.

    Whole-store listing doubles as this milestone's export mechanism -
    no separate export endpoint yet.
    """
    context = _resolve_context(user_id)

    return {
        "memories": [
            _memory_entry_to_dict(entry)
            for entry in context.memory_store.list_all()
        ]
    }


@app.post("/memory")
def add_memory(
    payload: MemoryWriteRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """
    The user explicitly asking URI to remember something -
    consent="user_provided" always, set unconditionally by MemoryStore
    itself, never taken from the request body. There is no path in
    this milestone for URI/the model to write a memory on its own.
    Prototype 1: written to the logged-in user's own memory store when
    authenticated (see _resolve_context).
    """
    context = _resolve_context(user_id)

    try:
        entry = context.memory_store.add(
            category=payload.category,
            content=payload.content,
            confidence=payload.confidence,
            notes=payload.notes,
        )
    except MemoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _record_growth_event_safely(
        context.growth_ledger_store,
        "memory_recorded",
        {"category": entry.category},
    )

    return _memory_entry_to_dict(entry)


@app.put("/memory/{memory_id}")
def update_memory(
    memory_id: str,
    payload: MemoryWriteRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Whole-entry replace (edit), same pattern as POST /profile.
    consent is preserved, not editable via this endpoint. Prototype 1:
    resolved against the logged-in user's own memory store, so a
    memory_id that only exists in another user's store correctly 404s
    here rather than being found."""
    context = _resolve_context(user_id)

    try:
        updated = context.memory_store.update(
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
def delete_memory(
    memory_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Real, complete removal - not a soft-delete/hide flag. Prototype
    1: resolved against the logged-in user's own memory store (see
    update_memory's docstring for the same cross-user 404 behaviour)."""
    context = _resolve_context(user_id)
    deleted = context.memory_store.delete(memory_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")

    return {"deleted": True, "memory_id": memory_id}


@app.post("/memory/{memory_id}/confirm")
def confirm_memory(
    memory_id: str,
    payload: Optional[MemoryConfirmRequest] = None,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M18: the user accepting a URI-proposed (pending_confirmation)
    memory, optionally correcting its category/content first. Only after
    this does the entry become eligible to inform URI
    (is_eligible_for_personalization). 404 for an unknown id."""
    context = _resolve_context(user_id)
    try:
        confirmed = context.memory_store.confirm(
            memory_id,
            category=payload.category if payload else None,
            content=payload.content if payload else None,
        )
    except MemoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if confirmed is None:
        raise HTTPException(status_code=404, detail="Memory not found.")

    return _memory_entry_to_dict(confirmed)


@app.get("/skills")
def list_skills() -> dict:
    """M18: the installed-skill ledger - every externally installed skill
    with its source, version, status (quarantined/enabled/disabled),
    declared capabilities and dependencies, and last validation report.
    This is NOT the runtime capability registry the dispatcher executes
    from; a skill listed here is tracked but not runnable until a human
    explicitly promotes it (a separate step by design), so reading this
    exposes what is installed without granting any of it execution."""
    installer = SkillInstaller()
    return {"skills": installer.list_installed()}


@app.post("/skills/{skill_id}/enable")
def enable_skill(
    skill_id: str,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M18: an operator vouching for an installed skill. Metadata only -
    flips its status to 'enabled'; it still never becomes executable
    through this call (promotion into the dispatcher is a separate,
    deliberate step). 404 for a skill that is not installed.

    M22.3 (S1): ADMIN-only - see
    docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md section 6.1. This
    endpoint had no authentication of any kind before this milestone."""
    result = SkillInstaller().enable(skill_id)
    if not result.ok:
        raise HTTPException(status_code=404, detail=result.detail or "Skill not installed.")
    return result.to_dict()


@app.post("/skills/{skill_id}/disable")
def disable_skill(
    skill_id: str,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M18: mark an installed skill disabled (metadata only).

    M22.3 (S1): ADMIN-only."""
    result = SkillInstaller().disable(skill_id)
    if not result.ok:
        raise HTTPException(status_code=404, detail=result.detail or "Skill not installed.")
    return result.to_dict()


@app.delete("/skills/{skill_id}")
def remove_skill(
    skill_id: str,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M18: remove an installed skill from the ledger entirely.

    M22.3 (S1): ADMIN-only."""
    result = SkillInstaller().remove(skill_id)
    if not result.ok:
        raise HTTPException(status_code=404, detail=result.detail or "Skill not installed.")
    return result.to_dict()


@app.get("/learning")
def learning_diagnostics(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M18: an honest, read-only summary of the memory/learning
    subsystem for THIS user, so a memory/learning problem is explainable
    rather than invisible. Counts only - never content - covering user
    memory (by consent state), stored experience, learned skills (with a
    confidence breakdown so a demoted/failing skill is visible), and
    saved conversations. Every field degrades to a safe zero/empty on a
    store failure rather than raising, and each degradation is reported
    as an explicit error string so 'why is this empty?' is answerable."""

    context = _resolve_context(user_id)
    errors: List[str] = []

    memory_by_consent: dict = {}
    try:
        for entry in context.memory_store.list_all():
            memory_by_consent[entry.consent] = memory_by_consent.get(entry.consent, 0) + 1
    except Exception as exc:
        errors.append(f"memory: {exc}")

    experience_count = 0
    try:
        experience_count = len(context.orchestrator.experience_store.recent())
    except Exception as exc:
        errors.append(f"experience: {exc}")

    skills_total = 0
    skills_recommended = 0
    skills_demoted = 0
    try:
        from uri_core.core.skill_memory import (
            SkillMemory as _SkillMemory,
            CONFIDENCE_RECALL_FLOOR as _FLOOR,
        )
        for skill in context.orchestrator.skill_memory.list_skills():
            skills_total += 1
            if _SkillMemory.confidence(skill) >= _FLOOR:
                skills_recommended += 1
            else:
                skills_demoted += 1
    except Exception as exc:
        errors.append(f"skills: {exc}")

    conversation_sessions = 0
    try:
        conversation_sessions = len(
            context.orchestrator.conversation_history.list_sessions(limit=200)
        )
    except Exception as exc:
        errors.append(f"conversations: {exc}")

    return {
        "memory": {
            "total": sum(memory_by_consent.values()),
            "by_consent": memory_by_consent,
            "pending_confirmation": memory_by_consent.get("pending_confirmation", 0),
        },
        "experience_records": experience_count,
        "skills": {
            "total": skills_total,
            "recommended": skills_recommended,
            "demoted": skills_demoted,
        },
        "conversation_sessions": conversation_sessions,
        "errors": errors,
    }


@app.post("/memory/{memory_id}/reject")
def reject_memory(
    memory_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M18: the user rejecting a URI-proposed memory. A rejection is a
    real, complete removal - a proposal the user declined leaves nothing
    behind. Same store call as delete; named separately so the client
    (and audit) can distinguish 'declined a proposal' from 'deleted an
    established memory'."""
    context = _resolve_context(user_id)
    deleted = context.memory_store.delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"rejected": True, "memory_id": memory_id}


@app.get("/growth")
def growth(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """
    Read-only summary: XP/level/achievements, always recomputed from
    the append-only growth event history (see
    growth_ledger.compute_summary - never a stored counter that could
    drift). Level is cosmetic only - see growth_ledger.py's module
    docstring. Nothing here is ever read by _orchestrator or anything
    that plans, authorizes, approves, or executes. Prototype 1: the
    logged-in user's own growth ledger when authenticated (see
    _resolve_context).
    """
    context = _resolve_context(user_id)
    return context.growth_ledger_store.summary()


@app.get("/capabilities")
def capabilities(
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """
    URI's self-knowledge: what it can currently do, what is merely
    planned, and what model/provider is powering it right now - all
    read-only, purely for display. M22.4: principal-aware, returning
    the resolved capability catalogue for the calling principal.
    """

    model_status = _model_provider.describe()
    if principal is not None and principal.user_id:
        resolved_descriptors = CapabilityResolver.resolve(
            principal=principal,
            capability_registry=_capability_registry,
            grants_store=_capability_grants_store,
        )
    else:
        resolved_descriptors = _capability_registry.list_capabilities()

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
                # M16: the honest reason a capability cannot be relied
                # on right now - "not_implemented" (no adapter exists,
                # and nothing the user says or approves changes that)
                # vs "unavailable_runtime" (it exists, this runtime
                # cannot use it yet). Null when genuinely usable. The
                # client needs this to explain a gap truthfully rather
                # than implying more detail would unblock it.
                "gap_reason": descriptor.gap_reason,
            }
            for descriptor in resolved_descriptors
        ],
    }


@app.get("/connections")
def connections() -> dict:
    """Real authorization state of URI's external service connections
    (Gmail, Drive), read-only and non-interactive - see
    connection_status.py. This exists so the client can show what is
    actually authorized instead of a hardcoded badge: before this
    endpoint, the Flutter client had no backend surface for
    connections at all and fell back to seeded mock data that always
    claimed "Connected".

    Like /capabilities above, this is purely informational - nothing
    here is ever consulted by _orchestrator, capability selection,
    approval, or execution, and querying it can never trigger an
    interactive OAuth sign-in on the server host.
    """

    return {"connections": list_connection_status()}


# ------------------------------------------------------------------
# M16 Priority 1 - user file attachments.
#
# The Engine side of the attachment boundary: it validates, authorizes,
# stores and lists files. It never extracts, interprets, or decides
# anything about their content - reading a file happens only when the
# Brain selects the registered read_attached_file capability and it is
# executed through the ordinary ApprovalGate/ToolDispatcher path (see
# uri_core/tools/read_attached_file.py).
#
# M21 (file store isolation fix): _file_store below is now ONLY the
# legacy ambient default used for a request with no (or no valid) login
# - identical in spirit to _user_profile_store/_memory_store above -
# never a store every user implicitly shares. Every endpoint resolves
# its actual store via _resolve_context(user_id), exactly like every
# other user-scoped endpoint in this file: a logged-in user_id gets its
# own FileStore, rooted at that user_id's own uri_workspace/users/
# <user_id>/uploads/ directory (see _build_user_context), so two
# different logged-in users who happen to reuse the same client-supplied
# session_id can never see or delete each other's attachments. Before
# this fix, file_store.py's own module docstring INCORRECTLY claimed
# this scoping already existed ("mirrors the existing convention
# exactly... identical to how MemoryStore/UserProfileStore are already
# wired") - this is the fix that makes that claim true.
# ------------------------------------------------------------------

_file_store = FileStore()


def _repo_root_for_credentials() -> str:
    """The directory connection_status.py resolves credential/token
    files against - reused here (rather than re-derived) so a real
    disconnect removes exactly the token the status check reads."""

    return connection_status_module._repo_root()


@app.post("/files")
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Accepts one user file for a conversation. Validation
    (type/size/name) is enforced in FileStore, not trusted from the
    client - see file_store.py. A rejected upload returns 400 with the
    real reason so the user can act on it, never a silent drop. Stored
    in the logged-in user's own isolated FileStore when authenticated
    (see _resolve_context), the legacy ambient store otherwise."""

    context = _resolve_context(user_id)
    content = await file.read()

    try:
        record = context.file_store.save(
            filename=file.filename,
            content=content,
            media_type=file.content_type,
            session_id=session_id,
        )

    except FileValidationError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {"file": record.to_reference()}


@app.get("/files")
def list_files(
    session_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Bounded references to the files attached to one conversation -
    never content, matching what the Brain itself is shown. Resolved
    against the logged-in user's own FileStore, so a session_id another
    user also happens to use never surfaces that user's attachments."""

    context = _resolve_context(user_id)

    return {
        "files": [
            record.to_reference()
            for record in context.file_store.list_for_session(session_id)
        ]
    }


@app.delete("/files/{file_id}")
def delete_file(
    file_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Removes an attachment the user no longer wants URI to have.
    Reports honestly whether anything was actually deleted. Scoped to
    the logged-in user's own FileStore - a file_id belonging to another
    user's store is simply not found there, matching that store's own
    honest "nothing deleted" report for any other unknown id."""

    context = _resolve_context(user_id)

    return {"deleted": context.file_store.delete(file_id)}


@app.get("/files/{file_id}/content")
def file_content(
    file_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> FileResponse:
    """Raw bytes of one previously uploaded attachment, so the client
    can let the user open/verify what they actually attached (the same
    file_id shown in an /ask turn's response, not a separate lookup).
    Scoped to the logged-in user's own FileStore (see _resolve_context)
    - a file_id belonging to another user's store resolves to nothing
    here, exactly like an unknown id. 404 either way, rather than
    leaking whether the id exists in someone else's store."""

    context = _resolve_context(user_id)
    record = context.file_store.get(file_id)
    path = context.file_store.path_for(file_id)

    if record is None or path is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    return FileResponse(
        path,
        media_type=record.media_type or "application/octet-stream",
        filename=record.filename,
    )


@app.get("/activity")
def activity(
    limit: int = 50,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M16 Priority 2: REAL activity, from the runtime's own AuditTrail
    (see audit_trail.py) - proposals, approvals, executions and
    recovery decisions that actually happened. This replaces a client
    fallback that previously served fabricated mock events.

    Honest scope: the audit store is in-memory, so this covers the
    current server process only. That is a real limitation of what URI
    can currently evidence, and is reported as an empty list after a
    restart rather than being padded with invented history.

    Structured outcomes only - never raw prompts, model responses, or
    chain-of-thought, matching audit_trail.py's own rule.
    """

    context = _resolve_context(user_id)

    try:
        events = context.orchestrator.audit_trail.store.query(
            limit=max(1, min(limit, 200))
        )
    except Exception:
        events = []

    return {
        "activity": [
            {
                "id": f"{event.event_type}-{index}",
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "status": event.status,
                "capability": event.capability,
                "session_id": event.session_id,
            }
            for index, event in enumerate(events)
        ]
    }


@app.get("/history")
def list_history(
    limit: int = 50,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M18: the user's own past conversations - a bounded summary list
    (session id, turn count, last activity, a short preview), most
    recently active first. Read from the durable per-user transcript
    store (see conversation_history.py); a logged-in user only ever
    sees their own (see _build_user_context). Degrades to an empty list
    rather than raising."""

    context = _resolve_context(user_id)
    try:
        sessions = context.orchestrator.conversation_history.list_sessions(
            limit=max(1, min(limit, 200))
        )
    except Exception:
        sessions = []
    return {"sessions": sessions}


@app.get("/history/{session_id}")
def get_history(
    session_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M18: the full transcript of one past conversation so a client can
    reload/resume it. Verbatim turns (user text + URI response + status),
    never a judgement. An unknown session degrades to an empty turn list
    rather than 404-leaking whether it exists."""

    context = _resolve_context(user_id)
    try:
        turns = context.orchestrator.conversation_history.get_session(session_id)
    except Exception:
        turns = []
    return {"session_id": session_id, "turns": turns}


@app.delete("/history/{session_id}")
def delete_history(
    session_id: str,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """M18: the user removing one of their own past conversations. Reports
    honestly whether anything was actually deleted."""

    context = _resolve_context(user_id)
    try:
        deleted = context.orchestrator.conversation_history.delete_session(session_id)
    except Exception:
        deleted = False
    return {"deleted": deleted, "session_id": session_id}


@app.post("/connections/{connection_id}/authorize")
def authorize_connection(
    connection_id: str,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M16 Priority 4: start Google sign-in for a service.

    Honest about what is actually possible: Google's installed-app
    consent flow opens a browser ON THE SERVER HOST (see
    GmailService.connect / InstalledAppFlow.run_local_server), so a
    phone cannot complete it remotely. This endpoint therefore does not
    pretend to authorize anything from the client - it reports what is
    genuinely required and returns the real, unchanged state.

    It deliberately does NOT invoke the interactive flow: a blocking
    browser prompt must never be triggerable by an HTTP request (the
    same rule connection_status.py already enforces for status reads).

    M22.3 (S1): ADMIN-only - this is an install-host-scoped action, not
    a per-user one (see docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md
    section 6.1). Had no authentication of any kind before this
    milestone.
    """

    if connection_id not in {"gmail", "drive"}:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown connection: {connection_id}",
        )

    credentials_present = os.path.exists(
        os.path.join(_repo_root_for_credentials(), "credentials.json")
    )

    return {
        "started": False,
        "detail": (
            "Google sign-in must be completed on the URI server host, "
            "where the consent browser opens. Run the one-time consent "
            "there, then refresh this screen."
            if credentials_present
            else "No Google client secret (credentials.json) is "
            "configured on the URI server host yet, so sign-in cannot "
            "be started."
        ),
        "connections": list_connection_status(),
    }


@app.delete("/connections/{connection_id}")
def disconnect_connection(
    connection_id: str,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M16 Priority 2: a REAL disconnect. Previously the client faked
    this against mock state, so "Disconnected" was displayed while
    nothing had changed.

    Revoking a Google connection means removing the stored OAuth token
    on the server host - after this, connection_status.py reports the
    service as needing authorization again, because it genuinely does.
    Both Gmail and Drive share one token file (they are one Google
    authorization with two scopes), so this is reported honestly as
    affecting both rather than pretending they are independent.

    M22.3 (S1): ADMIN-only - revokes a shared, install-wide token, not
    per-user state (see
    docs/plans/M22.3_SECURITY_ARCHITECTURE_PLAN.md section 6.1). Had no
    authentication of any kind before this milestone.
    """

    if connection_id not in {"gmail", "drive"}:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown connection: {connection_id}",
        )

    token_path = os.path.join(_repo_root_for_credentials(), "token.json")

    if not os.path.exists(token_path):
        return {
            "disconnected": False,
            "detail": "That service was not connected.",
            "connections": list_connection_status(),
        }

    try:
        os.remove(token_path)

    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"The stored token could not be removed: {error}",
        )

    return {
        "disconnected": True,
        "detail": (
            "Google authorization removed. Gmail and Drive share one "
            "token, so both now require sign-in again."
        ),
        "connections": list_connection_status(),
    }


# ------------------------------------------------------------------
# M22.4 - Capability Grants Administration (ADMIN only)
# ------------------------------------------------------------------

@app.get("/admin/users")
def list_admin_users(
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M22.4: List accounts for the admin grants UI picker.
    ADMIN only (401 anonymous, 403 non-admin).
    """
    accounts = _user_account_store._load()
    users = [
        {
            "user_id": acc.user_id,
            "username": acc.username,
            "role": acc.role,
            "created_at": acc.created_at,
        }
        for acc in accounts.values()
    ]
    return {"users": users}


@app.get("/admin/users/{user_id}/grants")
def get_user_grants(
    user_id: str,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M22.4: Current capability grants for a specific user.
    ADMIN only (401 anonymous, 403 non-admin).
    """
    all_descriptors = _capability_registry.list_capabilities()
    registry_ids = {d.id for d in all_descriptors}
    grants = _capability_grants_store.get_grants(
        user_id, registry_ceiling_ids=registry_ids
    )
    return {
        "user_id": user_id,
        "grants": sorted(list(grants)),
        "registry_ceiling": sorted(list(registry_ids)),
    }


@app.put("/admin/users/{user_id}/grants")
def update_user_grants(
    user_id: str,
    payload: UpdateGrantsRequest,
    principal: PrincipalContext = Depends(_resolve_admin_principal),
) -> dict:
    """M22.4: Replace a user's grant set.
    ADMIN only (401 anonymous, 403 non-admin).
    Validates every submitted capability_id against the live registry and
    rejects the whole request with 400 if any id is unknown.
    On success, writes an audit record via AuditTrail.record with acting admin
    user_id, target user_id, and resulting grant set.
    """
    all_descriptors = _capability_registry.list_capabilities()
    registry_ids = {d.id for d in all_descriptors}

    try:
        updated = _capability_grants_store.set_grants(
            user_id=user_id,
            granted_ids=payload.grants,
            valid_registry_ids=registry_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _audit_trail.record(
        event_type="admin_grant_mutation",
        status="success",
        metadata={
            "acting_user_id": principal.user_id or "unknown",
            "target_user_id": user_id,
            "resulting_grants": ",".join(sorted(list(updated))),
        },
    )

    return {
        "user_id": user_id,
        "grants": sorted(list(updated)),
        "status": "updated",
    }


# ---------------------------------------------------------------------------
# M22.5 — Provider registry and key management endpoints
# All three are USER-classified (route_classification.py).
# user_id always comes from the auth token, never from the request body.
# ---------------------------------------------------------------------------


class _UsageLimitsPayload(BaseModel):
    monthly_token_ceiling: Optional[StrictInt] = Field(..., ge=0)


@app.get("/usage")
def get_usage(user_id: Optional[str] = Depends(_resolve_authenticated_user_id)) -> dict:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    from uri_core.core.usage_aggregator import aggregate_month
    return aggregate_month(user_id)


@app.get("/usage/limits")
def get_usage_limits(user_id: Optional[str] = Depends(_resolve_authenticated_user_id)) -> dict:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    from uri_core.core.usage_ceiling_store import UsageCeilingStore
    store = UsageCeilingStore(user_id)
    return {"monthly_token_ceiling": store.get_ceiling(),
            "warn_threshold_ratio": store.get_warn_threshold_ratio()}


@app.put("/usage/limits")
def update_usage_limits(
    payload: _UsageLimitsPayload,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    from uri_core.core.usage_ceiling_store import UsageCeilingStore
    UsageCeilingStore(user_id).set_ceiling(payload.monthly_token_ceiling)
    return {**get_usage_limits(user_id), "status": "updated"}


class _ProviderKeyPayload(BaseModel):
    provider_id: str
    api_key: str


class _ProviderConfigPayload(BaseModel):
    provider_id: str
    base_url: Optional[str] = None
    model: Optional[str] = None


@app.post("/providers/keys")
def submit_provider_key(
    payload: _ProviderKeyPayload,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Submit an API key for a provider.

    The key is encrypted immediately on receipt and stored per-user.
    The raw key is NEVER stored in plaintext, logged, or returned.
    Only the last-four characters are included in the response as a
    confirmation signal.

    user_id comes exclusively from the auth token; a caller can never
    set another user's key by manipulating the request body.
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    from uri_core.core.provider_keys import ProviderKeyStore
    from uri_core.core.provider_registry import CATALOGUE_BY_ID

    if payload.provider_id not in CATALOGUE_BY_ID:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider_id: {payload.provider_id!r}. "
                   f"Known providers: {sorted(CATALOGUE_BY_ID)}",
        )

    try:
        key_store = ProviderKeyStore(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    last_four = payload.api_key[-4:] if len(payload.api_key) >= 4 else "****"
    key_store.set_key(payload.provider_id, payload.api_key)

    _audit_trail.record(
        event_type="provider_key_submitted",
        status="success",
        metadata={
            "user_id": user_id,
            "provider_id": payload.provider_id,
            # last_four only - never the key or any bigger fragment
            "last_four": last_four,
        },
    )

    return {
        "provider_id": payload.provider_id,
        "configured": True,
        "last_four": last_four,
    }


@app.get("/providers")
def list_providers(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Return the static provider catalogue merged with this user's
    configuration status.

    Each provider entry includes:
      - provider_id, display_name, adapter, base_url (catalogue default
        or user override)
      - configured: bool  (has_key)
      - last_four: str | null  (four-char confirmation only; never the key)
      - available: bool  (cheap reachability probe via describe())

    The raw key is never returned under any provider or model combination.
    """
    from uri_core.core.provider_registry import (
        PROVIDER_CATALOGUE,
        ProviderConfigStore,
    )
    from uri_core.core.provider_keys import ProviderKeyStore
    from uri_core.config.model_roles import UnknownModelProviderError
    from uri_core.core.model_providers import OpenAICompatibleProvider
    from uri_core.core.model_providers.base import ModelProviderConfig

    key_store: Optional[ProviderKeyStore] = None
    config_store: Optional[ProviderConfigStore] = None
    if user_id is not None:
        try:
            key_store = ProviderKeyStore(user_id)
            config_store = ProviderConfigStore(user_id)
        except ValueError:
            key_store = None
            config_store = None

    result = []
    for descriptor in PROVIDER_CATALOGUE:
        pid = descriptor.provider_id

        configured = False
        last_four = None
        if key_store is not None:
            configured = key_store.has_key(pid)
            if configured:
                info = key_store.describe_key(pid)
                last_four = info["last_four"] if info else None

        # Cheap reachability probe - never uses the key for this GET
        available = False
        if descriptor.adapter == "openai_compatible":
            try:
                user_cfg = config_store.get_provider_config(pid) if config_store else {}
                cfg = ModelProviderConfig(
                    base_url=user_cfg.get("base_url", descriptor.base_url),
                    model=user_cfg.get("model", (descriptor.models[0].model_id if descriptor.models else "")),
                )
                # No api_key for the health-check probe - just connectivity
                probe = OpenAICompatibleProvider(config=cfg)
                available = probe.describe().available
            except Exception:  # noqa: BLE001
                available = False
        elif descriptor.adapter == "ollama":
            from uri_core.core.model_providers import OllamaProvider
            try:
                probe_ollama = OllamaProvider()
                available = probe_ollama.describe().available
            except Exception:  # noqa: BLE001
                available = False

        result.append({
            "provider_id": pid,
            "display_name": descriptor.display_name,
            "adapter": descriptor.adapter,
            "base_url": descriptor.base_url,
            "configured": configured,
            "last_four": last_four,
            "available": available,
        })

    return {"providers": result}


@app.put("/providers/config")
def update_provider_config(
    payload: _ProviderConfigPayload,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Set per-user base_url and/or model override for a provider.

    Does not touch key material. Does not require a key to already be
    configured (a user may configure the endpoint before submitting a key).

    user_id comes exclusively from the auth token.
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    from uri_core.core.provider_registry import CATALOGUE_BY_ID, ProviderConfigStore

    if payload.provider_id not in CATALOGUE_BY_ID:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider_id: {payload.provider_id!r}.",
        )

    updates: dict = {}
    if payload.base_url is not None:
        updates["base_url"] = payload.base_url
    if payload.model is not None:
        updates["model"] = payload.model

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    config_store = ProviderConfigStore(user_id)
    config_store.set_provider_config(payload.provider_id, updates)

    return {"provider_id": payload.provider_id, "status": "updated", **updates}

