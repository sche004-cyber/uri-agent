"""Explicit authorized roots, bounded traversal and checked-handle fingerprints."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid

from .contracts import SourceRef, IdentityStatus as I, relpath, utc_now, digest
from .log import atomic_write

HASH_CAP = 64 * 1024 * 1024
REPARSE = 0x400
OFFLINE = 0x1000
# Python's stat module does not expose FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS.
RECALL = 0x00400000
HIDDEN_SYSTEM = 0x2 | 0x4
TYPE_MAP = {**dict.fromkeys((".xlsx", ".xls", ".xlsm", ".csv", ".ods"), "spreadsheet"),
            ".py":"script", **dict.fromkeys((".docx", ".doc", ".pdf", ".md", ".txt", ".odt"), "document")}


def normalized_path(path):
    return Path(os.path.normcase(str(path)))


def contained(child, parent):
    return normalized_path(child).is_relative_to(normalized_path(parent))


def _unsafe(path):
    info = path.lstat()
    return (path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())
            or bool(getattr(info, "st_file_attributes", 0) & REPARSE))


@dataclass(frozen=True)
class SourceLocator:
    source_id: str
    root_id: str
    relpath: str
    media_type: str
    size_bytes: int
    mtime_ns: int


@dataclass(frozen=True)
class ScanResult:
    locators: tuple[SourceLocator, ...]
    root_ids: tuple[str, ...]
    snapshot_digest: str
    complete: bool
    reason: str | None = None
    # Hidden/system *files* are never locators, but their names are kept so an
    # exact-name request can still fail closed on them (audit F-6). Hidden
    # directories remain whole-scan exclusions.
    hidden_names: tuple[str, ...] = ()


class SourceRegistry:
    def __init__(self, log, *, hash_cap=HASH_CAP, max_files=10000, max_depth=32, fault=None):
        if hash_cap < 1 or max_files < 1 or max_depth < 0: raise ValueError("invalid registry limits")
        self.log = log
        self.hash_cap = hash_cap
        self.max_files = max_files
        self.max_depth = max_depth
        self.fault = fault

    def roots(self):
        p = self.log.path / "sources.json"
        if not p.exists(): return {}
        d = json.loads(p.read_bytes())
        if set(d) != {"schema_version", "roots"} or d["schema_version"] != "m36.sources.v1": raise ValueError("INVALID_ROOT_REGISTRY")
        return d["roots"]

    def register(self, path):
        path = Path(path).absolute()
        if _unsafe(path) or not path.is_dir(): raise ValueError("UNSAFE_ROOT")
        resolved = path.resolve(strict=True)
        if contained(resolved,self.log.root) or contained(self.log.root,resolved): raise ValueError("PRIVATE_STORAGE_OVERLAP")
        with self.log.guard():
            roots = self.roots()
            for rid,p in roots.items():
                if normalized_path(resolved) == normalized_path(p): return rid
            rid = uuid.uuid4().hex; roots[rid] = str(resolved)
            atomic_write(self.log.path / "sources.json", json.dumps({"schema_version":"m36.sources.v1","roots":roots},sort_keys=True).encode())
            return rid

    def remove(self, root_id):
        with self.log.guard():
            roots = self.roots(); roots.pop(root_id, None)
            atomic_write(self.log.path / "sources.json", json.dumps({"schema_version":"m36.sources.v1","roots":roots},sort_keys=True).encode())

    def _safe_path(self, root, path):
        if _unsafe(root) or not root.is_dir(): raise ValueError("UNSAFE_ROOT")
        current = path
        while current != root:
            if not contained(current, root) or _unsafe(current): raise ValueError("UNSAFE_IDENTITY")
            current = current.parent
        resolved = path.resolve(strict=True)
        if not contained(resolved, root): raise ValueError("OUTSIDE_ROOT")
        if resolved != root: relpath(resolved.relative_to(root).as_posix())
        return resolved

    def scan(self, root_id=None, *, extensions=None):
        locators, exclusions, hidden = [], [], []
        try: roots = self.roots()
        except (OSError, ValueError): return ScanResult((),(),"",False,"REGISTRY_UNAVAILABLE")
        if root_id is not None:
            if root_id not in roots: return ScanResult((),(),"",False,"ROOT_UNAVAILABLE")
            roots = {root_id:roots[root_id]}
        visited = 0
        def walk(rid, root, directory, depth):
            nonlocal visited
            try:
                self._safe_path(root,directory)
                with os.scandir(directory) as it:
                    entries=[]
                    for entry in it:
                        entries.append(entry)
                        if len(entries)+visited>self.max_files:
                            exclusions.append("SCAN_BUDGET"); return
                    entries.sort(key=lambda e:(os.path.normcase(e.name),e.name))
                for entry in entries:
                    visited += 1
                    if visited > self.max_files: exclusions.append("SCAN_BUDGET"); return
                    path = Path(entry.path)
                    info = entry.stat(follow_symlinks=False)
                    attrs = getattr(info,"st_file_attributes",0)
                    if (entry.is_symlink() or (hasattr(entry,"is_junction") and entry.is_junction()) or attrs & REPARSE):
                        exclusions.append("REPARSE_EXCLUDED"); continue
                    if entry.name.startswith(".") or attrs & HIDDEN_SYSTEM:
                        if entry.is_file(follow_symlinks=False): hidden.append(entry.name)
                        else: exclusions.append("HIDDEN_EXCLUDED")
                        continue
                    safe = self._safe_path(root,path)
                    if entry.is_dir(follow_symlinks=False):
                        if depth >= self.max_depth: exclusions.append("DEPTH_EXCLUDED")
                        else: walk(rid,root,safe,depth+1)
                    elif entry.is_file(follow_symlinks=False):
                        rp = relpath(safe.relative_to(root).as_posix())
                        if extensions is not None and safe.suffix.casefold() not in extensions:
                            exclusions.append("EXTENSION_EXCLUDED"); continue
                        sid = hashlib.sha256((rid+"\0"+rp).encode()).hexdigest()[:32]
                        locators.append(SourceLocator(sid,rid,rp,TYPE_MAP.get(safe.suffix.casefold(),"unknown"),info.st_size,info.st_mtime_ns))
                    else: exclusions.append("UNCLASSIFIED_ENTRY")
            except (OSError, ValueError): exclusions.append("UNAVAILABLE_ENTRY")
        for rid,p in sorted(roots.items()): walk(rid,Path(p),Path(p),0)
        locators.sort(key=lambda l:l.source_id)
        snap = digest({"roots":roots,"locators":locators,"exclusions":sorted(exclusions),"hidden":sorted(hidden)})
        return ScanResult(tuple(locators),tuple(sorted(roots)),snap,not exclusions,
                          sorted(set(exclusions))[0] if exclusions else None,tuple(sorted(hidden)))

    def locate(self, source_id, scan=None):
        return next((l for l in (scan or self.scan()).locators if l.source_id == source_id),None)

    def _handle_path(self, stream, expected):
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            import msvcrt
            function = ctypes.WinDLL("kernel32",use_last_error=True).GetFinalPathNameByHandleW
            function.argtypes = (wintypes.HANDLE,wintypes.LPWSTR,wintypes.DWORD,wintypes.DWORD)
            function.restype = wintypes.DWORD
            buf = ctypes.create_unicode_buffer(32768)
            n = function(msvcrt.get_osfhandle(stream.fileno()),buf,len(buf),0)
            if not n or n >= len(buf): raise OSError("HANDLE_IDENTITY_UNAVAILABLE")
            value = buf.value
            if value.startswith("\\\\?\\UNC\\"): value = "\\\\" + value[8:]
            elif value.startswith("\\\\?\\"): value = value[4:]
            actual = Path(value)
        else:
            fdpath = Path("/proc/self/fd") / str(stream.fileno())
            if not fdpath.exists(): raise OSError("HANDLE_IDENTITY_UNAVAILABLE")
            actual = fdpath.resolve(strict=True)
        if normalized_path(actual) != normalized_path(expected): raise ValueError("HANDLE_PATH_MISMATCH")

    def fingerprint(self, source, *, observed_at=None):
        locator = source if isinstance(source,(SourceLocator,SourceRef)) else self.locate(source)
        if locator is None: return None
        roots = self.roots()
        if locator.root_id not in roots: return None
        root = Path(roots[locator.root_id]); path = root / relpath(locator.relpath)
        try:
            safe = self._safe_path(root,path); before = safe.stat()
            attrs = getattr(before,"st_file_attributes",0)
            status = I.HASH_VERIFIED; sha = None
            if attrs & (OFFLINE | RECALL): status = I.HASH_UNAVAILABLE_POLICY
            elif before.st_size > self.hash_cap: status = I.HASH_UNAVAILABLE_SIZE_CAP
            else:
                if self.fault: self.fault("before_open",safe)
                with open(safe,"rb") as stream:
                    opened = os.fstat(stream.fileno()); self._handle_path(stream,safe)
                    self._safe_path(root,safe)
                    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) != (opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns): raise ValueError("SOURCE_REPLACED")
                    h = hashlib.sha256(); total = 0
                    while chunk := stream.read(1024*1024):
                        total += len(chunk)
                        if total > self.hash_cap: raise ValueError("HASH_CAP_RACE")
                        h.update(chunk)
                    if self.fault: self.fault("after_hash",safe)
                    self._handle_path(stream,safe)
                    after_handle = os.fstat(stream.fileno())
                    if (opened.st_dev,opened.st_ino,opened.st_size,opened.st_mtime_ns) != (after_handle.st_dev,after_handle.st_ino,after_handle.st_size,after_handle.st_mtime_ns): raise ValueError("SOURCE_CHANGED_DURING_HASH")
                    sha = h.hexdigest()
            self._safe_path(root,safe); after = safe.stat()
            if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,getattr(before,"st_file_attributes",0)) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,getattr(after,"st_file_attributes",0)):
                raise ValueError("SOURCE_CHANGED_DURING_HASH")
            return SourceRef(locator.source_id,locator.root_id,locator.relpath,locator.media_type,sha,
                             before.st_size,before.st_mtime_ns,observed_at or utc_now(),status)
        except FileNotFoundError: return None

    def verify_source(self, source_id, expected_sha, scope_receipt=None):
        try:
            scan = self.scan()
            if scope_receipt and (not scope_receipt.complete or not scan.complete or scan.snapshot_digest != scope_receipt.snapshot_digest): return False
            ref = self.fingerprint(self.locate(source_id,scan)) if self.locate(source_id,scan) else None
            return bool(ref and ref.identity_status == I.HASH_VERIFIED and expected_sha is not None and ref.content_sha256 == expected_sha)
        except (OSError, ValueError): return False

    def freshness(self, recorded: SourceRef):
        from .contracts import Freshness as F
        try:
            live = self.fingerprint(recorded)
            if live is None: return F.SOURCE_MISSING
            if live.identity_status != I.HASH_VERIFIED or recorded.content_sha256 is None: return F.UNKNOWN
            return F.CURRENT if live.content_sha256 == recorded.content_sha256 else F.STALE_SOURCE
        except (OSError, ValueError): return F.UNKNOWN
