"""Redo coordination over the frozen S1 BindingService and the result ledger.

The frozen S1 `authorize_redo` decides whether a Change redo may run, from the
true edited status this module supplies. An unedited result is redone and
appended as a new head (REDONE). An edited or unverifiable result is never
overwritten: the redo stops and the current content is preserved as a version
(REDO_BLOCKED_*). A new version on top of an edit is created only by an
explicit, freshly authorized user request (VERSIONED), keeping the edit in
history (plan decision D-S11-1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from uri_v1.reference_clarification.binding import BindingService
from uri_v1.turn.rar_clarification_contract import BindingState

from .version_ledger import EditedStatus, ResultVersion, ResultVersionError, ResultVersionLedger

REDONE = "REDONE"
VERSIONED = "VERSIONED"
REDO_BLOCKED_EDITED = "REDO_BLOCKED_EDITED"
REDO_BLOCKED_UNKNOWN = "REDO_BLOCKED_UNKNOWN"
REDO_DECLINED = "REDO_DECLINED"


@dataclass(frozen=True)
class RedoResult:
    outcome: str
    binding_state: BindingState
    edited_status: EditedStatus
    new_version: Optional[ResultVersion] = None
    preserved_version: Optional[ResultVersion] = None


class RedoCoordinator:
    def __init__(self, service: BindingService, ledger: ResultVersionLedger) -> None:
        self.service, self.ledger = service, ledger

    @staticmethod
    def _read(reader: Callable[[], bytes]) -> Optional[bytes]:
        try:
            content = reader()
        except Exception:
            return None  # an unreadable result is UNKNOWN, never assumed unedited
        return bytes(content) if isinstance(content, (bytes, bytearray)) else None

    def redo_after_change(self, *, binding_id: str, result_id: str, read_current: Callable[[], bytes],
                          execute: Callable[[str], bytes], fresh_authorized: bool,
                          trace_id: Optional[str] = None) -> RedoResult:
        current = self._read(read_current)
        status = self.ledger.edited_status(result_id, current)
        state = self.service.authorize_redo(binding_id, fresh_authorized=fresh_authorized,
                                            edited_result_status=status.value)
        if state == BindingState.REDO_AUTHORIZED:
            binding = self.service.store.bindings[binding_id]
            head = self.ledger.head(result_id)
            if head is None or status != EditedStatus.UNEDITED:
                raise ResultVersionError("redo authorized without an unedited recorded head")
            content = execute(binding.candidate_id)
            new = self.ledger.append_redo(result_id, content, parent=head.version, binding_id=binding_id,
                                          candidate_id=binding.candidate_id, trace_id=trace_id)
            return RedoResult(REDONE, state, status, new_version=new)
        if status == EditedStatus.USER_EDITED:
            preserved = self.ledger.observe(result_id, current)  # keep the edit, byte for byte
            return RedoResult(REDO_BLOCKED_EDITED, state, status, preserved_version=preserved)
        if status == EditedStatus.UNKNOWN:
            return RedoResult(REDO_BLOCKED_UNKNOWN, state, status)
        return RedoResult(REDO_DECLINED, state, status)

    def create_new_version(self, *, binding_id: str, result_id: str, read_current: Callable[[], bytes],
                           execute: Callable[[str], bytes], explicit_user_request: bool, fresh_authorized: bool,
                           trace_id: Optional[str] = None) -> RedoResult:
        """Explicit user request after a blocked redo: add the redo as a new version on top of the edit."""
        if explicit_user_request is not True or fresh_authorized is not True:
            raise ResultVersionError("a new version needs an explicit, freshly authorized user request")
        binding = self.service.store.bindings[binding_id]
        if binding.state != BindingState.REDO_NOT_EXECUTED or not binding.from_change or not binding.candidate_id:
            raise ResultVersionError("only a redo blocked after a confirmed Change may be versioned")
        current = self._read(read_current)
        if current is None:
            raise ResultVersionError("current result unreadable; nothing is written")
        status = self.ledger.edited_status(result_id, current)
        if status == EditedStatus.UNEDITED:
            raise ResultVersionError("result is unedited; use the normal redo path")
        preserved = self.ledger.observe(result_id, current)
        content = execute(binding.candidate_id)
        new = self.ledger.append_redo(result_id, content, parent=preserved.version, binding_id=binding_id,
                                      candidate_id=binding.candidate_id, trace_id=trace_id)
        return RedoResult(VERSIONED, binding.state, status, new_version=new, preserved_version=preserved)
