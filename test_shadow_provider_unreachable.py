"""M22.1: proves, by inspecting actual import statements (same AST
technique as test_capability_authority_boundary.py/
test_client_identity_boundary.py), that the two remaining pre-M21
shadow-provider modules are unreachable from any live call path.

Background (see URI_M22_ARCHITECTURE.md section 18): the M22 audit
found five modules bypassing the M21 ModelProvider/build_provider seam
by calling Gemini/Groq/OpenAI directly with os.environ keys. Three had
zero real importers once the two dead orchestrator backups were removed
(strategic_evaluator.py, rost_evaluator.py, hermes_forge.py) and were
deleted outright in M22.1. The remaining two -
uri_core/services/hermes_service.py and
uri_core/core/semantic_interpreter.py - are NOT deleted in M22.1
because they are still exercised by real, passing regression tests
(test_credential_hygiene.py, test_semantic_interpreter.py) proving a
genuinely valuable property (an API key is read only from the
environment, never hardcoded, never silently substituted when absent).
Deleting them now would discard that coverage before M22.5 (provider
registry) ports the same guarantee onto the real per-user API-key
store - see each module's own M22.1 docstring.

This test is the enforced half of that plan: it proves neither module
is imported by anything under uri_core/ except its own dedicated test
file, so "retained but unreachable" is a verified fact rather than an
assumption that could silently rot as the codebase changes.
"""

import ast
import os
import unittest

PACKAGE_ROOT = os.path.join("uri_core")

# The two quarantined modules themselves, and the one legitimate M21
# module whose name is a superstring of one of them
# (provider_semantic_interpreter.py) and must not be mistaken for an
# importer of core/semantic_interpreter.py.
QUARANTINED_MODULES = {
    "uri_core.services.hermes_service": os.path.join(
        "uri_core", "services", "hermes_service.py"
    ),
    "uri_core.core.semantic_interpreter": os.path.join(
        "uri_core", "core", "semantic_interpreter.py"
    ),
}


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


def _all_python_files_under(root: str):

    for current, _dirs, files in os.walk(root):

        if "__pycache__" in current:
            continue

        for name in files:

            if name.endswith(".py"):
                yield os.path.join(current, name)


class ShadowProviderUnreachableTests(unittest.TestCase):

    def test_hermes_service_is_not_imported_outside_itself(self):
        self._assert_unreferenced("uri_core.services.hermes_service")

    def test_core_semantic_interpreter_is_not_imported_outside_itself(
        self,
    ):
        self._assert_unreferenced("uri_core.core.semantic_interpreter")

    def _assert_unreferenced(self, dotted_module_name: str) -> None:

        own_path = QUARANTINED_MODULES[dotted_module_name]
        offenders = []

        for path in _all_python_files_under(PACKAGE_ROOT):

            if os.path.normpath(path) == os.path.normpath(own_path):
                continue

            imports = _imported_module_names(path)

            if any(
                name == dotted_module_name
                or name.startswith(dotted_module_name + ".")
                for name in imports
            ):
                offenders.append(path)

        self.assertEqual(
            offenders,
            [],
            f"{dotted_module_name} must be unreachable from every "
            "other module under uri_core/ - it is retained only for "
            "its own dedicated regression test (see this module's "
            "M22.1 docstring) and must never be imported by new or "
            "existing production code.",
        )


if __name__ == "__main__":
    unittest.main()
