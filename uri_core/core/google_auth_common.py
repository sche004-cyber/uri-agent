"""Shared, non-interactive Google OAuth token loading helpers."""

import os
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def _repo_root() -> str:
    """Resolve the shared Google credentials directory without prompting."""
    override = os.environ.get("URI_GOOGLE_CREDENTIALS_DIR")
    if override:
        return override
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def load_usable_credentials(
    token_path: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    allow_refresh: bool = True,
) -> Optional[Credentials]:
    """Load usable stored credentials, optionally refreshing non-interactively.

    This function never initiates OAuth consent and never exposes token or
    exception data.  Any parse, refresh, or validity failure is represented by
    ``None``.
    """
    try:
        resolved_path = token_path or os.path.join(_repo_root(), "token.json")
        if not os.path.exists(resolved_path):
            return None

        creds = Credentials.from_authorized_user_file(resolved_path, scopes)
        if creds.valid:
            return creds

        if allow_refresh and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if creds.valid:
                return creds

    except Exception:
        pass

    return None
