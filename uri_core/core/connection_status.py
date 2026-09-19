"""Real authorization state for URI's external service connections
(Gmail, Google Drive), reported honestly from actual credential
evidence on disk.

This module exists because the Flutter client previously showed a
hardcoded "Connected" badge for Gmail regardless of whether any OAuth
credential existed (see uri_ui/lib/services/mock_uri_client.dart's
seeded connections) - a UI claim URI could not back with anything
real, which is exactly what the operating policy's anti-masking
principles forbid.

Deliberately NON-INTERACTIVE and read-only. It never calls
GmailService.connect(), never constructs an InstalledAppFlow, and can
never trigger the local-browser OAuth consent screen - a status query
arriving over HTTP must never be able to launch an interactive
sign-in on the server host. It only observes which credential files
exist and whether a stored token still loads, mirroring
capability_registry.py's "report what is really true, degrade to a
safe unknown rather than guessing" discipline.

The three states map exactly onto the client's existing
ConnectionStatus enum (see uri_ui/lib/models/connection.dart):

    connected            - a stored token exists and still loads.
    needs_authorization  - a client secret (credentials.json) exists,
                           but no usable token yet: consent has not
                           been completed on the server host.
    not_connected        - no client secret is configured at all;
                           nothing can be authorized until one is.
"""

import os
from typing import Any, Dict, List, Optional

from uri_core.core.google_auth_common import load_usable_credentials

STATUS_CONNECTED = "connected"
STATUS_NEEDS_AUTHORIZATION = "needs_authorization"
STATUS_NOT_CONNECTED = "not_connected"


def _repo_root() -> str:
    # 2026-09-12 (User directive): an explicit override for where
    # credentials.json/token.json live, for an install where the
    # repository root isn't where the Google Cloud Console download
    # was placed. Checked first; falls back to the repo root exactly
    # as before when unset, so every existing install is unaffected.
    override = os.environ.get("URI_GOOGLE_CREDENTIALS_DIR")
    if override:
        return override
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _token_is_usable(token_path: str, scopes: List[str]) -> bool:
    """True when a stored token file exists AND still loads as
    credentials - refreshing it first if needed. A token that needs a
    network refresh to be usable is still reported as usable here,
    because the refresh itself is non-interactive (a server-to-Google
    token-endpoint call using the stored refresh_token - never a
    browser consent screen) and happens later at real call time
    anyway; a token file that cannot even be parsed, or has no usable
    refresh_token, is not.

    Live UX Repair §10 (grounded-data-path consistency): this
    previously passed allow_refresh=False, contradicting this exact
    docstring - live-reproduced showing the real defect it caused: with
    a genuinely valid but access-token-expired token.json, this
    reported "needs_authorization" (Connections screen) while
    GmailSearchService.authenticate() (allow_refresh=True) refreshed
    successfully and returned a real unread count on Home - two
    surfaces disagreeing about the exact same underlying fact. Never
    raises."""

    return load_usable_credentials(
        token_path=token_path,
        scopes=scopes,
        allow_refresh=True,
    ) is not None


def _google_service_status(
    credentials_path: str, token_path: str, scopes: List[str]
) -> Dict[str, str]:
    """One Google service's real state plus a plain-language detail
    the client can show verbatim. Never raises."""

    if _token_is_usable(token_path, scopes):
        return {
            "status": STATUS_CONNECTED,
            "detail": "Connected",
        }

    if os.path.exists(credentials_path):
        return {
            "status": STATUS_NEEDS_AUTHORIZATION,
            "detail": (
                "Client secret found, but sign-in has not been "
                "completed on the URI server host yet."
            ),
        }

    return {
        "status": STATUS_NOT_CONNECTED,
        "detail": (
            "No Google client secret (credentials.json) is configured "
            "on the URI server host."
        ),
    }


def list_connection_status(
    user_id: Optional[str] = None,
    *,
    service_store: Optional[Any] = None,
    root: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Every external service URI knows how to connect to, with its
    real current authorization state. Read-only and non-interactive;
    safe to call on every client refresh. Never raises - an
    unexpected failure degrades that service to not_connected with an
    honest detail rather than inventing a connected state.

    Per-user mailbox isolation (M32 A1-3): when user_id is provided,
    token_path resolves strictly to that user's own scoped token.json.
    """
    from uri_core.core.google_auth_common import resolve_google_token_path

    repo_root = _repo_root()
    credentials_path = os.path.join(repo_root, "credentials.json")
    token_path = resolve_google_token_path(user_id) if user_id else os.path.join(repo_root, "token.json")

    services = [
        {
            "id": "gmail",
            "name": "Gmail",
            "description": (
                "Read relevant messages and prepare replies for your "
                "review."
            ),
            "token_path": token_path,
            "scopes": [
                "https://www.googleapis.com/auth/gmail.readonly"
            ],
        },
        {
            "id": "drive",
            "name": "Google Drive",
            "description": (
                "Find and reference documents you already have access "
                "to."
            ),
            "token_path": token_path,
            "scopes": [
                "https://www.googleapis.com/auth/drive.readonly"
            ],
        },
    ]

    results = []

    for service in services:

        try:
            state = _google_service_status(
                credentials_path,
                service["token_path"],
                service["scopes"],
            )

        except Exception:
            state = {
                "status": STATUS_NOT_CONNECTED,
                "detail": "Failed to determine service status",
            }

        results.append(
            {
                "id": service["id"],
                "name": service["name"],
                "description": service["description"],
                "status": state["status"],
                "detail": state["detail"],
            }
        )

    if user_id:
        try:
            from uri_core.external.service_store import ConnectedServiceStore
            if service_store is not None:
                ext_store = service_store
            elif root is not None:
                ext_store = ConnectedServiceStore(root=root)
            else:
                ext_store = ConnectedServiceStore()
            for ext_svc in ext_store.list_services(user_id):
                if ext_svc["id"] not in {"gmail", "drive"}:
                    results.append(
                        {
                            "id": ext_svc["id"],
                            "name": ext_svc["name"],
                            "description": ext_svc["description"],
                            "status": ext_svc["status"],
                            "detail": ext_svc["detail"],
                        }
                    )
        except Exception:
            pass

    return results
