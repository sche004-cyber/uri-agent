from uri_core.core.prompt_builder import PromptBuilder
from uri_core.core.dispatcher import ToolDispatcher
from uri_core.core.semantic_interpreter import SemanticInterpreter
from uri_core.core.skill_memory import SkillMemory
from uri_core.core.capability_planner import CapabilityPlanner
from uri_core.core.workflow_planner import WorkflowPlanner
from uri_core.core.workflow_capability_router import (
    WorkflowCapabilityRouter
)
from uri_core.core.workflow_recovery import (
    WorkflowRecoveryValidator
)
from uri_core.core.state import SessionManager
from uri_core.core.facts import Fact
from uri_core.core.fact_manager import update_fact
from uri_core.services.evidence_processor import (
    EvidenceProcessor
)


class UriOrchestrator:

    def __init__(self):

        self.prompt_builder = PromptBuilder()
        self.dispatcher = ToolDispatcher()
        self.semantic_interpreter = SemanticInterpreter()
        self.skill_memory = SkillMemory()
        self.capability_planner = CapabilityPlanner()
        self.workflow_planner = WorkflowPlanner()
        self.session_manager = SessionManager()

        self.evidence_processor = None
        self.workflow_executor = None

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

    def _persist_session(
        self,
        session_id
    ):

        self.session_manager.save_session(
            session_id
        )

    def _save_paused_workflow(
        self,
        session,
        execution_result
    ):

        session.active_workflow = (
            execution_result.get("workflow")
        )

        session.active_workflow_status = (
            execution_result.get("status")
        )

        session.active_workflow_required_field = (
            execution_result.get("required_field")
            or session.last_question_field
        )

        session.active_workflow_question = (
            execution_result.get("message")
        )

    def _clear_active_workflow(
        self,
        session
    ):

        session.active_workflow = None
        session.active_workflow_status = None
        session.active_workflow_required_field = None
        session.active_workflow_question = None

    def _is_legacy_workflow(
        self,
        workflow
    ):

        if not isinstance(workflow, dict):
            return False

        has_workflow_id = bool(
            workflow.get("workflow_id")
        )

        has_schema_version = bool(
            workflow.get("schema_version")
        )

        # A workflow with schema_version but no workflow_id
        # is NOT legacy. It is a malformed durable workflow.
        if (
            has_schema_version
            and not has_workflow_id
        ):
            return False

        # A workflow with workflow_id but without the new
        # durability schema is an older valid URI workflow.
        if (
            has_workflow_id
            and not has_schema_version
        ):
            return True

        # Very old workflows may have neither field.
        if (
            not has_workflow_id
            and not has_schema_version
        ):
            return True

        return False

    def _validate_recovery_workflow(
        self,
        session
    ):

        workflow = session.active_workflow

        if workflow is None:

            return {
                "action": "none",
                "reason":
                    "There is no active workflow."
            }

        # ---------------------------------------------
        # LEGACY WORKFLOW COMPATIBILITY
        # ---------------------------------------------

        if self._is_legacy_workflow(
            workflow
        ):

            status = (
                session.active_workflow_status
                or workflow.get("status")
            )

            if status == "waiting_for_input":

                return {
                    "action": "resume",
                    "reason":
                        (
                            "Legacy paused workflow "
                            "is eligible for normal resume."
                        ),
                    "legacy": True
                }

            if status == "planned":

                return {
                    "action": "resume",
                    "reason":
                        (
                            "Legacy planned workflow "
                            "is eligible for execution."
                        ),
                    "legacy": True
                }

            if status == "running":

                return {
                    "action": "recovery_review",
                    "reason":
                        (
                            "A legacy workflow was running "
                            "when recovery occurred; automatic "
                            "replay is unsafe."
                        ),
                    "legacy": True
                }

            if status == "completed":

                return {
                    "action": "already_complete",
                    "reason":
                        (
                            "The legacy workflow is already completed."
                        ),
                    "legacy": True
                }

            if status == "failed":

                return {
                    "action": "failed",
                    "reason":
                        (
                            "The legacy workflow previously failed."
                        ),
                    "legacy": True
                }

            if status == "blocked":

                return {
                    "action": "blocked",
                    "reason":
                        (
                            "The legacy workflow is blocked."
                        ),
                    "legacy": True
                }

            return {
                "action": "reject",
                "reason":
                    (
                        "Legacy workflow has an unknown "
                        "recovery state."
                    ),
                "legacy": True
            }

        # ---------------------------------------------
        # CURRENT DURABLE WORKFLOW
        # ---------------------------------------------

        return (
            WorkflowRecoveryValidator.recovery_action(
                workflow
            )
        )

    def _handle_recovery_review(
        self,
        session,
        session_id,
        recovery_result
    ):

        workflow = session.active_workflow

        session.active_workflow_status = (
            "recovery_review"
        )

        session.active_workflow_question = (
            recovery_result.get(
                "reason"
            )
        )

        self._persist_session(
            session_id
        )

        return {
            "status": "success",
            "session_id": session_id,
            "workflow": workflow,
            "execution": {
                "status":
                    "recovery_review",
                "workflow": workflow,
                "recovery":
                    recovery_result
            },
            "response": {
                "message":
                    (
                        "URI found a workflow that was "
                        "running when the previous session "
                        "ended. It will not automatically "
                        "rerun it because that could repeat "
                        "an external action."
                    ),
                "workflow": workflow,
                "recovery_action":
                    "recovery_review",
                "reason":
                    recovery_result.get(
                        "reason"
                    )
            }
        }

    def _handle_invalid_recovery(
        self,
        session,
        session_id,
        recovery_result
    ):

        workflow = session.active_workflow

        session.active_workflow_status = (
            "recovery_rejected"
        )

        session.active_workflow_question = (
            "The saved workflow could not be safely recovered."
        )

        self._persist_session(
            session_id
        )

        return {
            "status": "success",
            "session_id": session_id,
            "workflow": workflow,
            "execution": {
                "status":
                    "recovery_rejected",
                "workflow": workflow,
                "recovery":
                    recovery_result
            },
            "response": {
                "message":
                    (
                        "URI found that the saved workflow "
                        "is not structurally valid, so it "
                        "will not execute it."
                    ),
                "workflow": workflow,
                "recovery_action":
                    "reject",
                "errors":
                    recovery_result.get(
                        "validation",
                        {}
                    ).get(
                        "errors",
                        []
                    )
            }
        }

    def _recover_active_workflow(
        self,
        session,
        session_id
    ):

        recovery_result = (
            self._validate_recovery_workflow(
                session
            )
        )

        action = recovery_result.get(
            "action"
        )

        if action == "recovery_review":

            return self._handle_recovery_review(
                session,
                session_id,
                recovery_result
            )

        if action == "reject":

            return self._handle_invalid_recovery(
                session,
                session_id,
                recovery_result
            )

        if action == "already_complete":

            completed_workflow = (
                session.active_workflow
            )

            self._clear_active_workflow(
                session
            )

            self._persist_session(
                session_id
            )

            return {
                "status": "success",
                "session_id": session_id,
                "workflow": completed_workflow,
                "execution": {
                    "status":
                        "already_complete",
                    "workflow":
                        completed_workflow,
                    "recovery":
                        recovery_result
                },
                "response": {
                    "message":
                        "URI confirmed that this workflow is already completed.",
                    "workflow":
                        completed_workflow
                }
            }

        if action in (
            "failed",
            "blocked"
        ):

            session.active_workflow_status = action

            self._persist_session(
                session_id
            )

            return {
                "status": "success",
                "session_id": session_id,
                "workflow":
                    session.active_workflow,
                "execution": {
                    "status": action,
                    "workflow":
                        session.active_workflow,
                    "recovery":
                        recovery_result
                },
                "response": {
                    "message":
                        (
                            "URI will not automatically retry "
                            "the previously "
                            f"{action} workflow."
                        ),
                    "workflow":
                        session.active_workflow,
                    "recovery_action":
                        action
                }
            }

        return None

    def _resume_active_workflow(
        self,
        session,
        session_id,
        user_text
    ):

        required_field = (
            session.active_workflow_required_field
            or session.last_question_field
        )

        if required_field:

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
            execution_result.get("status")
        )

        if execution_status == "success":

            completed_workflow = (
                execution_result.get("workflow")
            )

            self._clear_active_workflow(
                session
            )

            self._persist_session(
                session_id
            )

            return {
                "status": "success",
                "workflow": completed_workflow,
                "execution": execution_result,
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
                "status": "success",
                "workflow":
                    execution_result.get(
                        "workflow"
                    ),
                "execution": execution_result,
                "response": {
                    "message":
                        execution_result.get(
                            "message",
                            (
                                "URI requires additional "
                                "information before continuing."
                            )
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
            "status": "success",
            "workflow":
                execution_result.get(
                    "workflow"
                ),
            "execution": execution_result,
            "response": {
                "message":
                    (
                        "URI could not complete "
                        "the resumed workflow."
                    ),
                "error":
                    execution_result.get(
                        "error"
                    )
            }
        }

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

            if session.active_workflow is not None:

                recovery_result = (
                    self._validate_recovery_workflow(
                        session
                    )
                )

                recovery_action = (
                    recovery_result.get(
                        "action"
                    )
                )

                if recovery_action == "recovery_review":

                    return (
                        self._handle_recovery_review(
                            session,
                            session_id,
                            recovery_result
                        )
                    )

                if recovery_action == "reject":

                    return (
                        self._handle_invalid_recovery(
                            session,
                            session_id,
                            recovery_result
                        )
                    )

                if recovery_action == "already_complete":

                    return (
                        self._recover_active_workflow(
                            session,
                            session_id
                        )
                    )

                if recovery_action in (
                    "failed",
                    "blocked"
                ):

                    return (
                        self._recover_active_workflow(
                            session,
                            session_id
                        )
                    )

                if (
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

            response = {
                "status": "success",
                "session_id": session_id,
                "semantic_analysis":
                    semantic_result,
                "learned_skill":
                    learned_skill,
                "plan": None,
                "workflow": None,
                "execution": None,
                "response": None
            }

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
                        (
                            "URI recognized this as a "
                            "previously learned workflow."
                        ),
                    "workflow":
                        learned_skill.get(
                            "workflow"
                        )
                }

                self._persist_session(
                    session_id
                )

                return response

            plan = (
                self.capability_planner.plan(
                    semantic_result
                )
            )

            response["plan"] = plan

            if (
                plan.get("status")
                == "capability_selected"
            ):

                tool_name = plan.get(
                    "tool_name"
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
                    "tool": tool_name
                }

                response["response"] = (
                    dispatch_result.get(
                        "data",
                        dispatch_result
                    )
                )

                if (
                    dispatch_result.get("status")
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
                        workflow=workflow,
                        tool_name=tool_name
                    )

                self._persist_session(
                    session_id
                )

                return response

            if (
                plan.get("status")
                == "planning_required"
            ):

                workflow_plan = (
                    self.workflow_planner.create_workflow(
                        semantic_result=
                            semantic_result,
                        request_text=user_text
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
                    execution_result.get("status")
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
                            (
                                "URI completed the "
                                "planned workflow."
                            ),
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
                        (
                            "URI could not complete "
                            "the planned workflow."
                        ),
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
                "tool": None
            }

            response["response"] = {
                "message":
                    (
                        "URI understands the request but "
                        "cannot safely execute it."
                    ),
                "suggested_next_step":
                    semantic_result.get(
                        "suggested_next_step"
                    )
            }

            self._persist_session(
                session_id
            )

            return response

        except Exception as e:

            return {
                "status": "failed",
                "error": str(e)
            }
