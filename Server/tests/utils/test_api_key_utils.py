import pytest
from app.utils.api_key_utils import generate_api_key

def test_generate_api_key_default_length():
    key = generate_api_key()
    assert isinstance(key, str)
    assert 40 <= len(key) <= 50  # base64 encoding can vary slightly


@pytest.mark.parametrize("length", [16, 32, 64])
def test_generate_api_key_valid_lengths(length):
    key = generate_api_key(length)
    assert isinstance(key, str)
    assert len(key) > 0


@pytest.mark.parametrize("invalid_length", [0, 15, 65, 100])
def test_generate_api_key_invalid_lengths(invalid_length):
    with pytest.raises(ValueError) as exc_info:
        generate_api_key(invalid_length)
    assert "length should be between" in str(exc_info.value)


def test_generate_api_keys_are_random():
    key1 = generate_api_key()
    key2 = generate_api_key()
    assert key1 != key2
