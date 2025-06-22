from unittest.mock import patch

from fastapi.testclient import TestClient


class TestUserRoutes:
    """Test suite for user API routes."""

    def test_register_user_success(self, client: TestClient, db_session):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "first_name": "New",
            "surname": "User",
        }

        # Act
        response = client.post("/api/v1/users/register", json=user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == "newuser"
        assert data["user"]["email"] == "newuser@example.com"
        assert "verification_link" in data

    def test_register_user_duplicate_email(
        self, client: TestClient, sample_user
    ):
        """Test registration fails with duplicate email."""
        # Arrange
        user_data = {
            "username": "anotheruser",
            "email": sample_user.email,  # Use existing email
            "password": "password123",
            "first_name": "Another",
            "surname": "User",
        }

        # Act
        response = client.post("/api/v1/users/register", json=user_data)

        # Assert
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_user_duplicate_username(
        self, client: TestClient, sample_user
    ):
        """Test registration fails with duplicate username."""
        # Arrange
        user_data = {
            "username": sample_user.username,  # Use existing username
            "email": "different@example.com",
            "password": "password123",
            "first_name": "Different",
            "surname": "User",
        }

        # Act
        response = client.post("/api/v1/users/register", json=user_data)

        # Assert
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_user_invalid_email(self, client: TestClient):
        """Test registration fails with invalid email format."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123",
            "first_name": "Test",
            "surname": "User",
        }

        # Act
        response = client.post("/api/v1/users/register", json=user_data)

        # Assert
        assert response.status_code == 422

    def test_login_user_success(self, client: TestClient, sample_user):
        """Test successful user login."""
        # Arrange
        login_data = {"email": sample_user.email, "password": "testpass123"}

        # Act
        response = client.post("/api/v1/users/login", json=login_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_user_invalid_credentials(
        self, client: TestClient, sample_user
    ):
        """Test login fails with invalid credentials."""
        # Arrange
        login_data = {"email": sample_user.email, "password": "wrongpassword"}

        # Act
        response = client.post("/api/v1/users/login", json=login_data)

        # Assert
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login fails for nonexistent user."""
        # Arrange
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123",
        }

        # Act
        response = client.post("/api/v1/users/login", json=login_data)

        # Assert
        assert response.status_code == 401

    def test_get_current_user_success(self, client: TestClient, auth_headers):
        """Test successful retrieval of current user."""
        # Act
        response = client.get("/api/v1/users/me", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert "email" in data

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test current user endpoint fails without authentication."""
        # Act
        response = client.get("/api/v1/users/me")

        # Assert
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test current user endpoint fails with invalid token."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}

        # Act
        response = client.get("/api/v1/users/me", headers=headers)

        # Assert
        assert response.status_code == 401

    def test_update_profile_success(self, client: TestClient, auth_headers):
        """Test successful profile update."""
        # Arrange
        update_data = {
            "first_name": "Updated",
            "surname": "Name",
            "phone_number": "555-0123",
        }

        # Act
        response = client.put(
            "/api/v1/users/me/profile", json=update_data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["surname"] == "Name"

    def test_change_password_success(self, client: TestClient, auth_headers):
        """Test successful password change."""
        # Arrange
        password_data = {
            "current_password": "testpass123",
            "new_password": "newpassword123",
        }

        # Act
        response = client.put(
            "/api/v1/users/me/password",
            json=password_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    def test_change_password_wrong_current(
        self, client: TestClient, auth_headers
    ):
        """Test password change fails with wrong current password."""
        # Arrange
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123",
        }

        # Act
        response = client.put(
            "/api/v1/users/me/password",
            json=password_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400

    def test_upload_profile_picture_success(
        self, client: TestClient, auth_headers, mock_minio
    ):
        """Test successful profile picture upload."""
        # Arrange
        files = {"file": ("test.jpg", b"fake image content", "image/jpeg")}

        # Act
        response = client.post(
            "/api/v1/users/me/profile-picture",
            files=files,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "url" in data

    def test_upload_profile_picture_invalid_file(
        self, client: TestClient, auth_headers
    ):
        """Test profile picture upload fails with invalid file type."""
        # Arrange
        files = {"file": ("test.txt", b"not an image", "text/plain")}

        # Act
        response = client.post(
            "/api/v1/users/me/profile-picture",
            files=files,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400

    def test_verify_email_success(self, client: TestClient):
        """Test successful email verification."""
        # Arrange
        with patch(
            "app.core.security.security_manager.verify_token"
        ) as mock_verify:
            mock_verify.return_value = {"email": "test@example.com"}

            # Act
            response = client.get(
                "/api/v1/users/verify-email?token=valid_token"
            )

            # Assert
            assert response.status_code == 200

    def test_verify_email_invalid_token(self, client: TestClient):
        """Test email verification fails with invalid token."""
        # Act
        response = client.get("/api/v1/users/verify-email?token=invalid_token")

        # Assert
        assert response.status_code == 400

    # Admin endpoints tests
    def test_create_user_admin_success(
        self, client: TestClient, admin_auth_headers
    ):
        """Test successful user creation by admin."""
        # Arrange
        user_data = {
            "username": "adminuser",
            "email": "adminuser@example.com",
            "role_id": 1,
            "first_name": "Admin",
            "surname": "User",
        }

        # Act
        response = client.post(
            "/api/v1/users/admin/create",
            json=user_data,
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == "adminuser"
        assert "temporary_password" in data

    def test_create_user_admin_unauthorized(
        self, client: TestClient, auth_headers
    ):
        """Test user creation by admin fails for non-admin user."""
        # Arrange
        user_data = {
            "username": "testuser2",
            "email": "testuser2@example.com",
            "role_id": 1,
            "first_name": "Test",
            "surname": "User",
        }

        # Act
        response = client.post(
            "/api/v1/users/admin/create", json=user_data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 403

    def test_get_users_admin_success(
        self, client: TestClient, admin_auth_headers
    ):
        """Test successful retrieval of users by admin."""
        # Act
        response = client.get(
            "/api/v1/users/admin/users", headers=admin_auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data

    def test_get_users_admin_with_pagination(
        self, client: TestClient, admin_auth_headers
    ):
        """Test user retrieval with pagination parameters."""
        # Act
        response = client.get(
            "/api/v1/users/admin/users?page=1&size=5",
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) <= 5

    def test_get_users_admin_with_search(
        self, client: TestClient, admin_auth_headers
    ):
        """Test user retrieval with search parameter."""
        # Act
        response = client.get(
            "/api/v1/users/admin/users?search=test", headers=admin_auth_headers
        )

        # Assert
        assert response.status_code == 200

    def test_get_users_admin_unauthorized(
        self, client: TestClient, auth_headers
    ):
        """Test user retrieval fails for non-admin user."""
        # Act
        response = client.get(
            "/api/v1/users/admin/users", headers=auth_headers
        )

        # Assert
        assert response.status_code == 403

    def test_get_user_by_id_admin_success(
        self, client: TestClient, admin_auth_headers, sample_user
    ):
        """Test successful retrieval of specific user by admin."""
        # Act
        response = client.get(
            f"/api/v1/users/admin/users/{sample_user.user_id}",
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user.user_id

    def test_get_user_by_id_admin_not_found(
        self, client: TestClient, admin_auth_headers
    ):
        """Test user retrieval by ID fails when user not found."""
        # Act
        response = client.get(
            "/api/v1/users/admin/users/nonexistent-id",
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 404

    def test_update_user_admin_success(
        self, client: TestClient, admin_auth_headers, sample_user
    ):
        """Test successful user update by admin."""
        # Arrange
        update_data = {"username": "updated_user", "is_active": False}

        # Act
        response = client.put(
            f"/api/v1/users/admin/users/{sample_user.user_id}",
            json=update_data,
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "updated_user"

    def test_deactivate_user_admin_success(
        self, client: TestClient, admin_auth_headers, sample_user
    ):
        """Test successful user deactivation by admin."""
        # Act
        response = client.post(
            f"/api/v1/users/admin/users/{sample_user.user_id}/deactivate",
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "User deactivated successfully"

    def test_activate_user_admin_success(
        self, client: TestClient, admin_auth_headers, sample_user
    ):
        """Test successful user activation by admin."""
        # Act
        response = client.post(
            f"/api/v1/users/admin/users/{sample_user.user_id}/activate",
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "User activated successfully"

    def test_delete_user_admin_success(
        self, client: TestClient, admin_auth_headers, sample_user
    ):
        """Test successful user deletion by admin."""
        # Act
        response = client.delete(
            f"/api/v1/users/admin/users/{sample_user.user_id}",
            headers=admin_auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "User deleted successfully"

    def test_admin_operations_unauthorized(
        self, client: TestClient, auth_headers, sample_user
    ):
        """Test admin operations fail for non-admin users."""
        # Test deactivate
        response = client.post(
            f"/api/v1/users/admin/users/{sample_user.user_id}/deactivate",
            headers=auth_headers,
        )
        assert response.status_code == 403

        # Test activate
        response = client.post(
            f"/api/v1/users/admin/users/{sample_user.user_id}/activate",
            headers=auth_headers,
        )
        assert response.status_code == 403

        # Test delete
        response = client.delete(
            f"/api/v1/users/admin/users/{sample_user.user_id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_request_password_reset_success(
        self, client: TestClient, sample_user, mock_email_service
    ):
        """Test successful password reset request."""
        # Arrange
        reset_data = {"email": sample_user.email}

        # Act
        response = client.post(
            "/api/v1/users/password-reset/request", json=reset_data
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Password reset email sent"

    def test_request_password_reset_nonexistent_email(
        self, client: TestClient
    ):
        """Test password reset request for nonexistent email."""
        # Arrange
        reset_data = {"email": "nonexistent@example.com"}

        # Act
        response = client.post(
            "/api/v1/users/password-reset/request", json=reset_data
        )

        # Assert
        assert response.status_code == 404

    def test_confirm_password_reset_success(self, client: TestClient):
        """Test successful password reset confirmation."""
        # Arrange
        reset_data = {
            "token": "valid_reset_token",
            "new_password": "newpassword123",
        }

        with patch(
            "app.core.security.security_manager.verify_token"
        ) as mock_verify:
            mock_verify.return_value = {"email": "test@example.com"}

            # Act
            response = client.post(
                "/api/v1/users/password-reset/confirm", json=reset_data
            )

            # Assert
            assert response.status_code == 200

    def test_confirm_password_reset_invalid_token(self, client: TestClient):
        """Test password reset confirmation fails with invalid token."""
        # Arrange
        reset_data = {
            "token": "invalid_token",
            "new_password": "newpassword123",
        }

        # Act
        response = client.post(
            "/api/v1/users/password-reset/confirm", json=reset_data
        )

        # Assert
        assert response.status_code == 400

    def test_refresh_token_success(self, client: TestClient, sample_user):
        """Test successful token refresh."""
        # Arrange
        refresh_token = "valid_refresh_token"

        with patch(
            "app.core.security.security_manager.verify_token"
        ) as mock_verify:
            mock_verify.return_value = {
                "sub": sample_user.username,
                "user_id": sample_user.user_id,
            }

            # Act
            response = client.post(
                "/api/v1/users/refresh-token",
                json={"refresh_token": refresh_token},
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    def test_refresh_token_invalid(self, client: TestClient):
        """Test token refresh fails with invalid token."""
        # Act
        response = client.post(
            "/api/v1/users/refresh-token",
            json={"refresh_token": "invalid_token"},
        )

        # Assert
        assert response.status_code == 401
