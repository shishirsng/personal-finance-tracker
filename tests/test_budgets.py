"""Tests for Budget upsert and retrieval."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_budget_upsert_and_ownership(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
    auth_headers_user_b: dict[str, str],
):
    # Setup category
    cat_res = await client.post(
        "/api/v1/categories",
        headers=auth_headers_user_a,
        json={"name": "Utilities", "kind": "expense"},
    )
    cat_id = cat_res.json()["id"]

    # 1. Upsert budget
    b1_res = await client.put(
        f"/api/v1/budgets/{cat_id}?month=2026-11",
        headers=auth_headers_user_a,
        json={"amount": "150.00"},
    )
    assert b1_res.status_code == 200
    b1 = b1_res.json()
    assert b1["amount"] == "150.00"
    assert b1["month"] == "2026-11"

    # 2. Upsert same category and month updates existing amount
    b2_res = await client.put(
        f"/api/v1/budgets/{cat_id}?month=2026-11",
        headers=auth_headers_user_a,
        json={"amount": "180.00"},
    )
    assert b2_res.status_code == 200
    assert b2_res.json()["amount"] == "180.00"
    assert b2_res.json()["id"] == b1["id"]

    # 3. List monthly budgets
    list_res = await client.get("/api/v1/budgets?month=2026-11", headers=auth_headers_user_a)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. User B cannot budget User A's category -> 404
    foreign_budget = await client.put(
        f"/api/v1/budgets/{cat_id}?month=2026-11",
        headers=auth_headers_user_b,
        json={"amount": "500.00"},
    )
    assert foreign_budget.status_code == 404
