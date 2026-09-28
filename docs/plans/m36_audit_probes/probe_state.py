from types import MappingProxyType
import uri_v1.memory.recorder as module
from uri_v1.memory.recorder import _runtime_observation
from uri_v1.memory.contracts import RecordKind, TaskStatus
from uri_v1.memory.context_package import build_context
from tests.test_m36_memory_support import setup,opened,intake,bind
from tests.test_m36_memory_verifier import bootstrap, claimed, fixture_verifier

def test_negated_user_transitions(tmp_path):
    log,s,rec,root=setup(tmp_path)
    for text,status in (("I'm not done yet","COMPLETED"),("please don't cancel this","ABANDONED"),("do not pause","PAUSED")):
        task,head=opened(rec)
        r=rec.task_state(task,head.record_id,intake=intake(text),status=status)
        h=log.load().task(task)
        print(repr(text),"->",status,"persisted=",r.persisted,"head=",h.payload["status"],h.authority)

def test_registry_absent_or_upgraded_on_reload(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    (root/"budget.xlsx").write_bytes(b"FAIL")
    task,head=opened(rec); src=s.fingerprint(s.scan().locators[0])
    claim=claimed(rec,task,src)
    v=rec.invoke_verifier(claim.record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    assert v.persisted
    saved=module._VERIFIERS
    for label,reg in (("no-bootstrap",MappingProxyType({})),("version-2",MappingProxyType({"uri.verifier.m36_fixture":("BYTE_EVIDENCE","2",fixture_verifier)}))):
        module._VERIFIERS=reg
        idx=log.load()
        cur={r.record_id:r.payload["verification_status"] for r in idx.current(RecordKind.OUTCOME,task)}
        pkg=build_context(idx,s,task).to_dict()
        print(label,"verdict_loaded=",v.record_ids[0] in idx.records,"current_outcomes=",cur,"pkg.degraded=",pkg["degraded"],
              "pkg.outcomes=",[(o["verification_status"],o["authority"]) for o in pkg["recent_outcomes"]])
    module._VERIFIERS=saved

def test_verified_completion_lost_without_registry(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    task,head=opened(rec); bound=bind(log,s,"budget.xlsx")
    rec.observe(bound.source,session_id="session",trace_id="a"*32)
    rec.task_state(task,head.record_id,intake=intake("budget.xlsx"),bindings=(bound,))
    head=log.load().task(task); raw=intake("complete"); obs=_runtime_observation(raw,"VERIFIED_COMPLETE")
    claim=claimed(rec,task,bound.source)
    verdict=rec.invoke_verifier(claim.record_ids[0],"uri.verifier.m36_fixture",trace_id="c"*32,session_id="session")
    assert rec.task_state(task,head.record_id,intake=raw,status="COMPLETED",runtime_action=obs,last_outcome_record_id=verdict.record_ids[0]).persisted
    saved=module._VERIFIERS; module._VERIFIERS=MappingProxyType({})
    idx=log.load(); h=idx.task(task)
    print("without registry: head status=",h.payload["status"] if h else None,"open_tasks=",[t["status"] for t in idx.open_tasks()],"recovery=",len(idx.recovery_ids))
    module._VERIFIERS=saved
