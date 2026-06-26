from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ai_request import AIRequest
    from app.models.user import User
    from app.models.workspace import Workspace


class BorrowRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "borrow_records"
    __table_args__ = (
        Index("ix_borrow_records_workspace_id", "workspace_id"),
        Index("ix_borrow_records_request_id", "request_id"),
        Index("ix_borrow_records_borrower_user_id", "borrower_user_id"),
        Index("ix_borrow_records_lender_user_id", "lender_user_id"),
    )

    request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    borrower_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    lender_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ai_request: Mapped[AIRequest] = relationship(lazy="selectin")
    workspace: Mapped[Workspace] = relationship(lazy="selectin")
    borrower: Mapped[User] = relationship(foreign_keys=[borrower_user_id], lazy="selectin")
    lender: Mapped[User] = relationship(foreign_keys=[lender_user_id], lazy="selectin")
