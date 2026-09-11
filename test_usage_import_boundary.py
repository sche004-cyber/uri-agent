"""AST boundaries and protected orchestrator newline invariant."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def imported_names(path):
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(alias.name for alias in node.names)
    return names


def test_aggregator_has_no_model_imports():
    names = imported_names(ROOT / "uri_core/core/usage_aggregator.py")
    assert not any(part in {"ModelProvider", "ModelRouter", "model_router", "model_providers"}
                   for name in names for part in name.split("."))


def test_router_authority_boundary():
    names = imported_names(ROOT / "uri_core/core/model_router.py")
    assert not any(part in {"approval_gate", "approval_store", "dispatcher", "capability_registry"}
                   for name in names for part in name.split("."))


def test_orchestrator_newline_count_does_not_increase():
    assert (ROOT / "uri_core/core/orchestrator.py").read_bytes().count(b"\n") <= 5460
