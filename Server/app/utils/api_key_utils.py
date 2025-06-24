import secrets

def generate_api_key(length: int = 32) -> str:
    """
    Generates a secure, URL-safe API key using the secrets module.
    Default length (32) gives ~43-character base64-encoded string.
    """
    if length < 16 or length > 64:
        raise ValueError("API key length should be between 16 and 64 bytes.")
    return secrets.token_urlsafe(length)