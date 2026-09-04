"""Deterministic approval state for individual proposed actions
(Milestone 7 — Real Approval Gate).

This is runtime-owned state, not model output. Nothing here is ever
constructed, mutated, or satisfied by a model response - a
ProposedAction is created only by ApprovalGate.execute_tool() (see
approval_gate.py) when the deterministic runtime itself decides a
CapabilityRegistry-declared approval_requirement applies, and it is
only ever approved/rejected by an explicit call recording a real
user decision (see server.py's POST /approve and POST /cancel).

An approval is bound to one specific invocation, not to a capability
name in general:
    - action_id     - a runtime-generated uuid4, never model-supplied.
    - capability_id - the exact tool_name this approval covers.
    - session_id    - the exact session it was proposed and must be
                      consumed in.
    - arguments     - the exact arguments it covers, plus a SHA-256
                      arguments_fingerprint used to detect any drift
                      between what was approved and what a caller
                      later tries to execute.

Every one of those four must match at consumption time (see
ApprovalStore.consume()) - approval for one action can never satisfy
a different capability, a different session, or the same capability
with different arguments. Consumption is single-use: a second
consume() for the same action_id always fails, which is this store's
replay-prevention control.

A pending action that is never decided, or an approved action that is
never consumed, expires after DEFAULT_EXPIRY_SECONDS - a stale
decision can never be resurrected to authorize a later, unrelated
request.

Persistence follows GrowthLedgerStore/MemoryStore's exact pattern
(JSON file, schema_version, safe degrade on a corrupted file) with one
important difference: degrading to an empty list on a corrupted or
missing file is exactly the correct fail-closed behaviour here -
empty means nothing is approved, so ApprovalGate can never mistake a
corrupted store for permission to execute.
"""

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uri_core.core.security_guards import (
    MAX_METADATA_VALUE_LENGTH,
    looks_like_credential_key,
    looks_like_credential_value,
)

SCHEMA_VERSION = "1.0"

# A pending decision, or an approved-but-unconsumed action, older than
# this many seconds fails closed rather than remaining usable
# indefinitely. Applies uniformly from created_at, so an approval
# cannot be "banked" and consumed much later under different
# circumstances.
DEFAULT_EXPIRY_SECONDS = 900  # 15 minutes

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_CONSUMED = "consumed"
STATUS_EXPIRED = "expired"


class ApprovalError(Exception):
    """Base class for every approval-flow failure. Any raise from this
    module means "fail closed" - ApprovalGate must treat all of these
    as a hard block, never a soft warning or a partial success."""


class ApprovalNotFoundError(ApprovalError):
    """No ProposedAction exists with the given action_id."""


class ApprovalStateError(ApprovalError):
    """Wrong state for the requested transition: already decided,
    already consumed, expired, or a mismatched capability/session/
    argument binding."""


class ApprovalValidationError(ApprovalError):
    """Proposed arguments failed validation (credential-shaped or
    oversized) - the action is never created."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _ensure_parent_dir(path: str) -> None:
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)


def _fingerprint(capability_id: str, arguments: Dict[str, Any]) -> str:
    """Deterministic, order-independent binding of a capability_id +
    arguments pair. Not a security control by itself - action_id,
    capability_id, and session_id are always independently
    cross-checked too (see ApprovalStore.consume()) - this exists so
    the exact bound content is auditable and reproducible without
    keeping a second, driftable copy of it."""

    canonical = json.dumps(
        {"capability_id": capability_id, "arguments": arguments},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_arguments(arguments: Dict[str, Any]) -> None:

    for key, value in arguments.items():

        if looks_like_credential_key(str(key)):
            raise ApprovalValidationError(
                f"argument key '{key}' looks credential-related and "
                "is not permitted in a proposed action."
            )

        if isinstance(value, str):

            if looks_like_credential_value(value):
                raise ApprovalValidationError(
                    f"argument value for key '{key}' looks like a "
                    "credential and is not permitted in a proposed "
                    "action."
                )

            if len(value) > MAX_METADATA_VALUE_LENGTH:
                raise ApprovalValidationError(
                    f"argument value for key '{key}' exceeds "
                    f"{MAX_METADATA_VALUE_LENGTH} characters."
                )


@dataclass
class ProposedAction:
    action_id: str
    capability_id: str
    session_id: Optional[str]
    arguments: Dict[str, Any]
    arguments_fingerprint: str
    status: str
    created_at: str
    decided_at: Optional[str] = None
    consumed_at: Optional[str] = None
    schema_version: str = SCHEMA_VERSION


class ApprovalStore:
    """Loads and saves the append-and-mutate list of ProposedAction
    records for this install."""

    def __init__(
        self, storage_path: str = "uri_workspace/approvals.json"
    ):
        self.storage_path = os.path.normpath(storage_path)

    def propose(
        self,
        capability_id: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> ProposedAction:

        arguments = dict(arguments or {})
        _validate_arguments(arguments)

        action = ProposedAction(
            action_id=str(uuid.uuid4()),
            capability_id=capability_id,
            session_id=session_id,
            arguments=arguments,
            arguments_fingerprint=_fingerprint(
                capability_id, arguments
            ),
            status=STATUS_PENDING,
            created_at=_now_iso(),
        )

        actions = self._load()
        actions.append(action)
        self._save(actions)

        return action

    def get(self, action_id: str) -> Optional[ProposedAction]:

        for action in self._load():

            if action.action_id == action_id:
                return action

        return None

    def list_pending(self) -> List[ProposedAction]:
        """Every action still awaiting a decision, across all
        sessions, excluding anything already expired - read-only,
        for a cross-session "what needs my attention" view (see
        server.py's GET /tasks). Callers must never use this to
        approve/consume anything; that stays exclusively decide()/
        consume()."""

        return [
            action
            for action in self._load()
            if action.status == STATUS_PENDING
            and not self._is_expired(action)
        ]

    def decide(
        self,
        action_id: str,
        approved: bool,
        session_id: Optional[str] = None,
    ) -> ProposedAction:
        """Records the user's decision - the only place a
        ProposedAction ever moves out of "pending". Fails closed with
        a specific ApprovalStateError for anything already decided,
        expired, or proposed in a different session, and
        ApprovalNotFoundError for an unknown action_id - never
        silently succeeds on ambiguous input.

        session_id is checked here, not only in consume(), so a
        wrong-session decision attempt is rejected before any state
        mutation happens - without this check, a mismatched-session
        caller could still flip a legitimate pending action to
        "approved" (consume() would then correctly refuse it for the
        session mismatch), permanently stranding it in a state the
        real proposing session can never successfully consume either,
        since decide() only ever runs once per action.
        """

        actions = self._load()

        for index, action in enumerate(actions):

            if action.action_id != action_id:
                continue

            if action.status != STATUS_PENDING:
                raise ApprovalStateError(
                    f"Action {action_id} is not pending "
                    f"(status={action.status}); it cannot be decided "
                    "again."
                )

            if action.session_id != session_id:
                raise ApprovalStateError(
                    f"Action {action_id} was proposed in a different "
                    "session."
                )

            if self._is_expired(action):
                action.status = STATUS_EXPIRED
                actions[index] = action
                self._save(actions)
                raise ApprovalStateError(
                    f"Action {action_id} expired before a decision "
                    "was recorded."
                )

            action.status = (
                STATUS_APPROVED if approved else STATUS_REJECTED
            )
            action.decided_at = _now_iso()
            actions[index] = action
            self._save(actions)

            return action

        raise ApprovalNotFoundError(
            f"No proposed action with id {action_id}."
        )

    def consume(
        self,
        action_id: str,
        capability_id: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> ProposedAction:
        """The one method that turns a recorded approval into
        permission to execute. Single-use: a second call for the same
        action_id always fails, even with identical, correct
        arguments - this is the replay-prevention control. Every
        mismatch (wrong status, expiry, capability, session,
        arguments) fails closed with a specific ApprovalStateError."""

        actions = self._load()

        for index, action in enumerate(actions):

            if action.action_id != action_id:
                continue

            if action.status != STATUS_APPROVED:
                raise ApprovalStateError(
                    f"Action {action_id} is not approved "
                    f"(status={action.status})."
                )

            if self._is_expired(action):
                action.status = STATUS_EXPIRED
                actions[index] = action
                self._save(actions)
                raise ApprovalStateError(
                    f"Action {action_id} expired before it was "
                    "executed."
                )

            if action.capability_id != capability_id:
                raise ApprovalStateError(
                    f"Action {action_id} was approved for "
                    f"'{action.capability_id}', not '{capability_id}'."
                )

            if action.session_id != session_id:
                raise ApprovalStateError(
                    f"Action {action_id} was approved in a different "
                    "session."
                )

            expected_fingerprint = _fingerprint(
                capability_id, arguments
            )

            if action.arguments_fingerprint != expected_fingerprint:
                raise ApprovalStateError(
                    f"Action {action_id}'s approved arguments do not "
                    "match the arguments requested for execution."
                )

            action.status = STATUS_CONSUMED
            action.consumed_at = _now_iso()
            actions[index] = action
            self._save(actions)

            return action

        raise ApprovalNotFoundError(
            f"No proposed action with id {action_id}."
        )

    def _is_expired(self, action: ProposedAction) -> bool:

        try:
            created = datetime.fromisoformat(action.created_at)

        except (TypeError, ValueError):
            return True  # malformed timestamp - fail closed

        age_seconds = (_now() - created).total_seconds()

        return age_seconds > DEFAULT_EXPIRY_SECONDS

    def _load(self) -> List[ProposedAction]:

        if not os.path.exists(self.storage_path):
            return []

        try:

            with open(
                self.storage_path, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            actions = []

            for raw in data.get("actions", []):

                actions.append(
                    ProposedAction(
                        action_id=raw["action_id"],
                        capability_id=raw["capability_id"],
                        session_id=raw.get("session_id"),
                        arguments=raw.get("arguments", {}),
                        arguments_fingerprint=raw.get(
                            "arguments_fingerprint", ""
                        ),
                        status=raw.get("status", STATUS_PENDING),
                        created_at=raw.get("created_at", ""),
                        decided_at=raw.get("decided_at"),
                        consumed_at=raw.get("consumed_at"),
                        schema_version=raw.get(
                            "schema_version", SCHEMA_VERSION
                        ),
                    )
                )

            return actions

        except (
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
        ):
            # Fail closed: a corrupted store means nothing is
            # approved, never "assume everything was fine".
            return []

    def _save(self, actions: List[ProposedAction]) -> None:
        _ensure_parent_dir(self.storage_path)

        data = {
            "schema_version": SCHEMA_VERSION,
            "actions": [asdict(action) for action in actions],
        }

        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
