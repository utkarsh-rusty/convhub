"""Resource sharing / borrowing tests."""

from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.mock import MockProvider
from app.main import app
from app.models.borrow_record import BorrowRecord
from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType, WorkspaceRole
from app.models.lending_preference import LendingPreference
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_sharing.engine import BorrowEngine
from app.resource_sharing.preference_service import LendingPreferenceService


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as http_client:
            yield http_client


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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


async def _register(client: AsyncClient, name: str = "User") -> tuple[str, str]:
    email = f"sharing-{uuid4().hex}@example.com"
    password = "password123"
    await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    login = await client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _seed_lender(
    db: AsyncSession,
    workspace_id,
    lender_user_id,
    *,
    remaining: Decimal,
    share_limit: Decimal,
    reserve: Decimal = Decimal("500"),
) -> None:
    pref_service = LendingPreferenceService(db)
    preference = await pref_service.create_preference(workspace_id, lender_user_id)
    preference.auto_share_enabled = True
    preference.monthly_share_limit = share_limit
    preference.minimum_reserved_credits = reserve

    budget = await BudgetService(db).get_budget(workspace_id, lender_user_id)
    budget.remaining_credits = remaining
    await db.flush()


@pytest.mark.asyncio
async def test_user_with_credits_skips_borrowing(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    get_settings.cache_clear()
    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())

    token, _user_id = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    workspace = await client.post("/workspaces", headers=headers, json={"name": "Has Credits"})
    workspace_id = workspace.json()["id"]
    headers["X-Workspace-ID"] = workspace_id

    conv = await client.post("/conversations", headers=headers, json={"title": "No Borrow"})
    conv_id = conv.json()["id"]

    response = await client.post(
        "/chat/send",
        headers=headers,
        json={"conversation_id": conv_id, "content": "Hello"},
    )
    assert response.status_code == 200

    session_factory = app.state.session_factory
    async with session_factory() as db:
        result = await db.execute(
            select(BorrowRecord).where(BorrowRecord.workspace_id == workspace_id)
        )
        assert result.scalars().all() == []

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_zero_credits_borrow_succeeds(client: AsyncClient, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    get_settings.cache_clear()
    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())

    borrower_token, borrower_id = await _register(client, "Borrower")
    lender_token, lender_id = await _register(client, "Lender")

    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    workspace = await client.post("/workspaces", headers=borrower_headers, json={"name": "Borrow WS"})
    workspace_id = workspace.json()["id"]
    borrower_headers["X-Workspace-ID"] = workspace_id

    lender_email = (
        await client.get("/users/me", headers={"Authorization": f"Bearer {lender_token}"})
    ).json()["email"]
    invite = await client.post(
        f"/workspaces/{workspace_id}/invite",
        headers=borrower_headers,
        json={"email": lender_email, "role": "member"},
    )
    await client.post(
        f"/invitations/{invite.json()['token']}/accept",
        headers={"Authorization": f"Bearer {lender_token}"},
    )

    session_factory = app.state.session_factory
    async with session_factory() as db:
        settings = await BudgetService(db).get_workspace_budget_settings(workspace_id)
        settings.allow_credit_borrowing = True

        borrower_budget = await BudgetService(db).get_budget(workspace_id, borrower_id)
        borrower_budget.remaining_credits = Decimal("0")
        borrower_budget.used_credits = borrower_budget.monthly_credit_limit

        await _seed_lender(
            db,
            workspace_id,
            lender_id,
            remaining=Decimal("3000"),
            share_limit=Decimal("2000"),
            reserve=Decimal("500"),
        )
        await db.commit()

    conv = await client.post("/conversations", headers=borrower_headers, json={"title": "Borrow"})
    conv_id = conv.json()["id"]

    response = await client.post(
        "/chat/send",
        headers=borrower_headers,
        json={"conversation_id": conv_id, "content": "Need shared credits"},
    )
    assert response.status_code == 200

    async with session_factory() as db:
        borrow_records = (
            await db.execute(
                select(BorrowRecord).where(BorrowRecord.workspace_id == workspace_id)
            )
        ).scalars().all()
        assert len(borrow_records) == 1
        record = borrow_records[0]
        assert str(record.borrower_user_id) == borrower_id
        assert str(record.lender_user_id) == lender_id
        assert record.credits > Decimal("0")

        lender_budget = await BudgetService(db).get_budget(workspace_id, lender_id)
        assert lender_budget.remaining_credits >= Decimal("500")

        tx_types = (
            await db.execute(
                select(CreditTransaction.transaction_type).where(
                    CreditTransaction.workspace_id == workspace_id,
                    CreditTransaction.transaction_type.in_(
                        [CreditTransactionType.BORROW, CreditTransactionType.LEND]
                    ),
                )
            )
        ).scalars().all()
        assert CreditTransactionType.BORROW in tx_types
        assert CreditTransactionType.LEND in tx_types

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lender_never_goes_below_reserve(db_session: AsyncSession) -> None:
    user = User(
        id=uuid4(),
        email=f"lender-{uuid4().hex}@example.com",
        name="Lender",
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
        name="Reserve WS",
        slug=f"reserve-{uuid4().hex[:12]}",
        owner_id=user.id,
    )
    db_session.add_all(
        [
            user,
            borrower,
            workspace,
            WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER),
            WorkspaceMember(workspace_id=workspace.id, user_id=borrower.id, role=WorkspaceRole.MEMBER),
        ]
    )
    await db_session.flush()

    budget_service = BudgetService(db_session)
    await budget_service.create_workspace_budget_settings(workspace.id)
    await budget_service.create_budget(workspace.id, user.id)
    await budget_service.create_budget(workspace.id, borrower.id)

    pref_service = LendingPreferenceService(db_session)
    lender_pref = await pref_service.create_preference(workspace.id, user.id)
    lender_pref.auto_share_enabled = True
    lender_pref.monthly_share_limit = Decimal("5000")
    lender_pref.minimum_reserved_credits = Decimal("500")

    lender_budget = await budget_service.get_budget(workspace.id, user.id)
    lender_budget.remaining_credits = Decimal("700")
    borrower_budget = await budget_service.get_budget(workspace.id, borrower.id)
    borrower_budget.remaining_credits = Decimal("0")
    await db_session.flush()

    engine = BorrowEngine(db_session, budget_service)
    reservation = await engine.reserve_shared_credits(workspace.id, borrower.id, Decimal("200"))
    assert reservation is not None

    await db_session.refresh(lender_budget)
    assert lender_budget.remaining_credits == Decimal("500")

    blocked = await engine.reserve_shared_credits(workspace.id, borrower.id, Decimal("1"))
    assert blocked is None

    await db_session.refresh(lender_budget)
    assert lender_budget.remaining_credits >= Decimal("500")


@pytest.mark.asyncio
async def test_borrow_engine_validate_lender(db_session: AsyncSession) -> None:
    workspace = Workspace(
        id=uuid4(),
        name="Validate WS",
        slug=f"validate-{uuid4().hex[:12]}",
        owner_id=uuid4(),
    )
    user_id = workspace.owner_id
    user = User(id=user_id, email=f"v-{uuid4().hex}@example.com", name="V", password_hash="x")
    db_session.add_all([user, workspace])
    await db_session.flush()

    budget_service = BudgetService(db_session)
    await budget_service.create_workspace_budget_settings(workspace.id)
    await budget_service.create_budget(workspace.id, user.id)

    pref = LendingPreference(
        workspace_id=workspace.id,
        user_id=user.id,
        auto_share_enabled=True,
        monthly_share_limit=Decimal("100"),
        minimum_reserved_credits=Decimal("500"),
    )
    db_session.add(pref)
    budget = await budget_service.get_budget(workspace.id, user.id)
    budget.remaining_credits = Decimal("1000")
    budget.lent_credits = Decimal("90")

    engine = BorrowEngine(db_session, budget_service)
    assert engine.validate_lender(pref, budget, Decimal("10")) is True
    assert engine.validate_lender(pref, budget, Decimal("20")) is False
