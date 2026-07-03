from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversations.schemas import ExecutionSummary
from app.models.ai_account import AIAccount
from app.models.ai_request import AIRequest
from app.models.borrow_record import BorrowRecord
from app.models.enums import ExecutionType, RoutingPolicyType
from app.models.user import User


async def load_execution_summaries(
    db: AsyncSession,
    assistant_message_ids: list[UUID],
    *,
    requesting_user_id: UUID | None = None,
) -> dict[UUID, ExecutionSummary]:
    if not assistant_message_ids:
        return {}

    result = await db.execute(
        select(AIRequest).where(AIRequest.assistant_message_id.in_(assistant_message_ids))
    )
    ai_requests = list(result.scalars().all())
    if not ai_requests:
        return {}

    request_ids = [request.id for request in ai_requests]
    account_ids = {
        request.selected_account_id
        for request in ai_requests
        if request.selected_account_id is not None
    }

    accounts: dict[UUID, AIAccount] = {}
    owner_names: dict[UUID, str] = {}
    if account_ids:
        account_result = await db.execute(select(AIAccount).where(AIAccount.id.in_(account_ids)))
        accounts = {account.id: account for account in account_result.scalars().all()}
        owner_ids = {account.owner_user_id for account in accounts.values()}
        if owner_ids:
            owner_result = await db.execute(select(User).where(User.id.in_(owner_ids)))
            owner_names = {user.id: user.name for user in owner_result.scalars().all()}

    borrow_result = await db.execute(
        select(BorrowRecord).where(BorrowRecord.request_id.in_(request_ids))
    )
    borrow_by_request = {record.request_id: record for record in borrow_result.scalars().all()}

    lender_ids = {record.lender_user_id for record in borrow_by_request.values()}
    lender_names: dict[UUID, str] = {}
    if lender_ids:
        lender_result = await db.execute(select(User).where(User.id.in_(lender_ids)))
        lender_names = {user.id: user.name for user in lender_result.scalars().all()}

    user_message_ids = {
        request.user_message_id for request in ai_requests if request.user_message_id is not None
    }
    author_by_message: dict[UUID, UUID] = {}
    if user_message_ids:
        from app.models.message import Message

        message_result = await db.execute(
            select(Message.id, Message.author_id).where(Message.id.in_(user_message_ids))
        )
        author_by_message = {
            message_id: author_id
            for message_id, author_id in message_result.all()
            if author_id is not None
        }

    summaries: dict[UUID, ExecutionSummary] = {}
    for request in ai_requests:
        if request.assistant_message_id is None:
            continue

        account = (
            accounts.get(request.selected_account_id)
            if request.selected_account_id is not None
            else None
        )
        borrow_record = borrow_by_request.get(request.id)
        lender_name = lender_names.get(borrow_record.lender_user_id) if borrow_record else None
        sender_user_id = (
            author_by_message.get(request.user_message_id)
            if request.user_message_id is not None
            else requesting_user_id
        )
        summaries[request.assistant_message_id] = build_execution_summary(
            request,
            account,
            sender_user_id=sender_user_id,
            owner_names=owner_names,
            lender_name=lender_name,
            borrowed_from=lender_name if borrow_record is not None else None,
        )

    return summaries


def build_execution_summary(
    ai_request: AIRequest,
    account: AIAccount | None,
    *,
    sender_user_id: UUID | None = None,
    owner_names: dict[UUID, str] | None = None,
    lender_name: str | None = None,
    owner_name: str | None = None,
    borrowed_from: str | None = None,
) -> ExecutionSummary:
    owner_lookup = owner_names or {}

    if ai_request.provider == "ollama" and account is None:
        execution_type = ExecutionType.LOCAL_MODEL
        resolved_owner_name = None
        resolved_borrowed_from = None
    elif borrowed_from is not None:
        execution_type = ExecutionType.BORROWED_PROVIDER
        resolved_owner_name = owner_name or (
            owner_lookup.get(account.owner_user_id, account.display_name) if account else None
        )
        resolved_borrowed_from = borrowed_from
    elif account is not None:
        resolved_owner_name = owner_name or owner_lookup.get(
            account.owner_user_id,
            account.display_name,
        )
        execution_type = ExecutionType.OWN_PROVIDER
        resolved_borrowed_from = None
    elif lender_name is not None:
        execution_type = ExecutionType.BORROWED_PROVIDER
        resolved_owner_name = lender_name
        resolved_borrowed_from = lender_name
    else:
        execution_type = ExecutionType.OWN_PROVIDER
        resolved_owner_name = owner_name or "Workspace"
        resolved_borrowed_from = None

    return ExecutionSummary(
        provider=ai_request.provider,
        model=ai_request.model,
        owner_name=resolved_owner_name,
        execution_type=execution_type,
        routing_policy=ai_request.routing_policy or RoutingPolicyType.OWNER_FIRST,
        borrowed_from=resolved_borrowed_from,
    )
