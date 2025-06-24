from cachetools import TTLCache
from uuid import UUID
from app.models.DB_tables.user import User
from app.utils.config import settings
from loguru import logger


class LoginAuthProcessor:
    _session_cache: TTLCache[str, User] = TTLCache(
        maxsize=10000,
        ttl=settings.JWT_EXPIRATION_MINUTES * 60  # convert minutes to seconds
    )

    @classmethod
    def add(cls, token: str, user: User) -> None:
        cls._session_cache[token] = user
        logger.info("[LOGIN_SESSION] Added session | user_id=%s", user.id)

    @classmethod
    def get(cls, token: str) -> User | None:
        user = cls._session_cache.get(token)
        if user:
            logger.debug("[LOGIN_SESSION] Cache hit | user_id=%s", user.id)
        else:
            logger.debug("[LOGIN_SESSION] Cache miss")
        return user

    @classmethod
    def remove(cls, token: str) -> None:
        user = cls._session_cache.get(token)
        cls._session_cache.pop(token, None)
        logger.info("[LOGIN_SESSION] Removed session | user_id=%s", getattr(user, "id", "unknown"))

    @classmethod
    def replace(cls, token: str, user: User) -> None:
        cls._session_cache[token] = user
        logger.info("[LOGIN_SESSION] Replaced session | user_id=%s", user.id)

    @classmethod
    def clear_user_sessions(cls, user_id: UUID) -> None:
        tokens_to_remove = [
            token for token, user in cls._session_cache.items()
            if user.id == user_id
        ]
        for token in tokens_to_remove:
            cls.remove(token)
        logger.info("[LOGIN_SESSION] Cleared sessions | user_id=%s | count=%d", user_id, len(tokens_to_remove))
