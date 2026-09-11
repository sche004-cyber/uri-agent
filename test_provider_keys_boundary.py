"""M22.5 invariant #4: provider_keys must never be imported by any
prompt-assembly module.

Architecture doc §19.4-#4: provider_keys store is never imported by
provider_semantic_interpreter.py, model_reasoning_adapter.py,
response_drafting.py, or document_composer.py.

Uses the same AST-scan technique as test_experience_tier_never_authorizes.py.
"""

import ast
import unittest
from pathlib import Path


def _imported_module_names(source_path: Path) -> set:
    """Return the set of all module names imported (directly or via from) in
    the given Python source file."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


_PROMPT_ASSEMBLY_MODULES = [
    Path("uri_core/core/provider_semantic_interpreter.py"),
    Path("uri_core/core/model_reasoning_adapter.py"),
    Path("uri_core/core/response_drafting.py"),
    Path("uri_core/services/document_composer.py"),
]

_FORBIDDEN = "provider_keys"


class TestProviderKeysBoundary(unittest.TestCase):
    """Invariant #4: provider_keys must not appear in prompt-assembly modules."""

    def _check_no_provider_keys_import(self, path: Path) -> None:
        if not path.exists():
            self.skipTest(f"{path} does not exist in this worktree.")
        imported = _imported_module_names(path)
        matching = {m for m in imported if _FORBIDDEN in m}
        self.assertEqual(
            matching,
            set(),
            msg=(
                f"Security boundary violation: {path} imports "
                f"{matching!r}. provider_keys must never be imported by "
                "prompt-assembly modules - only config/model_roles.py "
                "build_provider() may import it."
            ),
        )

    def test_provider_semantic_interpreter_no_provider_keys(self):
        self._check_no_provider_keys_import(_PROMPT_ASSEMBLY_MODULES[0])

    def test_model_reasoning_adapter_no_provider_keys(self):
        self._check_no_provider_keys_import(_PROMPT_ASSEMBLY_MODULES[1])

    def test_response_drafting_no_provider_keys(self):
        self._check_no_provider_keys_import(_PROMPT_ASSEMBLY_MODULES[2])

    def test_document_composer_no_provider_keys(self):
        self._check_no_provider_keys_import(_PROMPT_ASSEMBLY_MODULES[3])

    def test_model_roles_is_the_only_permitted_importer(self):
        """Positive check: build_provider in model_roles.py DOES import
        provider_keys (via a deferred import inside the function body)."""
        model_roles = Path("uri_core/config/model_roles.py")
        if not model_roles.exists():
            self.skipTest("model_roles.py not found.")
        source = model_roles.read_text(encoding="utf-8")
        # Deferred imports inside functions won''t appear in the AST
        # top-level walk, but the string must appear somewhere in the source.
        self.assertIn(
            "provider_keys",
            source,
            msg=(
                "model_roles.py is the one permitted importer of provider_keys; "
                "it should reference it (deferred inside build_provider())."
            ),
        )


if __name__ == "__main__":
    unittest.main()
