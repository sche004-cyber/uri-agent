"""Exact dashboard folds, with provider construction/calls forbidden."""
from dataclasses import replace
from unittest.mock import Mock

from test_usage_meter_recording import USER, OTHER, record
from uri_core.core.usage_aggregator import aggregate_month
from uri_core.core.usage_ceiling_store import UsageCeilingStore
from uri_core.core.usage_meter import UsageMeter


def test_exact_totals_and_no_model_calls(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    forbidden = Mock(side_effect=AssertionError("dashboard made a model call"))
    monkeypatch.setattr("uri_core.core.model_router.ModelRouter.attempt", forbidden)
    monkeypatch.setattr("uri_core.config.model_roles.build_provider", forbidden)
    meter = UsageMeter()
    meter.record(record())
    meter.record(replace(record(prompt=5, output=None, role="drafting"), provider_id="openai"))
    meter.record(replace(record(prompt=None, output=None), provider_id=None, model=None,
                         outcome="unreachable", duration_seconds={"value": None, "confidence": "UNAVAILABLE"}))
    meter.record(record(user_id=OTHER, prompt=9999))
    meter.record(record(month="2001-01", prompt=1, output=2))
    UsageCeilingStore(USER).set_ceiling(35)
    result = aggregate_month(USER)
    assert result["totals"] == {"calls": 3, "prompt_tokens": 15, "eval_tokens": 20,
                                "duration_seconds": 3.0, "known_total_tokens": 30,
                                "unavailable_records": 3, "outcomes": {"success": 2, "unreachable": 1}}
    assert result["by_role"]["reasoning"]["calls"] == 2
    assert result["by_role"]["drafting"]["prompt_tokens"] == 5
    assert result["by_provider"]["openai"]["display_name"] == "OpenAI"
    assert result["by_provider"]["ollama"]["known_total_tokens"] == 30
    assert result["limits"]["warning"] and not result["limits"]["ceiling_reached"]
    assert aggregate_month(USER, "2001-01")["totals"]["known_total_tokens"] == 3
    assert aggregate_month(USER, "2002-01")["totals"]["calls"] == 0
    UsageCeilingStore(USER).set_ceiling(30)
    assert aggregate_month(USER)["limits"]["ceiling_reached"]
    forbidden.assert_not_called()
