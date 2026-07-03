"""Authentication and user endpoint QA tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import register_user


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app_name" in body


@pytest.mark.asyncio
async def test_register_login_and_me_happy_path(client: AsyncClient) -> None:
    auth = await register_user(client, name="Auth QA", email=f"auth-{uuid4().hex}@example.com")
    me = await client.get("/users/me", headers=auth.headers)
    assert me.status_code == 200
    assert me.json()["email"] == auth.email
    assert me.json()["name"] == "Auth QA"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    email = f"dup-{uuid4().hex}@example.com"
    first = await client.post(
        "/auth/register",
        json={"name": "First", "email": email, "password": "password123"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/auth/register",
        json={"name": "Second", "email": email, "password": "password123"},
    )
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"name": "Bad Email", "email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "name": "Short PW",
            "email": f"short-{uuid4().hex}@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client: AsyncClient) -> None:
    auth = await register_user(client)
    response = await client.post(
        "/auth/login",
        json={"email": auth.email, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_me_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_happy_path(client: AsyncClient) -> None:
    auth = await register_user(client)
    login = await client.post(
        "/auth/login",
        json={"email": auth.email, "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert refreshed.json()["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh", json={"refresh_token": "invalid"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    auth = await register_user(client)
    login = await client.post(
        "/auth/login",
        json={"email": auth.email, "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    logout = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    refresh = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_register_does_not_allow_login_with_first_password_only(
    client: AsyncClient,
) -> None:
    """Regression: duplicate registration must not leave ambiguous auth state."""
    email = f"race-{uuid4().hex}@example.com"
    await client.post(
        "/auth/register",
        json={"name": "Original", "email": email, "password": "password123"},
    )
    dup = await client.post(
        "/auth/register",
        json={"name": "Duplicate", "email": email, "password": "otherpass99"},
    )
    assert dup.status_code == 409

    ok = await client.post("/auth/login", json={"email": email, "password": "password123"})
    bad = await client.post("/auth/login", json={"email": email, "password": "otherpass99"})
    assert ok.status_code == 200
    assert bad.status_code == 401
