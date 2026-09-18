"""test_m33_batch_a_external_capability_contract.py — M33 Batch A.

Tests uri_core/external/{contract,validator,qualification,lifecycle,
store}.py against the frozen blueprint's Batch A exit criteria:
contract/lifecycle tests pass; explicit user-A/user-B isolation for the
qualification record, lifecycle store, and every path constructed
through user_scoped_path; no adapter reachable from any execution path;
no registry change.
"""
from __future__ import annotations

import importlib
import tempfile
import unittest
import uuid

from uri_core.core.portable_paths import PortablePathValidationError
from uri_core.external import contract, lifecycle, qualification, store, validator


def _valid_descriptor(action_name="do_thing", **overrides):
    data = {
        "contract_version": "1.0",
        "id": "fixture.example_tool",
        "name": "Example Tool",
        "description": "A fixture external capability.",
        "category": "research",
        "transport": "in_process",
        "actions": {
            action_name: {
                "name": action_name,
                "description": "Does the thing.",
                "interface": {
                    "parameters": {
                        "query": {"type": "string", "minLength": 1, "maxLength": 200},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    },
                    "required": ["query"],
                    "returns": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"type": "string"},
                                "maxItems": 50,
                            }
                        },
                    },
                },
            }
        },
    }
    data.update(overrides)
    return data


class DescriptorValidationTests(unittest.TestCase):
    def test_valid_descriptor_passes(self):
        result = contract.validate_descriptor(_valid_descriptor())
        self.assertTrue(result.valid, result.reasons)

    def test_unknown_major_version_fails_closed(self):
        result = contract.validate_descriptor(_valid_descriptor(contract_version="99.0"))
        self.assertFalse(result.valid)
        self.assertTrue(any("contract_version" in r for r in result.reasons))

    def test_missing_required_field_fails(self):
        data = _valid_descriptor()
        del data["transport"]
        result = contract.validate_descriptor(data)
        self.assertFalse(result.valid)

    def test_unsupported_transport_fails_closed(self):
        result = contract.validate_descriptor(_valid_descriptor(transport="mcp"))
        self.assertFalse(result.valid)

    def test_unsupported_schema_construct_fails_closed(self):
        data = _valid_descriptor()
        data["actions"]["do_thing"]["interface"]["parameters"]["query"]["format"] = "email"
        result = contract.validate_descriptor(data)
        self.assertFalse(result.valid)
        self.assertTrue(any("unsupported schema construct" in r for r in result.reasons))

    def test_ref_keyword_fails_closed(self):
        data = _valid_descriptor()
        data["actions"]["do_thing"]["interface"]["parameters"]["query"]["$ref"] = "#/defs/x"
        result = contract.validate_descriptor(data)
        self.assertFalse(result.valid)

    def test_excess_nesting_depth_fails_closed(self):
        node = {"type": "string"}
        for _ in range(contract.MAX_SCHEMA_DEPTH + 3):
            node = {"type": "object", "properties": {"child": node}}
        data = _valid_descriptor()
        data["actions"]["do_thing"]["interface"]["parameters"]["query"] = node
        result = contract.validate_descriptor(data)
        self.assertFalse(result.valid)
        self.assertTrue(any("max depth" in r for r in result.reasons))

    def test_bad_id_characters_fail(self):
        result = contract.validate_descriptor(_valid_descriptor(id="not a valid id!"))
        self.assertFalse(result.valid)

    def test_descriptor_from_dict_round_trips(self):
        data = _valid_descriptor()
        validation = contract.validate_descriptor(data)
        self.assertTrue(validation.valid)
        descriptor = contract.descriptor_from_dict(data)
        self.assertEqual(descriptor.id, "fixture.example_tool")
        self.assertEqual(descriptor.major_version(), 1)
        self.assertIn("do_thing", descriptor.actions)
        round_tripped = descriptor.to_dict()
        self.assertEqual(round_tripped["id"], data["id"])


class ExternalActionValidatorTests(unittest.TestCase):
    def _validator(self):
        data = _valid_descriptor()
        interface = data["actions"]["do_thing"]["interface"]
        return validator.ExternalActionValidator(interface)

    def test_valid_input_passes(self):
        outcome = self._validator().validate_input({"query": "hello", "limit": 5})
        self.assertTrue(outcome.ok, outcome.errors)

    def test_missing_required_is_invalid_input(self):
        outcome = self._validator().validate_input({"limit": 5})
        self.assertEqual(outcome.outcome, validator.OUTCOME_INVALID_INPUT)

    def test_unknown_parameter_is_invalid_input(self):
        outcome = self._validator().validate_input({"query": "hi", "extra": "nope"})
        self.assertEqual(outcome.outcome, validator.OUTCOME_INVALID_INPUT)

    def test_length_bound_enforced(self):
        outcome = self._validator().validate_input({"query": ""})
        self.assertEqual(outcome.outcome, validator.OUTCOME_INVALID_INPUT)

    def test_range_bound_enforced(self):
        outcome = self._validator().validate_input({"query": "hi", "limit": 999})
        self.assertEqual(outcome.outcome, validator.OUTCOME_INVALID_INPUT)

    def test_type_mismatch_enforced(self):
        outcome = self._validator().validate_input({"query": 123})
        self.assertEqual(outcome.outcome, validator.OUTCOME_INVALID_INPUT)

    def test_enum_and_pattern_enforced(self):
        v = validator.ExternalActionValidator(
            {"parameters": {"mode": {"type": "string", "enum": ["fast", "slow"]}}, "required": ["mode"]}
        )
        self.assertTrue(v.validate_input({"mode": "fast"}).ok)
        self.assertFalse(v.validate_input({"mode": "medium"}).ok)

        v2 = validator.ExternalActionValidator(
            {"parameters": {"code": {"type": "string", "pattern": r"^[A-Z]{3}$"}}, "required": ["code"]}
        )
        self.assertTrue(v2.validate_input({"code": "ABC"}).ok)
        self.assertFalse(v2.validate_input({"code": "abc"}).ok)

    def test_nested_items_and_properties_enforced(self):
        v = validator.ExternalActionValidator(
            {
                "parameters": {
                    "record": {
                        "type": "object",
                        "properties": {"tags": {"type": "array", "items": {"type": "string"}, "maxItems": 2}},
                    }
                }
            }
        )
        self.assertTrue(v.validate_input({"record": {"tags": ["a", "b"]}}).ok)
        outcome = v.validate_input({"record": {"tags": ["a", "b", "c"]}})
        self.assertFalse(outcome.ok)

    def test_output_none_is_no_result(self):
        outcome = self._validator().validate_output(None)
        self.assertEqual(outcome.outcome, validator.OUTCOME_NO_RESULT)

    def test_malformed_output_is_invalid_output_not_no_result(self):
        outcome = self._validator().validate_output({"items": "not-a-list"})
        self.assertEqual(outcome.outcome, validator.OUTCOME_INVALID_OUTPUT)
        self.assertNotEqual(outcome.outcome, validator.OUTCOME_NO_RESULT)

    def test_valid_output_passes(self):
        outcome = self._validator().validate_output({"items": ["a", "b"]})
        self.assertTrue(outcome.ok, outcome.errors)


class QualifierTests(unittest.TestCase):
    def test_valid_descriptor_qualifies(self):
        record = qualification.Qualifier().qualify(
            _valid_descriptor(), source_revision="rev-1", dependency_lock={"pkgA": "1.2.3"}
        )
        self.assertEqual(record.status, qualification.STATUS_QUALIFIED)
        self.assertTrue(record.profile_digest)
        self.assertEqual(record.reasons, [])

    def test_invalid_descriptor_is_rejected_with_reasons(self):
        record = qualification.Qualifier().qualify(
            _valid_descriptor(transport="mcp"), source_revision="rev-1"
        )
        self.assertEqual(record.status, qualification.STATUS_REJECTED)
        self.assertTrue(record.reasons)

    def test_digest_stable_for_same_input(self):
        d1 = qualification.profile_digest(_valid_descriptor(), {"pkgA": "1.0"})
        d2 = qualification.profile_digest(_valid_descriptor(), {"pkgA": "1.0"})
        self.assertEqual(d1, d2)

    def test_digest_changes_with_dependency_lock(self):
        d1 = qualification.profile_digest(_valid_descriptor(), {"pkgA": "1.0"})
        d2 = qualification.profile_digest(_valid_descriptor(), {"pkgA": "2.0"})
        self.assertNotEqual(d1, d2)

    def test_no_import_or_execution_occurs(self):
        """Static-only: qualifying a descriptor naming a nonexistent
        module/binary must never raise ImportError/FileNotFoundError -
        nothing here is ever imported or run."""
        data = _valid_descriptor(id="fixture.nonexistent_binary_xyz")
        record = qualification.Qualifier().qualify(data, source_revision="rev-1")
        self.assertEqual(record.status, qualification.STATUS_QUALIFIED)


class LifecycleTests(unittest.TestCase):
    def test_label_derivation_order_is_data_driven(self):
        state = lifecycle.LifecycleState(descriptor_id="x")
        self.assertEqual(lifecycle.derive_label(state), "not_installed")

        state.presence = lifecycle.PRESENCE_PRESENT
        self.assertEqual(lifecycle.derive_label(state), "unqualified")

        state.qualification = lifecycle.QUALIFICATION_REJECTED
        self.assertEqual(lifecycle.derive_label(state), "rejected")

        state.qualification = lifecycle.QUALIFICATION_QUALIFIED
        self.assertEqual(lifecycle.derive_label(state), "needs_configuration")

        state.configuration = lifecycle.CONFIGURATION_CONFIGURED
        state.authentication = lifecycle.AUTHENTICATION_UNAUTHENTICATED
        self.assertEqual(lifecycle.derive_label(state), "needs_authentication")

        state.authentication = lifecycle.AUTHENTICATION_AUTHENTICATED
        state.health = lifecycle.UNHEALTHY
        self.assertEqual(lifecycle.derive_label(state), "unhealthy")

        state.health = lifecycle.HEALTHY
        self.assertEqual(lifecycle.derive_label(state), "disabled")

        state.enabled = True
        self.assertEqual(lifecycle.derive_label(state), "ready")

        state.update_available = True
        self.assertEqual(lifecycle.derive_label(state), "update_available")

    def test_happy_path_transitions(self):
        controller = lifecycle.LifecycleController()
        state = controller.detect("fixture.example_tool")
        state = controller.apply_qualification(state, qualified=True)
        state = controller.configure(state)
        state = controller.authenticate(state)
        state = controller.report_health(state, healthy=True)
        state = controller.enable(state)
        self.assertTrue(state.enabled)
        self.assertEqual(lifecycle.derive_label(state), "ready")

    def test_cannot_configure_unqualified(self):
        controller = lifecycle.LifecycleController()
        state = controller.detect("x")
        with self.assertRaises(lifecycle.LifecycleTransitionError):
            controller.configure(state)

    def test_cannot_enable_unconfigured(self):
        controller = lifecycle.LifecycleController()
        state = controller.detect("x")
        state = controller.apply_qualification(state, qualified=True)
        with self.assertRaises(lifecycle.LifecycleTransitionError):
            controller.enable(state)


class ExternalCapabilityStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = store.ExternalCapabilityStore(root=self.tmp)
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())

    def test_register_and_get_round_trips(self):
        result = self.store.register_descriptor(_valid_descriptor(), user_id=self.user_a, source_revision="rev-1")
        self.assertTrue(result.ok, result.reasons)
        record = self.store.get(self.user_a, "fixture.example_tool")
        self.assertIsNotNone(record)
        self.assertEqual(record["qualification"]["status"], "qualified")
        self.assertFalse(record["lifecycle"]["enabled"], "never auto-enabled on registration")

    def test_invalid_descriptor_registers_but_stays_rejected_not_enabled(self):
        result = self.store.register_descriptor(_valid_descriptor(transport="mcp"), user_id=self.user_a)
        self.assertFalse(result.ok)
        record = self.store.get(self.user_a, "fixture.example_tool")
        self.assertEqual(record["qualification"]["status"], "rejected")
        self.assertFalse(record["lifecycle"]["enabled"])

    def test_full_lifecycle_round_trip_through_store(self):
        self.store.register_descriptor(_valid_descriptor(), user_id=self.user_a)
        self.store.configure(self.user_a, "fixture.example_tool")
        self.store.authenticate(self.user_a, "fixture.example_tool")
        self.store.report_health(self.user_a, "fixture.example_tool", healthy=True)
        enabled = self.store.enable(self.user_a, "fixture.example_tool")
        self.assertTrue(enabled["enabled"])
        disabled = self.store.disable(self.user_a, "fixture.example_tool")
        self.assertFalse(disabled["enabled"])

    def test_user_a_and_user_b_are_mutually_isolated(self):
        """Explicit user-A/user-B isolation, per Batch A's exit criteria:
        two distinct user IDs must never observe or affect each other's
        qualification, install, or configuration state."""
        self.store.register_descriptor(_valid_descriptor(), user_id=self.user_a)
        # user_b has registered nothing at all.
        self.assertIsNone(self.store.get(self.user_b, "fixture.example_tool"))
        self.assertEqual(self.store.list_all(self.user_b), [])

        # Mutating user_a's lifecycle must never appear under user_b.
        self.store.configure(self.user_a, "fixture.example_tool")
        self.assertIsNone(self.store.get(self.user_b, "fixture.example_tool"))

        # user_b registers its own copy of the SAME descriptor id and
        # enables it fully; user_a's own record must be unaffected.
        self.store.register_descriptor(_valid_descriptor(), user_id=self.user_b)
        self.store.configure(self.user_b, "fixture.example_tool")
        self.store.authenticate(self.user_b, "fixture.example_tool")
        self.store.report_health(self.user_b, "fixture.example_tool", healthy=True)
        self.store.enable(self.user_b, "fixture.example_tool")

        record_a = self.store.get(self.user_a, "fixture.example_tool")
        record_b = self.store.get(self.user_b, "fixture.example_tool")
        self.assertFalse(record_a["lifecycle"]["enabled"], "user_a must not observe user_b's enable")
        self.assertTrue(record_b["lifecycle"]["enabled"])
        self.assertEqual(record_a["lifecycle"]["configuration"], "configured")
        self.assertNotEqual(record_a["lifecycle"]["authentication"], record_b["lifecycle"]["authentication"])

    def test_both_users_stores_live_under_their_own_user_scoped_path(self):
        self.store.register_descriptor(_valid_descriptor(), user_id=self.user_a)
        self.store.register_descriptor(_valid_descriptor(), user_id=self.user_b)
        path_a = self.store._path(self.user_a)
        path_b = self.store._path(self.user_b)
        self.assertNotEqual(path_a, path_b)
        self.assertIn(self.user_a, path_a)
        self.assertIn(self.user_b, path_b)

    def test_non_uuid_user_id_is_rejected(self):
        with self.assertRaises(PortablePathValidationError):
            self.store.register_descriptor(_valid_descriptor(), user_id="not-a-uuid")

    def test_restart_recovery_fresh_store_instance_sees_same_data(self):
        self.store.register_descriptor(_valid_descriptor(), user_id=self.user_a, source_revision="rev-1")
        fresh_store = store.ExternalCapabilityStore(root=self.tmp)
        record = fresh_store.get(self.user_a, "fixture.example_tool")
        self.assertIsNotNone(record)
        self.assertEqual(record["qualification"]["source_revision"], "rev-1")


class NoAdapterReachableFromExecutionTests(unittest.TestCase):
    """Batch A's own exit criterion: no adapter is reachable from any
    execution path, and no registry change has happened yet. Proven
    structurally - none of the five new modules import anything from the
    real dispatch/execution/registry surface."""

    FORBIDDEN_IMPORT_SUBSTRINGS = (
        "multi_action_dispatch",
        "canonical_execution",
        "capability_directory",
        "capabilities.registry",
        "capabilities.executor",
    )

    def test_no_batch_a_module_imports_the_execution_surface(self):
        for module_name in (
            "uri_core.external.contract",
            "uri_core.external.validator",
            "uri_core.external.qualification",
            "uri_core.external.lifecycle",
            "uri_core.external.store",
        ):
            module = importlib.import_module(module_name)
            source_path = module.__file__
            with open(source_path, "r", encoding="utf-8") as handle:
                source = handle.read()
            for forbidden in self.FORBIDDEN_IMPORT_SUBSTRINGS:
                self.assertNotIn(
                    forbidden, source, f"{module_name} must not reference {forbidden} in Batch A"
                )


if __name__ == "__main__":
    unittest.main()
