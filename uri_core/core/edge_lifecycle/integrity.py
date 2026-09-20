"""Streaming SHA-256 helpers used before asset registration."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import BinaryIO, Tuple


_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class IntegrityVerificationError(ValueError):
    pass


def normalize_sha256(value: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise IntegrityVerificationError("expected_sha256 must be 64 hexadecimal characters")
    return value.casefold()


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> Tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
            byte_count += len(chunk)
    return digest.hexdigest(), byte_count


def copy_and_hash(source: BinaryIO, destination: BinaryIO, *, chunk_size: int = 1024 * 1024) -> Tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0
    for chunk in iter(lambda: source.read(chunk_size), b""):
        destination.write(chunk)
        digest.update(chunk)
        byte_count += len(chunk)
    return digest.hexdigest(), byte_count


def verify_digest(actual: str, expected: str) -> None:
    normalized = normalize_sha256(expected)
    if actual.casefold() != normalized:
        raise IntegrityVerificationError("SHA-256 mismatch")
