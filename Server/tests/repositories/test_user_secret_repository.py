import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.infrastructure.database.repository.restAPI import secret_repository
from app.models.DB_tables.user_secrets import UserSecret
from app.models.DB_tables.webhook import Webhook
from app.utils.exceptions_base import AppException


# ────── Dummy Session and Helpers ──────
class DummySession:
    def __init__(self, execute_result=None, get_result=None):
        self._execute_result = execute_result
        self._get_result = get_result
        self.added = None
        self.deleted = None
        self.committed = False

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self, stmt): return DummyExecute(self._execute_result)
    async def get(self, cls, sid): return self._get_result
    async def flush(self): pass
    async def commit(self): self.committed = True
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


def patch_run_tx(monkeypatch, session):
    monkeypatch.setattr(
        "app.infrastructure.database.repository.restAPI.secret_repository.run_in_transaction",
        lambda: session,
        raising=True
    )


# ────── Tests ──────

@pytest.mark.asyncio
async def test_create_user_secret_success(monkeypatch):
    sid = uuid4()
    user_id = uuid4()
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    session = DummySession()

    monkeypatch.setattr(
        "app.infrastructure.database.transaction.run_in_transaction",
        lambda: session
    )

    result = await secret_repository.create_user_secret(
        session, # type: ignore
        user_id=user_id,
        secret="abc123",
        label="primary",
        is_active=True,
        expires_at=expires
    )

    assert result.user_id == user_id
    assert session.added == result
    assert isinstance(result.expires_at, datetime)


@pytest.mark.asyncio
async def test_get_user_secret_by_id_found(monkeypatch):
    sid = uuid4()
    secret = UserSecret(id=sid)
    session = DummySession(execute_result=[secret])

    result = await secret_repository.get_user_secret_by_id(session, sid)# type: ignore
    assert result == secret


@pytest.mark.asyncio
async def test_get_all_active_user_secrets(monkeypatch):
    secrets = [UserSecret(id=uuid4(), is_active=True) for _ in range(2)]
    session = DummySession(execute_result=secrets)

    result = await secret_repository.get_all_active_user_secrets(session, uuid4())# type: ignore
    assert len(result) == 2
    assert all(s.is_active for s in result)


@pytest.mark.asyncio
async def test_get_user_secret_by_label(monkeypatch):
    label = "login"
    secret = UserSecret(label=label)
    session = DummySession(execute_result=[secret])

    result = await secret_repository.get_user_secret_by_label(session, uuid4(), label)# type: ignore
    assert result.label == label # type: ignore


@pytest.mark.asyncio
async def test_get_user_secrets(monkeypatch):
    secrets = [UserSecret(label=f"s{i}") for i in range(2)]
    session = DummySession(execute_result=secrets)

    result = await secret_repository.get_user_secrets(session, uuid4())# type: ignore
    assert len(result) == 2
    assert result[0].label.startswith("s")


@pytest.mark.asyncio
async def test_get_user_secret_labels(monkeypatch):
    secrets = [("label1",), ("label2",)]
    session = DummySession(execute_result=secrets)

    result = await secret_repository.get_user_secret_labels(session, uuid4(), is_active=True)# type: ignore
    assert result == ["label1", "label2"]


@pytest.mark.asyncio
async def test_get_user_secrets_info(monkeypatch):
    now = datetime.now(timezone.utc)
    data = [("alpha", True, now, now + timedelta(days=1))]
    session = DummySession(execute_result=data)

    result = await secret_repository.get_user_secrets_info(session, uuid4())# type: ignore
    assert isinstance(result, list)
    assert result[0]["label"] == "alpha"


@pytest.mark.asyncio
async def test_revoke_all_user_secrets(monkeypatch):
    session = DummySession()
    await secret_repository.revoke_all_user_secrets(session, uuid4())# type: ignore


@pytest.mark.asyncio
async def test_set_user_secret_active_status_true(monkeypatch):
    session = DummySession(execute_result=[object()])
    result = await secret_repository.set_user_secret_active_status(session, uuid4(), "login", True)# type: ignore
    assert result is True


@pytest.mark.asyncio
async def test_delete_user_secret_by_label(monkeypatch):
    session = DummySession(execute_result=[object()])
    result = await secret_repository.delete_user_secret_by_label(session, uuid4(), "old")# type: ignore
    assert result is True
