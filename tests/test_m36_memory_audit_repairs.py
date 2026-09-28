"""Regression tests for the M36 independent closing-audit findings F-1..F-6."""
from types import MappingProxyType
import pytest
import uri_v1.memory.recorder as module
from uri_v1.memory.recorder import _runtime_observation
from uri_v1.memory.contracts import RecordKind, negated
from uri_v1.memory.context_package import build_context
from uri_v1.memory.index import VerifierRegistryMismatch
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.retrieval import Retriever
from uri_v1.turn.rar_clarification_contract import BindingState
from tests.test_m36_memory_support import setup,retrieval,opened,intake,bind,USER
from tests.test_m36_memory_grounding import registered
from tests.test_m36_memory_verifier import bootstrap,claimed,fixture_verifier


@pytest.mark.parametrize("raw,span",[
    ("don't use budget.xlsx",None),
    ("dont use budget.xlsx",None),
    ("never budget.xlsx",None),
    ("skip budget.xlsx",None),
    ("anything other than budget.xlsx",None),
    ("instead of budget.xlsx use the report",None),
    ("rather than budget.xlsx",None),
    ("not budget.xlsx",(4,15)),  # span cropped past the cue
    ("I wouldn't use budget.xlsx",None),
    ("we haven't approved budget.xlsx",None),
    ("it wasn't budget.xlsx",None),
    ("donʼt use budget.xlsx",None),  # U+02BC modifier letter apostrophe
    ("don‘t use budget.xlsx",None),  # U+2018 left single quote
    ("don＇t use budget.xlsx",None),  # U+FF07 fullwidth apostrophe
    ("ignore budget.xlsx",None),
    ("leave out budget.xlsx",None),
    ("neither budget.xlsx nor notes.txt",None),
    ("anything besides budget.xlsx",None),
    ("aside from budget.xlsx use report.docx",None),
    ("except for budget.xlsx",None),
])
def test_f1_negation_anywhere_in_turn_never_confirms(raw,span,tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget.xlsx","report.docx"))
    result=retrieval(log,sources,raw,proposal="budget.xlsx",span=span)
    state,service,p=registered(sources,result)
    assert state!=BindingState.CONFIRMED
    assert p.degraded=="EXPRESSION_GROUNDING_UNESTABLISHED" and p.grounding.status=="NEGATED_REFERENCE"


@pytest.mark.parametrize("raw",["update budget.xlsx","budget.xlsx","open notes.md","update the budget.xlsx now"])
def test_f1_positive_literals_are_not_negations(raw):
    assert not negated(raw)


@pytest.mark.parametrize("text,status",[
    ("I'm not done yet","COMPLETED"),
    ("please do not mark this done yet","COMPLETED"),
    ("please don't cancel this","ABANDONED"),
    ("do not pause","PAUSED"),
    ("never failed before","FAILED"),
    ("I haven't completed it","COMPLETED"),
    ("it wasn't done","COMPLETED"),
    ("they aren't done","COMPLETED"),
    ("it isnʼt done","COMPLETED"),
    ("hasn't failed","FAILED"),
    ("I wouldn't cancel","ABANDONED"),
])
def test_f2_negated_status_words_are_not_user_transitions(text,status,tmp_path):
    log,sources,rec,root=setup(tmp_path)
    task,head=opened(rec)
    with pytest.raises(ValueError,match="EXPLICIT_USER_TRANSITION_REQUIRED"):
        rec.task_state(task,head.record_id,intake=intake(text),status=status)
    assert log.load().task(task).payload["status"]=="OPEN"


def test_f2_explicit_transitions_still_accepted(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    task,head=opened(rec)
    assert rec.task_state(task,head.record_id,intake=intake("pause"),status="PAUSED").persisted
    assert rec.task_state(task,log.load().task(task).record_id,intake=intake("resume"),status="OPEN").persisted
    assert rec.task_state(task,log.load().task(task).record_id,intake=intake("done"),status="COMPLETED").persisted


@pytest.fixture
def swap_registry():
    saved=module._VERIFIERS
    def swap(registry): module._VERIFIERS=MappingProxyType(registry)
    yield swap
    module._VERIFIERS=saved


@pytest.mark.parametrize("registry",[{},{"uri.verifier.m36_fixture":("BYTE_EVIDENCE","2",fixture_verifier)}])
def test_f3_registry_mismatch_fails_closed_not_quarantined(registry,swap_registry,tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    (root/"budget.xlsx").write_bytes(b"FAIL")
    task,head=opened(rec); src=s.fingerprint(s.scan().locators[0])
    verdict=rec.invoke_verifier(claimed(rec,task,src).record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    assert verdict.persisted
    swap_registry(registry)
    with pytest.raises(VerifierRegistryMismatch): log.load()
    assert not list(log.path.glob("quarantine/*.json"))
    write=claimed(rec,task,src)
    assert not write.persisted and write.reason=="VERIFIER_REGISTRY_MISMATCH"
    ts_res=rec.task_state(task,head.record_id,intake=intake("pause"),status="PAUSED")
    assert not ts_res.persisted and ts_res.reason=="VERIFIER_REGISTRY_MISMATCH"
    fg_res=rec.forget((task,),intake=intake("forget"))
    assert not fg_res.persisted and fg_res.reason=="VERIFIER_REGISTRY_MISMATCH"
    ot_id,ot_res=rec.open_task(intake("open new task"),"open new task")
    assert not ot_res.persisted and ot_res.reason=="VERIFIER_REGISTRY_MISMATCH"
    result=retrieval(log,s,"resume the budget task")
    assert result.degraded=="VERIFIER_REGISTRY_MISMATCH"


def test_f3_verified_completion_does_not_reopen_without_registry(swap_registry,tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    task,head=opened(rec); bound=bind(log,s,"budget.xlsx")
    assert rec.task_state(task,head.record_id,intake=intake("budget.xlsx"),bindings=(bound,)).persisted
    head=log.load().task(task); raw=intake("complete"); obs=_runtime_observation(raw,"VERIFIED_COMPLETE")
    verdict=rec.invoke_verifier(claimed(rec,task,bound.source).record_ids[0],"uri.verifier.m36_fixture",trace_id="c"*32,session_id="session")
    assert rec.task_state(task,head.record_id,intake=raw,status="COMPLETED",runtime_action=obs,last_outcome_record_id=verdict.record_ids[0]).persisted
    swap_registry({})
    with pytest.raises(VerifierRegistryMismatch): log.load()
    swap_registry({"uri.verifier.m36_fixture":("BYTE_EVIDENCE","1",fixture_verifier)})
    assert log.load().task(task).payload["status"]=="COMPLETED"


def test_f3_tampered_receipt_is_still_quarantined(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    task,head=opened(rec); src=s.fingerprint(s.scan().locators[0])
    verdict=rec.invoke_verifier(claimed(rec,task,src).record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    record=log.load().records[verdict.record_ids[0]]
    (log.path/"attestations"/(record.payload["attestation_ref"]+".json")).write_bytes(b"{}")
    restored=log.load()
    assert record.record_id not in restored.records and restored.recovery_ids


def test_f4_forget_cannot_hide_verdict(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    (root/"budget.xlsx").write_bytes(b"FAIL")
    task,head=opened(rec); src=s.fingerprint(s.scan().locators[0])
    verdict=rec.invoke_verifier(claimed(rec,task,src).record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    assert claimed(rec,task,src).persisted
    hidden=rec.forget(verdict.record_ids,intake=intake("forget that"))
    assert not hidden.persisted and hidden.reason=="INVALID_HIDE_TARGET"
    package=build_context(log.load(),s,task).to_dict()
    assert any(o["record_id"]==verdict.record_ids[0] and o["verification_status"]=="FAILED" for o in package["recent_outcomes"])


def test_f4_forget_cannot_strand_task_but_can_hide_whole_task(tmp_path):
    log,s,rec,root=setup(tmp_path)
    task,head=opened(rec)
    assert rec.forget((head.record_id,),intake=intake("forget")).reason=="INVALID_HIDE_TARGET"
    assert log.load().task(task).record_id==head.record_id
    assert rec.forget((log.load().openings[task],),intake=intake("forget")).persisted
    assert log.load().task(task) is None


def test_f5_dot_separated_stem_is_a_collision(tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget-v2.xlsx","budget.v2.xlsx"))
    result=retrieval(log,sources,"budget v2")
    assert len(result.collision.matching_ids)==2 and result.collision.complete
    assert {c.source.relpath for c in result.candidates}>={"budget-v2.xlsx","budget.v2.xlsx"}
    state,service,p=registered(sources,result)
    assert state!=BindingState.CONFIRMED


def test_f6_unrelated_hidden_file_does_not_block_exact_title(tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget.xlsx",))
    (root/".DS_Store").write_bytes(b"finder metadata"); (root/".~lock.budget.xlsx#").write_bytes(b"lock")
    result=retrieval(log,sources,"update budget.xlsx",proposal="budget.xlsx",span=(7,18))
    assert result.collision.complete and not result.degraded
    state,service,p=registered(sources,result)
    assert state==BindingState.CONFIRMED


def test_f6_hidden_file_with_matching_name_still_blocks(tmp_path):
    log,sources,rec,root=setup(tmp_path,("notes.md",))
    (root/".notes.md").write_bytes(b"hidden twin")
    result=retrieval(log,sources,".notes.md")
    assert not result.collision.complete and result.collision.reason=="HIDDEN_NAME_MATCH"


def test_f6_hidden_directory_still_makes_scope_incomplete(tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget.xlsx",))
    (root/".git").mkdir(); (root/".git"/"budget.xlsx").write_bytes(b"x")
    assert not sources.scan().complete
