from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_value(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Cannot hash an empty or non-string value.")
    return pwd_context.hash(value)


def verify_value(plain_value: str, hashed_value: str) -> bool:
    if not plain_value or not hashed_value:
        return False
    return pwd_context.verify(plain_value, hashed_value)