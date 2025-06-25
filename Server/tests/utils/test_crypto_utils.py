import pytest
from app.utils.crypto_utils import encrypt_secret, decrypt_secret, MASTER_KEY


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_encrypt_secret_valid_string():
    result = encrypt_secret("test_secret")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_encrypt_secret_empty_string_raises():
    with pytest.raises(ValueError):
        encrypt_secret("")


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_encrypt_secret_non_string_raises():
    with pytest.raises(ValueError):
        encrypt_secret(12345)  # type: ignore


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_decrypt_secret_valid_encrypted_string():
    original = "another_secret"
    encrypted = encrypt_secret(original)
    decrypted = decrypt_secret(encrypted)
    assert decrypted == original


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_decrypt_secret_empty_string_raises():
    with pytest.raises(ValueError):
        decrypt_secret("")


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_decrypt_secret_non_string_raises():
    with pytest.raises(ValueError):
        decrypt_secret(99999)  # type: ignore


def test_encrypt_secret_with_missing_master_key_raises(monkeypatch):
    monkeypatch.setattr("app.utils.crypto_utils.MASTER_KEY", None)
    with pytest.raises(RuntimeError):
        encrypt_secret("secret")


def test_decrypt_secret_with_missing_master_key_raises(monkeypatch):
    monkeypatch.setattr("app.utils.crypto_utils.MASTER_KEY", None)
    with pytest.raises(RuntimeError):
        decrypt_secret("ZmFrZV9lbmNyeXB0ZWRfZGF0YQ==")


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_encrypt_decrypt_round_trip_consistency():
    original = "round_trip_value"
    encrypted = encrypt_secret(original)
    decrypted = decrypt_secret(encrypted)
    assert decrypted == original


@pytest.mark.skipif(MASTER_KEY is None, reason="MASTER_KEY not initialized")
def test_decrypt_secret_with_tampered_ciphertext_raises():
    original = "tamper_test"
    encrypted = encrypt_secret(original)
    tampered = encrypted[:-1] + ("A" if encrypted[-1] != "A" else "B")
    with pytest.raises(RuntimeError):
        decrypt_secret(tampered)
