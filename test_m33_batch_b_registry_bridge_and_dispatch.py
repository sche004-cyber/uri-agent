"""test_m33_batch_b_registry_bridge_and_dispatch.py — M33 Batch B.

Tests the frozen blueprint's Batch B scope against real collaborators
throughout (Model-free where possible, mirroring test_canonical_
execution.py's own standing convention): `uri_core/external/registry_
bridge.py`, `permission_binding.py`, the generalized seams in
`multi_action_dispatch.py`/`capabilities/context_resolver.py`/
`core/canonical_execution.py`/`core/capability_directory.py`, and the
bounded metadata extension in `capabilities/base.py`.

Exit criteria covered: the in-process fixture profile is discovered
(via CapabilityDirectory summaries, the same surface `preselect_
candidate_ids` reads) and executed through the real canonical dispatch
path into Brain-visible evidence; denied cases invoke no adapter;
existing Gmail behavior is unchanged (asserted by re-running the exact
Gmail-specific assertions test_canonical_execution.py already makes,
now through the generalized `_execute_multi_action`).
"""
from __future__ import annotations

import tempfile
import unittest
import uuid
from types import SimpleNamespace

from uri_core.capabilities import MultiActionCapabilityRegistry, MultiActionExecutor
from uri_core.capabilities.base import Action, ApprovalRequirement, Capability, EffectType
from uri_core.capabilities.context_resolver import CapabilityContextResolver
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.canonical_execution import _execute_multi_action
from uri_core.core.capability_directory import CapabilityDirectory
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from uri_core.external.permission_binding import external_permission_resolver, make_permission_resolver
from uri_core.external.registry_bridge import (
    ExternalCapabilityPublisher,
    descriptor_record_to_capability,
)
from uri_core.external.store import ExternalCapabilityStore
from test_multi_action_capabilities import FakeGmailService


def _descriptor(action_name="fetch_thing", capability_id="fixture.example_tool", **overrides):
    data = {
        "contract_version": "1.0",
        "id": capability_id,
        "name": "Example Tool",
        "description": "A fixture external capability for Batch B tests.",
        "category": "research",
        "transport": "in_process",
        "aliases": ["example", "the example tool"],
        "intent_signals": ["research_lookup"],
        "actions": {
            action_name: {
                "name": action_name,
                "description": "Fetches the thing.",
                "interface": {
                    "parameters": {"query": {"type": "string", "minLength": 1}},
                    "required": ["query"],
                    "returns": {"type": "object"},
                },
                "permissions": ["fixture.read"],
            }
        },
    }
    data.update(overrides)
    return data


def _fixture_handler(**kwargs):
    return {"status": "success", "items": ["real evidence"], "query": kwargs.get("query")}


def _new_user_id() -> str:
    return str(uuid.uuid4())


def _enabled_store_with_one_capability(tmp_root, user_id, action_name="fetch_thing", capability_id="fixture.example_tool"):
    store = ExternalCapabilityStore(root=tmp_root)
    descriptor = _descriptor(action_name=action_name, capability_id=capability_id)
    result = store.register_descriptor(descriptor, user_id=user_id, source_revision="test-rev")
    assert result.ok, result.reasons
    store.configure(user_id, capability_id)
    store.authenticate(user_id, capability_id)
    store.enable(user_id, capability_id)
    return store


class RegistryBridgePublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.user_id = _new_user_id()

    def test_enabled_qualified_descriptor_publishes_as_real_multi_action_capability(self):
        store = _enabled_store_with_one_capability(self.tmp.name, self.user_id)
        publisher = ExternalCapabilityPublisher(store=store)
        result = publisher.publish(self.user_id, handler_resolver=lambda *_: _fixture_handler)
        self.assertIn("fixture.example_tool", result.published_ids)
        capability = result.registry.get_capability("fixture.example_tool")
        self.assertIsNotNone(capability)
        self.assertEqual(capability.category, "research")
        self.assertEqual(tuple(capability.aliases), ("example", "the example tool"))
        action = capability.get_action("fetch_thing")
        self.assertIsNotNone(action)
        self.assertEqual(tuple(action.permissions), ("fixture.read",))
        self.assertIsNotNone(action.handler)

    def test_unqualified_or_disabled_descriptor_is_never_published(self):
        store = ExternalCapabilityStore(root=self.tmp.name)
        # Structurally invalid -> rejected qualification, never enabled.
        bad = _descriptor()
        del bad["transport"]
        store.register_descriptor(bad, user_id=self.user_id)
        publisher = ExternalCapabilityPublisher(store=store)
        result = publisher.publish(self.user_id)
        self.assertNotIn("fixture.example_tool", result.published_ids)
        self.assertIsNone(result.registry.get_capability("fixture.example_tool"))

        # Qualified but never configured/enabled.
        store2 = ExternalCapabilityStore(root=self.tmp.name)
        store2.register_descriptor(_descriptor(capability_id="fixture.never_enabled"), user_id=self.user_id)
        result2 = ExternalCapabilityPublisher(store=store2).publish(self.user_id)
        self.assertIsNone(result2.registry.get_capability("fixture.never_enabled"))

    def test_base_capabilities_are_preserved_alongside_published_external_ones(self):
        store = _enabled_store_with_one_capability(self.tmp.name, self.user_id)
        publisher = ExternalCapabilityPublisher(store=store)
        result = publisher.publish(self.user_id, base_capabilities=[GmailCapability(FakeGmailService())])
        self.assertIsNotNone(result.registry.get_capability("Gmail"))
        self.assertIsNotNone(result.registry.get_capability("fixture.example_tool"))

    def test_name_collision_with_base_capability_never_shadows_the_trusted_one(self):
        store = _enabled_store_with_one_capability(self.tmp.name, self.user_id, capability_id="Gmail")
        publisher = ExternalCapabilityPublisher(store=store)
        result = publisher.publish(self.user_id, base_capabilities=[GmailCapability(FakeGmailService())])
        self.assertIn("Gmail", result.skipped_ids)
        # The real, trusted Gmail capability (with its real actions) wins.
        self.assertIn("search_messages", [a.name for a in result.registry.get_capability("Gmail").list_actions()])

    def test_disable_produces_a_fresh_generation_no_longer_containing_the_capability(self):
        """D3: atomic swap via a fresh registry instance, never in-place
        mutation of a previously-published one."""
        store = _enabled_store_with_one_capability(self.tmp.name, self.user_id)
        publisher = ExternalCapabilityPublisher(store=store)
        first = publisher.publish(self.user_id)
        self.assertIsNotNone(first.registry.get_capability("fixture.example_tool"))

        store.disable(self.user_id, "fixture.example_tool")
        second = publisher.publish(self.user_id)
        self.assertIsNone(second.registry.get_capability("fixture.example_tool"))
        # The FIRST generation's own registry object is untouched -
        # in-flight work holding it still sees what it started under.
        self.assertIsNotNone(first.registry.get_capability("fixture.example_tool"))


class PermissionBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.user_id = _new_user_id()
        self.store = _enabled_store_with_one_capability(self.tmp.name, self.user_id)
        self.resolver = make_permission_resolver(store=self.store)

    def test_enabled_qualified_capability_resolves_true_for_its_own_user(self):
        principal = SimpleNamespace(user_id=self.user_id)
        self.assertTrue(self.resolver("fixture.example_tool", principal))

    def test_unknown_capability_id_resolves_false(self):
        principal = SimpleNamespace(user_id=self.user_id)
        self.assertFalse(self.resolver("fixture.never_registered", principal))

    def test_different_user_never_inherits_another_users_grant(self):
        other_user_id = _new_user_id()
        principal = SimpleNamespace(user_id=other_user_id)
        self.assertFalse(self.resolver("fixture.example_tool", principal))

    def test_no_principal_or_no_user_id_fails_closed(self):
        self.assertFalse(self.resolver("fixture.example_tool", None))
        self.assertFalse(self.resolver("fixture.example_tool", SimpleNamespace(user_id=None)))

    def test_never_defaults_to_full_registry_the_way_capability_grants_store_does(self):
        """The exact trap the blueprint names: a user with NO explicit
        record must never be treated as granted, unlike `Capability
        GrantsStore.get_grants`'s own documented migration default."""
        untouched_user_id = _new_user_id()
        principal = SimpleNamespace(user_id=untouched_user_id)
        self.assertFalse(self.resolver("fixture.example_tool", principal))

    def test_shared_module_level_resolver_also_fails_closed_with_no_principal(self):
        self.assertFalse(external_permission_resolver("fixture.example_tool", None))


class MultiActionDispatchGeneralizationTests(unittest.TestCase):
    """`_action_permitted`/`_granted_permissions`'s Batch B fallback,
    additive on top of P1's corrected seam - every assertion here is
    about the NEW `external_permission_resolver` path; P1's own Gmail-
    path assertions are untouched and still covered by
    test_m33_p1_permission_seam.py / test_multi_action_capabilities.py."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.user_id = _new_user_id()
        self.store = _enabled_store_with_one_capability(self.tmp.name, self.user_id)
        self.registry = ExternalCapabilityPublisher(store=self.store).publish(
            self.user_id, handler_resolver=lambda *_: _fixture_handler
        ).registry
        self.principal = SimpleNamespace(user_id=self.user_id)
        self.resolver = make_permission_resolver(store=self.store)

    def test_denied_when_resolver_absent_matches_p1s_additive_denial_rule(self):
        dispatch = MultiActionDispatch(registry=self.registry)  # no resolver wired
        envelope = dispatch.dispatch_explicit(
            "fixture.example_tool", "fetch_thing", {"query": "x"},
            session_id="s1", user_text="find the thing", principal=self.principal,
        )
        self.assertEqual(envelope["execution"]["status"], "permission_denied")

    def test_denied_when_resolver_denies_this_specific_user(self):
        other_user_id = _new_user_id()
        dispatch = MultiActionDispatch(registry=self.registry, external_permission_resolver=self.resolver)
        envelope = dispatch.dispatch_explicit(
            "fixture.example_tool", "fetch_thing", {"query": "x"},
            session_id="s1", user_text="find the thing",
            principal=SimpleNamespace(user_id=other_user_id),
        )
        self.assertEqual(envelope["execution"]["status"], "permission_denied")

    def test_allowed_and_executes_real_evidence_when_resolver_grants_it(self):
        dispatch = MultiActionDispatch(registry=self.registry, external_permission_resolver=self.resolver)
        envelope = dispatch.dispatch_explicit(
            "fixture.example_tool", "fetch_thing", {"query": "insurance"},
            session_id="s1", user_text="find the thing", principal=self.principal,
        )
        self.assertEqual(envelope["execution"]["status"], "success")
        self.assertIn("real evidence", envelope["response"]["items"])

    def test_resolver_exception_denies_never_crashes_and_never_executes(self):
        def _raising_resolver(capability_id, principal):
            raise RuntimeError("boom")

        dispatch = MultiActionDispatch(registry=self.registry, external_permission_resolver=_raising_resolver)
        envelope = dispatch.dispatch_explicit(
            "fixture.example_tool", "fetch_thing", {"query": "x"},
            session_id="s1", user_text="find the thing", principal=self.principal,
        )
        self.assertEqual(envelope["execution"]["status"], "permission_denied")

    def test_gmail_authorization_path_is_completely_unaffected_by_a_wired_external_resolver(self):
        """Gmail's own `_ACTION_GRANT_CAPABILITY` alias path must never
        consult `external_permission_resolver`, even when one is wired -
        it is a fallback for ids the Gmail table has no entry for, never
        a second opinion for ids it does."""
        gmail_registry = MultiActionCapabilityRegistry([GmailCapability(FakeGmailService())])
        never_called = {"called": False}

        def _resolver(capability_id, principal):
            never_called["called"] = True
            return False  # would deny if it were ever consulted

        dispatch = MultiActionDispatch(
            registry=gmail_registry, permission_checker=lambda *_: True,
            external_permission_resolver=_resolver,
        )
        envelope = dispatch.dispatch_explicit(
            "Gmail", "search_messages", {"query": "insurance"},
            session_id="s1", user_text="find email", principal=None,
        )
        self.assertEqual(envelope["execution"]["status"], "success")
        self.assertFalse(never_called["called"])

    def test_audit_sink_receives_a_real_execution_entry(self):
        recorded = []
        dispatch = MultiActionDispatch(
            registry=self.registry, external_permission_resolver=self.resolver,
            audit_sink=lambda entry: recorded.append(entry),
        )
        dispatch.dispatch_explicit(
            "fixture.example_tool", "fetch_thing", {"query": "x"},
            session_id="s1", user_text="find the thing", principal=self.principal,
        )
        self.assertTrue(recorded)
        self.assertEqual(recorded[0]["capability"], "fixture.example_tool")
        self.assertEqual(recorded[0]["status"], "success")


class CanonicalExecutionGeneralizationTests(unittest.TestCase):
    """`_execute_multi_action` (the generalized `_execute_gmail`) reached
    via `_execute_canonical`'s registry lookup - real collaborators,
    model-free, mirroring test_canonical_execution.py's own convention."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.user_id = _new_user_id()
        self.store = _enabled_store_with_one_capability(self.tmp.name, self.user_id)
        self.registry = ExternalCapabilityPublisher(store=self.store).publish(
            self.user_id, base_capabilities=[GmailCapability(FakeGmailService())],
            handler_resolver=lambda *_: _fixture_handler,
        ).registry
        self.resolver = make_permission_resolver(store=self.store)
        self.principal = SimpleNamespace(user_id=self.user_id)

    def _dispatch(self):
        return MultiActionDispatch(
            registry=self.registry, external_permission_resolver=self.resolver,
            permission_checker=lambda *_: True,  # Gmail's own legacy alias path
        )

    def test_registered_external_capability_executes_through_the_canonical_path(self):
        orchestrator = SimpleNamespace(multi_action_dispatch=self._dispatch())
        contract = {
            "capability": "fixture.example_tool",
            "actions": [{"name": "fetch_thing", "inputs": {"query": "insurance"}}],
        }
        envelope = _execute_multi_action(
            contract, capability_id="fixture.example_tool", orchestrator=orchestrator,
            session_id="s1", user_text="find the thing", principal=self.principal,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["execution"]["status"], "success")
        self.assertIn("real evidence", envelope["response"]["items"])

    def test_denied_case_never_invokes_the_real_handler(self):
        handler_calls = {"count": 0}

        def _counting_handler(**kwargs):
            handler_calls["count"] += 1
            return _fixture_handler(**kwargs)

        registry = ExternalCapabilityPublisher(store=self.store).publish(
            self.user_id, handler_resolver=lambda *_: _counting_handler
        ).registry
        other_user_principal = SimpleNamespace(user_id=_new_user_id())
        dispatch = MultiActionDispatch(registry=registry, external_permission_resolver=self.resolver)
        orchestrator = SimpleNamespace(multi_action_dispatch=dispatch)
        contract = {
            "capability": "fixture.example_tool",
            "actions": [{"name": "fetch_thing", "inputs": {"query": "insurance"}}],
        }
        envelope = _execute_multi_action(
            contract, capability_id="fixture.example_tool", orchestrator=orchestrator,
            session_id="s1", user_text="find the thing", principal=other_user_principal,
        )
        self.assertEqual(envelope["execution"]["status"], "permission_denied")
        self.assertEqual(handler_calls["count"], 0)

    def test_gmail_still_reached_and_unchanged_through_the_same_generalized_function(self):
        orchestrator = SimpleNamespace(multi_action_dispatch=self._dispatch())
        contract = {
            "capability": "Gmail",
            "actions": [{"name": "search_messages", "inputs": {"query": "insurance"}}],
        }
        envelope = _execute_multi_action(
            contract, capability_id="Gmail", orchestrator=orchestrator,
            session_id="s1", user_text="find the latest insurance email", principal=None,
        )
        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["execution"]["status"], "success")
        self.assertIn("results", envelope["response"])


class ContextResolverGeneralizationTests(unittest.TestCase):
    def test_external_capability_grounds_a_follow_up_reference(self):
        resolver = CapabilityContextResolver()
        resolver.record_action_result(
            "fixture.example_tool", "fetch_thing", {"status": "success", "items": ["a", "b"], "query": "insurance"}
        )
        grounded = resolver.resolve("fetch_thing", "and again", capability="fixture.example_tool")
        self.assertEqual(grounded.get("query"), "insurance")

    def test_gmail_extraction_is_byte_identical_through_the_generalized_registry(self):
        resolver = CapabilityContextResolver()
        resolver.record_action_result(
            "Gmail", "search_messages",
            {"messages": [{"message_id": "m-1", "thread_id": "t-1", "from": "a@example.com", "subject": "Hi"}]},
        )
        grounded = resolver.resolve("read_message", "read that one")
        self.assertEqual(grounded, {"message_id": "m-1"})

    def test_unregistered_capability_with_no_prior_result_grounds_nothing(self):
        resolver = CapabilityContextResolver()
        self.assertEqual(resolver.resolve("fetch_thing", "", capability="fixture.never_called"), {})

    def test_custom_registered_extractor_is_consulted_instead_of_the_generic_fallback(self):
        resolver = CapabilityContextResolver()
        seen = []

        def _extractor(self_, action, result):
            seen.append((action, dict(result)))

        resolver.register_extractor("fixture.example_tool", _extractor)
        resolver.record_action_result("fixture.example_tool", "fetch_thing", {"status": "success"})
        self.assertEqual(seen, [("fetch_thing", {"status": "success"})])


class CapabilityDirectorySummaryExtensionTests(unittest.TestCase):
    def test_multi_action_summary_carries_category_aliases_and_action_descriptions(self):
        registry = MultiActionCapabilityRegistry(
            [
                Capability(
                    name="fixture.example_tool",
                    description="A fixture tool.",
                    category="research",
                    aliases=("example",),
                    intent_signals=("research_lookup",),
                    actions={
                        "fetch_thing": Action(
                            name="fetch_thing", description="Fetches the thing.",
                            effect_type=EffectType.READ_ONLY,
                        )
                    },
                )
            ]
        )
        directory = CapabilityDirectory(multi_action_registry=registry, include_procedures=False)
        summaries = directory.summaries()
        self.assertEqual(len(summaries), 1)
        entry = summaries[0]
        self.assertEqual(entry["category"], "research")
        self.assertEqual(entry["aliases"], ["example"])
        self.assertEqual(entry["intent_signals"], ["research_lookup"])
        self.assertEqual(entry["action_descriptions"], {"fetch_thing": "Fetches the thing."})

    def test_legacy_entry_foundational_reads_descriptor_field_before_hardcoded_set(self):
        from uri_core.core.capability_directory import _is_foundational

        self.assertTrue(_is_foundational("remember_fact", {}))  # hardcoded-set fallback holds
        self.assertFalse(_is_foundational("some_other_id", {}))
        self.assertTrue(_is_foundational("some_other_id", {"foundational": True}))
        self.assertFalse(_is_foundational("remember_fact", {"foundational": False}))  # explicit override wins


class DescriptorRecordToCapabilityTests(unittest.TestCase):
    def test_record_with_no_actions_returns_none(self):
        record = {"descriptor": {"id": "x", "actions": {}}}
        self.assertIsNone(descriptor_record_to_capability(record))

    def test_record_with_no_id_returns_none(self):
        record = {"descriptor": {"actions": {"a": {"name": "a", "description": "", "interface": {}}}}}
        self.assertIsNone(descriptor_record_to_capability(record))


if __name__ == "__main__":
    unittest.main()
