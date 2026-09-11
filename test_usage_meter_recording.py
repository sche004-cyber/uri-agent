"""M22.7 terminal recording, confidence, append and failure guarantees."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
import multiprocessing

import pytest

from uri_core.core import model_router as routing
from uri_core.core.model_providers.base import ModelResponse, ProviderAuthenticationError, ProviderUnavailableError
from uri_core.core.usage_meter import UsageMeter, UsageRecord, current_month, month_records, usage_path

USER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def record(user_id=USER, prompt=10, output=20, role="reasoning", month=None):
    def field(value):
        return {"value": value, "confidence": "KNOWN" if value is not None else "UNAVAILABLE"}
    return UsageRecord((month or current_month()) + "-01T00:00:00+00:00", user_id,
                       "session", role, "ollama", "actual-model", field(prompt), field(output),
                       field(1.5), "success", [], field(None))


def fake_router(monkeypatch, response=None, error=None, candidates=None):
    router = routing.ModelRouter()
    monkeypatch.setattr(router, "_ordered_candidates", lambda role: candidates or ["ollama"])
    monkeypatch.setattr(router, "_model_for_role", lambda role: "configured-model")
    provider = Mock()
    provider.complete.return_value = response or ModelResponse("SECRET_RESPONSE", "actual-model", "ollama", 10, 20, 1.5)
    provider.complete.side_effect = error
    build = Mock(return_value=provider)
    monkeypatch.setattr(routing, "build_provider", build)
    return router, provider, build


@pytest.mark.parametrize("counts", [(10, 20, 1.5), (None, None, None), (0, None, 0.0)])
def test_success_exactly_one_record(monkeypatch, tmp_path, counts):
    monkeypatch.chdir(tmp_path)
    response = ModelResponse("secret", "actual-model", "adapter", *counts)
    router, provider, _ = fake_router(monkeypatch, response)
    assert router.attempt("reasoning", SimpleNamespace(user_id=USER), session_id="s1",
                          system="private system", user="private user") is response
    rows = list(month_records(USER, current_month()))
    assert len(rows) == 1
    row = rows[0]
    assert (row["provider_id"], row["model"], row["session_id"], row["fallback_from"]) == ("ollama", "actual-model", "s1", [])
    assert "session_id" not in provider.complete.call_args.kwargs
    for name, value in zip(("prompt_tokens", "eval_tokens", "duration_seconds"), counts):
        assert row[name] == {"value": value, "confidence": "KNOWN" if value is not None else "UNAVAILABLE"}


def test_failed_candidate_then_success_records_only_winner(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    router, provider, _ = fake_router(monkeypatch, candidates=["cloud", "ollama"])
    provider.complete.side_effect = [ProviderUnavailableError("down"), ModelResponse("ok", "winner", "local")]
    router.attempt("reasoning", SimpleNamespace(user_id=USER))
    rows = list(month_records(USER, current_month()))
    assert len(rows) == 1
    assert rows[0]["fallback_from"] == ["cloud(failed:ProviderUnavailableError)"]
    assert rows[0]["provider_id"] == "ollama"


def test_exhaustion_records_one_unavailable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    router, _, _ = fake_router(monkeypatch, error=ProviderUnavailableError("down"), candidates=["cloud", "ollama"])
    with pytest.raises(routing.AllProvidersUnreachableError):
        router.attempt("reasoning", SimpleNamespace(user_id=USER))
    rows = list(month_records(USER, current_month()))
    assert len(rows) == 1 and rows[0]["outcome"] == "unreachable"
    assert rows[0]["provider_id"] is None and rows[0]["model"] is None
    for name in ("prompt_tokens", "eval_tokens", "duration_seconds", "estimated_cost"):
        assert rows[0][name] == {"value": None, "confidence": "UNAVAILABLE"}


def test_auth_failure_never_records_or_falls_back(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    router, provider, _ = fake_router(monkeypatch, error=ProviderAuthenticationError("denied"), candidates=["cloud", "ollama"])
    with pytest.raises(ProviderAuthenticationError):
        router.attempt("reasoning", SimpleNamespace(user_id=USER))
    assert list(month_records(USER, current_month())) == []
    assert provider.complete.call_count == 1


def test_resolve_is_observation_only(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    router, provider, _ = fake_router(monkeypatch)
    router.resolve("reasoning", SimpleNamespace(user_id=USER))
    provider.complete.assert_not_called()
    assert list(month_records(USER, current_month())) == []


def test_append_concurrent_and_month_role_isolation(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    meter = UsageMeter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(meter.record, [record()] * 40))
    meter.record(record(prompt=None))
    meter.record(record(role="drafting"))
    meter.record(record(user_id=OTHER, prompt=999))
    meter.record(record(month="2001-01"))
    assert len(list(month_records(USER, current_month()))) == 42
    assert meter.estimate_current_month_tokens(USER) == 1230
    assert meter.estimate_current_month_tokens(USER, "reasoning") == 1200


def _process_append():
    for _ in range(20):
        UsageMeter().record(record())


def test_append_across_processes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    processes = [multiprocessing.get_context("spawn").Process(target=_process_append) for _ in range(3)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        if process.is_alive():
            process.terminate()
            process.join()
            pytest.fail("usage writer did not finish")
        assert process.exitcode == 0
    assert len(list(month_records(USER, current_month()))) == 60


def test_write_failure_does_not_break_completion(monkeypatch, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    router, _, _ = fake_router(monkeypatch)
    monkeypatch.setattr("uri_core.core.usage_meter.os.makedirs", Mock(side_effect=OSError("private")))
    assert router.attempt("reasoning", SimpleNamespace(user_id=USER)).content == "SECRET_RESPONSE"
    assert "Unable to append usage record" in caplog.text
    assert "private" not in caplog.text


def test_malformed_tail_and_invalid_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    UsageMeter().record(record())
    with open(usage_path(USER, current_month()), "a") as stream:
        stream.write('{"incomplete":')
    assert UsageMeter().estimate_current_month_tokens(USER) == 30
    UsageMeter().record(replace(record(), user_id="../escape"))  # never raises
    with pytest.raises(ValueError):
        usage_path(USER, "../../escape")
