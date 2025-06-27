import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.models.DB_tables.sensor import Sensor
from app.models.schemas.rest.sensor_schemas import SensorCreate, SensorUpdate
from app.infrastructure.database.repository.restAPI import sensor_repository
from app.utils.exceptions_base import AppException


class DummySession:
    def __init__(self, get_result=None, execute_result=None):
        self._get_result = get_result
        self._execute_result = execute_result
        self.added = None
        self.deleted = None

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def get(self, cls, sid): return self._get_result
    async def execute(self, stmt): return DummyExecute(self._execute_result)
    def add(self, obj): self.added = obj
    async def delete(self, obj): self.deleted = obj


class DummyExecute:
    def __init__(self, items): self.items = items
    def scalars(self): return DummyScalars(self.items)


class DummyScalars:
    def __init__(self, items): self.items = items
    def all(self): return self.items


def patch_run_tx(monkeypatch, session):
    monkeypatch.setattr(
        "app.infrastructure.database.repository.restAPI.sensor_repository.run_in_transaction",
        lambda: session
    )
    monkeypatch.setattr(
        "app.infrastructure.database.transaction.run_in_transaction",
        lambda: session
    )


@pytest.mark.asyncio
async def test_insert_sensor_conflict_raises(monkeypatch):
    sid = uuid4()

    async def mock_fetch(sensor_id): return Sensor(sensor_id=sid)
    monkeypatch.setattr(sensor_repository, "fetch_sensor_by_id", mock_fetch)
    patch_run_tx(monkeypatch, DummySession())

    data = SensorCreate(sensor_id=sid, name="test", location="lab", is_active=True)
    with pytest.raises(AppException) as e:
        await sensor_repository.insert_sensor(data)
    assert "already exists" in str(e.value)


@pytest.mark.asyncio
async def test_insert_sensor_success(monkeypatch):
    sid = uuid4()

    async def mock_fetch(sensor_id): return None
    monkeypatch.setattr(sensor_repository, "fetch_sensor_by_id", mock_fetch)
    session = DummySession()
    patch_run_tx(monkeypatch, session)

    data = SensorCreate(sensor_id=sid, name="Test", location="Lab", is_active=True)
    sensor = await sensor_repository.insert_sensor(data)

    assert isinstance(sensor, Sensor)
    assert sensor.sensor_id == sid
    assert session.added is sensor


@pytest.mark.asyncio
async def test_fetch_sensor_by_id_found(monkeypatch):
    sid = uuid4()
    sensor = Sensor(sensor_id=sid)
    patch_run_tx(monkeypatch, DummySession(get_result=sensor))

    result = await sensor_repository.fetch_sensor_by_id(sid)
    assert result == sensor


@pytest.mark.asyncio
async def test_fetch_sensor_by_id_none(monkeypatch):
    patch_run_tx(monkeypatch, DummySession(get_result=None))
    result = await sensor_repository.fetch_sensor_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_fetch_all_sensors_returns(monkeypatch):
    sensors = [Sensor(sensor_id=uuid4()) for _ in range(3)]
    patch_run_tx(monkeypatch, DummySession(execute_result=sensors))

    result = await sensor_repository.fetch_all_sensors()
    assert isinstance(result, list)
    assert len(result) == 3
    assert isinstance(result[0], Sensor)


@pytest.mark.asyncio
async def test_modify_sensor_updates_fields(monkeypatch):
    sid = uuid4()
    sensor = Sensor(sensor_id=sid, location="old", model="old", is_active=False)
    patch_run_tx(monkeypatch, DummySession(get_result=sensor))

    update = SensorUpdate(location="new", model="new", is_active=True)
    result = await sensor_repository.modify_sensor(sid, update)

    assert result is not None
    assert result.location == "new"
    assert result.model == "new"
    assert result.is_active is True
    assert isinstance(result.updated_at, datetime)


@pytest.mark.asyncio
async def test_modify_sensor_not_found_returns_none(monkeypatch):
    patch_run_tx(monkeypatch, DummySession(get_result=None))

    result = await sensor_repository.modify_sensor(uuid4(), SensorUpdate(model="X"))
    assert result is None


@pytest.mark.asyncio
async def test_remove_sensor_success(monkeypatch):
    sid = uuid4()
    sensor = Sensor(sensor_id=sid)
    session = DummySession(get_result=sensor)
    patch_run_tx(monkeypatch, session)

    result = await sensor_repository.remove_sensor(sid)
    assert result is True
    assert session.deleted == sensor


@pytest.mark.asyncio
async def test_remove_sensor_not_found(monkeypatch):
    session = DummySession(get_result=None)
    patch_run_tx(monkeypatch, session)

    result = await sensor_repository.remove_sensor(uuid4())
    assert result is False
