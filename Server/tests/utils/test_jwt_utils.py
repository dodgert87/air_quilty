from datetime import datetime, timedelta, timezone
import time
from unittest.mock import patch
import jwt
import pytest
from app.utils.jwt_utils import generate_jwt, decode_jwt, decode_jwt_unverified
from app.utils.config import settings


def test_generate_jwt_returns_valid_token_and_expiry():
    token, expiry = generate_jwt("user123", "admin", "mysecret")
    assert isinstance(token, str)
    assert expiry == settings.JWT_EXPIRATION_MINUTES * 60


def test_decode_jwt_returns_original_payload():
    secret = "supersecret"
    user_id = "abc123"
    role = "developer"
    token, _ = generate_jwt(user_id, role, secret)
    payload = decode_jwt(token, secret)
    assert payload["sub"] == user_id
    assert payload["role"] == role


def test_decode_jwt_with_expired_token_raises():
    # Manually generate expired token
    now = datetime.now(timezone.utc)
    past = now - timedelta(minutes=10)

    payload = {
        "sub": "u",
        "role": "admin",
        "iat": int(past.timestamp()),
        "nbf": int(past.timestamp()),
        "exp": int((past + timedelta(seconds=1)).timestamp())  # expires long ago
    }

    token = jwt.encode(payload, "s", algorithm=settings.JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    with pytest.raises(ValueError, match="Token has expired"):
        decode_jwt(token, "s") # type: ignore


def test_decode_jwt_with_invalid_signature_raises():
    token, _ = generate_jwt("userx", "admin", "original_secret")
    with pytest.raises(ValueError, match="Token validation failed"):
        decode_jwt(token, "wrong_secret")


def test_decode_jwt_with_malformed_token_raises():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_jwt("this.is.not.jwt", "secret")


def test_decode_jwt_unverified_extracts_payload():
    token, _ = generate_jwt("u42", "guest", "secret")
    payload = decode_jwt_unverified(token)
    assert payload["sub"] == "u42"
    assert payload["role"] == "guest"
