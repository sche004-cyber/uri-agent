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
    }


def build_query_context(
    policy_text: Optional[str] = None,
    personalization: Optional[Dict[str, Any]] = None,
    session_context: Optional[Dict[str, Any]] = None,
    verified_facts: Optional[Dict[str, Any]] = None,
    capabilities: Optional[List[CapabilityDescriptor]] = None,
) -> Dict[str, Any]:
    """Assembles one bounded, labeled dict for a single Brain query -
    never prose, never free-form instruction text, so a query prompt
    can only ever receive this as clearly-labeled data.

    Every argument is already-built by the caller from an existing
    authoritative source - this function performs no storage access,
    no filtering beyond dropping malformed entries, and no relevance
    judgment of its own:

    - policy_text: URI's identity/character/principles, verbatim, from
      ModelReasoningGateway.load_policy() (the sole source of URI's
      identity - see model_reasoning_adapter.py's own note on this).
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

    Any argument may be omitted (None) - the corresponding section
    degrades to an empty value rather than being guessed at, matching
    this codebase's existing "unknown-safe" discipline.
    """

    capability_list = capabilities or []

    return {
        "identity": policy_text or "",
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
    }
