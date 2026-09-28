import json
from pathlib import Path
import subprocess
import sys


def test_predeclared_real_flow_battery_and_determinism(tmp_path):
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/"scripts/m36_memory_qualification.py"),"--output",str(tmp_path)],
                          cwd=root,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    data=json.loads((tmp_path/"M36_TELEMETRY.json").read_bytes())
    assert data["deterministic"] and data["frozen_anchors"]["ok"]
    for run in data["runs"]:
        assert run["reference_cases"]>=40 and run["wrong_confirmed"]==run["invented_ids"]==run["private_leaks"]==0
        assert run["session_skip_rate"]>=0.95 and run["maximum_context_bytes"]<=8192
        assert run["e2e"]["s7_change_events"]==run["e2e"]["s11_versions"]==1
        assert run["e2e"]["paused_discovery_new_process"]
        assert run["e2e"]["correction_pair"]==[True,True]
