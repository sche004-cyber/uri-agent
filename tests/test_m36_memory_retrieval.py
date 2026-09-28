from dataclasses import replace
import subprocess
import sys
import json
import uuid
import pytest
from uri_v1.memory.contracts import MemoryQuery,canonical,RecordKind
from uri_v1.memory.retrieval import Retriever,selectors
from uri_v1.memory.context_package import build_context
from uri_v1.memory.telemetry import Telemetry
from uri_v1.memory.uri_adapter.envelope import MemoryAdapter
from tests.test_m36_memory_support import setup,opened,intake,bind,retrieval,USER,NOW


def reference_task(log,s,rec,label="budget task",name="budget.xlsx"):
    task,head=opened(rec,label); bound=bind(log,s,name)
    assert rec.observe(bound.source,session_id="session",trace_id="a"*32).persisted
    assert rec.task_state(task,head.record_id,intake=intake("use "+name),bindings=(bound,),next_step="inspect source").persisted
    return task,bound


def test_session_skip_telemetry_and_determinism(tmp_path):
    log,s,rec,root=setup(tmp_path)
    sid=s.scan().locators[0].source_id
    q=MemoryQuery(USER,"session","now open it",session_source_ids=(sid,),session_confirmed=True,now_utc=NOW,intake=intake("now open it"))
    telemetry=Telemetry(log)
    log.load=lambda: (_ for _ in ()).throw(AssertionError("durable read forbidden"))
    a=Retriever(log,s,telemetry).retrieve(q); b=Retriever(log,s,telemetry).retrieve(q)
    assert a.candidates==b.candidates and a.collision==b.collision
    assert a.telemetry["durable_reads"]==0 and a.telemetry["skip_reason"]=="SKIPPED_SESSION_CONFIRMED"
    raw=next(log.path.glob("telemetry-*.jsonl")).read_text()
    assert "budget.xlsx" not in raw and "now open it" not in raw


def test_temporal_task_recall_20_unrelated_tasks_and_subprocess_restart(tmp_path):
    log,s,rec,root=setup(tmp_path,("accounts.xlsx",))
    rec.clock=lambda:"2026-09-27T12:00:00+00:00"
    task,bound=reference_task(log,s,rec,"finances","accounts.xlsx")
    assert rec.task_state(task,log.load().task(task).record_id,intake=intake("pause"),status="PAUSED").persisted
    rec.clock=lambda:"2026-09-28T01:00:00+00:00"
    for n in range(21): opened(rec,f"unrelated {n}")
    raw="the spreadsheet from yesterday's task"
    result=retrieval(log,s,raw,user_timezone="Asia/Kolkata")
    assert len(result.candidates)==1 and result.candidates[0].source.source_id==bound.source.source_id
    code="""import sys,json
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.sources import SourceRegistry
from uri_v1.memory.retrieval import Retriever
from uri_v1.memory.contracts import MemoryQuery
from uri_v1.memory.uri_adapter.envelope import URIIntake
user,root=sys.argv[1:]
log=MemoryLog(user,root)
paused=log.load().open_tasks(statuses=('PAUSED',))
raw=\"the spreadsheet from yesterday's task\"
i=URIIntake().capture(user,'fresh','new','a'*32,raw,spans={'file':(0,len(raw))})
q=MemoryQuery(user,'fresh',raw,intake=i,now_utc='2026-09-28T12:00:00+00:00',user_timezone='Asia/Kolkata')
r=Retriever(log,SourceRegistry(log)).retrieve(q)
print(json.dumps({'tasks':paused,'ids':[c.source.source_id for c in r.candidates]}))
"""
    completed=subprocess.run([sys.executable,"-c",code,USER,str(log.root)],capture_output=True,text=True,check=True)
    restarted=json.loads(completed.stdout)
    assert len(restarted["tasks"])==1 and restarted["tasks"][0]["task_id"]==task
    assert restarted["ids"]==[bound.source.source_id]
    assert restarted["tasks"][0]["binding_authority"]=="HISTORICAL_BINDING"


def test_calendar_timezone_boundaries_and_unsupported(tmp_path):
    log,s,rec,root=setup(tmp_path)
    q=MemoryQuery(USER,"session","yesterday's task",now_utc="2026-09-28T00:30:00+00:00",user_timezone="America/New_York",intake=intake("yesterday's task"))
    assert selectors(q)[2]==("2026-09-26T04:00:00+00:00","2026-09-27T04:00:00+00:00")
    q=replace(q,reference_expression="last week",intake=intake("last week"))
    assert selectors(q)[2]==("2026-09-14T04:00:00+00:00","2026-09-21T04:00:00+00:00")
    for raw in ("tomorrow task","today yesterday task","recently spreadsheet"):
        assert retrieval(log,s,raw).degraded=="UNSUPPORTED_TEMPORAL_SELECTOR"
    assert retrieval(log,s,"yesterday task",user_timezone="invalid").degraded=="TIMEZONE_REQUIRED"


def test_used_timestamp_is_not_a_later_pause_timestamp(tmp_path):
    log,s,rec,root=setup(tmp_path)
    rec.clock=lambda:"2026-09-27T12:00:00+00:00"
    task,bound=reference_task(log,s,rec,"finances","budget.xlsx")
    rec.clock=lambda:NOW
    assert rec.task_state(task,log.load().task(task).record_id,intake=intake("pause"),status="PAUSED").persisted
    used=retrieval(log,s,"spreadsheet task last used yesterday")
    assert [c.source.source_id for c in used.candidates]==[bound.source.source_id]
    updated=retrieval(log,s,"spreadsheet task last updated yesterday")
    assert not updated.candidates


def test_edited_live_rediscovery_stale_derivative_and_context_privacy(tmp_path):
    log,s,rec,root=setup(tmp_path)
    task,bound=reference_task(log,s,rec)
    link={"source_id":bound.source.source_id,"content_sha256":bound.source.content_sha256}
    assert rec.derivative(task,result_id="summary",result_version=1,content_sha256="d"*64,derived_from=(link,),derivative_kind="summary",session_id="session",trace_id="a"*32).persisted
    other,_=opened(rec,"unrelated private task")
    (root/"budget.xlsx").write_bytes(b"edited")
    r=retrieval(log,s,"budget.xlsx",task_id=task)
    assert r.candidates and r.candidates[0].source.content_sha256!=bound.source.content_sha256
    package=build_context(log.load(),s,task).to_dict()
    assert package["references"][0]["freshness"]=="STALE_SOURCE"
    assert package["derivatives"][0]["freshness"]=="DERIVATIVE_STALE"
    assert other not in canonical(package).decode() and "unrelated private task" not in canonical(package).decode()
    assert bound.source.source_id in canonical(package).decode() and len(canonical(package))<=8192
    (root/"budget.xlsx").unlink()
    r=retrieval(log,s,"budget.xlsx",task_id=task)
    assert not r.candidates and r.stale


def test_task_ambiguity_paused_discovery_budget_and_terminal(tmp_path):
    log,s,rec,root=setup(tmp_path,("budget.xlsx","other.xlsx"))
    tasks=[]
    for name in ("budget.xlsx","other.xlsx"):
        task,bound=reference_task(log,s,rec,"budget task",name)
        assert rec.task_state(task,log.load().task(task).record_id,intake=intake("pause"),status="PAUSED").persisted
        tasks.append(task)
    assert len(log.load().open_tasks(statuses=("PAUSED",),label_tokens=("budget",)))==2
    r=retrieval(log,s,"continue the paused budget task")
    assert len(r.candidates)==2 and r.telemetry["matching_tasks"]==2
    assert MemoryAdapter(s).project(r).query is not None
    with pytest.raises(ValueError): log.load().open_tasks(max_tasks=1)
    assert retrieval(log,s,"budget task",max_candidates=1).degraded=="BUDGET_EXCEEDED"
    head=log.load().task(tasks[1])
    assert rec.task_state(tasks[1],head.record_id,intake=intake("complete"),status="COMPLETED").persisted
    assert len(log.load().open_tasks(statuses=("PAUSED",)))==1


def test_snapshot_stable_after_interleaved_recorder_write(tmp_path):
    log,s,rec,root=setup(tmp_path,("budget.xlsx","worker.py"))
    task,bound=reference_task(log,s,rec)
    r=retrieval(log,s,"budget sheet",task_id=task)
    adapter=MemoryAdapter(s); projected=adapter.project(r)
    assert rec.task_state(task,log.load().task(task).record_id,intake=intake("checkpoint"),next_step="interleaved update").persisted
    again=adapter.project(r)
    assert again.query==projected.query
    assert r.candidates[0].source.source_id==bound.source.source_id
