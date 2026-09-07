import json
import os

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone

from uri_core.core.prompt_builder import PromptBuilder
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.approval_gate import ApprovalGate
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.provider_semantic_interpreter import (
    ProviderSemanticInterpreter
)
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.capability_planner import CapabilityPlanner
from uri_core.core.conversational_classifier import (
    NO_CAPABILITY_REQUIRED_MESSAGE,
    is_conversational_no_capability_required
)
from uri_core.core.workflow_planner import WorkflowPlanner
from uri_core.core.workflow_capability_router import (
    WorkflowCapabilityRouter
)
from uri_core.core.workflow_executor import WorkflowExecutor
from uri_core.core.state import SessionManager
from uri_core.core.facts import Fact
from uri_core.core.fact_manager import update_fact
from uri_core.core.model_reasoning_gateway import (
    ModelReasoningGateway
)
from uri_core.core.response_drafting import (
    DraftRequest,
    ResponseDraftingError,
    condense_known_gaps,
    draft_response
)
from uri_core.core.response_validation import (
    ResponseValidationError,
    validate_drafted_response
)
from uri_core.core.evidence_context import (
    evidence_summary,
    get_verified_evidence
)
from uri_core.core.query_context import build_query_context
from uri_core.core.diagnostics_context import build_diagnostics_context
from uri_core.core.experience_store import (
    ExperienceStore,
    summarize_for_query_context as summarize_experience_for_query_context
)
from uri_core.core.file_store import FileStore
from uri_core.core.conversation_history import ConversationHistoryStore
from uri_core.core.skill_evaluator import SkillEvaluator
from uri_core.core.context_budget import ContextBudget
from uri_core.core.audit_trail import AuditTrail
from uri_core.core.workflow_recovery import (
    WorkflowRecoveryValidator
)
from uri_core.services.evidence_processor import (
    EvidenceProcessor
)


class UriOrchestrator:

    def __init__(
        self,
        model_reasoning_gateway=None,
        enable_model_reasoning_shadow=True,
        skill_evaluator=None,
        context_budget=None,
        audit_trail=None,
        enable_skill_router_shadow=True,
        skill_registry_path="uri_workspace/skill_registry.json",
        semantic_interpreter=None,
        approval_gate=None,
        enable_response_narrative=False,
        response_drafting_provider=None,
        session_manager=None,
        max_brain_iterations=3,
        experience_store=None,
        file_store=None,
        skill_memory=None,
        conversation_history=None
    ):

        # Milestone 11 Part 2 (Brain re-evaluation loop): a safety cap
        # on how many execute-then-evaluate rounds a single turn may
        # run, never a limitation on what the Brain may propose - see
        # _continue_brain_evaluation_loop. Overridable per instance
        # (mainly for tests) so it can be set low to deterministically
        # exercise the cap without an unbounded fixture.
        self.max_brain_iterations = max_brain_iterations

        self.prompt_builder = PromptBuilder()

        self.dispatcher = ToolDispatcher()

        if semantic_interpreter is not None:

            self.semantic_interpreter = (
                semantic_interpreter
            )

        else:

            self.semantic_interpreter = (
                ProviderSemanticInterpreter()
            )

        # M18: skill_memory is injectable so the server can give each
        # logged-in user_id their OWN skill store (see _build_user_context)
        # rather than every user sharing one global uri_workspace/
        # skill_memory.json. A None default preserves the legacy ambient
        # single-store behaviour for unauthenticated/legacy callers.
        self.skill_memory = skill_memory if skill_memory is not None else SkillMemory()

        self.capability_planner = CapabilityPlanner()

        self.workflow_planner = WorkflowPlanner()

        # Prototype 1 (multi-user identity): accepting an injected
        # SessionManager, rather than always constructing the default
        # ambient uri_workspace/sessions one, is what lets server.py
        # give each logged-in user_id their own conversation-state
        # directory (see portable_paths.user_scoped_path) without this
        # class knowing anything about users/auth - it stays exactly
        # as unaware of identity as approval_gate already is (see this
        # constructor's approval_gate parameter above). Every existing
        # caller/test that constructs UriOrchestrator() with no args
        # keeps the previous SessionManager() default behaviour.
        self.session_manager = (
            session_manager
            if session_manager is not None
            else SessionManager()
        )

        self.evidence_processor = None

        self.workflow_executor = None

        self.enable_model_reasoning_shadow = (
            enable_model_reasoning_shadow
        )

        if model_reasoning_gateway is not None:

            self.model_reasoning_gateway = (
                model_reasoning_gateway
            )

        else:

            self.model_reasoning_gateway = (
                ModelReasoningGateway()
            )

        # ------------------------------------------------------
        # Skill Router V1 shadow wiring.
        #
        # Observational only - see _run_skill_router_shadow.
        # It never influences `plan` or `execution`.
        # ------------------------------------------------------

        self.enable_skill_router_shadow = (
            enable_skill_router_shadow
        )

        self.audit_trail = (
            audit_trail
            if audit_trail is not None
            else AuditTrail()
        )

        self._skill_registry_items = (
            self._load_skill_registry_items(
                skill_registry_path
            )
        )

        if skill_evaluator is not None:

            self.skill_evaluator = skill_evaluator

        else:

            self.skill_evaluator = SkillEvaluator(
                registry_items=self._skill_registry_items
            )

        if context_budget is not None:

            self.context_budget = context_budget

        else:

            self.context_budget = ContextBudget(
                registry_items=self._skill_registry_items
            )

        # ------------------------------------------------------
        # Real approval gate (Milestone 7).
        #
        # The ONE execution boundary self.dispatcher is ever called
        # through - see process_user_input's capability_selected
        # branch and _create_workflow_executor below, both of which
        # now hand this gate (not self.dispatcher directly) to
        # anything that needs to execute a registered capability.
        # capability_planner.py/model reasoning may only ever propose
        # a tool_name; this gate is the sole place that turns a
        # CapabilityRegistry approval_requirement into a real,
        # enforced block. Constructed last, after self.dispatcher and
        # self.audit_trail already exist, so it can reuse both without
        # reordering anything above.
        # ------------------------------------------------------

        self.capability_registry = CapabilityRegistry()

        if approval_gate is not None:

            self.approval_gate = approval_gate

        else:

            self.approval_gate = ApprovalGate(
                dispatcher=self.dispatcher,
                capability_registry=self.capability_registry,
                audit_trail=self.audit_trail,
            )

        # ------------------------------------------------------
        # Live conversational response drafting (Milestone 8A).
        #
        # Defaults OFF: unlike enable_model_reasoning_shadow/
        # enable_skill_router_shadow (both default True, established
        # long before this milestone), this stays an explicit opt-in
        # so every existing orchestrator test/caller keeps its exact
        # prior behaviour with no new network dependency and no new
        # audit events, unless a caller (see server.py) deliberately
        # turns it on. When on, drafting/validation only ever runs
        # after process_user_input's capability_selected/
        # planning_required branches have already fully decided the
        # outcome - see _draft_narrative_safely - and any failure
        # (unreachable model, empty draft, failed validation) falls
        # back to the existing deterministic response untouched.
        # ------------------------------------------------------

        self.enable_response_narrative = enable_response_narrative
        self.response_drafting_provider = response_drafting_provider

        # Item 7 (structured experience/history records): ambient for
        # now, mirroring self.skill_memory's own ambient-store
        # precedent above - see experience_store.py's module docstring
        # for why, and for the deliberate separation from user
        # profile/personal memory/temporary session state.
        self.experience_store = (
            experience_store
            if experience_store is not None
            else ExperienceStore()
        )

        # M16 Priority 1 (file attachments): read-only here. The
        # orchestrator only ever asks which files the user attached to
        # a session, so the Brain can see that they exist (see
        # _build_query_context's "attachments" section); it never reads
        # their content. Content extraction happens only when the Brain
        # selects the registered read_attached_file capability, through
        # the same ApprovalGate/ToolDispatcher boundary as any other
        # capability. Ambient by default, exactly like
        # self.skill_memory/self.experience_store above.
        self.file_store = (
            file_store if file_store is not None else FileStore()
        )

        # M18: durable per-user/per-session conversation transcript.
        # Injectable and user-scoped by the server (see
        # _build_user_context); a None default keeps the legacy ambient
        # behaviour. Recording a turn here never affects the turn's
        # outcome - a write failure is swallowed (see
        # _record_conversation_turn_safely).
        self.conversation_history = (
            conversation_history
            if conversation_history is not None
            else ConversationHistoryStore()
        )

    # ==========================================================
    # SKILL REGISTRY LOADING
    # ==========================================================

    def _load_skill_registry_items(
        self,
        registry_path
    ):
        """
        Load the Skill Router V1 registry (uri_workspace/skill_registry.json).

        Loaded once at construction, not per-request - the file is
        ~300KB and its contents don't change during a session.

        Missing or malformed registries degrade to an empty list so
        the shadow path reports "no suitable capability" rather than
        raising and disturbing the live request.
        """

        normalized_path = os.path.normpath(
            registry_path
        )

        try:

            with open(
                normalized_path,
                "r",
                encoding="utf-8-sig"
            ) as file:

                registry = json.load(file)

        except (
            FileNotFoundError,
            json.JSONDecodeError
        ):
            return []

        items = registry.get("items", [])

        if not isinstance(items, list):
            return []

        return items

    # ==========================================================
    # MODEL REASONING SHADOW
    # ==========================================================

    def _serialize_model_context(
        self,
        value
    ):

        if is_dataclass(value):

            return asdict(value)

        if isinstance(value, dict):

            result = {}

            for key, item in value.items():

                result[str(key)] = (
                    self._serialize_model_context(
                        item
                    )
                )

            return result

        if isinstance(value, list):

            return [
                self._serialize_model_context(item)
                for item in value
            ]

        if isinstance(value, tuple):

            return [
                self._serialize_model_context(item)
                for item in value
            ]

        if isinstance(value, (str, int, float, bool)):

            return value

        if value is None:

            return None

        return str(value)

    def _build_model_session_context(
        self,
        session
    ):

        return {
            "session_id":
                getattr(
                    session,
                    "session_id",
                    None
                ),

            "task":
                getattr(
                    session,
                    "task",
                    None
                ),

            "current_facts":
                self._serialize_model_context(
                    getattr(
                        session,
                        "current_facts",
                        {}
                    )
                ),

            "evidence_facts":
                self._serialize_model_context(
                    getattr(
                        session,
                        "evidence_facts",
                        {}
                    )
                ),

            "historical_facts":
                self._serialize_model_context(
                    getattr(
                        session,
                        "historical_facts",
                        {}
                    )
                ),

            "last_question_field":
                getattr(
                    session,
                    "last_question_field",
                    None
                ),

            "clarification_complete":
                getattr(
                    session,
                    "clarification_complete",
                    False
                ),

            "active_workflow_status":
                getattr(
                    session,
                    "active_workflow_status",
                    None
                ),

            "active_workflow":
                self._serialize_model_context(
                    getattr(
                        session,
                        "active_workflow",
                        None
                    )
                )
        }

    def _build_model_evidence_context(
        self,
        session
    ):

        return {
            "active_evidence_query":
                getattr(
                    session,
                    "active_evidence_query",
                    None
                ),

            "active_evidence_context":
                getattr(
                    session,
                    "active_evidence_context",
                    None
                ),

            "evidence_facts":
                self._serialize_model_context(
                    getattr(
                        session,
                        "evidence_facts",
                        {}
                    )
                )
        }

    def _run_model_reasoning(
        self,
        user_text,
        session,
        session_id,
        personalization_context,
        attempt_history=None,
        learned_skill=None,
        pending_proposal=None,
        interaction_signal=None,
        retention_request=False
    ):
        """Runs ModelReasoningGateway.reason() and returns its result
        wrapped with a status of its own (see below). Despite the
        historical "shadow" name this method used to carry (Milestone
        6/7), its result is no longer observational-only as of
        Milestone 11 Phase 1: process_user_input's capability-selection
        step (see _model_proposed_capability) may use a validated,
        registered-capability proposal from here as the real plan,
        routed through the unmodified ApprovalGate/ToolDispatcher exactly
        like a CapabilityPlanner-selected tool always has been. This
        method itself still only ever reasons and proposes - it has no
        authority to execute anything, and returns a request/response
        pair that must always be gated. Wrapping never raises: a
        disabled or unreachable model must never break the live
        request whether or not its result is later used as the plan.

        "reasoning_disabled" - model reasoning is turned off entirely
        (self.enable_model_reasoning_shadow is False) - no request is
        even built.
        "reasoning_completed" - the gateway ran and returned a result
        (which may itself be "model_not_configured",
        "model_proposal_rejected", or "proposal_ready" - see
        ModelReasoningGateway.reason()).
        "reasoning_failed" - the gateway raised (unreachable model,
        malformed response, etc.).

        Milestone 11 Part 2 (Brain re-evaluation loop): attempt_history
        is optional and additive - omitted (None) for the first call in
        a turn, exactly as before. When _continue_brain_evaluation_loop
        calls this a second (or third) time within the same turn, it
        passes the compact record of what has already been tried and
        what actually happened, so the model can evaluate its own
        prior action's real result rather than being asked to propose
        blind each time. As of URI Correction Part 1, attempt_history
        may also carry forward the immediately preceding turn's
        history when the Brain was not satisfied then either (see
        process_user_input) - the same field, just a longer memory.

        URI Correction Part 1: learned_skill, when given, is folded
        into session_context as "learned_skill_reference" - advisory
        only. It is never used here to decide anything; it exists so
        the Brain can see "a similar request was handled this way
        before" and itself decide whether that is actually relevant to
        THIS request - see model_reasoning_adapter.py's prompt. Never
        used on the follow-up evaluation calls within
        _continue_brain_evaluation_loop, only on a turn's first call.

        Milestone 13 Part 1: pending_proposal, when given, asks the
        Brain to reconsider a plan it already formulated for this SAME
        request against this same fuller context, before anything has
        executed - see _run_pre_execution_sanity_check, the only
        caller that passes it. Omitted (None) everywhere else,
        including the turn's own first call and the post-execution
        _continue_brain_evaluation_loop, both unaffected.

        Milestone 13 Part 2: interaction_signal, when given, is a
        small generic label describing why this call follows a
        previous, not-yet-resolved turn (see process_user_input, the
        only caller that computes it, and REASONING_SYSTEM_PROMPT for
        what it means) - passed only on a turn's own first call.
        retention_request, when True, asks the Brain to summarize what
        is genuinely worth retaining after the user has accepted a
        result - see _run_acceptance_retention_step, the only caller
        that sets it. Both default to their ordinary, pre-M13
        behaviour (no signal, not a retention call) everywhere else.
        """

        if not self.enable_model_reasoning_shadow:

            return {
                "status":
                    "reasoning_disabled"
            }

        try:

            policy_text = (
                self.model_reasoning_gateway.load_policy()
            )

            # Milestone 10A/11: the same bounded, model-facing context
            # object already assembled for response drafting - reused
            # verbatim (see query_context.py), not rebuilt here.
            query_context = (
                self._build_query_context(
                    session_id=session_id,
                    policy_text=policy_text,
                    personalization_context=personalization_context,
                )
            )

            # Milestone 12: query_context's identity/session/
            # capabilities sections are, for THIS specific request,
            # verbatim duplicates of fields the reasoning request
            # already carries at its own top level - system_policy,
            # session_context, available_capabilities. Live testing
            # against real Ollama (qwen3:14b) showed this doubling the
            # policy text alone (~9.5k characters, repeated) reliably
            # made the model lose track of user_request entirely and
            # answer with an invented, boilerplate "clarification
            # needed" shape unrelated to the actual request - the real
            # root cause behind the schema-mismatch symptom this
            # milestone otherwise addresses via tolerant extraction.
            # Blanking out the duplicated sections here removes pure
            # noise the Brain already has through the other fields,
            # without losing any information - personalization,
            # verified_facts, and diagnostics in query_context are
            # genuinely new for this call, so those are kept. "soul" is
            # ALSO blanked here, deliberately never loaded/passed for
            # this call at all: live testing (reproduced against real
            # Ollama/qwen3:14b) showed unconditionally adding soul.md's
            # text to every structured-JSON reasoning/proposal call -
            # even once, not duplicated - measurably increased how
            # often the model returned an empty or unparseable response,
            # the same prompt-bulk sensitivity already documented above
            # for system_policy. This also matches
            # REASONING_SYSTEM_PROMPT's own framing: this narrow
            # structured-proposal role is explicitly "not URI's
            # identity" - soul.md's identity/character content belongs
            # in the response-drafting/narrative call (see
            # _draft_narrative_safely), where the Brain actually speaks
            # in URI's voice, not in this JSON-shaped planning call.
            query_context = dict(query_context)
            query_context["identity"] = ""
            query_context["soul"] = ""
            query_context["session"] = {}
            query_context["capabilities"] = []

            session_context = (
                self._build_model_session_context(
                    session
                )
            )

            if isinstance(learned_skill, dict):

                # A plain, bounded reference - never the raw
                # skill_memory record (which also carries an internal
                # "workflow" step-name list irrelevant to the Brain).
                # The Brain decides whether this is relevant; nothing
                # here treats it as a decision.
                session_context = dict(session_context)

                session_context["learned_skill_reference"] = {
                    "tool_name": learned_skill.get("tool_name"),
                    "task_type": learned_skill.get("task_type"),
                    "domain": learned_skill.get("domain"),
                    "success_count": learned_skill.get(
                        "success_count", 0
                    ),
                }

            result = (
                self.model_reasoning_gateway.reason(
                    user_text=user_text,
                    session_context=session_context,
                    evidence_context=(
                        self._build_model_evidence_context(
                            session
                        )
                    ),
                    query_context=query_context,
                    attempt_history=attempt_history,
                    pending_proposal=pending_proposal,
                    interaction_signal=interaction_signal,
                    retention_request=retention_request
                )
            )

            return {
                "status":
                    "reasoning_completed",

                "result":
                    result
            }

        except Exception as exc:

            return {
                "status":
                    "reasoning_failed",

                "error":
                    str(exc)
            }

    # Milestone 12 (Real Brain Loop): a handful of generic, self-
    # evidently identifier-shaped keys - not a task taxonomy, not a
    # set of domain keywords. These say nothing about WHAT the Brain
    # may decide, only recognize WHERE it commonly puts a capability
    # identifier when it does not use the exact action.capability/
    # workflow.steps[].capability path - see
    # _recover_capability_mentions.
    # The plural forms below were added after live testing against
    # qwen3:14b: given the FULL orchestrator context (session, query,
    # capability catalogue), the same model that returns a strict
    # {"steps": [{"capability": ...}]} shape on a lean prompt instead
    # returns {"capabilities_required": ["gmail_search"], ...} - the
    # capability named as a LIST ITEM under a plural, still
    # self-evidently identifier-shaped key. That is the identical
    # class of off-contract shape this recovery already exists to
    # recognize, so it is handled the same way and under the same two
    # guards: an identifier-shaped KEY, and a value independently
    # confirmed against the authoritative capability registry. Keys
    # that would mean the opposite ("gaps", "unavailable",
    # "missing_capabilities") are deliberately NOT listed - this set
    # only ever names "capabilities to use".
    _TOLERANT_CAPABILITY_KEYS = frozenset(
        {
            "capability",
            "capability_id",
            "tool",
            "tool_name",
            "capabilities",
            "capabilities_required",
            "required_capabilities",
            "tools",
            "tools_required",
        }
    )

    def _executable_capability_ids(self):
        """The authoritative, currently-executable capability id set -
        the single source every extraction path (strict or tolerant)
        checks a proposed capability name against. Reused, not
        reimplemented, from self.capability_registry (the same
        instance ApprovalGate/approval-requirement lookups already use
        elsewhere in this class). Never raises."""

        try:
            return {
                descriptor.id
                for descriptor in (
                    self.capability_registry.list_capabilities()
                )
                if descriptor.is_executable
            }
        except Exception:
            return set()

    def _recover_capability_mentions(
        self,
        node,
        executable_capability_ids,
        found=None
    ):
        """Milestone 12 (Real Brain Loop): a shape-agnostic recovery
        pass over an ALREADY-PARSED proposal object, for when the real
        Brain named a real, registered capability but not at the exact
        action.capability/workflow.steps[].capability path the strict
        contract expects - e.g. {"proposed_workflow": [{"capability_id":
        "..."}]} or {"proposed_actions": [{"capability": "...", ...}]}
        instead of {"action": {"capability": "..."}} - both genuinely
        observed from a real model in live testing. This is
        deliberately NOT a new cognitive template, task taxonomy, or
        keyword scorer: it does not care what the model names its own
        wrapper structure, and does not look at intent/goal/reasoning
        prose at all - it only ever recognizes a capability IDENTIFIER
        under one of a handful of generic, self-evidently identifier-
        shaped keys (_TOLERANT_CAPABILITY_KEYS), and only when that
        exact value is independently confirmed against the
        authoritative capability registry - the same check the strict
        path already relies on. Nothing about what the Brain is
        allowed to think, plan, or propose is constrained here; this
        only widens what URI recognizes as a decision the Brain has
        already made.

        Returns capability-name strings in first-seen (pre-order,
        depth-first) order, deduplicated. Never raises - any traversal
        failure degrades to whatever was already found.
        """

        if found is None:
            found = []

        try:

            if isinstance(node, dict):

                for key, value in node.items():

                    if key in self._TOLERANT_CAPABILITY_KEYS:

                        # A single identifier, or a list of them - both
                        # under the same identifier-shaped key, and both
                        # still confirmed one by one against the
                        # authoritative registry below. A list item that
                        # is not an exact registered capability id (a
                        # sentence, a nested object, a made-up name) is
                        # simply not matched, exactly as before.
                        candidates = (
                            [value] if isinstance(value, str) else value
                        )

                        if isinstance(candidates, list):

                            for candidate in candidates:

                                if (
                                    isinstance(candidate, str)
                                    and candidate in executable_capability_ids
                                    and candidate not in found
                                ):
                                    found.append(candidate)

                    self._recover_capability_mentions(
                        value, executable_capability_ids, found
                    )

            elif isinstance(node, list):

                for item in node:
                    self._recover_capability_mentions(
                        item, executable_capability_ids, found
                    )

        except Exception:
            return found

        return found

    def _model_proposed_capability(
        self,
        model_reasoning
    ):
        """Extracts a usable, registry-validated single-capability
        name from _run_model_reasoning's result, or None when there is
        none to use.

        Returns None (falls back to the deterministic
        CapabilityPlanner - see process_user_input) whenever:
        - model reasoning is disabled or failed to run;
        - no model is configured;
        - ModelReasoningGateway.validate_proposal() rejected the
          proposal (e.g. an unregistered/invented capability name -
          see model_reasoning_gateway.py's own validation, unmodified
          here);
        - the proposal names a workflow instead of - or in addition to
          - a single action (a genuine, multi-capability workflow is
          _model_proposed_workflow's concern, not this method's).

        Only a plain capability-name string ever crosses this
        boundary - never the model's proposed arguments/reason text,
        which are never read here or anywhere in process_user_input's
        capability_selected branch. The deterministic runtime still
        supplies the real arguments (request_text=user_text) exactly
        as it always has for a CapabilityPlanner-selected tool - see
        ApprovalGate.execute_tool, unmodified.

        Milestone 12 (Real Brain Loop): when the strict
        action.capability path finds nothing, this falls back to
        _recover_capability_mentions - promoted ONLY when it finds
        EXACTLY ONE distinct, already-registered capability mentioned
        anywhere in the proposal. Zero mentions means genuinely
        nothing to use (unchanged fallback behaviour). Two or more are
        deliberately left to _model_proposed_workflow, which treats
        multiple mentions as an implied sequential workflow rather
        than this method guessing which single one to use.

        Never raises: any unexpected shape degrades to None, the same
        as "no usable proposal," so a malformed result can never break
        real decision-making.
        """

        try:

            if model_reasoning.get("status") != "reasoning_completed":
                return None

            result = model_reasoning.get("result", {})

            if result.get("status") != "proposal_ready":
                return None

            proposal = result.get("proposal")

            if not isinstance(proposal, dict):
                return None

            if proposal.get("workflow") is not None:
                return None

            action = proposal.get("action")

            if isinstance(action, dict):

                capability = action.get("capability")

                if isinstance(capability, str) and capability.strip():
                    return capability

            mentions = self._recover_capability_mentions(
                proposal, self._executable_capability_ids()
            )

            if len(mentions) == 1:
                return mentions[0]

            return None

        except Exception:
            return None

    def _strict_model_proposed_workflow(
        self,
        model_reasoning
    ):
        """Extracts a usable, registry-validated multi-step workflow
        proposal from _run_model_reasoning's result, or None when
        there is none to use - mirrors _model_proposed_capability for
        the single-action case (Milestone 11 Phase 2). Unmodified since
        Phase 2 - see _model_proposed_workflow, the public entry point,
        for the Milestone 12 tolerant fallback layered on top of this
        exact, unchanged strict path.

        Returns None (falls back to the deterministic WorkflowPlanner/
        WorkflowCapabilityRouter path - see process_user_input)
        whenever:
        - model reasoning is disabled, failed to run, or not
          configured;
        - the proposal has no workflow object, or the workflow has no
          steps (a single-action proposal is _model_proposed_capability's
          concern, not this method's);
        - ModelReasoningGateway.validate_proposal() already rejected
          the proposal (e.g. an unregistered capability name in any
          step - see model_reasoning_gateway.py's own validation,
          unmodified here) - reaching "proposal_ready" is a
          precondition checked below;
        - despite already passing validate_proposal(), any step's
          capability does not independently resolve to an EXECUTABLE
          descriptor in self.capability_registry right now (belt-and-
          braces re-check immediately before execution, using the
          same CapabilityRegistry instance ApprovalGate/approval-
          requirement lookups already use elsewhere in this class -
          not a second, independent implementation of "is this
          registered").

        On success, returns a small, normalized {"goal": str,
        "steps": [...]}, not the raw proposal - every step reduced to
        exactly the fields WorkflowExecutor needs (step_id, capability,
        depends_on, requires_user_input), so nothing beyond an
        already-validated capability name and dependency shape crosses
        from model output into execution.

        Never raises: any unexpected shape degrades to None, the same
        as "no usable proposal."
        """

        try:

            if model_reasoning.get("status") != "reasoning_completed":
                return None

            result = model_reasoning.get("result", {})

            if result.get("status") != "proposal_ready":
                return None

            proposal = result.get("proposal")

            if not isinstance(proposal, dict):
                return None

            workflow_proposal = proposal.get("workflow")

            if not isinstance(workflow_proposal, dict):
                return None

            steps = workflow_proposal.get("steps")

            if not isinstance(steps, list) or not steps:
                return None

            executable_capability_ids = {
                descriptor.id
                for descriptor in self.capability_registry.list_capabilities()
                if descriptor.is_executable
            }

            normalized_steps = []

            for step in steps:

                if not isinstance(step, dict):
                    return None

                step_id = step.get("step_id")

                if not isinstance(step_id, str) or not step_id.strip():
                    return None

                capability = step.get("capability")

                if (
                    not isinstance(capability, str)
                    or capability not in executable_capability_ids
                ):
                    return None

                depends_on = step.get("depends_on", [])

                if not isinstance(depends_on, list):
                    return None

                normalized_steps.append(
                    {
                        "step_id": step_id,
                        "capability": capability,
                        "depends_on": list(depends_on),
                        "requires_user_input": bool(
                            step.get("requires_user_input", False)
                        ),
                    }
                )

            goal = workflow_proposal.get("goal")

            if not isinstance(goal, str) or not goal.strip():
                goal = ""

            return {
                "goal": goal,
                "steps": normalized_steps,
            }

        except Exception:
            return None

    def _model_proposed_workflow(
        self,
        model_reasoning
    ):
        """Public entry point: tries _strict_model_proposed_workflow
        (Phase 2, unmodified) first - the exact action.capability/
        workflow.steps[] contract, still preferred whenever the Brain
        actually uses it. When that finds nothing, falls back to
        _recover_capability_mentions (Milestone 12, Real Brain Loop):
        if the Brain named TWO OR MORE distinct, already-registered
        capabilities anywhere in its response - just not in the exact
        strict shape - this treats that as an implied sequential
        workflow in the order they were written, each step depending
        on the one before it. This is the most faithful, still
        entirely generic reading of "the Brain listed these as steps
        in this order" without guessing at any dependency structure it
        did not actually state.

        A single mention is deliberately left to
        _model_proposed_capability (never duplicated here), preserving
        the same mutual exclusivity the strict paths already have.

        Never raises.
        """

        strict = self._strict_model_proposed_workflow(model_reasoning)

        if strict is not None:
            return strict

        try:

            if model_reasoning.get("status") != "reasoning_completed":
                return None

            result = model_reasoning.get("result", {})

            if result.get("status") != "proposal_ready":
                return None

            proposal = result.get("proposal")

            if not isinstance(proposal, dict):
                return None

            mentions = self._recover_capability_mentions(
                proposal, self._executable_capability_ids()
            )

            if len(mentions) < 2:
                return None

            normalized_steps = [
                {
                    "step_id": f"step_{index + 1}",
                    "capability": capability,
                    "depends_on": (
                        [f"step_{index}"] if index > 0 else []
                    ),
                    "requires_user_input": False,
                }
                for index, capability in enumerate(mentions)
            ]

            return {
                "goal": "",
                "steps": normalized_steps,
            }

        except Exception:
            return None

    def _model_evaluation(
        self,
        model_reasoning
    ):
        """Extracts a usable {"satisfied": bool, "reason": Optional[str]}
        evaluation from _run_model_reasoning's result, or None when
        there is none to use (Milestone 11 Part 2 - Brain re-evaluation
        loop).

        Returns None whenever:
        - model reasoning is disabled, failed to run, or not
          configured;
        - ModelReasoningGateway.validate_proposal() rejected the
          proposal;
        - the proposal has no "evaluation" object at all, or (even
          tolerantly, see below) no usable satisfaction boolean in it
          (e.g. this was an initial proposal with nothing to evaluate
          yet, or the model responded with something malformed).

        Milestone 13 Part 2: live testing found the real model
        sometimes puts the SAME satisfaction judgment under a
        different, still self-evidently-named boolean key inside the
        SAME evaluation object (e.g. "result_satisfies_request" instead
        of "satisfied") rather than an entirely different response
        shape - the identical class of problem
        _recover_capability_mentions already solves for capability
        proposals, applied here narrowly to one boolean field within an
        already-present evaluation object (never a scan of the whole
        proposal, and never a guess when there is no evaluation object
        at all - the harder case of the Brain skipping evaluation
        entirely and just proposing again is left as "nothing usable,"
        exactly as before, rather than inferring intent from an
        unrelated shape).

        A None return always means "cannot get a structured judgment
        from the Brain right now" - callers must stop the evaluation
        loop safely rather than guess, exactly like
        _model_proposed_capability/_model_proposed_workflow returning
        None means "nothing usable to execute."

        Never raises.
        """

        try:

            if model_reasoning.get("status") != "reasoning_completed":
                return None

            result = model_reasoning.get("result", {})

            if result.get("status") != "proposal_ready":
                return None

            proposal = result.get("proposal")

            if not isinstance(proposal, dict):
                return None

            evaluation = proposal.get("evaluation")

            if not isinstance(evaluation, dict):
                return None

            satisfied = evaluation.get("satisfied")

            if not isinstance(satisfied, bool):

                satisfied = None

                for key in self._TOLERANT_SATISFACTION_KEYS:

                    value = evaluation.get(key)

                    if isinstance(value, bool):
                        satisfied = value
                        break

            if not isinstance(satisfied, bool):
                return None

            reason = evaluation.get("reason")

            return {
                "satisfied": satisfied,
                "reason": reason if isinstance(reason, str) else None,
            }

        except Exception:
            return None

    _TOLERANT_SATISFACTION_KEYS = frozenset(
        {
            "result_satisfies_request",
            "satisfies_request",
            "goal_achieved",
            "task_complete",
            "request_fulfilled",
        }
    )

    def _model_clarification(
        self,
        model_reasoning
    ):
        """Extracts a usable {"question": str} clarification from
        _run_model_reasoning's result, or None when there is none to
        use. Mirrors _model_evaluation's exact discipline - a None
        return always means "nothing usable," never "the Brain said
        no." Never raises."""

        try:

            if model_reasoning.get("status") != "reasoning_completed":
                return None

            result = model_reasoning.get("result", {})

            if result.get("status") != "proposal_ready":
                return None

            proposal = result.get("proposal")

            if not isinstance(proposal, dict):
                return None

            clarification = proposal.get("clarification")

            if not isinstance(clarification, dict):
                return None

            question = clarification.get("question")

            if not isinstance(question, str) or not question.strip():
                return None

            return {"question": question}

        except Exception:
            return None

    _RETENTION_CATEGORIES = frozenset(
        {
            "successful_approach",
            "user_preference",
            "reference_pattern",
            "other",
        }
    )

    _MAX_RETENTION_SUMMARY_LENGTH = 500

    def _model_retention_candidate(
        self,
        model_reasoning
    ):
        """Milestone 13 Part 2: extracts a usable retention candidate
        - {"category": str, "summary": str} - from a retention_request
        call's result, or None when the Brain proposed nothing worth
        retaining (should_retain false/absent, a malformed shape, or
        the call itself produced nothing usable). Mirrors
        _model_clarification's exact discipline - URI does its own
        bounding here (category must be one of a small known set,
        summary is length-capped) rather than trusting the Brain's
        output as already safe to persist; this is extraction, not
        persistence - see _run_acceptance_retention_step for what
        actually gets stored. Never raises."""

        try:

            if model_reasoning.get("status") != "reasoning_completed":
                return None

            result = model_reasoning.get("result", {})

            if result.get("status") != "proposal_ready":
                return None

            proposal = result.get("proposal")

            if not isinstance(proposal, dict):
                return None

            candidate = proposal.get("retention_candidate")

            if not isinstance(candidate, dict):
                return None

            if candidate.get("should_retain") is not True:
                return None

            category = candidate.get("category")

            if category not in self._RETENTION_CATEGORIES:
                category = "other"

            summary = candidate.get("summary")

            if not isinstance(summary, str) or not summary.strip():
                return None

            summary = summary.strip()[: self._MAX_RETENTION_SUMMARY_LENGTH]

            return {"category": category, "summary": summary}

        except Exception:
            return None

    def _describe_model_proposal(
        self,
        capability,
        workflow
    ):
        """Builds the {"action": {...}} or {"workflow": {...}} shape a
        capability/workflow proposal is handed back to the Brain in -
        deliberately the exact same shape the Brain's own output
        contract already uses (see REASONING_SYSTEM_PROMPT's "action"/
        "workflow" keys), so a pending_proposal reads as "the plan you
        already proposed," not a new, unfamiliar structure. capability
        and workflow are mutually exclusive, exactly as
        _model_proposed_capability/_model_proposed_workflow already
        guarantee for any single reasoning result. Returns None when
        neither is given. Never raises."""

        try:

            if capability is not None:
                return {"action": {"capability": capability}}

            if workflow is not None:
                return {"workflow": workflow}

            return None

        except Exception:
            return None

    def _run_pre_execution_sanity_check(
        self,
        user_text,
        session,
        session_id,
        personalization_context,
        learned_skill,
        model_capability_proposal,
        model_workflow_proposal
    ):
        """Milestone 13 Part 1 - the canonical loop's pre-execution
        step: gives the Brain one explicit opportunity to reconsider
        its own already-formulated plan against the same full session/
        evidence/capability/personalization context, before anything
        executes. URI's only role here is to present the Brain's own
        prior proposal back to it (see _describe_model_proposal) inside
        a fresh, otherwise-ordinary reasoning call (pending_proposal -
        see _run_model_reasoning) and relay whatever the Brain decides
        into the exact same validated extraction path
        (_model_proposed_capability/_model_proposed_workflow/
        _model_clarification) any other proposal already goes through.
        URI never judges whether the Brain's plan is intellectually
        correct, and never distinguishes "confirmed" from "modified"
        from "replaced" - all three simply mean "use whatever the
        Brain now says," exactly as if this were the Brain's first and
        only proposal.

        Returns:
        - {"status": "revised_or_confirmed", "model_reasoning": ...}
          when the Brain returned a usable action or workflow (whether
          identical to the original or genuinely different - URI does
          not distinguish the two).
        - {"status": "clarification_needed", "clarification":
          {"question": ...}, "model_reasoning": ...} when the Brain
          decided more information is needed instead.
        - {"status": "unavailable", "model_reasoning": ...} when this
          second call itself produced nothing usable (reasoning
          disabled/unreachable/malformed) - the caller must keep the
          ORIGINAL proposal unchanged in this case, never discard an
          already-valid Brain decision because the sanity check itself
          could not run.

        Never raises: any unexpected shape is treated as
        "unavailable," the same safe default as everywhere else this
        codebase reasons about the Brain's output.
        """

        try:

            pending_proposal = self._describe_model_proposal(
                model_capability_proposal, model_workflow_proposal
            )

            model_reasoning = self._run_model_reasoning(
                user_text=user_text,
                session=session,
                session_id=session_id,
                personalization_context=personalization_context,
                attempt_history=None,
                learned_skill=learned_skill,
                pending_proposal=pending_proposal,
            )

            new_capability = self._model_proposed_capability(
                model_reasoning
            )
            new_workflow = self._model_proposed_workflow(
                model_reasoning
            )

            if new_capability is not None or new_workflow is not None:
                return {
                    "status": "revised_or_confirmed",
                    "model_reasoning": model_reasoning,
                }

            clarification = self._model_clarification(model_reasoning)

            if clarification is not None:
                return {
                    "status": "clarification_needed",
                    "clarification": clarification,
                    "model_reasoning": model_reasoning,
                }

            return {
                "status": "unavailable",
                "model_reasoning": model_reasoning,
            }

        except Exception:
            return {
                "status": "unavailable",
                "model_reasoning": model_reasoning
                if "model_reasoning" in locals()
                else None,
            }

    def _apply_clarification_pause(
        self,
        response,
        question,
        stage,
        session,
        session_id,
        user_text,
        attempt_history_so_far=None
    ):
        """Milestone 13 Part 1/2: pauses a turn on the Brain's own
        decision that more information is needed, before anything
        (further) executes - reused for an initial-call clarification
        (no plan was ever formulated), a pre-execution sanity-check
        clarification (a plan was formulated, then the Brain decided
        against acting on it once given fuller context), and a
        post-execution re-evaluation clarification (real actions may
        already have happened this turn, but the Brain has nothing
        further to propose without an answer first). Mirrors the same
        "waiting_for_input" pause vocabulary WorkflowExecutor already
        uses elsewhere in this class, so callers/UI treat it exactly
        like any other pause. stage is a plain, human-readable label
        for transparency only - it changes nothing about how the pause
        itself is handled.

        Milestone 13 Part 2: also carries this exchange forward as one
        more attempt_history entry - {"goal": user_text, "proposal":
        {"type": "clarification", "question": question}, "result":
        {"status": "awaiting_user_response", "data": None}} - appended
        to attempt_history_so_far (whatever real actions already
        happened this turn, or none). This is the SAME generic
        attempt_history carry-forward _carry_forward_goal_attempt_history
        already provides; nothing new is invented here, it is just
        also used for a clarification rather than only a completed
        action's result. On the user's next message, process_user_input
        reads this back and computes interaction_signal =
        "MISSING_INFORMATION" - see there for how the Brain is told
        why. Never raises.
        """

        response["plan"] = {
            "status": "clarification_needed",
            "tool_name": None,
            "reason": question,
            "source": "model_reasoning",
        }

        response["execution"] = {
            "status": "waiting_for_input",
            "message": question,
        }

        response["clarification"] = {
            "question": question,
            "stage": stage,
        }

        try:

            combined_history = list(attempt_history_so_far or [])

            combined_history.append(
                {
                    "goal": user_text,
                    "proposal": {
                        "type": "clarification",
                        "question": question,
                    },
                    "result": {
                        "status": "awaiting_user_response",
                        "data": None,
                    },
                }
            )

            self._carry_forward_goal_attempt_history(
                session=session,
                session_id=session_id,
                user_text=user_text,
                attempt_history=combined_history,
            )

        except Exception:
            pass

        return response

    def _record_pre_execution_sanity_check_audit(
        self,
        session_id,
        outcome
    ):
        """Honest bookkeeping for one pre-execution sanity check -
        mirrors _record_brain_reevaluation_audit's exact discipline.
        Never raises."""

        try:

            self.audit_trail.record(
                event_type="pre_execution_sanity_check",
                status=outcome,
                session_id=session_id,
                metadata={"outcome": outcome},
            )

        except Exception:
            return

    def _executed_tool_names(
        self,
        response
    ):
        """The capability name(s) actually executed for this turn's
        response - a single-item list for a plain capability
        execution, or the ordered capability list from a Brain-
        composed workflow. Read-only, purely descriptive: never
        re-derives or re-validates anything, only reports what
        response already recorded. Never raises."""

        try:

            execution = response.get("execution")

            if (
                isinstance(execution, dict)
                and isinstance(execution.get("tool"), str)
            ):
                return [execution["tool"]]

            workflow = response.get("workflow")

            if isinstance(workflow, dict):

                return [
                    step.get("capability")
                    for step in workflow.get("steps", [])
                    if isinstance(step, dict)
                    and isinstance(step.get("capability"), str)
                ]

            return []

        except Exception:
            return []

    def _record_retention_audit(
        self,
        session_id,
        outcome,
        category=None,
        summary=None,
        persisted=False
    ):
        """Honest bookkeeping for one acceptance retention step -
        mirrors _record_brain_reevaluation_audit's exact discipline.
        This is also the PROVENANCE record for whatever the Brain
        proposed retaining, independent of whether URI actually
        persisted it anywhere else. Never raises."""

        try:

            self.audit_trail.record(
                event_type="brain_retention_candidate",
                status=outcome,
                session_id=session_id,
                metadata={
                    "outcome": outcome,
                    "category": category,
                    "summary": summary,
                    "persisted": bool(persisted),
                },
            )

        except Exception:
            return

    def _run_acceptance_retention_step(
        self,
        session,
        session_id,
        user_text,
        response,
        personalization_context=None
    ):
        """Milestone 13 Part 2 - the canonical loop's acceptance step:
        once the Brain has judged a result satisfied (the closest
        generic proxy URI has today to "the user accepted it," in a
        text-only interface with no separate accept/reject gesture),
        asks the Brain ONE dedicated question - what, if anything, from
        this interaction is genuinely worth remembering for a future,
        DIFFERENT request - via a fresh retention_request call (see
        _run_model_reasoning/REASONING_SYSTEM_PROMPT). The Brain
        decides WHAT is worth retaining (_model_retention_candidate
        already bounds category/summary shape); URI decides
        independently whether, how, and where to actually persist it:

        - "successful_approach" for a genuinely multi-capability
          workflow this turn is recorded into the existing
          SkillMemory (the same store/mechanism a single-capability
          success is already unconditionally recorded into elsewhere -
          see process_user_input's dispatch-success branch - so a
          single-capability "successful_approach" candidate is
          deliberately NOT re-recorded here, to avoid double-counting
          the exact same outcome).
        - every other category (or should_retain=false/absent) is not
          persisted anywhere as a standing fact - only kept as an
          honest, inspectable audit record of what the Brain proposed
          (see _record_retention_audit) - deliberately NOT a general
          long-term knowledge store: building one is a real, separate
          piece of work this milestone does not attempt.

        Never blindly stores the whole interaction, never promotes a
        single success into a permanent rule, and never raises - a
        failure here must never affect the already-decided
        brain_evaluation/execution outcome. Mutates response in place,
        adding response["retention"].
        """

        try:

            model_reasoning = self._run_model_reasoning(
                user_text=user_text,
                session=session,
                session_id=session_id,
                personalization_context=personalization_context,
                attempt_history=None,
                learned_skill=None,
                retention_request=True,
            )

            candidate = self._model_retention_candidate(model_reasoning)

            if candidate is None:

                response["retention"] = {"outcome": "nothing_to_retain"}

                self._record_retention_audit(
                    session_id=session_id,
                    outcome="nothing_to_retain",
                )

                return

            category = candidate["category"]
            summary = candidate["summary"]
            persisted = False

            if category == "successful_approach":

                tool_names = self._executed_tool_names(response)

                if len(tool_names) > 1:

                    semantic_result = (
                        response.get("semantic_analysis") or {}
                    )

                    self.skill_memory.learn_skill(
                        semantic_result=semantic_result,
                        workflow=list(tool_names),
                        tool_name="+".join(tool_names),
                    )

                    persisted = True

            # Item 7 (structured experience/history records): every
            # candidate the Brain judged worth retaining - not only
            # "successful_approach" for a multi-capability workflow -
            # is additionally kept as one small, structured, retrievable
            # ExperienceRecord (see experience_store.py). This is
            # independent of `persisted` above, which stays scoped to
            # the existing SkillMemory dedup discipline (see the
            # milestone note on this method): "persisted" answers
            # "was this also learned as a reusable tool sequence?",
            # while `experience_recorded` answers "did URI keep a
            # structured record of what happened?" - the two may
            # legitimately differ. Never blocks the retention outcome
            # already decided above - a write failure here degrades to
            # experience_recorded=False, not an exception.
            experience_recorded = False

            try:

                self.experience_store.add(
                    category=category,
                    intent=user_text,
                    summary=summary,
                    actions=self._executed_tool_names(response),
                    results=str(
                        (response.get("execution") or {}).get("status")
                        if isinstance(response.get("execution"), dict)
                        else ""
                    ),
                )

                experience_recorded = True

            except Exception:
                experience_recorded = False

            self._record_retention_audit(
                session_id=session_id,
                outcome="candidate_received",
                category=category,
                summary=summary,
                persisted=persisted,
            )

            response["retention"] = {
                "outcome": "candidate_received",
                "category": category,
                "summary": summary,
                "persisted": persisted,
                "experience_recorded": experience_recorded,
            }

        except Exception:
            response["retention"] = {"outcome": "unavailable"}

    def _build_model_workflow(
        self,
        model_workflow_proposal
    ):
        """Turns _model_proposed_workflow's normalized {"goal", "steps"}
        into a full workflow dict WorkflowExecutor._ensure_workflow_metadata
        can complete (workflow_id/schema_version/status/timestamps are
        all filled in there, unmodified - the same way
        WorkflowPlanner.create_workflow's own output relies on it).

        "source": "model_reasoning" is the one field this workflow
        carries that a WorkflowPlanner-built workflow never has - it is
        what _create_workflow_executor below reads to decide which
        kind of executor a persisted/resumed workflow needs, and what
        makes response["plan"]/audit metadata honest about this
        workflow's real origin.
        """

        return {
            "workflow_id": (
                "model-workflow-" + os.urandom(8).hex()
            ),
            "source": "model_reasoning",
            "goal": model_workflow_proposal["goal"],
            "request_text": model_workflow_proposal["goal"],
            "status": "planned",
            "steps": model_workflow_proposal["steps"],
        }

    def _build_model_workflow_executor(
        self,
        workflow,
        session_id
    ):
        """Builds a generic WorkflowExecutor for a Brain-composed
        workflow (Milestone 11 Phase 2): one handler per REAL,
        already-registry-confirmed capability named in
        workflow["steps"] (see _model_proposed_workflow), each handler
        doing nothing but calling self.approval_gate.execute_tool(...)
        - never self.dispatcher directly - so approval requirements,
        execution, and persistence are decided exactly as they already
        are for the direct single-capability path (Milestone 11 Phase
        1) and the existing WorkflowCapabilityRouter-backed workflow
        path. WorkflowExecutor itself is unmodified and generic; only
        handler registration differs from _create_workflow_executor's
        default (WorkflowCapabilityRouter) branch.

        Known, deliberate limitation (Milestone 11 Phase 2 - see
        process_user_input): every step's request_text is
        workflow["goal"] - the Brain's original request text, exactly
        the same field WorkflowCapabilityRouter's own handlers already
        read this way (see workflow_capability_router.py's
        draft_output/retrieve_evidence). A model-proposed step's own
        "arguments" are never read here, the same discipline
        _model_proposed_capability already applies to a single-action
        proposal - richer, per-step structured argument synthesis is
        deferred to a later increment, not invented ad hoc here.
        """

        executor = WorkflowExecutor()

        goal = workflow.get("goal", "")

        capability_ids = {
            step.get("capability")
            for step in workflow.get("steps", [])
            if (
                isinstance(step, dict)
                and isinstance(step.get("capability"), str)
            )
        }

        for capability_id in capability_ids:

            executor.register_handler(
                capability_id,
                self._model_workflow_step_handler(
                    capability_id=capability_id,
                    session_id=session_id,
                    goal=goal,
                ),
            )

        return executor

    def _model_workflow_step_handler(
        self,
        capability_id,
        session_id,
        goal
    ):
        """One closure per capability - the ONLY thing a Brain-
        composed workflow step's handler ever does is call
        ApprovalGate.execute_tool(), unmodified, with exactly the
        arguments the direct single-capability path already uses
        (session_id, request_text). This is what guarantees approval
        requirements are enforced identically regardless of whether a
        capability was chosen directly (Phase 1) or as one step of a
        Brain-composed workflow (Phase 2)."""

        def _handler(step, workflow):

            return self.approval_gate.execute_tool(
                capability_id,
                session_id=session_id,
                request_text=goal,
            )

        return _handler

    def _record_model_workflow_audit(
        self,
        session_id,
        workflow_proposed,
        workflow_valid,
        used_as_plan,
        fallback_reason=None
    ):
        """Milestone 11 Phase 2's honest bookkeeping for the workflow
        decision, mirroring _record_model_reasoning_audit's Phase 1
        "used_as_plan" discipline: records whether the Brain proposed
        a workflow at all this turn (workflow_proposed), whether that
        proposal survived re-validation against the authoritative
        CapabilityRegistry (workflow_valid), whether it actually became
        the executed plan (used_as_plan), and - when it did not - why
        the deterministic WorkflowPlanner/WorkflowCapabilityRouter
        fallback was used instead (fallback_reason).

        Never raises - a failure to audit must never break the live
        request."""

        try:

            self.audit_trail.record(
                event_type="model_workflow_evaluation",
                status="used" if used_as_plan else "fallback",
                session_id=session_id,
                metadata={
                    "workflow_proposed": bool(workflow_proposed),
                    "workflow_valid": bool(workflow_valid),
                    "used_as_plan": bool(used_as_plan),
                    "fallback_reason": fallback_reason,
                },
            )

        except Exception:
            return

    # ==========================================================
    # BRAIN RE-EVALUATION LOOP (Milestone 11 Part 2)
    #
    # user goal -> Brain proposes -> URI validates/executes ->
    # real result -> Brain re-evaluates -> satisfied, or a new
    # proposal -> URI validates/executes -> ... -> goal achieved
    # (or the Brain honestly has nothing further to try, or the
    # safety cap is reached).
    #
    # URI never decides on its own that a technically-successful
    # execution means the user's goal was achieved, and URI never
    # repeats an action on its own initiative - every additional
    # attempt here comes from a fresh, independently-validated Brain
    # proposal (_model_proposed_capability/_model_proposed_workflow,
    # both unmodified), executed only through the exact same
    # ApprovalGate/WorkflowExecutor boundary as the first attempt.
    # This section only ever runs for a plan whose "source" is
    # "model_reasoning" - a learned skill or a CapabilityPlanner/
    # WorkflowPlanner fallback plan is never re-evaluated this way,
    # preserving their existing, unmodified behaviour exactly.
    # ==========================================================

    def _is_paused_execution(
        self,
        execution
    ):
        """True when an execution result is waiting on a human
        decision (approval or more information) rather than actually
        finished (success/failure/blocked). A paused result must never
        be sent to the Brain for evaluation - the user hasn't acted
        yet, so there is nothing real to evaluate."""

        if not isinstance(execution, dict):
            return False

        return execution.get("status") in (
            "awaiting_approval",
            "waiting_for_input",
        )

    def _compact_attempt_result(
        self,
        execution,
        response_data
    ):
        """Builds one bounded, JSON-safe {"status", "data"} summary of
        an attempt's real outcome for attempt_history - the actual
        result data (not just a bare status word) is what lets the
        Brain judge whether the goal was really satisfied, e.g.
        recognising a tool's own "local_fallback_cache"/mock-data
        marker rather than presenting it as a real answer. Bounded the
        same way response_drafting.py already bounds known_gaps text,
        so one large tool result can never blow up the next reasoning
        request. Never raises."""

        status = (
            execution.get("status")
            if isinstance(execution, dict)
            else None
        )

        try:
            data_text = json.dumps(
                response_data,
                default=str,
                ensure_ascii=False,
            )
        except Exception:
            data_text = str(response_data)

        if len(data_text) > 800:
            data_text = data_text[:800].rstrip() + "...(truncated)"

        return {
            "status": status,
            "data": data_text,
        }

    def _record_brain_reevaluation_audit(
        self,
        session_id,
        iteration,
        satisfied,
        used_next_proposal,
        stop_reason=None
    ):
        """Honest bookkeeping for one round of the re-evaluation loop -
        mirrors _record_model_reasoning_audit/_record_model_workflow_audit's
        existing discipline. Never raises."""

        try:

            self.audit_trail.record(
                event_type="brain_reevaluation",
                status="satisfied" if satisfied else "continuing",
                session_id=session_id,
                metadata={
                    "iteration": iteration,
                    "satisfied": bool(satisfied),
                    "used_next_proposal": bool(used_next_proposal),
                    "stop_reason": stop_reason,
                },
            )

        except Exception:
            return

    # Bounds how much attempt history carries forward into the next
    # turn - the same "small, bounded reference, never an unbounded
    # dump" discipline personalization_context.py/query_context.py
    # already apply elsewhere in this codebase.
    _MAX_CARRIED_ATTEMPT_ENTRIES = 3

    def _carry_forward_goal_attempt_history(
        self,
        session,
        session_id,
        user_text,
        attempt_history
    ):
        """URI Correction Part 1 / M12 feedback loop: persists this
        turn's attempt history so the Brain sees it on the NEXT turn if
        the user's following message continues, accepts, or rejects
        this same goal - read-once by process_user_input, which clears
        both fields unconditionally at the start of every turn.

        Called even when the Brain judged itself satisfied: the Brain
        being satisfied is not the same as the USER accepting the
        result - only the user has that authority. If the user's very
        next message rejects or redirects, this carried history is
        what lets the Brain evaluate that rejection against the real
        result rather than starting from nothing. If the user's next
        message is unrelated, the Brain's own goal-comparison (see
        REASONING_SYSTEM_PROMPT's attempt_history rules) recognizes
        that and treats the carried entries as inert history - URI does
        not need to, and must not, decide for itself whether the user
        accepted, rejected, or moved on.

        Bounded to the most recent _MAX_CARRIED_ATTEMPT_ENTRIES entries
        - this is a short memory aid for the immediately following
        turn, never an accumulating log.

        Never raises - a failure to persist this must never break the
        live request."""

        try:

            session.last_goal_text = user_text

            session.last_goal_attempt_history = list(
                attempt_history[-self._MAX_CARRIED_ATTEMPT_ENTRIES:]
            )

            self._persist_session(session_id)

        except Exception:
            return

    def _execute_brain_proposal(
        self,
        session,
        session_id,
        user_text,
        next_capability,
        next_workflow
    ):
        """Executes exactly one Brain-proposed next action (either a
        single capability or a workflow, never both - the same
        mutual exclusivity _model_proposed_capability/
        _model_proposed_workflow already guarantee) through the exact
        same boundaries the first attempt in a turn already uses:
        ApprovalGate.execute_tool for a single capability,
        _create_workflow_executor/WorkflowExecutor.execute for a
        workflow. Returns (execution, response_data, workflow_dict_or_None)
        so the caller can update the turn's response in place. Never
        calls self.dispatcher directly."""

        if next_capability is not None:

            dispatch_result = self.approval_gate.execute_tool(
                next_capability,
                session_id=session_id,
                request_text=user_text,
            )

            execution = {
                "status": dispatch_result.get("status"),
                "tool": next_capability,
            }

            response_data = dispatch_result.get("data", dispatch_result)

            return execution, response_data, None

        workflow = self._build_model_workflow(next_workflow)

        workflow_executor = self._create_workflow_executor(
            session,
            session_id=session_id,
            workflow=workflow,
        )

        execution = workflow_executor.execute(workflow)

        execution_status = execution.get("status")

        if execution_status == "success":

            response_data = {
                "message": "URI completed the Brain-composed workflow.",
                "workflow": execution.get("workflow"),
                "execution_log": execution.get("execution_log"),
            }

        elif execution_status == "waiting_for_input":

            self._save_paused_workflow(session, execution)

            response_data = {
                "message": session.active_workflow_question,
                "workflow": session.active_workflow,
                "required_information":
                    session.active_workflow_required_field,
            }

        else:

            response_data = {
                "message":
                    "URI could not complete the Brain-composed "
                    "workflow.",
                "workflow": execution.get("workflow"),
                "error": execution.get("error"),
            }

        return execution, response_data, workflow

    def _continue_brain_evaluation_loop(
        self,
        user_text,
        session,
        session_id,
        personalization_context,
        response,
        first_proposal_description
    ):
        """After a Brain-directed execution (response["execution"]/
        response["response"] already reflect what just happened),
        sends the Brain the original goal, what it proposed, and the
        real result, and asks it to evaluate - not because URI decided
        execution succeeding means the goal is achieved, but because
        URI never decides that on its own (see module-level comment
        above). Mutates response in place with the outcome of however
        many further rounds actually happen (0 or more, bounded by
        self.max_brain_iterations) and always leaves it in the same
        shape process_user_input's existing branches already produce -
        callers do not need to change their own return/persist logic.

        No-ops immediately (no extra call to the Brain at all) when
        the just-completed execution is still paused on a human
        decision (_is_paused_execution) - an approval-required or
        needs-more-information result is never sent for evaluation
        until the human has actually acted.

        Never repeats an action on its own: every additional execution
        here comes from a fresh next_capability/next_workflow the
        Brain itself proposed in its evaluation response, re-validated
        exactly like an initial proposal - if the Brain proposes
        nothing further, or reasoning fails/is unavailable, or the
        iteration cap is reached, the loop stops and reports which of
        those honestly happened, using whatever the LAST real
        execution already produced.
        """

        if self._is_paused_execution(response.get("execution")):
            return

        attempt_history = [
            {
                "goal": user_text,
                "proposal": first_proposal_description,
                "result": self._compact_attempt_result(
                    response.get("execution"),
                    response.get("response"),
                ),
            }
        ]

        iteration = 1

        while iteration < self.max_brain_iterations:

            model_reasoning = self._run_model_reasoning(
                user_text=user_text,
                session=session,
                session_id=session_id,
                personalization_context=personalization_context,
                attempt_history=attempt_history,
            )

            evaluation = self._model_evaluation(model_reasoning)

            if evaluation is None:

                self._record_brain_reevaluation_audit(
                    session_id=session_id,
                    iteration=iteration,
                    satisfied=False,
                    used_next_proposal=False,
                    stop_reason="evaluation_unavailable",
                )

                self._carry_forward_goal_attempt_history(
                    session=session,
                    session_id=session_id,
                    user_text=user_text,
                    attempt_history=attempt_history,
                )

                response["brain_evaluation"] = {
                    "satisfied": False,
                    "iterations": iteration,
                    "status": "evaluation_unavailable",
                }

                return

            if evaluation["satisfied"]:

                self._record_brain_reevaluation_audit(
                    session_id=session_id,
                    iteration=iteration,
                    satisfied=True,
                    used_next_proposal=False,
                )

                # M12 feedback loop: the BRAIN being satisfied is not
                # the same as the USER accepting the result - carry
                # this turn's real result forward exactly as an
                # unsatisfied turn would, so a rejecting or redirecting
                # next message still reaches the Brain as evidence
                # about what actually happened, not a fresh blank
                # slate. See _carry_forward_goal_attempt_history.
                self._carry_forward_goal_attempt_history(
                    session=session,
                    session_id=session_id,
                    user_text=user_text,
                    attempt_history=attempt_history,
                )

                response["brain_evaluation"] = {
                    "satisfied": True,
                    "reason": evaluation["reason"],
                    "iterations": iteration,
                }

                # Milestone 13 Part 2: the Brain's own satisfied=True
                # judgment is the closest generic signal URI has today
                # to "the user accepted this result" - ask the Brain,
                # once, whether anything from this interaction is
                # genuinely worth retaining for a future, different
                # request. See _run_acceptance_retention_step - it
                # never overrides brain_evaluation above, only adds its
                # own outcome to response["retention"].
                self._run_acceptance_retention_step(
                    session=session,
                    session_id=session_id,
                    user_text=user_text,
                    response=response,
                    personalization_context=personalization_context,
                )

                return

            next_capability = self._model_proposed_capability(
                model_reasoning
            )

            next_workflow = self._model_proposed_workflow(
                model_reasoning
            )

            if next_capability is None and next_workflow is None:

                # Milestone 13 Part 2: before honestly giving up, check
                # whether the Brain has a targeted question instead of
                # a next action - "nothing further to propose" and "I
                # need to ask the user something" are different
                # outcomes, and the second one deserves to reach the
                # user rather than being reported as a dead end.
                clarification = self._model_clarification(model_reasoning)

                if clarification is not None:

                    self._record_brain_reevaluation_audit(
                        session_id=session_id,
                        iteration=iteration,
                        satisfied=False,
                        used_next_proposal=False,
                        stop_reason="clarification_needed",
                    )

                    self._apply_clarification_pause(
                        response,
                        clarification["question"],
                        stage="post_execution_reevaluation",
                        session=session,
                        session_id=session_id,
                        user_text=user_text,
                        attempt_history_so_far=attempt_history,
                    )

                    return

                self._record_brain_reevaluation_audit(
                    session_id=session_id,
                    iteration=iteration,
                    satisfied=False,
                    used_next_proposal=False,
                    stop_reason="no_further_proposal",
                )

                self._carry_forward_goal_attempt_history(
                    session=session,
                    session_id=session_id,
                    user_text=user_text,
                    attempt_history=attempt_history,
                )

                response["brain_evaluation"] = {
                    "satisfied": False,
                    "reason": evaluation["reason"],
                    "iterations": iteration,
                    "status": "no_further_proposal",
                }

                return

            iteration += 1

            execution, response_data, workflow = (
                self._execute_brain_proposal(
                    session=session,
                    session_id=session_id,
                    user_text=user_text,
                    next_capability=next_capability,
                    next_workflow=next_workflow,
                )
            )

            response["execution"] = execution
            response["response"] = response_data

            if workflow is not None:

                response["workflow"] = workflow

                response["plan"] = {
                    "status": "planning_required",
                    "tool_name": None,
                    "reason": evaluation["reason"],
                    "source": "model_reasoning",
                }

                proposal_description = {
                    "type": "workflow",
                    "steps": [
                        step["capability"]
                        for step in workflow.get("steps", [])
                    ],
                }

                if execution.get("status") == "success":
                    self._clear_active_workflow(session)

            else:

                response.pop("workflow", None)

                response["plan"] = {
                    "status": "capability_selected",
                    "tool_name": next_capability,
                    "reason": evaluation["reason"],
                    "source": "model_reasoning",
                }

                proposal_description = {
                    "type": "capability",
                    "capability": next_capability,
                }

            attempt_history.append(
                {
                    "goal": user_text,
                    "proposal": proposal_description,
                    "result": self._compact_attempt_result(
                        execution, response_data
                    ),
                }
            )

            self._record_brain_reevaluation_audit(
                session_id=session_id,
                iteration=iteration,
                satisfied=False,
                used_next_proposal=True,
            )

            self._persist_session(session_id)

            if self._is_paused_execution(execution):
                return

        self._carry_forward_goal_attempt_history(
            session=session,
            session_id=session_id,
            user_text=user_text,
            attempt_history=attempt_history,
        )

        response["brain_evaluation"] = {
            "satisfied": False,
            "iterations": iteration,
            "status": "iteration_limit_reached",
        }

    # ==========================================================
    # UNIFIED QUERY CONTEXT (Milestone 10A)
    # ==========================================================

    def _build_query_context(
        self,
        session_id,
        policy_text,
        personalization_context,
        soul_text=None,
        last_operation=None
    ):
        """Assembles Milestone 10A's bounded, model-facing query
        context purely from state this orchestrator already builds or
        holds for other purposes - no new parallel state pipeline:

        - policy_text is passed in by the caller (already loaded via
          self.model_reasoning_gateway.load_policy() for the drafting
          system prompt - reused, not re-read).
        - session_context reuses _build_model_session_context, the
          same session snapshot the model-reasoning shadow path
          already builds.
        - verified_facts reuses evidence_context.get_verified_evidence
          (VERIFIED-status only) + evidence_summary - deliberately not
          evidence_context.get_relevant_evidence, whose keyword
          taxonomy is scenario-specific (see query_context.py).
        - capabilities reuses self.capability_registry (the same
          CapabilityRegistry instance already constructed for
          approval-requirement/risk lookups elsewhere in this class).

        Never raises: each section degrades to empty independently so
        one missing/unavailable piece (e.g. no session yet) never
        blanks out the rest - callers still sit behind
        _draft_narrative_safely's own broad except as a final
        backstop.
        """

        session = None

        if session_id:

            try:
                session = self.session_manager.get_session(session_id)
            except Exception:
                session = None

        session_context = {}
        verified_facts = {}

        if session is not None:

            try:
                session_context = (
                    self._build_model_session_context(session)
                )
            except Exception:
                session_context = {}

            try:
                verified_facts = evidence_summary(
                    get_verified_evidence(session)
                )
            except Exception:
                verified_facts = {}

        try:
            capabilities = self.capability_registry.list_capabilities()
        except Exception:
            capabilities = []

        # DIAGNOSTICS (item 2/8): real, already-recorded runtime state
        # only - never fabricated. recent_events reuses this session's
        # own AuditTrail entries (already validated/capped at write
        # time); known_gaps reuses the same CapabilityRegistry instance
        # already constructed above. last_operation, when given by the
        # caller, is this turn's own most recent real execution outcome
        # (see _run_model_reasoning/_draft_narrative_safely).
        try:
            recent_events = (
                self.audit_trail.for_session(session_id)
                if session_id
                else []
            )
        except Exception:
            recent_events = []

        try:
            known_gaps = self.capability_registry.known_gaps()
        except Exception:
            known_gaps = []

        diagnostics = build_diagnostics_context(
            last_operation=last_operation,
            recent_events=recent_events,
            known_gaps=known_gaps,
        )

        # EXPERIENCE (item 7): a short, bounded list of past-interaction
        # summaries the Brain itself already judged worth retaining -
        # see experience_store.py/_run_acceptance_retention_step. A
        # store failure (corrupted file, missing directory) degrades to
        # "nothing known yet," never breaks context assembly.
        try:
            experience = summarize_experience_for_query_context(
                self.experience_store.recent()
            )
        except Exception:
            experience = []

        # ATTACHMENTS (M16 Priority 1): bounded references only - what
        # the user actually attached to THIS session, never content.
        # Reading a file requires the Brain to select the registered
        # read_attached_file capability; seeing that one exists is what
        # lets it make that decision. A store failure degrades to "no
        # attachments" rather than breaking context assembly - it must
        # never claim a file exists that URI cannot actually produce.
        try:
            attachments = [
                record.to_reference()
                for record in self.file_store.list_for_session(
                    session_id
                )
            ] if session_id else []
        except Exception:
            attachments = []

        return build_query_context(
            policy_text=policy_text,
            soul_text=soul_text,
            personalization=personalization_context,
            session_context=session_context,
            verified_facts=verified_facts,
            capabilities=capabilities,
            diagnostics=diagnostics,
            experience=experience,
            attachments=attachments,
        )

    # ==========================================================
    # LIVE RESPONSE NARRATIVE (Milestone 8A)
    # ==========================================================

    def _draft_narrative_safely(
        self,
        user_text,
        response,
        personalization_context,
        session_id
    ):
        """Attempts to add response["narrative"] - additive only,
        never replaces response["execution"]/response["response"].
        Never raises: any failure (disabled, unreachable model, empty
        draft, failed claim-consistency validation) simply means no
        narrative is added, and the existing deterministic response
        (already fully built by the caller before this runs) is
        exactly what the caller returns - the pre-Milestone-8A
        fallback that is never removed.

        outcome is built only from response["execution"]/
        response["response"] - fields the deterministic runtime has
        already fully decided by the time this is called. The model
        drafting this text is never given, and never asked to decide,
        anything the runtime hasn't already settled.
        """

        if not self.enable_response_narrative:
            return

        try:

            policy_text = self.model_reasoning_gateway.load_policy()

            # URI SOUL: loaded alongside policy_text - passed to
            # DraftRequest.soul_text below, which build_drafting_system_prompt
            # prepends as this call's own system prompt, so query_context's
            # "soul" section is blanked below for the same reason
            # "identity" already is.
            soul_text = self.model_reasoning_gateway.load_soul()

            plan = response.get("plan")

            execution = response.get("execution")
            response_data = response.get("response")

            outcome = {
                "execution": execution,
                "response": response_data,
                # The real evidence for "why can't URI do this" (see
                # capability_planner.py's _known_gaps() /
                # CapabilityRegistry.known_gaps()) - without this, the
                # drafting model has no grounded information about a
                # missing capability and previously free-associated
                # troubleshooting advice instead. See
                # response_validation.py's evidence-proportional
                # length check, which uses this same field.
                "known_gaps": (
                    condense_known_gaps(plan.get("known_gaps"))
                    if isinstance(plan, dict)
                    else None
                ),
            }

            # DIAGNOSTICS: this turn's own just-decided outcome, in the
            # same {"capability", "status", "error", "message"} shape
            # diagnostics_context.py expects - real fields already
            # present in execution/response_data, never invented here.
            last_operation = {
                "capability": (
                    execution.get("tool")
                    if isinstance(execution, dict)
                    else None
                ),
                "status": (
                    execution.get("status")
                    if isinstance(execution, dict)
                    else None
                ),
                "error": (
                    response_data.get("error")
                    if isinstance(response_data, dict)
                    else None
                ),
                "message": (
                    response_data.get("message")
                    if isinstance(response_data, dict)
                    else None
                ),
            }

            query_context = self._build_query_context(
                session_id=session_id,
                policy_text=policy_text,
                personalization_context=personalization_context,
                soul_text=soul_text,
                last_operation=last_operation,
            )

            # M14 correction: query_context's identity/session/
            # capabilities/personalization sections are, for THIS
            # specific call, verbatim duplicates of what the drafting
            # request already carries elsewhere - identity duplicates
            # policy_text (used as this call's own system prompt via
            # build_drafting_system_prompt), personalization duplicates
            # DraftRequest.personalization below, and session/
            # capabilities add nothing the narrow "explain this
            # already-decided outcome" task needs that outcome itself
            # doesn't already supply. Live testing reproduced the exact
            # failure this caused: with the full ~9.5k-character policy
            # text duplicated into the prompt, the drafting model
            # reliably ignored the real outcome.response evidence it
            # was given and invented an unrelated "please clarify"
            # reply instead - the identical prompt-bulk sensitivity
            # already fixed once for the reasoning gateway (see
            # _run_model_reasoning) and once for its own explanatory
            # addenda (see model_reasoning_adapter.py) - never
            # previously applied here. verified_facts and diagnostics
            # are the genuinely new information in query_context for
            # this call, so those are the sections kept. "soul" is
            # blanked for the identical reason "identity" already is -
            # soul_text is passed to DraftRequest below and already
            # becomes this call's own system prompt.
            query_context = dict(query_context)
            query_context["identity"] = ""
            query_context["soul"] = ""
            query_context["session"] = {}
            query_context["capabilities"] = []
            query_context["personalization"] = {}

            draft_request = DraftRequest(
                user_text=user_text,
                outcome=outcome,
                personalization=personalization_context,
                policy_text=policy_text,
                soul_text=soul_text,
                query_context=query_context,
            )

            # M15 correction: a transient failure here (a timeout, or
            # the model's own output failing an honesty check just
            # once) previously discarded the Brain's chance to answer
            # outright - the caller fell straight through to whatever
            # generic fallback it had, even though a real, already-
            # produced tool result (outcome) was sitting right there
            # unexplained. One bounded retry costs nothing on the
            # common case (the first attempt almost always succeeds)
            # and measurably reduces how often a real result goes
            # unexplained to a transient hiccup - never a redesign,
            # still the exact same real model producing the exact
            # same kind of answer, just given one more real chance at
            # it before this method gives up.
            attempts_remaining = 2
            last_error = None
            validated = None

            while attempts_remaining > 0 and validated is None:

                attempts_remaining -= 1

                try:
                    draft = draft_response(
                        draft_request,
                        provider=self.response_drafting_provider,
                    )
                    validated = validate_drafted_response(draft, outcome)

                except (
                    ResponseDraftingError,
                    ResponseValidationError,
                ) as exc:
                    last_error = exc

            if validated is None:
                raise last_error

        except (ResponseDraftingError, ResponseValidationError) as exc:

            self._record_narrative_audit_safely(
                session_id=session_id,
                status="narrative_rejected",
                reason=str(exc),
            )

            return

        except Exception as exc:

            self._record_narrative_audit_safely(
                session_id=session_id,
                status="narrative_failed",
                reason=str(exc),
            )

            return

        response["narrative"] = validated

        self._record_narrative_audit_safely(
            session_id=session_id,
            status="narrative_accepted",
        )

    def _record_narrative_audit_safely(
        self, session_id, status, reason=None
    ):
        """Never raises - matches every other audit-recording helper
        in this codebase (see _record_growth_event_safely,
        ApprovalGate._record_audit_safely)."""

        try:

            metadata = {"reason": reason[:200]} if reason else {}

            self.audit_trail.record(
                event_type="response_narrative",
                status=status,
                session_id=session_id,
                metadata=metadata,
            )

        except Exception:
            return

    # ==========================================================
    # SKILL ROUTER SHADOW
    # ==========================================================

    def _run_skill_router_shadow(
        self,
        user_text
    ):
        """
        Run the Skill Router V1 (ContextBudget -> SkillEvaluator)
        pipeline as a shadow evaluation only.

        It cannot execute anything. It cannot replace the
        deterministic CapabilityPlanner. Its result is attached to
        the response for observability and recorded via AuditTrail
        so the router's picks can be compared against
        CapabilityPlanner's picks before any migration decision is
        made.
        """

        if not self.enable_skill_router_shadow:

            return {
                "status":
                    "shadow_disabled"
            }

        try:

            context_budget_output = (
                self.context_budget.build_context(
                    request_text=user_text
                )
            )

            result = (
                self.skill_evaluator
                .evaluate_from_context_budget(
                    user_request=user_text,
                    context_budget_output=
                        context_budget_output
                )
            )

            return {
                "status":
                    "shadow_completed",

                "result":
                    result
            }

        except Exception as exc:

            return {
                "status":
                    "shadow_failed",

                "error":
                    str(exc)
            }

    def _record_skill_router_audit(
        self,
        session_id,
        skill_router_shadow,
        comparison_tool_name
    ):
        """
        Record a single, small audit event comparing the Skill
        Router V1 shadow's pick against the tool actually selected
        on this turn (by SkillMemory or CapabilityPlanner).

        Never raises - a failure to audit must not break the live
        request the shadow is only observing.
        """

        try:

            shadow_status = skill_router_shadow.get(
                "status"
            )

            router_capability = None
            router_destination = None

            if shadow_status == "shadow_completed":

                result = skill_router_shadow.get(
                    "result",
                    {}
                )

                best_match = result.get(
                    "best_match"
                )

                if isinstance(best_match, dict):
                    router_capability = best_match.get(
                        "name"
                    )

                routing_recommendation = result.get(
                    "routing_recommendation",
                    {}
                )

                router_destination = (
                    routing_recommendation.get(
                        "destination"
                    )
                )

            self.audit_trail.record(
                event_type=
                    "skill_router_shadow_evaluation",

                status=shadow_status or "unknown",

                session_id=session_id,

                capability=router_capability,

                metadata={
                    "router_destination":
                        str(router_destination),

                    "planner_tool_name":
                        str(comparison_tool_name),

                    "agrees_with_planner":
                        router_capability
                        == comparison_tool_name
                }
            )

        except Exception:
            return

    def _record_model_reasoning_audit(
        self,
        session_id,
        model_reasoning_shadow,
        comparison_tool_name,
        used_as_plan
    ):
        """
        Records one audit event per turn describing this turn's model
        reasoning outcome: what it proposed, what the deterministic
        fallback (SkillMemory/CapabilityPlanner) would have picked
        instead (comparison_tool_name), and - as of Milestone 11 Phase
        1 - whether the proposal actually became the real plan
        (used_as_plan) rather than only ever being an audit
        comparison. Before this milestone every event here was purely
        observational by construction; that is no longer universally
        true, so "agrees_with_planner"/used_as_plan together are what
        make this event honest about which one actually decided
        execution on a given turn, instead of always implying the
        deterministic planner did.

        Nothing is recorded when there was no model configured to
        propose anything (model_reasoning_gateway.model_callable is
        None, the default everywhere except where a real
        ModelProvider-backed callable has been explicitly wired in) -
        there is nothing to record in that case.

        Never raises - a failure to audit must never break the live
        request, whether or not this turn's proposal was actually used.
        """

        try:

            reasoning_status = model_reasoning_shadow.get(
                "status"
            )

            if reasoning_status != "reasoning_completed":
                return

            result = model_reasoning_shadow.get(
                "result",
                {}
            )

            model_proposal_status = result.get(
                "status"
            )

            if model_proposal_status == "model_not_configured":
                return

            model_capability = None

            proposal = result.get(
                "proposal"
            )

            if isinstance(proposal, dict):

                action = proposal.get(
                    "action"
                )

                if isinstance(action, dict):
                    model_capability = action.get(
                        "capability"
                    )

            self.audit_trail.record(
                event_type=
                    "model_reasoning_shadow_evaluation",

                status=model_proposal_status or "unknown",

                session_id=session_id,

                capability=model_capability,

                metadata={
                    "planner_tool_name":
                        str(comparison_tool_name),

                    "agrees_with_planner":
                        model_capability
                        == comparison_tool_name,

                    # Milestone 11 Phase 1: True only when this
                    # proposal (not SkillMemory/CapabilityPlanner) was
                    # the actual source of process_user_input's plan -
                    # see _model_proposed_capability. False whenever a
                    # learned skill took priority, the proposal was
                    # rejected/absent, or it named a workflow rather
                    # than a single action.
                    "used_as_plan":
                        bool(used_as_plan)
                }
            )

        except Exception:
            return

    # ==========================================================
    # EVIDENCE
    # ==========================================================

    def _get_evidence_processor(self):

        if self.evidence_processor is None:

            self.evidence_processor = (
                EvidenceProcessor()
            )

        return self.evidence_processor

    def _create_workflow_executor(
        self,
        session,
        session_id=None,
        workflow=None
    ):
        """Milestone 11 Phase 2: workflow is optional and additive -
        every existing caller that omits it (or passes a
        WorkflowPlanner-built workflow, which never carries
        "source": "model_reasoning") gets exactly the pre-Phase-2
        WorkflowCapabilityRouter-backed executor below, unchanged.
        Only a workflow this orchestrator itself built via
        _build_model_workflow gets the generic, capability-name-keyed
        executor instead - required so resuming a paused Brain-
        composed workflow (see _resume_active_workflow) rebuilds the
        SAME kind of executor it was originally created with, not the
        abstract-pipeline-stage one."""

        if self.workflow_executor is not None:

            return self.workflow_executor

        if (
            isinstance(workflow, dict)
            and workflow.get("source") == "model_reasoning"
        ):

            return self._build_model_workflow_executor(
                workflow=workflow,
                session_id=session_id,
            )

        router = WorkflowCapabilityRouter(
            dispatcher=self.approval_gate,
            session=session,
            evidence_processor=(
                self._get_evidence_processor()
            )
        )

        return router.create_executor()

    # ==========================================================
    # PERSISTENCE
    # ==========================================================

    def _persist_session(
        self,
        session_id
    ):

        self.session_manager.save_session(
            session_id
        )

    # ==========================================================
    # WORKFLOW STATE
    # ==========================================================

    def _save_paused_workflow(
        self,
        session,
        execution_result
    ):

        workflow = (
            execution_result.get(
                "workflow"
            )
        )

        # ------------------------------------------------------
        # A workflow produced by the current execution path is
        # no longer considered a recovered workflow.
        # ------------------------------------------------------

        session.active_workflow_recovered = False

        session.active_workflow = workflow

        session.active_workflow_status = (
            execution_result.get(
                "status"
            )
        )

        session.active_workflow_required_field = (
            execution_result.get(
                "required_field"
            )
            or
            session.last_question_field
        )

        session.active_workflow_question = (
            execution_result.get(
                "message"
            )
        )

    def _clear_active_workflow(
        self,
        session
    ):

        session.active_workflow = None

        session.active_workflow_status = None

        session.active_workflow_required_field = None

        session.active_workflow_question = None

    # ==========================================================
    # WORKFLOW RECOVERY
    # ==========================================================

    def _recover_active_workflow(
        self,
        session,
        session_id
    ):

        workflow = session.active_workflow

        # ------------------------------------------------------
        # IMPORTANT LIFECYCLE RULE
        #
        # Only workflows restored from persistent storage enter
        # crash/restart recovery.
        #
        # A workflow created directly in the current process is
        # handled by the normal resume path.
        # ------------------------------------------------------

        if not getattr(
            session,
            "active_workflow_recovered",
            False
        ):

            return None

        validation = (
            WorkflowRecoveryValidator.validate(
                workflow
            )
        )

        recovery = (
            WorkflowRecoveryValidator.recovery_action(
                workflow
            )
        )

        action = recovery.get(
            "action"
        )

        recovery_metadata = dict(
            recovery
        )

        recovery_metadata[
            "validation"
        ] = validation

        # ------------------------------------------------------
        # INVALID RESTORED WORKFLOW
        # ------------------------------------------------------

        if (
            not validation.get(
                "valid",
                False
            )
            or
            action == "reject"
        ):

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_rejected",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "URI rejected the persisted workflow "
                            "because its recovery state is invalid."
                        ),

                    "workflow":
                        workflow,

                    "recovery":
                        recovery_metadata
                }
            }

        # ------------------------------------------------------
        # WAITING FOR INPUT
        #
        # Valid restored paused workflows re-enter the established
        # clarification/resume lifecycle.
        # ------------------------------------------------------

        if (
            action == "resume"
            and
            session.active_workflow_status
            == "waiting_for_input"
        ):

            return None

        # ------------------------------------------------------
        # PLANNED WORKFLOW
        # ------------------------------------------------------

        if action == "resume":

            return None

        # ------------------------------------------------------
        # COMPLETED WORKFLOW
        # ------------------------------------------------------

        if action == "already_complete":

            self._clear_active_workflow(
                session
            )

            self._persist_session(
                session_id
            )

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "already_complete",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow was already completed. "
                            "URI will not re-execute it."
                        ),

                    "workflow":
                        workflow
                }
            }

        # ------------------------------------------------------
        # RUNNING WORKFLOW
        # ------------------------------------------------------

        if action == "recovery_review":

            session.active_workflow_status = (
                "recovery_review"
            )

            self._persist_session(
                session_id
            )

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_review",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow was running when URI "
                            "recovered. Automatic replay is blocked "
                            "pending recovery review."
                        ),

                    "workflow":
                        workflow,

                    "recovery_required":
                        True
                }
            }

        # ------------------------------------------------------
        # FAILED WORKFLOW
        # ------------------------------------------------------

        if action == "failed":

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_failed",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow previously failed. "
                            "URI will not retry it automatically."
                        ),

                    "workflow":
                        workflow,

                    "retry_required":
                        True
                }
            }

        # ------------------------------------------------------
        # BLOCKED WORKFLOW
        # ------------------------------------------------------

        if action == "blocked":

            return {
                "status":
                    "success",

                "workflow":
                    workflow,

                "execution": {
                    "status":
                        "recovery_blocked",

                    "recovery":
                        recovery_metadata,

                    "reason":
                        recovery.get(
                            "reason"
                        ),

                    "validation":
                        validation
                },

                "response": {
                    "message":
                        (
                            "This workflow is blocked and "
                            "requires resolution before it can continue."
                        ),

                    "workflow":
                        workflow
                }
            }

        return {
            "status":
                "success",

            "workflow":
                workflow,

            "execution": {
                "status":
                    "recovery_rejected",

                "recovery": {
                    "action":
                        "reject",

                    "reason":
                        (
                            "Unknown recovery action returned by "
                            "WorkflowRecoveryValidator."
                        ),

                    "validation":
                        validation
                },

                "reason":
                    (
                        "Unknown recovery action returned by "
                        "WorkflowRecoveryValidator."
                    ),

                "validation":
                    validation
            },

            "response": {
                "message":
                    (
                        "URI could not determine a safe recovery "
                        "action for the persisted workflow."
                    ),

                "workflow":
                    workflow
            }
        }

    # ==========================================================
    # RESUME ACTIVE WORKFLOW
    # ==========================================================

    def _resume_active_workflow(
        self,
        session,
        session_id,
        user_text
    ):

        required_field = (
            session.active_workflow_required_field
            or
            session.last_question_field
        )

        if required_field:

            # The recovered workflow is now re-entering the
            # normal in-process execution lifecycle.
            session.active_workflow_recovered = False

            new_fact = Fact(
                name=required_field,
                value=user_text.strip(),
                status="CONFIRMED",
                source="User clarification"
            )

            update_fact(
                session,
                new_fact
            )

            session.last_question_field = None

            self._persist_session(
                session_id
            )

        workflow_executor = (
            self._create_workflow_executor(
                session,
                session_id=session_id,
                workflow=session.active_workflow,
            )
        )

        execution_result = (
            workflow_executor.execute(
                session.active_workflow
            )
        )

        execution_status = (
            execution_result.get(
                "status"
            )
        )

        if execution_status == "success":

            completed_workflow = (
                execution_result.get(
                    "workflow"
                )
            )

            self._clear_active_workflow(
                session
            )

            self._persist_session(
                session_id
            )

            return {
                "status":
                    "success",

                "workflow":
                    completed_workflow,

                "execution":
                    execution_result,

                "response": {
                    "message":
                        "URI completed the resumed workflow.",

                    "workflow":
                        completed_workflow,

                    "execution_log":
                        execution_result.get(
                            "execution_log"
                        )
                }
            }

        if execution_status == "waiting_for_input":

            self._save_paused_workflow(
                session,
                execution_result
            )

            self._persist_session(
                session_id
            )

            return {
                "status":
                    "success",

                "workflow":
                    execution_result.get(
                        "workflow"
                    ),

                "execution":
                    execution_result,

                "response": {
                    "message":
                        execution_result.get(
                            "message",
                            "URI requires additional information before continuing."
                        ),

                    "required_information":
                        session.active_workflow_required_field
                }
            }

        self._clear_active_workflow(
            session
        )

        self._persist_session(
            session_id
        )

        return {
            "status":
                "success",

            "workflow":
                execution_result.get(
                    "workflow"
                ),

            "execution":
                execution_result,

            "response": {
                "message":
                    "URI could not complete the resumed workflow.",

                "error":
                    execution_result.get(
                        "error"
                    )
            }
        }

    # ==========================================================
    # MAIN USER INPUT
    # ==========================================================

    def process_user_input(
        self,
        session_id: str,
        user_text: str,
        personalization_context: dict = None
    ) -> dict:
        """Public entry point. Runs the unchanged core turn logic, then
        records the exchange to the durable conversation transcript (M18).
        The recording is best-effort and strictly after the outcome is
        decided - it can never change what happened, only note it - so a
        transcript-store failure never affects the returned result."""

        result = self._process_user_input_core(
            session_id=session_id,
            user_text=user_text,
            personalization_context=personalization_context,
        )

        self._record_conversation_turn_safely(
            session_id=session_id,
            user_text=user_text,
            result=result,
        )

        return result

    def _record_conversation_turn_safely(
        self,
        session_id: str,
        user_text: str,
        result: dict,
    ) -> None:
        """Append one {user_text, response, status, capability, attachments}
        turn to the transcript. Never raises."""
        try:
            if not isinstance(result, dict):
                return

            response = result.get("response")
            if isinstance(response, dict):
                response_text = (
                    result.get("narrative")
                    or response.get("message")
                    or response.get("note_sheet")
                    or ""
                )
            else:
                response_text = result.get("narrative") or (response or "")

            execution = result.get("execution")
            status = None
            capability = None
            if isinstance(execution, dict):
                status = execution.get("status")
                capability = execution.get("tool") or execution.get("capability")
            if status is None:
                status = result.get("status")

            attachments = []
            try:
                attachments = [
                    record.to_reference()
                    for record in self.file_store.list_for_session(session_id)
                ] if session_id else []
            except Exception:
                attachments = []

            self.conversation_history.append_turn(
                session_id=session_id,
                turn_id=f"turn-{datetime.now(timezone.utc).timestamp()}",
                user_text=user_text,
                response_text=str(response_text),
                status=status,
                capability=capability,
                attachments=attachments,
            )
        except Exception:
            # A transcript write must never affect the turn's outcome.
            return

    def _process_user_input_core(
        self,
        session_id: str,
        user_text: str,
        personalization_context: dict = None
    ) -> dict:

        try:

            session = (
                self.session_manager.get_session(
                    session_id
                )
            )

            # --------------------------------------------------
            # Recover any persisted active workflow before normal
            # request processing.
            #
            # The recovery validator is authoritative for persisted
            # workflow state. The model never decides recovery.
            # --------------------------------------------------

            if session.active_workflow is not None:

                recovery_result = (
                    self._recover_active_workflow(
                        session=session,
                        session_id=session_id
                    )
                )

                if recovery_result is not None:

                    recovery_result[
                        "session_id"
                    ] = session_id

                    return recovery_result

            # --------------------------------------------------
            # Resume a previously paused workflow first.
            # --------------------------------------------------

            if (
                session.active_workflow is not None
                and
                session.active_workflow_status
                == "waiting_for_input"
            ):

                resumed = (
                    self._resume_active_workflow(
                        session=session,
                        session_id=session_id,
                        user_text=user_text
                    )
                )

                resumed["session_id"] = session_id

                return resumed

            # --------------------------------------------------
            # Existing deterministic semantic interpretation.
            # --------------------------------------------------

            semantic_result = (
                self.semantic_interpreter.interpret(
                    user_text
                )
            )

            learned_skill = (
                self.skill_memory.find_matching_skill(
                    semantic_result
                )
            )

            # URI Correction Part 1: read-once carry-forward of the
            # immediately preceding turn's Brain attempt history (see
            # state.py's SessionState.last_goal_text/
            # last_goal_attempt_history, and
            # _continue_brain_evaluation_loop below, which is the only
            # writer). Cleared here unconditionally - if this turn
            # doesn't end up Brain-driven either, that history simply
            # isn't carried further rather than growing without bound.
            carried_attempt_history = (
                session.last_goal_attempt_history
            )

            session.last_goal_attempt_history = None
            session.last_goal_text = None

            # Milestone 13 Part 2: a small, generic label telling the
            # Brain WHY there is carried history to consider, without
            # URI itself deciding what that history means. "the most
            # recent entry's result was awaiting_user_response" is a
            # plain, generic fact about the carried record's own shape
            # (see _apply_clarification_pause) - not a judgment about
            # the user's new message.
            interaction_signal = None

            if carried_attempt_history:

                try:
                    last_carried = carried_attempt_history[-1]
                    last_result = (
                        last_carried.get("result")
                        if isinstance(last_carried, dict)
                        else None
                    )
                    if (
                        isinstance(last_result, dict)
                        and last_result.get("status")
                        == "awaiting_user_response"
                    ):
                        interaction_signal = "MISSING_INFORMATION"
                    else:
                        interaction_signal = (
                            "RESULT_NOT_ACCEPTED_OR_INCOMPLETE"
                        )
                except Exception:
                    interaction_signal = (
                        "RESULT_NOT_ACCEPTED_OR_INCOMPLETE"
                    )

            # --------------------------------------------------
            # Run model reasoning (Milestone 11 Phase 1).
            #
            # It still never executes anything itself. Its result MAY
            # become the real plan for the direct single-capability
            # path below (see _model_proposed_capability) when it
            # proposes a registered capability that
            # ModelReasoningGateway.validate_proposal() already
            # accepted - otherwise CapabilityPlanner remains the
            # fallback, exactly as before this milestone.
            # --------------------------------------------------

            model_reasoning = (
                self._run_model_reasoning(
                    user_text=user_text,
                    session=session,
                    session_id=session_id,
                    personalization_context=personalization_context,
                    attempt_history=carried_attempt_history,
                    learned_skill=learned_skill,
                    interaction_signal=interaction_signal
                )
            )

            # --------------------------------------------------
            # NEW:
            # Run the Skill Router V1 (ContextBudget ->
            # SkillEvaluator) pipeline as a shadow evaluation only.
            #
            # It cannot execute anything.
            # It cannot replace the deterministic planner.
            # --------------------------------------------------

            skill_router_shadow = (
                self._run_skill_router_shadow(
                    user_text=user_text
                )
            )

            # The deterministic fallback pick - what would have
            # executed without any Brain involvement at all. Computed
            # once and reused both as the comparison baseline for the
            # audit events below and, when nothing overrides it, as
            # the actual fallback plan further down - never
            # recomputed.
            capability_planner_plan = (
                self.capability_planner.plan(
                    semantic_result
                )
            )

            comparison_tool_name = (
                learned_skill.get("tool_name")
                if learned_skill
                else capability_planner_plan.get("tool_name")
            )

            # A validated, registered-capability proposal from model
            # reasoning (Milestone 11 Phase 1) - None whenever there is
            # nothing usable to promote to a real plan (see
            # _model_proposed_capability's own docstring for every
            # reason that can be).
            model_capability_proposal = (
                self._model_proposed_capability(
                    model_reasoning
                )
            )

            # URI Correction Part 1: a fresh Brain workflow proposal
            # also takes priority over a learned skill, exactly like a
            # fresh single-action proposal does - checked here (cheap,
            # pure, re-checked again inside the planning_required
            # branch below where the actual workflow is built) purely
            # to decide priority, not to build anything yet.
            model_workflow_proposal = (
                self._model_proposed_workflow(
                    model_reasoning
                )
            )

            model_workflow_proposal_present = (
                model_workflow_proposal is not None
            )

            self._record_skill_router_audit(
                session_id=session_id,
                skill_router_shadow=skill_router_shadow,
                comparison_tool_name=comparison_tool_name
            )

            self._record_model_reasoning_audit(
                session_id=session_id,
                model_reasoning_shadow=model_reasoning,
                comparison_tool_name=comparison_tool_name,
                used_as_plan=(
                    model_capability_proposal is not None
                    or model_workflow_proposal_present
                )
            )

            response = {
                "status":
                    "success",

                "session_id":
                    session_id,

                "semantic_analysis":
                    semantic_result,

                "model_reasoning":
                    model_reasoning,

                "skill_router_shadow":
                    skill_router_shadow,

                "learned_skill":
                    learned_skill,

                "plan":
                    None,

                "workflow":
                    None,

                "execution":
                    None,

                "response":
                    None
            }

            # --------------------------------------------------
            # Milestone 13 Part 1: pre-execution Brain sanity check.
            #
            # Canonical loop: BRAIN FORMULATES PLAN -> URI PROVIDES
            # RELEVANT CONTEXT -> URI asks BRAIN "is this really what
            # the user needs?" -> BRAIN RE-EVALUATES -> BRAIN CONFIRMS/
            # MODIFIES/REPLACES -> URI EXECUTES. Only runs when the
            # Brain actually formulated a plan (a single capability or
            # a workflow) on its first call - a Brain proposal of
            # nothing at all is unaffected, falling through to the
            # existing learned-skill/CapabilityPlanner/WorkflowPlanner
            # path exactly as before this milestone. Nothing has
            # executed yet at this point either way - this only
            # decides which proposal execution will use.
            # --------------------------------------------------

            if (
                model_capability_proposal is not None
                or model_workflow_proposal_present
            ):

                pre_execution_check = (
                    self._run_pre_execution_sanity_check(
                        user_text=user_text,
                        session=session,
                        session_id=session_id,
                        personalization_context=personalization_context,
                        learned_skill=learned_skill,
                        model_capability_proposal=model_capability_proposal,
                        model_workflow_proposal=model_workflow_proposal,
                    )
                )

                self._record_pre_execution_sanity_check_audit(
                    session_id=session_id,
                    outcome=pre_execution_check["status"],
                )

                response["pre_execution_check"] = {
                    "outcome": pre_execution_check["status"],
                }

                if pre_execution_check["status"] == "revised_or_confirmed":

                    # Whatever the Brain now says - confirmed unchanged
                    # or genuinely modified/replaced - becomes the
                    # proposal every downstream branch (single-action
                    # or workflow-building) independently re-derives
                    # from model_reasoning, with no further change
                    # needed to any of that existing code.
                    model_reasoning = pre_execution_check["model_reasoning"]
                    response["model_reasoning"] = model_reasoning

                    model_capability_proposal = (
                        self._model_proposed_capability(model_reasoning)
                    )
                    model_workflow_proposal = (
                        self._model_proposed_workflow(model_reasoning)
                    )
                    model_workflow_proposal_present = (
                        model_workflow_proposal is not None
                    )

                elif pre_execution_check["status"] == "clarification_needed":

                    question = (
                        pre_execution_check["clarification"]["question"]
                    )

                    return self._apply_clarification_pause(
                        response,
                        question,
                        stage="pre_execution_check",
                        session=session,
                        session_id=session_id,
                        user_text=user_text,
                    )

                # "unavailable": the sanity check itself produced
                # nothing usable - keep the ORIGINAL proposal exactly
                # as first formulated, never discarding an
                # already-valid Brain decision because this second
                # call could not run.

            else:

                # Milestone 13 Part 1: the Brain's very FIRST call may
                # already have decided it needs more information
                # rather than formulating a plan at all (action and
                # workflow both null, clarification given instead).
                # Before this fix, that clarification was silently
                # discarded and URI fell straight through to the
                # deterministic CapabilityPlanner/WorkflowPlanner
                # fallback, which could confidently select and execute
                # a capability the Brain had explicitly said it did not
                # yet have enough information to use responsibly - live
                # testing surfaced exactly this (a missing roll number
                # correctly flagged by the Brain, then silently
                # overridden). The Brain's own "I need more
                # information" decision is honored the same way
                # regardless of which call it came from.
                initial_clarification = self._model_clarification(
                    model_reasoning
                )

                if initial_clarification is not None:

                    return self._apply_clarification_pause(
                        response,
                        initial_clarification["question"],
                        stage="initial_reasoning",
                        session=session,
                        session_id=session_id,
                        user_text=user_text,
                    )

            # --------------------------------------------------
            # Capability selection.
            #
            # URI Correction Part 1: a learned skill is REFERENCE ONLY
            # (surfaced to the Brain as "learned_skill_reference" in
            # _run_model_reasoning's session_context above) - it must
            # never automatically override a fresh Brain proposal for
            # THIS request. A fresh, validated Brain proposal (single
            # action or workflow) therefore takes priority; a learned
            # skill remains a genuine, still fully re-executed and
            # re-authorized fallback whenever the Brain has nothing
            # usable to offer (disabled, unavailable, or its proposal
            # didn't validate) - never short-circuited past approval
            # either way. A stale/renamed learned tool_name correctly
            # surfaces the dispatcher's real "URI lacks the
            # capability" error instead of a false "recognized"
            # message, for the same reason as before.
            #
            # CapabilityPlanner.plan() remains the last, purely
            # deterministic fallback whenever there is no learned
            # skill and no usable model proposal either.
            #
            # In every branch, only a plain capability-name string
            # crosses into "plan" - the model's proposed arguments/
            # reason text are never used, and this plan is still routed
            # through the exact same capability_selected branch below
            # (ApprovalGate.execute_tool, unmodified): approval
            # requirements, execution, and persistence are decided
            # exactly as they always have been, regardless of which of
            # these sources chose the tool_name.
            # --------------------------------------------------

            if model_capability_proposal is not None:

                plan = {
                    "status":
                        "capability_selected",

                    "tool_name":
                        model_capability_proposal,

                    "reason":
                        "Brain-proposed capability, already validated "
                        "against the registered capability catalogue "
                        "by ModelReasoningGateway before being used as "
                        "the plan.",

                    "source":
                        "model_reasoning"
                }

            elif model_workflow_proposal_present:

                # Defers to the existing, unmodified workflow branch
                # below (which independently re-derives and re-
                # validates the actual workflow via
                # _model_proposed_workflow) - this only ensures a
                # fresh Brain workflow proposal is not preempted by a
                # learned skill either, exactly like a single-action
                # proposal.
                plan = {
                    "status": "planning_required",
                    "tool_name": None,
                    "reason": (
                        "Brain proposed a multi-step workflow for "
                        "this request."
                    ),
                    "source": "model_reasoning",
                }

            elif learned_skill:

                plan = {
                    "status":
                        "capability_selected",

                    "tool_name":
                        learned_skill.get(
                            "tool_name"
                        ),

                    "reason":
                        "No fresh Brain proposal was usable for this "
                        "request; matched a previously learned "
                        "workflow for this task type/domain instead - "
                        "still executed and authorized like a fresh "
                        "selection.",

                    "source":
                        "skill_memory",

                    "success_count":
                        learned_skill.get(
                            "success_count",
                            0
                        )
                }

            else:

                plan = capability_planner_plan

            response["plan"] = plan

            # --------------------------------------------------
            # Direct registered capability.
            # --------------------------------------------------

            if (
                plan.get(
                    "status"
                )
                == "capability_selected"
            ):

                tool_name = (
                    plan.get(
                        "tool_name"
                    )
                )

                dispatch_result = (
                    self.approval_gate.execute_tool(
                        tool_name,
                        session_id=session_id,
                        request_text=user_text
                    )
                )

                response["execution"] = {
                    "status":
                        dispatch_result.get(
                            "status"
                        ),

                    "tool":
                        tool_name
                }

                response["response"] = (
                    dispatch_result.get(
                        "data",
                        dispatch_result
                    )
                )

                if (
                    dispatch_result.get(
                        "status"
                    )
                    == "success"
                ):

                    workflow = [
                        "interpret_request",
                        "check_skill_memory",
                        "select_registered_capability",
                        f"execute_{tool_name}",
                        "review_result"
                    ]

                    self.skill_memory.learn_skill(
                        semantic_result=
                            semantic_result,

                        workflow=
                            workflow,

                        tool_name=
                            tool_name
                    )

                # M18: a matched skill that then FAILS to execute must
                # lose confidence, so a formerly-good pattern that has
                # gone bad stops being recommended (see
                # skill_memory.CONFIDENCE_RECALL_FLOOR). Only recorded
                # when this turn actually acted on a recalled skill -
                # never for an ordinary planner selection, and never on
                # an approval-pending (not-yet-executed) result.
                elif (
                    learned_skill is not None
                    and dispatch_result.get("status") not in (
                        "success",
                        "awaiting_approval",
                        "awaiting_user_response",
                    )
                ):
                    try:
                        self.skill_memory.record_failure(
                            semantic_result=semantic_result,
                            tool_name=tool_name,
                        )
                    except Exception:
                        pass

                # Milestone 11 Part 2: only a Brain-proposed plan gets
                # re-evaluated - a learned skill or a CapabilityPlanner
                # selection is untouched, exactly as before. No-ops
                # immediately if this result is still awaiting
                # approval.
                if plan.get("source") == "model_reasoning":

                    self._continue_brain_evaluation_loop(
                        user_text=user_text,
                        session=session,
                        session_id=session_id,
                        personalization_context=personalization_context,
                        response=response,
                        first_proposal_description={
                            "type": "capability",
                            "capability": tool_name,
                        },
                    )

                self._draft_narrative_safely(
                    user_text=user_text,
                    response=response,
                    personalization_context=personalization_context,
                    session_id=session_id
                )

                self._persist_session(
                    session_id
                )

                return response

            # --------------------------------------------------
            # Dynamic workflow path.
            # --------------------------------------------------

            if (
                plan.get(
                    "status"
                )
                == "planning_required"
            ):

                # ----------------------------------------------
                # Deterministic "no capability required" check.
                #
                # Some requests (a greeting, a thank-you, a bare
                # question about what URI can do) genuinely need no
                # registered capability at all. Without this check,
                # every one of these would fall into the generic
                # workflow below and fail at prepare_output with a
                # capability-gap message - correct for a genuine gap,
                # dishonest here. See conversational_classifier.py's
                # module docstring for the exact discriminator and why
                # it is safe: it never touches genuine capability-gap
                # requests (verified against test_capability_planner.py's
                # own "optimize my pc" fixtures), never calls
                # self.approval_gate, never dispatches a tool, and
                # never lets the model decide - only the user's own raw
                # text plus a fail-closed check on the semantic
                # interpreter's structured entities/requires_evidence/
                # requires_clarification fields.
                # ----------------------------------------------

                if is_conversational_no_capability_required(
                    user_text, semantic_result
                ):

                    response["execution"] = {
                        "status": "success"
                    }

                    response["response"] = {
                        "message": NO_CAPABILITY_REQUIRED_MESSAGE
                    }

                    self._draft_narrative_safely(
                        user_text=user_text,
                        response=response,
                        personalization_context=personalization_context,
                        session_id=session_id
                    )

                    self._persist_session(
                        session_id
                    )

                    return response

                # ----------------------------------------------
                # Brain-composed workflow (Milestone 11 Phase 2).
                #
                # When ModelReasoningGateway proposed a multi-step
                # workflow and it survives re-confirmation against the
                # authoritative CapabilityRegistry (see
                # _model_proposed_workflow), it is preferred over the
                # deterministic WorkflowPlanner/WorkflowCapabilityRouter
                # pipeline below for THIS planning_required turn. Every
                # step still executes only through
                # self.approval_gate.execute_tool() (see
                # _build_model_workflow_executor) - never
                # self.dispatcher directly - so approval requirements
                # are enforced exactly as they already are for the
                # direct single-capability path and the deterministic
                # workflow path. Absent, invalid, or unsupported (e.g.
                # an unregistered capability, no model configured)
                # falls through unchanged to today's WorkflowPlanner
                # path immediately below.
                # ----------------------------------------------

                model_workflow_proposal = (
                    self._model_proposed_workflow(
                        model_reasoning
                    )
                )

                raw_workflow_proposed = False

                try:
                    raw_workflow_proposed = isinstance(
                        model_reasoning.get("result", {})
                        .get("proposal", {})
                        .get("workflow"),
                        dict,
                    )
                except Exception:
                    raw_workflow_proposed = False

                if model_workflow_proposal is not None:

                    self._record_model_workflow_audit(
                        session_id=session_id,
                        workflow_proposed=raw_workflow_proposed,
                        workflow_valid=True,
                        used_as_plan=True,
                    )

                    workflow = self._build_model_workflow(
                        model_workflow_proposal
                    )

                    response["workflow"] = workflow

                    response["plan"] = {
                        "status": "planning_required",
                        "tool_name": None,
                        "reason": (
                            "Brain-proposed multi-step workflow - "
                            "every step's capability already "
                            "re-confirmed against the registered "
                            "capability catalogue before execution."
                        ),
                        "source": "model_reasoning",
                    }

                    workflow_executor = (
                        self._create_workflow_executor(
                            session,
                            session_id=session_id,
                            workflow=workflow,
                        )
                    )

                    execution_result = (
                        workflow_executor.execute(
                            workflow
                        )
                    )

                    response["execution"] = execution_result

                    execution_status = execution_result.get(
                        "status"
                    )

                    if execution_status == "success":

                        self._clear_active_workflow(session)
                        self._persist_session(session_id)

                        response["response"] = {
                            "message":
                                "URI completed the Brain-composed "
                                "workflow.",
                            "workflow":
                                execution_result.get("workflow"),
                            "execution_log":
                                execution_result.get("execution_log"),
                        }

                        self._continue_brain_evaluation_loop(
                            user_text=user_text,
                            session=session,
                            session_id=session_id,
                            personalization_context=(
                                personalization_context
                            ),
                            response=response,
                            first_proposal_description={
                                "type": "workflow",
                                "steps": [
                                    step["capability"]
                                    for step in workflow.get(
                                        "steps", []
                                    )
                                ],
                            },
                        )

                        return response

                    if execution_status == "waiting_for_input":

                        self._save_paused_workflow(
                            session, execution_result
                        )
                        self._persist_session(session_id)

                        response["response"] = {
                            "message": session.active_workflow_question,
                            "workflow": session.active_workflow,
                            "required_information":
                                session.active_workflow_required_field,
                        }

                        return response

                    self._clear_active_workflow(session)
                    self._persist_session(session_id)

                    response["response"] = {
                        "message":
                            "URI could not complete the "
                            "Brain-composed workflow.",
                        "workflow":
                            execution_result.get("workflow"),
                        "error":
                            execution_result.get("error"),
                    }

                    self._continue_brain_evaluation_loop(
                        user_text=user_text,
                        session=session,
                        session_id=session_id,
                        personalization_context=(
                            personalization_context
                        ),
                        response=response,
                        first_proposal_description={
                            "type": "workflow",
                            "steps": [
                                step["capability"]
                                for step in workflow.get("steps", [])
                            ],
                        },
                    )

                    self._draft_narrative_safely(
                        user_text=user_text,
                        response=response,
                        personalization_context=personalization_context,
                        session_id=session_id
                    )

                    return response

                self._record_model_workflow_audit(
                    session_id=session_id,
                    workflow_proposed=raw_workflow_proposed,
                    workflow_valid=False,
                    used_as_plan=False,
                    fallback_reason=(
                        "no_valid_workflow_proposal"
                        if raw_workflow_proposed
                        else "no_workflow_proposed"
                    ),
                )

                workflow_plan = (
                    self.workflow_planner.create_workflow(
                        semantic_result=
                            semantic_result,

                        request_text=
                            user_text
                    )
                )

                workflow = (
                    workflow_plan.get(
                        "workflow"
                    )
                )

                response["workflow"] = workflow

                workflow_executor = (
                    self._create_workflow_executor(
                        session
                    )
                )

                execution_result = (
                    workflow_executor.execute(
                        workflow
                    )
                )

                response["execution"] = (
                    execution_result
                )

                execution_status = (
                    execution_result.get(
                        "status"
                    )
                )

                if execution_status == "success":

                    self._clear_active_workflow(
                        session
                    )

                    self._persist_session(
                        session_id
                    )

                    response["response"] = {
                        "message":
                            "URI completed the planned workflow.",

                        "workflow":
                            execution_result.get(
                                "workflow"
                            ),

                        "execution_log":
                            execution_result.get(
                                "execution_log"
                            )
                    }

                    return response

                if (
                    execution_status
                    == "waiting_for_input"
                ):

                    self._save_paused_workflow(
                        session,
                        execution_result
                    )

                    self._persist_session(
                        session_id
                    )

                    response["response"] = {
                        "message":
                            session.active_workflow_question,

                        "workflow":
                            session.active_workflow,

                        "required_information":
                            session.active_workflow_required_field
                    }

                    return response

                self._clear_active_workflow(
                    session
                )

                self._persist_session(
                    session_id
                )

                response["response"] = {
                    "message":
                        "URI could not complete the planned workflow.",

                    "workflow":
                        execution_result.get(
                            "workflow"
                        ),

                    "error":
                        execution_result.get(
                            "error"
                        )
                }

                self._draft_narrative_safely(
                    user_text=user_text,
                    response=response,
                    personalization_context=personalization_context,
                    session_id=session_id
                )

                return response

            response["execution"] = {
                "status":
                    "planning_required",

                "tool":
                    None
            }

            response["response"] = {
                "message":
                    "URI understands the request but cannot safely execute it.",

                "suggested_next_step":
                    semantic_result.get(
                        "suggested_next_step"
                    )
            }

            self._persist_session(
                session_id
            )

            return response

        except Exception as exc:

            return {
                "status":
                    "failed",

                "error":
                    str(exc)
            }

    def _resume_model_workflow_after_decision(
        self,
        session_id,
        proposed,
        approved,
        decision_result
    ):
        """Milestone 11 Phase 2.1: when the decided action_id was one
        paused step of a Brain-composed workflow
        (session.active_workflow tagged "source": "model_reasoning"),
        continues that workflow's remaining steps after the decision -
        rather than leaving it permanently stuck "waiting_for_input"
        once its one approval-required action has already been
        irreversibly decided (an ApprovalStore action_id can only ever
        be decided once - see approval_store.py's STATUS_PENDING ->
        STATUS_APPROVED/REJECTED -> STATUS_CONSUMED lifecycle).

        Returns None whenever there is nothing to resume - no
        session_id, no active workflow, not a Brain-composed one, not
        currently paused, or the paused step does not match this
        decision's capability. This covers every existing single-
        capability approval (Milestone 7) and every
        WorkflowCapabilityRouter-backed workflow (none of whose 4 real
        tools require approval today) completely unchanged - only a
        Brain-composed workflow's own paused step can ever match here.

        The approved capability itself is never re-executed: this
        method only records the ALREADY-PRODUCED decision_result
        (self.approval_gate.decide() already executed the underlying
        ToolDispatcher call exactly once, unmodified) onto the
        matching paused step via
        WorkflowExecutor.complete_step_externally(), then calls
        WorkflowExecutor.execute() again to let already-completed
        steps be skipped and any newly-unblocked dependent step run
        for the first time through the same generic, ApprovalGate-
        backed handlers _build_model_workflow_executor already built -
        never a second, independent execution path.

        A rejected or otherwise-failed decision fails the workflow
        closed (WorkflowExecutor.fail_step_externally) instead of
        leaving it stuck waiting on an action_id that can never be
        decided again.

        Never raises: any failure here must never break the
        already-decided approval result the caller (decide_action) is
        returning regardless.
        """

        try:

            if not session_id or proposed is None:
                return None

            session = self.session_manager.get_session(session_id)

            workflow = session.active_workflow

            if not isinstance(workflow, dict):
                return None

            if workflow.get("source") != "model_reasoning":
                return None

            if session.active_workflow_status != "waiting_for_input":
                return None

            paused_step = None

            for step in workflow.get("steps", []):

                if (
                    isinstance(step, dict)
                    and step.get("status") == "waiting_for_input"
                    and step.get("capability")
                    == getattr(proposed, "capability_id", None)
                ):
                    paused_step = step
                    break

            if paused_step is None:
                return None

            workflow_executor = self._create_workflow_executor(
                session,
                session_id=session_id,
                workflow=workflow,
            )

            decision_status = decision_result.get("status")

            if not approved or decision_status not in (
                "success",
                "completed",
            ):

                workflow_executor.fail_step_externally(
                    workflow,
                    paused_step.get("step_id"),
                    error=(
                        "Approval was rejected."
                        if not approved
                        else str(
                            decision_result.get(
                                "message",
                                "Action could not be executed.",
                            )
                        )
                    ),
                )

                self._clear_active_workflow(session)
                self._persist_session(session_id)

                return {
                    "status": "failed",
                    "workflow": workflow,
                }

            completed = workflow_executor.complete_step_externally(
                workflow,
                paused_step.get("step_id"),
                output=decision_result.get("data", decision_result),
            )

            if not completed:
                return None

            execution_result = workflow_executor.execute(workflow)

            execution_status = execution_result.get("status")

            if execution_status == "success":

                self._clear_active_workflow(session)
                self._persist_session(session_id)

            elif execution_status == "waiting_for_input":

                self._save_paused_workflow(session, execution_result)
                self._persist_session(session_id)

            else:

                self._clear_active_workflow(session)
                self._persist_session(session_id)

            return execution_result

        except Exception:
            return None

    def decide_action(
        self,
        action_id: str,
        approved: bool,
        session_id=None,
        personalization_context: dict = None
    ) -> dict:
        """The only entry point for recording a real user decision on
        a proposed action (Milestone 7). Never called from within
        process_user_input itself - only from an explicit, separate
        caller (see server.py's POST /approve / POST /cancel) - so a
        single conversational turn can never approve its own proposal.
        The actual decision is delegated entirely to
        self.approval_gate.decide(), unmodified - it still fails
        closed on any invalid, missing, expired, or mismatched
        approval, and ApprovalGate itself remains completely unaware
        of drafting/model_providers (see its own boundary tests).

        Milestone 8A addition: attempts the same additive,
        shadow-rolled-out response.narrative process_user_input
        already produces (see _draft_narrative_safely, reused
        unchanged here) so an approved/cancelled/failed decision gets
        the same explanatory treatment an initial proposal does,
        instead of only ever showing raw tool output. user_text for
        the drafting call comes from the original proposal's stored
        arguments (ApprovalStore already has this - no new
        client-facing field needed). Always present in the returned
        dict (None when narrative is disabled or fails), matching
        POST /ask's existing contract.
        """

        proposed = self.approval_gate.approval_store.get(action_id)

        original_request_text = (
            proposed.arguments.get("request_text", "")
            if proposed is not None
            else ""
        )

        result = dict(
            self.approval_gate.decide(
                action_id=action_id,
                approved=approved,
                session_id=session_id,
            )
        )

        narrative_context = {
            "execution": {"status": result.get("status")},
            "response": result,
        }

        self._draft_narrative_safely(
            user_text=original_request_text,
            response=narrative_context,
            personalization_context=personalization_context,
            session_id=session_id,
        )

        result["narrative"] = narrative_context.get("narrative")

        # Milestone 11 Phase 2.1: additive only - None (the
        # overwhelming majority of decisions, including every
        # existing single-capability approval) leaves result exactly
        # as it already was.
        workflow_continuation = (
            self._resume_model_workflow_after_decision(
                session_id=session_id,
                proposed=proposed,
                approved=approved,
                decision_result=result,
            )
        )

        if workflow_continuation is not None:
            result["workflow_continuation"] = workflow_continuation

        return result

    # ==========================================================
    # LEGACY COMPATIBILITY METHODS
    # ==========================================================

    def process_message(
        self,
        message,
        session_id="default",
        **kwargs
    ):

        return self.process_user_input(
            session_id=session_id,
            user_text=str(message)
        )

    def process_evidence(
        self,
        query,
        session_id="default",
        **kwargs
    ):

        try:

            session = (
                self.session_manager.get_session(
                    session_id
                )
            )

            processor = (
                self._get_evidence_processor()
            )

            result = (
                processor.process_gmail_query(
                    query=str(query),
                    session=session
                )
            )

            self._persist_session(
                session_id
            )

            return result

        except Exception as exc:

            return {
                "success":
                    False,

                "error":
                    str(exc)
            }