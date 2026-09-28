from dataclasses import replace
import json
import pytest
from uri_v1.memory.contracts import RecordKind,Authority,VerificationStatus,canonical,digest
from uri_v1.memory.recorder import _bootstrap_verifiers,_runtime_observation
import uri_v1.memory.recorder as module
from tests.test_m36_memory_support import setup,opened,intake,bind,USER


def fixture_verifier(claim,sources):
    """URI-owned byte-evidence fixture, no Office domain interpretation."""
    refs=[]
    for link in claim.payload["inputs"]:
        ref=sources.fingerprint(link["source_id"])
        assert ref and ref.content_sha256==link["content_sha256"]
        roots=sources.roots()
        from pathlib import Path
        data=(Path(roots[ref.root_id])/ref.relpath).read_bytes()
        refs.append((ref.source_id,ref.content_sha256,len(data)))
        if b"FAIL" in data: return VerificationStatus.FAILED,("d"*32,),refs
        if b"PARTIAL" in data: return VerificationStatus.PARTIALLY_VERIFIED,("d"*32,),refs
        if b"UNVERIFIABLE" in data: return VerificationStatus.UNVERIFIABLE,("d"*32,),refs
    return VerificationStatus.VERIFIED,("d"*32,),refs


def bootstrap():
    if not module._VERIFIERS: _bootstrap_verifiers({"uri.verifier.m36_fixture":("BYTE_EVIDENCE","1",fixture_verifier)})


def claimed(rec,task,source):
    return rec.outcome(task,action_label="actual byte evidence",inputs=({"source_id":source.source_id,"content_sha256":source.content_sha256},),
                       outputs=(),session_id="session",trace_id="b"*32)


def test_impersonation_and_actual_trusted_invocation(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    task,head=opened(rec); source=s.fingerprint(s.scan().locators[0])
    for forged in ({"verifier_id":"uri.verifier.m36_fixture"},{"provenance":"VERIFIER_RESULT"},{"verification_status":"VERIFIED"},{"capability":"xyz"}):
        with pytest.raises(ValueError): rec.outcome(task,action_label="claim",inputs=(),session_id="session",trace_id="a"*32,**forged)
    claim=claimed(rec,task,source); assert claim.persisted
    with pytest.raises(ValueError): rec.invoke_verifier(claim.record_ids[0],"arbitrary",trace_id="a"*32,session_id="session")
    result=rec.invoke_verifier(claim.record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    assert result.persisted,result
    record=log.load().records[result.record_ids[0]]
    assert record.authority==Authority.VERIFIED_OUTCOME
    copied=replace(record,record_id="e"*32)
    assert not log.append((copied,)).persisted
    with pytest.raises(ValueError): rec._verifier_write(copied,fixture_verifier,"forged")
    assert rec.outcome(task,action_label="later harness success",inputs=(),session_id="session",trace_id="c"*32).persisted
    assert record.record_id in {r.record_id for r in log.load().current(RecordKind.OUTCOME,task)}
    receipt=log.path/"attestations"/(record.payload["attestation_ref"]+".json")
    raw=json.loads(receipt.read_bytes()); raw["record_digest"]="0"*64; receipt.write_bytes(canonical(raw))
    restored=log.load()
    assert record.record_id not in restored.records
    assert restored.records[claim.record_ids[0]].authority==Authority.CLAIMED_OUTCOME
    assert restored.recovery_ids


@pytest.mark.parametrize("marker,status",[(b"FAIL","FAILED"),(b"PARTIAL","PARTIALLY_VERIFIED"),(b"UNVERIFIABLE","UNVERIFIABLE")])
def test_negative_verdict_not_superseded_by_harness(marker,status,tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    (root/"budget.xlsx").write_bytes(marker)
    task,head=opened(rec); source=s.fingerprint(s.scan().locators[0])
    claim=claimed(rec,task,source)
    result=rec.invoke_verifier(claim.record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    assert result.persisted
    r=log.load().records[result.record_ids[0]]
    assert r.payload["verification_status"]==status and r.authority==Authority.VERIFIER_ATTESTED
    assert claimed(rec,task,source).persisted
    assert r.record_id in {x.record_id for x in log.load().current(RecordKind.OUTCOME,task)}
    for _ in range(5): assert claimed(rec,task,source).persisted
    from uri_v1.memory.context_package import build_context
    package=build_context(log.load(),s,task).to_dict()
    assert any(x["record_id"]==r.record_id and x["authority"]=="VERIFIER_ATTESTED" for x in package["recent_outcomes"])


def test_verified_completion_requires_current_refs_and_event_capability(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    task,head=opened(rec); bound=bind(log,s,"budget.xlsx")
    assert rec.observe(bound.source,session_id="session",trace_id="a"*32).persisted
    assert rec.task_state(task,head.record_id,intake=intake("budget.xlsx"),bindings=(bound,)).persisted
    head=log.load().task(task); raw=intake("complete")
    with pytest.raises(ValueError): rec.task_state(task,head.record_id,intake=raw,status="COMPLETED",runtime_action="VERIFIED_COMPLETE")
    obs=_runtime_observation(raw,"VERIFIED_COMPLETE")
    assert not rec.task_state(task,head.record_id,intake=raw,status="COMPLETED",runtime_action=obs).persisted
    claim=claimed(rec,task,bound.source)
    verdict=rec.invoke_verifier(claim.record_ids[0],"uri.verifier.m36_fixture",trace_id="c"*32,session_id="session")
    assert rec.task_state(task,head.record_id,intake=raw,status="COMPLETED",runtime_action=obs,last_outcome_record_id=verdict.record_ids[0]).persisted
