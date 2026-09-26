import ast
import hashlib
from pathlib import Path

from uri_core.core.arn.engine import ARNEngine
from uri_core.core.arn.models import ARNState, Candidate, UserClue
from uri_v1.reference_clarification.attribute_narrowing import apply_user_clue, recommend_axis
from uri_v1.turn.rar_contracts import RARCandidate


ROOT = Path(__file__).resolve().parents[1]


def test_arn1_axis_and_clue_port_parity():
    raw = (
        RARCandidate("a", "Report", "document", owner="Alice", recency_rank=0),
        RARCandidate("b", "Report", "document", owner="Bob", recency_rank=1),
        RARCandidate("c", "Report", "document", owner="Bob", recency_rank=2),
    )
    state = ARNState(task_goal="find report")
    engine = ARNEngine(state=state)
    engine.add_candidates(Candidate(c.id, c.title, metadata={"title": c.title, "type": c.candidate_type,
        "owner": c.owner, "recency": f"recency {c.recency_rank}"}) for c in raw)
    old = engine.get_clarification_recommendation()
    new = recommend_axis(raw)
    assert new[0] == old.suggested_axis
    assert new[1] == {k: tuple(v) for k, v in old.candidate_groups.items()}
    assert tuple(c.id for c in apply_user_clue(raw, "owner", " bob ")) == ("b", "c")
    assert tuple(c.candidate_id for c in engine.apply_user_clue(UserClue("owner", " bob "))) == ("b", "c")


def test_protected_hashes_and_uri_v1_import_boundary():
    expected = {
        "uri_v1/turn/rar_deterministic.py": "e02af25bb7009d12d829c8b8fc92e487d3da75aeaa160092db617458278fb649",
        "uri_v1/turn/rar_contracts.py": "4cc9aa43726a870ca2e9ab1b19f6bf9d72dcb74c8a2818856776af95195b6819",
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    battery = (ROOT / "fixtures/m33_3_batch_a/battery.json").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(battery).hexdigest() == "06d0dfffd8ecabff8b98ea7d24c1574904aa16fa172a3956e0a5fb95d6d1c3fa"
    for path in (ROOT / "uri_v1").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(alias.name.startswith("uri_core") for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("uri_core"), path


def test_s1_has_no_model_provider_network_or_later_execution_dependency():
    package = ROOT / "uri_v1/reference_clarification"
    forbidden = ("ollama", "openai", "anthropic", "requests", "httpx", "socket", "uri_core", "versioned", "REDONE(")
    for path in package.rglob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        assert not any(symbol.lower() in source for symbol in forbidden), path
