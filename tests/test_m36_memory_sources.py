import os
from pathlib import Path
import subprocess
import pytest
from uri_v1.memory.contracts import IdentityStatus
from tests.test_m36_memory_support import setup


def test_identity_changed_missing_cap_private_overlap(tmp_path):
    log,s,rec,root=setup(tmp_path)
    locator=s.scan().locators[0]; a=s.fingerprint(locator)
    (root/"budget.xlsx").write_bytes(b"changed")
    b=s.fingerprint(locator)
    assert a.source_id==b.source_id and a.content_sha256!=b.content_sha256
    assert not s.verify_source(a.source_id,a.content_sha256)
    s.hash_cap=1
    assert s.fingerprint(locator).identity_status==IdentityStatus.HASH_UNAVAILABLE_SIZE_CAP
    assert not s.verify_source(b.source_id,b.content_sha256)
    (root/"budget.xlsx").unlink(); assert s.fingerprint(locator) is None
    with pytest.raises(ValueError): s.register(log.path)
    with pytest.raises(ValueError): s.register(tmp_path)


@pytest.mark.skipif(os.name!="nt",reason="Windows junction qualification requires Windows")
def test_real_junction_escape(tmp_path):
    log,s,rec,root=setup(tmp_path)
    outside=tmp_path/"outside"; outside.mkdir(); (outside/"secret.xlsx").write_bytes(b"private")
    junction=root/"junction"
    result=subprocess.run(["cmd","/c","mklink","/J",str(junction),str(outside)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    try:
        scan=s.scan(); assert not scan.complete
        assert all(l.relpath!="junction/secret.xlsx" for l in scan.locators)
        with pytest.raises(ValueError): s.register(junction)
    finally: os.rmdir(junction)


def test_symlink_escape(tmp_path):
    log,s,rec,root=setup(tmp_path)
    outside=tmp_path/"secret.xlsx"; outside.write_bytes(b"outside")
    try: (root/"link.xlsx").symlink_to(outside)
    except OSError as e: pytest.skip("Symlink creation unavailable: "+str(e))
    scan=s.scan(); assert not scan.complete
    assert all(l.relpath!="link.xlsx" for l in scan.locators)


def test_hash_replacement_race_and_hidden_incompleteness(tmp_path):
    log,s,rec,root=setup(tmp_path)
    locator=s.scan().locators[0]
    def fault(stage,path):
        if stage=="after_hash": path.write_bytes(b"raced")
    s.fault=fault
    with pytest.raises(ValueError): s.fingerprint(locator)
    (root/".hidden").mkdir(); (root/".hidden"/"budget.xlsx").write_bytes(b"collision")
    assert not s.scan().complete
