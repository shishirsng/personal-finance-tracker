"""Tests for Reports with Redis cache hit and invalidation."""
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from redis.asyncio import Redis


@pytest.mark.asyncio
async def test_monthly_summary_cache_and_invalidation(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
    fake_redis: Redis,
):
    # Setup account & category
    acc_res = await client.post(
        "/api/v1/accounts",
        headers=auth_headers_user_a,
        json={"name": "Report Account", "type": "checking", "currency": "USD"},
    )
    acc_id = acc_res.json()["id"]

    cat_res = await client.post(
        "/api/v1/categories",
        headers=auth_headers_user_a,
        json={"name": "Bonus", "kind": "income"},
    )
    cat_id = cat_res.json()["id"]

    # 1. Post initial income transaction
    tx_time = datetime(2026, 11, 5, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    await client.post(
        "/api/v1/transactions",
        headers=auth_headers_user_a,
        json={
            "account_id": acc_id,
            "category_id": cat_id,
            "amount": "2000.00",
            "direction": "income",
            "occurred_at": tx_time,
        },
    )

    # 2. Request monthly summary (cache miss -> cached in Redis)
    res1 = await client.get("/api/v1/reports/monthly-summary?month=2026-11", headers=auth_headers_user_a)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_income"] == "2000.00"
    assert data1["total_expense"] == "0.00"
    assert data1["net_savings"] == "2000.00"

    # Verify Redis key exists
    keys = await fake_redis.keys("cache:reports:monthly-summary:*")
    assert len(keys) == 1

    # 3. Add expense transaction -> must invalidate Redis cache
    tx_time2 = datetime(2026, 11, 6, 14, 0, 0, tzinfo=timezone.utc).isoformat()
    await client.post(
        "/api/v1/transactions",
        headers=auth_headers_user_a,
        json={
            "account_id": acc_id,
            "category_id": None,
            "amount": "500.00",
            "direction": "expense",
            "occurred_at": tx_time2,
        },
    )

    # 4. Request summary again -> must reflect new totals
    res2 = await client.get("/api/v1/reports/monthly-summary?month=2026-11", headers=auth_headers_user_a)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_income"] == "2000.00"
    assert data2["total_expense"] == "500.00"
    assert data2["net_savings"] == "1500.00"
    assert data2["savings_rate"] == "75.00"

    # 5. Category breakdown
    breakdown_res = await client.get(
        "/api/v1/reports/category-breakdown?month=2026-11&direction=income",
        headers=auth_headers_user_a,
    )
    assert breakdown_res.status_code == 200
    assert breakdown_res.json()["total_amount"] == "2000.00"

    # 6. Budget vs Actual report
    bva_res = await client.get("/api/v1/reports/budget-vs-actual?month=2026-11", headers=auth_headers_user_a)
    assert bva_res.status_code == 200
    assert "items" in bva_res.json()
