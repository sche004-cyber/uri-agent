"""Milestone 10A: one bounded, model-facing context representation.

Architectural framing this module exists to serve: the user is
purpose/authority, the Brain (the reasoning model) is broad cognition,
and URI is the companion/body/reality layer standing between them. This
module's only job is assembling what URI already knows - about itself,
the user, the current task, and its own capabilities - into one small,
labeled, bounded object the Brain can read. It is context
infrastructure, not a new reasoning subsystem: it decides nothing,
selects nothing, and scores nothing.

Mirrors personalization_context.py's exact discipline, one level up:
this module is pure and read-only - it never touches storage itself,
never writes anything, and is never imported by capability_planner.py,
dispatcher.py, approval_gate.py, or approval_store.py. Every input is
already-loaded data the caller assembled from an existing authoritative
source; this module only shapes those pieces into one consistent
envelope. See test_capability_authority_boundary.py for the structural
proof of that import boundary.

Deliberately NOT here, by design:
    - Any storage/file access of its own - every section is supplied
      pre-built by the caller (orchestrator.py), reusing the exact
      functions/state it already maintains for other purposes
      (ModelReasoningGateway.load_policy(),
      personalization_context.build_personalization_context(),
      UriOrchestrator._build_model_session_context(),
      evidence_context.get_verified_evidence()/evidence_summary(),
      CapabilityRegistry.list_capabilities()) - see this module's
      docstring section by section below for which.
    - Keyword-based relevance filtering. evidence_context.py's
      get_relevant_evidence() applies a fixed, scenario-specific
      keyword taxonomy (institution/insurance terms from an early
      demo) to decide what evidence "counts" - exactly the kind of
      hard-coded task taxonomy ADR-018 says URI must move away from.
      This module instead passes through every VERIFIED fact via
      get_verified_evidence()/evidence_summary() and lets the Brain
      itself judge relevance from the full, honestly-labeled set.
    - Capability scoring or selection. capability_planner.py's
      per-tool if/elif keyword scoring remains the deterministic
      selection mechanism and is untouched by this milestone; this
      module only reports the capability catalogue (including its
      constraint/approval/risk fields) so the Brain can reason about
      capability relevance itself, exactly as CapabilityDescriptor's
      own docstring already intends for reporting-only consumers.
"""

from typing import Any, Dict, List, Optional

from uri_core.core.capability_registry import CapabilityDescriptor


def _serialize_capability(descriptor: CapabilityDescriptor) -> Optional[Dict[str, Any]]:
    """One CapabilityDescriptor -> one plain dict, keeping every field
    the Brain needs to reason about whether/how a capability applies:
    identity (id/description), current usability (status/availability/
    gap_reason), and the constraints around using it (permissions/
    approval_requirement/risk/limitations). Unknown-safe: a value that
    is not actually a CapabilityDescriptor is dropped rather than
    guessed at, matching capability_registry.py's own discipline."""

    if not isinstance(descriptor, CapabilityDescriptor):
        return None

    return {
        "id": descriptor.id,
        "description": descriptor.description,
        "status": descriptor.status,
        "availability": descriptor.availability,
        "permissions": list(descriptor.permissions),
        "approval_requirement": descriptor.approval_requirement,
        "risk": descriptor.risk,
        "limitations": descriptor.limitations,
        "gap_reason": descriptor.gap_reason,
        # BODY: the capability's own interface/schema (when curated),
        # e.g. {"kind": "system_diagnostics", "summary_fields": [...]}
        # - lets the Brain reason about a capability's shape/purpose,
        # not only whether it exists. None when the registry entry
        # never curated one (the common case today).
        "interface": descriptor.interface,
    }


def build_query_context(
    policy_text: Optional[str] = None,
    soul_text: Optional[str] = None,
    personalization: Optional[Dict[str, Any]] = None,
    session_context: Optional[Dict[str, Any]] = None,
    verified_facts: Optional[Dict[str, Any]] = None,
    capabilities: Optional[List[CapabilityDescriptor]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    experience: Optional[List[Dict[str, Any]]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    conversation: Optional[List[Dict[str, Any]]] = None,
    graph_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assembles one bounded, labeled dict for a single Brain query -
    never prose, never free-form instruction text, so a query prompt
    can only ever receive this as clearly-labeled data.

    Every argument is already-built by the caller from an existing
    authoritative source - this function performs no storage access,
    no filtering beyond dropping malformed entries, and no relevance
    judgment of its own:

    - policy_text: URI's operating policy - the behavioural rules and
      guardrails URI must follow, verbatim, from
      ModelReasoningGateway.load_policy().
    - soul_text: URI's identity/character, verbatim, from
      ModelReasoningGateway.load_soul() (soul.md) - deliberately a
      separate section from policy_text: soul.md is who URI is, the
      operating policy is what URI must/must not do. Neither one may
      be inferred from the other; see soul.md's own module note on
      this split.
    - personalization: the already-bounded, already-consent-filtered
      dict from personalization_context.build_personalization_context()
      - passed through unchanged; this module never re-derives or
      re-filters memory eligibility, only relays what that function
      already decided.
    - session_context: the current task/session snapshot, e.g. from
      UriOrchestrator._build_model_session_context() (task,
      current_facts, active_workflow, clarification state).
    - verified_facts: VERIFIED-status evidence only, e.g. from
      evidence_context.evidence_summary(
      evidence_context.get_verified_evidence(session)) - never
      evidence_context.get_relevant_evidence(), whose keyword taxonomy
      is scenario-specific (see module docstring).
    - capabilities: the capability catalogue as a list of
      CapabilityDescriptor (e.g. from
      CapabilityRegistry.list_capabilities()), including entries that
      are not currently executable - the Brain is given the same
      status/availability/gap_reason fields URI's own gap-reporting
      path uses, not a pre-filtered "available only" subset, so it can
      reason about what exists versus what it can rely on right now.

    - diagnostics: the current turn's real, already-known runtime
      state - e.g. from diagnostics_context.build_diagnostics_context()
      - the last operation attempted, its component, its exact status/
      error, and any known service-availability gaps. Never fabricated
      here or by the caller: every field must trace back to a real
      execution/audit record. Degrades to an empty dict when nothing is
      known yet (a fresh turn with no prior operation).
    - experience: a short list of past-interaction summaries the Brain
      itself already judged worth retaining, e.g. from
      experience_store.summarize_for_query_context(
      ExperienceStore().recent()) - reusable experience, distinct from
      personalization (facts ABOUT the user) and session_context
      (THIS turn's state). Never a raw conversation dump: only already-
      Brain-approved retention candidates ever reach this list (see
      orchestrator.py's _run_acceptance_retention_step). Degrades to an
      empty list when none exist yet.
    - attachments: bounded references to files the user actually
      attached to this conversation - {file_id, filename, media_type,
      size_bytes} only, from core/file_store.StoredFile.to_reference().
      Never file CONTENT: the Brain sees only that an attachment
      exists and what it is, and must select the registered
      read_attached_file capability for URI to actually extract and
      return its text. Degrades to an empty list when nothing is
      attached.
    - conversation (M21): a small, token-budgeted window of the most
      recent real turns of THIS session's own verbatim dialogue - e.g.
      from orchestrator.py's _build_conversation_context, which reads
      conversation_history.ConversationHistoryStore.get_session() and
      trims it with context_budget.fit_within_budget(). Each entry is
      {"user": ..., "uri": ..., "status": ...} - plain recorded text,
      never a judgment or a summary. This is historical context for the
      Brain to read, exactly like experience below - it is never
      written to MemoryStore/ExperienceStore/SkillMemory by anything in
      this module or its caller, and carries no more authority than any
      other section here. Degrades to an empty list when no
      conversation_history is available or session_id is unknown.
    - graph_context (M23): the bounded structured graph envelope from
      graph_context.build_graph_context() - entities/relationships/
      paths/provenance/confidence_status the caller already resolved
      via graph_engine.py's bounded read primitives. Context/evidence
      only, exactly like verified_facts/experience/conversation above -
      never an authorization input (see graph_engine.py/graph_store.py
      module docstrings and test_graph_authority_boundary.py). Degrades
      to the all-empty shape when omitted.

    Any argument may be omitted (None) - the corresponding section
    degrades to an empty value rather than being guessed at, matching
    this codebase's existing "unknown-safe" discipline.
    """

    capability_list = capabilities or []

    return {
        "identity": policy_text or "",
        "soul": soul_text or "",
        "personalization": personalization or {},
        "session": session_context or {},
        "verified_facts": verified_facts or {},
        "capabilities": [
            item
            for item in (
                _serialize_capability(descriptor)
                for descriptor in capability_list
            )
            if item is not None
        ],
        "diagnostics": diagnostics or {},
        "experience": experience or [],
        "attachments": attachments or [],
        "conversation": conversation or [],
        "graph_context": graph_context or {
            "entities": [],
            "relationships": [],
            "paths": [],
            "provenance": [],
            "confidence_status": [],
        },
    }
