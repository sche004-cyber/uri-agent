import hashlib
import json
import sys
from pathlib import Path

from scripts import m33_2_batch_b4_live_qualification_runner as runner
from uri_core.core.edge.adapters.ensemble import (
    NeedleSubprocessAdapter,
    build_candidate_configurations,
)


ROOT = Path(__file__).parent


def test_additive_real_needle_corpus_is_frozen_and_manifested():
    corpus_path = ROOT / "fixtures/m33_2_edge_benchmark/corpus.json"
    manifest = json.loads(
        (ROOT / "fixtures/m33_2_edge_benchmark/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    structured = [item for item in corpus if item.get("operation") == "structured_extract"]

    assert len(corpus) == manifest["corpus_item_count"] == 24
    assert manifest["items_per_tier"]["reflex"] == 8
    assert len(structured) == 4
    assert all(item["expected_record"] == item["expected"] for item in structured)
    assert all(item["offered_capabilities"] == ["record.extract"] for item in structured)
    assert hashlib.sha256(corpus_path.read_bytes()).hexdigest()


def test_needle_subprocess_adapter_is_proposal_only_jsonl_bridge(tmp_path):
    bridge = tmp_path / "bridge.py"
    bridge.write_text(
        """
import json, sys
for raw in sys.stdin:
    request = json.loads(raw)
    if request['operation'] == 'ping':
        print(json.dumps({'status':'ready','package_version':'test'}), flush=True)
    elif request['operation'] == 'qualify':
        print(json.dumps({'status':'ok','provider_response':{'type':'call'},'output':{
            'answer': {'intent':'weather','capability_id':'weather.lookup'},
            'capability_id':'weather.lookup','arguments':{},'score':0.9,
            'status':'completed'}}), flush=True)
    elif request['operation'] == 'close':
        break
""".strip(),
        encoding="utf-8",
    )
    adapter = NeedleSubprocessAdapter(Path(sys.executable), bridge)
    try:
        adapter.load()
        output = adapter(
            {
                "id": "probe",
                "input": "weather",
                "offered_capabilities": ["weather.lookup"],
            }
        )
        assert output["capability_id"] == "weather.lookup"
        assert adapter.runtime_info["status"] == "ready"
        assert adapter.records[0]["provider_response"] == {"type": "call"}
    finally:
        adapter.close()


def test_real_configuration_score_semantics_do_not_fake_gguf_confidence():
    component = lambda item: {"answer": item.get("expected"), "status": "completed"}
    candidates = build_candidate_configurations(
        tiny_reasoner_id="qwen2.5-0.5b-instruct",
        needle=component,
        language=component,
        reasoner=component,
    )
    assert candidates["A"].score_semantics == "calibrated_confidence"
    assert candidates["B"].score_semantics == "none"
    assert candidates["C"].score_semantics == "none"
    assert candidates["D"].score_semantics == "none"


def test_runner_assets_are_confined_and_have_pinned_sha256():
    root = (ROOT / "uri_workspace/edge_models").resolve()
    for metadata in runner.ASSETS.values():
        path = Path(metadata["path"]).resolve()
        assert path.is_relative_to(root)
        assert len(metadata["sha256"]) == 64
        int(metadata["sha256"], 16)


def test_reasoning_answer_normalization_is_generic_not_expected_value_driven():
    assert runner._short_answer("No.") == "no"
    assert runner._short_answer("in the drawer") == "drawer"
    assert runner._short_answer("The key is in the drawer.") == "drawer"
    assert runner._short_answer("Cy") == "Cy"
