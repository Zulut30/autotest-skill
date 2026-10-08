from tests.backend.conftest import sign_in


def test_login_failure_logout_and_revoked_session(api):
    client, _ = api
    assert (
        client.post("/api/login", json={"username": "alice", "password": "wrong"}).status_code
        == 401
    )
    headers = sign_in(client)
    assert client.get("/api/me", headers=headers).json()["username"] == "alice"
    assert client.post("/api/logout", json={}, headers=headers).status_code == 204
    assert client.get("/api/me", headers=headers).status_code == 401


def test_expired_session_is_denied(api):
    client, state = api
    headers = sign_in(client)
    for record in state.sessions.values():
        record["expires"] = 0
    assert client.get("/api/me", headers=headers).status_code == 401
