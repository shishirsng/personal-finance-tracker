"""Tests for Category endpoints and ownership enforcement."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_category_management(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
    auth_headers_user_b: dict[str, str],
):
    # 1. Create income and expense categories
    c1_res = await client.post(
        "/api/v1/categories",
        headers=auth_headers_user_a,
        json={"name": "Salary", "kind": "income", "color": "#2ECC71"},
    )
    assert c1_res.status_code == 201
    c1 = c1_res.json()

    c2_res = await client.post(
        "/api/v1/categories",
        headers=auth_headers_user_a,
        json={"name": "Groceries", "kind": "expense", "color": "#E74C3C"},
    )
    assert c2_res.status_code == 201
    c2 = c2_res.json()

    # 2. Filter categories by kind
    filtered = await client.get("/api/v1/categories?kind=income", headers=auth_headers_user_a)
    assert filtered.status_code == 200
    income_items = filtered.json()
    assert all(item["kind"] == "income" for item in income_items)

    # 3. Duplicate category under same user and kind returns 409 Conflict
    dup_res = await client.post(
        "/api/v1/categories",
        headers=auth_headers_user_a,
        json={"name": "Salary", "kind": "income"},
    )
    assert dup_res.status_code == 409

    # 4. User B cannot delete User A's category -> 404
    foreign_del = await client.delete(f"/api/v1/categories/{c2['id']}", headers=auth_headers_user_b)
    assert foreign_del.status_code == 404

    # 5. User A deletes category
    del_res = await client.delete(f"/api/v1/categories/{c2['id']}", headers=auth_headers_user_a)
    assert del_res.status_code == 204
