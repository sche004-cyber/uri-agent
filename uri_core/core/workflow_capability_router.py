from uri_core.core.workflow_executor import (
    WorkflowExecutor
)
from uri_core.core.dispatcher import real_tool_status
from uri_core.core.evidence_search import (
    build_evidence_queries
)
from uri_core.core.evidence_context import (
    get_relevant_evidence,
    evidence_summary
)
from uri_core.core.clarification import (
    get_next_question
)


class WorkflowCapabilityRouter:
    """
    Connects abstract workflow capabilities to URI's
    real session, evidence, clarification and drafting
    infrastructure.
    """

    def __init__(
        self,
        dispatcher,
        session=None,
        evidence_processor=None
    ):

        self.dispatcher = dispatcher
        self.session = session
        self.evidence_processor = (
            evidence_processor
        )

    def create_executor(self):

        executor = WorkflowExecutor()

        executor.register_handler(
            "retrieve_evidence",
            self.retrieve_evidence
        )

        executor.register_handler(
            "verify_facts",
            self.verify_facts
        )

        executor.register_handler(
            "identify_missing_information",
            self.identify_missing_information
        )

        executor.register_handler(
            "prepare_decision_context",
            self.prepare_decision_context
        )

        executor.register_handler(
            "prepare_output",
            self.prepare_output
        )

        executor.register_handler(
            "draft_output",
            self.draft_output
        )

        executor.register_handler(
            "review_result",
            self.review_result
        )

        return executor

    def retrieve_evidence(
        self,
        step: dict,
        workflow: dict
    ) -> dict:

        if self.session is None:

            return {
                "status": "success",
                "data": {
                    "queries": [],
                    "evidence_available": False,
                    "message":
                        "No active session is available."
                }
            }

        task = self._resolve_task(
            workflow
        )

        queries = build_evidence_queries(
            task=task,
            current_facts=self.session.current_facts
        )

        workflow[
            "evidence_queries"
        ] = queries

        if not queries:

            return {
                "status": "success",
                "data": {
                    "queries": [],
                    "evidence_available": bool(
                        self.session.evidence_facts
                    ),
                    "message":
                        "No additional evidence query is required."
                }
            }

        if self.evidence_processor is None:

            return {
                "status": "success",
                "data": {
                    "queries": queries,
                    "evidence_available": bool(
                        self.session.evidence_facts
                    ),
                    "message":
                        "Evidence processor is not configured."
                }
            }

        processing_results = []

        for query in queries:

            try:

                result = (
                    self.evidence_processor
                    .process_gmail_query(
                        query=query,
                        session=self.session
                    )
                )

                processing_results.append(
                    result
                )

            except Exception as e:

                processing_results.append(
                    {
                        "success": False,
                        "query": query,
                        "error": str(e)
                    }
                )

        relevant_evidence = (
            get_relevant_evidence(
                session=self.session,
                task=task,
                message=workflow.get(
                    "goal",
                    ""
                )
            )
        )

        evidence_data = (
            evidence_summary(
                relevant_evidence
            )
        )

        workflow[
            "relevant_evidence"
        ] = evidence_data

        successful_processing = any(
            result.get("success")
            for result in processing_results
        )

        return {
            "status": "success",
            "data": {
                "queries": queries,
                "processing_results":
                    processing_results,
                "evidence_available":
                    bool(relevant_evidence),
                "evidence_processed":
                    successful_processing,
                "relevant_evidence":
                    evidence_data
            }
        }

    def verify_facts(
        self,
        step: dict,
        workflow: dict
    ) -> dict:

        if self.session is None:

            return {
                "status": "success",
                "data": {
                    "verification_status":
                        "no_session"
                }
            }

        task = self._resolve_task(
            workflow
        )

        relevant_evidence = (
            get_relevant_evidence(
                session=self.session,
                task=task,
                message=workflow.get(
                    "goal",
                    ""
                )
            )
        )

        evidence_data = (
            evidence_summary(
                relevant_evidence
            )
        )

        workflow[
            "relevant_evidence"
        ] = evidence_data

        return {
            "status": "success",
            "data": {
                "verification_status":
                    (
                        "verified_evidence_available"
                        if relevant_evidence
                        else "no_verified_evidence"
                    ),
                "verified_facts":
                    evidence_data
            }
        }

    def identify_missing_information(
        self,
        step: dict,
        workflow: dict
    ) -> dict:

        current_facts = {}

        relevant_evidence = {}

        if self.session is not None:

            current_facts = (
                self.session.current_facts
            )

            task = self._resolve_task(
                workflow
            )

            relevant_evidence = (
                get_relevant_evidence(
                    session=self.session,
                    task=task,
                    message=workflow.get(
                        "goal",
                        ""
                    )
                )
            )

        task = self._resolve_task(
            workflow
        )

        question = get_next_question(
            task=task,
            current_facts=current_facts,
            relevant_evidence=relevant_evidence
        )

        if question:

            if self.session is not None:

                self.session.last_question_field = (
                    question.get("field")
                )

                self.session.clarification_complete = (
                    False
                )

            return {
                "status":
                    "waiting_for_input",
                "message":
                    question.get("question"),
                "required_field":
                    question.get("field")
            }

        if self.session is not None:

            self.session.last_question_field = None

            self.session.clarification_complete = (
                True
            )

        return {
            "status": "success",
            "data": {
                "missing_information": None,
                "clarification_complete": True
            }
        }

    def prepare_decision_context(
        self,
        step: dict,
        workflow: dict
    ) -> dict:

        context = {
            "goal":
                workflow.get("goal"),
            "semantic_context":
                workflow.get(
                    "semantic_context",
                    {}
                )
        }

        if self.session is not None:

            context[
                "current_facts"
            ] = {
                name: fact.value
                for name, fact in (
                    self.session.current_facts.items()
                )
            }

            relevant_evidence = (
                get_relevant_evidence(
                    session=self.session,
                    task=self._resolve_task(
                        workflow
                    ),
                    message=workflow.get(
                        "goal",
                        ""
                    )
                )
            )

            context[
                "verified_evidence"
            ] = evidence_summary(
                relevant_evidence
            )

        workflow[
            "decision_context"
        ] = context

        return {
            "status": "success",
            "data": context
        }

    def prepare_output(
        self,
        step: dict,
        workflow: dict
    ) -> dict:
        """Only reached by the generic workflow shape (see
        workflow_planner.py's _create_steps) - "noting"/"insurance"
        tasks route through draft_output instead, which dispatches to
        a real, registered tool. There is no real, implemented
        capability behind this generic bucket at all (no
        TASK_REQUIREMENTS entry in clarification.py, no drafting/
        compilation tool wired in), so claiming "prepared: True" here
        would be a false claim of progress - this is a genuine missing-
        capability outcome, distinct from a missing-evidence or
        missing-resource one, and must be reported as such rather than
        silently faked."""

        return {
            "status": "failed",
            "error": (
                "URI does not have an implemented capability for "
                "this kind of task yet."
            )
        }

    def draft_output(
        self,
        step: dict,
        workflow: dict
    ) -> dict:

        requested_output = str(
            workflow.get(
                "semantic_context",
                {}
            ).get(
                "requested_output",
                ""
            )
        ).lower()

        tool_name = None

        if (
            "office note" in requested_output
            or "noting" in requested_output
        ):

            tool_name = (
                "draft_institutional_note"
            )

        elif (
            "office order" in requested_output
            or "order" in requested_output
        ):

            tool_name = (
                "draft_institutional_order"
            )

        else:

            # M19 (audit finding #8): a requested output that is not an
            # institutional note or order (a proposal, a presentation,
            # a spreadsheet, a PDF report, or anything else) no longer
            # dead-ends this step waiting for a "supported output
            # format" that only ever meant note/order - it drafts via
            # the generic Brain-authored document capability instead,
            # which detects DOCX/XLSX/PPTX/PDF from the request itself.
            tool_name = "generate_document"

        decision_context = (
            workflow.get(
                "decision_context",
                {}
            )
        )

        result = (
            self.dispatcher.execute_tool(
                tool_name,
                session_id=(
                    getattr(self.session, "session_id", None)
                ),
                request_text=workflow.get(
                    "goal",
                    ""
                ),
                decision_context=decision_context
            )
        )

        # M19: real_tool_status looks past the dispatcher's own
        # unconditional outer "success" to the drafting tool's actual
        # reported outcome, so a tool that could not draft (e.g.
        # returned "unavailable"/"input_required") is never reported
        # as a completed draft (audit finding #3).
        if real_tool_status(result) == "success":

            return {
                "status": "success",
                "data": result.get("data")
            }

        data = result.get("data")
        error_detail = (
            data.get("message") if isinstance(data, dict) else None
        )

        return {
            "status": "failed",
            "error":
                error_detail
                or result.get(
                    "message",
                    "Drafting failed."
                )
        }

    def review_result(
        self,
        step: dict,
        workflow: dict
    ) -> dict:

        draft = self._previous_result(
            workflow,
            "draft_output"
        )

        if draft is None:

            return {
                "status": "failed",
                "error":
                    "No drafted output was available for review."
            }

        return {
            "status": "success",
            "data": {
                "reviewed": True,
                "output_available": True
            }
        }

    def _resolve_task(
        self,
        workflow: dict
    ) -> str:

        semantic_context = (
            workflow.get(
                "semantic_context",
                {}
            )
        )

        requested_output = str(
            semantic_context.get(
                "requested_output",
                ""
            )
        ).lower()

        goal = str(
            workflow.get(
                "goal",
                ""
            )
        ).lower()

        combined = (
            requested_output
            + " "
            + goal
        )

        if (
            "note" in combined
            or "noting" in combined
        ):

            return "noting"

        if "letter" in combined:

            return "letter"

        return "generic"

    def _previous_result(
        self,
        workflow: dict,
        capability: str
    ):

        for workflow_step in workflow.get(
            "steps",
            []
        ):

            if (
                workflow_step.get(
                    "capability"
                )
                == capability
            ):

                return workflow_step.get(
                    "result"
                )

        return None
