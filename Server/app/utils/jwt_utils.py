from datetime import datetime, timedelta, timezone
from typing import cast, Any, Dict

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError
from jwt import InvalidSignatureError

from app.utils.config import settings


def generate_jwt(user_id: str, role: str, secret: str) -> tuple[str, int]:
    """
    Generate a signed JWT with role and user ID.
    """
    exp_minutes = settings.JWT_EXPIRATION_MINUTES
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=exp_minutes)

    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires.timestamp())
    }

    token_raw = jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)
    token_str = token_raw.decode("utf-8") if isinstance(token_raw, bytes) else cast(str, token_raw)

    return token_str, exp_minutes * 60  # seconds


def decode_jwt(token: str, secret: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except InvalidSignatureError:
        raise ValueError("Token validation failed")
    except DecodeError:
        raise ValueError("Invalid token")
    except InvalidTokenError:
        raise ValueError("Token validation failed")


def decode_jwt_unverified(token: str) -> Dict[str, Any]:
    """
    Decode JWT without verifying its signature (e.g., to extract 'sub' early).
    """
    return jwt.decode(token, key="", options={"verify_signature": False})
