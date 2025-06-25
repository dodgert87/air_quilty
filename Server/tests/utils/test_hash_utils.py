import pytest
from app.utils.hashing import hash_value, verify_value


def test_hash_value_valid_string():
    hashed = hash_value("my_password")
    assert isinstance(hashed, str)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_hash_value_empty_string_raises():
    with pytest.raises(ValueError):
        hash_value("")


def test_hash_value_non_string_raises():
    with pytest.raises(ValueError):
        hash_value(12345)  # type: ignore


def test_verify_value_correct_match_returns_true():
    raw = "secret123"
    hashed = hash_value(raw)
    assert verify_value(raw, hashed) is True


def test_verify_value_incorrect_match_returns_false():
    hashed = hash_value("correct_password")
    assert verify_value("wrong_password", hashed) is False


def test_verify_value_with_empty_inputs_returns_false():
    assert verify_value("", "") is False
    assert verify_value("something", "") is False
    assert verify_value("", "something") is False
