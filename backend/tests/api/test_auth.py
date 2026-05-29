import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test.com",
            "username": "newuser",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@test.com",
            "username": "user2",
            "password": "weakpassword",  # 大文字・数字なし
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # まず登録
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logintest@test.com",
            "username": "logintest",
            "password": "LoginTest123",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "logintest@test.com", "password": "LoginTest123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong@test.com",
            "username": "wrongtest",
            "password": "Correct123",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@test.com", "password": "WrongPass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@test.com",
            "username": "metest",
            "password": "MeTest123",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@test.com", "password": "MeTest123"},
    )
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "me@test.com"
