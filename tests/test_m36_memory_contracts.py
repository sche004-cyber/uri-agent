import uuid
import pytest
from uri_v1.memory.contracts import *

USER = str(uuid.UUID(int=1))


def test_authority_matrix_and_claims():
    assert derive_authority(RecordKind.TASK_STATE, Provenance.URI_RECORDED) == Authority.RUNTIME_RECORDED
    for status in VerificationStatus:
        if status not in (VerificationStatus.CLAIMED_ONLY, VerificationStatus.FAILED):
            with pytest.raises(ValueError): derive_authority(RecordKind.OUTCOME, Provenance.EXECUTION_OUTCOME, status)
    assert derive_authority(RecordKind.OUTCOME, Provenance.VERIFIER_RESULT, VerificationStatus.FAILED) == Authority.VERIFIER_ATTESTED
    with pytest.raises(ValueError): derive_authority(RecordKind.TASK_STATE, Provenance.MODEL_DERIVED)


def test_closed_immutable_serialized_authority():
    p = dict(objective_label="budget", origin_turn_trace_id="a"*32, transition_evidence_ids=["b"*32])
    record = MemoryRecord(USER, RecordKind.TASK_OPENED, Provenance.USER_PROVIDED, p, task_id="c"*32)
    p["objective_label"] = "changed"
    assert record.payload["objective_label"] == "budget"
    assert MemoryRecord.from_dict(record.to_dict()) == record
    with pytest.raises(TypeError): record.payload["objective_label"] = "overwrite"
    with pytest.raises(TypeError): MemoryRecord(USER, RecordKind.TASK_OPENED, Provenance.USER_PROVIDED, p, authority="VERIFIED_OUTCOME")
    raw = record.to_dict(); raw["authority"] = "VERIFIED_OUTCOME"
    with pytest.raises(ValueError): MemoryRecord.from_dict(raw)
    for extra in ("harness_run_ref", "unknown"):
        with pytest.raises(ValueError): MemoryRecord(USER, RecordKind.TASK_OPENED, Provenance.USER_PROVIDED, {**p, extra:"x"}, task_id="c"*32)
    with pytest.raises(ValueError): MemoryRecord(USER, RecordKind.TASK_OPENED, Provenance.USER_PROVIDED, p, scope=Scope.SHAREABLE, task_id="c"*32)


@pytest.mark.parametrize("path", ["../a", "/a", "a:stream", "CON.txt", "foo.", "foo ", "a//b", "C:/a", "a\\b"])
def test_bad_paths(path):
    with pytest.raises(ValueError): relpath(path)


def test_bounds_secrets_trace():
    for text in ("api_key=secret", "password: secret", "x"*513):
        with pytest.raises(ValueError): bounded(text)
    with pytest.raises(ValueError): require_trace_id("0"*32)


def test_source_hash_degradation():
    root = "a"*32; path = "budget.xlsx"
    sid = hashlib.sha256((root+"\0"+path).encode()).hexdigest()[:32]
    args = (sid,root,path,"spreadsheet",None,64*1024*1024+1,1,utc_now())
    with pytest.raises(ValueError): SourceRef(*args)
    assert SourceRef(*args,IdentityStatus.HASH_UNAVAILABLE_SIZE_CAP).content_sha256 is None
