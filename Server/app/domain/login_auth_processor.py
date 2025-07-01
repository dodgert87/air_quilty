from cachetools import TTLCache
from uuid import UUID
from app.models.DB_tables.user import User
from app.utils.config import settings
from loguru import logger


class LoginAuthProcessor:
    """
    In-memory cache for JWT login sessions.

    Provides:
    - Fast token-to-user lookup
    - Time-based expiry
    - Manual session invalidation by token or user ID
    """

    _session_cache: TTLCache[str, User] = TTLCache(
        maxsize=10000,  # Maximum number of cached tokens
        ttl=settings.JWT_EXPIRATION_MINUTES * 60  # Convert minutes to seconds
    )

    @classmethod
    def add(cls, token: str, user: User) -> None:
        """
        Store a new token-user session pair in memory.

        Args:
            token (str): JWT token string.
            user (User): Associated user.
        """
        cls._session_cache[token] = user
        logger.info("[LOGIN_SESSION] Added session | user_id=%s", user.id)

    @classmethod
    def get(cls, token: str) -> User | None:
        """
        Retrieve user associated with token, if still valid.

        Args:
            token (str): JWT token.

        Returns:
            User | None: Cached user or None if expired/missing.
        """
        user = cls._session_cache.get(token)
        if user:
            logger.debug("[LOGIN_SESSION] Cache hit | user_id=%s", user.id)
        else:
            logger.debug("[LOGIN_SESSION] Cache miss")
        return user

    @classmethod
    def remove(cls, token: str) -> None:
        """
        Remove a token from the cache (e.g. during logout).

        Args:
            token (str): JWT token to invalidate.
        """
        user = cls._session_cache.get(token)
        cls._session_cache.pop(token, None)
        logger.info("[LOGIN_SESSION] Removed session | user_id=%s", getattr(user, "id", "unknown"))

    @classmethod
    def replace(cls, token: str, user: User) -> None:
        """
        Replace the user object for a given token.

        Used when updating the user record (e.g. after password change).
        """
        cls._session_cache[token] = user
        logger.info("[LOGIN_SESSION] Replaced session | user_id=%s", user.id)

    @classmethod
    def clear_user_sessions(cls, user_id: UUID) -> None:
        """
        Remove all tokens associated with a specific user.

        Useful after password reset, logout all, etc.

        Args:
            user_id (UUID): Target user ID.
        """
        tokens_to_remove = [
            token for token, user in cls._session_cache.items()
            if user.id == user_id
        ]
        for token in tokens_to_remove:
            cls.remove(token)
        logger.info("[LOGIN_SESSION] Cleared sessions | user_id=%s | count=%d", user_id, len(tokens_to_remove))
