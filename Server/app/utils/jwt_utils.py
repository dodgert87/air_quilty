from datetime import datetime, timedelta, timezone
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError
from app.utils.config import settings
from typing import cast, Any, Dict


def generate_jwt(user_id: str, role: str, secret: str) -> tuple[str, int]:
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
    return token_str, exp_minutes * 60 # seconds


def decode_jwt(token: str, secret: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except DecodeError:
        raise ValueError("Invalid token")
    except InvalidTokenError:
        raise ValueError("Token validation failed")