"""M33.1: Connected Service descriptor and contracts.

Represents external service connections (OAuth, API-key services like Gmail, GitHub,
Firecrawl, Slack, Notion) with distinct lifecycle: connect, disconnect, token refresh/revocation,
per-user connection state, and service-exposed capabilities.
Deliberately separated from installable Skills packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

STATUS_CONNECTED = "connected"
STATUS_NEEDS_AUTHORIZATION = "needs_authorization"
STATUS_NOT_CONNECTED = "not_connected"
STATUS_ERROR = "error"

AUTH_TYPE_OAUTH = "oauth"
AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_NONE = "none"


@dataclass(frozen=True)
class ConnectedServiceDescriptor:
    """Descriptor for a Connected Service."""

    id: str
    name: str
    description: str
    auth_type: str = AUTH_TYPE_API_KEY
    scopes: Tuple[str, ...] = ()
    capabilities: Tuple[str, ...] = ()
    endpoint: Optional[str] = None
    config_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "auth_type": self.auth_type,
            "scopes": list(self.scopes),
            "capabilities": list(self.capabilities),
            "endpoint": self.endpoint,
            "config_schema": dict(self.config_schema),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConnectedServiceDescriptor":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            auth_type=str(data.get("auth_type", AUTH_TYPE_API_KEY)),
            scopes=tuple(data.get("scopes") or ()),
            capabilities=tuple(data.get("capabilities") or ()),
            endpoint=data.get("endpoint"),
            config_schema=dict(data.get("config_schema") or {}),
            metadata=dict(data.get("metadata") or {}),
        )
