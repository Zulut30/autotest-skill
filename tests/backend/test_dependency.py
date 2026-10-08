from tests.backend.conftest import sign_in


def test_dependency_failure_is_honest_and_recoverable(api):
    client, _ = api
    admin = sign_in(client, "admin")
    assert (
        client.post("/__test/dependency", headers=sign_in(client), json={"down": True}).status_code
        == 403
    )
    assert client.get("/api/dependent").status_code == 200
    assert client.post("/__test/dependency", headers=admin, json={"down": True}).status_code == 200
    assert client.get("/api/dependent").status_code == 503
    assert client.get("/api/dependent").json()["available"] is False
    client.post("/__test/dependency", headers=admin, json={"down": False})
    assert client.get("/api/dependent").json()["available"] is True
