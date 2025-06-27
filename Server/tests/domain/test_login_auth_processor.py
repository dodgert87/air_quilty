import pytest
from uuid import uuid4
from collections import namedtuple

from app.domain.login_auth_processor import LoginAuthProcessor

DummyUser = namedtuple("DummyUser", ["id", "username", "role"])

@pytest.fixture
def dummy_user():
    return DummyUser(id=uuid4(), username="tester", role="admin")

@pytest.fixture
def dummy_token():
    return "dummy.jwt.token"

@pytest.mark.asyncio
async def test_add_and_get_session(dummy_user, dummy_token):
    LoginAuthProcessor._session_cache.clear()
    LoginAuthProcessor.add(dummy_token, dummy_user)
    retrieved = LoginAuthProcessor.get(dummy_token)
    assert retrieved == dummy_user

@pytest.mark.asyncio
async def test_remove_session(dummy_user, dummy_token):
    LoginAuthProcessor._session_cache.clear()
    LoginAuthProcessor.add(dummy_token, dummy_user)
    LoginAuthProcessor.remove(dummy_token)
    assert LoginAuthProcessor.get(dummy_token) is None

@pytest.mark.asyncio
async def test_replace_session(dummy_user, dummy_token):
    LoginAuthProcessor._session_cache.clear()
    LoginAuthProcessor.add(dummy_token, dummy_user)
    # simulate an updated user (same ID, different username)
    updated_user = DummyUser(id=dummy_user.id, username="updated", role="admin")
    LoginAuthProcessor.replace(dummy_token, updated_user) # type: ignore
    assert LoginAuthProcessor.get(dummy_token) == updated_user

@pytest.mark.asyncio
async def test_clear_user_sessions(dummy_user):
    LoginAuthProcessor._session_cache.clear()
    tokens = [f"token{i}" for i in range(3)]
    for t in tokens:
        LoginAuthProcessor.add(t, dummy_user)
    LoginAuthProcessor.clear_user_sessions(dummy_user.id)
    for t in tokens:
        assert LoginAuthProcessor.get(t) is None
