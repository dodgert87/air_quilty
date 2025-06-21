import base64
import os
from loguru import logger
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.utils.config import settings



try:
    raw_key = settings.MASTER_ENCRYPTION_KEY.get_secret_value()
    if not raw_key:
        raise ValueError("MASTER_ENCRYPTION_KEY is not set in the environment.")

    MASTER_KEY = base64.urlsafe_b64decode(raw_key)
    if len(MASTER_KEY) not in (16, 24, 32):  # AES key sizes: 128/192/256 bits
        raise ValueError("MASTER_ENCRYPTION_KEY must decode to 16, 24, or 32 bytes.")

except Exception as e:
    logger.exception(f"Failed to initialize encryption key: {e}")
    MASTER_KEY = None  # Prevents silent failures later

def encrypt_secret(secret: str) -> str:
    """
    Encrypts a secret string using AES-GCM and returns a base64-encoded string.
    """
    if not isinstance(secret, str) or not secret.strip():
        logger.error("encrypt_secret: Input must be a non-empty string.")
        raise ValueError("Cannot encrypt an empty or non-string value.")

    if MASTER_KEY is None:
        raise RuntimeError("Encryption key not initialized.")

    try:
        nonce = os.urandom(12)  # Random 96-bit nonce (needed per operation)
        aesgcm = AESGCM(MASTER_KEY)
        ciphertext = aesgcm.encrypt(nonce, secret.encode('utf-8'), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')
    except Exception as e:
        logger.exception("encrypt_secret: Encryption failed.")
        raise RuntimeError("Encryption failed.")

def decrypt_secret(encoded: str) -> str:
    if not isinstance(encoded, str) or not encoded.strip():
        logger.error("decrypt_secret: Input must be a non-empty string.")
        raise ValueError("Cannot decrypt an empty or non-string value.")

    if MASTER_KEY is None:
        raise RuntimeError("Decryption key not initialized.")

    try:
        data = base64.urlsafe_b64decode(encoded.encode('utf-8'))
        nonce, ciphertext = data[:12], data[12:]
        aesgcm = AESGCM(MASTER_KEY)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception as e:
        logger.exception("decrypt_secret: Decryption failed.")
        raise RuntimeError("Decryption failed.")