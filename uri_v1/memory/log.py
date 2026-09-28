"""Append-only monthly storage with guarded framing and exact read-back."""
from __future__ import annotations

from contextlib import contextmanager
import base64
import hashlib
import json
import os
from pathlib import Path
import uuid
import time

from uri_v1.user_storage import user_scoped_path, locked_append
from .contracts import MemoryRecord, WriteResult, canonical, digest, identifier


def atomic_write(path: Path, data: bytes):
    """Fsync content and durably publish the name before reporting success."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with open(tmp, "xb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            move = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
            move.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
            move.restype = wintypes.BOOL
            # MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH.
            if not move(str(tmp), str(path), 0x1 | 0x8): raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.replace(tmp, path)
            fd = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        if path.read_bytes() != data: raise OSError("ATOMIC_READBACK_FAILED")
    finally:
        if tmp.exists(): tmp.unlink()


class MemoryLog:
    def __init__(self, user_id: str, root: str | Path, *, fault=None):
        self.user_id = user_id
        self.root = Path(root).resolve()
        self.path = Path(user_scoped_path(user_id, "memory", str(self.root)))
        self.path.mkdir(parents=True, exist_ok=True)
        self.fault = fault

    @contextmanager
    def guard(self):
        with locked_append(str(self.path / "write.guard")):
            yield

    def _fault(self, stage):
        if self.fault: self.fault(stage)

    def durable_enabled(self):
        p = self.path / "settings.json"
        if not p.exists(): return True  # M36-specific ON default, independent of S7.
        try:
            d = json.loads(p.read_bytes())
            return set(d) == {"schema_version", "durable_enabled"} and d["schema_version"] == "m36.settings.v1" and d["durable_enabled"] is True
        except (OSError, ValueError): return False

    def set_durable_enabled(self, enabled: bool):
        if type(enabled) is not bool: raise ValueError("boolean required")
        with self.guard(): atomic_write(self.path / "settings.json", canonical({"schema_version":"m36.settings.v1", "durable_enabled":enabled}))

    def put_protected(self, category, key, value):
        if category not in ("events", "attestations"): raise ValueError("protected category")
        identifier(key)
        path = self.path / category / (key + ".json")
        data = canonical(value)
        if path.exists():
            if path.read_bytes() != data: raise ValueError("PROTECTED_ID_CONFLICT")
        else: atomic_write(path, data)

    def protected(self, category, key):
        if category not in ("events", "attestations"): raise ValueError("protected category")
        identifier(key)
        try: return json.loads((self.path / category / (key + ".json")).read_bytes())
        except (OSError, ValueError): return None

    def _quarantine(self, partition, offset, fragment, reason):
        # Recovery adds a separator, not new logical fragment evidence.
        qid = digest({"partition":partition,"offset":offset,"sha256":hashlib.sha256(fragment.removesuffix(b"\n")).hexdigest()})
        q = {"recovery_id":qid,"partition":partition,"offset":offset,"fragment_sha256":hashlib.sha256(fragment).hexdigest(),
             "fragment_base64":base64.b64encode(fragment).decode(),"reason":reason}
        # One immutable copy per offset/hash; deterministic dedup, never truncate log.
        target = self.path / "quarantine" / (qid + ".json")
        if not target.exists(): atomic_write(target, canonical(q))
        return qid

    def _physical(self):
        records, rejected = [], []
        for p in sorted(self.path.glob("log-????-??.jsonl")):
            offset = 0
            with open(p, "rb") as stream:
                for line in stream:
                    try:
                        if not line.endswith(b"\n"): raise ValueError("UNTERMINATED_TAIL")
                        record = MemoryRecord.from_dict(json.loads(line))
                        if record.user_id != self.user_id: raise ValueError("CROSS_USER_RECORD")
                        records.append((record, p.name, offset, line))
                    except (ValueError, TypeError, KeyError) as e:
                        rejected.append(self._quarantine(p.name, offset, line, type(e).__name__ + ":" + str(e)))
                    offset += len(line)
        return records, rejected

    def load_unlocked(self):
        from .index import MemoryIndex
        physical, recovery = self._physical()
        index = MemoryIndex(self.user_id, self.protected)
        for record, partition, offset, line in physical:
            try: index.accept(record)
            except (ValueError, TypeError, KeyError) as e:
                recovery.append(self._quarantine(partition, offset, line, type(e).__name__ + ":" + str(e)))
        index.recovery_ids = tuple(recovery)
        return index

    def load(self):
        with self.guard(): return self.load_unlocked()

    def append(self, records):
        with self.guard(): return self.append_unlocked(tuple(records))

    def reset(self):
        """Whole-user Memory reset. Selective forget remains hide-only."""
        import shutil
        with self.guard():
            for target in self.path.iterdir():
                if target.name=="write.guard": continue
                resolved=target.resolve(strict=True)
                if not resolved.is_relative_to(self.path.resolve(strict=True)): raise ValueError("UNSAFE_RESET_TARGET")
                if target.is_dir(): shutil.rmtree(target)
                else: target.unlink()

    def append_unlocked(self, records):
        start=time.perf_counter_ns()
        result=self._append_records_unlocked(records)
        try:
            trace=next((r.trace_id for r in records if r.trace_id),None)
            payload={"event":"WRITE","trace_id":trace,"record_ids":result.record_ids,"persisted":result.persisted,
                     "per_record":result.per_record,"recovery_ids":result.recovery_ids,"write_us":(time.perf_counter_ns()-start)//1000}
            month=records[0].recorded_at[:7] if records else "unknown"
            # Same Memory guard is already held: no nested locked_append.
            with open(self.path/("telemetry-"+month+".jsonl"),"ab") as stream: stream.write(canonical(payload)+b"\n")
        except (OSError,ValueError,TypeError): pass
        return result

    def _append_records_unlocked(self, records):
        if not self.durable_enabled(): return WriteResult(False, "DURABLE_OFF", tuple(r.record_id for r in records))
        done, recovery = [], []
        try:
            # Repair all relevant boundaries before deciding expected heads.
            for month in sorted({r.recorded_at[:7] for r in records}):
                p = self.path / ("log-" + month + ".jsonl")
                if not p.exists(): atomic_write(p, b"")
                with open(p, "rb") as reader:
                    reader.seek(0, os.SEEK_END); length = reader.tell()
                    if length: reader.seek(-1, os.SEEK_END); last = reader.read(1)
                    else: last = b"\n"
                if last != b"\n":
                    with open(p, "ab") as stream:
                        self._fault("separator"); stream.write(b"\n"); stream.flush(); os.fsync(stream.fileno())
            index = self.load_unlocked(); recovery = list(index.recovery_ids)
            for record in records:
                prior = index.records.get(record.record_id)
                if prior:
                    if canonical(prior.to_dict()) != canonical(record.to_dict()): raise ValueError("ID_CONFLICT")
                    done.append(True); continue
                index.accept(record, writing=True)
                p = self.path / ("log-" + record.recorded_at[:7] + ".jsonl")
                data = canonical(record.to_dict()) + b"\n"
                boundary = p.stat().st_size
                with open(p, "ab") as stream:
                    self._fault("before_write")
                    # Fault hooks cover the JSON/newline boundary, flush and fsync independently.
                    stream.write(data[:-1]); self._fault("after_body")
                    stream.write(b"\n"); self._fault("after_newline")
                    stream.flush(); self._fault("flush"); os.fsync(stream.fileno()); self._fault("fsync")
                self._fault("readback")
                with open(p, "rb") as stream:
                    stream.seek(boundary); actual = stream.read(len(data))
                if actual != data: raise OSError("READBACK_BYTES_MISMATCH")
                check = MemoryRecord.from_dict(json.loads(actual))
                if check.to_dict() != record.to_dict(): raise OSError("READBACK_RECORD_MISMATCH")
                restored = self.load_unlocked()
                if record.record_id not in restored.records: raise OSError("READBACK_VALIDATION_FAILED")
                done.append(True); self._fault("after_record")
            restored = self.load_unlocked()
            if any(r.kind.value == "CORRECTION" and r.record_id in restored.pending_corrections for r in records):
                return WriteResult(False, "PENDING_CORRECTION", tuple(r.record_id for r in records), tuple(done), tuple(recovery))
            return WriteResult(True, "READBACK_VALIDATED", tuple(r.record_id for r in records), tuple(done), tuple(recovery))
        except (OSError, ValueError, TypeError, KeyError) as e:
            return WriteResult(False, str(e) or type(e).__name__, tuple(r.record_id for r in records),
                               tuple(done + [False] * (len(records)-len(done))), tuple(recovery))
