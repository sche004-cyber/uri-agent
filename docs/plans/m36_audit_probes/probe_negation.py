import pytest
from tests.test_m36_memory_support import setup,retrieval
from tests.test_m36_memory_grounding import registered
from uri_v1.turn.rar_clarification_contract import BindingState

CASES=[
 ("not budget.xlsx","budget.xlsx",None),              # control (tested by Codex)
 ("don't use budget.xlsx","budget.xlsx",None),
 ("never budget.xlsx","budget.xlsx",None),
 ("skip budget.xlsx","budget.xlsx",None),
 ("anything other than budget.xlsx","budget.xlsx",None),
 ("instead of budget.xlsx use the report","budget.xlsx",None),
 ("not budget.xlsx","budget.xlsx",(4,15)),            # span cropped past the negation
]
@pytest.mark.parametrize("raw,proposal,span",CASES)
def test_probe(raw,proposal,span,tmp_path):
    log,sources,rec,root=setup(tmp_path,("budget.xlsx","report.docx"))
    result=retrieval(log,sources,raw,proposal=proposal,span=span)
    state,service,p=registered(sources,result)
    print(repr(raw),span,"->",state, p.degraded if p else None)
    assert state!=BindingState.CONFIRMED
