"""Focused M31 contract checks; provider network calls are never made here."""
from pathlib import Path

import pytest
from fastapi import HTTPException

from uri_core.core.fallback_routing_store import FallbackRoutingStore
from uri_core.core.conversation_history import ConversationHistoryStore, ConversationTurn
from uri_core.core.model_router import ModelRouter
from uri_core.core.model_providers import (
    AnthropicProvider,
    ModelProviderConfig,
    ModelResponse,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from uri_core.core.provider_registry import CATALOGUE_BY_ID
from uri_core.app import server


def test_transport_seam_is_metadata_only():
    assert CATALOGUE_BY_ID["ollama"].auth_transports == ["local"]
    assert "subscription_oauth" in CATALOGUE_BY_ID["openai"].auth_transports
    assert "subscription_oauth" in CATALOGUE_BY_ID["anthropic"].auth_transports
    assert "subscription_oauth" in CATALOGUE_BY_ID["gemini"].auth_transports


def test_fallback_routing_store_defaults_and_round_trips(monkeypatch, tmp_path):
    monkeypatch.setattr("uri_core.core.fallback_routing_store.user_scoped_path", lambda _user, _name: str(tmp_path / _name))
    store = FallbackRoutingStore("user-a")
    assert store.load() == {"primary": None, "fallback_1": None, "fallback_2": None}
    expected = {"primary": {"provider_id": "ollama", "model": "qwen3:14b"}, "fallback_1": "auto", "fallback_2": None}
    store.save(expected)
    assert store.load() == expected


def test_brain_runtime_does_not_shell_out_to_development_agents():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("uri_core").rglob("*.py"))
    assert "subprocess" not in source or all(token not in source for token in ("claude -p", "codex exec", "antigravity"))


def test_verify_provider_rejects_unknown_and_missing_key(monkeypatch):
    user_id = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(HTTPException) as unknown:
        server.verify_provider("missing", user_id=user_id)
    assert unknown.value.status_code == 400

    monkeypatch.setattr(server, "_verified_models_cache", {})
    monkeypatch.setattr(
        "uri_core.core.provider_keys.ProviderKeyStore",
        lambda _user: type("Keys", (), {"has_key": lambda _self, _provider: False})(),
    )
    result = server.verify_provider("openai", user_id=user_id)
    assert result["verified"] is False
    assert result["verified_models"] == []
    assert "API key" in result["error"]


def test_verify_provider_uses_short_lived_cache(monkeypatch):
    monkeypatch.setattr(server, "_verified_models_cache", {
        ("user-a", "openai"): (server.time.monotonic() + 60, ["gpt-4o"]),
    })
    result = server.verify_provider("openai", user_id="user-a")
    assert result == {
        "provider_id": "openai",
        "verified": True,
        "verified_models": ["gpt-4o"],
        "error": None,
        "cached": True,
    }


def test_fallback_routing_endpoint_rejects_unverified_models(monkeypatch, tmp_path):
    monkeypatch.setattr("uri_core.core.fallback_routing_store.user_scoped_path", lambda _user, name: str(tmp_path / name))
    monkeypatch.setattr(server, "_verified_models_cache", {})
    with pytest.raises(HTTPException) as rejected:
        server.update_fallback_routing(
            server.FallbackRoutingRequest(primary={"provider_id": "ollama", "model": "not-verified"}),
            user_id="user-a",
        )
    assert rejected.value.status_code == 400

    monkeypatch.setattr(server, "_verified_models_cache", {
        ("user-a", "ollama"): (server.time.monotonic() + 60, ["qwen3:14b"]),
    })
    payload = server.FallbackRoutingRequest(
        primary={"provider_id": "ollama", "model": "qwen3:14b"},
        fallback_1="auto",
        fallback_2=None,
    )
    assert server.update_fallback_routing(payload, user_id="user-a") == payload.model_dump()
    assert server.get_fallback_routing(user_id="user-a") == payload.model_dump()

    with pytest.raises(HTTPException) as dup_rejected:
        server.update_fallback_routing(
            server.FallbackRoutingRequest(
                primary={"provider_id": "ollama", "model": "qwen3:14b"},
                fallback_1={"provider_id": "ollama", "model": "qwen3:14b"},
            ),
            user_id="user-a",
        )
    assert dup_rejected.value.status_code == 400
    assert "Duplicate" in dup_rejected.value.detail


def test_router_prefers_validated_custom_routing_before_role_config(monkeypatch, tmp_path):
    monkeypatch.setattr("uri_core.core.fallback_routing_store.user_scoped_path", lambda _user, name: str(tmp_path / name))
    FallbackRoutingStore("user-a").save({
        "primary": {"provider_id": "openai", "model": "gpt-4o"},
        "fallback_1": {"provider_id": "ollama", "model": "qwen3:14b"},
        "fallback_2": None,
    })
    principal = type("Principal", (), {"user_id": "user-a"})()
    assert ModelRouter()._ordered_candidates("reasoning", principal) == ["openai", "ollama"]
    assert ModelRouter()._ordered_candidates("reasoning", None)[0] == "ollama"


def test_router_fallback_auto_attempts_next_on_primary_failure(monkeypatch, tmp_path):
    monkeypatch.setattr("uri_core.core.fallback_routing_store.user_scoped_path", lambda _user, name: str(tmp_path / name))
    user_id = "11111111-1111-4111-8111-111111111111"
    FallbackRoutingStore(user_id).save({
        "primary": {"provider_id": "openai", "model": "gpt-4o"},
        "fallback_1": "auto",
        "fallback_2": None,
    })
    attempts = []

    class FailingPrimary:
        def complete(self, **_kwargs):
            attempts.append("openai")
            raise ProviderUnavailableError("primary unavailable")

    class WorkingOllama:
        def complete(self, **_kwargs):
            attempts.append("ollama")
            return ModelResponse(content="ok", model="qwen3:14b", provider="ollama")

    monkeypatch.setattr(
        "uri_core.core.model_router.build_provider",
        lambda _role, _principal, provider_id_override: FailingPrimary()
        if provider_id_override == "openai" else WorkingOllama(),
    )
    principal = type("Principal", (), {"user_id": user_id})()
    response = ModelRouter().attempt("reasoning", principal, system="s", user="u")
    assert response.content == "ok"
    assert attempts == ["openai", "ollama"]


class _AnthropicResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_anthropic_complete_success(monkeypatch):
    captured = {}
    def post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _AnthropicResponse(200, {
            "model": "claude-3-5-sonnet",
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 7, "output_tokens": 3},
        })
    monkeypatch.setattr("uri_core.core.model_providers.anthropic_provider.requests.post", post)
    provider = AnthropicProvider(ModelProviderConfig(base_url="https://api.anthropic.com", model="claude-3-5-sonnet"), api_key="secret")
    response = provider.complete(system="system", user="user", max_tokens=9)
    assert response.content == "hello"
    assert response.provider == "anthropic"
    assert response.prompt_tokens == 7
    assert response.eval_tokens == 3
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"] == {"x-api-key": "secret", "anthropic-version": "2023-06-01", "content-type": "application/json"}
    assert captured["json"]["system"] == "system"
    assert captured["json"]["messages"] == [{"role": "user", "content": "user"}]


def test_anthropic_authentication_failure(monkeypatch):
    monkeypatch.setattr("uri_core.core.model_providers.anthropic_provider.requests.post", lambda *_args, **_kwargs: _AnthropicResponse(401))
    with pytest.raises(ProviderAuthenticationError):
        AnthropicProvider(api_key="bad").complete(system="", user="u")


@pytest.mark.parametrize(("status_code", "error"), [(429, ProviderRateLimitError), (500, ProviderUnavailableError)])
def test_anthropic_rate_limit_and_unavailable(monkeypatch, status_code, error):
    monkeypatch.setattr("uri_core.core.model_providers.anthropic_provider.requests.post", lambda *_args, **_kwargs: _AnthropicResponse(status_code))
    with pytest.raises(error):
        AnthropicProvider(api_key="key").complete(system="", user="u")


def test_anthropic_verification_endpoint(monkeypatch):
    user_id = "user-a"
    monkeypatch.setattr(server, "_verified_models_cache", {})
    monkeypatch.setattr(
        "uri_core.core.provider_keys.ProviderKeyStore",
        lambda _user: type("Keys", (), {
            "has_key": lambda _self, _provider: True,
            "get_key_for_use": lambda _self, _provider: "key",
        })(),
    )
    monkeypatch.setattr(
        "uri_core.core.provider_registry.ProviderConfigStore",
        lambda _user: type("Config", (), {"get_provider_config": lambda _self, _provider: {}})(),
    )
    calls = []
    class Probe:
        def __init__(self, config, api_key):
            assert api_key == "key"
            self.config = config
        def complete(self, **kwargs):
            calls.append(kwargs)
            return ModelResponse(content="OK", model=self.config.model, provider="anthropic")
    monkeypatch.setattr("uri_core.core.model_providers.AnthropicProvider", Probe)
    result = server.verify_provider("anthropic", user_id=user_id)
    assert result["verified"] is True
    assert result["verified_models"] == ["claude-3-5-sonnet"]
    assert calls == [{"system": "Reply with OK.", "user": "OK", "max_tokens": 1}]


def test_ask_request_override_is_optional_and_conversation_turn_serving_metadata(tmp_path):
    assert server.AskRequest(session_id="s", text="hello").model_override is None
    assert server.AskRequest(session_id="s", text="hello", model_override={"provider_id": "openai", "model": "gpt-4o"}).model_override["model"] == "gpt-4o"
    turn = ConversationTurn("t", "now", "hello", "hi", serving_provider="openai", serving_model="gpt-4o")
    assert turn.to_dict()["serving_provider"] == "openai"
    store = ConversationHistoryStore(str(tmp_path))
    assert store.append_turn(session_id="s", turn_id="t", user_text="hello", response_text="hi")
    assert store.annotate_latest_turn("s", serving_provider="openai", serving_model="gpt-4o")
    assert store.get_session("s")[-1]["serving_model"] == "gpt-4o"
