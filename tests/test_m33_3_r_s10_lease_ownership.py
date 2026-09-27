"""M33.3-R S10: additive lease-owner provenance and the ownership ledger."""

from __future__ import annotations

import threading

import pytest

from uri_core.core.edge.contracts import (LEASE_OWNER_EXTERNAL, LEASE_OWNER_UNKNOWN, LEASE_OWNER_URI,
                                          RuntimeLease)
from uri_core.core.edge.lease_ownership import (URI_INSTANCE_PREFIX, LeaseOwnershipError, LeaseOwnershipLedger,
                                                new_uri_instance_id)


def test_runtime_lease_contract_change_is_additive():
    legacy = RuntimeLease("lease-1", "lmstudio")  # original positional two-field construction
    assert legacy.owner_kind == LEASE_OWNER_UNKNOWN and legacy.owner_id is None and legacy.model_id is None
    with pytest.raises(ValueError):
        RuntimeLease("lease-1", "lmstudio", owner_kind="ME")


def test_uri_records_and_releases_only_its_own_leases():
    ledger = LeaseOwnershipLedger()
    instance = new_uri_instance_id()
    assert instance.startswith(URI_INSTANCE_PREFIX)
    lease = ledger.record_acquired(runtime_id="lmstudio", model_id="qwen3.5-2b", provider_instance_id=instance)
    assert lease.owner_kind == LEASE_OWNER_URI and ledger.may_unload(lease) and ledger.may_unload(instance)
    assert not ledger.may_unload("qwen3.5-9b")
    with pytest.raises(LeaseOwnershipError):
        ledger.require_may_unload("qwen3.5-9b")
    with pytest.raises(LeaseOwnershipError):
        ledger.record_released("qwen3.5-9b")
    assert ledger.record_released(instance) == lease and not ledger.may_unload(instance)
    with pytest.raises(LeaseOwnershipError):
        ledger.record_acquired(runtime_id="lmstudio", model_id="m", provider_instance_id="plain-name")


def test_classification_never_marks_external_or_orphan_as_uri_owned():
    ledger = LeaseOwnershipLedger()
    mine = ledger.record_acquired(runtime_id="lmstudio", model_id="qwen3.5-2b",
                                  provider_instance_id=new_uri_instance_id())
    orphan = new_uri_instance_id()  # URI-looking identifier with no ledger record (e.g. after restart)
    observed = [(mine.provider_instance_id, "qwen3.5-2b"), ("qwen3.5-9b", "qwen3.5-9b"), (orphan, "x"), (None, "y")]
    kinds = [lease.owner_kind for lease in ledger.classify("lmstudio", observed)]
    assert kinds == [LEASE_OWNER_URI, LEASE_OWNER_EXTERNAL, LEASE_OWNER_EXTERNAL, LEASE_OWNER_UNKNOWN]
    assert not ledger.may_unload(orphan) and not ledger.may_unload("qwen3.5-9b")


def test_duplicate_acquire_rejected_and_ledger_thread_safe():
    ledger = LeaseOwnershipLedger()
    ids = [new_uri_instance_id() for _ in range(200)]
    threads = [threading.Thread(target=ledger.record_acquired,
                                kwargs=dict(runtime_id="r", model_id="m", provider_instance_id=i)) for i in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ledger.active()) == 200
    with pytest.raises(LeaseOwnershipError):
        ledger.record_acquired(runtime_id="r", model_id="m", provider_instance_id=ids[0])
