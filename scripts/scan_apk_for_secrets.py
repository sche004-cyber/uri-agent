#!/usr/bin/env python3
"""M22.9 (§5.1/§7): a pre-release static check, run manually (never
shipped in the app), that no key-shaped string literal exists anywhere
in a built URI Flutter APK's assets or compiled Dart snapshot.

This does not prove the app is secret-free in some absolute sense — it
proves this one, real, named class of mistake (an API key accidentally
compiled into the client) is not present, exactly what M22.9's own
acceptance criterion 2 asks for.

Usage:
    python scripts/scan_apk_for_secrets.py path/to/app-debug.apk
"""
from __future__ import annotations

import re
import sys
import zipfile

# Deliberately conservative patterns for real, currently-known key
# shapes this project actually uses (see uri_core/config/providers.py
# for the provider set) plus a generic high-entropy fallback for
# anything shaped like a bearer secret this list doesn't yet name.
PATTERNS: dict[str, re.Pattern[bytes]] = {
    "OpenAI-style key (sk-...)": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "Google API key (AIza...)": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"),
    "Anthropic key (sk-ant-...)": re.compile(rb"sk-ant-[A-Za-z0-9\-_]{20,}"),
    "generic 32+ char high-entropy token": re.compile(
        rb"[A-Za-z0-9_\-]{32,}"
    ),
}

# A high-entropy match on its own is extremely noisy (build hashes,
# font checksums, Dart snapshot symbol names all qualify) - only the
# named, real key-shaped patterns above are treated as a hard failure.
# The generic pattern is reported separately, for a human to eyeball,
# never as a scan failure by itself.
HARD_FAIL_PATTERNS = {
    "OpenAI-style key (sk-...)",
    "Google API key (AIza...)",
    "Anthropic key (sk-ant-...)",
}


def scan_apk(path: str) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    notices: list[str] = []

    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            data = archive.read(info.filename)
            for label, pattern in PATTERNS.items():
                matches = pattern.findall(data)
                if not matches:
                    continue
                line = f"{info.filename}: {label} ({len(matches)} match(es))"
                if label in HARD_FAIL_PATTERNS:
                    failures.append(line)
                else:
                    notices.append(line)

    return failures, notices


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    failures, notices = scan_apk(sys.argv[1])

    if notices:
        print("Generic high-entropy matches (informational only, not a failure):")
        for line in notices:
            print(f"  {line}")
        print()

    if failures:
        print("FAIL: key-shaped literal(s) found in the built APK:")
        for line in failures:
            print(f"  {line}")
        return 1

    print("PASS: no key-shaped literal found in the built APK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
