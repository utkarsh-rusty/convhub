from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.core.config import Settings
from app.core.jwt import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expires_at,
)
from app.core.password import hash_password, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def register(self, data: RegisterRequest) -> UserResponse:
        user = User(
            email=data.email.lower(),
            name=data.name,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)

        try:
            await self.db.commit()
            await self.db.refresh(user)
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            ) from exc

        return UserResponse.model_validate(user)

    async def login(self, data: LoginRequest) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == data.email.lower()))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        tokens = await self._issue_tokens(user.id, device_name=data.device_name)
        await self.db.commit()
        return tokens

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        token_record = await self._get_valid_refresh_token(raw_refresh_token)
        token_record.revoked_at = datetime.now(UTC)

        tokens = await self._issue_tokens(
            user_id=token_record.user_id,
            device_name=token_record.device_name,
        )
        await self.db.commit()
        return tokens

    async def logout(self, raw_refresh_token: str) -> None:
        token_record = await self._get_valid_refresh_token(raw_refresh_token)
        token_record.revoked_at = datetime.now(UTC)
        await self.db.commit()

    async def _issue_tokens(self, user_id: UUID, device_name: str | None) -> TokenResponse:
        access_token = create_access_token(user_id=user_id, settings=self.settings)
        raw_refresh_token = generate_refresh_token()
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_refresh_token),
            device_name=device_name,
            expires_at=refresh_token_expires_at(self.settings),
        )
        self.db.add(refresh_token)
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
        )

    async def _get_valid_refresh_token(self, raw_refresh_token: str) -> RefreshToken:
        token_hash = hash_refresh_token(raw_refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()

        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        if token_record.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        if token_record.expires_at <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )

        return token_record
