"""Shared, non-interactive Google OAuth token loading helpers."""

import os
import tempfile
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def _repo_root() -> str:
    """Resolve the shared Google credentials directory without prompting."""
    override = os.environ.get("URI_GOOGLE_CREDENTIALS_DIR")
    if override:
        return override
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def resolve_google_token_path(user_id: Optional[str] = None) -> str:
    """Resolve the Google OAuth token.json path.

    If a user_id is provided, resolves strictly to that user's scoped
    directory (via portable_paths.user_scoped_path) so each user's
    mailbox token is completely isolated.
    If user_id is None, falls back to the install-wide token.json at
    _repo_root() for backwards-compatibility with ambient test fixtures.
    """
    if user_id:
        from uri_core.core.portable_paths import user_scoped_path

        return user_scoped_path(user_id, "token.json")
    return os.path.join(_repo_root(), "token.json")


def _persist_refreshed_credentials(creds: Credentials, resolved_path: str) -> None:
    """Write a just-refreshed credential back to the exact path it was
    loaded from (already resolved to that one user's own scoped file by
    the caller - this never widens or changes which file is written, so
    per-user isolation is preserved automatically). Best-effort only: a
    write failure must never invalidate the refresh that already
    succeeded in memory, so this never raises out to the caller.

    M32 D1: without this, the on-disk token keeps its stale, already-
    expired access token forever, so every subsequent load re-refreshes
    from Google again - confirmed by measurement
    (docs/plans/M32_POST_BATCH_C_LATENCY_ARCHITECTURE_PLAN.md §2.2) to
    cost a real network round trip on literally every call. Persisting
    the refreshed token lets a real Google access token (~1 hour
    lifetime) actually be reused for its real lifetime."""
    folder = os.path.dirname(resolved_path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=folder or None, delete=False
        ) as stream:
            temporary = stream.name
            stream.write(creds.to_json())
        os.replace(temporary, resolved_path)
        temporary = None
    except Exception:
        pass
    finally:
        if temporary is not None and os.path.exists(temporary):
            try:
                os.unlink(temporary)
            except Exception:
                pass


def load_usable_credentials(
    token_path: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    allow_refresh: bool = True,
    user_id: Optional[str] = None,
) -> Optional[Credentials]:
    """Load usable stored credentials, optionally refreshing non-interactively.

    This function never initiates OAuth consent and never exposes token or
    exception data.  Any parse, refresh, or validity failure is represented by
    ``None``.
    """
    try:
        resolved_path = token_path or resolve_google_token_path(user_id)
        if not os.path.exists(resolved_path):
            return None

        creds = Credentials.from_authorized_user_file(resolved_path, scopes)
        if creds.valid:
            return creds

        if allow_refresh and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if creds.valid:
                # M32 D1: persist so the NEXT load sees a still-valid
                # token instead of refreshing again - see
                # _persist_refreshed_credentials' own docstring.
                _persist_refreshed_credentials(creds, resolved_path)
                return creds

    except Exception:
        pass

    return None
