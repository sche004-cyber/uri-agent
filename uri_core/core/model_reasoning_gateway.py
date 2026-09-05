import json
import os
from typing import Any, Callable, Optional


class ModelReasoningGateway:
    """
    Boundary between URI's AI reasoning layer and deterministic runtime.

    The model reasons and proposes.

    This component does NOT execute capabilities.

    The runtime remains responsible for:
    - authorization
    - capability registration
    - execution
    - persistence
    - approval enforcement
    - security
    """

    CONTRACT_VERSION = "1.0"

    VALID_FACT_STATUSES = {
        "CONFIRMED",
        "PROVISIONAL",
        "HISTORICAL",
        "SUPERSEDED",
        "EXPIRED",
    }

    def __init__(
        self,
        policy_path=(
            "URI_Model_Centric_Architecture_Docs/"
            "URI_AI_OPERATING_POLICY.md"
        ),
        registry_path="uri_workspace/capabilities_registry.json",
        model_callable: Optional[Callable[[str], Any]] = None,
    ):
        self.policy_path = os.path.normpath(policy_path)
        self.registry_path = os.path.normpath(registry_path)
        self.model_callable = model_callable

    # ---------------------------------------------------------
    # POLICY
    # ---------------------------------------------------------

    def load_policy(self) -> str:
        try:
            with open(
                self.policy_path,
                "r",
                encoding="utf-8-sig",
            ) as file:
                return file.read()

        except FileNotFoundError:
            return ""

    # ---------------------------------------------------------
    # CAPABILITY CATALOGUE
    # ---------------------------------------------------------

    def load_capabilities(self) -> dict:
        try:
            with open(
                self.registry_path,
                "r",
                encoding="utf-8-sig",
            ) as file:
                registry = json.load(file)

        except (
            FileNotFoundError,
            json.JSONDecodeError,
        ):
            return {}

        active_tools = registry.get(
            "active_tools",
            {},
        )

        if not isinstance(
            active_tools,
            dict,
        ):
            return {}

        return active_tools

    def registered_capability_names(self) -> set[str]:
        return set(
            self.load_capabilities().keys()
        )

    # ---------------------------------------------------------
    # MODEL REQUEST
    # ---------------------------------------------------------

    def build_reasoning_request(
        self,
        user_text: str,
        session_context: Optional[dict] = None,
        evidence_context: Optional[dict] = None,
        query_context: Optional[dict] = None,
        attempt_history: Optional[list] = None,
        pending_proposal: Optional[dict] = None,
    ) -> dict:

        capabilities = self.load_capabilities()

        return {
            "contract_version":
                self.CONTRACT_VERSION,

            "system_policy":
                self.load_policy(),

            "user_request":
                str(user_text),

            "session_context":
                session_context
                if isinstance(
                    session_context,
                    dict,
                )
                else {},

            "evidence_context":
                evidence_context
                if isinstance(
                    evidence_context,
                    dict,
                )
                else {},

            # Milestone 10A/11: the same bounded, model-facing context
            # object query_context.build_query_context() already
            # assembles for response drafting (identity/personalization/
            # session/verified_facts/capabilities) - reused verbatim,
            # not rebuilt here. Additive: every existing caller that
            # omits this keeps getting exactly the pre-M11 request
            # shape below it.
            "query_context":
                query_context
                if isinstance(
                    query_context,
                    dict,
                )
                else {},

            # Milestone 11 Part 2 (Brain re-evaluation loop): empty for
            # the first reasoning call in a turn. When non-empty, each
            # entry is a compact {"proposal", "result"} record of an
            # action already taken THIS turn and what actually
            # happened - the model is being asked to evaluate the most
            # recent entry's real result against the original
            # user_request, not merely propose again from scratch.
            "attempt_history":
                attempt_history
                if isinstance(
                    attempt_history,
                    list,
                )
                else [],

            "available_capabilities":
                self._capability_descriptions(
                    capabilities
                ),

            # Milestone 13 Part 1 (canonical loop's pre-execution
            # step): present only on the sanity-check call that
            # follows an initial proposal, never on the initial call
            # itself. {"action": {...}} or {"workflow": {...}}, in the
            # exact same shape the model itself would return - see
            # REASONING_SYSTEM_PROMPT for what the model is asked to
            # do with it. None (the default) changes nothing about the
            # pre-M13 request shape.
            "pending_proposal":
                pending_proposal
                if isinstance(
                    pending_proposal,
                    dict,
                )
                else None,

            "instruction": (
                "Reason about the user's objective and return a "
                "structured URI model proposal. Do not execute anything. "
                "Use only capabilities present in the supplied catalogue. "
                "Adapt to new tasks by composing available capabilities "
                "rather than assuming a predefined workflow. If "
                "attempt_history is non-empty, evaluate whether the most "
                "recent attempt's real result actually satisfies "
                "user_request before proposing anything further."
            ),
        }

    def _capability_descriptions(
        self,
        capabilities: dict,
    ) -> list[dict]:

        descriptions = []

        for name, definition in capabilities.items():

            if isinstance(
                definition,
                dict,
            ):
                item = dict(definition)
                item.setdefault(
                    "name",
                    name,
                )

            else:
                item = {
                    "name": name,
                    "description": str(
                        definition
                    ),
                }

            descriptions.append(item)

        return descriptions

    # ---------------------------------------------------------
    # MODEL INVOCATION
    # ---------------------------------------------------------

    def reason(
        self,
        user_text: str,
        session_context: Optional[dict] = None,
        evidence_context: Optional[dict] = None,
        query_context: Optional[dict] = None,
        attempt_history: Optional[list] = None,
        pending_proposal: Optional[dict] = None,
    ) -> dict:

        request = (
            self.build_reasoning_request(
                user_text=user_text,
                session_context=session_context,
                evidence_context=evidence_context,
                query_context=query_context,
                attempt_history=attempt_history,
                pending_proposal=pending_proposal,
            )
        )

        if self.model_callable is None:

            return {
                "status":
                    "model_not_configured",

                "request":
                    request,

                "proposal":
                    None,
            }

        raw_response = self.model_callable(
            json.dumps(
                request,
                ensure_ascii=False,
            )
        )

        proposal = (
            self.parse_model_response(
                raw_response
            )
        )

        validation = (
            self.validate_proposal(
                proposal
            )
        )

        if not validation["valid"]:

            return {
                "status":
                    "model_proposal_rejected",

                "request":
                    request,

                "proposal":
                    proposal,

                "validation":
                    validation,
            }

        return {
            "status":
                "proposal_ready",

            "request":
                request,

            "proposal":
                proposal,

            "validation":
                validation,
        }

    # ---------------------------------------------------------
    # RESPONSE PARSING
    # ---------------------------------------------------------

    def parse_model_response(
        self,
        raw_response: Any,
    ) -> dict:

        if isinstance(
            raw_response,
            dict,
        ):
            return raw_response

        if not isinstance(
            raw_response,
            str,
        ):
            raise ValueError(
                "Model response must be a JSON object or JSON string."
            )

        text = raw_response.strip()

        if not text:
            raise ValueError(
                "Model returned an empty response."
            )

        # Accept a fenced JSON response from models.
        if text.startswith("```"):
            lines = text.splitlines()

            if (
                lines
                and lines[0].strip().startswith("```")
            ):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(
                lines
            ).strip()

        try:
            parsed = json.loads(text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Model response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(
            parsed,
            dict,
        ):
            raise ValueError(
                "Model response must contain a JSON object."
            )

        return parsed

    # ---------------------------------------------------------
    # CONTRACT VALIDATION
    # ---------------------------------------------------------

    def validate_proposal(
        self,
        proposal: Any,
    ) -> dict:

        errors = []

        if not isinstance(
            proposal,
            dict,
        ):
            return {
                "valid": False,
                "errors": [
                    "Proposal must be a JSON object."
                ],
            }

        intent = proposal.get(
            "intent"
        )

        if (
            intent is not None
            and not isinstance(
                intent,
                dict,
            )
        ):
            errors.append(
                "intent must be an object."
            )

        facts = proposal.get(
            "facts",
            [],
        )

        if not isinstance(
            facts,
            list,
        ):
            errors.append(
                "facts must be a list."
            )

        else:

            for index, fact in enumerate(
                facts
            ):

                if not isinstance(
                    fact,
                    dict,
                ):
                    errors.append(
                        f"facts[{index}] must be an object."
                    )
                    continue

                status = fact.get(
                    "status"
                )

                if (
                    status is not None
                    and status
                    not in self.VALID_FACT_STATUSES
                ):
                    errors.append(
                        "facts[{}] contains invalid status '{}'.".format(
                            index,
                            status,
                        )
                    )

        clarification = proposal.get(
            "clarification"
        )

        if clarification is not None:

            if not isinstance(
                clarification,
                dict,
            ):
                errors.append(
                    "clarification must be an object or null."
                )

            else:

                question = clarification.get(
                    "question"
                )

                if not isinstance(
                    question,
                    str,
                ) or not question.strip():

                    errors.append(
                        "clarification.question must be non-empty."
                    )

        # Milestone 11 Part 2 (Brain re-evaluation loop): present only
        # when the model was asked to evaluate a prior attempt's real
        # result (see attempt_history in build_reasoning_request).
        # Absent/null is valid and means "this is an initial proposal,
        # not an evaluation" - unchanged behavior for every existing
        # caller.
        evaluation = proposal.get(
            "evaluation"
        )

        if evaluation is not None:

            if not isinstance(
                evaluation,
                dict,
            ):
                errors.append(
                    "evaluation must be an object or null."
                )

            else:

                satisfied = evaluation.get(
                    "satisfied"
                )

                if not isinstance(
                    satisfied,
                    bool,
                ):
                    errors.append(
                        "evaluation.satisfied must be a boolean."
                    )

        capability_names = (
            self.registered_capability_names()
        )

        for location, capability in (
            self._find_proposed_capabilities(
                proposal
            )
        ):

            if capability not in capability_names:

                errors.append(
                    "{} proposes unregistered capability '{}'.".format(
                        location,
                        capability,
                    )
                )

        workflow = proposal.get(
            "workflow"
        )

        if workflow is not None:

            if not isinstance(
                workflow,
                dict,
            ):
                errors.append(
                    "workflow must be an object or null."
                )

            else:

                steps = workflow.get(
                    "steps",
                    [],
                )

                if not isinstance(
                    steps,
                    list,
                ):
                    errors.append(
                        "workflow.steps must be a list."
                    )

                else:

                    step_ids = set()

                    for index, step in enumerate(
                        steps
                    ):

                        if not isinstance(
                            step,
                            dict,
                        ):
                            errors.append(
                                f"workflow.steps[{index}] must be an object."
                            )
                            continue

                        step_id = step.get(
                            "step_id"
                        )

                        if (
                            not isinstance(
                                step_id,
                                str,
                            )
                            or not step_id.strip()
                        ):
                            errors.append(
                                f"workflow.steps[{index}] requires step_id."
                            )

                        elif step_id in step_ids:

                            errors.append(
                                f"workflow contains duplicate step_id '{step_id}'."
                            )

                        else:
                            step_ids.add(
                                step_id
                            )

                        depends_on = step.get(
                            "depends_on",
                            [],
                        )

                        if not isinstance(
                            depends_on,
                            list,
                        ):
                            errors.append(
                                f"workflow.steps[{index}].depends_on must be a list."
                            )

        action = proposal.get(
            "action"
        )

        if action is not None:

            if not isinstance(
                action,
                dict,
            ):
                errors.append(
                    "action must be an object or null."
                )

        return {
            "valid":
                not errors,

            "errors":
                errors,
        }

    def _find_proposed_capabilities(
        self,
        proposal: dict,
    ) -> list[tuple[str, str]]:

        found = []

        action = proposal.get(
            "action"
        )

        if isinstance(
            action,
            dict,
        ):

            capability = action.get(
                "capability"
            )

            if isinstance(
                capability,
                str,
            ) and capability.strip():

                found.append(
                    (
                        "action",
                        capability,
                    )
                )

        workflow = proposal.get(
            "workflow"
        )

        if isinstance(
            workflow,
            dict,
        ):

            steps = workflow.get(
                "steps",
                [],
            )

            if isinstance(
                steps,
                list,
            ):

                for index, step in enumerate(
                    steps
                ):

                    if not isinstance(
                        step,
                        dict,
                    ):
                        continue

                    capability = step.get(
                        "capability"
                    )

                    if isinstance(
                        capability,
                        str,
                    ) and capability.strip():

                        found.append(
                            (
                                f"workflow.steps[{index}]",
                                capability,
                            )
                        )

        return found