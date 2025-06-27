from typing import List
from uuid import UUID
from pydantic import SecretStr
from loguru import logger

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
                    logger.warning("[API_KEY] Skipping key: user not found | user_id=%s", key_obj.user_id)
                    continue

                config = APIKeyConfig(
                    user_id=key_obj.user_id,
                    key=SecretStr(key_obj.key),
                    expires_at=key_obj.expires_at,
                    role=user.role
                )
                cls._api_keys.append(config)

            logger.info("[API_KEY] Loaded %d API keys", len(cls._api_keys))

    @classmethod
    def get_all(cls) -> List[APIKeyConfig]:
        return cls._api_keys

    @classmethod
    def add(cls, config: APIKeyConfig) -> None:
        cls._api_keys.append(config)
        logger.info("[API_KEY] Added | user_id=%s | role=%s", config.user_id, config.role)

    @classmethod
    def remove(cls, key_value: str) -> None:
        before = len(cls._api_keys)
        cls._api_keys = [
            k for k in cls._api_keys if not verify_value(key_value, k.key.get_secret_value())
        ]
        after = len(cls._api_keys)
        logger.info("[API_KEY] Removed key | count_removed=%d", before - after)

    @classmethod
    def replace(cls, config: APIKeyConfig) -> None:
        logger.info("[API_KEY] Replacing key | user_id=%s", config.user_id)
        cls.invalidate_user(config.user_id)  # remove all keys for the user
        cls.add(config)

    @classmethod
    def invalidate_user(cls, user_id: UUID) -> None:
        before = len(cls._api_keys)
        cls._api_keys = [k for k in cls._api_keys if k.user_id != user_id]
        after = len(cls._api_keys)
        logger.info("[API_KEY] Invalidated keys for user | user_id=%s | count_removed=%d", user_id, before - after)

    @classmethod
    async def match(cls, raw_key: str) -> User:
        for config in cls._api_keys:
            if verify_value(raw_key, config.key.get_secret_value()):
                async with run_in_transaction() as session:
                    user = await get_user_by_id(session, config.user_id)
                    if not user:
                        logger.error("[API_KEY] Matched key but user not found | user_id=%s", config.user_id)
                        raise AuthValidationError("User for API key not found")

                    logger.info("[API_KEY] Match found | user_id=%s | role=%s", user.id, user.role)
                    return user

        logger.warning("[API_KEY] No match for provided key")
        raise AuthValidationError("Invalid or inactive API key")