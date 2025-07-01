from pydantic import SecretStr
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.DB_tables.api_keys import APIKey
from app.utils.exceptions_base import AuthConflictError, AuthValidationError, UserNotFoundError
from app.models.DB_tables.user_secrets import UserSecret
from app.models.schemas.rest.auth_schemas import LoginResponse, NewUserInput, OnboardResult, SecretCreateRequest, SecretInfo
from app.domain import auth_logic
from app.models.DB_tables.user import User



# -------------------------------
# USER ONBOARDING
# -------------------------------
@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_by_email", new_callable=AsyncMock)
@patch("app.domain.auth_logic.create_user", new_callable=AsyncMock)
@patch("app.domain.auth_logic.create_user_secret", new_callable=AsyncMock)
@patch("app.domain.auth_logic.hash_value", return_value="hashed_pw")
@patch("app.domain.auth_logic.generate_secret", return_value="secret123")
@patch("app.domain.auth_logic.encrypt_secret", return_value="encrypted123")
@patch("app.domain.auth_logic.get_secret_expiry", return_value=datetime.now(timezone.utc) + timedelta(days=30))
async def test_onboard_users_from_inputs_success(
    mock_expiry,
    mock_encrypt,
    mock_generate,
    mock_hash,
    mock_create_secret,
    mock_create_user,
    mock_get_user,
    mock_run_txn,
):
    mock_session = MagicMock()
    mock_run_txn.return_value.__aenter__.return_value = mock_session

    # One new user and one existing user
    inputs = [
        NewUserInput(name="Alice Smith", role="developer"),
        NewUserInput(name="Bob Jones", role="guest"),
    ]

    # First user doesn't exist, second one does
    mock_get_user.side_effect = [None, MagicMock()]

    # Mock user object to return from create_user
    mock_user = User(
        id=uuid4(),
        email="alice.smith@tuni.fi",
        username="alice_smith",
        hashed_password="hashed_pw",
        role="developer",
        created_at=datetime.now(timezone.utc),
        last_login=None
    )
    mock_create_user.return_value = mock_user
    mock_create_secret.return_value = UserSecret(
        id=uuid4(),
        user_id=mock_user.id,
        secret="encrypted123",
        label="login",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        expires_at=mock_expiry.return_value,
        revoked_at=None
    )

    result: OnboardResult = await auth_logic.onboard_users_from_inputs(inputs)

    assert result.created_count == 1
    assert "alice.smith@tuni.fi" in result.users
    assert "bob.jones@tuni.fi" in result.skipped

    mock_create_user.assert_called_once()
    mock_create_secret.assert_called_once()


@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_by_email", new_callable=AsyncMock)
@patch("app.domain.auth_logic.create_user", new_callable=AsyncMock)
@patch("app.domain.auth_logic.create_user_secret", new_callable=AsyncMock)
@patch("app.domain.auth_logic.hash_value", return_value="hashed_pw")
@patch("app.domain.auth_logic.generate_secret", return_value="secret123")
@patch("app.domain.auth_logic.encrypt_secret", return_value="encrypted123")
@patch("app.domain.auth_logic.get_secret_expiry", return_value=datetime.now(timezone.utc) + timedelta(days=30))
async def test_onboard_users_handles_exception(
    mock_expiry,
    mock_encrypt,
    mock_generate,
    mock_hash,
    mock_create_secret,
    mock_create_user,
    mock_get_user,
    mock_run_txn,
):
    mock_session = MagicMock()
    mock_run_txn.return_value.__aenter__.return_value = mock_session

    inputs = [
        NewUserInput(name="Crash Dummy", role="admin"),
    ]

    mock_get_user.return_value = None
    mock_create_user.side_effect = Exception("Simulated DB failure")

    result = await auth_logic.onboard_users_from_inputs(inputs)

    assert result.created_count == 0
    assert result.users == []
    assert "crash.dummy@tuni.fi" in result.skipped
    mock_create_user.assert_called_once()


# -------------------------------
# AUTHENTICATION & LOGIN
# -------------------------------




# ─────────────────────────────────────────────────────────────
# change_user_password
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.secret_repository")
@patch("app.domain.auth_logic.api_key_repository")
@patch("app.domain.auth_logic.user_repository")
async def test_change_user_password_success(mock_user_repo, mock_api_repo, mock_secret_repo, mock_txn, dummy_user):
    mock_session = AsyncMock()
    mock_txn.return_value.__aenter__.return_value = mock_session

    mock_user_repo.update_user_password = AsyncMock()
    mock_secret_repo.revoke_all_user_secrets = AsyncMock()
    mock_api_repo.revoke_all_user_api_keys = AsyncMock()
    mock_secret_repo.create_user_secret = AsyncMock()

    await auth_logic.change_user_password(dummy_user, "old_password", "NewPass123!")


@pytest.mark.asyncio
async def test_change_user_password_wrong_old(dummy_user):
    with pytest.raises(AuthValidationError, match="Auth validation error"):
        await auth_logic.change_user_password(dummy_user, "wrong_old", "NewPass123!")


@pytest.mark.asyncio
async def test_change_user_password_weak_new(dummy_user):
    with pytest.raises(AuthValidationError, match="Auth validation error"):
        await auth_logic.change_user_password(dummy_user, "old_password", "123")


# ─────────────────────────────────────────────────────────────
# login_user
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_by_email")
@patch("app.domain.auth_logic.get_user_secret_by_label")
@patch("app.domain.auth_logic.update_last_login")
@patch("app.domain.auth_logic.generate_jwt")
async def test_login_user_success(mock_jwt, mock_update, mock_get_secret, mock_get_user, mock_txn, dummy_user):
    mock_session = AsyncMock()
    mock_txn.return_value.__aenter__.return_value = mock_session

    secret = auth_logic.encrypt_secret("login_secret")
    dummy_secret = UserSecret(
        id=uuid4(),
        user_id=dummy_user.id,
        secret=secret,
        label="login",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    mock_get_user.return_value = dummy_user
    mock_get_secret.return_value = dummy_secret
    mock_jwt.return_value = ("jwt.token.here", 3600)

    result = await auth_logic.login_user(dummy_user.email, "old_password")
    assert isinstance(result, LoginResponse)
    assert result.access_token == "jwt.token.here"
    assert result.expires_in == 3600


@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_by_email")
async def test_login_user_wrong_password(mock_get_user, mock_txn, dummy_user):
    mock_session = AsyncMock()
    mock_txn.return_value.__aenter__.return_value = mock_session

    dummy_user.hashed_password = auth_logic.hash_value("correct_password")
    mock_get_user.return_value = dummy_user

    with pytest.raises(AuthValidationError, match="Auth validation error"):
        await auth_logic.login_user(dummy_user.email, "wrong_password")


# ─────────────────────────────────────────────────────────────
# validate_token_and_get_user
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_by_id")
@patch("app.domain.auth_logic.get_user_secret_by_label")
@patch("app.domain.auth_logic.decode_jwt_unverified")
@patch("app.domain.auth_logic.decode_jwt")
async def test_validate_token_success(mock_decode, mock_unverified, mock_get_secret, mock_get_user, mock_txn, dummy_user):
    mock_session = AsyncMock()
    mock_txn.return_value.__aenter__.return_value = mock_session

    dummy_secret = UserSecret(
        id=uuid4(),
        user_id=dummy_user.id,
        secret=auth_logic.encrypt_secret("jwt_secret"),
        label="login",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    mock_unverified.return_value = {"sub": str(dummy_user.id)}
    mock_get_secret.return_value = dummy_secret
    mock_get_user.return_value = dummy_user

    user = await auth_logic.validate_token_and_get_user("valid.token")
    assert user.id == dummy_user.id


@pytest.mark.asyncio
async def test_validate_token_invalid_format():
    with pytest.raises(AuthValidationError, match="Auth validation error"):
        await auth_logic.validate_token_and_get_user("invalid")



# -------------------------------
# API KEY MANAGEMENT
# -------------------------------



@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.get_api_keys_by_user")
@patch("app.domain.auth_logic.api_key_repository.create_api_key")
@patch("app.domain.auth_logic.run_in_transaction")
async def test_generate_api_key_success(mock_txn, mock_create, mock_get_keys, dummy_user):
    mock_session = AsyncMock()
    mock_txn.return_value.__aenter__.return_value = mock_session
    mock_get_keys.return_value = []

    result = await auth_logic.generate_api_key_for_user(dummy_user.id, "main")

    assert isinstance(result.raw_key, str)
    assert isinstance(result.hashed_key, SecretStr)



@pytest.mark.asyncio
@patch("app.domain.auth_logic.settings")
@patch("app.domain.auth_logic.api_key_repository.get_api_keys_by_user")
@patch("app.domain.auth_logic.run_in_transaction")
async def test_generate_api_key_limit_exceeded(mock_txn, mock_get_keys, mock_settings, dummy_user):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_settings.MAX_API_KEYS_PER_USER = 2
    mock_get_keys.return_value = [
        APIKey(
            key="$2b$12$" + "A" * 53,  # valid bcrypt hash pattern
            user_id=dummy_user.id,
            label="a",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )
    ] * 2

    with pytest.raises(AuthConflictError) as exc:
        await auth_logic.generate_api_key_for_user(dummy_user.id, "label")
    assert "limit reached" in str(exc.value)

@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.get_api_keys_by_user")
@patch("app.domain.auth_logic.run_in_transaction")
async def test_generate_api_key_duplicate_label(mock_txn, mock_get_keys, dummy_user):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_get_keys.return_value = [
        APIKey(
            key="$2b$12$" + "B" * 53,
            user_id=dummy_user.id,
            label="existing",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )
    ]

    with pytest.raises(AuthConflictError) as exc:
        await auth_logic.generate_api_key_for_user(dummy_user.id, "existing")
    assert "already in use" in str(exc.value)


@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.get_api_keys_by_user")
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.generate_api_key")
@patch("app.domain.auth_logic.hash_value")
@patch("app.domain.auth_logic.verify_value")
async def test_generate_api_key_collision(mock_verify, mock_hash, mock_gen, mock_txn, mock_get_keys, dummy_user):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_gen.return_value = "abc123"
    mock_hash.return_value = "$2b$12$" + "X" * 53
    mock_verify.return_value = True  # simulate a key collision

    mock_get_keys.return_value = [
        APIKey(
            key="$2b$12$" + "X" * 53,
            user_id=dummy_user.id,
            label="any",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
        )
    ]

    with pytest.raises(AuthConflictError) as exc:
        await auth_logic.generate_api_key_for_user(dummy_user.id, "label")
    assert "matches existing one" in str(exc.value)


@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.get_all_active_keys")
@patch("app.domain.auth_logic.get_user_by_id")
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.verify_value")
async def test_validate_api_key_success(mock_verify, mock_txn, mock_get_user, mock_get_keys, dummy_user):
    mock_verify.return_value = True
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_get_user.return_value = dummy_user

    dummy_key = APIKey(key="hashed", user_id=dummy_user.id, label="x", is_active=True,
                       created_at=datetime.now(timezone.utc), expires_at=datetime.now(timezone.utc))
    mock_get_keys.return_value = [dummy_key]

    user = await auth_logic.validate_api_key("raw-key")
    assert user.id == dummy_user.id


@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.get_all_active_keys")
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.verify_value")
async def test_validate_api_key_invalid(mock_verify, mock_txn, mock_get_keys):
    mock_verify.return_value = False
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_get_keys.return_value = []

    with pytest.raises(AuthValidationError) as exc:
        await auth_logic.validate_api_key("bad-key")
    assert "API key" in str(exc.value) or "Invalid" in str(exc.value)

@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.delete_api_key_by_label")
@patch("app.domain.auth_logic.run_in_transaction")
async def test_delete_api_key_success(mock_txn, mock_delete, dummy_user):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_delete.return_value = "main"

    result = await auth_logic.delete_api_key_for_user(dummy_user.id, "main")
    assert result == "main"


@pytest.mark.asyncio
@patch("app.domain.auth_logic.api_key_repository.delete_api_key_by_label")
@patch("app.domain.auth_logic.run_in_transaction")
async def test_delete_api_key_not_found(mock_txn, mock_delete, dummy_user):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_delete.return_value = None

    with pytest.raises(UserNotFoundError, match="not found"):
        await auth_logic.delete_api_key_for_user(dummy_user.id, "not-real")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_user() -> User:
    """Standalone user object used across admin-utility tests."""
    return User(
        id=uuid4(),
        email="test.user@tuni.fi",
        username="test_user",
        hashed_password=auth_logic.hash_value("old_password"),
        role="authenticated",
        created_at=datetime.now(timezone.utc),
        last_login=None,
    )

@pytest.fixture
def dummy_secret(dummy_user) -> UserSecret:
    return UserSecret(
        id=uuid4(),
        user_id=dummy_user.id,
        secret="enc-secret",
        label="login",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        revoked_at=None
    )

# ---------------------------------------------------------------------------
# Tests: get_user_and_active_secret
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_by_id", new_callable=AsyncMock)
@patch("app.domain.auth_logic.get_all_active_user_secrets", new_callable=AsyncMock)
async def test_get_user_and_active_secret(
    mock_get_secrets: AsyncMock,
    mock_get_user: AsyncMock,
    mock_txn,
    dummy_user: User,
    dummy_secret: UserSecret,
):
    # simulate successful DB transaction
    mock_txn.return_value.__aenter__.return_value = MagicMock()

    # stub repository helpers
    mock_get_user.return_value = dummy_user
    mock_get_secrets.return_value = [dummy_secret]

    user, secret = await auth_logic.get_user_and_active_secret(dummy_user.id)

    assert user.id == dummy_user.id
    assert secret.label == "login"


# ---------------------------------------------------------------------------
# Tests: get_user_profile_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.user_repository.get_user_by_id", new_callable=AsyncMock)
@patch("app.domain.auth_logic.secret_repository.get_user_secrets", new_callable=AsyncMock)
@patch("app.domain.auth_logic.api_key_repository.get_api_keys_by_user", new_callable=AsyncMock)
async def test_get_user_profile_data(
    mock_get_keys: AsyncMock,
    mock_get_secrets: AsyncMock,
    mock_get_user: AsyncMock,
    mock_txn,
    dummy_user: User,
    dummy_secret: UserSecret,
    dummy_key: APIKey,
):
    mock_txn.return_value.__aenter__.return_value = MagicMock()
    mock_get_user.return_value = dummy_user
    mock_get_secrets.return_value = [dummy_secret]
    mock_get_keys.return_value = [dummy_key]

    profile = await auth_logic.get_user_profile_data(dummy_user.id)

    assert profile["email"] == dummy_user.email
    assert profile["secrets"][0]["label"] == "login"
    assert profile["api_keys"][0]["label"] == "main"


# ---------------------------------------------------------------------------
# Tests: find_user_info
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.user_repository.get_user_by_id", new_callable=AsyncMock)
async def test_find_user_info_by_id(
    mock_get_user: AsyncMock,
    mock_txn,
    dummy_user: User,
):
    mock_txn.return_value.__aenter__.return_value = MagicMock()
    mock_get_user.return_value = dummy_user

    found = await auth_logic.find_user_info(dummy_user.id, None, None)
    assert found is not None
    assert found.id == dummy_user.id


@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.user_repository.get_user_by_email", new_callable=AsyncMock)
async def test_find_user_info_by_email(
    mock_get_email: AsyncMock,
    mock_txn,
    dummy_user: User,
):
    mock_txn.return_value.__aenter__.return_value = MagicMock()
    mock_get_email.return_value = dummy_user

    found = await auth_logic.find_user_info(None, dummy_user.email, None)
    assert found is not None
    assert found.email == dummy_user.email


@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.user_repository.get_user_by_email", new_callable=AsyncMock)
async def test_find_user_info_by_name(
    mock_get_email: AsyncMock,
    mock_txn,
    dummy_user: User,
):
    mock_txn.return_value.__aenter__.return_value = MagicMock()
    mock_get_email.return_value = dummy_user

    found = await auth_logic.find_user_info(None, None, "Test User")
    # Any uniquely identifying attribute works; we reuse email for simplicity
    assert found is not None
    assert found.email == dummy_user.email


# ---------------------------------------------------------------------------
# Tests: delete_user_by_identifier
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.user_repository.delete_user", new_callable=AsyncMock)
@patch("app.domain.auth_logic.api_key_repository.delete_all_user_api_keys", new_callable=AsyncMock)
@patch("app.domain.auth_logic.secret_repository.delete_user_secrets", new_callable=AsyncMock)
@patch("app.domain.auth_logic.find_user_info", new_callable=AsyncMock)
async def test_delete_user_by_identifier(
    mock_find_user: AsyncMock,
    mock_delete_secrets: AsyncMock,
    mock_delete_keys: AsyncMock,
    mock_delete_user: AsyncMock,
    mock_txn,
    dummy_user: User,
):
    mock_txn.return_value.__aenter__.return_value = MagicMock()
    mock_find_user.return_value = dummy_user

    deleted_email = await auth_logic.delete_user_by_identifier(dummy_user.id, None, None)

    mock_delete_secrets.assert_awaited_with(  # ensure cascade deletion occurs
        mock_txn.return_value.__aenter__.return_value, dummy_user.id
    )
    mock_delete_keys.assert_awaited()
    mock_delete_user.assert_awaited()
    assert deleted_email == dummy_user.email


# ---------------------------------------------------------------------------
# Tests: get_all_users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.user_repository.get_all_users", new_callable=AsyncMock)
async def test_get_all_users(
    mock_get_all: AsyncMock,
    mock_txn,
    dummy_user: User,
):
    mock_txn.return_value.__aenter__.return_value = MagicMock()
    mock_get_all.return_value = [dummy_user]

    users = await auth_logic.get_all_users()

    mock_get_all.assert_awaited()
    assert len(users) == 1
    assert users[0].id == dummy_user.id


# -------------------------------
# SECRET MANAGEMENT
# -------------------------------
user_id = uuid4()



@pytest.fixture
def dummy_key(dummy_user) -> APIKey:
    return APIKey(
        key="keyhash",
        user_id=dummy_user.id,
        label="main",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
    )

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.get_user_secrets_info")
async def test_get_secret_info_for_user(mock_repo_fn, mock_txn):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_repo_fn.return_value = [{
        "label": "login",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc)
    }]

    result = await auth_logic.get_secret_info_for_user(user_id)
    assert isinstance(result[0], SecretInfo)
    assert result[0].label == "login"

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.create_user_secret")
@patch("app.domain.auth_logic.encrypt_secret")
@patch("app.domain.auth_logic.generate_secret")
async def test_create_secret_for_user(mock_gen, mock_enc, mock_create, mock_txn, dummy_secret):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_gen.return_value = "plain-secret"
    mock_enc.return_value = "enc-secret"
    mock_create.return_value = dummy_secret

    payload = SecretCreateRequest(label="login", is_active=True, expires_at=None)
    response = await auth_logic.create_secret_for_user(user_id, payload)

    assert response.label == "login"
    assert response.secret == "plain-secret"

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.delete_user_secret_by_label")
async def test_delete_secret_by_label_success(mock_delete, mock_txn):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_delete.return_value = True

    result = await auth_logic.delete_secret_by_label(user_id, "login")
    assert result == "login"

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.delete_user_secret_by_label")
async def test_delete_secret_by_label_not_found(mock_delete, mock_txn):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_delete.return_value = False

    with pytest.raises(AuthValidationError):
        await auth_logic.delete_secret_by_label(user_id, "missing")

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.set_user_secret_active_status")
async def test_set_secret_active_status_success(mock_toggle, mock_txn):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_toggle.return_value = True

    result = await auth_logic.set_secret_active_status(user_id, "login", False)
    assert result == "login"

@pytest.mark.asyncio
@patch("app.domain.auth_logic.run_in_transaction")
@patch("app.domain.auth_logic.set_user_secret_active_status")
async def test_set_secret_active_status_not_found(mock_toggle, mock_txn):
    mock_txn.return_value.__aenter__.return_value = AsyncMock()
    mock_toggle.return_value = False

    with pytest.raises(AuthValidationError):
        await auth_logic.set_secret_active_status(user_id, "login", True)