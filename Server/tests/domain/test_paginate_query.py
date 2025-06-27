import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select, column
from pydantic import BaseModel

from app.domain.pagination import paginate_query
from app.utils.config import settings


# ── Fake Pydantic Schemas ────────────────────────────────────────────────────
class ItemSingle(BaseModel):
    name: str


class ItemMulti(BaseModel):
    name: str
    location: str


# ── Single-column query (uses result.scalars()) ──────────────────────────────
@pytest.mark.asyncio
@patch("app.domain.pagination.run_in_transaction")
async def test_paginate_query_single_column(mock_txn):
    fake_query = select(column("name"))

    # mocked DB session & results
    mock_session = AsyncMock()
    mock_session.scalar.return_value = 1  # total rows

    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [{"name": "sensor1"}]  # ← dict

    mock_result = AsyncMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars_result)
    mock_session.execute.return_value = mock_result
    mock_txn.return_value.__aenter__.return_value = mock_session

    result = await paginate_query(fake_query, ItemSingle, page=1, page_size=10)

    assert result.total == 1
    assert result.items == [ItemSingle(name="sensor1")]


# ── Multi-column query (uses result.mappings()) ──────────────────────────────
@pytest.mark.asyncio
@patch("app.domain.pagination.run_in_transaction")
async def test_paginate_query_multi_column(mock_txn):
    fake_query = select(column("name"), column("location"))

    mock_session = AsyncMock()
    mock_session.scalar.return_value = 2

    mock_mappings_result = MagicMock()
    mock_mappings_result.all.return_value = [
        {"name": "sensor1", "location": "lab"},
        {"name": "sensor2", "location": "field"},
    ]

    mock_result = AsyncMock()
    mock_result.mappings = MagicMock(return_value=mock_mappings_result)
    mock_session.execute.return_value = mock_result
    mock_txn.return_value.__aenter__.return_value = mock_session

    result = await paginate_query(fake_query, ItemMulti, page=1, page_size=5)

    assert result.total == 2
    assert result.items[1] == ItemMulti(name="sensor2", location="field")


# ── Default page-size fallback ───────────────────────────────────────────────
@pytest.mark.asyncio
@patch("app.domain.pagination.run_in_transaction")
async def test_paginate_query_uses_default_page_size(mock_txn):
    fake_query = select(column("name"))

    mock_session = AsyncMock()
    mock_session.scalar.return_value = 1

    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [{"name": "sensorX"}]

    mock_result = AsyncMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars_result)
    mock_session.execute.return_value = mock_result
    mock_txn.return_value.__aenter__.return_value = mock_session

    result = await paginate_query(fake_query, ItemSingle, page=2)

    assert result.page_size == settings.DEFAULT_PAGE_SIZE
    assert result.page == 2
    assert result.items[0] == ItemSingle(name="sensorX")
