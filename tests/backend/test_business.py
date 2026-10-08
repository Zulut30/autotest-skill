from tests.backend.conftest import sign_in


def test_create_reopen_and_list_preserve_domain_data(api):
    client, _ = api
    headers = sign_in(client)
    create = client.post("/api/items", headers=headers, json={"name": "Saved work", "quantity": 3})
    assert create.status_code == 201
    saved = create.json()
    assert saved["owner"] == "alice"
    assert saved["quantity"] == 3
    reopened = client.get(f"/api/items/{saved['id']}", headers=headers)
    assert reopened.json() == saved
    assert saved in client.get("/api/items", headers=headers).json()["items"]
    assert saved not in client.get("/api/items", headers=sign_in(client, "bob")).json()["items"]
