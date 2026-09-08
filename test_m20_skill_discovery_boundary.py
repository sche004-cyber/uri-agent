"""M20 (requirement 6): confirms M20's changes do not weaken the
existing skill-installation quarantine boundary - a genuinely new
skill, however discovered, still requires explicit human promotion
before it can execute, and no code path this milestone touched can
write to the live capability registry or call SkillInstaller
automatically.

M20 deliberately did NOT build any new skill-discovery, skill-
installation, or capability-promotion mechanism (see the M20
completion report's "what was not built"). This file is a boundary-
preservation check, not a test of new functionality.
"""

import ast
import os
import unittest


_ORCHESTRATOR_PATH = os.path.join(
    "uri_core", "core", "orchestrator.py"
)


def _module_source(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


class NoRuntimePathWritesTheRegistryTests(unittest.TestCase):
    """Static check: no function in orchestrator.py opens
    capabilities_registry.json in a write mode, mirroring
    test_authoritative_facts_immutability.py's own discipline for
    CapabilityRegistry/ModelReasoningGateway."""

    def test_orchestrator_never_opens_capabilities_registry_for_writing(self):
        source = _module_source(_ORCHESTRATOR_PATH)
        tree = ast.parse(source)

        write_modes = {"w", "a", "x", "w+", "a+", "r+"}
        offending = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "open"):
                continue

            args = node.args
            mode = None
            if len(args) >= 2 and isinstance(args[1], ast.Constant):
                mode = args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value

            if mode in write_modes:
                offending.append(ast.dump(node))

        # orchestrator.py delegates all persistence to dedicated store
        # classes (SessionManager, AuditTrail, SkillMemory, FileStore,
        # ...) - it performs no file I/O of its own, capability
        # registry included. A future write-mode open() appearing here
        # at all is worth a human look, regardless of which file it
        # targets.
        self.assertEqual(offending, [])


class SkillInstallerStaysQuarantinedTests(unittest.TestCase):
    """SkillInstaller's own lifecycle guarantee (installed skills stay
    "quarantined" until a human explicitly enables them, and even
    "enabled" never becomes dispatcher-executable on its own) is
    unmodified by M20 - this is the existing boundary
    uri_core/skills/skill_installer.py already documents and
    test_m18_memory_learning.py already exercises; this test only
    confirms M20 added no alternate path around it."""

    def test_orchestrator_never_imports_skill_installer(self):
        source = _module_source(_ORCHESTRATOR_PATH)
        self.assertNotIn("skill_installer", source)
        self.assertNotIn("SkillInstaller", source)

    def test_capability_feasibility_never_imports_skill_installer(self):
        path = os.path.join(
            "uri_core", "core", "capability_feasibility.py"
        )
        source = _module_source(path)
        self.assertNotIn("skill_installer", source)
        self.assertNotIn("SkillInstaller", source)

    def test_model_reasoning_adapter_research_addendum_never_mentions_install(
        self,
    ):
        """The new W5 research-recovery prompt clause must not
        introduce language that could be read as authorizing
        self-installation - it only ever talks about web_search/
        fetch_url, both already-registered capabilities."""

        path = os.path.join(
            "uri_core", "core", "model_reasoning_adapter.py"
        )
        source = _module_source(path)
        self.assertIn("_RESEARCH_RECOVERY_ADDENDUM", source)
        start = source.index("_RESEARCH_RECOVERY_ADDENDUM = ")
        end = source.index('"""', source.index('"""', start) + 3)
        addendum_text = source[start:end].lower()
        self.assertNotIn("install", addendum_text)
        self.assertNotIn("registry", addendum_text)


if __name__ == "__main__":
    unittest.main()
