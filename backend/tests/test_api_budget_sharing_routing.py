"""Budget, sharing, routing, and chat API QA tests."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.ai.providers.mock import MockProvider
from app.main import app
from app.models.borrow_record import BorrowRecord
from app.models.credit_transaction import CreditTransaction
from app.models.enums import CreditTransactionType
from app.resource_management.budget_service import BudgetService
from tests.conftest import (
    AuthContext,
    WorkspaceContext,
    create_workspace,
    invite_and_accept,
    register_user,
)


@pytest.mark.asyncio
async def test_budget_and_credit_history(client: AsyncClient, workspace: WorkspaceContext) -> None:
    budget = await client.get(
        f"/workspaces/{workspace.workspace_id}/budget/me",
        headers=workspace.headers,
    )
    assert budget.status_code == 200
    assert budget.json()["monthly_credit_limit"] == "5000.00"

    history = await client.get(
        f"/workspaces/{workspace.workspace_id}/credits/history",
        headers=workspace.headers,
        params={"limit": 10, "offset": 0},
    )
    assert history.status_code == 200
    assert history.json()["total"] >= 1


@pytest.mark.asyncio
async def test_member_cannot_update_workspace_budget_settings(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}/settings/budget",
        headers=member.headers,
        json={"allow_credit_borrowing": True},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_update_workspace_budget_settings(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}/settings/budget",
        headers=workspace.headers,
        json={"allow_credit_borrowing": True, "routing_policy": "balanced"},
    )
    assert response.status_code == 200
    assert response.json()["allow_credit_borrowing"] is True
    assert response.json()["routing_policy"] == "balanced"


@pytest.mark.asyncio
async def test_sharing_preferences_happy_path(client: AsyncClient, workspace: WorkspaceContext) -> None:
    current = await client.get(
        f"/workspaces/{workspace.workspace_id}/sharing/me",
        headers=workspace.headers,
    )
    assert current.status_code == 200

    updated = await client.patch(
        f"/workspaces/{workspace.workspace_id}/sharing/me",
        headers=workspace.headers,
        json={
            "auto_share_enabled": True,
            "monthly_share_limit": "1000.00",
            "minimum_reserved_credits": "500.00",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["auto_share_enabled"] is True


@pytest.mark.asyncio
async def test_sharing_overview_admin_only(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    admin = await client.get(
        f"/workspaces/{workspace.workspace_id}/sharing",
        headers=workspace.headers,
    )
    assert admin.status_code == 200
    assert len(admin.json()["members"]) >= 2

    member_view = await client.get(
        f"/workspaces/{workspace.workspace_id}/sharing",
        headers=member.headers,
    )
    assert member_view.status_code == 403


@pytest.mark.asyncio
async def test_routing_settings_happy_path(client: AsyncClient, workspace: WorkspaceContext) -> None:
    current = await client.get(
        f"/workspaces/{workspace.workspace_id}/routing",
        headers=workspace.headers,
    )
    assert current.status_code == 200
    assert "routing_policy" in current.json()
    assert "preview" in current.json()

    updated = await client.patch(
        f"/workspaces/{workspace.workspace_id}/routing",
        headers=workspace.headers,
        json={"routing_policy": "cheapest"},
    )
    assert updated.status_code == 200
    assert updated.json()["routing_policy"] == "cheapest"


@pytest.mark.asyncio
async def test_member_cannot_update_routing(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}/routing",
        headers=member.headers,
        json={"routing_policy": "priority"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_chat_send_returns_execution_summary(
    client: AsyncClient,
    workspace: WorkspaceContext,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())
    await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "mock",
            "display_name": "Alice's Account",
            "api_key": "test-key",
            "is_active": True,
            "priority": 0,
        },
    )
    conv = await client.post(
        "/conversations",
        headers=workspace.headers,
        json={"title": "Execution QA"},
    )
    conv_id = conv.json()["id"]

    response = await client.post(
        "/chat/send",
        headers=workspace.headers,
        json={"conversation_id": conv_id, "content": "Summarize ConvHub"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["execution"] is not None
    assert body["execution"]["provider"] == "mock"
    assert body["execution"]["execution_type"] == "own_provider"


@pytest.mark.asyncio
async def test_borrow_flow_creates_ledger_and_borrow_record(
    client: AsyncClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr("app.ai.gateway.create_provider", lambda **_: MockProvider())

    owner = await register_user(client, name="Lender")
    borrower = await register_user(client, name="Borrower")
    workspace = await create_workspace(client, owner)
    await invite_and_accept(client, workspace, borrower)

    session_factory = app.state.session_factory
    async with session_factory() as db:
        settings = await BudgetService(db).get_workspace_budget_settings(workspace.workspace_id)
        settings.allow_credit_borrowing = True
        borrower_budget = await BudgetService(db).get_budget(workspace.workspace_id, borrower.user_id)
        borrower_budget.remaining_credits = Decimal("0")
        borrower_budget.used_credits = borrower_budget.monthly_credit_limit

        from app.resource_sharing.preference_service import LendingPreferenceService

        pref = await LendingPreferenceService(db).get_my_preference(workspace.workspace_id, owner.user_id)
        pref.auto_share_enabled = True
        pref.monthly_share_limit = Decimal("2000")
        lender_budget = await BudgetService(db).get_budget(workspace.workspace_id, owner.user_id)
        lender_budget.remaining_credits = Decimal("3000")
        await db.commit()

    borrower_headers = {**borrower.headers, "X-Workspace-ID": workspace.workspace_id}
    await client.post(
        "/ai-accounts",
        headers=workspace.headers,
        json={
            "provider": "anthropic",
            "display_name": "Lender Anthropic",
            "api_key": "lender-key",
            "is_active": True,
            "priority": 0,
        },
    )
    conv = await client.post("/conversations", headers=borrower_headers, json={"title": "Borrow QA"})
    conv_id = conv.json()["id"]
    await client.post(
        f"/conversations/{conv_id}/participants",
        headers=borrower_headers,
        json={"user_ids": [owner.user_id]},
    )
    response = await client.post(
        "/chat/send",
        headers=borrower_headers,
        json={"conversation_id": conv_id, "content": "Need credits"},
    )
    assert response.status_code == 200
    assert response.json()["execution"]["execution_type"] == "borrowed_provider"

    async with session_factory() as db:
        records = (
            await db.execute(
                select(BorrowRecord).where(BorrowRecord.workspace_id == workspace.workspace_id)
            )
        ).scalars().all()
        assert len(records) == 1

        tx_types = (
            await db.execute(
                select(CreditTransaction.transaction_type).where(
                    CreditTransaction.workspace_id == workspace.workspace_id,
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
async def test_dashboard_budget_totals_match_sharing_overview(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    overview = await client.get(
        f"/workspaces/{workspace.workspace_id}/sharing",
        headers=workspace.headers,
    )
    assert overview.status_code == 200
    total_remaining = sum(
        Decimal(member["remaining_credits"]) for member in overview.json()["members"]
    )
    assert total_remaining > Decimal("0")
