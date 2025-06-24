import secrets
from datetime import datetime, timedelta, timezone
from app.utils.config import settings


def generate_secret(length: int | None = None) -> str:
    """
    Generate a secure random user secret string.
    Uses URL-safe base64 encoding and trims to the required length.
    """
    length = length or settings.USER_SECRET_LENGTH
    return secrets.token_urlsafe(length)[:length]


def generate_api_key(length: int | None = None) -> str:
    """
    Generate a secure random API key string.
    URL-safe and clipped to length.
    """
    length = length or settings.API_KEY_LENGTH
    return secrets.token_urlsafe(length)[:length]


def get_secret_expiry() -> datetime:
    """
    Return the datetime at which a new secret should expire.
    """
    return datetime.now(timezone.utc) + timedelta(days=settings.USER_SECRET_EXPIRATION_DAYS)


def get_api_key_expiry() -> datetime:
    """
    Return the datetime at which a new API key should expire.
    """
    return datetime.now(timezone.utc) + timedelta(days=settings.API_KEY_EXPIRATION_DAYS)
