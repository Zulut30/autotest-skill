import httpx

from autotest_skill.demo import start_demo


def test_fixture_has_isolated_users_and_real_state():
    with start_demo() as (base, state):
        assert httpx.get(base + "/health").json()["ready"] is True
        auth = httpx.post(
            base + "/api/login", json={"username": "alice", "password": "demo-password"}
        ).json()["authorization"]
        assert (
            httpx.get(base + "/api/me", headers={"Authorization": auth}).json()["username"]
            == "alice"
        )
        assert httpx.get(base + "/api/items/2", headers={"Authorization": auth}).status_code == 403
        assert (
            httpx.post(
                base + "/api/items",
                headers={"Authorization": auth},
                json={"name": "New", "quantity": 2},
            ).status_code
            == 201
        )
        assert len(state.items) == 3
    with start_demo() as (_, state):
        assert len(state.items) == 2
