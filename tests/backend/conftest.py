import httpx
import pytest

from autotest_skill.demo import start_demo


@pytest.fixture
def api():
    with start_demo() as (base, state), httpx.Client(base_url=base) as client:
        yield client, state


def sign_in(client, user="alice"):
    response = client.post("/api/login", json={"username": user, "password": "demo-password"})
    assert response.status_code == 200
    return {"Authorization": response.json()["authorization"]}
