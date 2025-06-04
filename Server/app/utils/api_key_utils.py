import secrets

def generate_api_key(length: int = 32) -> str:
    return secrets.token_urlsafe(length)
