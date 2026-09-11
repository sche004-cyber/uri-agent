"""Real storage and real estimator drive pre-flight stop/fallback/degrade."""
from types import SimpleNamespace

import pytest

from test_usage_meter_recording import USER, OTHER, fake_router, record
from uri_core.core.model_router import AllProvidersUnreachableError, ModelRouter
from uri_core.core.usage_ceiling_store import UsageCeilingStore
from uri_core.core.usage_meter import UsageMeter, current_month, month_records


def test_unlimited_default_and_reset(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    store = UsageCeilingStore(USER)
    assert store.get_ceiling() is None and store.get_warn_threshold_ratio() == 0.8
    router = ModelRouter()
    for principal in (None, object(), SimpleNamespace(user_id=USER)):
        assert router._budget_ok("ollama", "reasoning", principal, "x" * 10000)
    store.set_ceiling(0)
    assert not router._budget_ok("ollama", "reasoning", SimpleNamespace(user_id=USER))
    store.set_ceiling(None)
    assert UsageCeilingStore(USER).get_ceiling() is None


@pytest.mark.parametrize("ceiling,allowed", [(29, False), (30, False), (31, True)])
def test_known_usage_boundary(monkeypatch, tmp_path, ceiling, allowed):
    monkeypatch.chdir(tmp_path)
    UsageMeter().record(record())
    UsageMeter().record(record(prompt=9999, output=None))
    UsageMeter().record(record(user_id=OTHER, prompt=9999))
    UsageCeilingStore(USER).set_ceiling(ceiling)
    assert ModelRouter()._budget_ok("ollama", "drafting", SimpleNamespace(user_id=USER)) is allowed


def test_prompt_estimate_blocks_all_candidates_before_build(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    UsageMeter().record(record())
    UsageCeilingStore(USER).set_ceiling(32)
    router, provider, build = fake_router(monkeypatch, candidates=["cloud", "ollama"])
    with pytest.raises(AllProvidersUnreachableError):
        router.attempt("reasoning", SimpleNamespace(user_id=USER), system="abcd", user="efgh")
    build.assert_not_called()
    provider.complete.assert_not_called()
    rows = list(month_records(USER, current_month()))
    assert len(rows) == 2
    assert rows[-1]["fallback_from"] == ["cloud(over_budget)", "ollama(over_budget)"]
    assert rows[-1]["outcome"] == "unreachable"
    assert router._health.is_healthy("cloud", "configured-model")


def test_warning_does_not_block(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    UsageMeter().record(record(prompt=60, output=20))
    UsageCeilingStore(USER).set_ceiling(100)
    router, provider, _ = fake_router(monkeypatch)
    router.attempt("reasoning", SimpleNamespace(user_id=USER), system="abcd", user="efgh")
    provider.complete.assert_called_once()


@pytest.mark.parametrize("value", [-1, True, 1.5, "100"])
def test_store_rejects_invalid_values(monkeypatch, tmp_path, value):
    monkeypatch.chdir(tmp_path)
    store = UsageCeilingStore(USER)
    store.set_ceiling(100)
    with pytest.raises(ValueError):
        store.set_ceiling(value)
    assert store.get_ceiling() == 100
