import secrets
import string
from datetime import datetime, timedelta, timezone

from app.utils.config import settings


def generate_secret(length: int | None = None) -> str:
    """
    Generate a secure random user secret.
    """
    length = length or settings.USER_SECRET_LENGTH
    return secrets.token_urlsafe(length)[:length]


def generate_api_key(length: int | None = None) -> str:
    """
    Generate a secure random API key string.
    """
    length = length or settings.API_KEY_LENGTH
    return secrets.token_urlsafe(length)[:length]


def get_secret_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.USER_SECRET_EXPIRATION_DAYS)


def get_api_key_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.API_KEY_EXPIRATION_DAYS)
