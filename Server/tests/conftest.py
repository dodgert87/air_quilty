import asyncio
import sys
import pytest
import pytest_asyncio
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI, Depends
from app.infrastructure.database.init_db import init_db
from app.models.DB_tables.user import User, RoleEnum


# ---------------------------------------------------------------------------
# Initialize DB once for test session
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_db():
    await init_db()


@pytest.fixture(scope="session", autouse=True)
def _set_selector_event_loop_policy():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ---------------------------------------------------------------------------
# Shared dummy user and token
# ---------------------------------------------------------------------------
@pytest.fixture
def dummy_user() -> User:
    return User(id=uuid4(), email="tester@example.com", role=RoleEnum.authenticated)


@pytest.fixture
def token() -> str:
    return "dummy.jwt.token"


# ---------------------------------------------------------------------------
# FastAPI app with LoginAuthMiddleware and mocked dependencies
# ---------------------------------------------------------------------------
@pytest.fixture
def app(monkeypatch, dummy_user, token) -> FastAPI:
    from app.middleware.login_auth_middleware import LoginAuthMiddleware
    from app.utils import jwt_utils
    from app.infrastructure.database import transaction
    from app.infrastructure.database.repository.restAPI import user_repository, secret_repository
    from app.utils import crypto_utils

    # Patch JWT decode helpers
    monkeypatch.setattr(jwt_utils, "decode_jwt_unverified", lambda _t: {"sub": str(dummy_user.id)}, raising=False)
    monkeypatch.setattr(jwt_utils, "decode_jwt", lambda _t, **_: None, raising=False)

    # Patch DB context
    class _FakeCM:
        async def __aenter__(self):
            return SimpleNamespace()
        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(transaction, "run_in_transaction", lambda *a, **k: _FakeCM(), raising=False)

    # Patch secret repo, user repo, and decryption
    monkeypatch.setattr(
        secret_repository,
        "get_user_secret_by_label",
        lambda _s, _uid, label="login": SimpleNamespace(secret="encrypted", is_active=True),
        raising=False,
    )
    monkeypatch.setattr(
        user_repository,
        "get_user_by_id",
        lambda _s, _uid: dummy_user,
        raising=False,
    )
    monkeypatch.setattr(
        crypto_utils,
        "decrypt_secret",
        lambda s: "plaintext" if s == "encrypted" else s,
        raising=False,
    )

    # Build app
    app = FastAPI()
    app.add_middleware(LoginAuthMiddleware)

    @app.get("/api/v1/auth/authenticated")
    async def protected(request=Depends(lambda r: r)):
        return {"user_id": request.state.user_id}

    @app.get("/api/v1/auth/admin")
    async def admin(request=Depends(lambda r: r)):
        return {"admin_access": True}

    return app
