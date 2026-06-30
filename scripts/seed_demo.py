#!/usr/bin/env python3
"""Seed a demo workspace for ConvHub presentations.

Usage:
  cd convhub/backend && PYTHONPATH=. python ../scripts/seed_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai_accounts.schemas import AIAccountCreate
from app.ai_accounts.service import AIAccountService
from app.conversations.deps import WorkspaceContext
from app.conversations.schemas import ConversationCreate, MessageCreate
from app.conversations.service import ConversationService
from app.core.config import get_settings
from app.core.credentials import CredentialEncryption
from app.core.password import hash_password
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import (
    AIRequestStatus,
    ConversationParticipantRole,
    MessageRole,
    RoutingPolicyType,
    WorkspaceRole,
)
from app.models.message import Message
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.resource_management.budget_service import BudgetService
from app.resource_sharing.preference_service import LendingPreferenceService
from app.workspaces.schemas import WorkspaceCreate
from app.workspaces.service import WorkspaceService

DEMO_PASSWORD = "demo12345"
DEMO_USERS = [
    ("alice@demo.convhub.local", "Alice"),
    ("bob@demo.convhub.local", "Bob"),
    ("charlie@demo.convhub.local", "Charlie"),
]


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_uri)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        existing = await db.execute(select(User).where(User.email == DEMO_USERS[0][0]))
        if existing.scalar_one_or_none() is not None:
            print("Demo data already exists. Skipping.")
            await engine.dispose()
            return

        users = [
            User(email=email, name=name, password_hash=hash_password(DEMO_PASSWORD))
            for email, name in DEMO_USERS
        ]
        db.add_all(users)
        await db.flush()

        alice, bob, charlie = users

        workspace_response = await WorkspaceService(db).create_workspace(
            alice,
            WorkspaceCreate(name="Demo Workspace", slug="demo"),
        )
        workspace = await db.get(Workspace, workspace_response.id)
        assert workspace is not None

        alice_membership = (
            await db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace.id,
                    WorkspaceMember.user_id == alice.id,
                )
            )
        ).scalar_one()

        for user in (bob, charlie):
            db.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role=WorkspaceRole.MEMBER,
                )
            )
            await BudgetService(db).create_budget(workspace.id, user.id)
            await LendingPreferenceService(db).create_preference(workspace.id, user.id)
        await db.flush()

        budget_service = BudgetService(db)
        ws_settings = await budget_service.get_workspace_budget_settings(workspace.id)
        ws_settings.allow_credit_borrowing = True

        alice_budget = await budget_service.get_budget(workspace.id, alice.id)
        alice_budget.remaining_credits = Decimal("4200")
        alice_budget.used_credits = Decimal("800")

        bob_budget = await budget_service.get_budget(workspace.id, bob.id)
        bob_budget.remaining_credits = Decimal("0")
        bob_budget.used_credits = bob_budget.monthly_credit_limit

        charlie_budget = await budget_service.get_budget(workspace.id, charlie.id)
        charlie_budget.remaining_credits = Decimal("3100")

        pref_service = LendingPreferenceService(db)
        alice_pref = await pref_service.get_my_preference(workspace.id, alice.id)
        alice_pref.auto_share_enabled = True
        alice_pref.monthly_share_limit = Decimal("1500")
        alice_pref.minimum_reserved_credits = Decimal("500")

        encryption = CredentialEncryption(settings.credentials_encryption_key)
        ai_service = AIAccountService(db, settings, encryption)
        ctx = WorkspaceContext(workspace_id=workspace.id, user=alice, membership=alice_membership)

        mock_account = await ai_service.create_account(
            ctx,
            AIAccountCreate(
                provider="mock",
                display_name="Alice's Account",
                api_key="demo-key",
                is_active=True,
                priority=0,
                default_model="mock",
            ),
        )
        await ai_service.create_account(
            ctx,
            AIAccountCreate(
                provider="ollama",
                display_name="Local Ollama",
                is_active=True,
                priority=1,
                default_model="llama3.2",
            ),
        )

        conversation_service = ConversationService(db)
        conversation = await conversation_service.create_conversation(
            ctx,
            ConversationCreate(title="Product Launch Planning"),
        )
        conv = await db.get(Conversation, conversation.id)
        assert conv is not None

        for user in (bob, charlie):
            db.add(
                ConversationParticipant(
                    conversation_id=conv.id,
                    user_id=user.id,
                    role=ConversationParticipantRole.MEMBER,
                )
            )
        await db.flush()

        user_msg = await conversation_service.create_message(
            conv,
            alice,
            MessageCreate(content="Team, let's draft launch messaging for ConvHub.", role=MessageRole.USER),
        )
        await conversation_service.create_message(
            conv,
            bob,
            MessageCreate(content="I'll handle the onboarding flow copy.", role=MessageRole.USER),
        )

        assistant_message = Message(
            conversation_id=conv.id,
            author_id=None,
            role=MessageRole.ASSISTANT,
            content=(
                "[mock] Great plan. ConvHub routes requests across team accounts "
                "while enforcing credit policies and borrowing rules."
            ),
        )
        db.add(assistant_message)
        await db.flush()

        now = datetime.now(UTC)
        db.add(
            AIRequest(
                conversation_id=conv.id,
                user_message_id=user_msg.id,
                assistant_message_id=assistant_message.id,
                provider="mock",
                model="mock",
                status=AIRequestStatus.COMPLETED,
                started_at=now,
                completed_at=now,
                latency_ms=120,
                input_tokens=42,
                output_tokens=24,
                selected_account_id=mock_account.id,
                selected_policy="owner_first",
                routing_policy=RoutingPolicyType.OWNER_FIRST,
                routing_reason="Demo seed data",
            )
        )
        await db.commit()

        print("Demo workspace seeded successfully.")
        print("")
        print("Workspace: Demo Workspace (slug: demo)")
        print("Password for all users:", DEMO_PASSWORD)
        print("")
        for email, name in DEMO_USERS:
            print(f"  - {name}: {email}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
