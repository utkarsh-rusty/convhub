from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum
from app.models.enums import AIRequestStatus, RoutingPolicyType
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ai_account import AIAccount
    from app.models.conversation import Conversation
    from app.models.message import Message


class AIRequest(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_requests"
    __table_args__ = (
        Index("ix_ai_requests_conversation_id", "conversation_id"),
        Index("ix_ai_requests_user_message_id", "user_message_id"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    assistant_message_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AIRequestStatus] = mapped_column(
        pg_enum(AIRequestStatus, name="ai_request_status"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    selected_policy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    routing_policy: Mapped[RoutingPolicyType | None] = mapped_column(
        pg_enum(RoutingPolicyType, name="routing_policy_type"),
        nullable=True,
    )
    routing_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    routing_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    conversation: Mapped[Conversation] = relationship(lazy="selectin")
    selected_account: Mapped[AIAccount | None] = relationship(lazy="selectin")
    user_message: Mapped[Message] = relationship(
        foreign_keys=[user_message_id],
        lazy="selectin",
    )
    assistant_message: Mapped[Message | None] = relationship(
        foreign_keys=[assistant_message_id],
        lazy="selectin",
    )
