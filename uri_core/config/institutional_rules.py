"""Configurable institutional drafting conventions (M17).

The single source of the *institution-specific* facts and conventions
that a drafted document must observe - the institution's name, its
issuing offices and signatory roles, its reference-number format, and
the language register it uses. Before M17 these were string literals
hardcoded inside the drafting tools (a frozen "NATIONAL INSTITUTE OF
TECHNOLOGY SIKKIM" banner, a fixed "NITS/2026/Admin/Order/___"
reference, a baked-in signature block), which is exactly what made the
old tools a single locked template. Here they are *data*: a default
dictionary that a deployment can override wholesale via a JSON file,
so pointing URI at a different institution is a config change, never a
code change.

Nothing in this module composes a document or decides its structure -
it only supplies the conventions the Brain is *given* and asked to
honour. The Brain still decides how (and whether) to apply each one
for a given request and purpose; a convention here is guidance and
constraint, never a template.
"""

import json
import os
from typing import Any, Dict


# The default institution. Deliberately expressed as plain data - names,
# roles, formats, and register - never as pre-rendered document text.
# A deployment for a different institution overrides this by placing a
# JSON object with the same shape at INSTITUTIONAL_RULES_PATH (or by
# passing an explicit dict to the drafting layer); any keys it omits
# fall back to these defaults, so a partial override is safe.
#
# 2026-09-12 (User directive): this previously defaulted to one real
# institution's actual name/offices/roles (National Institute of
# Technology Sikkim), baked in from this project's own early
# development/testing - meaning every fresh install silently assumed
# that identity before the Brain had ever been told who the user
# actually works for. Genuinely generic now: null/placeholder values
# the Brain must either fill from real, already-established context
# (the user's own confirmed profile/memory - see recall_memory,
# remember_fact) or ask for outright, never assume from this file.
DEFAULT_INSTITUTIONAL_RULES: Dict[str, Any] = {
    "institution_name": None,
    "short_name": None,
    "issuing_offices": [],
    "signatory_roles": [],
    # A *format*, not a frozen literal - {year} and {serial} are filled
    # by the Brain from real, current context (or left as an explicit
    # blank placeholder for a human to complete), never invented. The
    # old tool hardcoded a specific year and a literal "___" serial.
    "reference_number_format": "{institution_short_name}/{year}/Admin/{doc_kind}/{serial}",
    "language_register": (
        "formal Indian administrative English, concise and precise"
    ),
    # Conventions the Brain should observe, expressed as rules the model
    # reads - never as the finished heading/section text itself.
    "note_conventions": {
        "salutation": None,
        "closing_convention": (
            "submitted for the kind consideration and orders of the "
            "competent authority"
        ),
        "reference_line": "optional, included when a file/reference exists",
    },
    "order_conventions": {
        "heading_convention": (
            "a centred office-order heading naming the issuing office"
        ),
        "reference_line": (
            "a reference number line using reference_number_format"
        ),
        "authority_line": (
            "state that the order issues with the approval of the "
            "competent authority"
        ),
        "signature_block": (
            "close with the signatory role from signatory_roles and the "
            "institution short_name"
        ),
    },
    # Formatting expectations (font/header/footer) are stated as
    # requirements the Brain honours in the produced text/markdown, not
    # applied by a renderer here. Kept intentionally light and
    # overridable.
    "formatting": {
        "header": "institution name and issuing office, where applicable",
        "footer": None,
        "font_convention": "a standard serif administrative font",
        "numbering": (
            "number distinct operative clauses where a document has more "
            "than one, otherwise flowing paragraphs"
        ),
    },
}


# A deployment override, if present, is read from here. Absent by
# default - the packaged defaults above are used - so nothing NIT-
# specific is required to exist on disk for URI to run.
INSTITUTIONAL_RULES_PATH = os.path.join(
    "uri_workspace", "institutional_rules.json"
)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Override wins per key; nested dicts merge rather than replace, so
    a partial override (e.g. only a new institution_name) keeps every
    other default convention intact."""

    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_institutional_rules(path: str = INSTITUTIONAL_RULES_PATH) -> Dict[str, Any]:
    """The active institutional conventions: the packaged defaults,
    deep-merged with a deployment override JSON if one exists at [path].
    Never raises - a missing or malformed override degrades to the
    defaults rather than breaking drafting, mirroring the same
    degrade-to-safe discipline load_policy()/load_soul() already
    follow."""

    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            override = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULT_INSTITUTIONAL_RULES)

    if not isinstance(override, dict):
        return dict(DEFAULT_INSTITUTIONAL_RULES)

    return _deep_merge(DEFAULT_INSTITUTIONAL_RULES, override)
