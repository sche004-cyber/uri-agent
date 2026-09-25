"""Dependency-light YAML-subset reader for docs/governance/URI_STATE.yaml.

This is not a general YAML parser. It supports exactly the subset of YAML
syntax this repository's governance state file uses: block mappings, block
sequences of mappings or scalars, quoted/unquoted/boolean/null scalars,
empty flow collections (`[]`, `{}`), folded block scalars (`>`), comments,
and blank lines. It exists so the deterministic state validator has no
third-party dependency (no PyYAML is installed in this repository's
environment as of this writing) and no network dependency.

FAIL-CLOSED CONTRACT (repaired 2026-09-25, after an independent audit found
this parser fail-open on several inputs): anything this parser cannot
represent exactly and unambiguously raises `UriStateYamlError` rather than
silently degrading it to a different, wrong value. Specifically:
  - a duplicate key at the same mapping level is an error, not a silent
    overwrite;
  - unconsumed trailing content after the top-level document is an error,
    not silently ignored;
  - a malformed quoted string (unterminated or containing a stray quote) is
    an error, not silently treated as an unquoted scalar;
  - unsupported flow-collection syntax (anything but the empty `[]`/`{}`)
    is an error, not silently treated as a literal string.

If URI_STATE.yaml's authors ever need real YAML features beyond this
subset (anchors, non-empty flow collections, multi-document streams, etc.),
replace this module with a PyYAML-backed implementation rather than
extending this parser piecemeal.
"""

from __future__ import annotations

import re
from typing import Any


class UriStateYamlError(ValueError):
    """Raised when the input is not valid YAML-subset for this parser."""


_QUOTED_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
_LIST_ITEM_RE = re.compile(r"^-\s?(.*)$")
_KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_.\-]+):\s?(.*)$")


def _strip_comment(line: str) -> str:
    # Only strip a '#' that is not inside a quoted string.
    if "#" in line:
        in_quote = False
        for idx, ch in enumerate(line):
            if ch == '"':
                in_quote = not in_quote
            elif ch == "#" and not in_quote:
                return line[:idx]
    return line


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw == "":
        return None
    if raw in ("null", "~"):
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    if raw.startswith("[") or raw.startswith("{"):
        raise UriStateYamlError(
            f"Unsupported flow-collection syntax (only empty [] / {{}} are "
            f"supported by this restricted parser): {raw!r}"
        )
    if raw.startswith('"'):
        match = _QUOTED_RE.match(raw)
        if not match:
            raise UriStateYamlError(f"Malformed quoted scalar: {raw!r}")
        return match.group(1).replace('\\"', '"').replace("\\\\", "\\")
    if '"' in raw:
        raise UriStateYamlError(f"Stray unescaped quote in unquoted scalar: {raw!r}")
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if re.fullmatch(r"-?\d+\.\d+", raw):
        return float(raw)
    return raw


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _set_unique(mapping: dict, key: str, value: Any, context: str) -> None:
    if key in mapping:
        raise UriStateYamlError(
            f"Duplicate key '{key}' at the same mapping level ({context}); "
            f"this parser fails closed on duplicate keys rather than "
            f"silently overwriting the first value."
        )
    mapping[key] = value


def parse_uri_state_yaml(text: str) -> dict:
    """Parse the restricted YAML subset used by URI_STATE.yaml.

    Raises UriStateYamlError on anything outside the supported subset,
    including duplicate keys, unconsumed trailing content, malformed
    quoted strings, and unsupported flow-collection syntax.
    """

    raw_lines = text.split("\n")
    lines: list[tuple[int, str]] = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        stripped_for_comment = _strip_comment(line)
        if stripped_for_comment.strip() == "":
            i += 1
            continue
        indent = _indent_of(stripped_for_comment)
        content = stripped_for_comment[indent:].rstrip()
        # Folded block scalar: consume all more-indented following lines.
        if content.endswith(">") or re.search(r":\s*>\s*$", content):
            i += 1
            block_words: list[str] = []
            while i < len(raw_lines):
                nxt = raw_lines[i]
                if nxt.strip() == "":
                    i += 1
                    continue
                nxt_indent = _indent_of(nxt)
                if nxt_indent <= indent:
                    break
                block_words.append(nxt.strip())
                i += 1
            key_part = content.rsplit(":", 1)[0]
            lines.append((indent, f"{key_part}: \"{' '.join(block_words)}\""))
            continue
        lines.append((indent, content))
        i += 1

    pos = 0

    def parse_block(min_indent: int) -> Any:
        nonlocal pos
        if pos >= len(lines):
            return None
        indent, content = lines[pos]
        if indent < min_indent:
            return None

        if content.startswith("-"):
            return parse_sequence(indent)
        return parse_mapping(indent)

    def parse_sequence(seq_indent: int) -> list:
        nonlocal pos
        result: list = []
        while pos < len(lines):
            indent, content = lines[pos]
            if indent != seq_indent or not content.startswith("-"):
                break
            m = _LIST_ITEM_RE.match(content)
            item_body = m.group(1) if m else ""
            pos += 1
            if item_body == "":
                value = parse_block(seq_indent + 1)
                result.append(value)
                continue
            kv = _KEY_VALUE_RE.match(item_body)
            if kv:
                key, rest = kv.group(1), kv.group(2)
                entry: dict = {}
                if rest.strip() == "":
                    entry[key] = parse_block(seq_indent + 1)
                else:
                    entry[key] = _parse_scalar(rest)
                sibling_indent = seq_indent + 2
                while pos < len(lines):
                    nindent, ncontent = lines[pos]
                    if nindent != sibling_indent or ncontent.startswith("-"):
                        break
                    nkv = _KEY_VALUE_RE.match(ncontent)
                    if not nkv:
                        raise UriStateYamlError(f"Cannot parse line: {ncontent!r}")
                    nkey, nrest = nkv.group(1), nkv.group(2)
                    pos += 1
                    if nrest.strip() == "":
                        value = parse_block(sibling_indent + 1)
                    else:
                        value = _parse_scalar(nrest)
                    _set_unique(entry, nkey, value, context=f"list item at indent {seq_indent}")
                result.append(entry)
            else:
                result.append(_parse_scalar(item_body))
        return result

    def parse_mapping(map_indent: int) -> dict:
        nonlocal pos
        result: dict = {}
        while pos < len(lines):
            indent, content = lines[pos]
            if indent != map_indent or content.startswith("-"):
                break
            kv = _KEY_VALUE_RE.match(content)
            if not kv:
                raise UriStateYamlError(f"Cannot parse line: {content!r}")
            key, rest = kv.group(1), kv.group(2)
            pos += 1
            if rest.strip() == "":
                value = parse_block(map_indent + 1)
            else:
                value = _parse_scalar(rest)
            _set_unique(result, key, value, context=f"mapping at indent {map_indent}")
        return result

    top = parse_mapping(0)
    if pos != len(lines):
        remaining_indent, remaining_content = lines[pos]
        raise UriStateYamlError(
            f"Unconsumed trailing content at indent {remaining_indent}: "
            f"{remaining_content!r} (line {pos + 1} of {len(lines)} non-blank "
            f"content lines) — likely inconsistent indentation."
        )
    return top


def load_uri_state_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    return parse_uri_state_yaml(text)
