from conftest import sign_in


def test_explicit_reset_makes_repeated_flows_independent(api):
    client, state = api
    for _ in range(3):
        headers = sign_in(client)
        response = client.post('/api/items',headers=headers,json={'name':'Repeatable','quantity':1})
        assert response.json()['id'] == 3
        assert len(state.items) == 3
        admin = sign_in(client,'admin')
        assert client.post('/__test/reset',headers=admin,json={}).json()['reset'] is True
        assert len(state.items) == 2
        assert client.get('/api/me',headers=headers).status_code == 401
