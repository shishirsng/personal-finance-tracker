"""Tests for Transaction management, filtering, and account activity updates."""
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transaction_crud_and_activity(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
    auth_headers_user_b: dict[str, str],
):
    # Setup account & category
    acc_res = await client.post(
        "/api/v1/accounts",
        headers=auth_headers_user_a,
        json={"name": "Checking for Tx", "type": "checking", "currency": "USD"},
    )
    acc_id = acc_res.json()["id"]

    cat_res = await client.post(
        "/api/v1/categories",
        headers=auth_headers_user_a,
        json={"name": "Dining", "kind": "expense"},
    )
    cat_id = cat_res.json()["id"]

    # 1. Create transaction
    tx_time = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    tx_payload = {
        "account_id": acc_id,
        "category_id": cat_id,
        "amount": "45.50",
        "direction": "expense",
        "description": "Lunch with team",
        "occurred_at": tx_time,
    }
    res = await client.post("/api/v1/transactions", headers=auth_headers_user_a, json=tx_payload)
    assert res.status_code == 201
    tx = res.json()
    assert tx["amount"] == "45.50"
    assert tx["category"]["name"] == "Dining"

    # 2. Account last_activity_at must be updated and is_stale False
    acc_check = await client.get(f"/api/v1/accounts/{acc_id}", headers=auth_headers_user_a)
    assert acc_check.json()["is_stale"] is False
    assert acc_check.json()["last_activity_at"] is not None

    # 3. Ownership enforcement: User B cannot read User A's transaction -> 404
    foreign_get = await client.get(f"/api/v1/transactions/{tx['id']}", headers=auth_headers_user_b)
    assert foreign_get.status_code == 404

    # 4. Filter transactions
    filter_res = await client.get(
        f"/api/v1/transactions?account_id={acc_id}&direction=expense&sort_by=amount&sort_order=desc",
        headers=auth_headers_user_a,
    )
    assert filter_res.status_code == 200
    assert filter_res.json()["total"] >= 1
