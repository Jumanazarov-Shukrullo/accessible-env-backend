from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.domain.unit_of_work import UnitOfWork
from app.models.user_model import User, UserProfile, UserSecurity
from app.schemas.user_schema import InviteCreate, UserProfileUpdate, UserUpdate
from app.services.user_service import UserService


class TestUserService:
    """Test suite for UserService class."""

    @pytest.fixture
    def mock_uow(self):
        """Create a mock unit of work."""
        mock_uow = Mock(spec=UnitOfWork)
        mock_uow.session = Mock(spec=Session)
        mock_uow.users = Mock()
        mock_uow.commit = Mock()
        mock_uow.rollback = Mock()
        return mock_uow

    @pytest.fixture
    def user_service(self, mock_uow):
        """Create UserService instance with mocked dependencies."""
        return UserService(mock_uow)

    def test_create_user_with_profile_success(
        self, user_service, mock_uow, admin_user
    ):
        """Test successful user creation with profile."""
        # Arrange
        invite_data = InviteCreate(
            username="newuser",
            email="newuser@example.com",
            role_id=1,
            first_name="New",
            surname="User",
            phone_number="123-456-7890",
        )

        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act
        with (
            patch(
                "app.core.security.security_manager.generate_temp_password"
            ) as mock_gen_pass,
            patch(
                "app.core.security.security_manager.get_password_hash"
            ) as mock_hash,
        ):
            mock_gen_pass.return_value = "temp123"
            mock_hash.return_value = "hashed_temp123"

            user, temp_password = user_service.create_user_with_profile(
                invite_data, admin_user
            )

        # Assert
        assert temp_password == "temp123"
        mock_uow.session.add.assert_called()
        mock_uow.commit.assert_called()

    def test_create_user_with_existing_email_raises_exception(
        self, user_service, mock_uow, admin_user
    ):
        """Test user creation fails when email already exists."""
        # Arrange
        invite_data = InviteCreate(
            username="newuser",
            email="existing@example.com",
            role_id=1,
            first_name="New",
            surname="User",
        )

        existing_user = Mock(spec=User)
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            existing_user)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            user_service.create_user_with_profile(invite_data, admin_user)

        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)

    def test_get_user_with_profile_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful retrieval of user with profile."""
        # Arrange
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            sample_user)

        # Act
        result = user_service.get_user_with_profile(sample_user.user_id)

        # Assert
        assert result is not None
        mock_uow.session.query.assert_called()

    def test_get_user_with_profile_not_found(self, user_service, mock_uow):
        """Test user retrieval returns None when user not found."""
        # Arrange
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None)

        # Act
        result = user_service.get_user_with_profile("nonexistent_id")

        # Assert
        assert result is None

    def test_get_user_by_email_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful retrieval of user by email."""
        # Arrange
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            sample_user)

        # Act
        result = user_service.get_user_by_email(sample_user.email)

        # Assert
        assert result == sample_user

    def test_get_user_by_username_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful retrieval of user by username."""
        # Arrange
        mock_uow.session.query.return_value.options.return_value.filter.return_value.first.return_value = (
            sample_user)

        # Act
        result = user_service.get_user_by_username(sample_user.username)

        # Assert
        assert result == sample_user

    def test_update_user_core_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful core user data update."""
        # Arrange
        user_update = UserUpdate(
            username="updated_user", email="updated@example.com"
        )
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            sample_user)

        with patch.object(user_service, "get_user_with_profile") as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = user_service.update_user_core(
                sample_user.user_id, user_update
            )

            # Assert
            assert result is not None
            mock_uow.commit.assert_called()

    def test_update_user_core_not_found(self, user_service, mock_uow):
        """Test user core update fails when user not found."""
        # Arrange
        user_update = UserUpdate(username="updated_user")
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            user_service.update_user_core("nonexistent_id", user_update)

        assert exc_info.value.status_code == 404

    def test_update_user_profile_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful user profile update."""
        # Arrange
        profile_update = UserProfileUpdate(
            first_name="Updated", surname="Name"
        )
        mock_profile = Mock(spec=UserProfile)
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_profile)

        with patch.object(user_service, "get_user_with_profile") as mock_get:
            mock_get.return_value = Mock()

            # Act
            result = user_service.update_user_profile(
                sample_user.user_id, profile_update
            )

            # Assert
            assert result is not None
            mock_uow.commit.assert_called()

    def test_update_user_profile_creates_new_profile(
        self, user_service, mock_uow, sample_user
    ):
        """Test profile update creates new profile if none exists."""
        # Arrange
        profile_update = UserProfileUpdate(first_name="New", surname="Profile")
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        with patch.object(user_service, "get_user_with_profile") as mock_get:
            mock_get.return_value = Mock()

            # Act
            user_service.update_user_profile(
                sample_user.user_id, profile_update
            )

            # Assert
            mock_uow.session.add.assert_called()
            mock_uow.commit.assert_called()

    def test_authenticate_user_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful user authentication."""
        # Arrange
        mock_user_with_security = Mock(spec=User)
        mock_user_with_security.security = Mock(spec=UserSecurity)
        mock_user_with_security.security.failed_login_attempts = 0
        mock_user_with_security.password_hash = "hashed_password"

        with (
            patch.object(user_service, "get_user_by_email") as mock_get,
            patch(
                "app.core.security.security_manager.verify_password"
            ) as mock_verify,
        ):
            mock_get.return_value = mock_user_with_security
            mock_verify.return_value = True

            # Act
            result = user_service.authenticate_user(
                "test@example.com", "testpass123", "127.0.0.1"
            )

            # Assert
            assert result == mock_user_with_security
            mock_uow.commit.assert_called()

    def test_authenticate_user_invalid_password(
        self, user_service, mock_uow, sample_user
    ):
        """Test authentication fails with invalid password."""
        # Arrange
        mock_user_with_security = Mock(spec=User)
        mock_user_with_security.security = Mock(spec=UserSecurity)
        mock_user_with_security.security.failed_login_attempts = 0

        with (
            patch.object(user_service, "get_user_by_email") as mock_get,
            patch(
                "app.core.security.security_manager.verify_password"
            ) as mock_verify,
        ):
            mock_get.return_value = mock_user_with_security
            mock_verify.return_value = False

            # Act
            result = user_service.authenticate_user(
                "test@example.com", "wrongpass", "127.0.0.1"
            )

            # Assert
            assert result is None
            assert mock_user_with_security.security.failed_login_attempts == 1

    def test_authenticate_user_account_locked(self, user_service, mock_uow):
        """Test authentication fails when account is locked."""
        # Arrange
        mock_user_with_security = Mock(spec=User)
        mock_user_with_security.security = Mock(spec=UserSecurity)
        mock_user_with_security.security.failed_login_attempts = 5

        with patch.object(user_service, "get_user_by_email") as mock_get:
            mock_get.return_value = mock_user_with_security

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                user_service.authenticate_user(
                    "test@example.com", "password", "127.0.0.1"
                )

            assert exc_info.value.status_code == 423

    def test_get_users_paginated_success(self, user_service, mock_uow):
        """Test successful paginated user retrieval."""
        # Arrange
        mock_users = [Mock(spec=User) for _ in range(3)]
        for i, user in enumerate(mock_users):
            user.user_id = f"user_{i}"
            user.username = f"user_{i}"
            user.email = f"user{i}@example.com"
            user.is_active = True
            user.role = Mock()
            user.role.role_name = "user"
            user.profile = Mock()
            user.profile.full_name = f"User {i}"
            user.security = Mock()
            user.security.last_login_at = None

        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_users

        mock_uow.session.query.return_value = mock_query

        # Act
        users, total = user_service.get_users_paginated(page=1, size=10)

        # Assert
        assert len(users) == 3
        assert total == 3

    def test_change_password_success(
        self, user_service, mock_uow, sample_user
    ):
        """Test successful password change."""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.password_hash = "old_hash"
        mock_user.security = Mock(spec=UserSecurity)

        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_user)

        with (
            patch(
                "app.core.security.security_manager.verify_password"
            ) as mock_verify,
            patch(
                "app.core.security.security_manager.get_password_hash"
            ) as mock_hash,
        ):
            mock_verify.return_value = True
            mock_hash.return_value = "new_hash"

            # Act
            result = user_service.change_password(
                sample_user.user_id, "oldpass", "newpass"
            )

            # Assert
            assert result is True
            assert mock_user.password_hash == "new_hash"
            mock_uow.commit.assert_called()

    def test_change_password_wrong_current_password(
        self, user_service, mock_uow, sample_user
    ):
        """Test password change fails with wrong current password."""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.password_hash = "old_hash"

        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            mock_user)

        with patch(
            "app.core.security.security_manager.verify_password"
        ) as mock_verify:
            mock_verify.return_value = False

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                user_service.change_password(
                    sample_user.user_id, "wrongpass", "newpass"
                )

            assert exc_info.value.status_code == 400

    def test_deactivate_user_success(self, user_service, mock_uow, admin_user):
        """Test successful user deactivation."""
        # Arrange
        target_user = Mock(spec=User)
        target_user.username = "target_user"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            target_user)

        # Act
        result = user_service.deactivate_user("target_id", admin_user)

        # Assert
        assert result is True
        assert target_user.is_active is False
        mock_uow.commit.assert_called()

    def test_activate_user_success(self, user_service, mock_uow, admin_user):
        """Test successful user activation."""
        # Arrange
        target_user = Mock(spec=User)
        target_user.username = "target_user"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            target_user)

        # Act
        result = user_service.activate_user("target_id", admin_user)

        # Assert
        assert result is True
        assert target_user.is_active is True
        mock_uow.commit.assert_called()

    def test_delete_user_success(self, user_service, mock_uow, admin_user):
        """Test successful user deletion."""
        # Arrange
        target_user = Mock(spec=User)
        target_user.username = "target_user"
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            target_user)

        # Act
        result = user_service.delete_user("target_id", admin_user)

        # Assert
        assert result is True
        mock_uow.session.delete.assert_called_with(target_user)
        mock_uow.commit.assert_called()

    def test_user_not_found_operations(
        self, user_service, mock_uow, admin_user
    ):
        """Test operations fail when user is not found."""
        # Arrange
        mock_uow.session.query.return_value.filter.return_value.first.return_value = (
            None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            user_service.deactivate_user("nonexistent_id", admin_user)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            user_service.activate_user("nonexistent_id", admin_user)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            user_service.delete_user("nonexistent_id", admin_user)
        assert exc_info.value.status_code == 404
