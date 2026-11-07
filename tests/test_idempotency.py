"""Tests for Idempotency-Key support and conflict detection."""
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transaction_idempotency(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
):
    # Setup account
    acc_res = await client.post(
        "/api/v1/accounts",
        headers=auth_headers_user_a,
        json={"name": "Idempotent Account", "type": "checking", "currency": "USD"},
    )
    acc_id = acc_res.json()["id"]

    idempotency_key = "unique-test-key-12345"
    tx_time = datetime(2026, 11, 2, 9, 0, 0, tzinfo=timezone.utc).isoformat()
    original_payload = {
        "account_id": acc_id,
        "category_id": None,
        "amount": "99.99",
        "direction": "expense",
        "description": "Original Purchase",
        "occurred_at": tx_time,
    }

    headers = {**auth_headers_user_a, "Idempotency-Key": idempotency_key}

    # 1. First execution
    res1 = await client.post("/api/v1/transactions", headers=headers, json=original_payload)
    assert res1.status_code == 201
    tx1 = res1.json()

    # 2. Replay with identical payload returns cached original response
    res2 = await client.post("/api/v1/transactions", headers=headers, json=original_payload)
    assert res2.status_code == 201
    tx2 = res2.json()
    assert tx1["id"] == tx2["id"]
    assert tx1["amount"] == tx2["amount"]

    # 3. Replay with modified payload under same key triggers 409 Conflict
    mutated_payload = {**original_payload, "amount": "199.99"}
    res3 = await client.post("/api/v1/transactions", headers=headers, json=mutated_payload)
    assert res3.status_code == 409
    assert res3.json()["error"]["code"] == "CONFLICT"
