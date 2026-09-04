import re


"""
Small, dependency-free credential-pattern guard, factored out so
new runtime infrastructure (currently: evidence_fact_integrity.py)
doesn't have to duplicate it. Deliberately not wired into
audit_trail.py in this change - that module is left untouched.
"""


MAX_METADATA_VALUE_LENGTH = 500

_SECRET_KEY_MARKERS = (
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "authorization",
    "auth_header",
    "access_token",
    "refresh_token",
    "credential",
    "private_key",
)

_SECRET_VALUE_PATTERN = re.compile(
    r"^(gsk_|sk-|AIza|AQ\.|Bearer\s)",
    re.IGNORECASE,
)


def looks_like_credential_key(key: str) -> bool:

    lowered = str(key).lower()

    return any(marker in lowered for marker in _SECRET_KEY_MARKERS)


def looks_like_credential_value(value: str) -> bool:

    return bool(_SECRET_VALUE_PATTERN.match(value.strip()))
