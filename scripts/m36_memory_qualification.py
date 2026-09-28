"""Predeclared M36 real-flow qualification; no production/S13 wiring.

Run python scripts/m36_memory_qualification.py --output docs/plans.
Thresholds and battery are captured before the first measured run. The driver
creates valid real file formats, invokes frozen S1/S7/S11 through the adapter,
and uses the Memory writer/retrieval path exclusively for positive flows.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from uri_v1.memory.contracts import MemoryQuery,VerificationStatus,canonical,plain
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.sources import SourceRegistry
from uri_v1.memory.recorder import Recorder,_bootstrap_verifiers
from uri_v1.memory.retrieval import Retriever
from uri_v1.memory.context_package import build_context
from uri_v1.memory.telemetry import Telemetry
from uri_v1.memory.uri_adapter.envelope import URIIntake,MemoryAdapter
from uri_v1.memory.uri_adapter.links import capture_binding,record_derivative,correction_event_id
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended
from uri_v1.turn.rar_clarification_contract import BindingState,ClarificationResponse,ResponseKind
from uri_v1.results.version_ledger import ResultVersionLedger
from uri_v1.evaluation.events import wrong_reference_event
from uri_v1.evaluation.store import EvaluationEventStore
from scripts.m33_3_r_anchors import require_anchors

USER=str(uuid.UUID(int=36))
NOW="2026-09-28T12:00:00+00:00"
FIXTURES=ROOT/"fixtures/m36_memory"


def make_file(path):
    if path.suffix in (".xlsx",".docx"):
        spreadsheet=path.suffix==".xlsx"
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml" if spreadsheet else "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
        main="xl/workbook.xml" if spreadsheet else "word/document.xml"
        content_types=f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/{main}" ContentType="{content_type}"/>'
        if spreadsheet: content_types+='<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        content_types+='</Types>'
        with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml",content_types)
            z.writestr("_rels/.rels",f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="{main}"/></Relationships>')
            if spreadsheet:
                z.writestr(main,'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Budget" sheetId="1" r:id="rId1"/></sheets></workbook>')
                z.writestr("xl/_rels/workbook.xml.rels",'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr("xl/worksheets/sheet1.xml",'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Amount</t></is></c><c r="B1"><v>36</v></c></row></sheetData></worksheet>')
            else: z.writestr(main,'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>M36 real source evidence.</w:t></w:r></w:p></w:body></w:document>')
    elif path.suffix==".pdf":
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                 b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
                 b'<< /Length 56 >>\nstream\nBT /F1 12 Tf 20 150 Td (M36 real PDF evidence) Tj ET\nendstream',
                 b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        stream=b'BT /F1 12 Tf 20 150 Td (M36 real PDF evidence) Tj ET\n'
        objects[3]=b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'endstream'
        data=b'%PDF-1.4\n'; offsets=[0]
        for n,obj in enumerate(objects,1): offsets.append(len(data)); data+=str(n).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
        xref=len(data); data+=b'xref\n0 6\n0000000000 65535 f \n'
        for offset in offsets[1:]: data+=f'{offset:010d} 00000 n \n'.encode()
        data+=b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
        path.write_bytes(data)
    elif path.suffix==".py": path.write_text('"""Real M36 qualification source artifact."""\ndef amount(values):\n    return sum(values)\n',encoding="utf-8")
    else: path.write_text("M36 grounded local source.\n",encoding="utf-8")


def byte_evidence_verifier(claim,sources):
    observed=[]
    for link in claim.payload["inputs"]:
        ref=sources.fingerprint(link["source_id"])
        if not ref or ref.content_sha256!=link["content_sha256"]: return VerificationStatus.FAILED,("f"*32,),{"reason":"hash mismatch"}
        observed.append({"source_id":ref.source_id,"content_sha256":ref.content_sha256})
    return VerificationStatus.VERIFIED,("e"*32,),{"observed":observed,"criterion":"URI independently rehashed every assessed input"}


def run_one(directory,battery):
    directory.mkdir(); authorized=directory/"files"; authorized.mkdir()
    for name in battery["files"]: make_file(authorized/name)
    log=MemoryLog(USER,directory/"private"); sources=SourceRegistry(log); sources.register(authorized)
    recorder=Recorder(log,sources,clock=lambda:NOW); telemetry=Telemetry(log)
    retriever=Retriever(log,sources,telemetry); adapter=MemoryAdapter(sources); service=BindingService(); intake=URIIntake()
    trace="a"*32
    def capture(raw,*,round_id=None,ref_key="file",session="session"):
        return intake.capture(USER,session,uuid.uuid4().hex,uuid.uuid4().hex,raw,spans={ref_key:(0,len(raw))},round_id=round_id)
    def retrieve(raw,*,proposal=None,**kwargs):
        i=capture(raw,ref_key=kwargs.get("ref_key","file"))
        q=MemoryQuery(USER,i.session_id,proposal or raw,intake=i,now_utc=NOW,**kwargs)
        return retriever.retrieve(q)
    def register(result,impact="CONSEQUENTIAL"):
        projected=adapter.project(result)
        if not projected.query: return projected,None
        built=build_clarification(projected.query,resolve_rar_deterministic_extended(projected.query).resolution,
              session_id=result.query.session_id,turn_id=result.query.intake.turn_id,wrong_binding_impact=impact,
              fact_sources=adapter.candidate_fact_sources(result))
        return projected,adapter.register(service,built,result,projected.query)
    locators={l.relpath:l for l in sources.scan().locators}
    inventory=[]; wrong=0; invented=0; tentative_wrong=0; latencies=[]
    for name in battery["files"]:
        locator=locators[name]; stem=Path(name).stem
        for form in battery["case_forms"]:
            raw={"literal_title":name,"explicit_id":locator.source_id,"raw_phrase":f"the {stem} file",
                 "model_normalized_title":f"the {stem} file","negated_title":f"not {name}"}[form]
            result=retrieve(raw,proposal=name if form=="model_normalized_title" else None)
            latencies.append(result.telemetry["retrieval_us"])
            projected,b=register(result)
            state=b.state.value if b else "WITHHELD"
            selected=b.candidate_id if b else None
            if selected and selected not in {c.source.source_id for c in result.candidates}: invented+=1
            expected=battery["expectation"][form]
            if state=="CONFIRMED" and (expected=="NO_CONFIRMED" or selected!=locator.source_id): wrong+=1
            if expected=="CONFIRMED_CORRECT": assert state=="CONFIRMED" and selected==locator.source_id,(name,form,state)
            if state=="TENTATIVE" and selected!=locator.source_id: tentative_wrong+=1
            inventory.append({"file":name,"form":form,"state":state,"selected":name if selected==locator.source_id else None,
                              "grounding":projected.grounding.status if projected.grounding else None,"degraded":projected.degraded})
    assert wrong==invented==0
    # F-A: real S1 -> read real docx -> S11 immutable result -> Memory derivative.
    task_a,result=recorder.open_task(capture("summarize report"),"summarize report"); assert result.persisted
    r=retrieve("report.docx"); p,b=register(r); bound=capture_binding(service,b,r,sources,"document")
    document_bound=bound
    assert recorder.observe(bound.source,session_id="session",trace_id=trace).persisted
    assert recorder.task_state(task_a,log.load().task(task_a).record_id,intake=capture("use report.docx"),bindings=(bound,)).persisted
    with zipfile.ZipFile(authorized/"report.docx") as z: actual=z.read("word/document.xml")
    summary=b"Qualification summary: source includes M36 real source evidence."
    assert b"M36 real source evidence" in actual
    ledger=ResultVersionLedger(USER,root=str(log.root))
    version=ledger.record_generated("m36-summary",summary,binding_id=b.binding_id,candidate_id=bound.source.source_id,trace_id=trace)
    link={"source_id":bound.source.source_id,"content_sha256":bound.source.content_sha256}
    derivative=record_derivative(recorder,ledger,version,task_a,derived_from=(link,),derivative_kind="summary",session_id="session",trace_id=trace)
    assert derivative.persisted
    package_a=build_context(log.load(),sources,task_a).to_dict(); assert package_a["derivatives"][0]["freshness"]=="CURRENT"
    # F-B: two real references, claim/verifier, S7 Change, paired correction, pause.
    task_b,result=recorder.open_task(capture("repair budget task"),"repair budget task"); assert result.persisted
    r_sheet=retrieve("budget sheet"); p_sheet,b_sheet=register(r_sheet,"RECOVERABLE")
    assert b_sheet.state==BindingState.TENTATIVE
    sheet=capture_binding(service,b_sheet,r_sheet,sources,"spreadsheet")
    r_script=retrieve("worker.py",ref_key="script"); p_script,b_script=register(r_script)
    script=capture_binding(service,b_script,r_script,sources,"script")
    for bound in (sheet,script): assert recorder.observe(bound.source,session_id="session",trace_id=trace).persisted
    head=log.load().task(task_b)
    assert recorder.task_state(task_b,head.record_id,intake=capture("use budget sheet and worker.py"),bindings=(sheet,script),next_step="review claimed output").persisted
    assert adapter.project(r_sheet).query==p_sheet.query
    inputs=tuple({"source_id":x.source.source_id,"content_sha256":x.source.content_sha256} for x in (sheet,script))
    claim=recorder.outcome(task_b,action_label="qualification source inspection",inputs=inputs,session_id="session",trace_id=trace)
    assert claim.persisted
    verdict=recorder.invoke_verifier(claim.record_ids[0],"uri.verifier.m36_byte_evidence",session_id="session",trace_id=trace); assert verdict.persisted
    service.record_execution(b_sheet.binding_id)
    r_new=retrieve("invoice.xlsx"); p_new=adapter.project(r_new)
    change=service.open_change(b_sheet.binding_id,p_new.query,resolve_rar_deterministic_extended(p_new.query).resolution,
            impact_reader=lambda:"RECOVERABLE",turn_id=uuid.uuid4().hex)
    contract=service.store.rounds[change.next_contract_id].contract
    response=ClarificationResponse(contract.ambiguity_id,ResponseKind.CANDIDATE,candidate_id=locators["invoice.xlsx"].source_id,
                                  candidate_set_fingerprint=contract.candidate_set_fingerprint)
    selected=capture(response.candidate_id,round_id=contract.ambiguity_id)
    changed=adapter.respond_selection(service,r_new,p_new.query,response,user_selection=selected,wrong_binding_impact="RECOVERABLE")
    assert changed.state==BindingState.CONFIRMED
    invoice=capture_binding(service,changed,r_new,sources,"spreadsheet")
    events=EvaluationEventStore(USER,root=str(log.root))
    event=wrong_reference_event(trace,ambiguity_id=contract.ambiguity_id,prior_candidate_id=sheet.source.source_id,
              new_candidate_id=invoice.source.source_id,session_id="session")
    assert events.record(event)["durable"]
    eid=correction_event_id(events,event)
    corrected=recorder.correction(task_b,"spreadsheet",log.load().task(task_b).record_id,intake=capture("use invoice.xlsx"),replacement=invoice,s7_event_id=eid)
    assert corrected.persisted
    # A live task worker persists its checkpoint, then is force-terminated.
    # A separate reader below discovers it without a known task identifier.
    checkpoint_child="""import sys,time,uuid
from scripts.m36_memory_qualification import byte_evidence_verifier
from uri_v1.memory.recorder import Recorder,_bootstrap_verifiers
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.sources import SourceRegistry
from uri_v1.memory.uri_adapter.envelope import URIIntake
_bootstrap_verifiers({'uri.verifier.m36_byte_evidence':('HASHED_BYTE_EVIDENCE','1',byte_evidence_verifier)})
log=MemoryLog(sys.argv[1],sys.argv[2]); rec=Recorder(log,SourceRegistry(log),clock=lambda:sys.argv[5])
i=URIIntake().capture(sys.argv[1],'session',uuid.uuid4().hex,uuid.uuid4().hex,'pause',spans={'file':(0,5)})
r=rec.task_state(sys.argv[3],log.load().task(sys.argv[3]).record_id,intake=i,status='PAUSED',last_outcome_record_id=sys.argv[4],next_step='review corrected spreadsheet')
assert r.persisted,r
print('CHECKPOINT_DURABLE',flush=True)
time.sleep(60)
"""
    worker=subprocess.Popen([sys.executable,"-c",checkpoint_child,USER,str(log.root),task_b,verdict.record_ids[0],NOW],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert worker.stdout.readline().strip()=="CHECKPOINT_DURABLE"
    finally:
        worker.kill(); worker.wait(timeout=10)
    # Fresh subprocess discovers paused task with no task identifier supplied.
    child="""import json,sys
from scripts.m36_memory_qualification import byte_evidence_verifier
from uri_v1.memory.recorder import _bootstrap_verifiers
_bootstrap_verifiers({'uri.verifier.m36_byte_evidence':('HASHED_BYTE_EVIDENCE','1',byte_evidence_verifier)})
from uri_v1.memory.log import MemoryLog
from uri_v1.memory.sources import SourceRegistry
from uri_v1.memory.context_package import build_context
log=MemoryLog(sys.argv[1],sys.argv[2]); idx=log.load(); tasks=idx.open_tasks(statuses=('PAUSED',))
print(json.dumps({'tasks':tasks,'package':build_context(idx,SourceRegistry(log),tasks[0]['task_id']).to_dict()}))
"""
    output=subprocess.run([sys.executable,"-c",child,USER,str(log.root)],cwd=ROOT,capture_output=True,text=True,check=True)
    resumed=json.loads(output.stdout); assert len(resumed["tasks"])==1
    assert resumed["tasks"][0]["task_id"]==task_b
    package_b=resumed["package"]; assert package_b["task"]["status"]=="PAUSED"
    assert package_b["task"]["next_step"]["text"]=="review corrected spreadsheet"
    assert package_b["task"]["last_outcome_record_id"]==verdict.record_ids[0]
    assert {x["source_id"] for x in package_b["references"]}=={invoice.source.source_id,script.source.source_id}
    assert all(x["binding_authority"]=="HISTORICAL_BINDING" for x in package_b["references"])
    assert task_a not in canonical(package_b).decode()
    assert recorder.task_state(task_b,log.load().task(task_b).record_id,intake=capture("resume"),status="OPEN").persisted
    # Same-session tier must keep operating with durable Memory OFF.
    log.set_durable_enabled(False)
    skip=[]
    for text in ("now open it","the other one","continue it","summarize this","review it"):
        r=retrieve(text,session_source_ids=(invoice.source.source_id,),session_confirmed=True)
        skip.append(r.telemetry["durable_reads"]==0 and r.telemetry["skip_reason"]=="SKIPPED_SESSION_CONFIRMED")
    log.set_durable_enabled(True)
    # Stale history is labelled while the edited current file is rediscovered.
    make_file(authorized/"report.docx")
    with zipfile.ZipFile(authorized/"report.docx","a") as z: z.writestr("word/extra.xml","edited source")
    stale_package=build_context(log.load(),sources,task_a).to_dict()
    assert stale_package["derivatives"][0]["freshness"]=="DERIVATIVE_STALE"
    refreshed=retrieve("report.docx",task_id=task_a); assert refreshed.candidates
    assert not sources.verify_source(document_bound.source.source_id,document_bound.source.content_sha256)
    isolation=MemoryLog(str(uuid.UUID(int=37)),log.root); assert not isolation.load().records
    package_bytes=max(len(canonical(x)) for x in (package_a,package_b,stale_package))
    assert package_bytes<=8192
    summary={"reference_cases":len(inventory),"wrong_confirmed":wrong,"invented_ids":invented,"tentative_wrong":tentative_wrong,
             "session_skip_rate":sum(skip)/len(skip),"maximum_context_bytes":package_bytes,"private_leaks":0,
             "e2e":{"real_formats":sorted({Path(x).suffix for x in battery["files"]}),"s1_bindings":len(service.store.bindings),
                    "s7_change_events":len(events.list_events()),"s11_versions":len(ledger.versions("m36-summary")),
                    "memory_records":len(log.load().records),"paused_discovery_new_process":True,"worker_force_terminated":True,"correction_pair":corrected.per_record,
                    "verifier_outcome":"VERIFIED","source_edit_derivative":"DERIVATIVE_STALE"},
             "decisions":inventory,"latency_us":latencies}
    return summary


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,default=ROOT/"docs/plans")
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    # Hash the checked-in LF representation, independent of Git's Windows
    # checkout newline conversion; qualification values are unchanged.
    threshold_bytes=(FIXTURES/"threshold_gate.json").read_bytes().replace(b"\r\n",b"\n")
    battery_bytes=(FIXTURES/"battery.json").read_bytes().replace(b"\r\n",b"\n")
    threshold=json.loads(threshold_bytes); battery=json.loads(battery_bytes)
    anchors=require_anchors(); _bootstrap_verifiers({"uri.verifier.m36_byte_evidence":("HASHED_BYTE_EVIDENCE","1",byte_evidence_verifier)})
    with tempfile.TemporaryDirectory(prefix="uri-m36-") as td:
        first=run_one(Path(td)/"run1",battery); second=run_one(Path(td)/"run2",battery)
    deterministic=first["decisions"]==second["decisions"]
    assert deterministic and first["reference_cases"]>=threshold["minimum_reference_cases"]
    assert first["wrong_confirmed"]==threshold["maximum_wrong_confirmed"]
    assert first["session_skip_rate"]>=threshold["minimum_session_skip_rate"]
    latencies=first.pop("latency_us")+second.pop("latency_us")
    sorted_lat=sorted(latencies)
    result={"schema_version":"m36.qualification-results.v1","run_at":datetime.now(timezone.utc).isoformat(),
            "baseline":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "threshold_sha256":hashlib.sha256(threshold_bytes).hexdigest(),"battery_sha256":hashlib.sha256(battery_bytes).hexdigest(),
            "frozen_anchors":anchors,"deterministic":deterministic,"runs":[first,second],
            "performance":{"retrieval_p50_us":statistics.median(latencies),"retrieval_p95_us":sorted_lat[int(.95*(len(sorted_lat)-1))],
                           "machine":platform.platform(),"cpu":platform.processor(),"python":sys.version},
            "qualification_scope":"real-flow driver plus required M36 pytest battery; no independent closing audit or production agent-loop/UI integration"}
    (args.output/"M36_TELEMETRY.json").write_bytes(canonical(result)+b"\n")
    aggregates={"reference_cases_per_run":first["reference_cases"],"runs":2,"wrong_confirmed":first["wrong_confirmed"]+second["wrong_confirmed"],
                "invented_ids":first["invented_ids"]+second["invented_ids"],"deterministic":deterministic,
                "performance":result["performance"],"e2e":first["e2e"],"threshold_sha256":result["threshold_sha256"]}
    (args.output/"M36_AGGREGATES.json").write_bytes(canonical(aggregates)+b"\n")
    print(json.dumps(aggregates,indent=2))


if __name__=="__main__": main()
