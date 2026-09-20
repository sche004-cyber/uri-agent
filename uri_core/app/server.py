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

import asyncio
import json
import os
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Direct ``uvicorn uri_core.app.server:app`` development starts do not pass
# through scripts/run_uri_server.py, which otherwise supplies this local
# credential-store secret.  Preserve an explicitly configured secret.
os.environ.setdefault("URI_PROVIDER_KEY_SECRET", "uri_local_dev_secret_key_v1")

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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
from uri_core.config.model_roles import ROLE_REASONING, build_provider, load_model_roles
from uri_core.core.model_reasoning_adapter import OllamaReasoningAdapter
from uri_core.core.model_reasoning_gateway import ModelReasoningGateway
from uri_core.core.orchestrator import UriOrchestrator
from uri_core.core.evidence_fact_integrity import EvidenceLedger, FileEvidenceStore
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
from uri_core.config.modes import DEFAULT_MODE, VALID_MODES
from uri_core.core.user_memory import (
    MemoryEntry,
    MemoryStore,
    MemoryValidationError,
)
from uri_core.core.memory_settings import (
    MemorySettingsStore,
    MemorySettingsValidationError,
)
from uri_core.core.user_profile import (
    UserProfile,
    UserProfileStore,
    UserProfileValidationError,
)
from uri_core.external.operation_store import FileOperationStore
from uri_core.external.evidence_adapter import complete_operation_feedback
from uri_core.core.graph_store import GraphStore
from uri_core.core.graphify_index import (
    DEFAULT_INDEX_PATH, GraphifyIndex, build_index, load_index, save_index,
)
from uri_core.core.startup_services import run_startup_services
from uri_core.core.graph_engine import (
    graph_explain,
    graph_get_entity,
    graph_impact,
    graph_neighbors,
    graph_path,
    graph_query,
)
from uri_core.core.graph_ingest import ingest_memory_entry

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
_memory_settings_store = MemorySettingsStore()

# M23: graph context/evidence only - never authority (see
# graph_store.py/graph_engine.py module docstrings). Legacy-ambient
# single-install store, same convention as every store above.
# _orchestrator (constructed above, before this store existed) is
# repointed at this same instance so its Brain-facing graph_context
# section reads the identical store the /graph/* routes below expose
# for an anonymous/legacy caller - never two silently-divergent files.
_graph_store = GraphStore()
_orchestrator.graph_store = _graph_store

# Graphify Foundation: a system-level, read-only capability/skill/
# workflow/memory-pointer index - "URI's cognitive index and GPS."
# Separate from _graph_store above (M23's own per-user facts/memory
# graph, unchanged). Starts empty; GraphifyIndexLoader (below,
# registered as a Startup Service) loads or builds the real index at
# real application startup. Never authoritative - see
# graphify_index.py's own module docstring. A bare, non-lifespan
# TestClient(app) (every existing test's own convention) never
# populates this beyond empty, which is always a safe, valid state.
_graphify_index = GraphifyIndex()
_orchestrator.graphify_index = _graphify_index

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

# M33 Batch C bounded fix: the legacy ambient path (no Authorization
# header, no user_id, predates login) never gets a per-user durable
# EvidenceLedger/FileOperationStore - FileEvidenceStore/FileOperation
# Store both require a real UUID user_id (see portable_paths.py) and
# no such identity exists on this branch. Nothing currently reads
# operation_store or complete_operation_feedback off the legacy
# _UserContext, so an in-memory-only ledger and an explicit no-op
# feedback callable satisfy _UserContext's fields honestly, without
# fabricating per-user durability that does not apply here.
_legacy_evidence_ledger = EvidenceLedger()
_legacy_operation_store = None


def _legacy_complete_operation_feedback(operation_id, completion):
    return None


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
    memory_settings_store: MemorySettingsStore
    growth_ledger_store: GrowthLedgerStore
    orchestrator: UriOrchestrator
    file_store: FileStore
    graph_store: GraphStore
    # M33 Batch C: these stores are constructed per authenticated user and
    # rehydrate on process restart.  C3 alone will route legacy evidence
    # projections through this ledger, so this is composition, not a second
    # runtime authority alongside the legacy dict transport.
    evidence_ledger: EvidenceLedger
    operation_store: FileOperationStore
    complete_operation_feedback: object
    # M33.1: store-root consistency
    external_capability_store: Optional[Any] = None
    connected_service_store: Optional[Any] = None
    external_credential_store: Optional[Any] = None
    external_lifecycle_lock: Any = field(default_factory=threading.RLock)


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
    memory_settings_store = MemorySettingsStore(
        storage_path=user_scoped_path(
            user_id, "memory_settings.json", root=_USER_STATE_ROOT
        )
    )
    account = _user_account_store.get_by_user_id(user_id)
    role = account.role if account is not None else None
    mode = account.mode if account is not None else DEFAULT_MODE
    principal = PrincipalContext(
        user_id=user_id, role=role, device_id=None, mode=mode
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

    # 2026-09-12 (User directive): passed as ApprovalGate(file_store=...)
    # so both of its real dispatch points inject THIS user's own
    # FileStore into a tool's constructor (see dispatcher.py) - not
    # this user's own uploads directory, since a generated file was
    # previously always saved to the ambient uri_workspace/uploads
    # store instead and could never be found again via this same
    # user's own GET /files/{file_id}/content lookup below.
    audit_trail = AuditTrail()
    approval_gate = ApprovalGate(
        dispatcher=ToolDispatcher(),
        capability_registry=_capability_registry,
        approval_store=approval_store,
        audit_trail=audit_trail,
        capability_grants_store=_capability_grants_store,
        principal=principal,
        file_store=file_store,
    )

    # M23: graph_store follows the exact same per-user-directory
    # discipline as file_store/experience_store/skill_memory above -
    # one user's structured graph never leaks into another's (see
    # graph_store.py's own module docstring and
    # test_graph_isolation.py). Passed into UriOrchestrator(graph_store=
    # ...) so the Brain's own bounded graph_context section
    # (orchestrator._build_graph_context) reads only this user's own
    # data, and into _UserContext so the /graph/* endpoints below read
    # the same instance.
    graph_store = GraphStore(
        storage_path=user_scoped_path(
            user_id, "graph.sqlite3", root=_USER_STATE_ROOT
        )
    )

    # M33 Batch C: construct durable stores at the same user-context seam as
    # every other user-owned store.  Their constructors perform fail-closed
    # rehydration; no replay or resubmission occurs here.
    evidence_ledger = EvidenceLedger(
        store=FileEvidenceStore(user_id=user_id, root=_USER_STATE_ROOT)
    )
    operation_store = FileOperationStore(user_id=user_id, root=_USER_STATE_ROOT)

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
        graph_store=graph_store,
    )
    # C3: the workflow's compatibility dicts are now derived from this one
    # durable ledger; the orchestrator never owns an independent evidence map.
    orchestrator.evidence_ledger = evidence_ledger
    orchestrator.pending_completion_evidence = []

    def _complete_operation_feedback(operation_id, completion):
        projection = complete_operation_feedback(
            operation_store=operation_store,
            ledger=evidence_ledger,
            operation_id=operation_id,
            completion=completion,
        )
        if projection is not None:
            orchestrator.pending_completion_evidence.append(projection)
        return projection

    # M33 Batch B: composition, not orchestrator growth. orchestrator.py's
    # own MultiActionDispatch(capability_registry=...) construction
    # (unmodified by this milestone) stays exactly what P1 found; this
    # wires the M33 Batch B seams onto the already-built instance:
    #   - a fresh registry generation (D3) containing this user's own
    #     enabled+qualified external capabilities (Batch A's store),
    #     built on top of the same base Gmail registration `Multi
    #     ActionDispatch`'s own default construction already used;
    #   - the generalized, fail-closed external-permission resolver
    #     (uri_core/external/permission_binding.py) - never Capability
    #     Resolver's legacy missing-grant full-registry default;
    #   - a real audit_sink (executor.py's own already-existing kwarg,
    #     previously never passed) - the SAME AuditTrail instance
    #     approval_gate above already uses, so one user's multi-action
    #     executions land in the one audit trail their approvals do.
    from uri_core.capabilities.discovery import CapabilityDiscoveryEngine
    from uri_core.capabilities.gmail import GmailCapability
    from uri_core.external.adapters.in_process import remember_fact_capability
    from uri_core.external.credentials import ExternalCredentialStore
    from uri_core.external.permission_binding import make_permission_resolver
    from uri_core.external.registry_bridge import ExternalCapabilityPublisher
    from uri_core.external.service_store import ConnectedServiceStore
    from uri_core.external.store import ExternalCapabilityStore

    external_credential_store = ExternalCredentialStore(root=_USER_STATE_ROOT)
    external_capability_store = ExternalCapabilityStore(root=_USER_STATE_ROOT)
    connected_service_store = ConnectedServiceStore(
        root=_USER_STATE_ROOT, credential_store=external_credential_store
    )

    _remember_descriptor = _capability_registry.describe_status("remember_fact")
    _base_capabilities = [GmailCapability()]
    if _remember_descriptor is not None:
        _base_capabilities.append(remember_fact_capability(_remember_descriptor, principal=principal))
    _publisher = ExternalCapabilityPublisher(store=external_capability_store)
    _publish_result = _publisher.publish(user_id, base_capabilities=_base_capabilities)
    orchestrator.multi_action_dispatch.registry = _publish_result.registry
    orchestrator.multi_action_dispatch.discovery = CapabilityDiscoveryEngine(
        orchestrator.multi_action_dispatch.registry
    )
    orchestrator.multi_action_dispatch.external_permission_resolver = make_permission_resolver(
        store=external_capability_store
    )
    # This is a derived, per-user view.  Never mutate the process-global
    # Graphify index with a user's installed capability/service state: doing
    # so would leak that state to another user's context.
    orchestrator.graphify_index = GraphifyIndex(records=dict(_graphify_index.records))
    orchestrator.multi_action_dispatch.audit_sink = (
        lambda entry: audit_trail.record(
            event_type="multi_action_capability_execution",
            status=str(entry.get("status", "unknown")),
            session_id=None,
            capability=entry.get("capability"),
            metadata=entry,
        )
    )

    return _UserContext(
        profile_store=profile_store,
        memory_store=memory_store,
        memory_settings_store=memory_settings_store,
        growth_ledger_store=growth_ledger_store,
        orchestrator=orchestrator,
        file_store=file_store,
        graph_store=graph_store,
        evidence_ledger=evidence_ledger,
        operation_store=operation_store,
        complete_operation_feedback=_complete_operation_feedback,
        external_capability_store=external_capability_store,
        connected_service_store=connected_service_store,
        external_credential_store=external_credential_store,
    )


def refresh_user_external_lifecycle(
    user_id: str, context: Optional[_UserContext] = None
) -> Any:
    """Synchronously republish the external capability registry, update live
    MultiActionDispatch registry & discovery references, and refresh Graphify
    derived capability and service indexes without requiring a server restart."""
    if context is None:
        context = _get_user_context(user_id)
    with context.external_lifecycle_lock:
        from uri_core.capabilities.gmail import GmailCapability
        from uri_core.external.adapters.in_process import remember_fact_capability
        from uri_core.external.permission_binding import make_permission_resolver
        from uri_core.external.registry_bridge import ExternalCapabilityPublisher
        from uri_core.core.multi_action_dispatch import MultiActionDispatch

        base_caps = [GmailCapability()]
        rem = _capability_registry.describe_status("remember_fact")
        if rem is not None:
            principal = getattr(context.orchestrator, "principal", None)
            base_caps.append(remember_fact_capability(rem, principal=principal))
        publisher = ExternalCapabilityPublisher(store=context.external_capability_store)
        res = publisher.publish(user_id, base_capabilities=base_caps)
        previous_dispatch = context.orchestrator.multi_action_dispatch
        next_dispatch = MultiActionDispatch(
            registry=res.registry,
            granted_permissions=previous_dispatch._explicit_permissions,
            permission_checker=previous_dispatch.permission_checker,
            capability_registry=previous_dispatch.capability_registry,
            external_permission_resolver=make_permission_resolver(
                store=context.external_capability_store
            ),
            audit_sink=previous_dispatch.audit_sink,
        )
        graphify = getattr(context.orchestrator, "graphify_index", None)
        if graphify is not None:
            from uri_core.core.capability_directory import CapabilityDirectory
            from uri_core.core.graphify_index import refresh as graphify_refresh

            cap_dir = CapabilityDirectory(multi_action_registry=res.registry)
            graphify_refresh(graphify, capability_directory=cap_dir, scope="capabilities")
            if context.connected_service_store is not None:
                graphify_refresh(
                    graphify,
                    connected_service_store=context.connected_service_store,
                    user_id=user_id,
                    scope="services",
                )
        # One attribute replacement publishes a complete coherent generation:
        # registry, discovery engine, permission resolver, selected-session
        # state, and cached executors can never be mixed across generations.
        context.orchestrator.multi_action_dispatch = next_dispatch
        return res


def _connection_status_for_user(user_id: Optional[str]) -> list[dict]:
    """Project status from the same composed service store as execution."""
    service_store = None
    if user_id is not None:
        service_store = _get_user_context(user_id).connected_service_store
    return list_connection_status(user_id=user_id, service_store=service_store)


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
            memory_settings_store=_memory_settings_store,
            growth_ledger_store=_growth_ledger_store,
            orchestrator=_orchestrator,
            file_store=_file_store,
            graph_store=_graph_store,
            evidence_ledger=_legacy_evidence_ledger,
            operation_store=_legacy_operation_store,
            complete_operation_feedback=_legacy_complete_operation_feedback,
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
        return PrincipalContext(user_id=None, role=None, device_id=None, mode=None)

    account = _user_account_store.get_by_user_id(user_id)
    role = account.role if account is not None else None
    mode = account.mode if account is not None else DEFAULT_MODE

    device_id = None
    if authorization is not None and authorization.startswith("Bearer "):
        device_id = _auth_session_store.get_device_id(
            authorization[len("Bearer "):].strip()
        )

    return PrincipalContext(
        user_id=user_id, role=role, device_id=device_id, mode=mode
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


def _resolve_authenticated_principal(
    principal: PrincipalContext = Depends(_resolve_principal),
) -> PrincipalContext:
    """Any signed-in user, regardless of role - 401 when there is no
    login at all, never a 403 for a non-ADMIN role. Google Workspace
    connect/disconnect (see POST /connections/credentials, POST
    /connections/{id}/authorize, DELETE /connections/{id}) is
    per-request User directive: open to every authenticated user, not
    ADMIN-only - unlike the five endpoints that still require
    _resolve_admin_principal (skills enable/disable/remove,
    /admin/users*), which remain ADMIN-only and are unaffected by
    this."""

    if principal.user_id is None:
        raise HTTPException(
            status_code=401, detail="Sign in required for this action."
        )
    return principal


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


class _UserScopedStoreInitializer:
    """Startup Service wrapper around the pre-existing
    `_initialize_user_scoped_stores()` - identical behavior, now the
    first entry in a real, generic list instead of `_lifespan()`'s own
    only hardcoded call."""

    def start(self) -> None:
        _initialize_user_scoped_stores()


class _GraphifyIndexLoader:
    """Startup Service: loads the persisted Graphify Foundation index
    (`uri_workspace/graphify_index.json`), or builds a fresh one from
    the real, already-existing authorities (`CapabilityDirectory`,
    `SkillMemory`, `WorkflowPlanner`, `MemoryStore`) when none is
    persisted yet or the persisted one is empty. Never raises, never
    blocks server startup - see `graphify_index.py`'s own module
    docstring for why an empty/stale index is always a safe state."""

    def start(self) -> None:
        global _graphify_index

        index = load_index(DEFAULT_INDEX_PATH)
        if not index.records:
            capability_directory = None
            try:
                from uri_core.core.decision_engine import build_turn_state_and_directory

                _, capability_directory = build_turn_state_and_directory(
                    orchestrator=_orchestrator, session_id=None, user_text="", principal=None,
                )
            except Exception:
                capability_directory = None

            index = build_index(
                capability_directory=capability_directory,
                skill_memory=getattr(_orchestrator, "skill_memory", None),
                workflow_planner=getattr(_orchestrator, "workflow_planner", None),
                memory_store=_memory_store,
            )
            save_index(index, DEFAULT_INDEX_PATH)

        _graphify_index = index
        _orchestrator.graphify_index = index


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """FastAPI/Starlette lifespan: the one place explicit application
    startup work belongs, as opposed to module import. Runs for a real
    `uvicorn uri_core.app.server:app` launch and for
    `with TestClient(app):`; does not run for a bare
    `TestClient(app)` with no `with` block, which every existing test
    in this repo uses - those tests are unaffected either way because
    they already override the store globals directly in setUp() (and,
    for `_graphify_index`, an empty/default index is always a safe,
    valid state - see `graphify_index.py`'s own module docstring).

    Startup Services (docs/plans/M30_GRAPHIFY_FOUNDATION_PLAN.md §A.5):
    a real, generic list, not a hardcoded one-off - a service's own
    failure never blocks another service or prevents the server from
    starting (see `run_startup_services()`)."""
    run_startup_services([
        _UserScopedStoreInitializer(),
        _GraphifyIndexLoader(),
    ])
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
    model_override: Optional[object] = None
    # M34: explicit request-scoped attachment handles.  Omission remains
    # the historical no-current-attachment shape; never infer from files
    # persisted earlier in the session.
    attached_file_ids: List[str] = Field(default_factory=list)


class FallbackRoutingRequest(BaseModel):
    primary: Optional[dict] = None
    fallback_1: Optional[object] = None
    fallback_2: Optional[dict] = None


_verified_models_cache: dict = {}
_VERIFIED_MODELS_TTL_SECONDS = 300


def _verified_models_for(user_id: Optional[str], provider_id: str) -> list:
    """Return the short-lived result of an explicit credential verification."""
    if not user_id:
        return []
    entry = _verified_models_cache.get((user_id, provider_id))
    if not entry or entry[0] <= time.monotonic():
        return []
    return list(entry[1])


def _selectable_models_for(user_id: Optional[str], provider_id: str) -> list:
    """Return models URI may route to for this user/provider.

    Cloud entries are limited to an explicit credential verification. Ollama's
    installed inventory is already direct evidence of model availability and
    must not disappear when the short-lived verification cache expires.
    """
    if provider_id != "ollama":
        return _verified_models_for(user_id, provider_id)
    try:
        from uri_core.core.model_providers import OllamaProvider
        from uri_core.core.model_providers.base import ModelProviderConfig

        installed = OllamaProvider(ModelProviderConfig.from_env()).list_installed_models()
        return list(dict.fromkeys(installed + _verified_models_for(user_id, provider_id)))
    except Exception:  # noqa: BLE001
        return _verified_models_for(user_id, provider_id)


def _measured(record: dict, field: str) -> Optional[float]:
    """Unwrap a UsageRecord {"value", "confidence"} field to its plain
    numeric value only when actually measured - never guesses or
    substitutes 0/None-as-zero for a genuinely unavailable measurement
    (Live UX Repair §8: never fabricate an unavailable token count)."""
    entry = record.get(field)
    if not isinstance(entry, dict) or entry.get("confidence") != "KNOWN":
        return None
    value = entry.get("value")
    return value if isinstance(value, (int, float)) else None


def _serving_model_for_turn(user_id: Optional[str], session_id: str) -> dict:
    """Return the most recent successful router record for this request:
    provider_id, model, and (Live UX Repair §8) whichever of
    prompt_tokens/eval_tokens/duration_seconds were actually measured -
    never a fabricated number for a field the provider never reported.

    ModelRouter writes this observational record only after a ModelResponse
    succeeds, so it describes the provider/model that actually served the
    turn rather than a configured preference or attempted candidate.
    """
    empty = {
        "provider_id": None, "model": None,
        "prompt_tokens": None, "eval_tokens": None, "duration_seconds": None,
    }
    if not user_id:
        return dict(empty)
    try:
        from uri_core.core.usage_meter import current_month, month_records

        records = [
            record for record in month_records(user_id, current_month())
            if record.get("session_id") == session_id and record.get("outcome") == "success"
        ]
        # UsageMeter records created by existing adapters do not always carry
        # the conversational session ID.  They remain user-scoped, so use the
        # latest successful observation for that user when the precise match
        # is unavailable.
        if not records:
            records = [
                record for record in month_records(user_id, current_month())
                if record.get("outcome") == "success"
            ]
        if records:
            latest = records[-1]
            return {
                "provider_id": latest.get("provider_id"),
                "model": latest.get("model"),
                "prompt_tokens": _measured(latest, "prompt_tokens"),
                "eval_tokens": _measured(latest, "eval_tokens"),
                "duration_seconds": _measured(latest, "duration_seconds"),
            }
    except Exception:
        pass
    return dict(empty)


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


class MemorySettingsPayload(BaseModel):
    persistent_memory: Optional[bool] = None
    user_profile: Optional[bool] = None
    memory_budget: Optional[StrictInt] = None
    profile_budget: Optional[StrictInt] = None
    memory_provider: Optional[str] = None
    context_engine: Optional[str] = None
    auto_compression: Optional[bool] = None
    compression_threshold: Optional[StrictInt] = None
    compression_target: Optional[StrictInt] = None
    protected_recent_messages: Optional[StrictInt] = None

    def supplied(self) -> dict:
        return self.model_dump(exclude_none=True)


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


class ModeUpdateRequest(BaseModel):
    mode: str


@app.get("/modes")
def get_mode(
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """Return only the authenticated caller's current capability mode."""
    if principal.user_id is None:
        raise HTTPException(status_code=401, detail="Login is required to view this.")
    return {"mode": principal.mode or DEFAULT_MODE, "valid_modes": sorted(VALID_MODES)}


@app.put("/modes")
def update_mode(
    payload: ModeUpdateRequest,
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """Change only the authenticated caller's mode; body/query IDs are ignored."""
    if principal.user_id is None:
        raise HTTPException(status_code=401, detail="Login is required to change this.")
    if payload.mode not in VALID_MODES:
        raise HTTPException(
            status_code=422, detail=f"mode must be one of {sorted(VALID_MODES)}."
        )
    updated = _user_account_store.set_mode(principal.user_id, payload.mode)
    if updated is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    _user_contexts.pop(principal.user_id, None)
    return {"mode": updated.mode, "valid_modes": sorted(VALID_MODES)}


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


def _resolve_ask_context(payload: "AskRequest", user_id: Optional[str]):
    """Shared context/principal resolution for POST /ask and POST
    /ask/stream (M32 D5) - extracted verbatim from /ask's own opening
    so the two endpoints can never independently drift on identity,
    personalization, or per-request model-override rebinding. Returns
    ``(context, principal, personalization_context)``.

    Bounded personalization (Milestone 8A): only the confirmed profile
    and consent-eligible memory (never pending_confirmation, never
    growth/XP - see personalization_context.py) is assembled here, at
    the HTTP boundary, using the same user-scoped stores every other
    endpoint already reads - never inside UriOrchestrator itself,
    preserving its existing zero-coupling to profile/memory (see
    Milestone 5-7's structural boundary tests). This can only ever
    influence how a response is *phrased* (see _draft_narrative_safely)
    - it is never read by capability selection, approval, or execution.

    Prototype 1 (multi-user identity): context resolves to the
    logged-in user_id's own isolated profile/memory/orchestrator when
    an Authorization header is present, and to the pre-existing legacy
    ambient globals otherwise - see _resolve_context.
    """
    context = _resolve_context(user_id)

    personalization_context = build_personalization_context(
        context.profile_store.load_or_create(),
        context.memory_store.list_all(),
    )

    principal = None
    if user_id is not None:
        account = _user_account_store.get_by_user_id(user_id)
        role = account.role if account is not None else None
        mode = account.mode if account is not None else DEFAULT_MODE
        principal = PrincipalContext(
            user_id=user_id, role=role, device_id=None, mode=mode,
            model_override=payload.model_override,
        )
        # User contexts are cached, but a conversation model override belongs
        # to this request only. Rebind the reasoning adapter before any model
        # call so the router sees the composer selection rather than the
        # principal that happened to construct this user's cached context.
        context.orchestrator.principal = principal
        context.orchestrator.model_reasoning_gateway.model_callable = (
            OllamaReasoningAdapter(principal=principal)
        )
        from uri_core.core.provider_semantic_interpreter import ProviderSemanticInterpreter

        context.orchestrator.semantic_interpreter = ProviderSemanticInterpreter(
            principal=principal
        )

    return context, principal, personalization_context


def _current_turn_attachment_references(context, payload: "AskRequest") -> List[dict]:
    """Validate and project only attachment handles named by THIS /ask.

    File stores are user-scoped through ``context``; session ownership is
    additionally checked here.  Unknown, cross-session, or malformed ids
    are rejected rather than silently exposed or treated as an attachment.
    """
    file_ids = payload.attached_file_ids or []
    if len(file_ids) > 20 or any(not isinstance(file_id, str) or not file_id for file_id in file_ids):
        raise HTTPException(status_code=400, detail="attached_file_ids must contain at most 20 non-empty file ids.")
    references = []
    for file_id in dict.fromkeys(file_ids):
        record = context.file_store.get(file_id)
        if record is None or record.session_id != payload.session_id:
            raise HTTPException(status_code=400, detail="Attached file is unavailable for this session.")
        references.append(record.to_reference())
    return references


def _lifecycle_intent_ask_envelope(
    session_id: Optional[str], lifecycle_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Project `execute_lifecycle_intent`'s own result dict into the exact
    `{"status", "session_id", "execution", "response"}` shape `/ask` already
    relays - the same "deterministic status message" convention canonical_
    execution.py's own `_canonical_nonexecution_envelope` already uses for
    every other non-execution outcome (approval_required/disconnected/
    unsupported/clarification), not a new one invented for this seam."""
    status = lifecycle_result.get("status", "unavailable")
    operation = lifecycle_result.get("operation")
    target_id = lifecycle_result.get("target_id")
    messages = {
        "success": f"'{operation}' on '{target_id}' completed.",
        "not_installed": f"'{target_id}' is not installed, so '{operation}' has nothing to do.",
        "unknown_target": f"'{target_id}' is not a recognized skill or service.",
        "unsupported_operation": f"'{operation}' is not a supported lifecycle operation.",
        "invalid_intent": "That lifecycle request could not be understood.",
        "credentials_required": (
            f"Connecting '{target_id}' requires credentials; use the connect flow to provide them."
        ),
        "rejected": f"'{operation}' on '{target_id}' was rejected.",
    }
    message = messages.get(status, f"'{operation}' on '{target_id}' returned '{status}'.")
    response: Dict[str, Any] = {"message": message}
    if "state" in lifecycle_result:
        response["state"] = lifecycle_result["state"]
    return {
        "status": "success" if status == "success" else "unavailable",
        "session_id": session_id,
        "execution": {"status": status, "operation": operation, "target_id": target_id},
        "response": response,
    }


def _record_lifecycle_intent_audit(
    context, user_id: str, session_id: Optional[str], lifecycle_result: Dict[str, Any]
) -> None:
    """Record structured lifecycle evidence without retaining prompt text or secrets."""
    try:
        context.orchestrator.audit_trail.record(
            event_type="lifecycle_intent",
            status=str(lifecycle_result.get("status", "unavailable")),
            session_id=session_id,
            metadata={
                "user_id": user_id,
                "operation": lifecycle_result.get("operation"),
                "target_id": lifecycle_result.get("target_id"),
            },
        )
    except Exception:
        # Audit persistence must not turn a completed state transition into a
        # fabricated failure; the runtime result remains authoritative.
        pass


@app.post("/ask")
def ask(
    payload: AskRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
    _size_check: None = Depends(enforce_ask_content_length),
) -> dict:
    context, principal, personalization_context = _resolve_ask_context(payload, user_id)
    current_turn_attachments = _current_turn_attachment_references(context, payload)

    # M32.1: a durable, pending approval-required action (see
    # approval_resumption.py) gets first chance at this turn, before
    # anything else even attempts to interpret it fresh - a plain "yes"
    # sent as a brand-new message would otherwise be reinterpreted by
    # the Brain as an unrelated request. Isolated, default-off,
    # never raises: any failure here falls straight through to the
    # existing chain below exactly as if this block did not exist.
    result = None
    early_executed = False
    try:
        from uri_core.core.approval_resumption import (
            approval_resumption_enabled,
            resume_pending_approval,
        )

        if approval_resumption_enabled():
            resumed = resume_pending_approval(
                orchestrator=context.orchestrator, session_id=payload.session_id,
                user_text=payload.text, principal=principal,
            )
            if resumed is not None:
                result = resumed
                early_executed = True
    except Exception:
        result = None
        early_executed = False

    # M33.1 Batch 4: a bounded, deterministic (model-free) lifecycle-intent
    # seam - "enable skill yt_dlp", "connect service github", etc. Isolated
    # and additive exactly like the approval-resumption block above: any
    # failure, or a `None` interpretation (every ordinary conversational
    # message), falls straight through to the unchanged chain below. The
    # executor is a narrow closure bound to THIS request's already-
    # authenticated `context`/`user_id` - the interpreter never supplies or
    # chooses a user_id, and the seam never runs at all for the
    # unauthenticated/legacy-ambient path (`user_id is None`). All real
    # authority (catalog membership, state-machine legality, isolation)
    # remains `execute_lifecycle_intent`'s - the exact same function
    # Batch 4's standalone acceptance tests already exercise; this block
    # only ever decides WHETHER to call it, never what it is allowed to do.
    if not early_executed:
        try:
            from uri_core.core.lifecycle_intent_interpreter import (
                interpret as interpret_lifecycle_intent,
                lifecycle_intent_seam_enabled,
            )

            if lifecycle_intent_seam_enabled() and user_id is not None:
                intent = interpret_lifecycle_intent(payload.text)
                if intent is not None:
                    from uri_core.external.lifecycle_intent import execute_lifecycle_intent

                    lifecycle_result = execute_lifecycle_intent(
                        context, user_id,
                        operation=intent["operation"], target_id=intent["target_id"],
                    )
                    _record_lifecycle_intent_audit(
                        context, user_id, payload.session_id, lifecycle_result
                    )
                    result = _lifecycle_intent_ask_envelope(payload.session_id, lifecycle_result)
                    early_executed = True
        except Exception:
            result = None
            early_executed = False

    # M30.7: pending WorkflowExecutor pauses otherwise resume inside the
    # legacy orchestrator before the Decision Contract can judge whether this
    # message is actually a continuation.  This isolated, default-off branch
    # gives that judgment one chance first; every fallback keeps the legacy
    # order below intact.
    # M32.1: only run this check (and only reset legacy_fallback) when
    # the approval-resumption block above did NOT already produce a
    # result - never reset result/early_executed here, or this would
    # silently discard a real, already-resumed approval decision before
    # it ever reached the response.
    legacy_fallback = None
    if not early_executed:
        try:
            from uri_core.core.canonical_execution import workflow_continuation_mode_enabled

            if workflow_continuation_mode_enabled():
                from uri_core.core.canonical_execution import run_canonical_for_ask

                session = context.orchestrator.session_manager.get_session(payload.session_id)
                if (
                    session.active_workflow is not None
                    and session.active_workflow_status == "waiting_for_input"
                ):
                    observed = {}

                    def _observe_decision(contract, gate_result):
                        observed["mode"] = contract.get("mode")
                        observed["gate_outcome"] = getattr(gate_result, "outcome", None)

                    early_result = run_canonical_for_ask(
                        orchestrator=context.orchestrator,
                        session_id=payload.session_id,
                        user_text=payload.text,
                        principal=principal,
                        personalization_context=personalization_context,
                        decision_observer=_observe_decision,
                        current_turn_attachments=current_turn_attachments,
                    )
                    if observed.get("mode") == "workflow_continuation" and early_result is not None:
                        if early_result.get("_canonical_fallback"):
                            legacy_fallback = early_result
                        else:
                            result = early_result
                            early_executed = True
                    elif observed.get("mode") and observed.get("mode") != "workflow_continuation":
                        context.orchestrator._clear_active_workflow(session)
        except Exception:
            pass

    # M32 Batch C: the native tool loop (Tier 0 direct chat / Tier 1
    # native tool calling), built ON canonical's existing gate/execution
    # boundary - see native_tool_loop.py. Runtime-settable, OFF by
    # default (plan §10: "the toggle must be runtime-settable, not a
    # module constant") - materially newer code than canonical's own
    # flags, with less accumulated live evidence, so it has not yet
    # earned the same default-on bar. A None result (turn-state assembly
    # failure, or the toggle simply being off) falls through completely
    # unchanged to the existing canonical/legacy chain below - this can
    # never be a third, competing execution route: it is additive, and
    # inert until explicitly enabled.
    if result is None and not early_executed:
        try:
            from uri_core.core.native_tool_loop import (
                default_model_callable,
                native_tool_loop_enabled,
                run_native_tool_loop,
            )

            if native_tool_loop_enabled():
                native_result = run_native_tool_loop(
                    orchestrator=context.orchestrator,
                    session_id=payload.session_id,
                    user_text=payload.text,
                    principal=principal,
                    model_callable=default_model_callable(principal),
                    current_turn_attachments=current_turn_attachments,
                )
                if native_result is not None:
                    result = native_result
        except Exception:
            pass

    # M30.8: canonical is the default authority.  A canonical response is
    # terminal whether it executes or correctly reports clarification,
    # unsupported, connection, approval, or conversation state.  Legacy is
    # reached only for an explicit engine/model failure marker.  A narrowed
    # allowlist is the emergency rollback lever and deliberately restores
    # legacy-first behavior for the process.
    if result is None and not early_executed:
        try:
            from uri_core.core.canonical_execution import (
                canonical_killswitch_enabled,
                decision_engine_live_enabled,
                run_canonical_for_ask,
            )

            if decision_engine_live_enabled():
                if canonical_killswitch_enabled():
                    legacy_fallback = {
                        "fallback_reason": "CANONICAL_KILLSWITCH",
                        "gate_outcome": "KILLSWITCH",
                    }
                elif legacy_fallback is None:
                    canonical_result = run_canonical_for_ask(
                        orchestrator=context.orchestrator,
                        session_id=payload.session_id,
                        user_text=payload.text,
                        principal=principal,
                        personalization_context=personalization_context,
                        current_turn_attachments=current_turn_attachments,
                    )
                    if canonical_result.get("_canonical_fallback"):
                        legacy_fallback = canonical_result
                    else:
                        result = canonical_result
        except Exception:
            legacy_fallback = {
                "fallback_reason": "engine_failure:canonical_route_exception",
                "gate_outcome": "DEGRADED",
            }

    if result is None:
        result = context.orchestrator.process_user_input(
            session_id=payload.session_id,
            user_text=payload.text,
            personalization_context=personalization_context,
            principal=principal,
        )
        if legacy_fallback is not None:
            try:
                from uri_core.core.decision_engine import record_shadow_trace

                record_shadow_trace({
                    "event": "legacy_fallback",
                    "session_id": payload.session_id,
                    "user_text_length_bucket": len(payload.text or "") // 20 * 20,
                    "fallback_reason": legacy_fallback.get("fallback_reason"),
                    "gate_outcome": legacy_fallback.get("gate_outcome"),
                })
            except Exception:
                pass

    # M30.3: canonical Brain Decision Engine, SHADOW MODE ONLY - proposes
    # a decision for comparison, never executes, never alters `result`.
    # Env-var gated (default off, see decision_engine.py's own docstring
    # for why an env var rather than a constructor flag); the call itself
    # is fully self-contained and swallows its own failures, but the
    # flag check + import are also guarded here so a shadow-mode issue
    # can never reach a real user's response.
    try:
        from uri_core.core.decision_engine import (
            decision_engine_shadow_enabled,
            run_shadow_for_ask,
        )

        if decision_engine_shadow_enabled():
            run_shadow_for_ask(
                orchestrator=context.orchestrator,
                session_id=payload.session_id,
                user_text=payload.text,
                principal=principal,
                old_path_result=result,
            )
    except Exception:
        pass

    return _finalize_ask_response(context, user_id, payload, result)


def _finalize_ask_response(
    context, user_id: Optional[str], payload: "AskRequest", result: dict
) -> dict:
    """Shared tail for POST /ask and POST /ask/stream's "done" event
    (M32 D5) - extracted verbatim from /ask's own tail so the two
    endpoints can never independently drift on serving-model annotation
    or on which fields of the orchestrator's raw result cross the wire.

    The router writes the serving-model observation only after a
    successful completion. It is read here, after the request, so
    captions describe the actual serving model, never merely the user's
    requested override.
    """
    _serving = _serving_model_for_turn(user_id, payload.session_id)
    serving_provider = _serving["provider_id"]
    serving_model = _serving["model"]
    serving_prompt_tokens = _serving["prompt_tokens"]
    serving_eval_tokens = _serving["eval_tokens"]
    serving_duration_seconds = _serving["duration_seconds"]
    if (
        serving_provider is None
        and isinstance(payload.model_override, dict)
        and isinstance(payload.model_override.get("provider_id"), str)
        and isinstance(payload.model_override.get("model"), str)
    ):
        # Older adapter seams do not carry session_id into UsageMeter.  A
        # request-scoped override remains the selected conversation model even
        # when the request fails before a successful router observation exists;
        # it never changes global routing state. No token/duration
        # measurement exists for this fallback path - it stays None
        # (Live UX Repair §8: never fabricate an unavailable measurement).
        serving_provider = payload.model_override["provider_id"]
        serving_model = payload.model_override["model"]
    try:
        context.orchestrator.conversation_history.annotate_latest_turn(
            payload.session_id,
            serving_provider=serving_provider,
            serving_model=serving_model,
        )
    except Exception:
        # Best-effort caption annotation (see annotate_latest_turn's own
        # docstring): a request-scoped or minimal orchestrator context
        # that lacks conversation_history must never turn this into a
        # failed /ask response - the same defensive stance already taken
        # for the shadow decision-engine call just above.
        pass

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
        "narrative_unavailable_reason": result.get(
            "narrative_unavailable_reason"
        ),
        "serving_provider": serving_provider,
        "serving_model": serving_model,
        "serving_prompt_tokens": serving_prompt_tokens,
        "serving_eval_tokens": serving_eval_tokens,
        "serving_duration_seconds": serving_duration_seconds,
    }


def _sse_event(event: str, data: dict) -> str:
    """Formats one Server-Sent Event (M32 D5). Every event this endpoint
    emits carries a JSON object payload, never raw text, so a client can
    parse every event the same way regardless of kind."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _ask_stream_eligible(context, payload: "AskRequest") -> bool:
    """M32 D5: true only for the one case this design targets - native
    tool loop enabled, and no workflow_continuation pause pending for
    this session (§13.1/§13.6: a resumed workflow's turn is always a
    structured, non-prose decision, never streamed prose). Anything
    else (native_tool_loop off, or a genuine pending pause) delegates
    to the existing, completely unmodified ask() rather than being
    re-routed here - this function only ever decides whether to TRY the
    fast path, never re-implements what ask() itself would decide."""
    try:
        from uri_core.core.canonical_execution import workflow_continuation_mode_enabled
        from uri_core.core.native_tool_loop import native_tool_loop_enabled

        if not native_tool_loop_enabled():
            return False
        if workflow_continuation_mode_enabled():
            session = context.orchestrator.session_manager.get_session(payload.session_id)
            if (
                session.active_workflow is not None
                and session.active_workflow_status == "waiting_for_input"
            ):
                return False
        return True
    except Exception:
        return False


@app.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    request: Request,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
    _size_check: None = Depends(enforce_ask_content_length),
) -> StreamingResponse:
    """M32 D5: streaming counterpart to POST /ask.

    Streams live content ONLY for the one case this design targets -
    native tool loop enabled, Tier 0 (no tool call), no pending
    workflow_continuation (see _ask_stream_eligible,
    docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §13). Every
    other case - native_tool_loop off, a pending approval/workflow pause,
    the stream-capacity cap already at limit, or the fast path declining
    to produce a result at all (turn-state assembly failure - the SAME
    "None means fall back" convention /ask's own native_tool_loop branch
    already follows) - delegates to the existing, completely unmodified
    ask() function and re-emits its single dict as one terminal "message"
    SSE event. This endpoint never re-implements /ask's own 4-tier
    routing logic (workflow_continuation / native_tool_loop / canonical /
    legacy) - it only ever decides whether to TRY the streaming fast
    path first, and always falls back to calling ask() itself, verbatim,
    for everything else.

    Per the User's frozen design and its clarification: a first content
    chunk never proves a turn is terminal. Every "content" SSE event is
    provisional until "done" arrives; if a "tool_call_detected" event
    appears, every prior "content" event for this turn must be treated
    as discarded by the client - the eventual "done" event's `envelope`
    (or the fallback "message" event) is always the single source of
    truth for what actually happened and what was persisted.
    """
    context, principal, personalization_context = _resolve_ask_context(payload, user_id)
    current_turn_attachments = _current_turn_attachment_references(context, payload)

    async def _fallback_to_ask():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: ask(payload, user_id=user_id, _size_check=None)
        )
        yield _sse_event("message", result)
        yield _sse_event("done", {"narrative_interrupted": False})

    async def _generate():
        # Streaming Tier 0 has no Turn State payload seam.  Attachment
        # turns therefore use the ordinary /ask path, which passes the
        # one validated structured signal to canonical/native routing;
        # do not create a second stream-only attachment mechanism.
        if current_turn_attachments or not _ask_stream_eligible(context, payload):
            async for chunk in _fallback_to_ask():
                yield chunk
            return

        from uri_core.core.stream_tool_loop import (
            StreamCapacityExceededError,
            stream_first_turn,
        )

        cancel_event = threading.Event()
        loop = asyncio.get_event_loop()
        stream_iter = iter(stream_first_turn(
            orchestrator=context.orchestrator, session_id=payload.session_id,
            user_text=payload.text, principal=principal, cancel_event=cancel_event,
        ))
        _STREAM_EXHAUSTED = object()

        def _next_or_sentinel():
            # A bare `next()` raising StopIteration cannot be awaited
            # through run_in_executor (PEP 479: StopIteration may never
            # propagate out of a coroutine/Future) - a sentinel return
            # value sidesteps that cleanly instead of catching
            # StopIteration around the await itself.
            return next(stream_iter, _STREAM_EXHAUSTED)

        try:
            while True:
                if await request.is_disconnected():
                    cancel_event.set()
                    break
                try:
                    # Blocking next() runs off the event loop thread so
                    # `await request.is_disconnected()` can still be
                    # polled between items, without blocking the server.
                    event = await loop.run_in_executor(None, _next_or_sentinel)
                except StreamCapacityExceededError:
                    async for chunk in _fallback_to_ask():
                        yield chunk
                    return
                if event is _STREAM_EXHAUSTED:
                    break

                if event.kind == "content":
                    yield _sse_event("content", {"text": event.content})
                elif event.kind == "tool_call_detected":
                    yield _sse_event("tool_call_detected", {})
                elif event.kind == "error":
                    yield _sse_event("error", {"error": event.error})
                elif event.kind == "done":
                    if event.envelope is None:
                        async for chunk in _fallback_to_ask():
                            yield chunk
                        return
                    finalized = _finalize_ask_response(context, user_id, payload, event.envelope)
                    yield _sse_event("done", {
                        "response": finalized,
                        "ttft_seconds": event.ttft_seconds,
                        "narrative_interrupted": event.narrative_interrupted,
                    })
        finally:
            cancel_event.set()

    return StreamingResponse(_generate(), media_type="text/event-stream")


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


@app.get("/system/performance")
def system_performance(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Read-only real CPU/memory/disk snapshot for the dashboard's
    System tab (2026-09-12, User directive). No GPU/temperature/fan/
    power metrics - psutil cannot read those on this platform, and the
    UI must show them as unavailable rather than fabricate a value."""
    from uri_core.tools.system_performance import SystemPerformanceTool

    return SystemPerformanceTool().report()


@app.get("/gmail/unread-count")
def gmail_unread_count(
    principal: PrincipalContext = Depends(_resolve_principal),
) -> dict:
    """Return Gmail's current unread-label count without proposing or
    executing an action.  A failed Gmail read is passed through unchanged so
    the UI can render an explicit unavailable state rather than inventing a
    count."""
    user_id = principal.user_id
    if user_id:
        from uri_core.core.capability_resolver import CapabilityResolver

        if not CapabilityResolver.is_allowed("gmail_search", principal=principal):
            return {
                "success": False,
                "error": "Capability 'gmail_search' is not granted for this user.",
                "unread_count": None,
            }

    from uri_core.services.gmail_search_service import GmailSearchService

    return GmailSearchService(user_id=user_id).get_unread_count()


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

    # M23: the real, live ingestion trigger point (plan section 9) -
    # a memory becoming eligible for personalization right here is
    # exactly the moment graph_ingest.ingest_memory_entry's own
    # eligibility re-check expects. user_id may be None for the
    # legacy-ambient path; ingest_memory_entry treats an empty
    # external user_id the same way upsert_node already does (no
    # special-casing needed here). Never blocks the confirm response
    # on a graph-store failure - this is additive context, not
    # authority, so any exception here must never surface as this
    # endpoint's own failure.
    try:
        ingest_memory_entry(context.graph_store, confirmed, user_id or "")
    except Exception:
        pass

    return _memory_entry_to_dict(confirmed)


# ---------------------------------------------------------------
# M23: Graph Intelligence - read-only, self-scoped query/traversal.
#
# Every route below reads exactly one thing: the authenticated
# caller's OWN GraphStore (see _resolve_context) - never another
# user's. All six are pure reads over graph_engine.py's bounded
# primitives; none writes. The graph is context/evidence for the
# Brain, never an independent authorization source (see
# graph_store.py/graph_engine.py module docstrings and
# test_graph_authority_boundary.py) - nothing here grants, checks, or
# implies any capability/approval authority.
# ---------------------------------------------------------------


@app.get("/graph/entities/{entity_id}")
def graph_get_entity_route(
    entity_id: str,
    limit: int = 50,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """One node (plus its bounded, ACTIVE-only incident edges) from the
    caller's own graph. 404 for an unknown id, or one that belongs to
    a different user's isolated GraphStore - this route can never
    distinguish those two cases from the caller's own store, which is
    the isolation guarantee itself (see test_graph_isolation.py)."""
    context = _resolve_context(user_id)
    result = graph_get_entity(context.graph_store, entity_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return result


@app.get("/graph/query")
def graph_query_route(
    entity_type: Optional[str] = None,
    name_contains: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Filtered node listing over the caller's own graph. limit is
    always server-capped by graph_engine.graph_query regardless of the
    query-parameter value supplied."""
    context = _resolve_context(user_id)
    return {"entities": graph_query(context.graph_store, entity_type=entity_type, name_contains=name_contains, limit=limit)}


@app.get("/graph/neighbors/{entity_id}")
def graph_neighbors_route(
    entity_id: str,
    relationship_types: Optional[str] = None,
    direction: str = "both",
    limit: int = 50,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """One-hop neighbors of entity_id in the caller's own graph, each
    with its connecting edge's own provenance/confidence/status.
    relationship_types is a comma-separated list, e.g.
    'DEPENDS_ON,AFFECTS'; omitted means all types."""
    context = _resolve_context(user_id)
    types = [t.strip() for t in relationship_types.split(",")] if relationship_types else None
    return {
        "neighbors": graph_neighbors(
            context.graph_store, entity_id, relationship_types=types, direction=direction, limit=limit
        )
    }


@app.get("/graph/path")
def graph_path_route(
    source_id: str,
    target_id: str,
    max_hops: int = 4,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Bounded shortest path between two entities in the caller's own
    graph. max_hops is always clamped server-side (graph_engine.
    MAX_HOPS_CEILING) regardless of the query-parameter value
    supplied. {"path": null} when no path exists within the bound -
    never an error."""
    context = _resolve_context(user_id)
    return {"path": graph_path(context.graph_store, source_id, target_id, max_hops=max_hops)}


@app.get("/graph/explain")
def graph_explain_route(
    source_id: str,
    target_id: str,
    max_hops: int = 4,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Why are these two entities connected: the bounded path plus
    each edge's own provenance/confidence/status - real citations, not
    a generated narrative (that remains the Brain's own job)."""
    context = _resolve_context(user_id)
    return graph_explain(context.graph_store, source_id, target_id, max_hops=max_hops)


@app.get("/graph/impact/{entity_id}")
def graph_impact_route(
    entity_id: str,
    relationship_types: Optional[str] = None,
    direction: str = "incoming",
    max_hops: int = 3,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    """Bounded impact analysis: what would be affected if entity_id
    changed, along the named relationship types (default DEPENDS_ON/
    AFFECTS). Read-only and reporting-only - never a trigger for any
    execution decision (see graph_engine.graph_impact's own
    docstring)."""
    context = _resolve_context(user_id)
    types = [t.strip() for t in relationship_types.split(",")] if relationship_types else ("DEPENDS_ON", "AFFECTS")
    return {
        "impact": graph_impact(
            context.graph_store, entity_id, relationship_types=types, direction=direction, max_hops=max_hops
        )
    }


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
def connections(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
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

    return {"connections": _connection_status_for_user(user_id)}


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


class GoogleCredentialsUploadRequest(BaseModel):
    raw_json: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


def _google_client_credentials(payload: GoogleCredentialsUploadRequest) -> dict:
    """Validate and normalize a Google OAuth client-secrets document."""
    if payload.raw_json is not None:
        try:
            credentials = json.loads(payload.raw_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=400,
                detail="raw_json must be valid Google OAuth client credentials JSON.",
            ) from exc

        if not isinstance(credentials, dict):
            raise HTTPException(
                status_code=400,
                detail="Google OAuth credentials must be a JSON object.",
            )

        for client_type in ("installed", "web"):
            client = credentials.get(client_type)
            if (
                isinstance(client, dict)
                and isinstance(client.get("client_id"), str)
                and client["client_id"].strip()
                and isinstance(client.get("client_secret"), str)
                and client["client_secret"].strip()
            ):
                return credentials

        raise HTTPException(
            status_code=400,
            detail=(
                "Google OAuth credentials must contain an installed or web "
                "object with client_id and client_secret."
            ),
        )

    if (
        isinstance(payload.client_id, str)
        and payload.client_id.strip()
        and isinstance(payload.client_secret, str)
        and payload.client_secret.strip()
    ):
        return {
            "installed": {
                "client_id": payload.client_id.strip(),
                "client_secret": payload.client_secret.strip(),
            }
        }

    raise HTTPException(
        status_code=400,
        detail="Provide raw_json or both client_id and client_secret.",
    )


@app.post("/connections/credentials")
def upload_google_credentials(
    payload: GoogleCredentialsUploadRequest,
    principal: PrincipalContext = Depends(_resolve_authenticated_principal),
) -> dict:
    """Atomically configure the install-wide Google OAuth client secret.

    Open to any authenticated user (User directive, 2026-09-12) - not
    ADMIN-only. This still writes one shared, install-wide
    credentials.json every user's Google connection depends on, so any
    signed-in user can now replace it for everyone on this install."""
    credentials = _google_client_credentials(payload)
    credentials_root = _repo_root_for_credentials()
    os.makedirs(credentials_root, exist_ok=True)
    destination = os.path.join(credentials_root, "credentials.json")
    temporary_path: Optional[str] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=credentials_root,
            prefix=".credentials-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(credentials, temporary_file, indent=2)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
    except OSError as exc:
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Google client credentials could not be saved: {exc}",
        ) from exc

    return {
        "saved": True,
        "detail": "Google client credentials configured successfully.",
        "connections": list_connection_status(),
    }


@app.get("/memory/settings")
def get_memory_settings(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    return _resolve_context(user_id).memory_settings_store.load().__dict__


@app.put("/memory/settings")
def update_memory_settings(
    payload: MemorySettingsPayload,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    try:
        return _resolve_context(user_id).memory_settings_store.update(
            payload.supplied()
        ).__dict__
    except MemorySettingsValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


_LOOPBACK_HOSTS = {
    "127.0.0.1", "::1", "localhost",
    # FastAPI/Starlette's own TestClient reports this literal fixed
    # pseudo-hostname for every request.client.host regardless of real
    # network origin - recognized here only so existing/new tests
    # against this endpoint can exercise the loopback-allowed path
    # without a real socket; a real deployment never sees this string
    # as an actual connecting client.
    "testclient",
}

# 2026-09-12 (User directive): a single, module-level guard against two
# concurrent OAuth consent flows racing each other (both would try to
# bind their own local callback port and write token.json). Not
# per-user - like the connection itself, this is one shared,
# install-wide flow.
_google_auth_flow_lock = threading.Lock()
_google_auth_flow_state: dict = {"running": False, "last_error": None}


def _run_google_auth_flow_in_background(user_id: Optional[str] = None) -> None:
    from uri_core.services.gmail_service import GmailService

    try:
        result = GmailService(user_id=user_id).connect()
        if not result.get("success", True):
            _google_auth_flow_state["last_error"] = result.get("reason")
    except Exception as exc:  # noqa: BLE001 - reported via status, never raised into the request
        _google_auth_flow_state["last_error"] = str(exc)
    finally:
        _google_auth_flow_state["running"] = False


@app.post("/connections/{connection_id}/authorize")
def authorize_connection(
    connection_id: str,
    request: Request,
    principal: PrincipalContext = Depends(_resolve_authenticated_principal),
) -> dict:
    """M16 Priority 4, revised for M32 (A1-3): actually
    start Google sign-in for a service on behalf of THIS user.

    Google's installed-app consent flow opens a browser and a local
    callback server ON THE URI SERVER HOST (see GmailService.connect /
    InstalledAppFlow.run_local_server) - genuinely correct for this
    install (a loopback-only desktop app talking to its own local
    backend), so launching it here is launching it on the same machine
    the User is sitting at, not on some other person's server.

    Safety, preserved rather than removed: M22.3's original concern was
    a REMOTE caller triggering an interactive prompt on a shared host.
    That risk is addressed here, not discarded - this endpoint refuses
    to start the flow for any request whose connecting client is not
    the loopback address itself (request.client.host not in
    _LOOPBACK_HOSTS), regardless of who is authenticated. Combined with
    this server's own loopback-only default bind (scripts/
    run_uri_server.py), a non-loopback caller cannot reach this
    behavior at all under the sanctioned launch path.

    Runs GmailService(user_id=principal.user_id).connect() (which blocks
    on the interactive consent) in a background thread rather than the
    request handler itself, so the HTTP response returns immediately
    with "started" rather than hanging for however long the User takes to
    complete consent in their browser. Poll GET /connections afterward for
    the real, resulting status once consent completes.

    Per-user mailbox isolation (M32 A1-3): writes token.json strictly
    to THIS user's scoped directory.
    """

    if connection_id not in {"gmail", "drive"}:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown connection: {connection_id}",
        )

    client_host = request.client.host if request.client else None
    if client_host not in _LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=403,
            detail=(
                "Google sign-in can only be started from the URI "
                "server's own machine (loopback), never over the "
                "network."
            ),
        )

    credentials_present = os.path.exists(
        os.path.join(_repo_root_for_credentials(), "credentials.json")
    )

    if not credentials_present:
        return {
            "started": False,
            "detail": (
                "No Google client secret (credentials.json) is "
                "configured on the URI server host yet, so sign-in "
                "cannot be started."
            ),
            "connections": _connection_status_for_user(principal.user_id),
        }

    with _google_auth_flow_lock:
        if _google_auth_flow_state["running"]:
            return {
                "started": False,
                "detail": (
                    "A Google sign-in is already in progress - "
                    "complete or close that browser window first."
                ),
                "connections": _connection_status_for_user(principal.user_id),
            }
        _google_auth_flow_state["running"] = True
        _google_auth_flow_state["last_error"] = None
        threading.Thread(
            target=_run_google_auth_flow_in_background,
            args=(principal.user_id,),
            name="google-oauth-consent",
            daemon=True,
        ).start()

    return {
        "started": True,
        "detail": (
            "Opening your browser for Google sign-in - complete the "
            "consent there, then refresh this screen."
        ),
        "connections": _connection_status_for_user(principal.user_id),
    }


@app.delete("/connections/{connection_id}")
def disconnect_connection(
    connection_id: str,
    principal: PrincipalContext = Depends(_resolve_authenticated_principal),
) -> dict:
    """M16 Priority 2 / M32 A1-3: a REAL per-user disconnect.

    Revoking a Google connection means removing the calling user's stored
    OAuth token in their own user_scoped_path.
    Both Gmail and Drive share one token file (they are one Google
    authorization with two scopes), so this affects both for THIS user
    without modifying any other user's authorization.
    """

    if connection_id not in {"gmail", "drive"}:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown connection: {connection_id}",
        )

    from uri_core.core.google_auth_common import resolve_google_token_path

    token_path = resolve_google_token_path(principal.user_id)

    if not os.path.exists(token_path):
        return {
            "disconnected": False,
            "detail": "That service was not connected.",
            "connections": _connection_status_for_user(principal.user_id),
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
            "Google authorization removed for this account. Gmail and Drive share one "
            "token, so both now require sign-in again."
        ),
        "connections": _connection_status_for_user(principal.user_id),
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


class ActiveBrainUpdateRequest(BaseModel):
    provider_id: str
    model: Optional[str] = None


def _active_brain_for_user(user_id: Optional[str]) -> dict:
    """Resolve the selected reasoning backend with a safe catalogue default."""
    from uri_core.core.provider_registry import CATALOGUE_BY_ID, ProviderConfigStore

    provider_id = "ollama"
    model = "qwen3:14b"
    role_config = load_model_roles().get(ROLE_REASONING, {})
    configured_provider = role_config.get("provider_id", role_config.get("provider"))
    if configured_provider in CATALOGUE_BY_ID:
        provider_id = configured_provider
    if isinstance(role_config.get("model"), str) and role_config["model"]:
        model = role_config["model"]

    is_configured = False
    if user_id is not None:
        try:
            active_brain = ProviderConfigStore(user_id).get_active_brain()
        except ValueError:
            active_brain = None
        if active_brain is not None and active_brain["provider_id"] in CATALOGUE_BY_ID:
            provider_id = active_brain["provider_id"]
            model = active_brain["model"]
            is_configured = True

    descriptor = CATALOGUE_BY_ID[provider_id]
    display_name = next(
        (
            model_descriptor.display_name
            for model_descriptor in descriptor.models
            if model_descriptor.model_id == model
        ),
        model,
    )
    return {
        "provider_id": provider_id,
        "model": model,
        "display_name": display_name,
        "is_configured": is_configured,
    }


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
    from uri_core.core.model_providers import AnthropicProvider, OpenAICompatibleProvider
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

    active_brain = _active_brain_for_user(user_id)
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
                    timeout_seconds=2.0,
                )
                # No api_key for the health-check probe - just connectivity
                probe = OpenAICompatibleProvider(config=cfg)
                available = probe.describe().available
            except Exception:  # noqa: BLE001
                available = False
        elif descriptor.adapter == "anthropic":
            try:
                user_cfg = config_store.get_provider_config(pid) if config_store else {}
                cfg = ModelProviderConfig(
                    base_url=user_cfg.get("base_url", descriptor.base_url),
                    model=user_cfg.get("model", (descriptor.models[0].model_id if descriptor.models else "")),
                    timeout_seconds=2.0,
                )
                api_key = key_store.get_key_for_use(pid) if configured and key_store else None
                available = AnthropicProvider(config=cfg, api_key=api_key).describe().available
            except Exception:  # noqa: BLE001
                available = False
        installed_models: Optional[list] = None
        if descriptor.adapter == "ollama":
            from uri_core.core.model_providers import OllamaProvider
            try:
                env_config = ModelProviderConfig.from_env()
                probe_ollama = OllamaProvider(
                    config=ModelProviderConfig(
                        base_url=env_config.base_url,
                        model=env_config.model,
                        timeout_seconds=2.0,
                        context_tokens=env_config.context_tokens,
                    )
                )
                available = probe_ollama.describe().available
                # Real installed-model list (docs/plans/URI_APPROVED_UI_*
                # startup-flow repair): describe().available only proves the
                # daemon answers - it never proves the specific configured/
                # default model was actually pulled. Surfacing the real
                # list lets a client pick a model Ollama can truly serve
                # instead of blindly trusting the catalogue's default.
                installed_models = probe_ollama.list_installed_models() if available else []
            except Exception:  # noqa: BLE001
                available = False
                installed_models = []

        # Local providers have no credential to store. A successful endpoint
        # probe is the truthful configuration signal: URI has an endpoint and
        # can reach it. It is intentionally still separate from model discovery.
        if "local" in descriptor.auth_transports:
            configured = available

        user_cfg = config_store.get_provider_config(pid) if config_store else {}
        selected_model = user_cfg.get("model")
        if not selected_model and pid == active_brain["provider_id"]:
            selected_model = active_brain["model"]
        if not selected_model and descriptor.models:
            selected_model = descriptor.models[0].model_id

        verified_models = (
            list(installed_models or []) if pid == "ollama"
            else _verified_models_for(user_id, pid)
        )
        # Catalogue entries document known choices; they do not establish
        # usability. Add live-discovered models to this one inventory so the
        # active brain, routing dialog, and chat selector agree.
        catalogue_models = {model.model_id: model for model in descriptor.models}
        inventory_ids = list(catalogue_models)
        for model_id in verified_models:
            if model_id not in catalogue_models:
                inventory_ids.append(model_id)
        result.append({
            "provider_id": pid,
            "display_name": descriptor.display_name,
            "adapter": descriptor.adapter,
            "auth_transports": descriptor.auth_transports,
            "base_url": descriptor.base_url,
            "configured": configured,
            "last_four": last_four,
            "available": available,
            "installed_models": installed_models,
            "models": [
                {
                    "model_id": model_id,
                    "display_name": catalogue_models[model_id].display_name
                        if model_id in catalogue_models else model_id,
                    "context_tokens": catalogue_models[model_id].context_tokens.value
                        if model_id in catalogue_models else None,
                    "verified": model_id in verified_models,
                }
                for model_id in inventory_ids
            ],
            "active_brain": (
                active_brain["is_configured"] and pid == active_brain["provider_id"]
                and active_brain["model"] in verified_models
            ),
            "active_model": selected_model,
        })

    return {"providers": result, "active_brain": active_brain}


@app.post("/providers/{provider_id}/verify")
def verify_provider(provider_id: str, user_id: Optional[str] = Depends(_resolve_authenticated_user_id)) -> dict:
    """Run an explicit, small direct-provider check and cache usable models."""
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    from uri_core.core.provider_registry import CATALOGUE_BY_ID, ProviderConfigStore
    from uri_core.core.provider_keys import ProviderKeyStore
    from uri_core.core.model_providers import AnthropicProvider, OpenAICompatibleProvider, OllamaProvider
    from uri_core.core.model_providers.base import ModelProviderConfig
    descriptor = CATALOGUE_BY_ID.get(provider_id)
    if descriptor is None:
        raise HTTPException(status_code=400, detail=f"Unknown provider_id: {provider_id!r}.")
    cached = _verified_models_for(user_id, provider_id)
    if cached:
        return {"provider_id": provider_id, "verified": True, "verified_models": cached, "error": None, "cached": True}
    try:
        if provider_id == "ollama":
            models = OllamaProvider(ModelProviderConfig.from_env()).list_installed_models()
        elif not ProviderKeyStore(user_id).has_key(provider_id):
            return {"provider_id": provider_id, "verified": False, "verified_models": [], "error": "An API key is required."}
        else:
            stored = ProviderConfigStore(user_id).get_provider_config(provider_id)
            key = ProviderKeyStore(user_id).get_key_for_use(provider_id)
            models = []
            for item in descriptor.models:
                provider_cls = AnthropicProvider if provider_id == "anthropic" else OpenAICompatibleProvider
                probe = provider_cls(ModelProviderConfig(base_url=stored.get("base_url", descriptor.base_url), model=item.model_id, timeout_seconds=5.0), api_key=key)
                try:
                    probe.complete(system="Reply with OK.", user="OK", max_tokens=1)
                    models.append(item.model_id)
                except Exception:
                    continue
        _verified_models_cache[(user_id, provider_id)] = (time.monotonic() + _VERIFIED_MODELS_TTL_SECONDS, models)
        return {"provider_id": provider_id, "verified": bool(models), "verified_models": models, "error": None if models else "No configured model could be verified.", "cached": False}
    except Exception as exc:
        return {"provider_id": provider_id, "verified": False, "verified_models": [], "error": str(exc)}


@app.get("/providers/fallback-routing")
def get_fallback_routing(user_id: Optional[str] = Depends(_resolve_authenticated_user_id)) -> dict:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    from uri_core.core.fallback_routing_store import FallbackRoutingStore
    return FallbackRoutingStore(user_id).load()


@app.put("/providers/fallback-routing")
def update_fallback_routing(payload: FallbackRoutingRequest, user_id: Optional[str] = Depends(_resolve_authenticated_user_id)) -> dict:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    config = payload.model_dump()
    for slot, value in config.items():
        if value is None or (slot == "fallback_1" and value == "auto"):
            continue
        if not isinstance(value, dict) or not isinstance(value.get("provider_id"), str) or not isinstance(value.get("model"), str):
            raise HTTPException(status_code=400, detail=f"Invalid {slot} selection.")
        if value["model"] not in _selectable_models_for(user_id, value["provider_id"]):
            raise HTTPException(status_code=400, detail=f"{slot} must use a discovered and verified model.")
    concrete_slots = [
        (v["provider_id"], v["model"])
        for slot, v in config.items()
        if isinstance(v, dict) and "provider_id" in v and "model" in v
    ]
    if len(concrete_slots) != len(set(concrete_slots)):
        raise HTTPException(status_code=400, detail="Duplicate models selected across fallback routing slots.")
    from uri_core.core.fallback_routing_store import FallbackRoutingStore
    FallbackRoutingStore(user_id).save(config)
    return config


@app.get("/providers/active-brain")
def get_active_brain(
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    return _active_brain_for_user(user_id)


@app.put("/providers/active-brain")
def update_active_brain(
    payload: ActiveBrainUpdateRequest,
    user_id: Optional[str] = Depends(_resolve_authenticated_user_id),
) -> dict:
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    from uri_core.core.provider_registry import CATALOGUE_BY_ID, ProviderConfigStore

    descriptor = CATALOGUE_BY_ID.get(payload.provider_id)
    if descriptor is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider_id: {payload.provider_id!r}.",
        )

    config_store = ProviderConfigStore(user_id)

    if descriptor.models:
        # A provider with a real catalogue can be meaningfully checked
        # against discovered/verified inventory (rule 1: only discovered
        # AND verified-usable models are ever selectable as Active Brain).
        if payload.model is None or payload.model not in _selectable_models_for(
            user_id, payload.provider_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Active Brain must use a discovered and verified model.",
            )
        chosen_model = payload.model
    else:
        # 2026-09-12 (User directive): a provider with no fixed catalogue
        # models (e.g. LM Studio, or any custom OpenAI-compatible endpoint -
        # "dynamic, depends on what the user has loaded", see
        # provider_registry.py's own catalogue comment) has nothing for
        # rule 1's verified-inventory check to compare against, and must
        # never silently fall back to a literal Ollama model name that has
        # nothing to do with what this provider is actually serving.
        # Prefer, in order: the model the client explicitly asked for,
        # this user's own already-configured model override for this
        # provider (PUT /providers/config), then a hardcoded literal only
        # when this provider genuinely has no other source of a model
        # name at all.
        chosen_model = (
            payload.model
            or config_store.get_provider_config(payload.provider_id).get("model")
            or "qwen3:14b"
        )

    config_store.set_active_brain(payload.provider_id, chosen_model)
    _user_contexts.pop(user_id, None)
    return {
        "active_brain": {
            "provider_id": payload.provider_id,
            "model": chosen_model,
        }
    }


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

