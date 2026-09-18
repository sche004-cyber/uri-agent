"""test_m33_p1_permission_seam.py — M33 P1 (permission-seam
generalization), the frozen blueprint's §3.

Fixes F2: `MultiActionDispatch._action_permitted` used to treat the mere
PRESENCE of a `permission_checker`/`_explicit_permissions` as
unconditional permission, bypassing per-action authorization entirely.
These tests target the fixed seam directly, with real collaborators
(real `MultiActionDispatch`, real `MultiActionExecutor`, real
`GmailCapability` wrapping the established `FakeGmailService` fixture) -
never mocking the seam under test itself.
"""
from __future__ import annotations

import unittest

from uri_core.capabilities import (
    Action,
    ActionSchema,
    Capability,
    MultiActionCapabilityRegistry,
    MultiActionExecutor,
)
from uri_core.capabilities.gmail import GmailCapability
from uri_core.core.multi_action_dispatch import MultiActionDispatch
from test_multi_action_capabilities import FakeGmailService, gmail_registry


def _fixture_capability(*, base_scope="fixture.base", extra_scope="fixture.special"):
    """A second, non-Gmail capability with no legacy alias entry at all -
    proves P1's generalization and its deny-by-default for unmapped
    capability ids, independent of anything Gmail-specific."""

    def _plain_handler(**_kwargs):
        return {"status": "success"}

    plain_action = Action(
        name="plain_action",
        description="No extra permission required beyond the capability grant.",
        parameters=ActionSchema(),
        handler=_plain_handler,
    )
    guarded_action = Action(
        name="guarded_action",
        description="Requires an additional scope beyond the capability grant.",
        parameters=ActionSchema(),
        handler=_plain_handler,
        permissions=(extra_scope,),
    )
    return Capability(
        name="Fixture",
        description="A synthetic non-Gmail capability for P1 permission tests.",
        category="test",
        permissions=[base_scope],
        actions={"plain_action": plain_action, "guarded_action": guarded_action},
    )


class ActionPermittedNoSilentBypassTests(unittest.TestCase):
    """The named F2 regression: a checker's presence must never itself
    grant access, and its real False/error answer must be honored."""

    def test_checker_present_and_returning_false_denies(self):
        dispatch = MultiActionDispatch(gmail_registry(), permission_checker=lambda *_: False)
        result = dispatch.dispatch_explicit(
            "Gmail", "search_messages", {"query": "x"},
            session_id="s1", user_text="search",
        )
        self.assertEqual(result["execution"]["status"], "permission_denied")

    def test_checker_present_and_returning_true_allows(self):
        dispatch = MultiActionDispatch(gmail_registry(), permission_checker=lambda *_: True)
        result = dispatch.dispatch_explicit(
            "Gmail", "search_messages", {"query": "insurance"},
            session_id="s1", user_text="search for insurance",
        )
        self.assertEqual(result["execution"]["status"], "success")

    def test_explicit_permissions_empty_set_denies_not_silently_allows(self):
        """Presence of `_explicit_permissions` (even an empty set) used
        to short-circuit to True. It must now genuinely narrow: an
        empty granted set denies every action."""
        dispatch = MultiActionDispatch(gmail_registry(), granted_permissions=set())
        result = dispatch.dispatch_explicit(
            "Gmail", "search_messages", {"query": "x"},
            session_id="s1", user_text="search",
        )
        self.assertEqual(result["execution"]["status"], "permission_denied")

    def test_explicit_permissions_matching_scope_allows(self):
        dispatch = MultiActionDispatch(gmail_registry(), granted_permissions={"gmail.readonly"})
        result = dispatch.dispatch_explicit(
            "Gmail", "search_messages", {"query": "insurance"},
            session_id="s1", user_text="search for insurance",
        )
        self.assertEqual(result["execution"]["status"], "success")

    def test_unmapped_capability_action_denies_by_default_even_with_checker(self):
        """Requirement #4: absence from the legacy alias map denies -
        additive denial for a new/unmapped id, regardless of whether a
        checker happens to be configured for other capabilities."""
        registry = MultiActionCapabilityRegistry([GmailCapability(), _fixture_capability()])
        dispatch = MultiActionDispatch(registry, permission_checker=lambda *_: True)
        result = dispatch.dispatch_explicit(
            "Fixture", "plain_action", {},
            session_id="s1", user_text="do the fixture thing",
        )
        self.assertEqual(result["execution"]["status"], "permission_denied")


class PermissionCheckerErrorHandlingTests(unittest.TestCase):
    def test_checker_raising_is_treated_as_denied_not_a_crash(self):
        def _raising_checker(*_args):
            raise RuntimeError("downstream grants service unavailable")

        dispatch = MultiActionDispatch(gmail_registry(), permission_checker=_raising_checker)
        result = dispatch.dispatch_explicit(
            "Gmail", "search_messages", {"query": "x"},
            session_id="s1", user_text="search",
        )
        self.assertEqual(result["execution"]["status"], "permission_denied")

    def test_checker_raising_never_executes_the_action(self):
        service = FakeGmailService()
        registry = MultiActionCapabilityRegistry([GmailCapability(service)])

        def _raising_checker(*_args):
            raise RuntimeError("boom")

        dispatch = MultiActionDispatch(registry, permission_checker=_raising_checker)
        dispatch.dispatch_explicit(
            "Gmail", "create_draft", {"body": "hi"},
            session_id="s1", user_text="draft a reply",
        )
        self.assertEqual(service.drafts, [])


class MultiActionMixedPermissionTests(unittest.TestCase):
    """A chained dispatch spanning a permitted and a denied step must
    deny the WHOLE chain before executing any step - never partial
    execution, per `dispatch_chain_explicit`'s existing pre-loop check
    now actually enforcing real authorization."""

    def test_chain_denies_entirely_when_any_step_is_unauthorized(self):
        service = FakeGmailService()
        registry = MultiActionCapabilityRegistry([GmailCapability(service), _fixture_capability()])
        dispatch = MultiActionDispatch(registry, permission_checker=lambda cap, *_: cap == "gmail_search")

        steps = [
            {"capability": "Gmail", "action": "search_messages", "inputs": {"query": "insurance"}},
            {"capability": "Fixture", "action": "plain_action", "inputs": {}},
        ]
        result = dispatch.dispatch_chain_explicit(steps, session_id="s1")
        self.assertEqual(result["execution"]["status"], "permission_denied")
        # The chain must have been rejected before the first (permitted)
        # step ever ran - no partial execution.
        self.assertEqual(service.drafts, [])

    def test_chain_allows_when_every_step_is_authorized(self):
        service = FakeGmailService()
        registry = MultiActionCapabilityRegistry([GmailCapability(service)])
        dispatch = MultiActionDispatch(registry, permission_checker=lambda *_: True)
        steps = [
            {"capability": "Gmail", "action": "search_messages", "inputs": {"query": "insurance"}},
        ]
        result = dispatch.dispatch_chain_explicit(steps, session_id="s1")
        self.assertNotEqual(result["execution"]["status"], "permission_denied")


class ActionLevelPermissionGateInExecutorTests(unittest.TestCase):
    """Requirement #3: `Action.permissions` + the new executor gate
    between the capability-level check and schema validation."""

    def test_action_level_scope_missing_denies_even_when_capability_level_granted(self):
        registry = MultiActionCapabilityRegistry([_fixture_capability()])
        executor = MultiActionExecutor(registry, granted_permissions={"fixture.base"})
        result = executor.execute("Fixture", "guarded_action", {})
        self.assertEqual(result["status"], "permission_denied")
        self.assertIn("fixture.special", result.get("missing_action_permissions", []))

    def test_action_level_scope_present_allows(self):
        registry = MultiActionCapabilityRegistry([_fixture_capability()])
        executor = MultiActionExecutor(
            registry, granted_permissions={"fixture.base", "fixture.special"}
        )
        result = executor.execute("Fixture", "guarded_action", {})
        self.assertEqual(result["status"], "success")

    def test_action_with_no_declared_permissions_is_unaffected_by_new_gate(self):
        registry = MultiActionCapabilityRegistry([_fixture_capability()])
        executor = MultiActionExecutor(registry, granted_permissions={"fixture.base"})
        result = executor.execute("Fixture", "plain_action", {})
        self.assertEqual(result["status"], "success")

    def test_existing_gmail_actions_declare_no_action_level_permissions_yet(self):
        """P1 adds the primitive without retrofitting Gmail's own
        actions onto it - Gmail's authorization stays entirely on the
        pre-existing capability-level + legacy-alias mechanism."""
        registry = gmail_registry()
        gmail = registry.get_capability("Gmail")
        for action in gmail.list_actions():
            self.assertEqual(action.permissions, ())


class GeneralizedGrantedPermissionsTests(unittest.TestCase):
    """Requirement #2: `_granted_permissions` derives scopes generically
    per registered capability, with Gmail's own resulting set unchanged."""

    def test_gmail_granted_set_unchanged_when_allowed(self):
        dispatch = MultiActionDispatch(gmail_registry(), permission_checker=lambda *_: True)
        self.assertEqual(dispatch._granted_permissions(None), {"gmail.readonly"})

    def test_gmail_granted_set_empty_when_denied(self):
        dispatch = MultiActionDispatch(gmail_registry(), permission_checker=lambda *_: False)
        self.assertEqual(dispatch._granted_permissions(None), set())

    def test_unmapped_capability_contributes_nothing_even_if_checker_allows_everything(self):
        """`Fixture` has no `_CAPABILITY_GRANT_ALIAS` entry - P1
        deliberately does not widen recognition of new capability ids;
        that is Batch B's own permission-binding work."""
        registry = MultiActionCapabilityRegistry([GmailCapability(), _fixture_capability()])
        dispatch = MultiActionDispatch(registry, permission_checker=lambda *_: True)
        granted = dispatch._granted_permissions(None)
        self.assertEqual(granted, {"gmail.readonly"})
        self.assertNotIn("fixture.base", granted)


if __name__ == "__main__":
    unittest.main()
