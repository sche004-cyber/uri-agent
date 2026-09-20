"""M33.1: Connected Service store.

Manages user-scoped connection states, credentials, and lifecycle for Connected Services
(e.g. Gmail, GitHub, Firecrawl). Disconnect wipes credentials and marks state not_connected.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from uri_core.core.portable_paths import DEFAULT_USER_STATE_ROOT, user_scoped_path
from uri_core.external.credentials import ExternalCredentialStore
from uri_core.external.service_contract import (
    ConnectedServiceDescriptor,
    STATUS_CONNECTED,
    STATUS_NEEDS_AUTHORIZATION,
    STATUS_NOT_CONNECTED,
    STATUS_ERROR,
)

CONNECTED_SERVICES_FILENAME = "connected_services.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: str, data: Mapping[str, Any]) -> None:
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-svc-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


class ConnectedServiceStore:
    """Per-user store for Connected Services."""

    def __init__(
        self,
        *,
        root: str = DEFAULT_USER_STATE_ROOT,
        credential_store: Optional[ExternalCredentialStore] = None,
    ):
        self.root = root
        self.credential_store = credential_store or ExternalCredentialStore(root=root)
        self._registered_services: Dict[str, ConnectedServiceDescriptor] = {}
        self._register_default_services()

    def _register_default_services(self) -> None:
        self.register_service(
            ConnectedServiceDescriptor(
                id="gmail",
                name="Gmail",
                description="Read relevant messages and prepare replies for review.",
                auth_type="oauth",
                scopes=("https://www.googleapis.com/auth/gmail.readonly",),
                capabilities=("Gmail",),
            )
        )
        self.register_service(
            ConnectedServiceDescriptor(
                id="github",
                name="GitHub",
                description="Access issues, pull requests, and repository metadata.",
                auth_type="api_key",
                scopes=("repo", "read:user"),
                capabilities=("github.issues", "github.prs"),
            )
        )
        self.register_service(
            ConnectedServiceDescriptor(
                id="firecrawl",
                name="Firecrawl",
                description="Crawl websites, extract clean markdown, and parse web documents.",
                auth_type="api_key",
                scopes=("crawl", "scrape"),
                capabilities=("firecrawl.map_site", "firecrawl.crawl_site", "firecrawl.read_document"),
            )
        )

    def register_service(self, descriptor: ConnectedServiceDescriptor) -> None:
        self._registered_services[descriptor.id] = descriptor

    def get_service_descriptor(self, service_id: str) -> Optional[ConnectedServiceDescriptor]:
        return self._registered_services.get(service_id)

    def _path(self, user_id: str) -> str:
        return user_scoped_path(user_id, CONNECTED_SERVICES_FILENAME, root=self.root)

    def _load(self, user_id: str) -> Dict[str, Any]:
        path = self._path(user_id)
        if not os.path.exists(path):
            return {"services": {}}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) and isinstance(data.get("services"), dict) else {"services": {}}
        except (json.JSONDecodeError, OSError):
            return {"services": {}}

    def _save(self, user_id: str, data: Mapping[str, Any]) -> None:
        _atomic_write_json(self._path(user_id), data)

    def state_is_readable(self, user_id: str) -> bool:
        """Whether this user's existing connection document can be mutated.

        A malformed document is not an empty document at a lifecycle mutation
        boundary: callers must fail closed rather than overwrite it.
        """
        path = self._path(user_id)
        if not os.path.exists(path):
            return True
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return False
        return isinstance(data, dict) and isinstance(data.get("services"), dict)

    def connect(
        self,
        user_id: str,
        service_id: str,
        credentials: Mapping[str, Any],
        *,
        scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        descriptor = self.get_service_descriptor(service_id)
        if descriptor is None:
            raise ValueError(f"Unknown service: {service_id}")

        document = self._load(user_id)
        self.credential_store.set_credential(user_id, service_id, credentials)
        effective_scopes = list(scopes) if scopes is not None else list(descriptor.scopes)
        state = {
            "id": service_id,
            "status": STATUS_CONNECTED,
            "detail": "Connected",
            "scopes": effective_scopes,
            "connected_at": _now(),
        }
        document["services"][service_id] = state
        self._save(user_id, document)
        return dict(state)

    def disconnect(self, user_id: str, service_id: str) -> Dict[str, Any]:
        document = self._load(user_id)
        self.credential_store.delete_credential(user_id, service_id)
        state = {
            "id": service_id,
            "status": STATUS_NOT_CONNECTED,
            "detail": "Disconnected",
            "scopes": [],
            "disconnected_at": _now(),
        }
        document["services"][service_id] = state
        self._save(user_id, document)
        return dict(state)

    def get_status(self, user_id: str, service_id: str) -> Dict[str, Any]:
        descriptor = self.get_service_descriptor(service_id)
        name = descriptor.name if descriptor else service_id
        description = descriptor.description if descriptor else ""

        document = self._load(user_id)
        recorded = document.get("services", {}).get(service_id)

        # Built-in Gmail fallback to disk-based check if no recorded state
        if service_id == "gmail" and recorded is None:
            from uri_core.core.connection_status import _google_service_status, _repo_root
            from uri_core.core.google_auth_common import resolve_google_token_path
            root = _repo_root()
            creds = os.path.join(root, "credentials.json")
            token = resolve_google_token_path(user_id) if user_id else os.path.join(root, "token.json")
            g_state = _google_service_status(creds, token, ["https://www.googleapis.com/auth/gmail.readonly"])
            return {
                "id": "gmail",
                "name": name,
                "description": description,
                "status": g_state["status"],
                "detail": g_state["detail"],
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"] if g_state["status"] == STATUS_CONNECTED else [],
            }

        if recorded is None:
            return {
                "id": service_id,
                "name": name,
                "description": description,
                "status": STATUS_NOT_CONNECTED,
                "detail": "Not connected",
                "scopes": [],
            }

        return {
            "id": service_id,
            "name": name,
            "description": description,
            "status": recorded.get("status", STATUS_NOT_CONNECTED),
            "detail": recorded.get("detail", ""),
            "scopes": list(recorded.get("scopes") or []),
        }

    def list_services(self, user_id: str) -> List[Dict[str, Any]]:
        results = []
        for service_id in self._registered_services:
            results.append(self.get_status(user_id, service_id))
        return results
