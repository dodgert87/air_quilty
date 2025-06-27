import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from typing import List
from pydantic import SecretStr

from app.utils.hashing import hash_value, verify_value
from app.models.DB_tables.user import RoleEnum
from app.domain.api_key_processor import APIKeyAuthProcessor
from app.models.schemas.rest.auth_schemas import APIKeyConfig
from app.utils.exceptions_base import AuthValidationError


class DummyUser:
    def __init__(self, id, role):
        self.id = id
        self.role = role


@pytest.fixture
def valid_key_config():
    return APIKeyConfig(
        user_id=uuid4(),
        key=SecretStr(hash_value("my-secret")),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        role=RoleEnum.admin
    )


@pytest.mark.asyncio
async def test_add_and_get_all_keys(valid_key_config):
    APIKeyAuthProcessor._api_keys.clear()
    APIKeyAuthProcessor.add(valid_key_config)

    keys = APIKeyAuthProcessor.get_all()
    assert isinstance(keys, List)
    assert len(keys) == 1
    assert keys[0].user_id == valid_key_config.user_id


@pytest.mark.asyncio
async def test_remove_key(valid_key_config):
    raw_key = "my-secret"
    APIKeyAuthProcessor._api_keys = [valid_key_config]
    assert verify_value(raw_key, valid_key_config.key.get_secret_value())
    APIKeyAuthProcessor.remove(raw_key)
    assert len(APIKeyAuthProcessor._api_keys) == 0

@pytest.mark.asyncio
async def test_replace_key(valid_key_config):
    APIKeyAuthProcessor._api_keys = [valid_key_config]

    new_key_plain = "my-secret"  # same as original, but new hash
    new_config = APIKeyConfig(
        user_id=valid_key_config.user_id,
        key=SecretStr(hash_value(new_key_plain)),
        expires_at=valid_key_config.expires_at,
        role=valid_key_config.role
    )

    APIKeyAuthProcessor.replace(new_config)
    keys = APIKeyAuthProcessor.get_all()
    assert len(keys) == 1
    assert verify_value(new_key_plain, keys[0].key.get_secret_value())


@pytest.mark.asyncio
async def test_invalidate_user(valid_key_config):
    APIKeyAuthProcessor._api_keys = [valid_key_config]
    APIKeyAuthProcessor.invalidate_user(valid_key_config.user_id)
    assert len(APIKeyAuthProcessor._api_keys) == 0


@pytest.mark.asyncio
async def test_match_success(monkeypatch, valid_key_config):
    APIKeyAuthProcessor._api_keys = [valid_key_config]
    dummy_user = DummyUser(valid_key_config.user_id, valid_key_config.role)

    async def mock_get_user_by_id(session, uid):
        return dummy_user

    monkeypatch.setattr(
        "app.domain.api_key_processor.get_user_by_id",
        mock_get_user_by_id
    )

    result = await APIKeyAuthProcessor.match("my-secret")
    assert result.id == valid_key_config.user_id
    assert result.role == valid_key_config.role

@pytest.mark.asyncio
async def test_match_fail(monkeypatch):
    APIKeyAuthProcessor._api_keys = []
    with pytest.raises(AuthValidationError):
        await APIKeyAuthProcessor.match("wrong-key")
