import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.models.DB_tables.user import User
from app.infrastructure.database.repository.restAPI import user_repository
from app.utils.exceptions_base import AppException

# ────── Dummy Session and Helpers ──────
class DummySession:
    def __init__(self, execute_result=None, get_result=None):
        self._execute_result = execute_result
        self._get_result = get_result
        self.added = None
        self.deleted = None
        self.committed = False
        self.refreshed = None
        self.flushed = False

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self, stmt): return DummyExecute(self._execute_result)
    async def get(self, cls, sid): return self._get_result
    async def flush(self): self.flushed = True
    async def commit(self): self.committed = True
    async def refresh(self, obj): self.refreshed = obj
    def add(self, obj): self.added = obj
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
async def test_get_user_by_email_found():
    user = User(email="test@example.com")
    session = DummySession(execute_result=[user])

    result = await user_repository.get_user_by_email(session, "test@example.com") #type: ignore
    assert result == user


@pytest.mark.asyncio
async def test_create_user_success():
    session = DummySession()
    email = "test@example.com"
    username = "testuser"
    hashed_password = "hashed_pw"

    result = await user_repository.create_user(
        session , email, username, hashed_password, role="authenticated" #type: ignore
    )

    assert result.email == email
    assert result.username == username
    assert session.added == result
    assert session.committed
    assert session.refreshed == result


@pytest.mark.asyncio
async def test_update_user_secret_ref_executes_and_flushes():
    user_id = uuid4()
    secret_id = uuid4()
    session = DummySession()

    await user_repository.update_user_secret_ref(session, user_id, secret_id) #type: ignore
    assert session.flushed


@pytest.mark.asyncio
async def test_get_user_by_id_found():
    user = User(id=uuid4())
    session = DummySession(execute_result=[user])

    result = await user_repository.get_user_by_id(session, user.id) #type: ignore
    assert result == user


@pytest.mark.asyncio
async def test_update_user_password_ok():
    session = DummySession()
    await user_repository.update_user_password(session, uuid4(), "new_hash")#type: ignore


@pytest.mark.asyncio
async def test_update_last_login_ok():
    session = DummySession()
    await user_repository.update_last_login(session, uuid4())#type: ignore


@pytest.mark.asyncio
async def test_delete_user_ok():
    session = DummySession()
    await user_repository.delete_user(session, uuid4())#type: ignore


@pytest.mark.asyncio
async def test_get_all_users_returns_list():
    users = [User(email="a@test.com"), User(email="b@test.com")]
    session = DummySession(execute_result=users)

    result = await user_repository.get_all_users(session)#type: ignore
    assert result == users
    assert isinstance(result, list)
    assert isinstance(result[0], User)
