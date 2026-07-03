"""Budget enforcement tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_management.constants import DEFAULT_MONTHLY_CREDIT_LIMIT
from app.resource_management.exceptions import InsufficientCreditsError


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


async def _seed_member(session: AsyncSession) -> tuple[Workspace, User]:
    user = User(
        id=uuid4(),
        email=f"enforce-{uuid4().hex}@example.com",
        name="Enforcement Tester",
        password_hash="hashed",
    )
    workspace = Workspace(
        id=uuid4(),
        name="Enforcement WS",
        slug=f"enforce-{uuid4().hex[:12]}",
        owner_id=user.id,
    )
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
    )
    session.add_all([user, workspace, membership])
    await session.flush()
    return workspace, user


@pytest.mark.asyncio
async def test_has_available_credits(db_session: AsyncSession) -> None:
    workspace, user = await _seed_member(db_session)
    service = BudgetService(db_session)
    await service.create_workspace_budget_settings(workspace.id)
    await service.create_budget(workspace.id, user.id)

    assert await service.has_available_credits(workspace.id, user.id, Decimal("100")) is True
    assert await service.has_available_credits(workspace.id, user.id, Decimal("5000")) is True
    assert await service.has_available_credits(workspace.id, user.id, Decimal("5000.01")) is False


@pytest.mark.asyncio
async def test_consume_credits_fails_when_insufficient(
    db_session: AsyncSession,
) -> None:
    workspace, user = await _seed_member(db_session)
    service = BudgetService(db_session)
    await service.create_workspace_budget_settings(workspace.id)
    await service.create_budget(workspace.id, user.id)

    with pytest.raises(InsufficientCreditsError):
        await service.consume_credits(
            workspace_id=workspace.id,
            user_id=user.id,
            ai_request_id=uuid4(),
            amount=DEFAULT_MONTHLY_CREDIT_LIMIT + Decimal("0.01"),
        )


@pytest.mark.asyncio
async def test_consume_credits_deducts_balance(db_session: AsyncSession) -> None:
    workspace, user = await _seed_member(db_session)
    service = BudgetService(db_session)
    await service.create_workspace_budget_settings(workspace.id)
    await service.create_budget(workspace.id, user.id)

    from app.models.ai_request import AIRequest
    from app.models.conversation import Conversation
    from app.models.enums import AIRequestStatus, MessageRole
    from app.models.message import Message

    conversation = Conversation(
        id=uuid4(),
        workspace_id=workspace.id,
        owner_id=user.id,
        title="Test",
    )
    message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        author_id=user.id,
        role=MessageRole.USER,
        content="Hi",
    )
    ai_request = AIRequest(
        id=uuid4(),
        conversation_id=conversation.id,
        user_message_id=message.id,
        provider="anthropic",
        model="claude-sonnet-4",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
    )
    db_session.add_all([conversation, message, ai_request])
    await db_session.flush()

    await service.consume_credits(
        workspace_id=workspace.id,
        user_id=user.id,
        ai_request_id=ai_request.id,
        amount=Decimal("10.00"),
    )

    budget = await service.get_budget(workspace.id, user.id)
    assert budget.used_credits == Decimal("10.00")
    assert budget.remaining_credits == DEFAULT_MONTHLY_CREDIT_LIMIT - Decimal("10.00")
