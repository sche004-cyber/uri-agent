from dataclasses import asdict, is_dataclass

from uri_core.core.prompt_builder import PromptBuilder
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.semantic_interpreter import SemanticInterpreter
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
        enable_model_reasoning_shadow=True
    ):

        self.prompt_builder = PromptBuilder()

        self.dispatcher = ToolDispatcher()

        self.semantic_interpreter = SemanticInterpreter()

        self.skill_memory = SkillMemory()

        self.capability_planner = CapabilityPlanner()

        self.workflow_planner = WorkflowPlanner()

        self.session_manager = SessionManager()

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
            dispatcher=self.dispatcher,
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
        user_text: str
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

            learned_skill = (
                self.skill_memory.find_matching_skill(
                    semantic_result
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
            # Learned workflow remains deterministic.
            # --------------------------------------------------

            if learned_skill:

                response["execution"] = {
                    "status":
                        "workflow_recalled",

                    "source":
                        "skill_memory",

                    "tool":
                        learned_skill.get(
                            "tool_name"
                        ),

                    "workflow":
                        learned_skill.get(
                            "workflow"
                        ),

                    "success_count":
                        learned_skill.get(
                            "success_count",
                            0
                        )
                }

                response["response"] = {
                    "message":
                        "URI recognized this as a previously learned workflow.",

                    "workflow":
                        learned_skill.get(
                            "workflow"
                        )
                }

                self._persist_session(
                    session_id
                )

                return response

            # --------------------------------------------------
            # Existing deterministic capability planner.
            #
            # IMPORTANT:
            # The model proposal is NOT used here yet.
            # --------------------------------------------------

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
                    self.dispatcher.execute_tool(
                        tool_name,
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