import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.models.DB_tables.sensor import Sensor
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorUpdate
from app.infrastructure.database.repository.restAPI import sensor_repository
from app.utils.exceptions_base import AppException

# ──────────────────────────────────────────────────────────────────────────────
# Dummy session – identical to your previous one
# ──────────────────────────────────────────────────────────────────────────────
class DummySession:
    def __init__(self, get_result=None, execute_result=None):
        self._get_result = get_result
        self._execute_result = execute_result
        self.added = None
        self.deleted = None

    async def __aenter__(self): return self
    async def __aexit__(self, *exc): pass

    async def get(self, cls, sid):    # cls is always Sensor for these tests
        return self._get_result

    async def execute(self, stmt):    # used only by fetch_all
        return DummyExecute(self._execute_result)

    def add(self, obj): self.added = obj
    async def delete(self, obj): self.deleted = obj


class DummyExecute:
    def __init__(self, items): self._items = items
    def scalars(self): return DummyScalars(self._items)


class DummyScalars:
    def __init__(self, items): self._items = items
    def all(self): return self._items


# ──────────────────────────────────────────────────────────────────────────────
# Helpers to patch run_in_transaction once per-test
# ──────────────────────────────────────────────────────────────────────────────
def patch_run_tx(monkeypatch, session: DummySession):
    """Redirect *both* copies of run_in_transaction to the DummySession."""
    monkeypatch.setattr(
        "app.infrastructure.database.repository.restAPI.sensor_repository.run_in_transaction",
        lambda: session,
        raising=True
    )
    # Safety-belt: also patch the original path in case some code imports it directly
    monkeypatch.setattr(
        "app.infrastructure.database.transaction.run_in_transaction",
        lambda: session,
        raising=True
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_insert_sensor_conflict_raises(monkeypatch):
    sid = uuid4()
    async def mock_fetch(sensor_id): return Sensor(sensor_id=sid)

    monkeypatch.setattr(sensor_repository, "fetch_sensor_by_id", mock_fetch, raising=True)
    patch_run_tx(monkeypatch, DummySession())  # still needed for the WITH-block

    payload = SensorCreate(sensor_id=sid, name="test", location="lab", is_active=True)
    with pytest.raises(AppException) as exc:
        await sensor_repository.insert_sensor(payload)
    assert "already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_insert_sensor_success(monkeypatch):
    sid = uuid4()

    async def mock_fetch(sensor_id): return None
    monkeypatch.setattr(sensor_repository, "fetch_sensor_by_id", mock_fetch, raising=True)

    sess = DummySession()
    patch_run_tx(monkeypatch, sess)

    payload = SensorCreate(sensor_id=sid, name="Test", location="Lab", is_active=True)
    sensor = await sensor_repository.insert_sensor(payload)

    assert isinstance(sensor, Sensor)
    assert sensor.sensor_id == sid
    assert sess.added is sensor                      # was added to session


@pytest.mark.asyncio
async def test_fetch_sensor_by_id_found(monkeypatch):
    sid = uuid4(); target = Sensor(sensor_id=sid)
    patch_run_tx(monkeypatch, DummySession(get_result=target))

    result = await sensor_repository.fetch_sensor_by_id(sid)
    assert result == target


@pytest.mark.asyncio
async def test_fetch_sensor_by_id_none(monkeypatch):
    patch_run_tx(monkeypatch, DummySession(get_result=None))
    assert await sensor_repository.fetch_sensor_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_fetch_all_sensors(monkeypatch):
    sensors = [Sensor(sensor_id=uuid4()) for _ in range(4)]
    patch_run_tx(monkeypatch, DummySession(execute_result=sensors))

    result = await sensor_repository.fetch_all_sensors()
    assert result == sensors


@pytest.mark.asyncio
async def test_modify_sensor_updates(monkeypatch):
    sid = uuid4()
    obj = Sensor(sensor_id=sid, location="old", model="old", is_active=False)
    patch_run_tx(monkeypatch, DummySession(get_result=obj))

    upd = SensorUpdate(location="new", model="new", is_active=True)
    updated = await sensor_repository.modify_sensor(sid, upd)

    # ---- tell the type checker it's definitely a Sensor ----
    assert updated is not None
    assert updated.location == "new"
    assert updated.model == "new"
    assert updated.is_active is True
    assert isinstance(updated.updated_at, datetime)

@pytest.mark.asyncio
async def test_modify_sensor_not_found(monkeypatch):
    patch_run_tx(monkeypatch, DummySession(get_result=None))
    out = await sensor_repository.modify_sensor(uuid4(), SensorUpdate(model="x"))
    assert out is None


@pytest.mark.asyncio
async def test_remove_sensor_success(monkeypatch):
    sid = uuid4(); obj = Sensor(sensor_id=sid)
    session = DummySession(get_result=obj)
    patch_run_tx(monkeypatch, session)

    ok = await sensor_repository.remove_sensor(sid)
    assert ok is True
    assert session.deleted is obj


@pytest.mark.asyncio
async def test_remove_sensor_not_found(monkeypatch):
    session = DummySession(get_result=None)
    patch_run_tx(monkeypatch, session)

    assert await sensor_repository.remove_sensor(uuid4()) is False
