from dataclasses import replace
import pytest
from uri_v1.memory.uri_adapter.envelope import MemoryAdapter,URIIntake,ground
from uri_v1.memory.contracts import TrustedInput,MemoryQuery
from uri_v1.memory.retrieval import Retriever
from uri_v1.reference_clarification.binding import BindingService
from uri_v1.reference_clarification.builder import build_clarification
from uri_v1.turn.rar_clarification_contract import BindingState
from uri_v1.turn.rar_deterministic import resolve_rar_deterministic_extended
from tests.test_m36_memory_support import setup,retrieval,intake,resolve,NOW,USER


def registered(sources,result):
    adapter=MemoryAdapter(sources); projection=adapter.project(result)
    if projection.query is None: return BindingState.PENDING, None, projection
    service=BindingService()
    built=build_clarification(projection.query,resolve_rar_deterministic_extended(projection.query).resolution,
        session_id=result.query.session_id,turn_id=result.query.intake.turn_id,wrong_binding_impact="CONSEQUENTIAL")
    bound=adapter.register(service,built,result,projection.query)
    return bound.state,service,projection


@pytest.mark.parametrize("raw,proposal,span",[
    ("update the budget sheet","budget.xlsx",(11,23)),
    ("update the spreadsheet","COPIED_ID",(11,22)),
    ("budget.xlsx.bak","budget.xlsx",None),
    ("old-budget.xlsx","budget.xlsx",None),
    ("budget xlsx","budget.xlsx",None),
    ("not budget.xlsx","budget.xlsx",None),
])
def test_a3_a_b_f_negation_no_confirmed(raw,proposal,span,tmp_path):
    log,sources,rec,root=setup(tmp_path)
    if proposal=="COPIED_ID": proposal=sources.scan().locators[0].source_id
    result=retrieval(log,sources,raw,proposal=proposal,span=span)
    state,service,p=registered(sources,result)
    assert state!=BindingState.CONFIRMED
    if p.query: assert p.query.reference_expression!=proposal


@pytest.mark.parametrize("raw,proposal,span",[
    ("update budget.xlsx","budget.xlsx",(7,18)),
    ('"BUDGET.XLSX"',"budget.xlsx",None),
])
def test_a3_c_literal_controls(raw,proposal,span,tmp_path):
    log,sources,rec,root=setup(tmp_path)
    result=retrieval(log,sources,raw,proposal=proposal,span=span)
    state,service,p=registered(sources,result)
    assert state==BindingState.CONFIRMED
    assert p.grounding.status=="RAW_VERBATIM"
    assert p.query.candidates[0].exact_aliases==()


def test_a3_d_collisions_and_incomplete_scan(tmp_path):
    log,sources,rec,root=setup(tmp_path,("old/budget.xlsx","new/budget.xlsx"))
    result=retrieval(log,sources,"budget.xlsx")
    state,service,p=registered(sources,result)
    assert state!=BindingState.CONFIRMED and len(p.query.candidates)==2
    narrowed=replace(result,candidates=result.candidates[:1])
    assert MemoryAdapter(sources).project(narrowed).query is None
    sources.max_files=1
    assert MemoryAdapter(sources).project(retrieval(log,sources,"budget.xlsx")).query is None


def test_a3_e_typed_identifier(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    sid=sources.scan().locators[0].source_id
    assert registered(sources,retrieval(log,sources,sid))[0]==BindingState.CONFIRMED
    assert registered(sources,retrieval(log,sources,sid[:20],proposal=sid))[0]!=BindingState.CONFIRMED


def test_a3_g_missing_echoed_forged_intake(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    result=retrieval(log,sources,"budget.xlsx")
    for raw in (None,{"raw_text":"budget.xlsx","provenance":"USER"},TrustedInput(USER,"session","turn","a"*32,"budget.xlsx",(("file",0,11),))):
        changed=replace(result,query=replace(result.query,intake=raw))
        assert MemoryAdapter(sources).project(changed).query is None


@pytest.mark.parametrize("raw,proposal,confirmed",[
    ("the one for the budget","budget.xlsx",False),
    ("the spreadsheet","COPIED_ID",False),
    ("budget.xlsx","budget.xlsx",True),
    ("TYPED_ID","COPIED_ID",True),
    ("not budget.xlsx","budget.xlsx",False),
    ("budget.xlsx.bak","budget.xlsx",False),
])
def test_a4_h_actual_free_input(raw,proposal,confirmed,tmp_path):
    log,sources,rec,root=setup(tmp_path)
    result,p,service,b=resolve(log,sources,"budget sheet")
    assert b.state==BindingState.PENDING and service.store.rounds[b.next_contract_id].contract.scope_candidate_ids
    sid=sources.scan().locators[0].source_id
    if raw=="TYPED_ID": raw=sid
    if proposal=="COPIED_ID": proposal=sid
    answer=intake(raw,round_id=b.next_contract_id)
    calls=[]; original=service.respond
    def observed(*args,**kw): calls.append(args[1].text); return original(*args,**kw)
    service.respond=observed
    bound=MemoryAdapter(sources).respond_free_input(service,result,p.query,b.next_contract_id,answer,proposed_text=proposal)
    assert (bound.state==BindingState.CONFIRMED)==confirmed
    assert all(text==raw for text in calls)


def test_a4_missing_previous_offsets_and_negated_subspan(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    result,p,service,b=resolve(log,sources,"budget sheet")
    adapter=MemoryAdapter(sources)
    for answer in (None,result.query.intake,{"raw_text":"budget.xlsx"},intake("budget.xlsx",round_id="different")):
        assert adapter.respond_free_input(service,result,p.query,b.next_contract_id,answer,proposed_text="budget.xlsx").state!=BindingState.CONFIRMED
    answer=intake("not budget.xlsx",round_id=b.next_contract_id)
    assert adapter.respond_free_input(service,result,p.query,b.next_contract_id,answer,proposed_offsets=(4,15)).state!=BindingState.CONFIRMED
    answer=intake("budget.xlsx",round_id=b.next_contract_id)
    assert adapter.respond_free_input(service,result,p.query,b.next_contract_id,answer,proposed_offsets=(0,100)).state!=BindingState.CONFIRMED


def test_a4_new_collision_and_changed_source_block(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    result,p,service,b=resolve(log,sources,"budget sheet")
    (root/"other").mkdir(); (root/"other"/"budget.xlsx").write_bytes(b"collision")
    answer=intake("budget.xlsx",round_id=b.next_contract_id)
    assert MemoryAdapter(sources).respond_free_input(service,result,p.query,b.next_contract_id,answer).state!=BindingState.CONFIRMED
    (root/"other"/"budget.xlsx").unlink(); (root/"other").rmdir()
    (root/"budget.xlsx").write_bytes(b"changed")
    assert MemoryAdapter(sources).respond_free_input(service,result,p.query,b.next_contract_id,answer).state!=BindingState.CONFIRMED


def test_a2_attachment_whole_turn_and_per_slot(tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget.xlsx","worker.py"))
    scan=sources.scan(); ids={x.relpath:x.source_id for x in scan.locators}
    r=retrieval(log,sources,"the spreadsheet",attachment_source_ids=tuple(ids.values()))
    p=MemoryAdapter(sources).project(r,slot_count=2)
    assert p.query and p.query.deterministic_anchor is None
    r=retrieval(log,sources,"script",attachment_source_ids=(ids["budget.xlsx"],))
    assert MemoryAdapter(sources).project(r,slot_count=2).query.deterministic_anchor is None
    r=retrieval(log,sources,"spreadsheet",attachment_source_ids=(ids["budget.xlsx"],))
    assert MemoryAdapter(sources).project(r,slot_count=2).query.deterministic_anchor.current_attachment_id==ids["budget.xlsx"]
    assert MemoryAdapter(sources).project(r,slot_count=2,distinct_files=True).query.deterministic_anchor is None


def test_a2_cap_degradation_no_certainty(tmp_path):
    log,sources,rec,root=setup(tmp_path)
    sources.hash_cap=1
    r=retrieval(log,sources,"budget.xlsx")
    assert MemoryAdapter(sources).project(r).query is None


def test_a2_cross_root_and_stem_collisions_ignore_type_hint(tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget.xlsx",))
    other=tmp_path/"second-root"; other.mkdir(); (other/"budget.xlsx").write_bytes(b"second")
    sources.register(other)
    r=retrieval(log,sources,"budget.xlsx")
    assert len(r.candidates)==2 and registered(sources,r)[0]!=BindingState.CONFIRMED
    (other/"budget.xlsx").unlink(); (other/"budget.pdf").write_bytes(b"different type same stem")
    r=retrieval(log,sources,"budget",type_hint="spreadsheet")
    assert len(r.candidates)==2 and registered(sources,r)[0]!=BindingState.CONFIRMED
    (other/"budget.pdf").unlink(); other.rmdir()
    assert MemoryAdapter(sources).project(retrieval(log,sources,"budget.xlsx")).query is None


def test_a2_conflicting_raw_slot_classes_and_extensionless_attachment(tmp_path):
    log,sources,rec,root=setup(tmp_path,("unknown",))
    sid=sources.scan().locators[0].source_id
    r=retrieval(log,sources,"spreadsheet",attachment_source_ids=(sid,))
    assert MemoryAdapter(sources).project(r,slot_count=2).query.deterministic_anchor is None
    r=retrieval(log,sources,"spreadsheet script",attachment_source_ids=(sid,))
    assert r.degraded=="AMBIGUOUS_SOURCE_CLASS"
