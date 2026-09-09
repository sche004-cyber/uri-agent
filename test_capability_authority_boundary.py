"""Structural invariant tests for Milestone 6 (Capability Awareness).

These assert authority boundaries by inspecting actual import
statements in source files, not by convention - mirroring the
technique already used across this codebase (e.g. server.py's own
comments verified by grep during Milestone 5) to prove an invariant
holds rather than merely documenting an intention.

Two boundaries are asserted:

1. dispatcher.py - the actual execution path - must never import
   capability_registry or model_providers. Self-knowledge is
   reporting-only; execution must remain unaware of it entirely.

2. capability_planner.py may import capability_registry (approved,
   gap-reporting only - see capability_planner.py's _known_gaps()),
   but must never import model_providers. Model/provider identity is
   never a routing input.
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


class CapabilityAuthorityBoundaryTests(unittest.TestCase):

    def test_dispatcher_never_imports_capability_registry(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "dispatcher.py")
        )

        offending = {
            name
            for name in imports
            if "capability_registry" in name
        }

        self.assertEqual(
            offending,
            set(),
            "dispatcher.py must never import capability_registry - "
            "self-knowledge is reporting-only and must never reach "
            "the execution path.",
        )

    def test_dispatcher_never_imports_model_providers(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "dispatcher.py")
        )

        offending = {
            name for name in imports if "model_providers" in name
        }

        self.assertEqual(
            offending,
            set(),
            "dispatcher.py must never import model_providers - model "
            "identity is never an execution input.",
        )

    def test_capability_planner_never_imports_model_providers(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "capability_planner.py")
        )

        offending = {
            name for name in imports if "model_providers" in name
        }

        self.assertEqual(
            offending,
            set(),
            "capability_planner.py must never import model_providers "
            "- model identity is never a routing/selection input.",
        )

    def test_capability_planner_only_uses_registry_for_reporting(self):
        # capability_registry IS an approved import for
        # capability_planner.py (its gap-reporting path) - this test
        # asserts the specific, narrower invariant: the registry is
        # never consulted inside _score_tool (the actual selection
        # logic), only inside _known_gaps (informational).
        with open(
            os.path.join(
                "uri_core", "core", "capability_planner.py"
            ),
            "r",
            encoding="utf-8-sig",
        ) as file:
            source = file.read()

        tree = ast.parse(source)

        score_tool_body = None

        for node in ast.walk(tree):

            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_score_tool"
            ):
                score_tool_body = ast.get_source_segment(source, node)

        self.assertIsNotNone(
            score_tool_body,
            "_score_tool must still exist and be inspectable.",
        )

        self.assertNotIn(
            "capability_registry",
            score_tool_body,
            "_score_tool (the selection heuristic) must never "
            "reference capability_registry.",
        )
        self.assertNotIn(
            "self.capability_registry",
            score_tool_body,
        )

    def test_workflow_executor_never_imports_model_providers(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "workflow_executor.py")
        )

        offending = {
            name for name in imports if "model_providers" in name
        }

        self.assertEqual(offending, set())

    def test_capability_registry_module_performs_no_execution(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "capability_registry.py")
        )

        self.assertNotIn("importlib", imports)
        self.assertNotIn("subprocess", imports)

    # ------------------------------------------------------------
    # Milestone 7 (Real Approval Gate) invariants.
    # ------------------------------------------------------------

    def test_capability_planner_never_imports_approval_modules(self):
        # The model/planning layer may PROPOSE a tool_name; it must
        # never be able to reach ApprovalStore/ApprovalGate and so can
        # never create, decide, or consume an approval itself.
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "capability_planner.py")
        )

        offending = {
            name
            for name in imports
            if "approval_store" in name or "approval_gate" in name
        }

        self.assertEqual(
            offending,
            set(),
            "capability_planner.py must never import approval_store "
            "or approval_gate - it may only propose a tool_name, "
            "never grant or satisfy approval.",
        )

    def test_dispatcher_never_imports_approval_modules(self):
        # ToolDispatcher stays a pure execution mechanism, unaware
        # that a gate exists in front of it - see approval_gate.py's
        # module docstring: the gate wraps the dispatcher, the
        # dispatcher never wraps or knows about the gate.
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "dispatcher.py")
        )

        offending = {
            name
            for name in imports
            if "approval_store" in name or "approval_gate" in name
        }

        self.assertEqual(offending, set())

    def test_model_reasoning_gateway_never_imports_approval_modules(
        self,
    ):
        # Milestone 11 Phase 1: model reasoning's result may now become
        # the real plan for the direct single-capability path (see
        # orchestrator.py's _model_proposed_capability), but only ever
        # as a plain capability-name string handed back to
        # orchestrator.py, which alone decides whether to route it into
        # ApprovalGate/ToolDispatcher. model_reasoning_gateway.py itself
        # must still have no path of its own to approval or execution
        # state - it only ever reasons and proposes.
        imports = _imported_module_names(
            os.path.join(
                "uri_core", "core", "model_reasoning_gateway.py"
            )
        )

        offending = {
            name
            for name in imports
            if any(
                fragment in name
                for fragment in (
                    "approval_store",
                    "approval_gate",
                    "dispatcher",
                )
            )
        }

        self.assertEqual(offending, set())

    def test_approval_gate_never_imports_model_providers(self):
        # Symmetric with the Milestone 6 invariant: approval decisions
        # must never be influenced by, or influence, model identity.
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "approval_gate.py")
        )

        offending = {
            name for name in imports if "model_providers" in name
        }

        self.assertEqual(offending, set())

    def test_approval_gate_is_the_only_caller_of_dispatcher_in_orchestrator(
        self,
    ):
        # orchestrator.py must never call self.dispatcher.execute_tool
        # directly - every execution of a registered capability must
        # go through self.approval_gate.execute_tool instead.
        with open(
            os.path.join("uri_core", "core", "orchestrator.py"),
            "r",
            encoding="utf-8-sig",
        ) as file:
            source = file.read()

        self.assertNotIn("self.dispatcher.execute_tool", source)

    # ------------------------------------------------------------
    # Milestone 8A (Live Conversational Surface) invariants.
    # ------------------------------------------------------------

    def test_response_drafting_never_imports_execution_or_approval_modules(
        self,
    ):
        # The drafting model only ever explains an already-decided
        # outcome - it must have no path to anything that could decide
        # or authorize one.
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "response_drafting.py")
        )

        offending = {
            name
            for name in imports
            if any(
                fragment in name
                for fragment in (
                    "capability_planner",
                    "dispatcher",
                    "approval_store",
                    "approval_gate",
                )
            )
        }

        self.assertEqual(offending, set())

    def test_response_validation_never_imports_execution_or_approval_modules(
        self,
    ):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "response_validation.py")
        )

        offending = {
            name
            for name in imports
            if any(
                fragment in name
                for fragment in (
                    "capability_planner",
                    "dispatcher",
                    "approval_store",
                    "approval_gate",
                )
            )
        }

        self.assertEqual(offending, set())

    def test_personalization_context_never_imports_execution_or_approval_modules(
        self,
    ):
        imports = _imported_module_names(
            os.path.join(
                "uri_core", "core", "personalization_context.py"
            )
        )

        offending = {
            name
            for name in imports
            if any(
                fragment in name
                for fragment in (
                    "capability_planner",
                    "dispatcher",
                    "approval_store",
                    "approval_gate",
                )
            )
        }

        self.assertEqual(offending, set())

    def test_personalization_context_never_imports_growth_ledger(self):
        # Growth/XP is cosmetic and must never become a personalization
        # signal - see personalization_context.py's module docstring.
        imports = _imported_module_names(
            os.path.join(
                "uri_core", "core", "personalization_context.py"
            )
        )

        self.assertNotIn("uri_core.core.growth_ledger", imports)

    def test_query_context_never_imports_execution_or_approval_modules(
        self,
    ):
        # Milestone 10A: query_context.py assembles the unified,
        # model-facing context but must never gain a path back into
        # execution/authorization, exactly like personalization_context
        # above.
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "query_context.py")
        )

        offending = {
            name
            for name in imports
            if any(
                fragment in name
                for fragment in (
                    "capability_planner",
                    "dispatcher",
                    "approval_store",
                    "approval_gate",
                )
            )
        }

        self.assertEqual(offending, set())

    def test_capability_planner_dispatcher_never_import_response_modules(
        self,
    ):
        # Symmetric check: the deterministic selection/execution path
        # must have no path back into drafting/validation either.
        for relative_path in (
            os.path.join("uri_core", "core", "capability_planner.py"),
            os.path.join("uri_core", "core", "dispatcher.py"),
        ):
            imports = _imported_module_names(relative_path)

            offending = {
                name
                for name in imports
                if "response_drafting" in name
                or "response_validation" in name
            }

            self.assertEqual(offending, set(), relative_path)

    # ------------------------------------------------------------
    # M21 (provider configuration seam) invariants.
    #
    # model_roles.py (uri_core/config/model_roles.py) adds a second way
    # to reach model_providers - build_provider(role) - on top of the
    # model_providers import itself. Both must stay just as unable to
    # reach or influence execution/approval/authority as the
    # Milestone 6/7 invariants above already require of model_providers
    # directly: which provider answers a role's prompt must never
    # become a routing, execution, or authorization input.
    # ------------------------------------------------------------

    def test_dispatcher_never_imports_model_roles(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "dispatcher.py")
        )

        offending = {name for name in imports if "model_roles" in name}

        self.assertEqual(
            offending,
            set(),
            "dispatcher.py must never import model_roles - provider "
            "selection is never an execution input.",
        )

    def test_capability_planner_never_imports_model_roles(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "capability_planner.py")
        )

        offending = {name for name in imports if "model_roles" in name}

        self.assertEqual(
            offending,
            set(),
            "capability_planner.py must never import model_roles - "
            "provider selection is never a routing/selection input.",
        )

    def test_approval_gate_never_imports_model_roles_or_providers(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "approval_gate.py")
        )

        offending = {
            name
            for name in imports
            if "model_roles" in name or "model_providers" in name
        }

        self.assertEqual(
            offending,
            set(),
            "approval_gate.py must never import model_roles/"
            "model_providers - approval decisions must stay "
            "uninfluenced by, and unable to influence, provider "
            "identity.",
        )

    def test_workflow_executor_never_imports_model_roles(self):
        imports = _imported_module_names(
            os.path.join("uri_core", "core", "workflow_executor.py")
        )

        offending = {name for name in imports if "model_roles" in name}

        self.assertEqual(offending, set())

    def test_model_roles_never_imports_approval_or_execution_modules(self):
        # Symmetric to the above: the provider-configuration seam itself
        # must have no path INTO approval or execution either - it can
        # only ever be asked to build a ModelProvider, never to decide
        # or perform anything.
        imports = _imported_module_names(
            os.path.join("uri_core", "config", "model_roles.py")
        )

        offending = {
            name
            for name in imports
            if any(
                fragment in name
                for fragment in (
                    "approval_store",
                    "approval_gate",
                    "dispatcher",
                    "capability_registry",
                    "capability_planner",
                )
            )
        }

        self.assertEqual(offending, set())


if __name__ == "__main__":
    unittest.main()
