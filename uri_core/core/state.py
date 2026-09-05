import json
import os
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Dict, List, Optional

from uri_core.core.facts import Fact


@dataclass
class SessionState:
    """
    Stores the active URI conversation state.
    """

    session_id: str

    task: Optional[str] = None

    current_facts: Dict[str, object] = field(
        default_factory=dict
    )

    evidence_facts: Dict[str, object] = field(
        default_factory=dict
    )

    historical_facts: Dict[str, object] = field(
        default_factory=dict
    )

    # Full, append-only conflict history: for each fact name, every
    # value that was ever superseded, in order. Unlike
    # historical_facts above (kept for backward compatibility as a
    # single most-recently-superseded slot per name), nothing here
    # is ever overwritten.
    fact_history: Dict[str, List[object]] = field(
        default_factory=dict
    )

    last_question_field: Optional[str] = None

    clarification_complete: bool = False

    evidence_verification_pending: bool = False

    active_evidence_query: Optional[str] = None

    active_evidence_context: Optional[str] = None

    # ---------------------------------------------
    # ACTIVE WORKFLOW STATE
    # ---------------------------------------------

    active_workflow: Optional[dict] = None

    active_workflow_status: Optional[str] = None

    active_workflow_required_field: Optional[str] = None

    active_workflow_question: Optional[str] = None

    # True only when the active workflow was restored from
    # persistent storage and has not yet re-entered the normal
    # in-process workflow lifecycle.
    #
    # This is intentionally transient and is NOT serialized.
    active_workflow_recovered: bool = False

    # ---------------------------------------------
    # CARRIED BRAIN ATTEMPT HISTORY (URI Correction Part 1)
    #
    # Read-once: the goal text and compact attempt/result history from
    # the immediately preceding turn's Brain re-evaluation loop
    # (orchestrator.py's _continue_brain_evaluation_loop), kept ONLY
    # when that turn did not end with the Brain judging itself
    # satisfied - i.e. exactly the case where the user's next message
    # (acceptance, rejection, or redirection) is real evidence the
    # Brain has not yet seen. orchestrator.py reads and clears both
    # fields at the start of the next turn's reasoning call; they are
    # never accumulated indefinitely and never independently
    # interpreted by URI as "the user rejected this" - that judgment,
    # like every other judgment of intent, belongs to the Brain.
    # ---------------------------------------------

    last_goal_text: Optional[str] = None

    last_goal_attempt_history: Optional[List[dict]] = None


class SessionManager:
    """
    Keeps URI conversation sessions in memory and
    persists them to JSON for restart recovery.
    """

    def __init__(
        self,
        storage_path="uri_workspace/sessions"
    ):

        self.sessions: Dict[
            str,
            SessionState
        ] = {}

        self.storage_path = os.path.normpath(
            storage_path
        )

        os.makedirs(
            self.storage_path,
            exist_ok=True
        )

    def get_session(
        self,
        session_id: str
    ) -> SessionState:

        if session_id in self.sessions:

            return self.sessions[
                session_id
            ]

        session = self._load_session(
            session_id
        )

        if session is None:

            session = SessionState(
                session_id=session_id
            )

        self.sessions[
            session_id
        ] = session

        return session

    def save_session(
        self,
        session_id: str
    ) -> SessionState:

        session = self.get_session(
            session_id
        )

        session_path = (
            self._get_session_path(
                session_id
            )
        )

        session_data = (
            self._serialize_session(
                session
            )
        )

        with open(
            session_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                session_data,
                file,
                indent=2,
                ensure_ascii=False
            )

        return session

    def reset_session(
        self,
        session_id: str
    ) -> SessionState:

        self.sessions[
            session_id
        ] = SessionState(
            session_id=session_id
        )

        session_path = (
            self._get_session_path(
                session_id
            )
        )

        if os.path.exists(
            session_path
        ):

            os.remove(
                session_path
            )

        return self.sessions[
            session_id
        ]

    def _get_session_path(
        self,
        session_id: str
    ) -> str:

        safe_session_id = (
            "".join(
                character
                for character in session_id
                if (
                    character.isalnum()
                    or character
                    in (
                        "-",
                        "_"
                    )
                )
            )
        )

        if not safe_session_id:

            safe_session_id = "default"

        filename = (
            f"{safe_session_id}.json"
        )

        return os.path.join(
            self.storage_path,
            filename
        )

    def _serialize_session(
        self,
        session: SessionState
    ) -> dict:

        return {
            "session_id":
                session.session_id,

            "task":
                session.task,

            "current_facts":
                self._serialize_fact_collection(
                    session.current_facts
                ),

            "evidence_facts":
                self._serialize_fact_collection(
                    session.evidence_facts
                ),

            "historical_facts":
                self._serialize_fact_collection(
                    session.historical_facts
                ),

            "fact_history":
                self._serialize_fact_history(
                    getattr(
                        session,
                        "fact_history",
                        {}
                    )
                ),

            "last_question_field":
                session.last_question_field,

            "clarification_complete":
                session.clarification_complete,

            "evidence_verification_pending":
                session.evidence_verification_pending,

            "active_evidence_query":
                session.active_evidence_query,

            "active_evidence_context":
                session.active_evidence_context,

            "active_workflow":
                session.active_workflow,

            "active_workflow_status":
                session.active_workflow_status,

            "active_workflow_required_field":
                (
                    session.active_workflow_required_field
                ),

            "active_workflow_question":
                session.active_workflow_question,

            "last_goal_text":
                getattr(session, "last_goal_text", None),

            "last_goal_attempt_history":
                getattr(session, "last_goal_attempt_history", None),
        }

    def _serialize_fact_collection(
        self,
        facts
    ) -> dict:

        serialized = {}

        for name, fact in facts.items():

            if isinstance(
                fact,
                Fact
            ):

                serialized[name] = {
                    "__type__": "Fact",
                    "data": asdict(fact)
                }

            elif is_dataclass(
                fact
            ):

                serialized[name] = {
                    "__type__":
                        "dataclass",
                    "data":
                        asdict(fact)
                }

            else:

                serialized[name] = fact

        return serialized

    def _deserialize_fact_collection(
        self,
        facts
    ) -> dict:

        restored = {}

        if not isinstance(
            facts,
            dict
        ):

            return restored

        for name, value in facts.items():

            if (
                isinstance(value, dict)
                and value.get("__type__")
                == "Fact"
            ):

                fact_data = value.get(
                    "data",
                    {}
                )

                try:

                    restored[name] = Fact(
                        **fact_data
                    )

                except Exception:

                    restored[name] = (
                        fact_data
                    )

            elif (
                isinstance(value, dict)
                and value.get("__type__")
                == "dataclass"
            ):

                restored[name] = value.get(
                    "data",
                    {}
                )

            else:

                restored[name] = value

        return restored

    def _serialize_fact_history(
        self,
        history
    ) -> dict:
        """
        Serializes fact_history: Dict[str, List[Fact]]. Reuses the
        same per-item Fact/dataclass tagging as
        _serialize_fact_collection, applied to each item in the
        list rather than to a single value.
        """

        serialized = {}

        for name, fact_list in history.items():

            if not isinstance(fact_list, list):
                continue

            serialized[name] = [
                self._serialize_single_fact(item)
                for item in fact_list
            ]

        return serialized

    def _serialize_single_fact(self, fact):

        if isinstance(fact, Fact):

            return {
                "__type__": "Fact",
                "data": asdict(fact)
            }

        if is_dataclass(fact):

            return {
                "__type__": "dataclass",
                "data": asdict(fact)
            }

        return fact

    def _deserialize_fact_history(
        self,
        history
    ) -> dict:

        restored = {}

        if not isinstance(history, dict):
            return restored

        for name, items in history.items():

            if not isinstance(items, list):
                continue

            restored_list = []

            for value in items:

                if (
                    isinstance(value, dict)
                    and value.get("__type__") == "Fact"
                ):

                    fact_data = value.get("data", {})

                    try:

                        restored_list.append(
                            Fact(**fact_data)
                        )

                    except Exception:

                        restored_list.append(fact_data)

                elif (
                    isinstance(value, dict)
                    and value.get("__type__") == "dataclass"
                ):

                    restored_list.append(
                        value.get("data", {})
                    )

                else:

                    restored_list.append(value)

            restored[name] = restored_list

        return restored

    def _load_session(
        self,
        session_id: str
    ) -> Optional[SessionState]:

        session_path = (
            self._get_session_path(
                session_id
            )
        )

        if not os.path.exists(
            session_path
        ):

            return None

        try:

            with open(
                session_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

            session = SessionState(
                session_id=data.get(
                    "session_id",
                    session_id
                )
            )

            session.task = data.get(
                "task"
            )

            session.current_facts = (
                self._deserialize_fact_collection(
                    data.get(
                        "current_facts",
                        {}
                    )
                )
            )

            session.evidence_facts = (
                self._deserialize_fact_collection(
                    data.get(
                        "evidence_facts",
                        {}
                    )
                )
            )

            session.historical_facts = (
                self._deserialize_fact_collection(
                    data.get(
                        "historical_facts",
                        {}
                    )
                )
            )

            session.fact_history = (
                self._deserialize_fact_history(
                    data.get(
                        "fact_history",
                        {}
                    )
                )
            )

            session.last_question_field = (
                data.get(
                    "last_question_field"
                )
            )

            session.clarification_complete = (
                data.get(
                    "clarification_complete",
                    False
                )
            )

            session.evidence_verification_pending = (
                data.get(
                    "evidence_verification_pending",
                    False
                )
            )

            session.active_evidence_query = (
                data.get(
                    "active_evidence_query"
                )
            )

            session.active_evidence_context = (
                data.get(
                    "active_evidence_context"
                )
            )

            session.active_workflow = (
                data.get(
                    "active_workflow"
                )
            )

            session.active_workflow_status = (
                data.get(
                    "active_workflow_status"
                )
            )

            session.active_workflow_required_field = (
                data.get(
                    "active_workflow_required_field"
                )
            )

            session.active_workflow_question = (
                data.get(
                    "active_workflow_question"
                )
            )

            session.last_goal_text = (
                data.get(
                    "last_goal_text"
                )
            )

            session.last_goal_attempt_history = (
                data.get(
                    "last_goal_attempt_history"
                )
            )

            # --------------------------------------------------
            # Mark the session as having restored workflow state.
            #
            # This flag is transient. It tells the orchestrator
            # that active_workflow came from persistent storage
            # and therefore must pass recovery validation before
            # URI allows automatic continuation.
            # --------------------------------------------------

            session.active_workflow_recovered = (
                session.active_workflow is not None
            )

            return session

        except Exception:

            return None
