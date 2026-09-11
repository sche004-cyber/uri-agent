"""Real bearer sessions scope usage and ceiling HTTP requests to the caller."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from test_usage_meter_recording import record
from uri_core.app import edge, route_classification, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import UserAccountStore
from uri_core.core.usage_meter import UsageMeter


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server, "_user_account_store", UserAccountStore(storage_path=str(tmp_path / "accounts.json")))
    monkeypatch.setattr(server, "_auth_session_store", AuthSessionStore(storage_path=str(tmp_path / "sessions.json")))
    monkeypatch.setattr(server, "_user_contexts", {})
    edge.reset_rate_limiters()
    client = TestClient(server.app)
    yield client
    client.close()
    edge.reset_rate_limiters()


def login(client, username):
    edge.reset_rate_limiters()
    response = client.post("/auth/signup", json={"username": username, "password": "Password123!"})
    assert response.status_code == 200, response.text
    response = client.post("/auth/login", json={"username": username, "password": "Password123!"})
    assert response.status_code == 200, response.text
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    uid = server._auth_session_store.resolve(response.json()["token"])
    return headers, uid


def test_routes_classified_user():
    for route in (("GET", "/usage"), ("GET", "/usage/limits"), ("PUT", "/usage/limits")):
        assert route_classification.ROUTE_CLASSIFICATION[route] == route_classification.USER


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_auth_required(client, headers):
    assert client.get("/usage", headers=headers).status_code == 401
    assert client.get("/usage/limits", headers=headers).status_code == 401
    assert client.put("/usage/limits", headers=headers, json={"monthly_token_ceiling": 100}).status_code == 401


def test_http_isolation_and_zero_model_calls(client, monkeypatch):
    a, aid = login(client, "usage_a")  # first user is ADMIN, still self-scoped
    b, bid = login(client, "usage_b")
    UsageMeter().record(record(user_id=aid))
    UsageMeter().record(record(user_id=bid, prompt=900, output=100))
    forbidden = Mock(side_effect=AssertionError("usage endpoint invoked model"))
    monkeypatch.setattr("uri_core.core.model_router.ModelRouter.attempt", forbidden)
    monkeypatch.setattr("uri_core.config.model_roles.build_provider", forbidden)
    assert client.get("/usage/limits", headers=a).json() == {"monthly_token_ceiling": None, "warn_threshold_ratio": 0.8}
    assert client.put("/usage/limits", headers=b, json={"monthly_token_ceiling": 1000}).status_code == 200
    assert client.put("/usage/limits", headers=a, json={"monthly_token_ceiling": 35, "user_id": bid}).status_code == 200
    dashboard = client.get("/usage?user_id=" + bid, headers=a).json()
    assert dashboard["totals"]["known_total_tokens"] == 30
    assert dashboard["limits"]["monthly_token_ceiling"] == 35
    assert dashboard["limits"]["warning"] and not dashboard["limits"]["ceiling_reached"]
    assert client.get("/usage", headers=b).json()["totals"]["known_total_tokens"] == 1000
    assert client.get("/usage/limits", headers=b).json()["monthly_token_ceiling"] == 1000
    assert client.put("/usage/limits", headers=a, json={"monthly_token_ceiling": None}).status_code == 200
    assert client.get("/usage/limits", headers=a).json()["monthly_token_ceiling"] is None
    forbidden.assert_not_called()


@pytest.mark.parametrize("body", [{}, {"monthly_token_ceiling": -1}, {"monthly_token_ceiling": True},
                                  {"monthly_token_ceiling": 1.5}, {"monthly_token_ceiling": "100"}])
def test_invalid_limit_rejected_without_update(client, body):
    headers, _ = login(client, "limits_user")
    assert client.put("/usage/limits", headers=headers, json=body).status_code == 422
    assert client.get("/usage/limits", headers=headers).json()["monthly_token_ceiling"] is None
