"""Sprint 13 — user-owned AI accounts and conversation-aware routing tests."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.conversations.execution import build_execution_summary
from app.main import app
from app.models.ai_account import AIAccount
from app.models.ai_request import AIRequest
from app.models.enums import AIRequestStatus, ExecutionType, RoutingPolicyType
from app.resource_management.budget_service import BudgetService
from app.routing.context import RoutingContext
from app.routing.health import ProviderHealth
from app.routing.sender_resolution import SenderFirstAccountResolver
from tests.conftest import AuthContext, WorkspaceContext


@pytest.fixture
async def db_session() -> AsyncSession:
    from app.core.config import get_settings

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


def _account(owner_id, *, provider: str = "mock", priority: int = 0) -> AIAccount:
    return AIAccount(
        id=uuid4(),
        workspace_id=uuid4(),
        owner_user_id=owner_id,
        provider=provider,
        display_name=f"{provider} account",
        encrypted_credentials="enc",
        is_active=True,
        monthly_budget=None,
        monthly_spent=Decimal("0"),
        priority=priority,
        default_model=None,
    )


def _health(account: AIAccount) -> ProviderHealth:
    return ProviderHealth(account=account, is_healthy=True, reason="ok")


def test_sender_first_resolver_prefers_lowest_priority() -> None:
    sender_id = uuid4()
    primary = _account(sender_id, priority=0)
    secondary = _account(sender_id, priority=2)
    other = _account(uuid4(), priority=0)
    context = RoutingContext(
        workspace=type("W", (), {"id": uuid4(), "owner_id": uuid4(), "name": "WS"})(),
        requesting_user=type("U", (), {"id": sender_id, "name": "Sender"})(),
        conversation=type("C", (), {"id": uuid4(), "title": "T"})(),
        provider=None,
        model=None,
        estimated_cost=Decimal("0"),
        participant_user_ids=frozenset({sender_id}),
    )
    resolver = SenderFirstAccountResolver()
    result = resolver.try_resolve(
        context,
        [_health(other), _health(secondary), _health(primary)],
        monthly_usage={},
    )
    assert result is not None
    assert result.account.id == primary.id


def test_build_execution_summary_sender_account() -> None:
    sender_id = uuid4()
    owner_id = sender_id
    account = _account(owner_id)
    request = AIRequest(
        conversation_id=uuid4(),
        provider="mock",
        model="mock",
        status=AIRequestStatus.COMPLETED,
        routing_policy=RoutingPolicyType.OWNER_FIRST,
    )
    summary = build_execution_summary(
        request,
        account,
        sender_user_id=sender_id,
        owner_names={owner_id: "Alice"},
    )
    assert summary.execution_type == ExecutionType.OWN_PROVIDER
    assert summary.owner_name == "Alice"


def test_build_execution_summary_borrowed_provider() -> None:
    sender_id = uuid4()
    owner_id = uuid4()
    account = _account(owner_id)
    request = AIRequest(
        conversation_id=uuid4(),
        provider="mock",
        model="mock",
        status=AIRequestStatus.COMPLETED,
        routing_policy=RoutingPolicyType.BALANCED,
    )
    summary = build_execution_summary(
        request,
        account,
        sender_user_id=sender_id,
        owner_names={owner_id: "Bob"},
        borrowed_from="Bob",
    )
    assert summary.execution_type == ExecutionType.BORROWED_PROVIDER
    assert summary.owner_name == "Bob"
    assert summary.borrowed_from == "Bob"


@pytest.mark.asyncio
async def test_member_can_create_and_list_own_ai_accounts(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    created = await client.post(
        "/ai-accounts",
        headers=member.headers,
        json={
            "provider": "mock",
            "display_name": "Member Mock",
            "api_key": "test-key",
            "priority": 1,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["owner_user_id"] == member.user_id
    assert body["is_mine"] is True

    listed = await client.get("/ai-accounts", headers=member.headers)
    assert listed.status_code == 200
    assert any(account["id"] == body["id"] for account in listed.json())


@pytest.mark.asyncio
async def test_member_cannot_delete_other_users_account(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    owner_account = await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Owner Mock",
            "api_key": "owner-key",
            "priority": 0,
        },
    )
    assert owner_account.status_code == 201
    account_id = owner_account.json()["id"]

    deleted = await client.delete(f"/ai-accounts/{account_id}", headers=member.headers)
    assert deleted.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_all_accounts_with_owners(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    await client.post(
        "/ai-accounts",
        headers=member.headers,
        json={
            "provider": "mock",
            "display_name": "Member Account",
            "api_key": "member-key",
            "priority": 0,
        },
    )

    listed = await client.get("/ai-accounts", headers=workspace.headers)
    assert listed.status_code == 200
    accounts = listed.json()
    assert len(accounts) >= 1
    assert all("owner_name" in account for account in accounts)


@pytest.mark.asyncio
async def test_borrow_engine_limits_to_conversation_participants(db_session) -> None:
    from datetime import UTC, datetime
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember
    from app.models.enums import WorkspaceRole
    from app.resource_management.budget_service import BudgetService
    from app.resource_sharing.engine import BorrowEngine
    from app.resource_sharing.preference_service import LendingPreferenceService

    lender = User(
        id=uuid4(),
        email=f"lender-{uuid4().hex}@example.com",
        name="Lender",
        password_hash="hashed",
    )
    outsider = User(
        id=uuid4(),
        email=f"outsider-{uuid4().hex}@example.com",
        name="Outsider",
        password_hash="hashed",
    )
    borrower = User(
        id=uuid4(),
        email=f"borrower-{uuid4().hex}@example.com",
        name="Borrower",
        password_hash="hashed",
    )
    workspace = Workspace(
        id=uuid4(),
        name="Borrow WS",
        slug=f"borrow-{uuid4().hex[:12]}",
        owner_id=lender.id,
    )
    db_session.add_all(
        [
            lender,
            outsider,
            borrower,
            workspace,
            WorkspaceMember(workspace_id=workspace.id, user_id=lender.id, role=WorkspaceRole.OWNER),
            WorkspaceMember(workspace_id=workspace.id, user_id=outsider.id, role=WorkspaceRole.MEMBER),
            WorkspaceMember(workspace_id=workspace.id, user_id=borrower.id, role=WorkspaceRole.MEMBER),
        ]
    )
    await db_session.flush()

    budget_service = BudgetService(db_session)
    await budget_service.create_workspace_budget_settings(workspace.id)
    for user_id in (lender.id, outsider.id, borrower.id):
        await budget_service.create_budget(workspace.id, user_id)

    pref_service = LendingPreferenceService(db_session)
    for user in (lender, outsider):
        pref = await pref_service.create_preference(workspace.id, user.id)
        pref.auto_share_enabled = True
        pref.monthly_share_limit = Decimal("5000")

    borrower_budget = await budget_service.get_budget(workspace.id, borrower.id)
    borrower_budget.remaining_credits = Decimal("0")
    await db_session.flush()

    engine = BorrowEngine(db_session, budget_service)
    participant_lenders = await engine.find_lenders(
        workspace.id,
        borrower.id,
        Decimal("100"),
        eligible_user_ids=frozenset({lender.id}),
    )
    assert len(participant_lenders) == 1
    assert participant_lenders[0].user_id == lender.id

    all_lenders = await engine.find_lenders(workspace.id, borrower.id, Decimal("100"))
    assert len(all_lenders) >= 2


@pytest.mark.asyncio
async def test_zero_budget_sender_uses_own_provider(
    client: AsyncClient,
    workspace: WorkspaceContext,
    monkeypatch,
) -> None:
    from app.ai.providers.mock import MockProvider

    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())
    await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Owner Mock",
            "api_key": "key",
            "priority": 0,
        },
    )
    session_factory = app.state.session_factory
    async with session_factory() as db:
        service = BudgetService(db)
        budget = await service.get_budget(workspace.workspace_id, workspace.auth.user_id)
        budget.remaining_credits = Decimal("0")
        budget.used_credits = budget.monthly_credit_limit
        await db.commit()

    conv = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Own provider"},
    )
    response = await client.post(
        "/chat/send",
        headers=workspace.headers,
        json={"conversation_id": conv.json()["id"], "content": "Hello"},
    )
    assert response.status_code == 200
    assert response.json()["execution"]["execution_type"] == "own_provider"
