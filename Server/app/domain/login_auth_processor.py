from cachetools import TTLCache
from uuid import UUID
from app.models.DB_tables.user import User
from pydantic import SecretStr
from datetime import timedelta
from app.utils.config import settings



class LoginAuthProcessor:
    # Cache JWT token → User
    _session_cache: TTLCache[str, User] = TTLCache(
        maxsize=10000,
        ttl=settings.JWT_EXPIRATION_MINUTES * 60  # convert minutes to seconds
    )

    @classmethod
    def add(cls, token: str, user: User) -> None:
        cls._session_cache[token] = user

    @classmethod
    def get(cls, token: str) -> User | None:
        return cls._session_cache.get(token)

    @classmethod
    def remove(cls, token: str) -> None:
        cls._session_cache.pop(token, None)

    @classmethod
    def replace(cls, token: str, user: User) -> None:
        cls._session_cache[token] = user

    @classmethod
    def clear_user_sessions(cls, user_id: UUID) -> None:
        tokens_to_remove = [
            token for token, user in cls._session_cache.items()
            if user.id == user_id
        ]
        for token in tokens_to_remove:
            cls.remove(token)