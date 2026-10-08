import pytest
from conftest import sign_in


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "", "quantity": 1},
        {"name": " ", "quantity": 1},
        {"name": "x" * 101, "quantity": 1},
        {"name": "x", "quantity": 0},
        {"name": "x", "quantity": -1},
        {"name": "x", "quantity": 101},
        {"name": "x", "quantity": True},
        {"name": "x", "quantity": "2"},
    ],
)
def test_invalid_and_boundary_inputs_do_not_change_state(api, body):
    client, state = api
    before = dict(state.items)
    assert client.post("/api/items", json=body, headers=sign_in(client)).status_code == 422
    assert state.items == before
