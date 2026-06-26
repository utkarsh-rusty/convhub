import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

INVITATION_EXPIRE_DAYS = 7


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invitation_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=INVITATION_EXPIRE_DAYS)


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:200] or "workspace"


async def unique_slug(base_slug: str, exists_fn) -> str:
    candidate = base_slug
    if not await exists_fn(candidate):
        return candidate

    suffix = secrets.token_hex(3)
    candidate = f"{base_slug}-{suffix}"
    if not await exists_fn(candidate):
        return candidate

    return f"{base_slug}-{uuid.uuid4().hex[:8]}"
