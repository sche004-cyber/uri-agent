"""M32 Precondition Tests: Capability Effect Classification.

Guarantees:
1. Every capability has an explicit EffectType (READ_ONLY, LOCAL_WRITE, EXTERNAL_WRITE).
2. Action.read_only is strictly synchronized with effect_type == EffectType.READ_ONLY.
3. Mutating tools (e.g. remember_fact, generate_document, convert_document,
   draft_institutional_note, draft_institutional_order) with approval="none"
   are NEVER falsely classified as read_only=True.
4. Parallel execution and scheduling must rely on real EffectType, never on
   approval == "none".
"""

import unittest
from uri_core.capabilities.base import Action, EffectType, ApprovalRequirement, RiskLevel
from uri_core.capabilities.registry import LegacyCapabilityAdapter, KNOWN_CAPABILITY_EFFECTS
from uri_core.core.capability_registry import CapabilityRegistry


class CapabilityEffectClassificationTests(unittest.TestCase):

    def test_effect_type_enum_members(self):
        self.assertEqual(EffectType.READ_ONLY.value, "read_only")
        self.assertEqual(EffectType.LOCAL_WRITE.value, "local_write")
        self.assertEqual(EffectType.EXTERNAL_WRITE.value, "external_write")

    def test_action_read_only_is_strictly_bound_to_effect_type(self):
        read_action = Action(
            name="test_read",
            description="Test read action",
            effect_type=EffectType.READ_ONLY,
            approval_requirement=ApprovalRequirement.NONE,
        )
        self.assertTrue(read_action.read_only)
        self.assertEqual(read_action.effect_type, EffectType.READ_ONLY)

        local_write_action = Action(
            name="test_local_write",
            description="Test local write action",
            effect_type=EffectType.LOCAL_WRITE,
            approval_requirement=ApprovalRequirement.NONE,
        )
        self.assertFalse(local_write_action.read_only)
        self.assertEqual(local_write_action.effect_type, EffectType.LOCAL_WRITE)

        ext_write_action = Action(
            name="test_ext_write",
            description="Test external write action",
            effect_type=EffectType.EXTERNAL_WRITE,
            approval_requirement=ApprovalRequirement.USER_APPROVAL_REQUIRED,
        )
        self.assertFalse(ext_write_action.read_only)
        self.assertEqual(ext_write_action.effect_type, EffectType.EXTERNAL_WRITE)

    def test_mutating_approval_free_tools_are_not_read_only(self):
        """Regression test for the critical safety flaw:
        Deriving read_only = (approval == 'none') falsely marked
        mutating tools as read_only=True.
        """
        mutating_tools = [
            "draft_institutional_note",
            "draft_institutional_order",
            "generate_document",
            "remember_fact",
            "convert_document",
        ]
        reg = CapabilityRegistry()
        for tool_name in mutating_tools:
            desc = reg.describe_status(tool_name)
            self.assertIsNotNone(desc, f"Tool {tool_name} must exist in registry")
            self.assertEqual(
                desc.approval_requirement,
                "none",
                f"{tool_name} was chosen because its approval is none",
            )
            self.assertEqual(
                desc.effect_type,
                "local_write",
                f"{tool_name} must have effect_type 'local_write', not read_only",
            )
            action_cap = LegacyCapabilityAdapter.from_descriptor(desc)
            action = action_cap.actions[tool_name]
            self.assertEqual(action.effect_type, EffectType.LOCAL_WRITE)
            self.assertFalse(
                action.read_only,
                f"{tool_name} mutates state and must NEVER be read_only=True",
            )

    def test_pure_read_tools_are_read_only(self):
        pure_reads = [
            "extract_student_records",
            "fetch_drive_spreadsheet",
            "system_performance",
            "recall_memory",
            "read_attached_file",
            "gmail_search",
            "gmail_find_draft",
            "web_search",
            "drive_search",
            "fetch_url",
        ]
        reg = CapabilityRegistry()
        for tool_name in pure_reads:
            desc = reg.describe_status(tool_name)
            self.assertIsNotNone(desc, f"Tool {tool_name} must exist in registry")
            self.assertEqual(
                desc.effect_type,
                "read_only",
                f"{tool_name} must have effect_type 'read_only'",
            )
            action_cap = LegacyCapabilityAdapter.from_descriptor(desc)
            action = action_cap.actions[tool_name]
            self.assertEqual(action.effect_type, EffectType.READ_ONLY)
            self.assertTrue(action.read_only)

    def test_external_write_tools_are_external_write(self):
        ext_writes = ["gmail_create_draft", "drive_upload"]
        reg = CapabilityRegistry()
        for tool_name in ext_writes:
            desc = reg.describe_status(tool_name)
            self.assertIsNotNone(desc, f"Tool {tool_name} must exist in registry")
            self.assertEqual(
                desc.effect_type,
                "external_write",
                f"{tool_name} must have effect_type 'external_write'",
            )
            action_cap = LegacyCapabilityAdapter.from_descriptor(desc)
            action = action_cap.actions[tool_name]
            self.assertEqual(action.effect_type, EffectType.EXTERNAL_WRITE)
            self.assertFalse(action.read_only)

    def test_known_effects_dictionary_covers_all_shipped_tools(self):
        reg = CapabilityRegistry()
        all_ids = {c.id for c in reg.list_capabilities() if c.is_executable}
        for tool_id in all_ids:
            self.assertIn(
                tool_id,
                KNOWN_CAPABILITY_EFFECTS,
                f"Shipped tool {tool_id} must have a verified effect in KNOWN_CAPABILITY_EFFECTS",
            )


if __name__ == "__main__":
    unittest.main()
