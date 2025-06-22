"""Unit tests for AuthService - comprehensive testing of authentication and authorization."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.core.constants import RoleID
from app.domain.exceptions import AuthenticationError, ValidationError
from app.models.user_model import User
from app.schemas.auth_schema import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService


class TestAuthService:
    """Test suite for AuthService."""

    @pytest.fixture
    def mock_uow(self):
        """Mock Unit of Work."""
        uow = Mock()
        uow.users = Mock()
        uow.commit = Mock()
        uow.rollback = Mock()
        uow.__enter__ = Mock(return_value=uow)
        uow.__exit__ = Mock(return_value=None)
        return uow

    @pytest.fixture
    def auth_service(self, mock_uow):
        """Create AuthService instance with mocked dependencies."""
        return AuthService(mock_uow)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            user_id=str(uuid4()),
            username="test_user",
            email="test@example.com",
            password_hash="hashed_password",
            role_id=RoleID.USER.value,
            is_active=True,
            email_verified=True,
        )

    def test_register_user_success(self, auth_service, mock_uow):
        """Test successful user registration."""
        register_data = RegisterRequest(
            username="newuser",
            email="new@example.com",
            password="password123",
            first_name="John",
            surname="Doe",
        )

        mock_uow.users.get_by_email.return_value = None
        mock_uow.users.get_by_username.return_value = None
        mock_uow.users.add.return_value = None

        with patch("app.services.auth_service.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"

            result = auth_service.register_user(register_data)

            assert result is not None
            mock_uow.users.add.assert_called_once()
            mock_uow.commit.assert_called_once()

    def test_register_user_email_exists(
        self, auth_service, mock_uow, sample_user
    ):
        """Test registration with existing email."""
        register_data = RegisterRequest(
            username="newuser",
            email="test@example.com",
            password="password123",
        )

        mock_uow.users.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Email already exists"):
            auth_service.register_user(register_data)

    def test_register_user_username_exists(
        self, auth_service, mock_uow, sample_user
    ):
        """Test registration with existing username."""
        register_data = RegisterRequest(
            username="test_user",
            email="new@example.com",
            password="password123",
        )

        mock_uow.users.get_by_email.return_value = None
        mock_uow.users.get_by_username.return_value = sample_user

        with pytest.raises(ValidationError, match="Username already exists"):
            auth_service.register_user(register_data)

    def test_authenticate_user_success(
        self, auth_service, mock_uow, sample_user
    ):
        """Test successful user authentication."""
        login_data = LoginRequest(
            email="test@example.com", password="password123"
        )

        mock_uow.users.get_by_email.return_value = sample_user

        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = True

            result = auth_service.authenticate_user(
                login_data.email, login_data.password
            )

            assert result == sample_user
            mock_verify.assert_called_once_with(
                "password123", sample_user.password_hash
            )

    def test_authenticate_user_not_found(self, auth_service, mock_uow):
        """Test authentication with non-existent user."""
        mock_uow.users.get_by_email.return_value = None

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_service.authenticate_user(
                "nonexistent@example.com", "password"
            )

    def test_authenticate_user_wrong_password(
        self, auth_service, mock_uow, sample_user
    ):
        """Test authentication with wrong password."""
        mock_uow.users.get_by_email.return_value = sample_user

        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(
                AuthenticationError, match="Invalid credentials"
            ):
                auth_service.authenticate_user(
                    "test@example.com", "wrong_password"
                )

    def test_authenticate_user_inactive(
        self, auth_service, mock_uow, sample_user
    ):
        """Test authentication with inactive user."""
        sample_user.is_active = False
        mock_uow.users.get_by_email.return_value = sample_user

        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = True

            with pytest.raises(
                AuthenticationError, match="Account is disabled"
            ):
                auth_service.authenticate_user(
                    "test@example.com", "password123"
                )

    def test_generate_tokens(self, auth_service, sample_user):
        """Test JWT token generation."""
        with (
            patch(
                "app.services.auth_service.create_access_token"
            ) as mock_access,
            patch(
                "app.services.auth_service.create_refresh_token"
            ) as mock_refresh,
        ):

            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"

            result = auth_service.generate_tokens(sample_user)

            assert result["access_token"] == "access_token"
            assert result["refresh_token"] == "refresh_token"
            assert result["token_type"] == "bearer"

    def test_verify_email_success(self, auth_service, mock_uow, sample_user):
        """Test successful email verification."""
        sample_user.email_verified = False
        mock_uow.users.get_by_id.return_value = sample_user

        with patch(
            "app.services.auth_service.verify_email_token"
        ) as mock_verify:
            mock_verify.return_value = sample_user.user_id

            result = auth_service.verify_email("valid_token")

            assert result is True
            assert sample_user.email_verified is True
            mock_uow.commit.assert_called_once()

    def test_verify_email_invalid_token(self, auth_service):
        """Test email verification with invalid token."""
        with patch(
            "app.services.auth_service.verify_email_token"
        ) as mock_verify:
            mock_verify.return_value = None

            with pytest.raises(
                ValidationError, match="Invalid verification token"
            ):
                auth_service.verify_email("invalid_token")

    def test_reset_password_success(self, auth_service, mock_uow, sample_user):
        """Test successful password reset."""
        mock_uow.users.get_by_id.return_value = sample_user

        with (
            patch(
                "app.services.auth_service.verify_reset_token"
            ) as mock_verify,
            patch("app.services.auth_service.hash_password") as mock_hash,
        ):

            mock_verify.return_value = sample_user.user_id
            mock_hash.return_value = "new_hashed_password"

            result = auth_service.reset_password("valid_token", "new_password")

            assert result is True
            assert sample_user.password_hash == "new_hashed_password"
            mock_uow.commit.assert_called_once()

    def test_change_password_success(
        self, auth_service, mock_uow, sample_user
    ):
        """Test successful password change."""
        with (
            patch("app.services.auth_service.verify_password") as mock_verify,
            patch("app.services.auth_service.hash_password") as mock_hash,
        ):

            mock_verify.return_value = True
            mock_hash.return_value = "new_hashed_password"

            result = auth_service.change_password(
                sample_user, "old_password", "new_password"
            )

            assert result is True
            assert sample_user.password_hash == "new_hashed_password"
            mock_uow.commit.assert_called_once()

    def test_change_password_wrong_old_password(
        self, auth_service, sample_user
    ):
        """Test password change with wrong old password."""
        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(
                ValidationError, match="Current password is incorrect"
            ):
                auth_service.change_password(
                    sample_user, "wrong_password", "new_password"
                )

    def test_revoke_token(self, auth_service):
        """Test token revocation."""
        with patch(
            "app.services.auth_service.blacklist_token"
        ) as mock_blacklist:
            auth_service.revoke_token("token_to_revoke")
            mock_blacklist.assert_called_once_with("token_to_revoke")

    def test_check_permissions_success(self, auth_service, sample_user):
        """Test successful permission check."""
        sample_user.role_id = RoleID.ADMIN.value

        result = auth_service.check_permissions(
            sample_user, [RoleID.ADMIN.value, RoleID.SUPERADMIN.value]
        )

        assert result is True

    def test_check_permissions_failure(self, auth_service, sample_user):
        """Test failed permission check."""
        sample_user.role_id = RoleID.USER.value

        result = auth_service.check_permissions(
            sample_user, [RoleID.ADMIN.value, RoleID.SUPERADMIN.value]
        )

        assert result is False

    def test_refresh_token_success(self, auth_service, mock_uow, sample_user):
        """Test successful token refresh."""
        mock_uow.users.get_by_id.return_value = sample_user

        with (
            patch(
                "app.services.auth_service.verify_refresh_token"
            ) as mock_verify,
            patch(
                "app.services.auth_service.create_access_token"
            ) as mock_create,
        ):

            mock_verify.return_value = sample_user.user_id
            mock_create.return_value = "new_access_token"

            result = auth_service.refresh_access_token("valid_refresh_token")

            assert result["access_token"] == "new_access_token"
            assert result["token_type"] == "bearer"

    def test_get_user_from_token_success(
        self, auth_service, mock_uow, sample_user
    ):
        """Test successful user retrieval from token."""
        mock_uow.users.get_by_id.return_value = sample_user

        with patch("app.services.auth_service.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": sample_user.user_id}

            result = auth_service.get_user_from_token("valid_token")

            assert result == sample_user
