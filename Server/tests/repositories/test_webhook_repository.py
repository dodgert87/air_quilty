import pytest
from uuid import uuid4
from app.infrastructure.database.repository.webhook import webhook_repository
from app.models.DB_tables.webhook import Webhook
from app.utils.exceptions_base import AppException


# ────── Dummy Mocks ──────
class DummySession:
    def __init__(self, execute_result=None):
        self._execute_result = execute_result
        self.added = None
        self.flushed = False

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self, stmt): return DummyExecute(self._execute_result)
    async def flush(self): self.flushed = True
    def add(self, obj): self.added = obj


class DummyExecute:
    def __init__(self, items, rowcount=None):
        self._items = items
        self._rowcount = rowcount if rowcount is not None else len(items)
    def scalar_one_or_none(self): return self._items[0] if self._items else None
    def scalars(self): return DummyScalars(self._items)
    def all(self): return self._items
    @property
    def rowcount(self): return self._rowcount


class DummyScalars:
    def __init__(self, items): self.items = items
    def all(self): return self.items


# ────── Tests ──────

@pytest.mark.asyncio
async def test_get_webhooks_by_user_returns_list():
    uid = uuid4()
    webhooks = [Webhook(user_id=uid), Webhook(user_id=uid)]
    session = DummySession(execute_result=webhooks)

    result = await webhook_repository.get_webhooks_by_user(session, uid) #type: ignore
    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_webhooks_by_user_and_event():
    uid = uuid4()
    w = Webhook(user_id=uid, event_type="ALERT")
    session = DummySession(execute_result=[w])

    result = await webhook_repository.get_webhooks_by_user_and_event(session, uid, "ALERT")#type: ignore
    assert result[0].event_type == "ALERT"


@pytest.mark.asyncio
async def test_get_active_webhooks_by_event():
    w1 = Webhook(event_type="ALERT", enabled=True)
    w2 = Webhook(event_type="*", enabled=True)
    session = DummySession(execute_result=[w1, w2])

    result = await webhook_repository.get_active_webhooks_by_event(session, "ALERT")#type: ignore
    assert all(w.enabled for w in result)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_webhook_by_id_and_user_found():
    uid = uuid4()
    wid = uuid4()
    session = DummySession(execute_result=[Webhook(id=wid, user_id=uid)])

    result = await webhook_repository.get_webhook_by_id_and_user(session, wid, uid)#type: ignore
    assert result is not None
    assert result.id == wid


@pytest.mark.asyncio
async def test_create_webhook_success():
    w = Webhook(id=uuid4(), user_id=uuid4())
    session = DummySession()

    result = await webhook_repository.create_webhook(session, w)#type: ignore
    assert result == w
    assert session.flushed is True
    assert session.added == w


@pytest.mark.asyncio
async def test_create_webhook_error():
    class BrokenSession(DummySession):
        async def flush(self): raise Exception("DB fail")

    w = Webhook(id=uuid4(), user_id=uuid4())

    with pytest.raises(AppException) as exc:
        await webhook_repository.create_webhook(BrokenSession(), w)  # type: ignore[arg-type]
    assert "Failed to create webhook:" in str(exc.value)

@pytest.mark.asyncio
async def test_update_webhook_success():
    w = Webhook(id=uuid4(), user_id=uuid4())
    session = DummySession()

    result = await webhook_repository.update_webhook(session, w)#type: ignore
    assert result == w
    assert session.flushed is True


@pytest.mark.asyncio
async def test_update_webhook_error():
    class BrokenSession(DummySession):
        async def flush(self): raise Exception("fail")

    w = Webhook(id=uuid4(), user_id=uuid4())

    with pytest.raises(AppException) as exc:
        await webhook_repository.update_webhook(BrokenSession(), w)  # type: ignore[arg-type]
    assert "Failed to update webhook" in str(exc.value)


@pytest.mark.asyncio
async def test_delete_webhook_success():
    uid = uuid4()
    wid = uuid4()
    session = DummySession()

    async def fake_execute(stmt): return DummyExecute([], rowcount=1)
    session.execute = fake_execute

    ok = await webhook_repository.delete_webhook(session, wid, uid)  # type: ignore[arg-type]
    assert ok is True


@pytest.mark.asyncio
async def test_delete_webhook_not_found():
    uid = uuid4()
    wid = uuid4()
    session = DummySession()

    async def fake_execute(stmt): return DummyExecute([], rowcount=0)
    session.execute = fake_execute

    result = await webhook_repository.delete_webhook(session, wid, uid)  # type: ignore[arg-type]
    assert result is False

@pytest.mark.asyncio
async def test_delete_webhook_error():
    class BrokenSession(DummySession):
        async def execute(self, stmt): raise Exception("delete error")

    with pytest.raises(AppException) as exc:
        await webhook_repository.delete_webhook(BrokenSession(), uuid4(), uuid4())  # type: ignore[arg-type]
    assert "Failed to delete webhook" in str(exc.value)