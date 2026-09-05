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
from uri_core.core.workflow_planner import WorkflowPlanner
from uri_core.core.workflow_capability_router import (
    WorkflowCapabilityRouter
)
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

    def _run_model_reasoning_shadow(
        self,
        user_text,
        session
    ):

        if not self.enable_model_reasoning_shadow:

            return {
                "status":
                    "shadow_disabled"
            }

        try:

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
                    )
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

            draft = draft_response(
                DraftRequest(
                    user_text=user_text,
                    outcome=outcome,
                    personalization=personalization_context,
                    policy_text=policy_text,
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
        comparison_tool_name
    ):
        """
        Record a single, small audit event comparing the model
        reasoning shadow's proposed capability against the tool
        actually selected on this turn (by SkillMemory or
        CapabilityPlanner) - mirrors _record_skill_router_audit,
        the same pattern already used to compare Skill Router V1's
        shadow pick.

        Nothing is recorded when the shadow had no model configured
        (model_reasoning_gateway.model_callable is None - the
        default everywhere except where a real ModelProvider-backed
        callable has been explicitly wired in). There is no proposal
        to compare in that case, so a comparison event would only be
        noise.

        Never raises - a failure to audit must not break the live
        request the shadow is only observing.
        """

        try:

            shadow_status = model_reasoning_shadow.get(
                "status"
            )

            if shadow_status != "shadow_completed":
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
                        == comparison_tool_name
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
        session
    ):

        if self.workflow_executor is not None:

            return self.workflow_executor

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
                session
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
            # NEW:
            # Run model reasoning as a shadow proposal only.
            #
            # It cannot execute anything.
            # It cannot replace the deterministic planner.
            # --------------------------------------------------

            model_reasoning = (
                self._run_model_reasoning_shadow(
                    user_text=user_text,
                    session=session
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

            comparison_tool_name = (
                learned_skill.get("tool_name")
                if learned_skill
                else self.capability_planner.plan(
                    semantic_result
                ).get("tool_name")
            )

            self._record_skill_router_audit(
                session_id=session_id,
                skill_router_shadow=skill_router_shadow,
                comparison_tool_name=comparison_tool_name
            )

            self._record_model_reasoning_audit(
                session_id=session_id,
                model_reasoning_shadow=model_reasoning,
                comparison_tool_name=comparison_tool_name
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
            # IMPORTANT:
            # The model proposal is NOT used here yet.
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

            else:

                plan = (
                    self.capability_planner.plan(
                        semantic_result
                    )
                )

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