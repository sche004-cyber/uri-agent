import json
import os

from dataclasses import asdict, is_dataclass

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
        session_manager=None
    ):

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

        self.skill_memory = SkillMemory()

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
        personalization_context
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

            result = (
                self.model_reasoning_gateway.reason(
                    user_text=user_text,
                    session_context=(
                        self._build_model_session_context(
                            session
                        )
                    ),
                    evidence_context=(
                        self._build_model_evidence_context(
                            session
                        )
                    ),
                    query_context=query_context
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
          - a single action (dynamic, multi-step Brain-proposed
          workflows remain deferred to a later M11 phase; this phase
          only promotes the single-capability path).

        Only a plain capability-name string ever crosses this
        boundary - never the model's proposed arguments/reason text,
        which are never read here or anywhere in process_user_input's
        capability_selected branch. The deterministic runtime still
        supplies the real arguments (request_text=user_text) exactly
        as it always has for a CapabilityPlanner-selected tool - see
        ApprovalGate.execute_tool, unmodified.

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

            if not isinstance(action, dict):
                return None

            capability = action.get("capability")

            if not isinstance(capability, str) or not capability.strip():
                return None

            return capability

        except Exception:
            return None

    def _model_proposed_workflow(
        self,
        model_reasoning
    ):
        """Extracts a usable, registry-validated multi-step workflow
        proposal from _run_model_reasoning's result, or None when
        there is none to use - mirrors _model_proposed_capability for
        the single-action case (Milestone 11 Phase 2).

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
    # UNIFIED QUERY CONTEXT (Milestone 10A)
    # ==========================================================

    def _build_query_context(
        self,
        session_id,
        policy_text,
        personalization_context
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

        return build_query_context(
            policy_text=policy_text,
            personalization=personalization_context,
            session_context=session_context,
            verified_facts=verified_facts,
            capabilities=capabilities,
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

            plan = response.get("plan")

            outcome = {
                "execution": response.get("execution"),
                "response": response.get("response"),
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

            query_context = self._build_query_context(
                session_id=session_id,
                policy_text=policy_text,
                personalization_context=personalization_context,
            )

            draft = draft_response(
                DraftRequest(
                    user_text=user_text,
                    outcome=outcome,
                    personalization=personalization_context,
                    policy_text=policy_text,
                    query_context=query_context,
                ),
                provider=self.response_drafting_provider,
            )

            validated = validate_drafted_response(draft, outcome)

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
                    personalization_context=personalization_context
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

            learned_skill = (
                self.skill_memory.find_matching_skill(
                    semantic_result
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
                    not learned_skill
                    and model_capability_proposal is not None
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
            # Capability selection.
            #
            # A learned skill only ever accelerates/confirms WHICH
            # capability to use - it must never substitute for
            # actually invoking it. "Learned" and "executed
            # successfully now" are not the same thing: reusing the
            # exact same capability_selected branch below (approval
            # gate, dispatcher, narrative, re-learning on success) is
            # what guarantees a learned skill is always genuinely
            # re-executed, and always still goes through approval if
            # the capability requires it, rather than short-circuiting
            # past both. A stale/renamed learned tool_name correctly
            # surfaces the dispatcher's real "URI lacks the
            # capability" error instead of a false "recognized"
            # message, for the same reason.
            #
            # IMPORTANT (Milestone 11 Phase 1):
            # A learned skill still takes priority over a fresh model
            # proposal - it represents a prior, already-successful
            # resolution for this exact task type/domain, and is
            # itself always genuinely re-executed and re-authorized
            # below, never short-circuited. Below that, a validated
            # model proposal (model_capability_proposal - a registered
            # capability name that already passed
            # ModelReasoningGateway.validate_proposal()) IS now used as
            # the real plan for this single-capability path, in place
            # of CapabilityPlanner's keyword-scored pick.
            # CapabilityPlanner.plan() remains the deterministic
            # fallback whenever there is no learned skill and no
            # usable model proposal (model not configured/disabled,
            # proposal rejected as invalid/unregistered, or the model
            # proposed a workflow instead of a single action).
            #
            # In every branch, only a plain capability-name string
            # crosses into "plan" - the model's proposed arguments/
            # reason text are never used, and this plan is still routed
            # through the exact same capability_selected branch below
            # (ApprovalGate.execute_tool, unmodified): approval
            # requirements, execution, and persistence are decided
            # exactly as they always have been, regardless of which of
            # these three sources chose the tool_name.
            # --------------------------------------------------

            if learned_skill:

                plan = {
                    "status":
                        "capability_selected",

                    "tool_name":
                        learned_skill.get(
                            "tool_name"
                        ),

                    "reason":
                        "Matched a previously learned workflow for "
                        "this task type/domain; still executed and "
                        "authorized like a fresh selection.",

                    "source":
                        "skill_memory",

                    "success_count":
                        learned_skill.get(
                            "success_count",
                            0
                        )
                }

            elif model_capability_proposal is not None:

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