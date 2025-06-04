from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from datetime import datetime, timezone
from app.models.user_secrets import UserSecret

async def create_user_secret(
    db: AsyncSession,
    user_id,
    secret: str,
    label: str,
    is_active: bool,
    expires_at: datetime,
) -> UserSecret:
    new_secret = UserSecret(
        id=uuid4(),
        user_id=user_id,
        secret=secret,
        label=label,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        revoked_at=None
    )

    db.add(new_secret)
    await db.flush()     # flush so it's ready in the same transaction
    return new_secret
