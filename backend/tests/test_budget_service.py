"""Integration tests for budget and ledger accounting."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.credit_transaction import CreditTransaction
from app.models.enums import (
    AIRequestStatus,
    CreditTransactionType,
    MessageRole,
    WorkspaceRole,
)
from app.models.message import Message
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_management.constants import DEFAULT_MONTHLY_CREDIT_LIMIT
from app.resource_management.credit_calculator import calculate_credits


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


async def _seed_workspace_member(session: AsyncSession) -> tuple[Workspace, User]:
    user = User(
        id=uuid4(),
        email=f"budget-{uuid4().hex}@example.com",
        name="Budget Tester",
        password_hash="hashed",
    )
    workspace = Workspace(
        id=uuid4(),
        name="Budget Workspace",
        slug=f"budget-{uuid4().hex[:12]}",
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
async def test_create_budget_allocates_default_credits(
    db_session: AsyncSession,
) -> None:
    workspace, user = await _seed_workspace_member(db_session)
    service = BudgetService(db_session)

    budget = await service.create_budget(workspace.id, user.id)

    assert budget.monthly_credit_limit == DEFAULT_MONTHLY_CREDIT_LIMIT
    assert budget.remaining_credits == DEFAULT_MONTHLY_CREDIT_LIMIT
    assert budget.used_credits == Decimal("0")

    tx_result = await db_session.execute(
        select(CreditTransaction).where(
            CreditTransaction.workspace_id == workspace.id,
            CreditTransaction.to_user_id == user.id,
            CreditTransaction.transaction_type == CreditTransactionType.ALLOCATION,
        )
    )
    assert tx_result.scalar_one().amount == DEFAULT_MONTHLY_CREDIT_LIMIT


@pytest.mark.asyncio
async def test_record_usage_updates_budget_and_ledger(db_session: AsyncSession) -> None:
    workspace, user = await _seed_workspace_member(db_session)
    service = BudgetService(db_session)
    await service.create_budget(workspace.id, user.id)

    conversation = Conversation(
        id=uuid4(),
        workspace_id=workspace.id,
        owner_id=user.id,
        title="Budget Test",
    )
    user_message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        author_id=user.id,
        role=MessageRole.USER,
        content="Hello",
    )
    ai_request = AIRequest(
        id=uuid4(),
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        provider="anthropic",
        model="claude-sonnet-4",
        status=AIRequestStatus.COMPLETED,
        started_at=datetime.now(UTC),
        input_tokens=600,
        output_tokens=400,
    )
    db_session.add_all([conversation, user_message, ai_request])
    await db_session.flush()

    credits = calculate_credits(ai_request)
    await service.record_usage(
        workspace_id=workspace.id,
        user_id=user.id,
        ai_request_id=ai_request.id,
        amount=credits,
    )

    budget = await service.get_budget(workspace.id, user.id)
    assert budget.used_credits == Decimal("1.00")
    assert budget.remaining_credits == DEFAULT_MONTHLY_CREDIT_LIMIT - Decimal("1.00")

    tx_result = await db_session.execute(
        select(CreditTransaction).where(
            CreditTransaction.request_id == ai_request.id,
            CreditTransaction.transaction_type == CreditTransactionType.USAGE,
        )
    )
    usage_tx = tx_result.scalar_one()
    assert usage_tx.amount == Decimal("1.00")
    assert usage_tx.from_user_id == user.id
