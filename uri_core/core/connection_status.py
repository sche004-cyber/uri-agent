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
from typing import Any, Dict, List

STATUS_CONNECTED = "connected"
STATUS_NEEDS_AUTHORIZATION = "needs_authorization"
STATUS_NOT_CONNECTED = "not_connected"


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _token_is_usable(token_path: str, scopes: List[str]) -> bool:
    """True only when a stored token file exists AND still loads as
    credentials. Never refreshes, never prompts - a token that needs a
    network refresh to be usable is still reported as usable here,
    because the refresh itself is non-interactive and happens later at
    real call time; a token file that cannot even be parsed is not.
    Never raises."""

    if not os.path.exists(token_path):
        return False

    try:
        from google.oauth2.credentials import Credentials

        Credentials.from_authorized_user_file(token_path, scopes)
        return True

    except Exception:
        return False


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


def list_connection_status() -> List[Dict[str, Any]]:
    """Every external service URI knows how to connect to, with its
    real current authorization state. Read-only and non-interactive;
    safe to call on every client refresh. Never raises - an
    unexpected failure degrades that service to not_connected with an
    honest detail rather than inventing a connected state."""

    root = _repo_root()
    credentials_path = os.path.join(root, "credentials.json")

    services = [
        {
            "id": "gmail",
            "name": "Gmail",
            "description": (
                "Read relevant messages and prepare replies for your "
                "review."
            ),
            "token_path": os.path.join(root, "token.json"),
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
            "token_path": os.path.join(root, "token.json"),
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
                "detail": "Connection state could not be determined.",
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

    return results
