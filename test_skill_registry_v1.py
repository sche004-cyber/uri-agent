import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "uri_workspace" / "skill_registry.json"


def load_registry():
    assert REGISTRY_PATH.exists(), f"Registry not found: {REGISTRY_PATH}"

    with REGISTRY_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def items_by_name(registry):
    return {
        item["normalized_name"]: item
        for item in registry["items"]
    }


class TestSkillRegistryV1(unittest.TestCase):

    def test_registry_file_exists(self):
        self.assertTrue(REGISTRY_PATH.exists())

    def test_registry_schema(self):
        registry = load_registry()

        self.assertEqual(registry["schema_version"], "1.0")
        self.assertEqual(registry["registry_name"], "URI Skill Registry")
        self.assertEqual(registry["registry_version"], "v1")
        self.assertIs(registry["runtime_authoritative"], True)
        self.assertIsInstance(registry["items"], list)
        self.assertEqual(
            registry["total_items"],
            len(registry["items"])
        )
        self.assertGreater(registry["total_items"], 0)

    def test_registry_entries_have_required_fields(self):
        registry = load_registry()

        required = {
            "name",
            "normalized_name",
            "source",
            "category",
            "purpose",
            "input_requirements",
            "output_type",
            "token_saving_potential",
            "latency",
            "reliability",
            "privacy_implications",
            "external_dependencies",
            "execution_risk",
            "model_facing",
            "runtime_facing",
            "invocation_conditions",
            "integration_status",
            "hermes_should_handle",
        }

        for item in registry["items"]:
            missing = required - set(item)

            self.assertFalse(
                missing,
                f"{item.get('name')} missing fields: "
                f"{sorted(missing)}"
            )

    def test_registry_has_unique_identities(self):
        registry = load_registry()

        identities = [
            (
                item["source"],
                item["normalized_name"]
            )
            for item in registry["items"]
        ]

        self.assertEqual(
            len(identities),
            len(set(identities)),
            "Duplicate (source, normalized_name) identities detected"
        )

    def test_core_uri_capabilities_are_correct(self):
        registry = load_registry()
        items = items_by_name(registry)

        expected_core = {
            "draft_institutional_note",
            "draft_institutional_order",
            "extract_student_records",
            "fetch_drive_spreadsheet",
            "tool_i_need_to_renew",
            "tool_i_want_to_submit",
        }

        for name in expected_core:
            self.assertIn(
                name,
                items,
                f"Missing core capability: {name}"
            )

            item = items[name]

            self.assertEqual(
                item["category"],
                "uri_core_capability"
            )

            self.assertTrue(item["runtime_facing"])

    def test_defuddle_is_integrated_pre_reasoning_optimization(self):
        registry = load_registry()
        items = items_by_name(registry)

        self.assertIn("defuddle_tool", items)

        item = items["defuddle_tool"]

        self.assertEqual(
            item["category"],
            "skill_optimization"
        )

        self.assertEqual(
            item["token_saving_potential"],
            "high"
        )

        self.assertEqual(
            item["integration_status"],
            "integrated"
        )

        self.assertIn(
            "pre_reasoning",
            item["invocation_conditions"]
        )

        self.assertEqual(
            item["execution_risk"],
            "low"
        )

        self.assertTrue(item["model_facing"])
        self.assertFalse(item["runtime_facing"])

    def test_high_token_optimization_candidates(self):
        registry = load_registry()
        items = items_by_name(registry)

        expected = {
            "defuddle_tool",
            "dspy",
            "guidance",
            "huggingface-tokenizers",
            "instructor",
            "nemo-curator",
            "outlines",
            "qmd",
            "scrapling",
            "whisper",
        }

        for name in expected:
            self.assertIn(
                name,
                items,
                f"Missing optimization candidate: {name}"
            )

            item = items[name]

            self.assertEqual(
                item["category"],
                "skill_optimization"
            )

            self.assertEqual(
                item["token_saving_potential"],
                "high"
            )

    def test_context7_is_optimization_candidate(self):
        registry = load_registry()
        items = items_by_name(registry)

        self.assertIn("context7", items)

        item = items["context7"]

        self.assertEqual(
            item["category"],
            "skill_optimization"
        )

        self.assertEqual(
            item["token_saving_potential"],
            "medium"
        )

    def test_model_providers_are_separate(self):
        registry = load_registry()
        items = items_by_name(registry)

        expected = {
            "actual",
            "ai-gateway",
            "alibaba",
            "anthropic",
            "deepseek",
            "gemini",
            "gmi",
            "huggingface",
            "ollama-cloud",
            "openai-codex",
            "openrouter",
            "qwen-oauth",
            "vertex",
            "xai",
        }

        for name in expected:
            self.assertIn(
                name,
                items,
                f"Missing model provider: {name}"
            )

            self.assertEqual(
                items[name]["category"],
                "model_provider"
            )

    def test_nit_sikkim_specialized_skill_is_preserved(self):
        registry = load_registry()
        items = items_by_name(registry)

        self.assertIn(
            "nit-sikkim-office-assistant",
            items
        )

        self.assertEqual(
            items["nit-sikkim-office-assistant"]["category"],
            "specialized"
        )

    def test_hermes_specialist_is_separate(self):
        registry = load_registry()
        items = items_by_name(registry)

        self.assertIn("hermes-agent", items)

        item = items["hermes-agent"]

        self.assertEqual(
            item["category"],
            "hermes_specialist"
        )

        self.assertTrue(
            item["hermes_should_handle"]
        )

        self.assertEqual(
            item["execution_risk"],
            "high"
        )

    def test_optimization_skills_are_model_facing(self):
        registry = load_registry()

        optimization_items = [
            item
            for item in registry["items"]
            if item["category"] == "skill_optimization"
        ]

        self.assertGreater(
            len(optimization_items),
            0
        )

        for item in optimization_items:
            self.assertTrue(
                item["model_facing"],
                f"{item['name']} is not model-facing"
            )

            self.assertFalse(
                item["runtime_facing"],
                f"{item['name']} incorrectly has runtime authority"
            )

    def test_runtime_authority_is_explicit(self):
        registry = load_registry()

        self.assertIs(
            registry["runtime_authoritative"],
            True
        )

        for item in registry["items"]:
            if item["category"] == "uri_core_capability":
                self.assertTrue(
                    item["runtime_facing"],
                    f"{item['name']} must be runtime-facing"
                )

    def test_ecosystem_layers_are_present(self):
        registry = load_registry()

        categories = {
            item["category"]
            for item in registry["items"]
        }

        expected_categories = {
            "uri_core_capability",
            "skill_optimization",
            "model_provider",
            "model_infrastructure",
            "on_demand_skill",
            "integration",
        }

        for category in expected_categories:
            self.assertIn(
                category,
                categories,
                f"Missing ecosystem category: {category}"
            )


if __name__ == "__main__":
    print("=" * 72)
    print("URI SKILL REGISTRY V1 TEST SUITE")
    print("=" * 72)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSkillRegistryV1
    )

    result = unittest.TextTestRunner(
        verbosity=2
    ).run(suite)

    print()
    print("=" * 72)

    if result.wasSuccessful():
        print("REGISTRY TESTS: PASS")
    else:
        print("REGISTRY TESTS: FAIL")

    print("=" * 72)

    raise SystemExit(
        0 if result.wasSuccessful() else 1
    )
