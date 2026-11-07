"""Tests for Admin role gating and user management."""
import pytest
from httpx import AsyncClient
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_endpoints(
    client: AsyncClient,
    auth_headers_user_a: dict[str, str],
    auth_headers_admin: dict[str, str],
    user_a: User,
):
    # 1. Non-admin accessing admin route is forbidden (403)
    non_admin_res = await client.get("/api/v1/admin/users", headers=auth_headers_user_a)
    assert non_admin_res.status_code == 403
    assert non_admin_res.json()["error"]["code"] == "FORBIDDEN"

    # 2. Admin successfully lists users
    admin_res = await client.get("/api/v1/admin/users", headers=auth_headers_admin)
    assert admin_res.status_code == 200
    data = admin_res.json()
    assert data["total"] >= 2

    # 3. Admin updates user role
    patch_role = await client.patch(
        f"/api/v1/admin/users/{user_a.id}/role",
        headers=auth_headers_admin,
        json={"role": "admin"},
    )
    assert patch_role.status_code == 200
    assert patch_role.json()["role"] == "admin"
