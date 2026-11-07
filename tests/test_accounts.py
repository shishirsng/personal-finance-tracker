"""Tests for Account CRUD, sorting, pagination, and ownership enforcement."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_account_crud_and_ownership(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
    auth_headers_user_b: dict[str, str],
):
    # 1. User A creates account
    res = await client.post(
        "/api/v1/accounts",
        headers=auth_headers_user_a,
        json={"name": "Alice Checking", "type": "checking", "currency": "USD"},
    )
    assert res.status_code == 201
    acc_a = res.json()
    acc_id = acc_a["id"]
    assert acc_a["name"] == "Alice Checking"

    # 2. User A retrieves account
    get_res = await client.get(f"/api/v1/accounts/{acc_id}", headers=auth_headers_user_a)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == acc_id

    # 3. User B attempts to access User A's account -> MUST return 404 (ownership / no existence leak)
    foreign_get = await client.get(f"/api/v1/accounts/{acc_id}", headers=auth_headers_user_b)
    assert foreign_get.status_code == 404
    assert foreign_get.json()["error"]["code"] == "NOT_FOUND"

    # 4. User B attempts to modify User A's account -> 404
    foreign_patch = await client.patch(
        f"/api/v1/accounts/{acc_id}",
        headers=auth_headers_user_b,
        json={"name": "Hacked Name"},
    )
    assert foreign_patch.status_code == 404

    # 5. User A updates account
    patch_res = await client.patch(
        f"/api/v1/accounts/{acc_id}",
        headers=auth_headers_user_a,
        json={"name": "Alice Primary Checking"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Alice Primary Checking"

    # 6. User A lists accounts (pagination & sorting)
    list_res = await client.get(
        "/api/v1/accounts?limit=10&offset=0&sort_by=name&sort_order=asc",
        headers=auth_headers_user_a,
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert any(item["id"] == acc_id for item in data["items"])

    # 7. User A deletes account
    del_res = await client.delete(f"/api/v1/accounts/{acc_id}", headers=auth_headers_user_a)
    assert del_res.status_code == 204

    # 8. Subsequent get returns 404
    after_del = await client.get(f"/api/v1/accounts/{acc_id}", headers=auth_headers_user_a)
    assert after_del.status_code == 404
