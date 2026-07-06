"""Execution summary and invitation polish tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.conversations.execution import (
    build_execution_summary,
    load_execution_summaries,
)
from app.core.config import get_settings
from app.main import app
from app.models.ai_account import AIAccount
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.enums import AIRequestStatus, ExecutionType, RoutingPolicyType
from app.models.message import Message
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace


@pytest.fixture
async def client() -> AsyncClient:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver/api/v1"
        ) as http_client:
            yield http_client


@pytest.fixture
async def db_session() -> AsyncSession:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_uri)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()

    await engine.dispose()


def test_build_execution_summary_own_account() -> None:
    owner_id = uuid4()
    account = AIAccount(
        id=uuid4(),
        workspace_id=uuid4(),
        owner_user_id=owner_id,
        provider="anthropic",
        display_name="Alice's Account",
        encrypted_credentials="enc",
    )
    request = AIRequest(
        conversation_id=uuid4(),
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
        routing_policy=RoutingPolicyType.BALANCED,
    )

    summary = build_execution_summary(
        request,
        account,
        sender_user_id=owner_id,
        owner_names={owner_id: "Alice"},
    )
    assert summary.execution_type == ExecutionType.OWN_PROVIDER
    assert summary.owner_name == "Alice"
    assert summary.routing_policy == RoutingPolicyType.BALANCED


def test_build_execution_summary_borrowed() -> None:
    request = AIRequest(
        conversation_id=uuid4(),
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
        routing_policy=RoutingPolicyType.OWNER_FIRST,
    )

    summary = build_execution_summary(request, None, lender_name="Bob")
    assert summary.execution_type == ExecutionType.BORROWED_PROVIDER
    assert summary.borrowed_from == "Bob"


def test_build_execution_summary_local_model() -> None:
    request = AIRequest(
        conversation_id=uuid4(),
        provider="ollama",
        model="llama3.2",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
        routing_policy=RoutingPolicyType.CHEAPEST,
    )

    summary = build_execution_summary(request, None)
    assert summary.execution_type == ExecutionType.LOCAL_MODEL


@pytest.mark.asyncio
async def test_load_execution_summaries(db_session: AsyncSession) -> None:
    user = User(
        id=uuid4(),
        email=f"exec-{uuid4().hex}@example.com",
        name="Exec User",
        password_hash="hashed",
    )
    workspace = Workspace(
        id=uuid4(),
        name="Exec WS",
        slug=f"exec-{uuid4().hex[:12]}",
        owner_id=user.id,
    )
    project = Project(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Default Project",
        created_by_id=user.id,
    )
    conversation = Conversation(
        id=uuid4(),
        workspace_id=workspace.id,
        project_id=project.id,
        owner_id=user.id,
        title="Exec Test",
        last_activity_at=datetime.now(UTC),
    )
    user_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        author_id=user.id,
        role="user",
        content="Hi",
    )
    assistant = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        author_id=None,
        role="assistant",
        content="Hello",
    )
    account = AIAccount(
        id=uuid4(),
        workspace_id=workspace.id,
        owner_user_id=user.id,
        provider="mock",
        display_name="Demo Account",
        encrypted_credentials="enc",
    )
    ai_request = AIRequest(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant.id,
        provider="mock",
        model="mock",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        selected_account_id=account.id,
        routing_policy=RoutingPolicyType.OWNER_FIRST,
    )
    db_session.add_all(
        [user, workspace, project, conversation, user_message, assistant, account, ai_request]
    )
    await db_session.flush()

    summaries = await load_execution_summaries(db_session, [assistant.id])
    assert assistant.id in summaries
    assert summaries[assistant.id].execution_type == ExecutionType.OWN_PROVIDER
    assert summaries[assistant.id].owner_name == "Exec User"


@pytest.mark.asyncio
async def test_invitation_preview(client: AsyncClient) -> None:
    email = f"preview-{uuid4().hex}@example.com"
    password = "password123"
    await client.post(
        "/auth/register",
        json={"name": "Preview Host", "email": email, "password": password},
    )
    login = await client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    workspace = await client.post("/workspaces", headers=headers, json={"name": "Preview WS"})
    workspace_id = workspace.json()["id"]
    headers["X-Workspace-ID"] = workspace_id

    invite = await client.post(
        f"/workspaces/{workspace_id}/invite",
        headers=headers,
        json={"email": f"guest-{uuid4().hex}@example.com", "role": "member"},
    )
    invite_token = invite.json()["token"]

    preview = await client.get(f"/invitations/{invite_token}")
    assert preview.status_code == 200
    body = preview.json()
    assert body["workspace_name"] == "Preview WS"
    assert body["is_valid"] is True

    pending = await client.get(f"/workspaces/{workspace_id}/invitations", headers=headers)
    assert pending.status_code == 200
    assert len(pending.json()) == 1
