"""Trusted qualification driver helpers, using real S1 for every binding."""
from pathlib import Path
import uuid
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.sources import SourceRegistry
from uri_v1.memory.recorder import Recorder
from uri_v1.memory.retrieval import Retriever
from uri_v1.memory.contracts import MemoryQuery
from uri_v1.memory.uri_adapter.envelope import URIIntake, MemoryAdapter
from uri_v1.memory.uri_adapter.links import capture_binding
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended

USER = str(uuid.UUID(int=1))
NOW = "2026-09-28T12:00:00+00:00"


def intake(raw,*,user=USER,session="session",ref="file",span=None,round_id=None):
    if span is None: span=(0,len(raw))
    return URIIntake().capture(user,session,uuid.uuid4().hex,uuid.uuid4().hex,raw,spans={ref:span},round_id=round_id)


def setup(tmp_path,files=("budget.xlsx",)):
    root=tmp_path/"authorized"; root.mkdir(exist_ok=True)
    for f in files:
        path=root/f; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b"actual qualification file:"+f.encode())
    log=MemoryLog(USER,tmp_path/"private")
    sources=SourceRegistry(log); sources.register(root)
    return log,sources,Recorder(log,sources,clock=lambda:NOW),root


def retrieval(log,sources,raw,*,proposal=None,span=None,**kw):
    i=intake(raw,span=span)
    if kw.get("attachment_source_ids"):
        kw["attachment_manifest"]=URIIntake().capture_attachments(i,kw["attachment_source_ids"])
    q=MemoryQuery(USER,i.session_id,proposal or raw,now_utc=NOW,intake=i,**kw)
    return Retriever(log,sources).retrieve(q)


def resolve(log,sources,expression,*,task_id=None,service=None,ref_key="file",impact="CONSEQUENTIAL"):
    i=intake(expression,ref=ref_key)
    q=MemoryQuery(USER,i.session_id,expression,task_id=task_id,now_utc=NOW,intake=i,ref_key=ref_key)
    result=Retriever(log,sources).retrieve(q)
    projected=MemoryAdapter(sources).project(result)
    if projected.query is None: raise ValueError(projected.degraded)
    resolution=resolve_rar_deterministic_extended(projected.query).resolution
    built=build_clarification(projected.query,resolution,session_id=i.session_id,turn_id=i.turn_id,
                             wrong_binding_impact=impact,fact_sources=MemoryAdapter(sources).candidate_fact_sources(result))
    service=service or BindingService()
    binding=MemoryAdapter(sources).register(service,built,result,projected.query)
    return result,projected,service,binding


def bind(log,sources,name,ref_key="file"):
    result,p,service,b=resolve(log,sources,name,ref_key=ref_key)
    return capture_binding(service,b,result,sources,ref_key)


def opened(recorder,label="budget task"):
    task,result=recorder.open_task(intake(label),label)
    assert result.persisted,result
    return task,recorder.log.load().task(task)
