"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "testregister@example.com",
        "password": "StrongPassword123!",
        "full_name": "Test User",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "testregister@example.com"
    assert user_data["role"] == "user"

    # 2. Duplicate registration triggers 409
    dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "CONFLICT"

    # 3. Login with JSON payload
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username": "testregister@example.com", "password": "StrongPassword123!"},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

    # 4. Login with bad password triggers 401
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"username": "testregister@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "UNAUTHORIZED"

    # 5. Refresh token rotation
    ref_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # 6. Reusing old rotated refresh token fails (revoked)
    replay_ref = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay_ref.status_code == 401

    # 7. Logout revokes newest refresh token
    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout_res.status_code == 204

    # 8. Using logged-out refresh token fails
    after_logout_ref = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert after_logout_ref.status_code == 401
