from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.prompt_builder import PromptBuilder
from app.ai.providers.factory import create_provider
from app.ai_accounts.service import AIAccountService
from app.conversations.schemas import MessageResponse
from app.conversations.execution import build_execution_summary
from app.core.config import Settings
from app.models.ai_request import AIRequest
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import AIRequestStatus, MessageRole
from app.models.message import Message
from app.models.user import User
from app.models.workspace import Workspace
from app.resource_management.budget_service import BudgetService
from app.resource_management.credit_calculator import calculate_credits
from app.resource_management.credit_policy import CreditPolicy
from app.resource_management.exceptions import InsufficientCreditsError
from app.resource_sharing.engine import BorrowEngine, BorrowReservation
from app.realtime.broadcaster import RealtimeBroadcaster, get_broadcaster
from app.routing.context import RoutingContext
from app.routing.engine import RoutingEngine


class AIGateway:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        ai_account_service: AIAccountService,
        budget_service: BudgetService,
        routing_engine: RoutingEngine,
        borrow_engine: BorrowEngine,
        prompt_builder: PromptBuilder | None = None,
        credit_policy: CreditPolicy | None = None,
        broadcaster: RealtimeBroadcaster | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.ai_account_service = ai_account_service
        self.budget_service = budget_service
        self.routing_engine = routing_engine
        self.borrow_engine = borrow_engine
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.credit_policy = credit_policy or CreditPolicy()
        self.broadcaster = broadcaster if broadcaster is not None else get_broadcaster()

    async def generate(
        self,
        conversation: Conversation,
        user_message: Message,
        history: list[Message],
    ) -> MessageResponse:
        started_at = datetime.now(UTC)

        workspace = await self._load_workspace(conversation.workspace_id)
        budget_settings = await self.budget_service.get_workspace_budget_settings(workspace.id)
        participants = await self._load_participants(conversation.id)
        author_names = await self._resolve_author_names(participants, history)
        requesting_user = await self._load_user(user_message.author_id)

        prompt_context = self.prompt_builder.build(
            workspace=workspace,
            conversation=conversation,
            participants=participants,
            messages=history,
            base_system_prompt=self.settings.ai_system_prompt,
            author_names=author_names,
        )

        reserved_cost = Decimal("0")
        borrow_reservation: BorrowReservation | None = None

        if user_message.author_id is not None:
            borrower_budget = await self.budget_service.reset_if_needed(
                conversation.workspace_id,
                user_message.author_id,
            )
            preliminary_estimate = self.credit_policy.estimate_request_cost(
                self.settings.ai_provider,
                self.settings.ai_model,
                prompt_context,
            )

            if preliminary_estimate > Decimal("0"):
                if borrower_budget.remaining_credits == Decimal("0"):
                    if not budget_settings.allow_credit_borrowing:
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail="Insufficient credits for this request",
                        )
                    borrow_reservation = await self.borrow_engine.reserve_shared_credits(
                        conversation.workspace_id,
                        user_message.author_id,
                        preliminary_estimate,
                    )
                    if borrow_reservation is None:
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail="Insufficient credits for this request",
                        )
                    await self._broadcast_borrow_started(
                        conversation,
                        borrow_reservation,
                    )

        routing_context = RoutingContext(
            workspace=workspace,
            requesting_user=requesting_user,
            conversation=conversation,
            provider=None,
            model=None,
            estimated_cost=Decimal("0"),
            prompt_context=prompt_context,
        )
        routing_decision = await self.routing_engine.select(routing_context)

        if routing_decision.selected_account is not None:
            provider_name = routing_decision.selected_account.provider
            credentials = routing_decision.credentials
        else:
            provider_name = self.settings.ai_provider
            credentials = None

        model_name = routing_decision.selected_model

        if self.broadcaster is not None:
            await self.broadcaster.routing_selected(
                conversation.workspace_id,
                conversation.id,
                {
                    "provider": provider_name,
                    "model": model_name,
                    "decision_reason": routing_decision.decision_reason,
                },
            )

        if provider_name == "ollama" and not budget_settings.allow_local_models:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Local models are disabled for this workspace",
            )

        if user_message.author_id is not None:
            estimated_cost = self.credit_policy.estimate_request_cost(
                provider_name,
                model_name,
                prompt_context,
            )
            if estimated_cost > Decimal("0"):
                if not await self.budget_service.has_available_credits(
                    conversation.workspace_id,
                    user_message.author_id,
                    estimated_cost,
                ):
                    if (
                        borrow_reservation is None
                        and budget_settings.allow_credit_borrowing
                    ):
                        borrow_reservation = await self.borrow_engine.reserve_shared_credits(
                            conversation.workspace_id,
                            user_message.author_id,
                            estimated_cost,
                        )
                        if borrow_reservation is not None:
                            await self._broadcast_borrow_started(conversation, borrow_reservation)
                    if not await self.budget_service.has_available_credits(
                        conversation.workspace_id,
                        user_message.author_id,
                        estimated_cost,
                    ):
                        if borrow_reservation is not None:
                            await self.borrow_engine.release_borrow(borrow_reservation)
                        raise HTTPException(
                            status_code=status.HTTP_402_PAYMENT_REQUIRED,
                            detail="Insufficient credits for this request",
                        )
                reserved_cost = estimated_cost

        try:
            provider = create_provider(
                provider_name=provider_name,
                credentials=credentials,
                settings=self.settings,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        ai_request = AIRequest(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            provider=provider_name,
            model=model_name,
            status=AIRequestStatus.PENDING,
            started_at=started_at,
            selected_account_id=(
                routing_decision.selected_account.id
                if routing_decision.selected_account
                else None
            ),
            selected_policy=routing_decision.policy_used.value,
            routing_policy=budget_settings.routing_policy,
            routing_reason=routing_decision.decision_reason,
            routing_score=routing_decision.score,
        )
        self.db.add(ai_request)
        await self.db.flush()

        if user_message.author_id is not None and reserved_cost > Decimal("0"):
            await self.budget_service.consume_credits(
                workspace_id=conversation.workspace_id,
                user_id=user_message.author_id,
                ai_request_id=ai_request.id,
                amount=reserved_cost,
                description=f"Estimated charge for AI request {ai_request.id}",
            )
            await self._broadcast_credits_updated(
                conversation.workspace_id,
                user_message.author_id,
            )

        try:
            response = await self._generate_provider_response(
                provider=provider,
                provider_name=provider_name,
                prompt_context=prompt_context,
                model_name=model_name,
                workspace_id=conversation.workspace_id,
                conversation_id=conversation.id,
            )

            completed_at = datetime.now(UTC)
            latency_ms = int((completed_at - started_at).total_seconds() * 1000)

            assistant_message = Message(
                conversation_id=conversation.id,
                author_id=None,
                role=MessageRole.ASSISTANT,
                content=response.content,
            )
            self.db.add(assistant_message)
            await self.db.flush()

            conversation.last_activity_at = completed_at
            ai_request.assistant_message_id = assistant_message.id
            ai_request.status = AIRequestStatus.COMPLETED
            ai_request.completed_at = completed_at
            ai_request.latency_ms = latency_ms
            ai_request.model = response.model
            ai_request.input_tokens = response.input_tokens
            ai_request.output_tokens = response.output_tokens
            ai_request.estimated_cost = (
                Decimal(str(response.estimated_cost))
                if response.estimated_cost is not None
                else None
            )

            if routing_decision.selected_account is not None:
                routing_decision.selected_account.monthly_spent += (
                    ai_request.estimated_cost or Decimal("0")
                )

            await self.db.flush()

            if user_message.author_id is not None:
                actual_cost = calculate_credits(ai_request, self.credit_policy)

                if reserved_cost == Decimal("0") and actual_cost > Decimal("0"):
                    await self.budget_service.consume_credits(
                        workspace_id=conversation.workspace_id,
                        user_id=user_message.author_id,
                        ai_request_id=ai_request.id,
                        amount=actual_cost,
                    )
                elif reserved_cost > Decimal("0") and actual_cost != reserved_cost:
                    await self.budget_service.adjust_credits(
                        workspace_id=conversation.workspace_id,
                        user_id=user_message.author_id,
                        amount=reserved_cost - actual_cost,
                        description=(
                            f"Estimate reconciliation for request {ai_request.id}: "
                            f"estimated {reserved_cost}, actual {actual_cost}"
                        ),
                        ai_request_id=ai_request.id,
                    )
                await self._broadcast_credits_updated(
                    conversation.workspace_id,
                    user_message.author_id,
                )

            lender_name: str | None = None
            if borrow_reservation is not None:
                await self.borrow_engine.record_borrow(ai_request.id, borrow_reservation)
                lender = await self._load_user(borrow_reservation.lender_user_id)
                lender_name = lender.name
                await self._broadcast_borrow_completed(conversation, borrow_reservation, ai_request.id)

            execution = build_execution_summary(
                ai_request,
                routing_decision.selected_account,
                lender_name=lender_name,
            )

            await self.db.commit()
            await self.db.refresh(assistant_message)
            assistant_response = MessageResponse(
                id=assistant_message.id,
                conversation_id=assistant_message.conversation_id,
                author_id=assistant_message.author_id,
                role=assistant_message.role,
                content=assistant_message.content,
                created_at=assistant_message.created_at,
                provider=provider_name,
                execution=execution,
            )
            if self.broadcaster is not None:
                await self.broadcaster.message_completed(
                    conversation.workspace_id,
                    conversation.id,
                    assistant_response.model_dump(mode="json"),
                )
            return assistant_response
        except HTTPException:
            if borrow_reservation is not None:
                await self.borrow_engine.release_borrow(borrow_reservation)
            if user_message.author_id is not None and reserved_cost > Decimal("0"):
                await self._refund_reserved_credits(
                    conversation.workspace_id,
                    user_message.author_id,
                    ai_request.id,
                    reserved_cost,
                )
            raise
        except InsufficientCreditsError as exc:
            if borrow_reservation is not None:
                await self.borrow_engine.release_borrow(borrow_reservation)
            completed_at = datetime.now(UTC)
            ai_request.status = AIRequestStatus.FAILED
            ai_request.completed_at = completed_at
            ai_request.error_message = str(exc)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for this request",
            ) from exc
        except Exception as exc:
            if borrow_reservation is not None:
                await self.borrow_engine.release_borrow(borrow_reservation)
            if user_message.author_id is not None and reserved_cost > Decimal("0"):
                await self._refund_reserved_credits(
                    conversation.workspace_id,
                    user_message.author_id,
                    ai_request.id,
                    reserved_cost,
                )
            completed_at = datetime.now(UTC)
            latency_ms = int((completed_at - started_at).total_seconds() * 1000)

            ai_request.status = AIRequestStatus.FAILED
            ai_request.completed_at = completed_at
            ai_request.latency_ms = latency_ms
            ai_request.error_message = str(exc)

            await self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI provider failed to generate a response",
            ) from exc

    async def _load_user(self, user_id: UUID | None) -> User:
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User message must have an author",
            )
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def _load_workspace(self, workspace_id: UUID) -> Workspace:
        result = await self.db.execute(select(Workspace).where(Workspace.id == workspace_id))
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
        return workspace

    async def _load_participants(self, conversation_id: UUID) -> list[ConversationParticipant]:
        result = await self.db.execute(
            select(ConversationParticipant)
            .options(selectinload(ConversationParticipant.user))
            .where(ConversationParticipant.conversation_id == conversation_id)
            .order_by(ConversationParticipant.joined_at.asc())
        )
        return list(result.scalars().all())

    async def _resolve_author_names(
        self,
        participants: list[ConversationParticipant],
        messages: list[Message],
    ) -> dict[UUID, str]:
        author_names: dict[UUID, str] = {}
        for participant in participants:
            if participant.user is not None:
                author_names[participant.user_id] = participant.user.name

        missing_author_ids = {
            message.author_id
            for message in messages
            if message.author_id is not None and message.author_id not in author_names
        }
        if not missing_author_ids:
            return author_names

        result = await self.db.execute(select(User).where(User.id.in_(missing_author_ids)))
        for user in result.scalars().all():
            author_names[user.id] = user.name

        return author_names

    async def _generate_provider_response(
        self,
        *,
        provider,
        provider_name: str,
        prompt_context,
        model_name: str,
        workspace_id: UUID,
        conversation_id: UUID,
    ):
        from app.ai.providers.base import AIResponse

        if self.broadcaster is not None and provider.supports_streaming:
            stream_id = str(uuid4())
            accumulated = ""
            response: AIResponse | None = None
            async for event in provider.stream_events(prompt_context, model_name):
                if event.delta:
                    accumulated += event.delta
                    await self.broadcaster.message_streaming(
                        workspace_id,
                        conversation_id,
                        {
                            "stream_id": stream_id,
                            "provider": provider_name,
                            "model": model_name,
                            "delta": event.delta,
                            "content": accumulated,
                        },
                    )
                if event.response is not None:
                    response = event.response
            if response is None:
                raise RuntimeError("Streaming provider did not return a final response")
            return response

        return await provider.generate(prompt_context, model_name)

    async def _broadcast_credits_updated(self, workspace_id: UUID, user_id: UUID) -> None:
        if self.broadcaster is None:
            return
        budget = await self.budget_service.get_budget(workspace_id, user_id)
        await self.broadcaster.credits_updated(
            workspace_id,
            user_id,
            {
                "user_id": str(user_id),
                "remaining_credits": str(budget.remaining_credits),
                "used_credits": str(budget.used_credits),
                "borrowed_credits": str(budget.borrowed_credits),
                "lent_credits": str(budget.lent_credits),
            },
        )

    async def _broadcast_borrow_started(
        self,
        conversation: Conversation,
        reservation: BorrowReservation,
    ) -> None:
        if self.broadcaster is None:
            return
        await self.broadcaster.borrow_started(
            conversation.workspace_id,
            conversation.id,
            {
                "borrower_user_id": str(reservation.borrower_user_id),
                "lender_user_id": str(reservation.lender_user_id),
                "credits": str(reservation.amount),
            },
        )

    async def _broadcast_borrow_completed(
        self,
        conversation: Conversation,
        reservation: BorrowReservation,
        request_id: UUID,
    ) -> None:
        if self.broadcaster is None:
            return
        await self.broadcaster.borrow_completed(
            conversation.workspace_id,
            conversation.id,
            {
                "request_id": str(request_id),
                "borrower_user_id": str(reservation.borrower_user_id),
                "lender_user_id": str(reservation.lender_user_id),
                "credits": str(reservation.amount),
            },
        )

    async def _refund_reserved_credits(
        self,
        workspace_id: UUID,
        user_id: UUID,
        ai_request_id: UUID,
        amount: Decimal,
    ) -> None:
        await self.budget_service.adjust_credits(
            workspace_id=workspace_id,
            user_id=user_id,
            amount=amount,
            description=f"Refund reserved credits for failed request {ai_request_id}",
            ai_request_id=ai_request_id,
        )
        await self.db.flush()
        await self._broadcast_credits_updated(workspace_id, user_id)
