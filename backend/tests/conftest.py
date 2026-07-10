"""Shared pytest fixtures and helpers for API integration tests."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.db.session import create_engine
from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/convhub_test"
)
_PROTECTED_DATABASE_NAMES = frozenset({"convhub", "postgres"})


def _rewrite_database_name(database_url: str, database_name: str) -> str:
    return make_url(database_url).set(database=database_name).render_as_string(
        hide_password=False
    )


def _database_name(database_url: str) -> str:
    return make_url(database_url).database or ""


def _resolve_test_database_url() -> str:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]

    env_path = BACKEND_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                base = line.split("=", 1)[1].strip().strip('"').strip("'")
                return _rewrite_database_name(base, "convhub_test")
    return _DEFAULT_TEST_DATABASE_URL


def _ensure_test_database(database_url: str) -> None:
    """Create the test database if missing, then apply migrations."""
    db_name = _database_name(database_url)
    if not db_name:
        raise RuntimeError("TEST_DATABASE_URL must include a database name")
    if db_name in _PROTECTED_DATABASE_NAMES:
        raise RuntimeError(
            f"Refusing to run tests against protected database '{db_name}'. "
            "Set TEST_DATABASE_URL to a dedicated database such as convhub_test."
        )

    admin_url = make_url(database_url).set(database="postgres")
    # Use a temporary Settings-like object for the admin connection.
    from app.core.config import Settings

    admin_settings = Settings(database_url=admin_url.render_as_string(hide_password=False))
    admin_settings = admin_settings.model_copy(update={"debug": False})

    import asyncio

    async def _create_if_missing() -> None:
        engine = create_engine(admin_settings)
        try:
            async with engine.connect() as conn:
                conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
                exists = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": db_name},
                )
                if exists.scalar_one_or_none() is None:
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        finally:
            await engine.dispose()

    asyncio.run(_create_if_missing())

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to migrate test database:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.fixture(scope="session", autouse=True)
def _configure_test_database() -> None:
    """Point the entire test session at a dedicated database."""
    test_url = _resolve_test_database_url()
    db_name = _database_name(test_url)
    if db_name in _PROTECTED_DATABASE_NAMES:
        raise RuntimeError(
            f"Refusing to run tests against protected database '{db_name}'. "
            "Set TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/convhub_test"
        )

    os.environ["DATABASE_URL"] = test_url
    os.environ["TEST_DATABASE_URL"] = test_url
    get_settings.cache_clear()
    _ensure_test_database(test_url)
    get_settings.cache_clear()


async def _truncate_all_tables() -> None:
    settings = get_settings()
    db_name = _database_name(settings.sqlalchemy_database_uri)
    if db_name in _PROTECTED_DATABASE_NAMES:
        raise RuntimeError(
            f"Refusing to truncate protected database '{db_name}'. "
            "Tests must use convhub_test (or another dedicated TEST_DATABASE_URL)."
        )

    engine = create_engine(settings)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename != 'alembic_version'
                    """
                )
            )
            table_names = ", ".join(f'"{row[0]}"' for row in result.fetchall())
            if table_names:
                await conn.execute(
                    text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
                )
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def reset_runtime_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset env-backed settings and realtime singletons before each test."""
    test_url = os.environ.get("TEST_DATABASE_URL") or _resolve_test_database_url()
    monkeypatch.setenv("DATABASE_URL", test_url)
    monkeypatch.setenv("TEST_DATABASE_URL", test_url)
    monkeypatch.setenv("ENABLE_DEMO_MODE", "false")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    get_settings.cache_clear()

    from app.realtime.manager import WebSocketManager, set_ws_manager

    set_ws_manager(WebSocketManager())

    yield

    set_ws_manager(None)
    get_settings.cache_clear()


@dataclass
class AuthContext:
    token: str
    user_id: str
    email: str
    name: str
    headers: dict[str, str]


@dataclass
class WorkspaceContext:
    workspace_id: str
    headers: dict[str, str]
    auth: AuthContext


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    await _truncate_all_tables()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver/api/v1"
        ) as http_client:
            yield http_client


async def register_user(
    client: AsyncClient,
    *,
    name: str | None = None,
    email: str | None = None,
    password: str = "password123",
) -> AuthContext:
    email = email or f"user-{uuid4().hex}@example.com"
    name = name or "Test User"
    response = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    login = await client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return AuthContext(
        token=token,
        user_id=user_id,
        email=email,
        name=name,
        headers={"Authorization": f"Bearer {token}"},
    )


async def create_workspace(
    client: AsyncClient,
    auth: AuthContext,
    *,
    name: str | None = None,
) -> WorkspaceContext:
    response = await client.post(
        "/workspaces",
        headers=auth.headers,
        json={"name": name or f"Workspace {uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    workspace_id = response.json()["id"]
    headers = {
        **auth.headers,
        "X-Workspace-ID": workspace_id,
    }
    return WorkspaceContext(workspace_id=workspace_id, headers=headers, auth=auth)


async def invite_and_accept(
    client: AsyncClient,
    workspace: WorkspaceContext,
    invitee: AuthContext,
    *,
    role: str = "member",
) -> None:
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": invitee.email, "role": role},
    )
    assert invite.status_code == 201, invite.text
    accept = await client.post(
        f"/invitations/{invite.json()['token']}/accept",
        headers=invitee.headers,
    )
    assert accept.status_code == 200, accept.text


@pytest.fixture
async def auth_user(client: AsyncClient) -> AuthContext:
    return await register_user(client)


@pytest.fixture
async def workspace(client: AsyncClient, auth_user: AuthContext) -> WorkspaceContext:
    return await create_workspace(client, auth_user)


@pytest.fixture
async def second_user(client: AsyncClient) -> AuthContext:
    return await register_user(client, name="Second User")


@pytest.fixture
async def member_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> tuple[WorkspaceContext, AuthContext]:
    await invite_and_accept(client, workspace, second_user)
    member_headers = {
        **second_user.headers,
        "X-Workspace-ID": workspace.workspace_id,
    }
    return workspace, AuthContext(
        token=second_user.token,
        user_id=second_user.user_id,
        email=second_user.email,
        name=second_user.name,
        headers=member_headers,
    )
