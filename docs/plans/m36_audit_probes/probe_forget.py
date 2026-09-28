from uri_v1.memory.context_package import build_context
from tests.test_m36_memory_support import setup,opened,intake
from tests.test_m36_memory_verifier import bootstrap, claimed

def test_forget_hides_failed_verdict(tmp_path):
    bootstrap(); log,s,rec,root=setup(tmp_path)
    (root/"budget.xlsx").write_bytes(b"FAIL")
    task,head=opened(rec); src=s.fingerprint(s.scan().locators[0])
    c=claimed(rec,task,src)
    v=rec.invoke_verifier(c.record_ids[0],"uri.verifier.m36_fixture",trace_id="a"*32,session_id="session")
    claimed(rec,task,src)
    f=rec.forget(v.record_ids,intake=intake("forget that"))
    pkg=build_context(log.load(),s,task).to_dict()
    print("forget persisted=",f.persisted,"outcomes=",[(o["verification_status"],o["authority"]) for o in pkg["recent_outcomes"]],"degraded=",pkg["degraded"])
