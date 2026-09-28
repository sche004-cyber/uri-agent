from dataclasses import replace
import json
import uuid
import pytest
from uri_v1.memory.contracts import *
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.recorder import _runtime_observation
from tests.test_m36_memory_support import setup,opened,intake,bind,USER,NOW


def test_restart_torn_tail_idempotency_quarantine(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    task,head=opened(rec)
    path=next(log.path.glob("log-*.jsonl"))
    with path.open("ab") as f: f.write(b'{"torn":')
    assert rec.task_state(task,head.record_id,intake=intake("pause"),status=TaskStatus.PAUSED).persisted
    loaded=MemoryLog(USER,log.root).load()
    assert loaded.task(task).payload["status"]==TaskStatus.PAUSED
    assert len(loaded.recovery_ids)==1
    assert len(list((log.path/"quarantine").glob("*.json")))==1
    log.load(); assert len(list((log.path/"quarantine").glob("*.json")))==1
    latest=loaded.task(task)
    assert log.append((latest,)).persisted
    assert len([r for r in log.load().records.values() if r.record_id==latest.record_id])==1
    assert not log.append((replace(latest,recorded_at="2026-09-28T12:01:00+00:00"),)).persisted


@pytest.mark.parametrize("stage",["before_write","after_body","after_newline","flush","fsync","readback"])
def test_fault_persistence_truthful_and_retry(stage,tmp_path):
    log,sources,rec,root=setup(tmp_path)
    task,head=opened(rec)
    fired=[]
    def fault(at):
        if at==stage and not fired: fired.append(at); raise OSError("INJECTED_"+stage)
    log.fault=fault
    result=rec.task_state(task,head.record_id,intake=intake("pause"),status=TaskStatus.PAUSED)
    assert not result.persisted
    log.fault=None
    # Next valid append remains readable after uncertain/torn writes.
    h=log.load().task(task)
    again=rec.task_state(task,h.record_id,intake=intake("checkpoint"))
    if again.reason=="CONFLICT":
        # Framing recovered a fully valid unterminated prior state. Never replay
        # the stale expected head: inspect the recovered head and retry explicitly.
        h=log.load().task(task)
        assert h.payload["status"]=="PAUSED"
        again=rec.task_state(task,h.record_id,intake=intake("checkpoint"))
    assert again.persisted
    assert again.record_ids[0] in MemoryLog(USER,log.root).load().records


def test_durable_off_unknown_schema_and_authority(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    log.set_durable_enabled(False)
    _,r=rec.open_task(intake("budget"),"budget"); assert not r.persisted and r.reason=="DURABLE_OFF"
    log.set_durable_enabled(True)
    task,head=opened(rec)
    raw=head.to_dict(); raw["authority"]="VERIFIED_OUTCOME"
    with next(log.path.glob("log-*.jsonl")).open("ab") as f: f.write(canonical(raw)+b"\n")
    assert len(log.load().recovery_ids)==1
    (log.path/"settings.json").write_text("invalid")
    assert not rec.task_state(task,head.record_id,intake=intake("pause"),status="PAUSED").persisted


def test_task_chain_concurrency_terminal_and_month_rollover(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    task,head=opened(rec)
    for status in ("PAUSED","OPEN","WAITING_USER","PAUSED","OPEN","COMPLETED"):
        old=log.load().task(task)
        rec.clock=lambda:"2026-10-01T00:00:00+00:00"
        raw={"PAUSED":"pause","OPEN":"resume","COMPLETED":"complete","WAITING_USER":"clarification"}[status]
        user_input=intake(raw)
        assert rec.task_state(task,old.record_id,intake=user_input,status=status,
                              runtime_action=_runtime_observation(user_input,"CLARIFICATION") if status=="WAITING_USER" else None).persisted
        assert not rec.task_state(task,old.record_id,intake=intake("pause"),status="PAUSED").persisted
    head=log.load().task(task)
    assert not rec.task_state(task,head.record_id,intake=intake("resume"),status="OPEN").persisted
    corrected=rec.correction(task,None,head.record_id,intake=intake("correct status"),corrected_status="PAUSED",note="completion was incorrect")
    assert corrected.persisted,corrected
    assert MemoryLog(USER,log.root).load().task(task).payload["status"]=="PAUSED"
    assert len(list(log.path.glob("log-*.jsonl")))==2


def test_correction_pairs_full_history_interruption_and_retry(tmp_path):
    log,sources,rec,root=setup(tmp_path,("a.xlsx","b.xlsx","c.xlsx"))
    task,head=opened(rec)
    a,b,c=[bind(log,sources,x) for x in ("a.xlsx","b.xlsx","c.xlsx")]
    assert rec.observe(a.source,session_id="session",trace_id="a"*32).persisted
    assert rec.task_state(task,head.record_id,intake=intake("use a.xlsx"),bindings=(a,)).persisted
    head=log.load().task(task); op=uuid.uuid4().hex; count=[]
    def fault(at):
        if at=="after_record" and not count: count.append(at); raise OSError("INTERRUPTED_PAIR")
    log.fault=fault
    r=rec.correction(task,"file",head.record_id,intake=intake("use b.xlsx"),replacement=b,operation_id=op)
    assert not r.persisted and r.per_record==(True,False)
    index=MemoryLog(USER,log.root).load()
    assert index.task(task).record_id==head.record_id
    assert len(index.pending_corrections)==1
    log.fault=None
    assert rec.correction(task,"file",head.record_id,intake=intake("retry b.xlsx"),replacement=b,operation_id=op).persisted
    h=log.load().task(task)
    assert h.payload["references"][0]["source_id"]==b.source.source_id
    assert rec.correction(task,"file",h.record_id,intake=intake("use c.xlsx"),replacement=c).persisted
    index=log.load(); h=index.task(task)
    assert h.payload["references"][0]["source_id"]==c.source.source_id
    assert len(index.history(h.record_id))==4
    assert len([r for r in index.records.values() if r.kind==RecordKind.CORRECTION])==2
    with pytest.raises(ValueError): rec.correction(task,"file",h.record_id,intake={"raw":"c.xlsx"},replacement=c)


def test_hide_and_cross_user(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    task,head=opened(rec)
    assert rec.forget((head.record_id,),intake=intake("forget")).persisted
    assert log.load().task(task) is None
    other=MemoryLog(str(uuid.UUID(int=2)),log.root)
    assert other.load().records=={}
    assert not other.append((head,)).persisted
