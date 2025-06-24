from typing import List
from uuid import UUID
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.transaction import run_in_transaction
from app.infrastructure.database.repository.restAPI.api_key_repository import get_all_active_keys
from app.infrastructure.database.repository.restAPI.user_repository import get_user_by_id
from app.models.schemas.rest.auth_schemas import APIKeyConfig
from app.utils.exceptions_base import AuthValidationError
from app.utils.hashing import verify_value
from app.models.DB_tables.user import User


class APIKeyAuthProcessor:
    _api_keys: List[APIKeyConfig] = []

    @classmethod
    async def load(cls) -> None:
        async with run_in_transaction() as session:
            db_keys = await get_all_active_keys(session)
            cls._api_keys = []

            for key_obj in db_keys:
                user = await get_user_by_id(session, key_obj.user_id)
                if not user:
                    continue

                cls._api_keys.append(APIKeyConfig(
                    user_id=key_obj.user_id,
                    key=SecretStr(key_obj.key),
                    expires_at=key_obj.expires_at,
                    role=user.role
                ))


    @classmethod
    def get_all(cls) -> List[APIKeyConfig]:
        return cls._api_keys

    @classmethod
    def add(cls, config: APIKeyConfig) -> None:
        cls._api_keys.append(config)
        print(f"API key added for user {config.user_id} with role {config.role} and value {config.key.get_secret_value()}")
    @classmethod
    def remove(cls, key_value: str) -> None:
        cls._api_keys = [k for k in cls._api_keys if k.key.get_secret_value() != key_value]

    @classmethod
    def replace(cls, config: APIKeyConfig) -> None:
        cls.remove(config.key.get_secret_value())
        cls.add(config)

    @classmethod
    def invalidate_user(cls, user_id: UUID) -> None:
        cls._api_keys = [k for k in cls._api_keys if k.user_id != user_id]

    @classmethod
    async def match(cls, raw_key: str) -> User:
        for config in cls._api_keys:
            if verify_value(raw_key, config.key.get_secret_value()):
                async with run_in_transaction() as session:
                    user = await get_user_by_id(session, config.user_id)
                    if not user:
                        raise AuthValidationError("User for API key not found")
                    return user

        raise AuthValidationError("Invalid or inactive API key")