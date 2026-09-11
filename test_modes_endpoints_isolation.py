"""M22.8 HTTP mode endpoints are authenticated and always self-scoped."""

import pytest
from fastapi.testclient import TestClient

from uri_core.app import edge, route_classification, server
from uri_core.core.auth_session import AuthSessionStore
from uri_core.core.user_accounts import UserAccountStore


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server, "_user_account_store", UserAccountStore(str(tmp_path / "accounts.json")))
    monkeypatch.setattr(server, "_auth_session_store", AuthSessionStore(storage_path=str(tmp_path / "sessions.json")))
    edge.reset_rate_limiters()
    client = TestClient(server.app)
    yield client
    client.close()
    edge.reset_rate_limiters()


def login(client, username):
    response = client.post("/auth/signup", json={"username": username, "password": "Password123!"})
    assert response.status_code == 200, response.text
    response = client.post("/auth/login", json={"username": username, "password": "Password123!"})
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    return {"Authorization": "Bearer " + token}, server._auth_session_store.resolve(token)


def test_modes_routes_are_user_classified():
    assert route_classification.ROUTE_CLASSIFICATION[("GET", "/modes")] == route_classification.USER
    assert route_classification.ROUTE_CLASSIFICATION[("PUT", "/modes")] == route_classification.USER


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_modes_require_authentication(client, headers):
    assert client.get("/modes", headers=headers).status_code == 401
    assert client.put("/modes", headers=headers, json={"mode": "office"}).status_code == 401


def test_modes_are_self_scoped_and_ignore_impersonation_fields(client):
    a, a_id = login(client, "modes_a")
    b, b_id = login(client, "modes_b")
    response = client.put("/modes?user_id=" + b_id, headers=a,
                          json={"mode": "diagnostic", "user_id": b_id})
    assert response.status_code == 200
    assert response.json()["mode"] == "diagnostic"
    assert client.get("/modes?user_id=" + b_id, headers=a).json()["mode"] == "diagnostic"
    assert client.get("/modes", headers=b).json()["mode"] == "office"
    assert server._user_account_store.get_by_user_id(a_id).mode == "diagnostic"
    assert server._user_account_store.get_by_user_id(b_id).mode == "office"


def test_invalid_mode_is_rejected(client):
    headers, _ = login(client, "modes_invalid")
    assert client.put("/modes", headers=headers, json={"mode": "unsafe"}).status_code == 422
