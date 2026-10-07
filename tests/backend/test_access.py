import pytest
from conftest import sign_in


@pytest.mark.parametrize('user,item,status', [('alice',1,200),('alice',2,403),('bob',1,403),('bob',2,200),('admin',1,200),('admin',2,200)])
def test_role_and_ownership_matrix(api, user, item, status):
    client, _ = api
    response = client.get(f'/api/items/{item}', headers=sign_in(client,user))
    assert response.status_code == status
    if status == 403:
        assert 'name' not in response.json()


def test_unauthenticated_user_is_denied(api):
    client, _ = api
    assert client.get('/api/items/1').status_code == 401
