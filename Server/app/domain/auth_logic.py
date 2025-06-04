from typing import List
from pydantic import BaseModel
import re

from app.utils.secret_utils import generate_secret, get_secret_expiry
from app.utils.hashing import hash_password
from app.utils.config import settings
from app.infrastructure.database.user_repository import get_user_by_email, create_user
from app.infrastructure.database.secret_repository import create_user_secret
from app.infrastructure.database.transaction import run_in_transaction


class OnboardResult(BaseModel):
    created_count: int
    users: List[str]
    skipped: List[str]


async def onboard_users_from_names(names: List[str]) -> OnboardResult:
    from sqlalchemy.ext.asyncio import AsyncSession

    created_users: List[str] = []
    skipped_users: List[str] = []

    async with run_in_transaction() as db:
        for name in names:
            name = name.strip()
            first, last = parse_full_name(name)
            email = f"{first.lower()}.{last.lower()}@tuni.fi"

            existing = await get_user_by_email(db, email)
            if existing:
                skipped_users.append(email)
                continue

            # Create user
            hashed_pw = hash_password(settings.DEFAULT_USER_PASSWORD)
            new_user = await create_user(
                db,
                email=email,
                username=f"{first}_{last}".lower(),
                hashed_password=hashed_pw,
                role="authenticated"
            )

            # Create secret (we rely on is_active = True to determine "current")
            await create_user_secret(
                db,
                user_id=new_user.id,
                secret=generate_secret(),
                label="temp",
                is_active=True,
                expires_at=get_secret_expiry()
            )

            created_users.append(email)

    return OnboardResult(
        created_count=len(created_users),
        users=created_users,
        skipped=skipped_users
    )


def parse_full_name(name: str) -> tuple[str, str]:
    parts = re.split(r"\s+", name.strip())
    if len(parts) < 2:
        return parts[0], "unknown"
    return parts[0], parts[-1]
