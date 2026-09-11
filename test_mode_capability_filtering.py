"""M22.8: modes can only narrow registered, granted capabilities."""

from uri_core.config.modes import DEFAULT_MODE, DEFAULT_MODES, load_modes
from uri_core.core.capability_registry import CapabilityRegistry
from uri_core.core.capability_resolver import CapabilityGrantsStore, CapabilityResolver
from uri_core.core.principal_context import PrincipalContext


def test_diagnostic_mode_narrows_a_broad_grant(tmp_path):
    registry = CapabilityRegistry()
    registered = {item.id for item in registry.list_capabilities()}
    store = CapabilityGrantsStore(str(tmp_path / "grants.json"))
    store.set_grants("broad-user", sorted(registered), registered)

    resolved = CapabilityResolver.resolve(
        PrincipalContext("broad-user", "USER", None, mode="diagnostic"), registry, store
    )
    resolved_ids = {item.id for item in resolved}
    assert resolved_ids <= registered
    assert resolved_ids <= set(DEFAULT_MODES["diagnostic"])
    assert "draft_institutional_note" not in resolved_ids
    assert "gmail_create_draft" not in resolved_ids
    assert not CapabilityResolver.is_allowed(
        "draft_institutional_note",
        PrincipalContext("broad-user", "USER", None, mode="diagnostic"), registry, store,
    )


def test_office_default_preserves_registry_and_grants_intersection(tmp_path):
    registry = CapabilityRegistry()
    registered = {item.id for item in registry.list_capabilities()}
    granted = set(sorted(registered)[:3])
    store = CapabilityGrantsStore(str(tmp_path / "grants.json"))
    store.set_grants("office-user", sorted(granted), registered)

    resolved = CapabilityResolver.resolve(
        PrincipalContext("office-user", "USER", None), registry, store
    )
    assert DEFAULT_MODE == "office"
    assert {item.id for item in resolved} == granted


def test_diagnostic_packaged_allowlist_has_no_drafting_or_execution_capabilities():
    registry = CapabilityRegistry()
    registered = {item.id for item in registry.list_capabilities()}
    diagnostic = set(load_modes()["diagnostic"])
    assert diagnostic <= registered
    assert not diagnostic & {
        "draft_institutional_note", "draft_institutional_order", "generate_document",
        "gmail_create_draft", "drive_upload",
    }
