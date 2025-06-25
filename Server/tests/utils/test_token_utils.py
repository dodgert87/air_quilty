from datetime import datetime, timedelta, timezone
import pytest
from app.utils.secret_utils import (
    generate_secret,
    generate_api_key,
    get_secret_expiry,
    get_api_key_expiry
)
from app.utils.config import settings


def test_generate_secret_default_length():
    key = generate_secret()
    assert isinstance(key, str)
    assert len(key) == settings.USER_SECRET_LENGTH


def test_generate_secret_custom_length():
    key = generate_secret(42)
    assert isinstance(key, str)
    assert len(key) == 42


def test_generate_api_key_default_length():
    key = generate_api_key()
    assert isinstance(key, str)
    assert len(key) == settings.API_KEY_LENGTH


def test_generate_api_key_custom_length():
    key = generate_api_key(48)
    assert isinstance(key, str)
    assert len(key) == 48


def test_get_secret_expiry_is_in_future():
    now = datetime.now(timezone.utc)
    expiry = get_secret_expiry()
    assert isinstance(expiry, datetime)
    assert expiry > now
    assert (expiry - now).days >= settings.USER_SECRET_EXPIRATION_DAYS - 1


def test_get_api_key_expiry_is_in_future():
    now = datetime.now(timezone.utc)
    expiry = get_api_key_expiry()
    assert isinstance(expiry, datetime)
    assert expiry > now
    assert (expiry - now).days >= settings.API_KEY_EXPIRATION_DAYS - 1
