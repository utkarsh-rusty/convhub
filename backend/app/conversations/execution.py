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
    if account_ids:
        account_result = await db.execute(
            select(AIAccount).where(AIAccount.id.in_(account_ids))
        )
        accounts = {account.id: account for account in account_result.scalars().all()}

    borrow_result = await db.execute(
        select(BorrowRecord).where(BorrowRecord.request_id.in_(request_ids))
    )
    borrow_by_request = {record.request_id: record for record in borrow_result.scalars().all()}

    lender_ids = {
        record.lender_user_id for record in borrow_by_request.values()
    }
    lender_names: dict[UUID, str] = {}
    if lender_ids:
        lender_result = await db.execute(select(User).where(User.id.in_(lender_ids)))
        lender_names = {user.id: user.name for user in lender_result.scalars().all()}

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
        summaries[request.assistant_message_id] = build_execution_summary(
            request,
            account,
            lender_name=(
                lender_names.get(borrow_record.lender_user_id) if borrow_record else None
            ),
        )

    return summaries


def build_execution_summary(
    ai_request: AIRequest,
    account: AIAccount | None,
    *,
    lender_name: str | None = None,
) -> ExecutionSummary:
    if ai_request.provider == "ollama" and account is None:
        execution_type = ExecutionType.LOCAL_MODEL
        account_owner_name = None
    elif lender_name is not None:
        execution_type = ExecutionType.BORROWED
        account_owner_name = lender_name
    else:
        execution_type = ExecutionType.OWN_ACCOUNT
        account_owner_name = account.display_name if account is not None else "Workspace"

    return ExecutionSummary(
        provider=ai_request.provider,
        model=ai_request.model,
        account_owner_name=account_owner_name,
        execution_type=execution_type,
        routing_policy=ai_request.routing_policy or RoutingPolicyType.OWNER_FIRST,
    )
