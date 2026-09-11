"""test_model_router_import_boundary.py — M22.6 acceptance criterion #6.

AST scan to verify that uri_core/core/model_router.py never imports:
  - approval_gate
  - approval_store
  - dispatcher
  - capability_registry

This is the architectural invariant described in M22.6 §6 and the
governing architecture documents. Enforced as a permanent automated test
so future edits cannot accidentally introduce a forbidden import.
"""
import ast
import pathlib
import unittest


FORBIDDEN_IMPORTS = frozenset([
    "approval_gate",
    "approval_store",
    "dispatcher",
    "capability_registry",
])

MODEL_ROUTER_PATH = pathlib.Path(__file__).parent / "uri_core" / "core" / "model_router.py"


def _collect_imports(tree: ast.AST):
    """Yield all top-level and inline import names from an AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module


class TestModelRouterImportBoundary(unittest.TestCase):

    def setUp(self):
        self.assertTrue(
            MODEL_ROUTER_PATH.exists(),
            f"model_router.py not found at {MODEL_ROUTER_PATH}"
        )
        source = MODEL_ROUTER_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(source, filename=str(MODEL_ROUTER_PATH))

    def test_no_forbidden_imports(self):
        """model_router.py must not import approval_gate, approval_store, dispatcher, or capability_registry."""
        violations = []
        for imported_name in _collect_imports(self.tree):
            for forbidden in FORBIDDEN_IMPORTS:
                if forbidden in imported_name:
                    violations.append(imported_name)
        self.assertEqual(
            violations,
            [],
            f"model_router.py contains forbidden imports: {violations}\n"
            f"See M22.6 §6 (import boundary invariant). "
            f"These modules have approval/execution authority that must "
            f"never be reachable from the routing decision layer."
        )

    def test_approval_gate_not_imported(self):
        """Specific check: approval_gate."""
        for imported_name in _collect_imports(self.tree):
            self.assertNotIn(
                "approval_gate", imported_name,
                f"model_router.py imports 'approval_gate' via: {imported_name!r}"
            )

    def test_approval_store_not_imported(self):
        """Specific check: approval_store."""
        for imported_name in _collect_imports(self.tree):
            self.assertNotIn(
                "approval_store", imported_name,
                f"model_router.py imports 'approval_store' via: {imported_name!r}"
            )

    def test_dispatcher_not_imported(self):
        """Specific check: dispatcher."""
        for imported_name in _collect_imports(self.tree):
            self.assertNotIn(
                "dispatcher", imported_name,
                f"model_router.py imports 'dispatcher' via: {imported_name!r}"
            )

    def test_capability_registry_not_imported(self):
        """Specific check: capability_registry."""
        for imported_name in _collect_imports(self.tree):
            self.assertNotIn(
                "capability_registry", imported_name,
                f"model_router.py imports 'capability_registry' via: {imported_name!r}"
            )

    def test_model_router_is_valid_python(self):
        """Syntactic sanity check — model_router.py must parse without errors."""
        source = MODEL_ROUTER_PATH.read_text(encoding="utf-8")
        try:
            ast.parse(source)
        except SyntaxError as exc:
            self.fail(f"model_router.py has a syntax error: {exc}")


if __name__ == "__main__":
    unittest.main()
