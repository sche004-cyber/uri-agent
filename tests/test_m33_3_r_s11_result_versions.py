"""M33.3-R S11: result-version ownership; an edited result is never overwritten by a redo."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from scripts.m33_3_s3_qualify import NOW, make_resolution
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.turn.rar_clarification_contract import BindingState, ClarificationResponse, ResponseKind
from uri_v1.turn.rar_contracts import RARBasis, RARCandidate, RAROutcome, RARQuery, RARResolution
from uri_v1.results.redo import (REDO_BLOCKED_EDITED, REDO_BLOCKED_UNKNOWN, REDO_DECLINED, REDONE, VERSIONED,
                                 RedoCoordinator)
from uri_v1.results.version_ledger import (EditedStatus, ResultVersionError, ResultVersionLedger, VersionOrigin,
                                           sha256)

USER = str(uuid.UUID(int=11))
X = RARCandidate(id="x", title="Q3 Budget.xlsx", candidate_type="document", owner="Finance")
Y = RARCandidate(id="y", title="Q3 Budget - board copy.xlsx", candidate_type="document", owner="Finance")


def changed_binding():
    """TENTATIVE X -> executed -> Change -> CONFIRMED Y (from_change), via the frozen S1 path."""
    service = BindingService()
    first_query = RARQuery("the budget", (X,))
    initial = build_clarification(first_query, RARResolution("the budget", RAROutcome.RESOLVED, candidate_id="x",
                                  basis=RARBasis.DETERMINISTIC_ANCHOR), session_id="s11", turn_id="t1",
                                  wrong_binding_impact="RECOVERABLE", now=NOW)
    first = service.register(initial, first_query)
    assert first.state == BindingState.TENTATIVE
    service.record_execution(first.binding_id, applied_result_exists=True)
    query = RARQuery("the budget", (X, Y))
    change = service.open_change(first.binding_id, query, make_resolution(query, "AMBIGUOUS", ["x", "y"]),
                                 impact_reader=lambda: "RECOVERABLE", turn_id="t2")
    contract = service.store.rounds[change.next_contract_id].contract
    rebound = service.respond("s11", ClarificationResponse(contract.ambiguity_id, ResponseKind.CANDIDATE,
                              candidate_id="y", candidate_set_fingerprint=contract.candidate_set_fingerprint),
                              query, wrong_binding_impact="RECOVERABLE", now=NOW)
    assert rebound.state == BindingState.CONFIRMED and rebound.candidate_id == "y"
    return service, rebound.binding_id


@pytest.fixture()
def setup(tmp_path):
    service, binding_id = changed_binding()
    ledger = ResultVersionLedger(USER, root=str(tmp_path))
    ledger.record_generated("draft-1", b"Draft body for X", binding_id="b-x", candidate_id="x")
    return service, binding_id, ledger, RedoCoordinator(service, ledger)


def test_normal_regeneration_redoes_unedited_result(setup):
    service, binding_id, ledger, coord = setup
    result = coord.redo_after_change(binding_id=binding_id, result_id="draft-1", read_current=lambda: b"Draft body for X",
                                     execute=lambda cid: f"Draft body for {cid.upper()}".encode(), fresh_authorized=True)
    assert result.outcome == REDONE and result.binding_state == BindingState.REDO_AUTHORIZED
    versions = ledger.versions("draft-1")
    assert [v.origin for v in versions] == ["GENERATED", "REDO"] and versions[-1].candidate_id == "y"
    assert ledger.blob(ledger.head("draft-1").content_sha256) == b"Draft body for Y"
    assert ledger.blob(versions[0].content_sha256) == b"Draft body for X"  # history kept
    with pytest.raises(ValueError):  # a second redo on the same rebind is not admissible (S1)
        coord.redo_after_change(binding_id=binding_id, result_id="draft-1", read_current=lambda: b"Draft body for Y",
                                execute=lambda cid: b"again", fresh_authorized=True)


def test_edited_result_is_never_overwritten(setup):
    service, binding_id, ledger, coord = setup
    edited = b"Draft body for X - with the user's own paragraph"
    calls = []
    result = coord.redo_after_change(binding_id=binding_id, result_id="draft-1", read_current=lambda: edited,
                                     execute=lambda cid: calls.append(cid) or b"overwrite!", fresh_authorized=True)
    assert result.outcome == REDO_BLOCKED_EDITED and result.edited_status == EditedStatus.USER_EDITED
    assert calls == []  # nothing regenerated
    assert service.store.bindings[binding_id].state == BindingState.REDO_NOT_EXECUTED
    head = ledger.head("draft-1")
    assert head.origin == VersionOrigin.USER_EDIT.value and ledger.blob(head.content_sha256) == edited
    # A preserved edit stays "edited" even though it now equals the head.
    assert ledger.edited_status("draft-1", edited) == EditedStatus.USER_EDITED


def test_explicit_new_version_keeps_edit_in_history(setup):
    service, binding_id, ledger, coord = setup
    edited = b"edited by user"
    coord.redo_after_change(binding_id=binding_id, result_id="draft-1", read_current=lambda: edited,
                            execute=lambda cid: b"x", fresh_authorized=True)
    with pytest.raises(ResultVersionError):
        coord.create_new_version(binding_id=binding_id, result_id="draft-1", read_current=lambda: edited,
                                 execute=lambda cid: b"x", explicit_user_request=False, fresh_authorized=True)
    result = coord.create_new_version(binding_id=binding_id, result_id="draft-1", read_current=lambda: edited,
                                      execute=lambda cid: f"new for {cid}".encode(), explicit_user_request=True,
                                      fresh_authorized=True)
    assert result.outcome == VERSIONED
    versions = ledger.versions("draft-1")
    assert [v.origin for v in versions] == ["GENERATED", "USER_EDIT", "REDO"]
    assert versions[-1].parent_version == versions[1].version
    assert ledger.blob(versions[1].content_sha256) == edited  # the edit is preserved, not replaced


def test_unreadable_or_unrecorded_result_fails_closed(setup, tmp_path):
    service, binding_id, ledger, coord = setup

    def broken():
        raise OSError("gone")

    result = coord.redo_after_change(binding_id=binding_id, result_id="draft-1", read_current=broken,
                                     execute=lambda cid: b"x", fresh_authorized=True)
    assert result.outcome == REDO_BLOCKED_UNKNOWN
    assert ledger.edited_status("never-recorded", b"x") == EditedStatus.UNKNOWN


def test_declined_fresh_authorization_does_not_redo(setup):
    service, binding_id, ledger, coord = setup
    result = coord.redo_after_change(binding_id=binding_id, result_id="draft-1", read_current=lambda: b"Draft body for X",
                                     execute=lambda cid: b"x", fresh_authorized=False)
    assert result.outcome == REDO_DECLINED and [v.origin for v in ledger.versions("draft-1")] == ["GENERATED"]
    with pytest.raises(ResultVersionError):  # unedited: the explicit versioning path is not a bypass
        coord.create_new_version(binding_id=binding_id, result_id="draft-1", read_current=lambda: b"Draft body for X",
                                 execute=lambda cid: b"x", explicit_user_request=True, fresh_authorized=True)


def test_ledger_is_append_only_content_addressed_and_validated(tmp_path):
    ledger = ResultVersionLedger(USER, root=str(tmp_path))
    v1 = ledger.record_generated("r1", b"abc")
    assert v1.content_sha256 == sha256(b"abc")
    with pytest.raises(ResultVersionError):
        ledger.record_generated("r1", b"again")
    for bad in ("../escape", "a/b", "", "x" * 200):
        with pytest.raises(ResultVersionError):
            ledger.record_generated(bad, b"x")
    with pytest.raises(ResultVersionError):
        ledger.append_redo("r1", b"z", parent=9, binding_id=None, candidate_id=None, trace_id=None)
    blob = next(Path(tmp_path).rglob(v1.content_sha256))
    blob.write_bytes(b"tampered")
    with pytest.raises(ResultVersionError):
        ledger.blob(v1.content_sha256)
    assert ledger.observe("r1", b"abc") == v1  # unchanged content appends nothing


def test_redo_requires_confirmed_change_rebind(tmp_path):
    service = BindingService()
    ledger = ResultVersionLedger(USER, root=str(tmp_path))
    with pytest.raises(KeyError):
        RedoCoordinator(service, ledger).redo_after_change(binding_id="nope", result_id="r", read_current=lambda: b"",
                                                           execute=lambda c: b"", fresh_authorized=True)
