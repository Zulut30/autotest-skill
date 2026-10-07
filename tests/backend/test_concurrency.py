from concurrent.futures import ThreadPoolExecutor
from conftest import sign_in


def test_concurrent_duplicates_create_one_item_and_conflicts_are_rejected(api):
    client, state = api
    headers = {**sign_in(client), 'Idempotency-Key':'fixture-request-1'}
    def create(_):
        return client.post('/api/items',headers=headers,json={'name':'One item','quantity':1})
    with ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(pool.map(create,range(10)))
    assert all(r.status_code in {200,201} for r in responses)
    assert len({r.json()['id'] for r in responses}) == 1
    assert sum(r.status_code == 201 for r in responses) == 1
    assert len(state.items) == 3
    assert client.post('/api/items',headers=headers,json={'name':'Different','quantity':1}).status_code == 409
