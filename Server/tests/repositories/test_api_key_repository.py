import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.models.DB_tables.api_keys import APIKey
from app.infrastructure.database.repository.restAPI import api_key_repository
from app.utils.exceptions_base import AppException


# ────── Dummy Mocks ──────
class DummySession:
    def __init__(self, execute_result=None):
        self._execute_result = execute_result
        self.added = None
        self.deleted = None
        self.flushed = False

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self, stmt): return DummyExecute(self._execute_result)
    def add(self, obj): self.added = obj
    async def flush(self): self.flushed = True
    async def commit(self): pass
    async def delete(self, obj): self.deleted = obj


class DummyExecute:
    def __init__(self, items): self._items = items
    def scalar_one_or_none(self): return self._items[0] if self._items else None
    def scalars(self): return DummyScalars(self._items)
    def all(self): return self._items
    @property
    def rowcount(self): return len(self._items)


class DummyScalars:
    def __init__(self, items): self.items = items
    def all(self): return self.items


# ────── Tests ──────

@pytest.mark.asyncio
async def test_create_api_key_success():
    session = DummySession()
    key = "abc123"
    user_id = uuid4()

    result = await api_key_repository.create_api_key(
        session, #type: ignore
        user_id=user_id,
        key=key,
        label="login",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    assert isinstance(result, APIKey)
    assert session.added == result
    assert result.key == key
    assert result.user_id == user_id
    assert result.is_active is True


@pytest.mark.asyncio
async def test_delete_api_key_by_label_found():
    session = DummySession(execute_result=["abc123"])
    user_id = uuid4()

    deleted_key = await api_key_repository.delete_api_key_by_label(session, user_id, "login")#type: ignore
    assert deleted_key == "abc123"


@pytest.mark.asyncio
async def test_get_api_keys_by_user_returns_list():
    user_id = uuid4()
    keys = [APIKey(user_id=user_id), APIKey(user_id=user_id)]
    session = DummySession(execute_result=keys)

    result = await api_key_repository.get_api_keys_by_user(session, user_id)#type: ignore
    assert isinstance(result, list)
    assert all(isinstance(k, APIKey) for k in result)


@pytest.mark.asyncio
async def test_get_active_api_key_found():
    api_key = APIKey(key="xyz", is_active=True)
    session = DummySession(execute_result=[api_key])

    result = await api_key_repository.get_active_api_key(session, "xyz")#type: ignore
    assert result == api_key


@pytest.mark.asyncio
async def test_get_all_active_keys_returns_list():
    keys = [APIKey(is_active=True), APIKey(is_active=True)]
    session = DummySession(execute_result=keys)

    result = await api_key_repository.get_all_active_keys(session)#type: ignore
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(k.is_active for k in result)


@pytest.mark.asyncio
async def test_revoke_all_user_api_keys_success():
    session = DummySession()
    await api_key_repository.revoke_all_user_api_keys(session, uuid4())#type: ignore


@pytest.mark.asyncio
async def test_delete_all_user_api_keys_success():
    session = DummySession()
    await api_key_repository.delete_all_user_api_keys(session, uuid4())#type: ignore
