"""Additional predeclared A2 failure, privacy and deterministic-boundary cases."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import uuid

import pytest
from uri_v1.memory.contracts import *
from uri_v1.memory.recorder import _runtime_observation
from uri_v1.memory.context_package import build_context
from uri_v1.memory.uri_adapter.envelope import MemoryAdapter,URIIntake
from tests.test_m36_memory_support import setup,opened,intake,bind,retrieval,USER,NOW


@pytest.mark.parametrize("before,after",[
    ("OPEN","PAUSED"),("OPEN","WAITING_USER"),("OPEN","COMPLETED"),("OPEN","FAILED"),("OPEN","ABANDONED"),
    ("WAITING_USER","PAUSED"),("WAITING_USER","OPEN"),("WAITING_USER","COMPLETED"),("WAITING_USER","FAILED"),("WAITING_USER","ABANDONED"),
    ("PAUSED","OPEN"),("PAUSED","COMPLETED"),("PAUSED","FAILED"),("PAUSED","ABANDONED"),
])
def test_all_admitted_transition_edges(before,after,tmp_path):
    log,s,rec,root=setup(tmp_path); task,head=opened(rec)
    text={"PAUSED":"pause","OPEN":"resume","WAITING_USER":"clarification","COMPLETED":"complete","FAILED":"failed","ABANDONED":"cancel"}
    def transition(status):
        i=intake(text[status]); return rec.task_state(task,log.load().task(task).record_id,intake=i,status=status,
            runtime_action=_runtime_observation(i,"CLARIFICATION") if status=="WAITING_USER" else None)
    if before!="OPEN": assert transition(before).persisted
    assert transition(after).persisted
    assert log.load().task(task).payload["status"]==after


def test_untrusted_transitions_and_same_head_concurrency(tmp_path):
    log,s,rec,root=setup(tmp_path); task,head=opened(rec)
    with pytest.raises(ValueError): rec.task_state(task,head.record_id,intake=intake("use source"),status="COMPLETED")
    with pytest.raises(ValueError): MemoryRecord(USER,RecordKind.TASK_STATE,Provenance.MODEL_DERIVED,plain(head.payload),task_id=task)
    def pause(n): return rec.task_state(task,head.record_id,intake=intake("pause"),status="PAUSED")
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(pause,range(2)))
    assert sum(r.persisted for r in results)==1 and any(r.reason=="CONFLICT" for r in results)


def test_load_fork_never_picks_later_timestamp(tmp_path):
    log,s,rec,root=setup(tmp_path); task,head=opened(rec)
    assert rec.task_state(task,head.record_id,intake=intake("pause"),status="PAUSED").persisted
    # Explicit corruption fixture: a second otherwise trusted branch at same parent.
    p=plain(head.payload); eid=uuid.uuid4().hex; p.update(status="WAITING_USER",transition_evidence_ids=[eid])
    fork=replace(head,record_id=uuid.uuid4().hex,payload=p,supersedes=(head.record_id,),recorded_at="2026-09-28T13:00:00+00:00")
    with log.guard(): rec._event((fork,),"RUNTIME","CLARIFICATION",eid)
    assert not log.append((fork,)).persisted
    with next(log.path.glob("log-*.jsonl")).open("ab") as f: f.write(canonical(fork.to_dict())+b"\n")
    index=log.load(); assert task in index.conflicts and index.task(task) is None
    assert build_context(index,s,task).to_dict()["degraded"]=="CONFLICT"


@pytest.mark.parametrize("bad",["forward","cross_task","cross_kind","self_cycle","authority","event_digest"])
def test_illegal_serialized_heads_quarantined(bad,tmp_path):
    log,s,rec,root=setup(tmp_path); task,head=opened(rec); other,other_head=opened(rec,"other")
    raw=head.to_dict(); raw["record_id"]=uuid.uuid4().hex; eid=uuid.uuid4().hex
    raw["payload"]["transition_evidence_ids"]=[eid]; raw["payload"]["status"]="PAUSED"
    raw["supersedes"]=[{"forward":"d"*32,"cross_task":other_head.record_id,"cross_kind":head.payload["opening_record_id"],"self_cycle":raw["record_id"]}.get(bad,head.record_id)]
    if bad=="authority": raw["authority"]="VERIFIED_OUTCOME"
    if bad not in ("authority","event_digest"):
        record=MemoryRecord.from_dict(raw)
        with log.guard(): rec._event((record,),"USER","PAUSE",eid)
    with next(log.path.glob("log-*.jsonl")).open("ab") as f: f.write(canonical(raw)+b"\n")
    index=log.load()
    assert raw["record_id"] not in index.records and index.task(task).record_id==head.record_id and index.recovery_ids


def test_real_64mib_and_offline_policy_no_hydration(tmp_path,monkeypatch):
    log,s,rec,root=setup(tmp_path)
    with (root/"large.xlsx").open("wb") as f: f.truncate(64*1024*1024+1)
    large=next(l for l in s.scan().locators if l.relpath=="large.xlsx")
    ref=s.fingerprint(large)
    assert ref.identity_status==IdentityStatus.HASH_UNAVAILABLE_SIZE_CAP and ref.content_sha256 is None
    r=retrieval(log,s,"large.xlsx"); assert MemoryAdapter(s).project(r).query is None
    ordinary=next(l for l in s.scan().locators if l.relpath=="budget.xlsx")
    original=Path.stat
    def offline(path,*args,**kwargs):
        info=original(path,*args,**kwargs)
        if path.name=="budget.xlsx" and kwargs.get("follow_symlinks",True):
            return SimpleNamespace(st_dev=info.st_dev,st_ino=info.st_ino,st_size=info.st_size,st_mtime_ns=info.st_mtime_ns,st_mode=info.st_mode,st_file_attributes=0x00400000)
        return info
    monkeypatch.setattr(Path,"stat",offline)
    assert s.fingerprint(ordinary).identity_status==IdentityStatus.HASH_UNAVAILABLE_POLICY


def test_attachment_membership_and_mime_cannot_be_model_flags(tmp_path):
    log,s,rec,root=setup(tmp_path); sid=s.scan().locators[0].source_id
    result=retrieval(log,s,"the spreadsheet",attachment_source_ids=(sid,))
    q=replace(result.query,attachment_manifest=None)
    p=MemoryAdapter(s).project(replace(result,query=q))
    assert p.query.deterministic_anchor is None and not p.query.candidates[0].is_attachment
    manifest=URIIntake().capture_attachments(result.query.intake,(sid,),media_classes=((sid,"script"),))
    p=MemoryAdapter(s).project(replace(result,query=replace(result.query,attachment_manifest=manifest)))
    assert p.query.deterministic_anchor is None


def test_real_process_writers_serialize_and_reset(tmp_path):
    log,s,rec,root=setup(tmp_path); sid=s.scan().locators[0].source_id
    code="""import sys
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.sources import SourceRegistry
from uri_v1.memory.recorder import Recorder
log=MemoryLog(sys.argv[1],sys.argv[2]); r=Recorder(log,SourceRegistry(log)).observe(sys.argv[3],session_id='session',trace_id='a'*32)
assert r.persisted,r
"""
    children=[subprocess.Popen([sys.executable,"-c",code,USER,str(log.root),sid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(4)]
    for child in children:
        out,err=child.communicate(timeout=30); assert child.returncode==0,err
    assert len(log.load().records)==4
    log.reset(); assert not log.load().records and (root/"budget.xlsx").exists()


def test_correction_lineage_and_context_fail_closed_budget(tmp_path):
    log,s,rec,root=setup(tmp_path,("a.xlsx","b.xlsx")); task,head=opened(rec)
    a,b=[bind(log,s,name) for name in ("a.xlsx","b.xlsx")]
    assert rec.observe(a.source,session_id="session",trace_id="a"*32).persisted
    assert rec.task_state(task,head.record_id,intake=intake("a.xlsx"),bindings=(a,)).persisted
    assert rec.derivative(task,result_id="summary",result_version=1,content_sha256="d"*64,
           derived_from=({"source_id":a.source.source_id,"content_sha256":a.source.content_sha256},),derivative_kind="summary",session_id="session",trace_id="a"*32).persisted
    assert rec.correction(task,"file",log.load().task(task).record_id,intake=intake("use b.xlsx"),replacement=b).persisted
    p=build_context(log.load(),s,task).to_dict()
    assert p["derivatives"][0]["freshness"]=="SUPERSEDED_REFERENCE"
    tiny=build_context(log.load(),s,task,max_bytes=1000).to_dict()
    assert tiny["degraded"]=="BUDGET_EXCEEDED" and not tiny["references"]


def test_core_adapter_import_boundaries_and_frozen_scope():
    root=Path(__file__).resolve().parents[1]
    banned={"uri_core","socket","requests","httpx","openai","anthropic","ollama"}
    for path in (root/"uri_v1/memory").rglob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or ""] if isinstance(node,ast.ImportFrom) and node.level==0 else []
            for mod in modules:
                assert mod.split(".")[0] not in banned
                assert mod!="uri_v1.turn.rar_deterministic"
                if "uri_adapter" not in path.parts and mod.startswith("uri_v1."):
                    assert mod=="uri_v1.user_storage" or mod.startswith("uri_v1.memory.")
    changed=subprocess.check_output(["git","diff","--name-only","291c9daa48435200c4b56857d0e3bc630016e82a","--","uri_v1","uri_core","uri_ui","tests","scripts","fixtures"],cwd=root,text=True).splitlines()
    assert all(p.startswith(("uri_v1/memory/","tests/test_m36_","scripts/m36_","fixtures/m36_memory/")) for p in changed)
    from scripts.m33_3_r_anchors import require_anchors
    assert require_anchors()["ok"]
