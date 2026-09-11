"""M23 (plan section 16, row 6 / section 8): the graph is context,
never authority - proven, not merely documented, by inspecting real
import statements, the same technique
test_capability_authority_boundary.py already uses.

Two directions are asserted:

1. dispatcher.py/approval_gate.py/approval_store.py/
   capability_registry.py/capability_resolver.py must never import any
   graph_* module - a graph edge can never become an input to any
   execution/approval/capability decision.
2. graph_engine.py/graph_context.py/graph_ingest.py must never import
   model_providers/model_router (no model identity input - same
   invariant URI_M22_ARCHITECTURE.md section 18.1 already requires
   elsewhere) or dispatcher.py/approval_gate.py/approval_store.py
   (mirrors query_context.py's own existing boundary).
"""

import ast
import os
import unittest


def _imported_module_names(file_path: str) -> set:
    with open(file_path, "r", encoding="utf-8-sig") as file:
        tree = ast.parse(file.read(), filename=file_path)

    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


_CORE = os.path.join("uri_core", "core")

_AUTHORITY_FILES = (
    "dispatcher.py",
    "approval_gate.py",
    "approval_store.py",
    "capability_registry.py",
    "capability_resolver.py",
)

_GRAPH_FILES = (
    "graph_store.py",
    "graph_engine.py",
    "graph_context.py",
    "graph_ingest.py",
)


class GraphAuthorityBoundaryTests(unittest.TestCase):
    def test_authority_modules_never_import_any_graph_module(self):
        for authority_file in _AUTHORITY_FILES:
            imports = _imported_module_names(os.path.join(_CORE, authority_file))
            offending = {name for name in imports if "graph_" in name}
            self.assertEqual(
                offending,
                set(),
                f"{authority_file} must never import a graph_* module - "
                "the graph must never become an authorization input.",
            )

    def test_graph_engine_never_imports_model_identity_or_execution_modules(self):
        imports = _imported_module_names(os.path.join(_CORE, "graph_engine.py"))
        forbidden = {"model_providers", "model_router", "dispatcher", "approval_gate", "approval_store"}
        offending = {name for name in imports if any(f in name for f in forbidden)}
        self.assertEqual(offending, set())

    def test_graph_context_never_imports_model_identity_or_execution_modules(self):
        imports = _imported_module_names(os.path.join(_CORE, "graph_context.py"))
        forbidden = {"model_providers", "model_router", "dispatcher", "approval_gate", "approval_store"}
        offending = {name for name in imports if any(f in name for f in forbidden)}
        self.assertEqual(offending, set())

    def test_graph_ingest_never_imports_model_identity_or_execution_modules(self):
        imports = _imported_module_names(os.path.join(_CORE, "graph_ingest.py"))
        forbidden = {"model_providers", "model_router", "dispatcher", "approval_gate", "approval_store"}
        offending = {name for name in imports if any(f in name for f in forbidden)}
        self.assertEqual(offending, set())

    def test_graph_store_never_imports_model_identity_or_execution_modules(self):
        imports = _imported_module_names(os.path.join(_CORE, "graph_store.py"))
        forbidden = {"model_providers", "model_router", "dispatcher", "approval_gate", "approval_store"}
        offending = {name for name in imports if any(f in name for f in forbidden)}
        self.assertEqual(offending, set())

    def test_all_graph_module_files_actually_exist(self):
        # Guards the boundary tests above against a silent no-op if a
        # file were ever renamed - each assertion above only proves
        # something about a file that is actually there.
        for graph_file in _GRAPH_FILES:
            self.assertTrue(
                os.path.isfile(os.path.join(_CORE, graph_file)),
                f"expected {graph_file} to exist under {_CORE}",
            )


if __name__ == "__main__":
    unittest.main()
