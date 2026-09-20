"""M33.1 Batch 4 - generic natural-language/UI lifecycle seam.

A model or UI may PROPOSE a lifecycle intent (install/enable/disable/update/
remove a Skill, or connect/disconnect a Connected Service) but can never
invent an id, credential, registration, grant, or success. This module
resolves the intent against a small, developer-maintained catalog of already
-reviewed Skills/Services - never a model-supplied package name, URL, argv,
or executable - and delegates entirely to the exact generic lifecycle
functions Batches 1-3 already proved (runtime_lifecycle.py, the per-package
install/update/remove modules, and ConnectedServiceStore). It returns only a
sanitized projection of the real resulting state - never a fabricated
success, and never a raw internal/exception detail.

The live `/ask` seam binds this function to the already-authenticated request
context without passing that context into canonical execution.  See the M33.1
Batch 4 closure record for the deliberately narrow server-side wiring.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

from uri_core.external import runtime_lifecycle
from uri_core.external.descriptors.strip_json_comments import (
    DESCRIPTOR_ID as STRIP_JSON_COMMENTS_DESCRIPTOR_ID,
    V3_REVISION as STRIP_JSON_COMMENTS_LATEST_REVISION,
)
from uri_core.external.descriptors.yt_dlp import (
    DESCRIPTOR_ID as YT_DLP_DESCRIPTOR_ID,
    PINNED_YT_DLP_VERSION,
    yt_dlp_descriptor,
)
from uri_core.external.packages import strip_json_comments as strip_json_comments_package

SKILL_OPERATIONS = frozenset({"install", "enable", "disable", "update", "remove"})
SERVICE_OPERATIONS = frozenset({"connect", "disconnect"})

_LIFECYCLE_STATE_FIELDS = (
    "presence", "qualification", "configuration", "authentication",
    "health", "enabled", "update_available",
)
# Connection detail/scopes may eventually contain provider-derived or caller-
# supplied text.  A lifecycle response needs only the fixed service id and
# state, so never project those free-form values across this boundary.
_CONNECTION_STATE_FIELDS = ("id", "status")


def _install_yt_dlp(context: Any, user_id: str, **_params: Any) -> Any:
    return runtime_lifecycle.register_and_refresh(
        context, user_id, yt_dlp_descriptor(), source_revision=PINNED_YT_DLP_VERSION,
    )


# Developer-authored, code-reviewed catalog of installable Skills. A target
# not listed here can never be installed/updated/removed through this seam
# regardless of what a model or user names - this is the same "developer-
# pinned, never runtime-constructed" boundary Batches 2/3 already require of
# every individual descriptor, applied here to the catalog of targets a
# lifecycle intent may even name.
_SKILL_CATALOG: Dict[str, Dict[str, Any]] = {
    "yt_dlp": {
        "descriptor_id": YT_DLP_DESCRIPTOR_ID,
        "install": _install_yt_dlp,
    },
    "strip_json_comments": {
        "descriptor_id": STRIP_JSON_COMMENTS_DESCRIPTOR_ID,
        "install": lambda context, user_id, **params: strip_json_comments_package.install_and_register(
            context, user_id, revision=params.get("revision", STRIP_JSON_COMMENTS_LATEST_REVISION),
        ),
        "update": lambda context, user_id, **params: strip_json_comments_package.update_and_refresh(
            context, user_id, revision=params.get("revision", STRIP_JSON_COMMENTS_LATEST_REVISION),
        ),
        "remove": lambda context, user_id, **_params: strip_json_comments_package.remove_and_refresh(
            context, user_id,
        ),
    },
}


def _result(status: str, operation: str, target_id: str, **extra: Any) -> Dict[str, Any]:
    return {"status": status, "operation": operation, "target_id": target_id, **extra}


def _sanitize_lifecycle(lifecycle: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(lifecycle, Mapping):
        return {}
    return {key: lifecycle[key] for key in _LIFECYCLE_STATE_FIELDS if key in lifecycle}


def _sanitize_connection(state: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(state, Mapping):
        return {}
    return {key: state[key] for key in _CONNECTION_STATE_FIELDS if key in state}


def _from_lifecycle(operation: str, target_id: str, lifecycle: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if lifecycle is None:
        return _result("not_installed", operation, target_id)
    return _result("success", operation, target_id, state=_sanitize_lifecycle(lifecycle))


def _from_registration(operation: str, target_id: str, result: Any) -> Dict[str, Any]:
    if not getattr(result, "ok", False):
        return _result("rejected", operation, target_id, reasons=list(getattr(result, "reasons", None) or []))
    return _result("success", operation, target_id, state=_sanitize_lifecycle(getattr(result, "lifecycle", None)))


def _execute_skill_operation(
    context: Any, user_id: str, *, operation: str, target_id: str, params: Mapping[str, Any],
) -> Dict[str, Any]:
    catalog_entry = _SKILL_CATALOG.get(target_id)
    if catalog_entry is None:
        return _result("unknown_target", operation, target_id)
    descriptor_id = catalog_entry["descriptor_id"]

    if operation == "enable":
        # Configuration is a precondition `enable()` itself enforces (see
        # lifecycle.py); it carries no external credential/input for either
        # catalog entry, so this seam satisfies it the same way Batches 1-3's
        # own install flows already do, rather than exposing it as a
        # separate intent operation the caller must remember to name first.
        if context.external_capability_store.get(user_id, descriptor_id) is not None:
            runtime_lifecycle.configure_and_refresh(context, user_id, descriptor_id)
        return _from_lifecycle(operation, target_id, runtime_lifecycle.enable_and_refresh(context, user_id, descriptor_id))
    if operation == "disable":
        return _from_lifecycle(operation, target_id, runtime_lifecycle.disable_and_refresh(context, user_id, descriptor_id))

    handler = catalog_entry.get(operation)
    if handler is None:
        return _result("unsupported_operation", operation, target_id)

    if operation == "remove":
        removed = handler(context, user_id, **params)
        return _result("success" if removed else "not_installed", operation, target_id)

    # install / update
    try:
        result = handler(context, user_id, **params)
    except Exception:  # noqa: BLE001 - never leak a raw exception to the caller
        return _result("unavailable", operation, target_id)
    return _from_registration(operation, target_id, result)


def _execute_service_operation(
    context: Any, user_id: str, *, operation: str, target_id: str, params: Mapping[str, Any],
) -> Dict[str, Any]:
    service_store = getattr(context, "connected_service_store", None)
    if service_store is None or service_store.get_service_descriptor(target_id) is None:
        return _result("unknown_target", operation, target_id)

    if operation == "disconnect":
        state = service_store.disconnect(user_id, target_id)
        return _result("success", operation, target_id, state=_sanitize_connection(state))

    # connect: credentials must already be supplied by the caller (a real
    # OAuth/API-key collection flow elsewhere) - this seam never invents,
    # requests, or guesses one.
    credentials = params.get("credentials")
    if not isinstance(credentials, Mapping) or not credentials:
        return _result("credentials_required", operation, target_id)
    scopes = params.get("scopes")
    state = service_store.connect(user_id, target_id, credentials, scopes=scopes)
    return _result("success", operation, target_id, state=_sanitize_connection(state))


def execute_lifecycle_intent(
    context: Any,
    user_id: str,
    *,
    operation: str,
    target_id: str,
    principal: Any = None,
    **params: Any,
) -> Dict[str, Any]:
    """Resolve and run one proposed lifecycle intent against real state.

    ``operation``/``target_id`` may come from a model's proposal or a UI
    action, but both are only ever used as lookup keys into this module's
    own fixed catalog and the caller's own already-authenticated
    ``user_id`` - never as a package name, path, executable, or argv, and
    never as a stand-in for an approval/permission/isolation check any
    other lifecycle entry point already enforces (this seam performs no
    mutation any of Batches 1-3's own functions would not already
    perform for the same authenticated ``context``/``user_id``).
    """
    if not isinstance(operation, str) or not operation:
        return _result("invalid_intent", "unknown", str(target_id) if target_id else "unknown")
    if not isinstance(target_id, str) or not target_id:
        return _result("invalid_intent", operation, "unknown")
    if operation in SKILL_OPERATIONS:
        store = getattr(context, "external_capability_store", None)
        if store is None or not store.state_is_readable(user_id):
            return _result("unavailable", operation, target_id)
        try:
            return _execute_skill_operation(context, user_id, operation=operation, target_id=target_id, params=params)
        except Exception:  # noqa: BLE001 - state/IO failures are unavailable, never caller-visible
            return _result("unavailable", operation, target_id)
    if operation in SERVICE_OPERATIONS:
        store = getattr(context, "connected_service_store", None)
        if store is None or not store.state_is_readable(user_id):
            return _result("unavailable", operation, target_id)
        try:
            return _execute_service_operation(context, user_id, operation=operation, target_id=target_id, params=params)
        except Exception:  # noqa: BLE001 - state/IO failures are unavailable, never caller-visible
            return _result("unavailable", operation, target_id)
    return _result("unsupported_operation", operation, target_id)


def known_skill_targets() -> Dict[str, Dict[str, Any]]:
    """Read-only, descriptive listing of what this seam can install/manage.

    Never authoritative by itself - matches Graphify's own "derived, never
    authoritative" discipline. Real state always comes from a live
    execute_lifecycle_intent call, not from this catalog.
    """
    return {
        key: {"descriptor_id": entry["descriptor_id"], "operations": sorted(
            {"enable", "disable"} | {op for op in ("install", "update", "remove") if op in entry}
        )}
        for key, entry in _SKILL_CATALOG.items()
    }
