import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.infrastructure.database.transaction import run_in_transaction
from app.models.DB_tables.user import User, RoleEnum
from app.models.DB_tables.api_keys import APIKey
from app.infrastructure.database.repository.restAPI.api_key_repository import (
    create_api_key,
    delete_api_key_by_label,
    get_api_keys_by_user,
    get_active_api_key,
    get_all_active_keys,
    revoke_all_user_api_keys,
    delete_all_user_api_keys,
)


async def seed_user(session):
    """Helper to insert a test user and return its ID."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email="testuser@example.com",
        username="testuser",
        hashed_password="irrelevant-hash",
        role=RoleEnum.authenticated,
        created_at=datetime.now(timezone.utc),
        last_login=None,
    )
    session.add(user)
    await session.flush()
    return user_id


@pytest.mark.asyncio
async def test_create_api_key_success():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        key = "testkey123"
        result = await create_api_key(session, user_id=user_id, key=key, label="test-label")
        await session.flush()

        assert result.key == key
        assert result.user_id == user_id
        assert result.is_active


@pytest.mark.asyncio
async def test_delete_api_key_by_label_success():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        key = "label-delete-key"
        label = "delete-me"
        await create_api_key(session, user_id, key, label)
        await session.flush()

        deleted = await delete_api_key_by_label(session, user_id, label)
        assert deleted == key


@pytest.mark.asyncio
async def test_delete_api_key_by_label_returns_none_if_not_found():
    async with run_in_transaction() as session:
        deleted = await delete_api_key_by_label(session, uuid4(), "nonexistent-label")
        assert deleted is None


@pytest.mark.asyncio
async def test_get_api_keys_by_user_returns_all_keys():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        await create_api_key(session, user_id, "key1")
        await session.flush()
        await create_api_key(session, user_id, "key2")
        await session.flush()

        keys = await get_api_keys_by_user(session, user_id)
        assert len(keys) == 2
        assert {k.key for k in keys} == {"key1", "key2"}


@pytest.mark.asyncio
async def test_get_active_api_key_success():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        key = "active-key"
        await create_api_key(session, user_id, key)
        await session.flush()

        found = await get_active_api_key(session, key)
        assert found is not None
        assert found.key == key


@pytest.mark.asyncio
async def test_get_active_api_key_inactive_returns_none():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        key = "inactive-key"
        apikey = await create_api_key(session, user_id, key)
        apikey.is_active = False
        await session.flush()

        found = await get_active_api_key(session, key)
        assert found is None


@pytest.mark.asyncio
async def test_get_all_active_keys_returns_only_active():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        await create_api_key(session, user_id, "active1")
        await session.flush()
        inactive = await create_api_key(session, user_id, "inactive1")
        inactive.is_active = False
        await session.flush()

        keys = await get_all_active_keys(session)
        assert all(k.is_active for k in keys)
        assert "inactive1" not in {k.key for k in keys}


@pytest.mark.asyncio
async def test_revoke_all_user_api_keys_sets_all_inactive():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        await create_api_key(session, user_id, "r1")
        await session.flush()
        await create_api_key(session, user_id, "r2")
        await session.flush()

        await revoke_all_user_api_keys(session, user_id)
        await session.flush()

        keys = await get_api_keys_by_user(session, user_id)
        assert all(not k.is_active for k in keys)


@pytest.mark.asyncio
async def test_delete_all_user_api_keys_deletes_keys():
    async with run_in_transaction() as session:
        user_id = await seed_user(session)

        await create_api_key(session, user_id, "d1")
        await session.flush()
        await create_api_key(session, user_id, "d2")
        await session.flush()

        await delete_all_user_api_keys(session, user_id)
        await session.flush()

        keys = await get_api_keys_by_user(session, user_id)
        assert keys == []
