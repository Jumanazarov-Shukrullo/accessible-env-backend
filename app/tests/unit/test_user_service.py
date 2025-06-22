"""Unit tests for UserService - testing business logic and interactions."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from app.core.constants import RoleID
from app.domain.exceptions import (
    CannotModifySelf,
    CannotModifySuperAdmin,
    InvalidCredentials,
    UserAlreadyExists,
)
from app.models.user_model import User
from app.schemas.user_schema import InviteCreate, UserCreate
from app.services.user_service import UserService


class TestUserService:
    """Test suite for UserService."""

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
    def mock_security_service(self):
        """Mock security service."""
        service = Mock()
        service.hash_password = Mock(return_value="hashed_password")
        service.verify_password = Mock(return_value=True)
        service.create_access_token = Mock(return_value="test_token")
        service.generate_secure_token = Mock(return_value="secure_token")
        return service

    @pytest.fixture
    def user_service(self, mock_uow, mock_security_service):
        """Create UserService instance with mocked dependencies."""
        return UserService(
            uow=mock_uow, security_service=mock_security_service
        )

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            username="testuser",
            email="test@example.com",
            first_name="Test",
            surname="User",
            password_hash="hashed_password",
            role_id=RoleID.USER.value,
            is_active=True,
            email_verified=False,
            created_at=datetime.now(timezone.utc),
        )

    def test_register_user_success(self, user_service, mock_uow):
        """Test successful user registration."""
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="secure_password",
            first_name="New",
            surname="User",
        )

        # Mock repository responses
        mock_uow.users.get_by_username.return_value = None
        mock_uow.users.get_by_email.return_value = None
        mock_uow.users.create.return_value = User(
            user_id="new_user_id",
            username=user_data.username,
            email=user_data.email,
            first_name=user_data.first_name,
            surname=user_data.surname,
        )

        # Execute
        with patch("app.utils.cache.invalidate"):
            user, verification_link = user_service.register_user(user_data)

        # Verify
        assert user.username == user_data.username
        assert user.email == user_data.email
        assert verification_link.startswith("http://")
        mock_uow.users.create.assert_called_once()
        mock_uow.commit.assert_called_once()

    def test_register_user_duplicate_username(
        self, user_service, mock_uow, sample_user
    ):
        """Test registration with duplicate username."""
        user_data = UserCreate(
            username="testuser",
            email="different@example.com",
            password="password",
            first_name="Test",
            surname="User",
        )

        mock_uow.users.get_by_username.return_value = sample_user
        mock_uow.users.get_by_email.return_value = None

        # Should raise UserAlreadyExists
        with pytest.raises(UserAlreadyExists):
            user_service.register_user(user_data)

    def test_register_user_duplicate_email(
        self, user_service, mock_uow, sample_user
    ):
        """Test registration with duplicate email."""
        user_data = UserCreate(
            username="different_user",
            email="test@example.com",
            password="password",
            first_name="Test",
            surname="User",
        )

        mock_uow.users.get_by_username.return_value = None
        mock_uow.users.get_by_email.return_value = sample_user

        # Should raise UserAlreadyExists
        with pytest.raises(UserAlreadyExists):
            user_service.register_user(user_data)

    def test_verify_email_success(
        self, user_service, mock_uow, sample_user, mock_security_service
    ):
        """Test successful email verification."""
        token = "valid_token"
        mock_security_service.decode_token.return_value = {
            "email": sample_user.email
        }
        mock_uow.users.get_by_email.return_value = sample_user
        mock_uow.users.update.return_value = sample_user

        with patch("app.utils.cache.invalidate"):
            result = user_service.verify_email(token)

        assert result.email_verified is True
        mock_uow.users.update.assert_called_once()

    def test_change_role_success(self, user_service, mock_uow, sample_user):
        """Test successful role change."""
        admin_user = User(
            user_id="admin_id",
            username="admin",
            email="admin@example.com",
            role_id=RoleID.ADMIN.value,
            is_active=True,
        )

        target_user = User(
            user_id="target_id",
            username="target",
            email="target@example.com",
            role_id=RoleID.USER.value,
            is_active=True,
        )

        mock_uow.users.get_by_id.return_value = target_user
        mock_uow.users.update.return_value = target_user

        result = user_service.change_role("target_id", "inspector", admin_user)

        assert result.role_id == RoleID.INSPECTOR.value
        mock_uow.users.update.assert_called_once()

    def test_change_role_cannot_modify_superadmin(
        self, user_service, mock_uow
    ):
        """Test that superadmin users cannot be modified."""
        admin_user = User(
            user_id="admin_id", role_id=RoleID.ADMIN.value, is_active=True
        )

        superadmin_user = User(
            user_id="super_id", role_id=RoleID.SUPERADMIN.value, is_active=True
        )

        mock_uow.users.get_by_id.return_value = superadmin_user

        with pytest.raises(CannotModifySuperAdmin):
            user_service.change_role("super_id", "admin", admin_user)

    def test_change_role_cannot_modify_self(self, user_service, mock_uow):
        """Test that users cannot modify their own role."""
        admin_user = User(
            user_id="admin_id", role_id=RoleID.ADMIN.value, is_active=True
        )

        mock_uow.users.get_by_id.return_value = admin_user

        with pytest.raises(CannotModifySelf):
            user_service.change_role("admin_id", "superadmin", admin_user)

    def test_ban_user_success(self, user_service, mock_uow, sample_user):
        """Test successful user ban."""
        admin_user = User(
            user_id="admin_id", role_id=RoleID.ADMIN.value, is_active=True
        )

        mock_uow.users.get_by_id.return_value = sample_user
        mock_uow.users.update.return_value = sample_user

        result = user_service.ban_user(sample_user.user_id, admin_user)

        assert result.is_active is False
        mock_uow.users.update.assert_called_once()

    def test_update_profile_success(self, user_service, sample_user):
        """Test successful profile update."""
        update_data = {"first_name": "Updated", "phone_number": "+1234567890"}

        result = user_service.update_profile(sample_user, update_data)

        assert result.first_name == "Updated"
        assert result.phone_number == "+1234567890"

    def test_update_profile_picture_success(
        self, user_service, sample_user, mock_security_service
    ):
        """Test successful profile picture update."""
        mock_file = Mock()
        mock_file.filename = "test.jpg"

        with patch(
            "app.utils.external_storage.MinioClient"
        ) as mock_minio_class:
            mock_minio = mock_minio_class.return_value
            mock_minio.upload_file = Mock()
            mock_minio.presigned_get_url.return_value = (
                "http://example.com/image.jpg"
            )

            result = user_service.update_profile_picture(
                sample_user, mock_file
            )

            assert result == "http://example.com/image.jpg"
            mock_minio.upload_file.assert_called_once()

    def test_change_password_success(
        self, user_service, sample_user, mock_security_service
    ):
        """Test successful password change."""
        old_password = "old_password"
        new_password = "new_secure_password"

        mock_security_service.verify_password.return_value = True
        mock_security_service.hash_password.return_value = (
            "new_hashed_password"
        )

        user_service.change_password(sample_user, old_password, new_password)

        assert sample_user.password_hash == "new_hashed_password"
        mock_security_service.verify_password.assert_called_once_with(
            old_password, sample_user.password_hash
        )
        mock_security_service.hash_password.assert_called_once_with(
            new_password
        )

    def test_change_password_invalid_old_password(
        self, user_service, sample_user, mock_security_service
    ):
        """Test password change with invalid old password."""
        old_password = "wrong_password"
        new_password = "new_password"

        mock_security_service.verify_password.return_value = False

        with pytest.raises(InvalidCredentials):
            user_service.change_password(
                sample_user, old_password, new_password
            )

    def test_create_user_with_role_success(
        self, user_service, mock_uow, mock_security_service
    ):
        """Test successful user creation with specific role."""
        admin_user = User(
            user_id="admin_id", role_id=RoleID.ADMIN.value, username="admin"
        )

        invite_data = InviteCreate(
            username="invited_user",
            email="invited@example.com",
            first_name="Invited",
            surname="User",
            role_id=RoleID.INSPECTOR.value,
        )

        mock_uow.users.get_by_username.return_value = None
        mock_uow.users.get_by_email.return_value = None

        created_user = User(
            user_id="new_id",
            username=invite_data.username,
            email=invite_data.email,
            role_id=invite_data.role_id,
        )
        mock_uow.users.create.return_value = created_user
        mock_uow.users.update.return_value = created_user

        user, temp_password = user_service.create_user_with_role(
            invite_data, admin_user
        )

        assert user.username == invite_data.username
        assert user.role_id == invite_data.role_id
        assert temp_password == "secure_token"
        mock_uow.users.create.assert_called_once()

    def test_list_users_paginated(self, user_service, mock_uow):
        """Test paginated user listing."""
        mock_users = [Mock(), Mock(), Mock()]
        mock_uow.users.get_minimal_users_paginated.return_value = (
            mock_users,
            3,
        )

        users, total = user_service.list_users_paginated(limit=10, offset=0)

        assert len(users) == 3
        assert total == 3
        mock_uow.users.get_minimal_users_paginated.assert_called_once_with(
            10, 0
        )

    def test_search_users(self, user_service, mock_uow):
        """Test user search functionality."""
        search_term = "test"
        mock_users = [Mock(), Mock()]
        mock_uow.users.search_users.return_value = mock_users

        result = user_service.search_users(search_term, limit=20, offset=0)

        assert len(result) == 2
        mock_uow.users.search_users.assert_called_once()

    def test_get_user_profile(self, user_service, sample_user):
        """Test getting user profile data."""
        profile = user_service.get_user_profile(sample_user)

        assert profile["user_id"] == sample_user.user_id
        assert profile["username"] == sample_user.username
        assert profile["email"] == sample_user.email
        assert profile["full_name"] == "Test User"
        assert profile["role_id"] == sample_user.role_id

    def test_get_user_profile_with_middle_name(self, user_service):
        """Test getting user profile data with middle name."""
        user_with_middle = User(
            user_id="test_id",
            username="testuser",
            email="test@example.com",
            first_name="Test",
            middle_name="Middle",
            surname="User",
        )

        profile = user_service.get_user_profile(user_with_middle)

        assert profile["full_name"] == "Test Middle User"

    @patch("app.utils.cache.invalidate")
    def test_cache_invalidation_on_user_operations(
        self, mock_cache_invalidate, user_service, mock_uow
    ):
        """Test that cache is properly invalidated during user operations."""
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="password",
            first_name="New",
            surname="User",
        )

        mock_uow.users.get_by_username.return_value = None
        mock_uow.users.get_by_email.return_value = None
        mock_uow.users.create.return_value = Mock()

        user_service.register_user(user_data)

        mock_cache_invalidate.assert_called_with("users:")

    def test_user_service_integration_with_domain_service(self, user_service):
        """Test that UserService properly integrates with domain service."""
        # Test domain service is initialized
        assert user_service.domain_service is not None

        # Test that domain service methods are accessible
        assert hasattr(
            user_service.domain_service, "validate_user_registration"
        )
        assert hasattr(user_service.domain_service, "validate_role_change")
        assert hasattr(user_service.domain_service, "construct_full_name")
