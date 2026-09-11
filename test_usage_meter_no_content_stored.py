"""Content privacy is checked against both schema and actual serialized records."""
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_usage_meter_recording import USER, fake_router, record
from uri_core.core.usage_meter import UsageRecord, current_month, usage_path


def test_exact_frozen_metadata_schema():
    assert set(UsageRecord.__dataclass_fields__) == {
        "ts", "user_id", "session_id", "role", "provider_id", "model", "prompt_tokens",
        "eval_tokens", "duration_seconds", "outcome", "fallback_from", "estimated_cost"}
    with pytest.raises(FrozenInstanceError):
        record().role = "other"


def test_router_never_serializes_prompt_or_response(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    router, _, _ = fake_router(monkeypatch)
    router.attempt("reasoning", SimpleNamespace(user_id=USER),
                   system="SECRET_SYSTEM", user="SECRET_USER")
    stored = Path(usage_path(USER, current_month())).read_text()
    for secret in ("SECRET_SYSTEM", "SECRET_USER", "SECRET_RESPONSE"):
        assert secret not in stored
